using System.Diagnostics;
using System.Text.Json.Nodes;
using Confluent.Kafka;
using Microsoft.Extensions.Options;

namespace SomSkillWorker;

/// <summary>
/// SOM Skill Worker — hackathon starter template.
///
/// Flow:
///   1. Consume story.context from som.story.context
///   2. For every skill registered in SkillRegistry, evaluate its Rules against the story
///   3. Publish each match as skill.warning.raised onto som.skills.staging
///   4. Publish one skill.run.completed per skill onto som.skills.runs
///
/// To add or change skills you don't edit this file — drop a JSON file into skills/
/// or use the dashboard's POST /api/skills endpoint. The rule engine handles the
/// evaluation generically.
/// </summary>
public class SkillWorker : BackgroundService
{
    private readonly ILogger<SkillWorker> _logger;
    private readonly KafkaOptions _options;
    private readonly SkillRegistry _registry;
    private readonly RuleEngine _engine;
    private readonly IProducer<string, string> _producer;
    private readonly IConsumer<string, string> _consumer;

    // Last-seen snapshot per story, for field_changed rules. Only touched from the
    // single consume loop, so no locking. Demo-scale: stories are few; no eviction.
    private readonly Dictionary<string, JsonNode> _previousStories = new();

    // One recall-skip log per skill id — a vendor whose skill never runs deserves an
    // Information-level line saying why, not a Debug-level whisper.
    private readonly HashSet<string> _recallSkipLogged = new();

    public SkillWorker(
        ILogger<SkillWorker> logger,
        IOptions<KafkaOptions> options,
        SkillRegistry registry,
        RuleEngine engine)
    {
        _logger = logger;
        _options = options.Value;
        _registry = registry;
        _engine = engine;

        var producerConfig = BuildProducerConfig();
        var consumerConfig = BuildConsumerConfig();

        var pb = new ProducerBuilder<string, string>(producerConfig);
        var cb = new ConsumerBuilder<string, string>(consumerConfig);
        KafkaAuthHelper.AttachOAuth(pb, _options);
        KafkaAuthHelper.AttachOAuth(cb, _options);

        _producer = pb.Build();
        _consumer = cb.Build();
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _consumer.Subscribe(_options.StoryContextTopic);
        _logger.LogInformation("SkillWorker subscribed to {Topic} with {Count} skill(s) loaded",
            _options.StoryContextTopic, _registry.All().Count);

        await Task.Yield();

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var result = _consumer.Consume(TimeSpan.FromSeconds(1));
                if (result is null) continue;

                var envelope = JsonNode.Parse(result.Message.Value);
                if (envelope is null) continue;

                // SOM v0.2 envelope wraps the story under "payload"; tolerate flat payloads too.
                var storyContext = envelope["payload"] ?? envelope;
                var sid = storyContext["story_id"] is JsonValue idv && idv.TryGetValue<string>(out string? s) && !string.IsNullOrEmpty(s) ? s : null;
                var hasStoryId = sid is not null;
                var storyId = sid ?? "unknown";
                // Echo the inbound correlation_id onto our outputs so all messages about one
                // story lifecycle stay correlated (envelope lock, decision #18).
                var correlationId = envelope["correlation_id"]?.GetValue<string>();
                _logger.LogInformation("Received story {StoryId}", storyId);

                // Previous version of this story, for field_changed rules (skills-model
                // field-change condition). Null on first sighting — change rules stay quiet.
                // Id-less messages share no baseline: never diff two unrelated payloads.
                JsonNode? previous = null;
                if (hasStoryId) _previousStories.TryGetValue(storyId, out previous);
                if (previous is null && _registry.All().Any(s => s.Rules.Any(r => r.Type == "field_changed")))
                {
                    _logger.LogInformation(
                        "First sighting of {StoryId} this session — field_changed rules stay quiet until the next version", storyId);
                }

                // Recall = deterministic advert matching (skills model): a skill whose
                // advert declares operates_on runs only when it covers this message type.
                // No advert → legacy behaviour, assume story.context.
                foreach (var skill in _registry.All())
                {
                    var operatesOn = skill.Advert?.OperatesOn;
                    if (operatesOn is { Length: > 0 } && !operatesOn.Contains("story.context"))
                    {
                        if (_recallSkipLogged.Add(skill.Id))
                            _logger.LogInformation(
                                "Recall: skill {SkillId} advert operates_on=[{OperatesOn}] does not cover story.context — it will never run on this topic",
                                skill.Id, string.Join(",", operatesOn));
                        continue;
                    }
                    await EvaluateSkillAsync(skill, storyContext, storyId, result.Message.Key, correlationId, previous, stoppingToken);
                }

                if (hasStoryId) _previousStories[storyId] = storyContext.DeepClone();
            }
            catch (ConsumeException ex)
            {
                _logger.LogError(ex, "Consume error");
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Skill execution error on story");
            }
        }

        _consumer.Close();
    }

    private async Task EvaluateSkillAsync(
        SkillDefinition skill,
        JsonNode storyContext,
        string storyId,
        string? messageKey,
        string? correlationId,
        JsonNode? previous,
        CancellationToken ct)
    {
        var sw = Stopwatch.StartNew();
        var warningIds = new List<string>();

        foreach (var rule in skill.Rules)
        {
            foreach (var match in _engine.Evaluate(rule, storyContext, previous))
            {
                var warningPayload = BuildWarning(skill, match, storyId);
                warningIds.Add(warningPayload["warning_id"]!.GetValue<string>());
                var warningMsg = BuildEnvelope("skill.warning.raised", _options.SkillStagingTopic, correlationId, warningPayload);
                await PublishAsync(_options.SkillStagingTopic, storyId, warningMsg.ToJsonString(), ct);
            }
        }

        sw.Stop();

        var runPayload = BuildRunRecord(
            skill,
            Guid.NewGuid().ToString(),
            storyId,
            messageKey,
            warningIds,
            sw.ElapsedMilliseconds);

        var runMsg = BuildEnvelope("skill.run.completed", _options.SkillRunsTopic, correlationId, runPayload);
        await PublishAsync(_options.SkillRunsTopic, storyId, runMsg.ToJsonString(), ct);

        _logger.LogInformation("Skill {SkillId}@{Version} on {StoryId}: {Count} warnings in {Ms}ms",
            skill.Id, skill.Version, storyId, warningIds.Count, sw.ElapsedMilliseconds);
    }

    // ═══════════════════════════════════════════════════════════
    // MESSAGE BUILDERS — conformant SOM message shapes
    // ═══════════════════════════════════════════════════════════

    /// <summary>Build a skill.warning.raised message (hackathon brief §8.3).</summary>
    private static JsonNode BuildWarning(SkillDefinition skill, RuleMatch match, string storyId)
    {
        var rule = match.Rule;
        // Twelve-field SkillWarning payload (decision #21). No payload-level timestamp or
        // message_type — those live on the envelope (decision #18, see BuildEnvelope).
        // scope is the firing level, as {level}:{id} (see docs/SOM-v0.3.1-scope-reconciliation.md):
        //   story:{id}  — system-level skill on story-wide context (what we emit here; RuleEngine
        //                 matches whole-story paths and RuleMatch carries no asset_id yet)
        //   asset:{id}  — system-level skill on one asset; awaits the firing-rule upgrade that
        //                 threads the matched asset_id into RuleMatch
        //   link:{id}   — destination-specific skill, fired at a link's Compliance Gate
        // Never an instance_ref (#3/#21).
        var warning = new JsonObject
        {
            ["warning_id"] = Guid.NewGuid().ToString(),
            ["skill_id"] = skill.Id,
            ["skill_version"] = skill.Version,
            ["story_id"] = storyId,
            ["scope"] = $"story:{storyId}",
            ["severity"] = rule.DefaultSeverity,
            ["rule_id"] = rule.RuleId,
            ["non_overridable"] = false,
            ["affected_fields"] = new JsonArray(
                rule.AffectedFields.Select(f => (JsonNode?)JsonValue.Create(f)).ToArray()),
            ["detail"] = match.Detail,
            ["blocks"] = new JsonArray(),
            ["skill_warning_ref"] = $"swr-{storyId}-{Guid.NewGuid().ToString("N")[..8]}",
        };

        var extensions = BuildExtensions(rule);
        if (extensions is not null) warning["extensions"] = extensions;

        return warning;
    }

    /// <summary>
    /// Build the per-warning extensions block (D-002b). Emits flat-key
    /// extensions.com.nbcu.citations and extensions.com.nbcu.rationale when
    /// the rule definition supplies them. Returns null if neither is set.
    /// </summary>
    private static JsonObject? BuildExtensions(SkillRule rule)
    {
        var hasCitations = rule.Citations is { Length: > 0 };
        var hasRationale = !string.IsNullOrWhiteSpace(rule.Rationale);
        if (!hasCitations && !hasRationale) return null;

        var ext = new JsonObject();
        if (hasCitations)
        {
            var arr = new JsonArray();
            foreach (var c in rule.Citations!)
                arr.Add(new JsonObject { ["source_id"] = c.SourceId, ["quote"] = c.Quote });
            ext["com.nbcu.citations"] = arr;
        }
        if (hasRationale) ext["com.nbcu.rationale"] = rule.Rationale!;
        return ext;
    }

    /// <summary>Build skill.run.completed audit record (Amendment 1, hackathon brief §8.1).</summary>
    private static JsonNode BuildRunRecord(
        SkillDefinition skill,
        string runId,
        string storyId,
        string? messageKey,
        List<string> warningIds,
        long latencyMs)
    {
        // Payload only — message_type and timestamp live on the envelope (BuildEnvelope).
        return new JsonObject
        {
            ["run_id"] = runId,
            ["skill_id"] = skill.Id,
            ["skill_version"] = skill.Version,
            ["story_id"] = storyId,
            ["triggered_by"] = new JsonObject
            {
                ["event_type"] = "story.context",
                ["message_id"] = messageKey ?? "",
            },
            ["inputs"] = new JsonObject
            {
                ["reads"] = new JsonArray(skill.Reads.Select(r => (JsonNode?)JsonValue.Create(r)).ToArray()),
                ["input_digest"] = "",                             // sha256 of consumed fields (TODO)
            },
            ["outputs"] = new JsonObject
            {
                ["suggestion_ids"] = new JsonArray(),
                ["warning_ids"] = new JsonArray(
                    warningIds.Select(id => (JsonNode?)JsonValue.Create(id)).ToArray()),
                ["enrichment_ids"] = new JsonArray(),
            },
            ["latency_ms"] = latencyMs,
            ["outcome"] = warningIds.Count > 0 ? "COMPLETED" : "SKIPPED",
            ["human_review_required"] = warningIds.Count > 0,
        };
    }

    /// <summary>
    /// Wrap a typed payload in a SOM v0.3.1 envelope. Timestamp lives here, not in the
    /// payload (decision #18); correlation_id is echoed from the inbound story.context so
    /// every message about one story lifecycle stays correlated.
    /// </summary>
    private static JsonNode BuildEnvelope(string messageType, string topic, string? correlationId, JsonNode payload)
    {
        return new JsonObject
        {
            ["som_version"] = "0.2.0",
            ["message_id"] = Guid.NewGuid().ToString(),
            ["correlation_id"] = correlationId ?? Guid.NewGuid().ToString(),
            ["message_type"] = messageType,
            ["timestamp"] = DateTimeOffset.UtcNow.ToString("o"),
            ["originating_system"] = new JsonObject
            {
                ["system_id"] = "nbcu-skill-executor",
                ["system_type"] = "skill_worker",
                ["system_name"] = "NBCU Skill Executor",
            },
            ["topic"] = topic,
            ["payload"] = payload,
        };
    }

    // ═══════════════════════════════════════════════════════════
    // KAFKA PLUMBING
    // ═══════════════════════════════════════════════════════════

    private async Task PublishAsync(string topic, string key, string value, CancellationToken ct)
    {
        var message = new Message<string, string> { Key = key, Value = value };
        var publishResult = await _producer.ProduceAsync(topic, message, ct);
        _logger.LogDebug("Published to {Topic} partition {Partition} offset {Offset}",
            topic, publishResult.Partition.Value, publishResult.Offset.Value);
    }

    private ProducerConfig BuildProducerConfig()
    {
        var config = new ProducerConfig
        {
            BootstrapServers = _options.BootstrapServers,
            Acks = Acks.All,
            EnableIdempotence = true,
        };
        ApplyAuth(config);
        return config;
    }

    private ConsumerConfig BuildConsumerConfig()
    {
        var config = new ConsumerConfig
        {
            BootstrapServers = _options.BootstrapServers,
            GroupId = _options.GroupId,
            AutoOffsetReset = AutoOffsetReset.Latest,
            EnableAutoCommit = true,
            TopicMetadataRefreshIntervalMs = 3000,
        };
        ApplyAuth(config);
        return config;
    }

    private void ApplyAuth(ClientConfig config)
    {
        KafkaAuthHelper.Configure(config, _options);
    }

    public override void Dispose()
    {
        _producer.Dispose();
        _consumer.Dispose();
        base.Dispose();
    }
}
