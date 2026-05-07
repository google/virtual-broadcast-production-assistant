using System.Text.Json.Nodes;

namespace SomSkillWorker;

/// <summary>
/// Layer 1 of skill validation: deterministic schema + config sanity checks.
/// Runs on every POST/PUT /api/skills; returns a list of issues. Empty list = OK.
///
/// This catches typos and structural mistakes before they reach the runtime
/// (where a bad rule would silently emit no warnings or throw at evaluation time).
/// Layer 2 is dry-run (SkillDryRunner). Layer 3 is AI review (ISkillReviewer).
/// </summary>
public static class SkillValidation
{
    private static readonly string[] ValidSeverities = { "hold", "flag", "inform" };
    private static readonly string[] ValidSkillTypes = { "broadcaster", "vendor", "reference" };
    private static readonly string[] ValidDisclosureLevels = { "L1", "L2", "L3" };
    private static readonly string[] ValidMigrationPolicies = { "hot", "cold", "gated" };

    /// <summary>
    /// Required config keys per rule type. Missing any of these is a validation error.
    /// </summary>
    private static readonly Dictionary<string, string[]> RequiredConfigKeys = new()
    {
        ["term_match"]               = new[] { "field", "terms" },
        ["phase_with_missing_field"] = new[] { "phase", "field" },
        ["field_value_in"]           = new[] { "field", "values" },
        ["field_present"]            = new[] { "field" },
        ["field_absent"]              = new[] { "field" },
        ["field_regex"]              = new[] { "field", "pattern" },
    };

    public static ValidationResult Validate(SkillDefinition? skill)
    {
        var errors = new List<ValidationIssue>();
        var warnings = new List<ValidationIssue>();

        if (skill is null)
        {
            errors.Add(new ValidationIssue("error", "skill", "Skill body is null or could not be parsed."));
            return new ValidationResult(errors.ToArray(), warnings.ToArray());
        }

        // ─── Skill identity ────────────────────────────────────────────────
        if (string.IsNullOrWhiteSpace(skill.Id))
            errors.Add(new ValidationIssue("error", "id", "Skill id is required."));
        else if (!skill.Id.Contains('/'))
            warnings.Add(new ValidationIssue("warning", "id",
                $"Skill id '{skill.Id}' should be vendor-prefixed (e.g. 'nbcu/editorial-standards')."));

        if (string.IsNullOrWhiteSpace(skill.Version))
            errors.Add(new ValidationIssue("error", "version", "Skill version is required."));

        if (string.IsNullOrWhiteSpace(skill.Name))
            warnings.Add(new ValidationIssue("warning", "name", "Skill name is empty."));

        if (string.IsNullOrWhiteSpace(skill.Description))
            warnings.Add(new ValidationIssue("warning", "description",
                "Skill description is empty. Editors will see this in the dashboard manifest."));

        if (!ValidSkillTypes.Contains(skill.SkillType))
            warnings.Add(new ValidationIssue("warning", "skill_type",
                $"skill_type '{skill.SkillType}' is unusual. Expected one of: {string.Join(", ", ValidSkillTypes)}."));

        if (!ValidDisclosureLevels.Contains(skill.DisclosureLevel))
            warnings.Add(new ValidationIssue("warning", "disclosure_level",
                $"disclosure_level '{skill.DisclosureLevel}' should be L1, L2, or L3."));

        if (!ValidMigrationPolicies.Contains(skill.MigrationPolicy))
            warnings.Add(new ValidationIssue("warning", "migration_policy",
                $"migration_policy '{skill.MigrationPolicy}' should be hot, cold, or gated."));

        // ─── Rules ──────────────────────────────────────────────────────────
        if (skill.Rules is null || skill.Rules.Length == 0)
        {
            warnings.Add(new ValidationIssue("warning", "rules",
                "Skill has no rules. It will run but emit nothing — every story will produce a SKIPPED run record."));
        }
        else
        {
            var seenRuleIds = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (var i = 0; i < skill.Rules.Length; i++)
            {
                ValidateRule(skill.Rules[i], i, errors, warnings, seenRuleIds);
            }
        }

        return new ValidationResult(errors.ToArray(), warnings.ToArray());
    }

    private static void ValidateRule(
        SkillRule rule, int idx,
        List<ValidationIssue> errors, List<ValidationIssue> warnings,
        HashSet<string> seenRuleIds)
    {
        var path = $"rules[{idx}]";

        if (string.IsNullOrWhiteSpace(rule.RuleId))
            errors.Add(new ValidationIssue("error", $"{path}.rule_id", "rule_id is required."));
        else if (!seenRuleIds.Add(rule.RuleId))
            errors.Add(new ValidationIssue("error", $"{path}.rule_id",
                $"Duplicate rule_id '{rule.RuleId}' within this skill."));

        if (string.IsNullOrWhiteSpace(rule.Name))
            warnings.Add(new ValidationIssue("warning", $"{path}.name", "Rule name is empty."));

        if (string.IsNullOrWhiteSpace(rule.Type))
        {
            errors.Add(new ValidationIssue("error", $"{path}.type", "Rule type is required."));
        }
        else if (!RequiredConfigKeys.ContainsKey(rule.Type))
        {
            errors.Add(new ValidationIssue("error", $"{path}.type",
                $"Unknown rule type '{rule.Type}'. Valid types: {string.Join(", ", RequiredConfigKeys.Keys)}."));
        }
        else
        {
            // Config keys for this type
            foreach (var key in RequiredConfigKeys[rule.Type])
            {
                if (rule.Config is null || !rule.Config.ContainsKey(key))
                {
                    errors.Add(new ValidationIssue("error", $"{path}.config.{key}",
                        $"Rule type '{rule.Type}' requires config.{key}."));
                }
                else if (key == "terms" || key == "values")
                {
                    if (rule.Config[key] is not JsonArray arr || arr.Count == 0)
                        errors.Add(new ValidationIssue("error", $"{path}.config.{key}",
                            $"config.{key} must be a non-empty array."));
                }
            }

            // Type-specific extras
            if (rule.Type == "field_regex" && rule.Config is not null
                && rule.Config["pattern"]?.GetValue<string>() is { } pattern)
            {
                try { _ = new System.Text.RegularExpressions.Regex(pattern); }
                catch (ArgumentException ex)
                {
                    errors.Add(new ValidationIssue("error", $"{path}.config.pattern",
                        $"Invalid regex: {ex.Message}"));
                }
            }
        }

        if (!string.IsNullOrWhiteSpace(rule.DefaultSeverity)
            && !ValidSeverities.Contains(rule.DefaultSeverity))
        {
            errors.Add(new ValidationIssue("error", $"{path}.default_severity",
                $"default_severity '{rule.DefaultSeverity}' must be one of: {string.Join(", ", ValidSeverities)}."));
        }

        if (string.IsNullOrWhiteSpace(rule.OutputMessageType))
            warnings.Add(new ValidationIssue("warning", $"{path}.output_message_type",
                "output_message_type is empty (typical: 'skill.warning.raised')."));

        if (rule.AffectedFields is null || rule.AffectedFields.Length == 0)
            warnings.Add(new ValidationIssue("warning", $"{path}.affected_fields",
                "affected_fields is empty. Editors won't see which story field this rule pertains to."));
    }
}

public sealed record ValidationResult(
    ValidationIssue[] Errors,
    ValidationIssue[] Warnings)
{
    public bool Ok => Errors.Length == 0;
}

public sealed record ValidationIssue(
    string Severity,    // error | warning
    string Path,        // dotted path within the skill, e.g. "rules[0].config.field"
    string Message);
