using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace SomSkillWorker;

/// <summary>
/// Layer 3 of skill validation: ship the skill + sample stories to an LLM and ask
/// for editorial review. Pluggable behind ISkillReviewer so vendors can swap the
/// provider. Default factory auto-selects based on env vars:
///
///   GOOGLE_API_KEY or GEMINI_API_KEY  → Gemini  (preferred, Google is providing keys)
///   ANTHROPIC_API_KEY                 → Claude  (Anthropic)
///   (none)                            → NoopSkillReviewer (returns "not configured")
///
/// All providers return the same SkillReviewResult shape so the UI doesn't care
/// which one ran.
/// </summary>
public interface ISkillReviewer
{
    string ProviderName { get; }
    bool Available { get; }
    Task<SkillReviewResult> ReviewAsync(
        SkillDefinition skill,
        IReadOnlyCollection<JsonNode> sampleStories,
        DryRunResult? dryRun,
        CancellationToken ct);
}

public sealed record SkillReviewResult(
    bool Available,
    string Provider,
    string? Summary,
    SkillReviewFinding[] Findings,
    string? Error,
    string? RawResponse);

public sealed record SkillReviewFinding(
    string Severity,    // info | warning | suggestion | nit
    string Category,    // naming | rule_logic | edge_cases | descriptions | detail_template | other
    string Message,
    string? RuleId);

// ─── Provider selection ─────────────────────────────────────────────────────

public static class SkillReviewerFactory
{
    public static ISkillReviewer Create(IHttpClientFactory http, ILoggerFactory logFactory)
    {
        var googleKey = Environment.GetEnvironmentVariable("GOOGLE_API_KEY")
                     ?? Environment.GetEnvironmentVariable("GEMINI_API_KEY");
        if (!string.IsNullOrWhiteSpace(googleKey))
            return new GeminiSkillReviewer(http, logFactory.CreateLogger<GeminiSkillReviewer>(), googleKey);

        var anthropicKey = Environment.GetEnvironmentVariable("ANTHROPIC_API_KEY");
        if (!string.IsNullOrWhiteSpace(anthropicKey))
            return new AnthropicSkillReviewer(http, logFactory.CreateLogger<AnthropicSkillReviewer>(), anthropicKey);

        return new NoopSkillReviewer();
    }
}

// ─── Shared prompt ───────────────────────────────────────────────────────────

internal static class SkillReviewPrompt
{
    public static string Build(SkillDefinition skill, IReadOnlyCollection<JsonNode> sampleStories, DryRunResult? dryRun)
    {
        var skillJson = JsonSerializer.Serialize(skill, SkillDefinitionJson.Options);
        var samplesJson = JsonSerializer.Serialize(sampleStories.Select(s => new
        {
            story_id = s["story_id"]?.GetValue<string>() ?? s["payload"]?["story_id"]?.GetValue<string>(),
            headline = s["headline"]?.GetValue<string>() ?? s["payload"]?["headline"]?.GetValue<string>(),
            phase    = (s["lifecycle"] ?? s["payload"]?["lifecycle"])?["phase"]?.GetValue<string>(),
        }).ToArray());
        var dryRunJson = dryRun is null ? "null" : JsonSerializer.Serialize(dryRun);

        return $$"""
            You are reviewing a SOM (Semantic Object Model) skill that runs inside a broadcast newsroom system.
            The skill consumes story.context messages from a Kafka bus and emits skill.warning.raised messages
            when its rules match. Editors see these warnings and decide whether to approve or reject them.

            SKILL DEFINITION:
            {{skillJson}}

            SAMPLE STORIES the skill is evaluated against:
            {{samplesJson}}

            DRY-RUN RESULTS (which rules fire on which sample stories):
            {{dryRunJson}}

            Review the skill against these criteria:
            1. Naming — are skill name, rule names, and rule_ids clear and editor-friendly?
            2. Rule logic — are detection terms, regex patterns, or value lists too broad, too narrow, or wrong?
            3. Edge cases — what realistic newsroom scenarios might this skill miss or over-fire on?
            4. Descriptions — is the skill description and each rule description accurate and useful for editors?
            5. Detail template — when a warning fires, will the rendered detail string help an editor understand WHY?

            Reply ONLY with a JSON object in EXACTLY this shape (no prose, no markdown fences):
            {
              "summary": "1-2 sentence overall assessment of this skill's quality and soundness",
              "findings": [
                {
                  "severity": "info" | "warning" | "suggestion" | "nit",
                  "category": "naming" | "rule_logic" | "edge_cases" | "descriptions" | "detail_template" | "other",
                  "message": "specific actionable feedback",
                  "rule_id": "rule-id-this-applies-to (or null if skill-wide)"
                }
              ]
            }

            Aim for 3-7 findings total. Be specific and actionable — "rename rule X to Y because Z" not "improve naming".
            """;
    }

    /// <summary>
    /// Robust JSON extraction. Models sometimes wrap JSON in ```json fences or add a preamble.
    /// </summary>
    public static SkillReviewResult ParseModelReply(string raw, string provider)
    {
        var json = ExtractJson(raw);
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            var summary = root.TryGetProperty("summary", out var s) ? s.GetString() : null;
            var findings = new List<SkillReviewFinding>();
            if (root.TryGetProperty("findings", out var f) && f.ValueKind == JsonValueKind.Array)
            {
                foreach (var item in f.EnumerateArray())
                {
                    findings.Add(new SkillReviewFinding(
                        Severity: item.TryGetProperty("severity", out var sev) ? (sev.GetString() ?? "info") : "info",
                        Category: item.TryGetProperty("category", out var cat) ? (cat.GetString() ?? "other") : "other",
                        Message: item.TryGetProperty("message", out var msg) ? (msg.GetString() ?? "") : "",
                        RuleId: item.TryGetProperty("rule_id", out var rid) && rid.ValueKind != JsonValueKind.Null
                            ? rid.GetString() : null));
                }
            }
            return new SkillReviewResult(true, provider, summary, findings.ToArray(), null, raw);
        }
        catch (JsonException ex)
        {
            return new SkillReviewResult(true, provider, null, Array.Empty<SkillReviewFinding>(),
                $"Could not parse model reply as JSON: {ex.Message}", raw);
        }
    }

    private static string ExtractJson(string text)
    {
        // Strip ```json fences if present
        var trimmed = text.Trim();
        if (trimmed.StartsWith("```"))
        {
            var firstNl = trimmed.IndexOf('\n');
            if (firstNl > 0) trimmed = trimmed[(firstNl + 1)..];
            var lastFence = trimmed.LastIndexOf("```", StringComparison.Ordinal);
            if (lastFence > 0) trimmed = trimmed[..lastFence];
            trimmed = trimmed.Trim();
        }
        // Find the outermost JSON object
        var firstBrace = trimmed.IndexOf('{');
        var lastBrace = trimmed.LastIndexOf('}');
        if (firstBrace >= 0 && lastBrace > firstBrace)
            return trimmed.Substring(firstBrace, lastBrace - firstBrace + 1);
        return trimmed;
    }
}

// ─── Noop (no API key configured) ───────────────────────────────────────────

public sealed class NoopSkillReviewer : ISkillReviewer
{
    public string ProviderName => "none";
    public bool Available => false;

    public Task<SkillReviewResult> ReviewAsync(
        SkillDefinition skill,
        IReadOnlyCollection<JsonNode> sampleStories,
        DryRunResult? dryRun,
        CancellationToken ct)
    {
        return Task.FromResult(new SkillReviewResult(
            Available: false,
            Provider: "none",
            Summary: null,
            Findings: Array.Empty<SkillReviewFinding>(),
            Error: "AI review is not configured. Set GOOGLE_API_KEY (or ANTHROPIC_API_KEY) to enable.",
            RawResponse: null));
    }
}

// ─── Google Gemini ──────────────────────────────────────────────────────────

public sealed class GeminiSkillReviewer : ISkillReviewer
{
    private readonly IHttpClientFactory _http;
    private readonly ILogger<GeminiSkillReviewer> _logger;
    private readonly string _apiKey;
    private readonly string _model;

    public string ProviderName => $"google/{_model}";
    public bool Available => true;

    public GeminiSkillReviewer(IHttpClientFactory http, ILogger<GeminiSkillReviewer> logger, string apiKey)
    {
        _http = http;
        _logger = logger;
        _apiKey = apiKey;
        _model = Environment.GetEnvironmentVariable("GEMINI_MODEL") ?? "gemini-2.0-flash";
    }

    public async Task<SkillReviewResult> ReviewAsync(
        SkillDefinition skill,
        IReadOnlyCollection<JsonNode> sampleStories,
        DryRunResult? dryRun,
        CancellationToken ct)
    {
        var prompt = SkillReviewPrompt.Build(skill, sampleStories, dryRun);
        var url = $"https://generativelanguage.googleapis.com/v1beta/models/{Uri.EscapeDataString(_model)}:generateContent?key={_apiKey}";
        var body = new JsonObject
        {
            ["contents"] = new JsonArray(new JsonObject
            {
                ["parts"] = new JsonArray(new JsonObject { ["text"] = prompt }),
            }),
            ["generationConfig"] = new JsonObject
            {
                ["temperature"] = 0.3,
                ["responseMimeType"] = "application/json",
            },
        };

        try
        {
            using var http = _http.CreateClient();
            http.Timeout = TimeSpan.FromSeconds(45);
            using var req = new HttpRequestMessage(HttpMethod.Post, url)
            {
                Content = new StringContent(body.ToJsonString(), Encoding.UTF8, "application/json"),
            };
            using var resp = await http.SendAsync(req, ct);
            var text = await resp.Content.ReadAsStringAsync(ct);
            if (!resp.IsSuccessStatusCode)
            {
                _logger.LogWarning("Gemini returned {Status}: {Body}", resp.StatusCode, text);
                return new SkillReviewResult(true, ProviderName, null, Array.Empty<SkillReviewFinding>(),
                    $"Gemini API {(int)resp.StatusCode}: {Truncate(text, 400)}", text);
            }
            var modelText = ExtractGeminiText(text);
            return SkillReviewPrompt.ParseModelReply(modelText, ProviderName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Gemini review failed");
            return new SkillReviewResult(true, ProviderName, null, Array.Empty<SkillReviewFinding>(),
                $"Gemini call failed: {ex.Message}", null);
        }
    }

    private static string ExtractGeminiText(string responseJson)
    {
        try
        {
            using var doc = JsonDocument.Parse(responseJson);
            var candidates = doc.RootElement.GetProperty("candidates");
            var parts = candidates[0].GetProperty("content").GetProperty("parts");
            return parts[0].GetProperty("text").GetString() ?? "";
        }
        catch { return responseJson; }
    }

    private static string Truncate(string s, int max) => s.Length <= max ? s : s[..max] + "…";
}

// ─── Anthropic Claude ───────────────────────────────────────────────────────

public sealed class AnthropicSkillReviewer : ISkillReviewer
{
    private readonly IHttpClientFactory _http;
    private readonly ILogger<AnthropicSkillReviewer> _logger;
    private readonly string _apiKey;
    private readonly string _model;

    public string ProviderName => $"anthropic/{_model}";
    public bool Available => true;

    public AnthropicSkillReviewer(IHttpClientFactory http, ILogger<AnthropicSkillReviewer> logger, string apiKey)
    {
        _http = http;
        _logger = logger;
        _apiKey = apiKey;
        _model = Environment.GetEnvironmentVariable("ANTHROPIC_MODEL") ?? "claude-sonnet-4-5-20250929";
    }

    public async Task<SkillReviewResult> ReviewAsync(
        SkillDefinition skill,
        IReadOnlyCollection<JsonNode> sampleStories,
        DryRunResult? dryRun,
        CancellationToken ct)
    {
        var prompt = SkillReviewPrompt.Build(skill, sampleStories, dryRun);
        var body = new JsonObject
        {
            ["model"] = _model,
            ["max_tokens"] = 2048,
            ["messages"] = new JsonArray(new JsonObject
            {
                ["role"] = "user",
                ["content"] = prompt,
            }),
        };

        try
        {
            using var http = _http.CreateClient();
            http.Timeout = TimeSpan.FromSeconds(45);
            using var req = new HttpRequestMessage(HttpMethod.Post, "https://api.anthropic.com/v1/messages")
            {
                Content = new StringContent(body.ToJsonString(), Encoding.UTF8, "application/json"),
            };
            req.Headers.TryAddWithoutValidation("x-api-key", _apiKey);
            req.Headers.TryAddWithoutValidation("anthropic-version", "2023-06-01");

            using var resp = await http.SendAsync(req, ct);
            var text = await resp.Content.ReadAsStringAsync(ct);
            if (!resp.IsSuccessStatusCode)
            {
                _logger.LogWarning("Anthropic returned {Status}: {Body}", resp.StatusCode, text);
                return new SkillReviewResult(true, ProviderName, null, Array.Empty<SkillReviewFinding>(),
                    $"Anthropic API {(int)resp.StatusCode}: {Truncate(text, 400)}", text);
            }
            var modelText = ExtractAnthropicText(text);
            return SkillReviewPrompt.ParseModelReply(modelText, ProviderName);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Anthropic review failed");
            return new SkillReviewResult(true, ProviderName, null, Array.Empty<SkillReviewFinding>(),
                $"Anthropic call failed: {ex.Message}", null);
        }
    }

    private static string ExtractAnthropicText(string responseJson)
    {
        try
        {
            using var doc = JsonDocument.Parse(responseJson);
            var content = doc.RootElement.GetProperty("content");
            return content[0].GetProperty("text").GetString() ?? "";
        }
        catch { return responseJson; }
    }

    private static string Truncate(string s, int max) => s.Length <= max ? s : s[..max] + "…";
}
