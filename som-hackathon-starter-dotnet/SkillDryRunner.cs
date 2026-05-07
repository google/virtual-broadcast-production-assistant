using System.Text.Json.Nodes;

namespace SomSkillWorker;

/// <summary>
/// Layer 2 of skill validation: evaluate a skill against every seed story without
/// publishing anything to Kafka. Tells the vendor "your skill fires N warnings on
/// scenario X" before they commit. Reuses RuleEngine + the same seed JSONs the
/// dashboard scenario buttons publish.
/// </summary>
public sealed class SkillDryRunner
{
    private readonly RuleEngine _engine;

    public SkillDryRunner(RuleEngine engine)
    {
        _engine = engine;
    }

    public async Task<DryRunResult> RunAsync(SkillDefinition skill)
    {
        var perScenario = new List<DryRunScenarioResult>();
        var totalMatches = 0;

        foreach (var scenario in TestProducer.Scenarios)
        {
            var json = await TestProducer.LoadScenarioJsonAsync(scenario);
            if (json is null)
            {
                perScenario.Add(new DryRunScenarioResult(scenario, null, Array.Empty<DryRunMatch>(),
                    "seed file not found"));
                continue;
            }

            var envelope = JsonNode.Parse(json);
            if (envelope is null)
            {
                perScenario.Add(new DryRunScenarioResult(scenario, null, Array.Empty<DryRunMatch>(),
                    "could not parse seed JSON"));
                continue;
            }

            var storyContext = envelope["payload"] ?? envelope;
            var storyId = storyContext["story_id"]?.GetValue<string>() ?? "(unknown)";

            var matches = new List<DryRunMatch>();
            foreach (var rule in skill.Rules ?? Array.Empty<SkillRule>())
            {
                foreach (var match in _engine.Evaluate(rule, storyContext))
                {
                    matches.Add(new DryRunMatch(
                        RuleId: match.Rule.RuleId,
                        RuleName: match.Rule.Name,
                        Severity: match.Rule.DefaultSeverity,
                        AffectedFields: match.Rule.AffectedFields,
                        Detail: match.Detail));
                }
            }

            perScenario.Add(new DryRunScenarioResult(
                Scenario: scenario,
                StoryId: storyId,
                Matches: matches.ToArray(),
                Note: matches.Count == 0 ? "skill SKIPPED" : null));
            totalMatches += matches.Count;
        }

        return new DryRunResult(
            SkillId: skill.Id,
            TotalMatches: totalMatches,
            Scenarios: perScenario.ToArray());
    }
}

public sealed record DryRunResult(
    string SkillId,
    int TotalMatches,
    DryRunScenarioResult[] Scenarios);

public sealed record DryRunScenarioResult(
    string Scenario,
    string? StoryId,
    DryRunMatch[] Matches,
    string? Note);

public sealed record DryRunMatch(
    string RuleId,
    string RuleName,
    string Severity,
    string[] AffectedFields,
    string Detail);
