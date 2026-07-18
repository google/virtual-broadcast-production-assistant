using System.Text.Json.Nodes;
using Confluent.Kafka;
using Microsoft.Extensions.Options;

namespace SomSkillWorker;

/// <summary>
/// Reference consumer for som.delivery.media_available — the WS1 role no external
/// participant fills in the PoC, so the starter carries it itself and vendors can watch
/// the whole loop in one process.
///
/// Spec behaviour (SOM↔TAMS join, 30 Jun): a media arrival joins to an EXISTING story by
/// resolving asset_id → Asset → Story; it never creates one. So:
///
///   1. Known asset + capture-complete signal (extensions["com.ibc-poc.capture_complete"])
///      → republish story.context flipping the asset's acquisition_state CAPTURING → CAPTURED
///        and bounding its media_refs[].time_range to the final range. Skills re-run on the
///        new version — that's the end-to-end loop.
///   2. Known asset, rolling arrival → availability noted; no story change (rolling
///        availability is the normal live-feed case; consumers take what exists so far).
///   3. Unknown asset → the safe-state non-action from the skills model: record a WITHHELD
///        audit on som.system.audit ("no story references this asset; declined to act").
///   4. Unknown asset + Coordinator:OrphanPreview=true → v0.3.2 PREVIEW: author a minimal
///        story_type ORPHAN story wrapping the media instead of withholding. Clearly labeled;
///        ORPHAN is NOT in the locked v0.3.1 schema — this exists to demo the v0.3.2 direction.
/// </summary>
public sealed class MediaCoordinatorService : BackgroundService
{
    private const string SystemId = "media-coordinator";
    private const string CaptureCompleteExt = "com.ibc-poc.capture_complete";

    private readonly ILogger<MediaCoordinatorService> _logger;
    private readonly DashboardService _dashboard;
    private readonly KafkaOptions _kafka;
    private readonly bool _orphanPreview;
    private IProducer<string, string>? _producer;

    public MediaCoordinatorService(
        ILogger<MediaCoordinatorService> logger,
        DashboardService dashboard,
        IOptions<KafkaOptions> kafkaOptions,
        IConfiguration configuration)
    {
        _logger = logger;
        _dashboard = dashboard;
        _kafka = kafkaOptions.Value;
        _orphanPreview = configuration.GetValue<bool>("Coordinator:OrphanPreview");
    }

    private IProducer<string, string> Producer
    {
        get
        {
            if (_producer is not null) return _producer;
            // Bounded message timeout: with the librdkafka default (5 min) a broker outage
            // reads as a silent hang mid-demo instead of a prompt error.
            var config = new ProducerConfig { BootstrapServers = _kafka.BootstrapServers, MessageTimeoutMs = 10000 };
            KafkaAuthHelper.Configure(config, _kafka);
            var pb = new ProducerBuilder<string, string>(config);
            KafkaAuthHelper.AttachOAuth(pb, _kafka);
            _producer = pb.Build();
            return _producer;
        }
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Let the broker + other services come up first.
        await Task.Delay(TimeSpan.FromSeconds(3), stoppingToken);

        var config = new ConsumerConfig
        {
            BootstrapServers = _kafka.BootstrapServers,
            GroupId = _kafka.CoordinatorGroupId,
            // Latest, not Earliest: this consumer MUTATES stories. Replaying historic
            // arrivals on every restart would re-flip acquisition_state and re-publish
            // story versions nobody asked for. React to new arrivals only.
            AutoOffsetReset = AutoOffsetReset.Latest,
            EnableAutoCommit = true,
        };
        KafkaAuthHelper.Configure(config, _kafka);
        var cb = new ConsumerBuilder<string, string>(config);
        KafkaAuthHelper.AttachOAuth(cb, _kafka);

        using var consumer = cb.Build();
        consumer.Subscribe(_kafka.DeliveryTopic);
        _logger.LogInformation(
            "MediaCoordinator: consuming {Topic} (orphan preview: {Orphan})",
            _kafka.DeliveryTopic, _orphanPreview ? "ON — v0.3.2 behaviour" : "off");

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var result = consumer.Consume(TimeSpan.FromSeconds(1));
                if (result is null) continue;
                try
                {
                    await HandleArrivalAsync(result.Message.Value, stoppingToken);
                }
                catch (OperationCanceledException) { throw; }
                catch (Exception ex)
                {
                    // Identify WHICH arrival died — with three emits in flight a bare
                    // stack trace is undebuggable. The arrival is dropped (at-most-once);
                    // recovery is re-emitting it.
                    var value = result.Message.Value ?? "";
                    _logger.LogError(ex, "MediaCoordinator failed handling an arrival (dropped): {Excerpt}",
                        value.Length > 200 ? value[..200] : value);
                }
            }
            catch (OperationCanceledException) { break; }
            catch (ConsumeException ex)
            {
                _logger.LogError(ex, "MediaCoordinator consume error");
                await Task.Delay(2000, stoppingToken);
            }
        }

        consumer.Close();
    }

    private async Task HandleArrivalAsync(string json, CancellationToken ct)
    {
        JsonNode? node;
        try { node = JsonNode.Parse(json); }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "MediaCoordinator: unparseable message on {Topic} — skipped", _kafka.DeliveryTopic);
            return;
        }

        // Tolerant reads throughout — hackathon partners hand-craft envelopes from the docs,
        // and a wrong-typed field should degrade to a specific warning, not a stack trace.
        var payload = (node as JsonObject)?["payload"] ?? node;
        if (payload is not JsonObject)
        {
            _logger.LogWarning("MediaCoordinator: message is not an object envelope/payload — skipped: {Excerpt}",
                json.Length > 120 ? json[..120] : json);
            return;
        }
        var assetId = payload["asset_id"] is JsonValue av && av.TryGetValue<string>(out var aid) ? aid : null;
        var source = payload["source"] is JsonValue sv && sv.TryGetValue<string>(out var src) ? src : null;
        // time_range may legally be a list of ranges — treat anything non-scalar as "unknown".
        var timeRange = payload["time_range"] is JsonValue trv && trv.TryGetValue<string>(out var tr) ? tr : null;
        if (assetId is null || source is null)
        {
            _logger.LogWarning(
                "MediaCoordinator: arrival with missing/non-string asset_id ({AssetId}) or source ({Source}), delivery_id {DeliveryId} — skipped",
                assetId ?? "∅", source ?? "∅", payload["delivery_id"]?.ToString() ?? "∅");
            return;
        }

        var captureComplete = payload["extensions"]?[CaptureCompleteExt] is JsonValue ccv
            && ccv.TryGetValue<bool>(out var cc) && cc;

        // Thread the arrival's correlation onto anything we produce in reaction to it, and
        // record the arrival as the cause (causation_id) — correlation MUST survive end to end.
        var envelope = node as JsonObject;
        var correlationId = envelope?["correlation_id"]?.GetValue<string>();
        var causationId = envelope?["message_id"]?.GetValue<string>();

        var storyId = _dashboard.FindStoryIdByAssetId(assetId);

        // The dashboard's consumer populates the story cache independently, so an arrival can
        // beat a just-published story by milliseconds. Two brief re-checks keep a false
        // WITHHELD (or a bogus orphan) off the governance topic.
        for (var attempt = 0; storyId is null && attempt < 2; attempt++)
        {
            _logger.LogInformation("MediaCoordinator: {AssetId} not matched yet — re-checking", assetId);
            await Task.Delay(500, ct);
            storyId = _dashboard.FindStoryIdByAssetId(assetId);
        }

        if (storyId is null)
        {
            if (_orphanPreview)
            {
                await PublishOrphanStoryAsync(assetId, source, timeRange, captureComplete, correlationId, causationId, ct);
            }
            else
            {
                await PublishWithheldAuditAsync(assetId, source, correlationId, causationId, ct);
            }
            return;
        }

        if (!captureComplete)
        {
            _logger.LogInformation(
                "MediaCoordinator: rolling availability for {AssetId} on {StoryId} (range {Range}) — no state change",
                assetId, storyId, timeRange);
            return;
        }

        var matchedAsset = false;
        var flip = await _dashboard.MutateStoryAsync(storyId, story =>
        {
            var assets = story["assets"] as JsonArray;
            if (assets is null) return;
            foreach (var asset in assets)
            {
                if (asset?["asset_id"] is not JsonValue av2 || !av2.TryGetValue<string>(out var id) || id != assetId) continue;
                matchedAsset = true;
                asset["acquisition_state"] = "CAPTURED";
                var refs = asset["media_refs"] as JsonArray;
                if (refs is not null && timeRange is not null)
                {
                    foreach (var mr in refs)
                    {
                        if (mr?["source"] is JsonValue msv && msv.TryGetValue<string>(out var ms) && ms == source)
                            mr["time_range"] = timeRange;
                    }
                }
            }
        }, ct);

        if (flip.Ok && !matchedAsset)
        {
            _logger.LogWarning(
                "MediaCoordinator: story {StoryId} republished but asset {AssetId} was not found in its assets[] — no state was actually flipped (join drift?)",
                storyId, assetId);
        }
        else if (flip.Ok)
        {
            _logger.LogInformation(
                "MediaCoordinator: capture complete for {AssetId} → {StoryId} republished with acquisition_state CAPTURED (range {Range}); skills re-run on the new version",
                assetId, storyId, timeRange);
        }
        else
        {
            _logger.LogError(
                "MediaCoordinator: capture-complete flip for {AssetId} on {StoryId} FAILED ({Status})",
                assetId, storyId, flip.Status);
        }
    }

    /// <summary>
    /// The skills-model safe-state stop, made observable: no story references this asset,
    /// so the coordinator declines to act and RECORDS the non-action on som.system.audit
    /// (action WITHHELD, system actor) — decision D2·B3's "the absence of an expected
    /// action is observable."
    /// </summary>
    private async Task PublishWithheldAuditAsync(string assetId, string source, string? correlationId, string? causationId, CancellationToken ct)
    {
        var now = DateTimeOffset.UtcNow;
        var payload = new JsonObject
        {
            ["message_type"] = "system.audit",
            ["audit_id"] = Guid.NewGuid().ToString(),
            ["action"] = "WITHHELD",
            ["target"] = new JsonObject { ["kind"] = "ASSET", ["id"] = assetId },
            ["actor"] = new JsonObject { ["actor_id"] = SystemId, ["actor_type"] = "system" },
            ["reason"] = $"Unmatched media arrival: no story references asset '{assetId}' (source {source}); declined to act",
            ["recorded_at"] = now.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'"),
        };

        try
        {
            await ProduceAsync(_kafka.AuditTopic, "system.audit", assetId, payload, correlationId, causationId, ct);
        }
        catch (Exception ex) when (ex is not OperationCanceledException)
        {
            // The whole point of WITHHELD is "the non-action is observable" — if the audit
            // itself can't be recorded, say exactly that rather than a generic failure.
            _logger.LogError(ex,
                "MediaCoordinator: WITHHELD audit for {AssetId} could NOT be recorded on {Topic} — the non-action exists only in this process log",
                assetId, _kafka.AuditTopic);
            return;
        }
        _logger.LogWarning(
            "MediaCoordinator: WITHHELD — unmatched arrival for {AssetId} ({Source}); audit recorded on {Topic}",
            assetId, source, _kafka.AuditTopic);
    }

    /// <summary>
    /// v0.3.2 PREVIEW (Coordinator:OrphanPreview=true): wrap unmatched media in a minimal
    /// ORPHAN story so it enters the editorial workflow instead of being withheld. ORPHAN
    /// is a v0.3.2 scaffold story_type, NOT in locked v0.3.1 — the story is labeled and
    /// carries extensions["com.ibc-poc.orphan_preview"] so nobody mistakes it for ratified.
    /// </summary>
    private async Task PublishOrphanStoryAsync(string assetId, string source, string? timeRange, bool captureComplete, string? correlationId, string? causationId, CancellationToken ct)
    {
        var now = DateTimeOffset.UtcNow;
        var storyId = $"orphan-{assetId}-{now:yyyyMMddHHmmss}";
        var payload = new JsonObject
        {
            ["story_id"] = storyId,
            ["slug"] = $"ORPHAN-{assetId.ToUpperInvariant()}",
            ["headline"] = $"[ORPHAN · v0.3.2 preview] Unmatched media arrival — {assetId}",
            ["story_type"] = "ORPHAN",
            // No lifecycle block: lifecycle is ACTIVE-only (decision #19) and ORPHAN carries none.
            ["assets"] = new JsonArray
            {
                new JsonObject
                {
                    ["asset_id"] = assetId,
                    ["asset_type"] = "VIDEO",
                    ["status"] = "IN_PRODUCTION",
                    ["evidential_position"] = "PRIMARY",
                    ["acquisition_state"] = captureComplete ? "CAPTURED" : "CAPTURING",
                    ["media_refs"] = new JsonArray
                    {
                        new JsonObject
                        {
                            ["source"] = source,
                            ["label"] = "unmatched arrival (orphan preview)",
                            ["time_range"] = timeRange ?? "[0:0_)",
                        },
                    },
                },
            },
            ["updated_at"] = now.ToString("o"),
            ["sequence_number"] = 1,
            ["newsroom_id"] = "nbcu-news",
            ["extensions"] = new JsonObject { ["com.ibc-poc.orphan_preview"] = true },
        };

        await ProduceAsync(_kafka.StoryContextTopic, "story.context", storyId, payload, correlationId, causationId, ct);
        _logger.LogWarning(
            "MediaCoordinator: ORPHAN PREVIEW — authored {StoryId} for unmatched asset {AssetId} (v0.3.2 behaviour, not ratified)",
            storyId, assetId);
    }

    private async Task ProduceAsync(string topic, string messageType, string key, JsonObject payload,
        string? correlationId, string? causationId, CancellationToken ct)
    {
        var now = DateTimeOffset.UtcNow;
        var envelope = new JsonObject
        {
            ["som_version"] = "0.2.0",
            ["message_id"] = Guid.NewGuid().ToString(),
            // Echo the triggering arrival's correlation so the chain is traceable end to end;
            // mint one only if the arrival had none (flat/legacy producer).
            ["correlation_id"] = correlationId ?? Guid.NewGuid().ToString(),
            ["message_type"] = messageType,
            ["timestamp"] = now.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'"),
            ["originating_system"] = new JsonObject
            {
                ["system_id"] = SystemId,
                ["system_type"] = "automation",
                ["system_name"] = "Media Coordinator (WS1 reference consumer)",
                ["vendor"] = "ibc-poc",
                ["version"] = "0.1",
            },
            ["topic"] = topic,
            ["payload"] = payload,
        };
        if (causationId is not null) envelope["causation_id"] = causationId;

        await Producer.ProduceAsync(topic,
            new Message<string, string> { Key = key, Value = envelope.ToJsonString() }, ct);
    }

    public override void Dispose()
    {
        if (_producer is not null)
        {
            _producer.Flush(TimeSpan.FromSeconds(5));
            _producer.Dispose();
        }
        base.Dispose();
    }
}
