using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace SomSkillWorker;

/// <summary>
/// Generic interpreter for SkillRule data. Every rule has a Type discriminator;
/// supported types and the Config keys each expects:
///
///   term_match                 → field, terms[], case_sensitive?
///                                Fires once per matching term in the field's value.
///   phase_with_missing_field   → phase_field, phase, field
///                                Fires when phase_field equals phase AND field is null/empty.
///   field_value_in             → field, values[]
///                                Fires when field's value matches one of values.
///   field_present              → field
///                                Fires when field exists and is not null/empty.
///   field_absent               → field
///                                Fires when field is missing or null/empty.
///   field_regex                → field, pattern, case_sensitive?
///                                Fires when field matches the regex.
///
/// Detail strings come from rule.detail_template with {term} / {value} substitutions
/// where applicable. Returning multiple matches per rule is supported (e.g. term_match
/// fires once per matched term so the editor sees each occurrence separately).
/// </summary>
public sealed class RuleEngine
{
    public IEnumerable<RuleMatch> Evaluate(SkillRule rule, JsonNode story) => rule.Type switch
    {
        "term_match"               => EvalTermMatch(rule, story),
        "phase_with_missing_field" => EvalPhaseMissingField(rule, story),
        "field_value_in"           => EvalFieldValueIn(rule, story),
        "field_present"            => EvalFieldPresent(rule, story, expectPresent: true),
        "field_absent"             => EvalFieldPresent(rule, story, expectPresent: false),
        "field_regex"              => EvalFieldRegex(rule, story),
        _                          => Array.Empty<RuleMatch>(),
    };

    // ─── Rule type implementations ──────────────────────────────────────────

    private static IEnumerable<RuleMatch> EvalTermMatch(SkillRule rule, JsonNode story)
    {
        var field = GetString(rule.Config, "field");
        var terms = GetStringArray(rule.Config, "terms");
        var caseSensitive = GetBool(rule.Config, "case_sensitive", false);
        if (field is null || terms.Length == 0) yield break;

        var value = GetByPath(story, field)?.GetValue<string>() ?? "";
        if (string.IsNullOrEmpty(value)) yield break;

        var cmp = caseSensitive ? StringComparison.Ordinal : StringComparison.OrdinalIgnoreCase;
        foreach (var term in terms)
        {
            if (value.IndexOf(term, cmp) >= 0)
                yield return new RuleMatch(rule, RenderDetail(rule, ("term", term), ("field", field), ("value", value)));
        }
    }

    private static IEnumerable<RuleMatch> EvalPhaseMissingField(SkillRule rule, JsonNode story)
    {
        var phaseField = GetString(rule.Config, "phase_field") ?? "lifecycle.phase";
        var phase = GetString(rule.Config, "phase");
        var field = GetString(rule.Config, "field");
        if (phase is null || field is null) yield break;

        var actualPhase = GetByPath(story, phaseField)?.GetValue<string>();
        if (!string.Equals(actualPhase, phase, StringComparison.OrdinalIgnoreCase)) yield break;

        if (IsEmpty(GetByPath(story, field)))
            yield return new RuleMatch(rule, RenderDetail(rule, ("phase", phase), ("field", field)));
    }

    private static IEnumerable<RuleMatch> EvalFieldValueIn(SkillRule rule, JsonNode story)
    {
        var field = GetString(rule.Config, "field");
        var values = GetStringArray(rule.Config, "values");
        if (field is null || values.Length == 0) yield break;

        var actual = GetByPath(story, field)?.GetValue<string>();
        if (actual is null) yield break;

        foreach (var v in values)
        {
            if (string.Equals(actual, v, StringComparison.OrdinalIgnoreCase))
            {
                yield return new RuleMatch(rule, RenderDetail(rule, ("value", v), ("field", field)));
                yield break;
            }
        }
    }

    private static IEnumerable<RuleMatch> EvalFieldPresent(SkillRule rule, JsonNode story, bool expectPresent)
    {
        var field = GetString(rule.Config, "field");
        if (field is null) yield break;

        var present = !IsEmpty(GetByPath(story, field));
        if (present == expectPresent)
            yield return new RuleMatch(rule, RenderDetail(rule, ("field", field)));
    }

    private static IEnumerable<RuleMatch> EvalFieldRegex(SkillRule rule, JsonNode story)
    {
        var field = GetString(rule.Config, "field");
        var pattern = GetString(rule.Config, "pattern");
        var caseSensitive = GetBool(rule.Config, "case_sensitive", false);
        if (field is null || pattern is null) yield break;

        var value = GetByPath(story, field)?.GetValue<string>();
        if (value is null) yield break;

        var opts = caseSensitive ? RegexOptions.None : RegexOptions.IgnoreCase;
        Match m;
        try { m = Regex.Match(value, pattern, opts); }
        catch (ArgumentException) { yield break; }

        if (m.Success)
            yield return new RuleMatch(rule, RenderDetail(rule, ("match", m.Value), ("field", field), ("value", value)));
    }

    // ─── Helpers ────────────────────────────────────────────────────────────

    /// <summary>
    /// Walk a dotted path through a JsonNode, e.g. "lifecycle.phase".
    /// Returns null if any segment is missing.
    /// </summary>
    public static JsonNode? GetByPath(JsonNode root, string path)
    {
        JsonNode? current = root;
        foreach (var part in path.Split('.'))
        {
            if (current is null) return null;
            current = current is JsonObject obj && obj.ContainsKey(part) ? obj[part] : null;
        }
        return current;
    }

    private static bool IsEmpty(JsonNode? node)
    {
        if (node is null) return true;
        if (node is JsonArray arr) return arr.Count == 0;
        if (node is JsonValue val)
        {
            var s = val.ToString();
            return string.IsNullOrWhiteSpace(s);
        }
        return false;
    }

    private static string? GetString(JsonObject? config, string key) =>
        config?.TryGetPropertyValue(key, out var node) == true && node is not null
            ? node.GetValue<string>()
            : null;

    private static bool GetBool(JsonObject? config, string key, bool defaultValue)
    {
        if (config is null || !config.TryGetPropertyValue(key, out var node) || node is null)
            return defaultValue;
        return node.GetValue<bool>();
    }

    private static string[] GetStringArray(JsonObject? config, string key)
    {
        if (config is null || !config.TryGetPropertyValue(key, out var node) || node is not JsonArray arr)
            return Array.Empty<string>();
        return arr.OfType<JsonNode>().Select(n => n?.GetValue<string>() ?? "")
                  .Where(s => !string.IsNullOrEmpty(s))
                  .ToArray();
    }

    private static string RenderDetail(SkillRule rule, params (string Key, string Value)[] subs)
    {
        var template = string.IsNullOrWhiteSpace(rule.DetailTemplate)
            ? rule.Description
            : rule.DetailTemplate;
        var result = template ?? rule.Name;
        foreach (var (k, v) in subs)
            result = result.Replace("{" + k + "}", v);
        return result;
    }
}

public sealed record RuleMatch(SkillRule Rule, string Detail);
