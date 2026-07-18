using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Confluent.Kafka;
using Microsoft.Extensions.Options;

namespace SomSkillWorker;

/// <summary>
/// Mock MAM — stands in for the TAMS media-store participant absent from the IBC PoC.
///
/// SOM never queries the MAM in the demos; a MAM's entire bus contract is two things:
///   1. Be the naming authority for Source URIs (tams://store/id), and
///   2. Emit som.delivery.media_available when media arrives / grows.
/// So this mock is WRITE-ONLY on the bus by design. Do NOT add query APIs or shared
/// state other services read — that would demonstrate a MAM API nobody ratified.
/// The /api/mam/* endpoints exist for the dashboard/simulator only, not for other
/// bus participants.
///
/// Payloads follow schema/v0.3.1-proposed/som-v0.3.1-delivery-media-available.schema.json
/// (Source re-key 29 Jun: Source URI + TAMS timerange — NOT flow_id). Full envelopes are
/// published (the envelope carries the timestamp per decision #18). Lightweight shape
/// checks are done inline; run schema/validate.py for full validation of captured output.
///
/// Catalog lives in content/mam-catalog.json — the Source IDs there are the ones the
/// WS2 seed work should reference from asset.media_refs[].source so the D1·B5 join
/// (arrival event ↔ asset) resolves.
/// </summary>
public sealed class MockMamService : IDisposable
{
    public const string StoreName = "mock-mam-store";

    private static readonly Regex TimerangePattern =
        new(@"^[\[(](\d+:\d+)?_(\d+:\d+)?[\])]$", RegexOptions.Compiled);

    private static readonly JsonSerializerOptions CatalogJsonOptions = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        ReadCommentHandling = JsonCommentHandling.Skip,
    };

    private readonly ILogger<MockMamService> _logger;
    private readonly KafkaOptions _kafka;
    private readonly object _catalogLock = new();
    private IReadOnlyList<MamCatalogEntry>? _catalog;
    private readonly object _producerLock = new();
    private IProducer<string, string>? _producer;

    public MockMamService(ILogger<MockMamService> logger, IOptions<KafkaOptions> kafka)
    {
        _logger = logger;
        _kafka = kafka.Value;
    }

    public IReadOnlyList<MamCatalogEntry> Catalog
    {
        get
        {
            lock (_catalogLock)
            {
                // Cache only a SUCCESSFUL load. LoadCatalog returns null on
                // not-found/parse failure, so a fixed file recovers on the next
                // access — a memoized empty list would need a process restart.
                if (_catalog is not null) return _catalog;
                var loaded = LoadCatalog();
                if (loaded is not null) _catalog = loaded;
                return loaded ?? Array.Empty<MamCatalogEntry>();
            }
        }
    }

    // One long-lived producer, built on first emit and reused (matches
    // DashboardService/SkillWorker). Routing auth through KafkaAuthHelper is what
    // makes OAuthBearer token-refresh work on the authenticated GCP cluster — a
    // hand-rolled SASL block works over local Plaintext but fails there.
    private IProducer<string, string> Producer
    {
        get
        {
            if (_producer is not null) return _producer;
            lock (_producerLock)
            {
                if (_producer is not null) return _producer;
                var config = new ProducerConfig
                {
                    BootstrapServers = _kafka.BootstrapServers,
                    Acks = Acks.Leader,
                };
                KafkaAuthHelper.Configure(config, _kafka);
                var pb = new ProducerBuilder<string, string>(config);
                KafkaAuthHelper.AttachOAuth(pb, _kafka);
                _producer = pb.Build();
                return _producer;
            }
        }
    }

    public MamCatalogEntry? Find(string sourceId) =>
        Catalog.FirstOrDefault(e => string.Equals(e.SourceId, sourceId, StringComparison.OrdinalIgnoreCase));

    /// <summary>
    /// Publish a delivery.media_available envelope for a catalogued Source.
    /// timeRange defaults to the full catalogued duration; pass a shorter range to
    /// mimic TAMS growing-recording behaviour (a recording is addressable while
    /// still being captured), then emit again with a longer range.
    /// Returns a result carrying the published envelope, or the discriminated
    /// reason nothing was emitted (unknown source / invalid range / missing asset /
    /// publish failure) so callers surface the specific cause instead of a bare null.
    /// </summary>
    public async Task<MamEmitResult> EmitAsync(
        string sourceId,
        string? timeRange = null,
        string? assetIdOverride = null,
        bool captureComplete = false,
        CancellationToken ct = default)
    {
        var entry = Find(sourceId);
        if (entry is null)
        {
            _logger.LogWarning("MockMAM: unknown source_id {SourceId}", sourceId);
            return MamEmitResult.Fail(MamEmitStatus.UnknownSource, $"unknown source_id '{sourceId}'");
        }

        var range = timeRange ?? $"[0:0_{entry.DurationSeconds}:0)";
        if (!TimerangePattern.IsMatch(range))
        {
            _logger.LogWarning("MockMAM: invalid TAMS timerange '{Range}' for {SourceId}", range, sourceId);
            return MamEmitResult.Fail(MamEmitStatus.InvalidRange, $"invalid TAMS timerange '{range}'");
        }

        var assetId = assetIdOverride ?? entry.AssetId;
        if (string.IsNullOrWhiteSpace(assetId))
        {
            _logger.LogWarning("MockMAM: no asset_id for {SourceId} (catalog or override required)", sourceId);
            return MamEmitResult.Fail(MamEmitStatus.MissingAsset, $"no asset_id for source '{sourceId}' (catalog or override required)");
        }

        var now = DateTimeOffset.UtcNow;
        // NOTE: schema asks uuid format; Guid.NewGuid() (v4) satisfies it. The spec
        // recommends UUIDv7 for message_id time-ordering — fine to upgrade at WS1.
        var payload = new JsonObject
        {
            ["message_type"] = "delivery.media_available",
            ["delivery_id"] = Guid.NewGuid().ToString(),
            ["asset_id"] = assetId,
            ["source"] = $"tams://{StoreName}/{entry.SourceId}",
            ["time_range"] = range,
            ["arrived_in"] = StoreName,
            ["arrived_at"] = now.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss'Z'"),
        };

        // "Capture finished" is not a first-class delivery field in v0.3.1, so it rides the
        // designed com.{vendor}.* extension namespace — a live example of the escape hatch
        // partners are told to use. MediaCoordinatorService reacts by flipping the asset's
        // acquisition_state CAPTURING → CAPTURED.
        if (captureComplete)
        {
            payload["extensions"] = new JsonObject
            {
                ["com.ibc-poc.capture_complete"] = true,
            };
        }

        var envelope = new JsonObject
        {
            // Wire version stays 0.2.0 until v0.3 ratifies on the wire (SOM-048).
            ["som_version"] = "0.2.0",
            ["message_id"] = Guid.NewGuid().ToString(),
            ["correlation_id"] = Guid.NewGuid().ToString(),
            ["message_type"] = "delivery.media_available",
            ["timestamp"] = now.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'"),
            ["originating_system"] = new JsonObject
            {
                ["system_id"] = "mock-mam",
                ["system_type"] = "archive",           // honest fit in the v0.3 enum
                ["system_name"] = "Mock MAM (TAMS stand-in for IBC PoC)",
                ["vendor"] = "ibc-poc",
                ["version"] = "0.1",
            },
            ["topic"] = _kafka.DeliveryTopic,
            ["payload"] = payload,
        };

        try
        {
            var result = await Producer.ProduceAsync(_kafka.DeliveryTopic, new Message<string, string>
            {
                Key = assetId,
                Value = envelope.ToJsonString(),
            }, ct);

            _logger.LogInformation(
                "MockMAM → {Topic} · source={Source} range={Range} asset={AssetId} (p{Partition}/o{Offset})",
                _kafka.DeliveryTopic, payload["source"], range, assetId,
                result.Partition.Value, result.Offset.Value);

            return MamEmitResult.Success(envelope);
        }
        catch (Exception ex)
        {
            // Broker unreachable, SASL/ACL failure, topic denied, oversize message,
            // or a build/DNS failure from the lazy Producer getter. Surface it —
            // don't let ProduceAsync throw out as an opaque 500 / silent scenario abort.
            _logger.LogError(ex, "MockMAM: publish to {Topic} failed for source {SourceId}",
                _kafka.DeliveryTopic, sourceId);
            return MamEmitResult.Fail(MamEmitStatus.PublishFailed,
                $"publish to {_kafka.DeliveryTopic} failed: {ex.Message}");
        }
    }

    // Returns null on not-found/parse failure (distinct from an empty catalog) so
    // the caller does not memoize a failed load — see the Catalog property.
    private IReadOnlyList<MamCatalogEntry>? LoadCatalog()
    {
        // Same resolution order as /api/content: source tree for `dotnet run`,
        // BaseDirectory for the published container.
        const string relPath = "content/mam-catalog.json";
        var sourceTreePath = Path.Combine(AppContext.BaseDirectory, "..", "..", "..", relPath);
        var publishedPath = Path.Combine(AppContext.BaseDirectory, relPath);
        var file = File.Exists(sourceTreePath) ? sourceTreePath
                 : File.Exists(publishedPath) ? publishedPath
                 : File.Exists(relPath) ? relPath
                 : null;
        if (file is null)
        {
            _logger.LogWarning("MockMAM: catalog not found at {Path} — will retry on next access", relPath);
            return null;
        }

        try
        {
            var entries = JsonSerializer.Deserialize<List<MamCatalogEntry>>(
                File.ReadAllText(file), CatalogJsonOptions);
            _logger.LogInformation("MockMAM: loaded {Count} catalog entries from {File}",
                entries?.Count ?? 0, file);
            return entries ?? new List<MamCatalogEntry>();
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "MockMAM: failed to parse {File} — will retry on next access", file);
            return null;
        }
    }

    public void Dispose()
    {
        if (_producer is null) return;
        _producer.Flush(TimeSpan.FromSeconds(5));
        _producer.Dispose();
    }
}

/// <summary>One catalogued Source in the mock store (content/mam-catalog.json, snake_case).</summary>
public sealed record MamCatalogEntry(
    string SourceId,
    string Label,
    int DurationSeconds,
    string? AssetId,
    string? Notes);

public enum MamEmitStatus { Emitted, UnknownSource, InvalidRange, MissingAsset, PublishFailed }

/// <summary>
/// Outcome of a MockMAM emit. Carries the discriminated failure reason so callers
/// (the /api/mam/emit endpoint, the simulator) surface the specific cause rather
/// than collapsing every miss to a bare null.
/// </summary>
public sealed record MamEmitResult(MamEmitStatus Status, JsonObject? Envelope, string? Error)
{
    public bool Ok => Status == MamEmitStatus.Emitted;
    public static MamEmitResult Success(JsonObject envelope) => new(MamEmitStatus.Emitted, envelope, null);
    public static MamEmitResult Fail(MamEmitStatus status, string error) => new(status, null, error);
}
