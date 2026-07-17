using System.Collections.Concurrent;
using Microsoft.Extensions.Options;

namespace SomSkillWorker;

/// <summary>
/// Local-dev fallback for AP ENPS. AP is the canonical native SOM publisher; this
/// simulator stands in until AP is wired up, and stays useful afterwards as a
/// self-contained test rig vendors can run against.
///
/// Two operating modes:
///
///   1. SCRIPTED SCENARIOS — multi-step storylines that demonstrate the full SOM
///      lifecycle (publish → editor adds compliance → advance phase → ON_AIR).
///      Run via POST /api/simulator/run/{id}. Each step uses DashboardService
///      mutators (AddComplianceFlagAsync, AdvancePhaseAsync) so the bus traffic
///      mirrors what a real NRCS would emit.
///
///   2. AUTO-STREAM — every N seconds, pick a random seed story and publish it.
///      Useful for keeping the dashboard alive during demos / vendor integration
///      testing. Toggle via POST /api/simulator/auto/start|stop.
///
/// Only one scenario runs at a time; starting a new one cancels the previous.
/// </summary>
public sealed class SimulatorService : BackgroundService
{
    private readonly ILogger<SimulatorService> _logger;
    private readonly DashboardService _dashboard;
    private readonly MockMamService _mockMam;
    private readonly KafkaOptions _kafkaOptions;
    private readonly Random _rng = new();

    private CancellationTokenSource? _scenarioCts;
    private string? _runningScenarioId;
    private DateTimeOffset? _runningStartedAt;

    private bool _autoEnabled;
    private int _autoIntervalSeconds = 20;

    public SimulatorService(ILogger<SimulatorService> logger, DashboardService dashboard, MockMamService mockMam, IOptions<KafkaOptions> kafkaOptions)
    {
        _logger = logger;
        _dashboard = dashboard;
        _mockMam = mockMam;
        _kafkaOptions = kafkaOptions.Value;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Auto-stream loop. Wakes every second, publishes when due.
        var lastAutoTick = DateTimeOffset.MinValue;
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                if (_autoEnabled)
                {
                    var dueAt = lastAutoTick + TimeSpan.FromSeconds(_autoIntervalSeconds);
                    if (DateTimeOffset.UtcNow >= dueAt)
                    {
                        await PublishRandomScenarioAsync(stoppingToken);
                        lastAutoTick = DateTimeOffset.UtcNow;
                    }
                }
                else
                {
                    lastAutoTick = DateTimeOffset.UtcNow;
                }

                await Task.Delay(1000, stoppingToken);
            }
            catch (OperationCanceledException) { break; }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Simulator auto-stream tick failed");
                await Task.Delay(2000, stoppingToken);
            }
        }
    }

    private async Task PublishRandomScenarioAsync(CancellationToken ct)
    {
        var scenarios = TestProducer.Scenarios;
        if (scenarios.Count == 0) return;
        var pick = scenarios[_rng.Next(scenarios.Count)];
        _logger.LogInformation("Auto-stream → publishing seed scenario {Scenario}", pick);
        await TestProducer.RunAsync(_kafkaOptions, pick);
    }

    // ─── Scripted scenarios ─────────────────────────────────────────────────

    public IReadOnlyCollection<SimulationScenario> Scenarios => SimScenarios.All.Values;

    public SimulationScenario? GetScenario(string id) =>
        SimScenarios.All.TryGetValue(id, out var s) ? s : null;

    public SimulatorStatus GetStatus() => new(
        AutoEnabled: _autoEnabled,
        AutoIntervalSeconds: _autoIntervalSeconds,
        RunningScenarioId: _runningScenarioId,
        RunningStartedAt: _runningStartedAt);

    public Task StartAutoStreamAsync(int intervalSeconds)
    {
        _autoIntervalSeconds = Math.Max(3, intervalSeconds);
        _autoEnabled = true;
        _logger.LogInformation("Auto-stream ON · interval={Seconds}s", _autoIntervalSeconds);
        return Task.CompletedTask;
    }

    public Task StopAutoStreamAsync()
    {
        _autoEnabled = false;
        _logger.LogInformation("Auto-stream OFF");
        return Task.CompletedTask;
    }

    public async Task<bool> RunScenarioAsync(string id)
    {
        var scenario = GetScenario(id);
        if (scenario is null) return false;

        // Cancel any previous run, then start fresh.
        _scenarioCts?.Cancel();
        _scenarioCts = new CancellationTokenSource();
        _runningScenarioId = scenario.Id;
        _runningStartedAt = DateTimeOffset.UtcNow;

        _ = Task.Run(() => RunScenarioLoopAsync(scenario, _scenarioCts.Token));
        return true;
    }

    public Task StopScenarioAsync()
    {
        _scenarioCts?.Cancel();
        _runningScenarioId = null;
        _runningStartedAt = null;
        return Task.CompletedTask;
    }

    private async Task RunScenarioLoopAsync(SimulationScenario scenario, CancellationToken ct)
    {
        _logger.LogInformation("▶ Running scenario {Id} ({StepCount} steps)", scenario.Id, scenario.Actions.Length);
        var startedAt = DateTimeOffset.UtcNow;
        try
        {
            foreach (var action in scenario.Actions)
            {
                var dueAt = startedAt.AddSeconds(action.DelaySeconds);
                var wait = dueAt - DateTimeOffset.UtcNow;
                if (wait > TimeSpan.Zero) await Task.Delay(wait, ct);
                if (ct.IsCancellationRequested) break;
                await ExecuteActionAsync(action, ct);
            }
            _logger.LogInformation("✓ Scenario {Id} completed", scenario.Id);
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Scenario {Id} cancelled", scenario.Id);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Scenario {Id} failed", scenario.Id);
        }
        finally
        {
            if (_runningScenarioId == scenario.Id)
            {
                _runningScenarioId = null;
                _runningStartedAt = null;
            }
        }
    }

    private async Task ExecuteActionAsync(SimAction action, CancellationToken ct)
    {
        _logger.LogInformation("  → t+{T}s: {Type} {Detail}", action.DelaySeconds, action.Type,
            action.Scenario ?? action.StoryId ?? "");
        switch (action.Type)
        {
            case "publish":
                if (action.Scenario is not null) await TestProducer.RunAsync(_kafkaOptions, action.Scenario);
                break;
            case "advance-phase":
                if (action.StoryId is not null) await _dashboard.AdvancePhaseAsync(action.StoryId, ct);
                break;
            case "add-compliance":
                if (action.StoryId is not null)
                    await _dashboard.AddComplianceFlagAsync(
                        action.StoryId,
                        action.FlagType ?? "EDITORIAL_REVIEW",
                        action.Severity ?? "MEDIUM",
                        action.Detail ?? "Added by simulator",
                        ct);
                break;
            case "rerun":
                if (action.StoryId is not null) await _dashboard.RerunSkillAsync(action.StoryId, ct);
                break;
            case "media-available":
                // Mock MAM emits som.delivery.media_available (TAMS stand-in — see MockMamService).
                if (action.SourceId is null)
                {
                    _logger.LogWarning("Simulator 'media-available' action missing SourceId — skipped");
                    break;
                }
                var emit = await _mockMam.EmitAsync(action.SourceId, action.TimeRange, ct: ct);
                if (!emit.Ok)
                    _logger.LogError(
                        "Simulator 'media-available' did NOT emit for source {SourceId}: {Status} — {Error}",
                        action.SourceId, emit.Status, emit.Error);
                break;
            default:
                _logger.LogWarning("Unknown simulator action type: {Type}", action.Type);
                break;
        }
    }
}

// ─── Records ────────────────────────────────────────────────────────────────

public sealed record SimAction(
    int DelaySeconds,
    string Type,
    string? Scenario = null,
    string? StoryId = null,
    string? FlagType = null,
    string? Severity = null,
    string? Detail = null,
    string? SourceId = null,
    string? TimeRange = null);

public sealed record SimulationScenario(
    string Id,
    string Name,
    string Description,
    int DurationSeconds,
    SimAction[] Actions);

public sealed record SimulatorStatus(
    bool AutoEnabled,
    int AutoIntervalSeconds,
    string? RunningScenarioId,
    DateTimeOffset? RunningStartedAt);

// ─── Built-in scenarios ─────────────────────────────────────────────────────

internal static class SimScenarios
{
    // story_ids match the seed files under seed-stories/. Hardcoded so scenarios
    // can target the story they just published.
    private const string ManhattanExplosion  = "manhattan-explosion-2026-0506";
    private const string LapdCounterfeit     = "lapd-counterfeit-2026-0510";
    private const string SentencingCourt     = "sentencing-2026-0401";
    private const string TransitExpansion    = "transit-expansion-2026-0512";
    private const string ElectionVa          = "election-special-2026-0615";

    public static readonly Dictionary<string, SimulationScenario> All = new(StringComparer.OrdinalIgnoreCase)
    {
        ["breaking-news-cycle"] = new(
            Id: "breaking-news-cycle",
            Name: "Breaking news cycle",
            Description: "BREAKING story arrives without compliance flags. Standards desk attaches one. Story progresses through READY_TO_AIR → ON_AIR → PUBLISHED over ~35 seconds. Demonstrates the full editorial loop closing.",
            DurationSeconds: 35,
            Actions: new[]
            {
                new SimAction(0,  "publish",        Scenario: "breaking-no-compliance"),
                new SimAction(8,  "add-compliance", StoryId: ManhattanExplosion,
                              FlagType: "EDITORIAL_REVIEW", Severity: "HIGH",
                              Detail: "Standards desk verified facts on scene"),
                new SimAction(14, "advance-phase",  StoryId: ManhattanExplosion),
                new SimAction(22, "advance-phase",  StoryId: ManhattanExplosion),
                new SimAction(30, "advance-phase",  StoryId: ManhattanExplosion),
            }),

        ["multi-vendor-stream"] = new(
            Id: "multi-vendor-stream",
            Name: "Multi-vendor stream",
            Description: "Publishes all 5 seed stories in quick succession over ~12 seconds. Useful for testing vendor skills against a realistic newsroom load — concurrent stories at different lifecycle stages.",
            DurationSeconds: 12,
            Actions: new[]
            {
                new SimAction(0,  "publish", Scenario: "informal"),
                new SimAction(3,  "publish", Scenario: "breaking"),
                new SimAction(6,  "publish", Scenario: "election"),
                new SimAction(9,  "publish", Scenario: "clean"),
                new SimAction(12, "publish", Scenario: "breaking-no-compliance"),
            }),

        ["election-night"] = new(
            Id: "election-night",
            Name: "Election night",
            Description: "Election story arrives in DEVELOPING and slowly progresses through phases over ~50 seconds. A late compliance flag (VOTING_RIGHTS) gets attached as projections firm up.",
            DurationSeconds: 50,
            Actions: new[]
            {
                new SimAction(0,  "publish",        Scenario: "election"),
                new SimAction(15, "rerun",          StoryId: ElectionVa),
                new SimAction(25, "add-compliance", StoryId: ElectionVa,
                              FlagType: "VOTING_RIGHTS", Severity: "MEDIUM",
                              Detail: "Election Decision Desk projection conditions"),
                new SimAction(35, "advance-phase",  StoryId: ElectionVa),
                new SimAction(45, "advance-phase",  StoryId: ElectionVa),
            }),

        ["media-arrival"] = new(
            Id: "media-arrival",
            Name: "Media arrival (mock MAM / TAMS junction)",
            Description: "D1·B5 proof without a MAM participant: breaking story publishes, then the mock MAM emits delivery.media_available three times with a GROWING TAMS timerange — authentic TAMS behaviour, a recording is addressable while still being captured. Final emit is the full range. Pair with a story.context update flipping acquisition_state CAPTURING → CAPTURED once seeds carry media_refs[] (WS2).",
            DurationSeconds: 30,
            Actions: new[]
            {
                new SimAction(0,  "publish",         Scenario: "breaking"),
                new SimAction(6,  "media-available", SourceId: "landfall-feed-01", TimeRange: "[0:0_30:0)"),
                new SimAction(16, "media-available", SourceId: "landfall-feed-01", TimeRange: "[0:0_75:0)"),
                new SimAction(26, "media-available", SourceId: "landfall-feed-01", TimeRange: "[0:0_1260:0)"),
            }),

        ["compliance-review"] = new(
            Id: "compliance-review",
            Name: "Standards-desk review",
            Description: "BREAKING courthouse story (with existing compliance) arrives. Simulator adds an extra LEGAL_HOLD flag mid-flight. Useful for verifying a skill that watches compliance[] mutations.",
            DurationSeconds: 18,
            Actions: new[]
            {
                new SimAction(0,  "publish",        Scenario: "breaking"),
                new SimAction(6,  "add-compliance", StoryId: SentencingCourt,
                              FlagType: "LEGAL_HOLD", Severity: "CRITICAL",
                              Detail: "Defense filed gag motion — hold on identifying jurors"),
                new SimAction(12, "advance-phase",  StoryId: SentencingCourt),
                new SimAction(18, "advance-phase",  StoryId: SentencingCourt),
            }),
    };
}
