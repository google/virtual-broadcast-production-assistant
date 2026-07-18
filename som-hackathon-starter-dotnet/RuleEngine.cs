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
///   field_changed              → field, to?, from?
///                                Fires when field's value differs from the PREVIOUS story
///                                version (skills-model field-change condition). Needs the
///                                caller to supply the previous snapshot; never fires on the
///                                first sighting of a story. `field` may contain one `[]`
///                                array wildcard (e.g. assets[].acquisition_state) — items
///                                are matched across versions by asset_id/source_id/flag_id/
///                                id, falling back to index. Optional `to`/`from` restrict
///                                which transitions fire.
///
/// Detail strings come from rule.detail_template with {term} / {value} substitutions
/// where applicable. Returning multiple matches per rule is supported (e.g. term_match
/// fires once per matched term so the editor sees each occurrence separately).
/// </summary>
public sealed class RuleEngine
{
    public IEnumerable<RuleMatch> Evaluate(SkillRule rule, JsonNode story, JsonNode? previous = null) => rule.Type switch
    {
        "term_match"               => EvalTermMatch(rule, story),
        "phase_with_missing_field" => EvalPhaseMissingField(rule, story),
        "field_value_in"           => EvalFieldValueIn(rule, story),
        "field_present"            => EvalFieldPresent(rule, story, expectPresent: true),
        "field_absent"             => EvalFieldPresent(rule, story, expectPresent: false),
        "field_regex"              => EvalFieldRegex(rule, story),
        "field_changed"            => EvalFieldChanged(rule, story, previous),
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

    private static IEnumerable<RuleMatch> EvalFieldChanged(SkillRule rule, JsonNode story, JsonNode? previous)
    {
        var field = GetString(rule.Config, "field");
        if (field is null || previous is null) yield break;

        var to = GetString(rule.Config, "to");
        var from = GetString(rule.Config, "from");

        // Last-wins on duplicate identities — the schema doesn't enforce asset_id uniqueness,
        // and a throw here would silently disable field_changed for the story (the worker's
        // catch would skip the snapshot store).
        var current = new Dictionary<string, JsonNode?>();
        foreach (var (k, n) in GetByPathMulti(story, field)) current[k] = n;
        var prior = new Dictionary<string, JsonNode?>();
        foreach (var (k, n) in GetByPathMulti(previous, field)) prior[k] = n;

        static string? ValueOf(JsonNode? n) => n switch
        {
            null => null,
            JsonValue => n.ToString(),
            _ => n.ToJsonString(),
        };

        foreach (var (key, node) in current)
        {
            // Only items present in BOTH versions can have "changed"; additions are not changes.
            if (!prior.TryGetValue(key, out var priorNode)) continue;

            var newValue = ValueOf(node);
            var oldValue = ValueOf(priorNode);
            if (string.Equals(newValue, oldValue, StringComparison.Ordinal)) continue;

            if (to is not null && !string.Equals(newValue, to, StringComparison.OrdinalIgnoreCase)) continue;
            if (from is not null && !string.Equals(oldValue, from, StringComparison.OrdinalIgnoreCase)) continue;

            yield return new RuleMatch(rule, RenderDetail(rule,
                ("field", field), ("item", key), ("from", oldValue ?? "∅"), ("to", newValue ?? "∅")));
        }
    }

    // ─── Helpers ────────────────────────────────────────────────────────────

    /// <summary>
    /// Like GetByPath, but a segment ending in "[]" expands over an array, yielding one
    /// (key, node) pair per element. Element identity is the child's asset_id / source_id /
    /// flag_id / id when present (stable across republished story versions), else its index.
    /// At most one wildcard is supported — enough for assets[].acquisition_state-style paths.
    /// </summary>
    public static IEnumerable<(string Key, JsonNode? Node)> GetByPathMulti(JsonNode root, string path)
    {
        var parts = path.Split('.');
        var results = new List<(string Key, JsonNode? Node)> { ("", root) };

        foreach (var part in parts)
        {
            var next = new List<(string Key, JsonNode? Node)>();
            var isWildcard = part.EndsWith("[]", StringComparison.Ordinal);
            var name = isWildcard ? part[..^2] : part;

            foreach (var (key, node) in results)
            {
                var child = node is JsonObject obj && obj.ContainsKey(name) ? obj[name] : null;
                if (child is null) continue;

                if (!isWildcard)
                {
                    next.Add((key, child));
                    continue;
                }

                if (child is not JsonArray arr) continue;
                for (var i = 0; i < arr.Count; i++)
                {
                    var item = arr[i];
                    var idNode = item?["asset_id"] ?? item?["source_id"] ?? item?["flag_id"] ?? item?["id"];
                    var identity = idNode is JsonValue ? idNode.ToString() : i.ToString();
                    next.Add((key.Length == 0 ? identity : $"{key}.{identity}", item));
                }
            }

            results = next;
            if (results.Count == 0) yield break;
        }

        foreach (var r in results) yield return r;
    }

    // ─── Helpers (continued) ────────────────────────────────────────────────

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
