using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.Json.Serialization;

namespace SomSkillWorker;

/// <summary>
/// One skill loaded from skills/{slug}.json. Wholly data-driven — the rule engine
/// interprets the Rules array against incoming story.context messages.
/// </summary>
public sealed record SkillDefinition(
    [property: JsonPropertyName("id")] string Id,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("description")] string Description,
    [property: JsonPropertyName("skill_type")] string SkillType,
    [property: JsonPropertyName("disclosure_level")] string DisclosureLevel,
    [property: JsonPropertyName("migration_policy")] string MigrationPolicy,
    [property: JsonPropertyName("reads")] string[] Reads,
    [property: JsonPropertyName("produces")] string[] Produces,
    [property: JsonPropertyName("rules")] SkillRule[] Rules);

/// <summary>
/// One detection rule inside a skill. The Type discriminator selects which
/// RuleEngine evaluator runs; Config is the type-specific payload.
/// </summary>
public sealed record SkillRule(
    [property: JsonPropertyName("rule_id")] string RuleId,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("description")] string Description,
    [property: JsonPropertyName("type")] string Type,
    [property: JsonPropertyName("config")] JsonObject Config,
    [property: JsonPropertyName("default_severity")] string DefaultSeverity,
    [property: JsonPropertyName("output_message_type")] string OutputMessageType,
    [property: JsonPropertyName("affected_fields")] string[] AffectedFields,
    [property: JsonPropertyName("detail_template")] string? DetailTemplate);

public static class SkillDefinitionJson
{
    public static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
}
