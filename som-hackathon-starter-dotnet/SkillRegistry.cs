using System.Collections.Concurrent;
using System.Text.Json;

namespace SomSkillWorker;

/// <summary>
/// In-memory registry of SkillDefinitions, backed by JSON files in skills/.
/// Hackathon teams add a skill by dropping a new .json file (or via the dashboard's
/// POST /api/skills endpoint, which writes to disk).
/// </summary>
public sealed class SkillRegistry
{
    private readonly ConcurrentDictionary<string, SkillDefinition> _skills = new();
    private readonly string _skillsDir;
    private readonly ILogger<SkillRegistry> _logger;

    public SkillRegistry(ILogger<SkillRegistry> logger)
    {
        _logger = logger;
        _skillsDir = ResolveSkillsDirectory();
        LoadAll();
    }

    public IReadOnlyCollection<SkillDefinition> All() => _skills.Values.ToArray();

    public SkillDefinition? Get(string id) =>
        _skills.TryGetValue(id, out var skill) ? skill : null;

    public bool Add(SkillDefinition skill)
    {
        if (_skills.ContainsKey(skill.Id)) return false;
        _skills[skill.Id] = skill;
        Persist(skill);
        _logger.LogInformation("Added skill {Id}@{Version}", skill.Id, skill.Version);
        return true;
    }

    public bool Update(string id, SkillDefinition skill)
    {
        if (!_skills.ContainsKey(id)) return false;
        // If the caller renamed the skill, drop the old file too.
        if (!string.Equals(id, skill.Id, StringComparison.Ordinal))
            Delete(id);
        _skills[skill.Id] = skill;
        Persist(skill);
        _logger.LogInformation("Updated skill {Id}", skill.Id);
        return true;
    }

    public bool Delete(string id)
    {
        if (!_skills.TryRemove(id, out _)) return false;
        var path = PathFor(id);
        if (File.Exists(path)) File.Delete(path);
        _logger.LogInformation("Deleted skill {Id}", id);
        return true;
    }

    public string SkillsDirectory => _skillsDir;

    // ─── Persistence ────────────────────────────────────────────────────────

    private void LoadAll()
    {
        if (!Directory.Exists(_skillsDir))
        {
            _logger.LogWarning("Skills directory not found at {Dir} — starting with empty registry", _skillsDir);
            return;
        }

        foreach (var path in Directory.EnumerateFiles(_skillsDir, "*.json"))
        {
            try
            {
                var json = File.ReadAllText(path);
                var skill = JsonSerializer.Deserialize<SkillDefinition>(json, SkillDefinitionJson.Options);
                if (skill is null) continue;
                _skills[skill.Id] = skill;
                _logger.LogInformation("Loaded skill {Id}@{Version} from {Path}", skill.Id, skill.Version, Path.GetFileName(path));
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to load skill from {Path}", path);
            }
        }
    }

    private void Persist(SkillDefinition skill)
    {
        Directory.CreateDirectory(_skillsDir);
        var path = PathFor(skill.Id);
        var json = JsonSerializer.Serialize(skill, SkillDefinitionJson.Options);
        File.WriteAllText(path, json + Environment.NewLine);
    }

    private string PathFor(string skillId) =>
        Path.Combine(_skillsDir, FileNameFor(skillId));

    /// <summary>Convert "nbcu/editorial-standards" → "nbcu-editorial-standards.json".</summary>
    private static string FileNameFor(string skillId) =>
        skillId.Replace('/', '-').Replace('\\', '-') + ".json";

    private static string ResolveSkillsDirectory()
    {
        // 1. Prefer the source-tree skills/ directory so edits via the dashboard land
        //    in the repo (and survive a rebuild). dotnet run sets CurrentDirectory to
        //    the project root by default.
        var cwdCandidate = Path.Combine(Directory.GetCurrentDirectory(), "skills");
        if (Directory.Exists(cwdCandidate)) return cwdCandidate;

        // 2. Walk up from the binary location, but skip any candidate inside a /bin/
        //    directory — that's the build output copy. The next match up the chain
        //    is the source folder.
        var dir = AppContext.BaseDirectory;
        for (var i = 0; i < 8; i++)
        {
            var candidate = Path.Combine(dir, "skills");
            if (Directory.Exists(candidate) && !candidate.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}"))
                return candidate;
            dir = Path.GetDirectoryName(dir) ?? "";
            if (string.IsNullOrEmpty(dir)) break;
        }

        // 3. Last resort: cwd (will be created on first persist).
        return cwdCandidate;
    }
}
