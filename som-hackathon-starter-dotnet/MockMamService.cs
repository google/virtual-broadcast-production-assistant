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
public sealed class MockMamService
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
                return _catalog ??= LoadCatalog();
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
    /// Returns the envelope published, or null if the source is unknown / range invalid.
    /// </summary>
    public async Task<JsonObject?> EmitAsync(
        string sourceId,
        string? timeRange = null,
        string? assetIdOverride = null,
        CancellationToken ct = default)
    {
        var entry = Find(sourceId);
        if (entry is null)
        {
            _logger.LogWarning("MockMAM: unknown source_id {SourceId}", sourceId);
            return null;
        }

        var range = timeRange ?? $"[0:0_{entry.DurationSeconds}:0)";
        if (!TimerangePattern.IsMatch(range))
        {
            _logger.LogWarning("MockMAM: invalid TAMS timerange '{Range}' for {SourceId}", range, sourceId);
            return null;
        }

        var assetId = assetIdOverride ?? entry.AssetId;
        if (string.IsNullOrWhiteSpace(assetId))
        {
            _logger.LogWarning("MockMAM: no asset_id for {SourceId} (catalog or override required)", sourceId);
            return null;
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

        var config = new ProducerConfig
        {
            BootstrapServers = _kafka.BootstrapServers,
            Acks = Acks.Leader,
        };
        if (_kafka.SecurityProtocol.Equals("SaslSsl", StringComparison.OrdinalIgnoreCase))
        {
            config.SecurityProtocol = SecurityProtocol.SaslSsl;
            config.SaslMechanism = SaslMechanism.Plain;
            config.SaslUsername = _kafka.SaslUsername;
            config.SaslPassword = _kafka.SaslPassword;
        }

        using var producer = new ProducerBuilder<string, string>(config).Build();
        var result = await producer.ProduceAsync(_kafka.DeliveryTopic, new Message<string, string>
        {
            Key = assetId,
            Value = envelope.ToJsonString(),
        }, ct);

        _logger.LogInformation(
            "MockMAM → {Topic} · source={Source} range={Range} asset={AssetId} (p{Partition}/o{Offset})",
            _kafka.DeliveryTopic, payload["source"], range, assetId,
            result.Partition.Value, result.Offset.Value);

        return envelope;
    }

    private IReadOnlyList<MamCatalogEntry> LoadCatalog()
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
            _logger.LogWarning("MockMAM: catalog not found at {Path} — catalog is empty", relPath);
            return Array.Empty<MamCatalogEntry>();
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
            _logger.LogError(ex, "MockMAM: failed to parse {File}", file);
            return Array.Empty<MamCatalogEntry>();
        }
    }
}

/// <summary>One catalogued Source in the mock store (content/mam-catalog.json, snake_case).</summary>
public sealed record MamCatalogEntry(
    string SourceId,
    string Label,
    int DurationSeconds,
    string? AssetId,
    string? Notes);
