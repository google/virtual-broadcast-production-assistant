using System.Net.WebSockets;
using System.Text.Json.Nodes;
using SomSkillWorker;

// ── Test producer mode (CLI) ──────────────────────────
// dotnet run -- --test-producer                                  → publishes ALL seed stories
// dotnet run -- --test-producer --story breaking                 → single scenario
// dotnet run -- --test-producer --story informal
// dotnet run -- --test-producer --story election
// dotnet run -- --test-producer --story clean
// dotnet run -- --test-producer --story breaking-no-compliance
if (args.Contains("--test-producer"))
{
    var storyIdx = Array.IndexOf(args, "--story");
    var scenario = storyIdx >= 0 && storyIdx + 1 < args.Length
        ? args[storyIdx + 1]
        : null;

    await TestProducer.RunAsync(scenario);
    return;
}

// ── Skill worker + dashboard mode ─────────────────────
var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<KafkaOptions>(builder.Configuration.GetSection("Kafka"));
builder.Services.AddSingleton<SkillRegistry>();
builder.Services.AddSingleton<RuleEngine>();
builder.Services.AddSingleton<SkillDryRunner>();
builder.Services.AddHttpClient();
builder.Services.AddSingleton<ISkillReviewer>(sp => SkillReviewerFactory.Create(
    sp.GetRequiredService<IHttpClientFactory>(),
    sp.GetRequiredService<ILoggerFactory>()));
builder.Services.AddSingleton<DashboardService>();
builder.Services.AddHostedService(sp => sp.GetRequiredService<DashboardService>());
builder.Services.AddHostedService<SkillWorker>();
builder.Services.AddSingleton<SimulatorService>();
builder.Services.AddHostedService(sp => sp.GetRequiredService<SimulatorService>());

builder.WebHost.ConfigureKestrel(o => o.ListenLocalhost(5050));

var app = builder.Build();

app.UseDefaultFiles();
app.UseStaticFiles();
app.UseWebSockets();

app.MapGet("/api/pending", (DashboardService dash) => Results.Ok(dash.SnapshotPending()));

// ── Skills CRUD ────────────────────────────────────────
app.MapGet("/api/skills", (SkillRegistry registry) => Results.Ok(registry.All()));

app.MapGet("/api/skills/{id}", (string id, SkillRegistry registry) =>
{
    var skill = registry.Get(Uri.UnescapeDataString(id));
    return skill is null
        ? Results.NotFound(new { error = "skill_not_found" })
        : Results.Ok(skill);
});

app.MapPost("/api/skills", (SkillDefinition skill, SkillRegistry registry) =>
{
    var validation = SkillValidation.Validate(skill);
    if (!validation.Ok)
        return Results.BadRequest(new { error = "validation_failed", validation.Errors, validation.Warnings });
    if (string.IsNullOrWhiteSpace(skill.Id))
        return Results.BadRequest(new { error = "id is required" });
    return registry.Add(skill)
        ? Results.Created($"/api/skills/{Uri.EscapeDataString(skill.Id)}",
            new { skill, warnings = validation.Warnings })
        : Results.Conflict(new { error = "skill_already_exists" });
});

app.MapPut("/api/skills/{id}", (string id, SkillDefinition skill, SkillRegistry registry) =>
{
    var validation = SkillValidation.Validate(skill);
    if (!validation.Ok)
        return Results.BadRequest(new { error = "validation_failed", validation.Errors, validation.Warnings });
    var decoded = Uri.UnescapeDataString(id);
    return registry.Update(decoded, skill)
        ? Results.Ok(new { skill, warnings = validation.Warnings })
        : Results.NotFound(new { error = "skill_not_found" });
});

// Layer 1: validate-only endpoint — no save, just feedback.
app.MapPost("/api/skills/validate",
    (SkillDefinition skill) => Results.Ok(SkillValidation.Validate(skill)));

// Layer 2: dry-run — evaluate against all seed stories, report matches.
app.MapPost("/api/skills/dry-run", async (SkillDefinition skill, SkillDryRunner dryRunner) =>
    Results.Ok(await dryRunner.RunAsync(skill)));

app.MapPost("/api/skills/{id}/dry-run",
    async (string id, SkillRegistry registry, SkillDryRunner dryRunner) =>
{
    var skill = registry.Get(Uri.UnescapeDataString(id));
    return skill is null
        ? Results.NotFound(new { error = "skill_not_found" })
        : Results.Ok(await dryRunner.RunAsync(skill));
});

// Layer 3: AI review — ship to Gemini/Anthropic, parse structured findings.
app.MapGet("/api/skills/ai-review/status",
    (ISkillReviewer reviewer) => Results.Ok(new
    {
        available = reviewer.Available,
        provider = reviewer.ProviderName,
    }));

app.MapPost("/api/skills/{id}/ai-review", async (
    string id,
    SkillRegistry registry,
    SkillDryRunner dryRunner,
    ISkillReviewer reviewer,
    CancellationToken ct) =>
{
    var skill = registry.Get(Uri.UnescapeDataString(id));
    if (skill is null) return Results.NotFound(new { error = "skill_not_found" });

    // Pull the same seed stories the dry-runner uses, so the AI sees the actual
    // sample data the skill will run against.
    var samples = new List<JsonNode>();
    foreach (var scenario in TestProducer.Scenarios)
    {
        var json = await TestProducer.LoadScenarioJsonAsync(scenario);
        if (json is null) continue;
        var node = JsonNode.Parse(json);
        if (node is not null) samples.Add(node["payload"] ?? node);
    }
    var dryRun = await dryRunner.RunAsync(skill);
    var result = await reviewer.ReviewAsync(skill, samples, dryRun, ct);
    return Results.Ok(result);
});

app.MapDelete("/api/skills/{id}", (string id, SkillRegistry registry) =>
{
    var decoded = Uri.UnescapeDataString(id);
    return registry.Delete(decoded)
        ? Results.NoContent()
        : Results.NotFound(new { error = "skill_not_found" });
});

app.MapGet("/api/seed-stories", () => Results.Ok(TestProducer.Scenarios));

app.MapGet("/api/seed-stories/{scenario}", async (string scenario) =>
{
    var json = await TestProducer.LoadScenarioJsonAsync(scenario);
    return json is null
        ? Results.NotFound(new { error = "unknown scenario" })
        : Results.Content(json, "application/json");
});

app.MapPost("/api/decision/{id}", async (
    string id,
    DecisionRequest body,
    DashboardService dash,
    CancellationToken ct) =>
{
    var result = await dash.DecideAsync(id, body.Decision, body.Reviewer, ct);
    return result.Ok
        ? Results.Ok(new { result.Status, published_to = result.PublishedTopic })
        : Results.BadRequest(new { error = result.Status });
});

app.MapPost("/api/stories/{storyId}/rerun", async (
    string storyId, DashboardService dash, CancellationToken ct) =>
{
    var r = await dash.RerunSkillAsync(storyId, ct);
    return r.Ok
        ? Results.Ok(new { r.Status, cleared_pending = r.ClearedPending })
        : Results.NotFound(new { error = r.Status });
});

app.MapPost("/api/stories/{storyId}/advance-phase", async (
    string storyId, DashboardService dash, CancellationToken ct) =>
{
    var r = await dash.AdvancePhaseAsync(storyId, ct);
    return r.Ok
        ? Results.Ok(new { r.Status, cleared_pending = r.ClearedPending })
        : Results.NotFound(new { error = r.Status });
});

app.MapPost("/api/stories/{storyId}/add-compliance", async (
    string storyId, AddComplianceRequest body, DashboardService dash, CancellationToken ct) =>
{
    var r = await dash.AddComplianceFlagAsync(
        storyId,
        body.Type ?? "EDITORIAL_REVIEW",
        body.Severity ?? "MEDIUM",
        body.Detail ?? "Added via dashboard simulator",
        ct);
    return r.Ok
        ? Results.Ok(new { r.Status, cleared_pending = r.ClearedPending })
        : Results.NotFound(new { error = r.Status });
});

// ── Simulator (local-dev fallback for AP ENPS) ─────────
app.MapGet("/api/simulator/status", (SimulatorService sim) => Results.Ok(sim.GetStatus()));

app.MapGet("/api/simulator/scenarios", (SimulatorService sim) =>
    Results.Ok(sim.Scenarios.Select(s => new
    {
        s.Id,
        s.Name,
        s.Description,
        duration_seconds = s.DurationSeconds,
        step_count = s.Actions.Length,
    })));

app.MapPost("/api/simulator/run/{id}", async (string id, SimulatorService sim) =>
    await sim.RunScenarioAsync(id)
        ? Results.Ok(new { running = id })
        : Results.NotFound(new { error = "scenario_not_found" }));

app.MapPost("/api/simulator/stop", async (SimulatorService sim) =>
{
    await sim.StopScenarioAsync();
    return Results.Ok(new { stopped = true });
});

app.MapPost("/api/simulator/auto/start", async (AutoStartRequest body, SimulatorService sim) =>
{
    await sim.StartAutoStreamAsync(body.IntervalSeconds ?? 20);
    return Results.Ok(sim.GetStatus());
});

app.MapPost("/api/simulator/auto/stop", async (SimulatorService sim) =>
{
    await sim.StopAutoStreamAsync();
    return Results.Ok(sim.GetStatus());
});

app.MapPost("/api/reset", async (DashboardService dash, CancellationToken ct) =>
{
    var result = await dash.ResetBusAsync(ct);
    return Results.Ok(new { result.Ok, topics_reset = result.TopicsReset });
});

app.MapPost("/api/publish/{scenario}", async (string scenario) =>
{
    try
    {
        await TestProducer.RunAsync(scenario);
        return Results.Ok(new { published = scenario });
    }
    catch (Exception ex)
    {
        return Results.Problem(ex.Message);
    }
});

app.Map("/ws", async (HttpContext ctx, DashboardService dash) =>
{
    if (!ctx.WebSockets.IsWebSocketRequest)
    {
        ctx.Response.StatusCode = StatusCodes.Status400BadRequest;
        return;
    }

    using var socket = await ctx.WebSockets.AcceptWebSocketAsync();
    await dash.HandleSocketAsync(socket, ctx.RequestAborted);
});

app.Run();

internal sealed record DecisionRequest(string Decision, string? Reviewer);
internal sealed record AddComplianceRequest(string? Type, string? Severity, string? Detail);
internal sealed record AutoStartRequest(int? IntervalSeconds);
