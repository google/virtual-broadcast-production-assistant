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
                var storyId = storyContext["story_id"]?.GetValue<string>() ?? "unknown";
                _logger.LogInformation("Received story {StoryId}", storyId);

                // Run every registered skill against this story.
                foreach (var skill in _registry.All())
                {
                    await EvaluateSkillAsync(skill, storyContext, storyId, result.Message.Key, stoppingToken);
                }
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
        CancellationToken ct)
    {
        var sw = Stopwatch.StartNew();
        var warningIds = new List<string>();

        foreach (var rule in skill.Rules)
        {
            foreach (var match in _engine.Evaluate(rule, storyContext))
            {
                var warning = BuildWarning(skill, match, storyId);
                warningIds.Add(warning["warning_id"]!.GetValue<string>());
                await PublishAsync(_options.SkillStagingTopic, storyId, warning.ToJsonString(), ct);
            }
        }

        sw.Stop();

        var runRecord = BuildRunRecord(
            skill,
            Guid.NewGuid().ToString(),
            storyId,
            messageKey,
            warningIds,
            sw.ElapsedMilliseconds);

        await PublishAsync(_options.SkillRunsTopic, storyId, runRecord.ToJsonString(), ct);

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
        var warning = new JsonObject
        {
            ["message_type"] = rule.OutputMessageType,
            ["warning_id"] = Guid.NewGuid().ToString(),
            ["skill_id"] = skill.Id,
            ["skill_version"] = skill.Version,
            ["story_id"] = storyId,
            ["severity"] = rule.DefaultSeverity,
            ["rule_id"] = rule.RuleId,
            ["non_overridable"] = false,
            ["affected_fields"] = new JsonArray(
                rule.AffectedFields.Select(f => (JsonNode?)JsonValue.Create(f)).ToArray()),
            ["detail"] = match.Detail,
            ["blocks"] = new JsonArray(),
            ["timestamp"] = DateTimeOffset.UtcNow.ToString("o"),
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
        return new JsonObject
        {
            ["message_type"] = "skill.run.completed",
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
            ["timestamp"] = DateTimeOffset.UtcNow.ToString("o"),
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
