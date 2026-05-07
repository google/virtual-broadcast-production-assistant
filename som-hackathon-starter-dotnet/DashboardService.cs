using System.Collections.Concurrent;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Confluent.Kafka;
using Confluent.Kafka.Admin;
using Microsoft.Extensions.Options;

namespace SomSkillWorker;

/// <summary>
/// Live dashboard backend.
///
/// Consumes ALL SOM topics (story.context, skills.staging, skills.events, skills.runs, skills.rejected),
/// fans them out to connected WebSocket clients, and exposes an approve/reject API that gates whether
/// a skill output makes it onto the production bus (som.skills.events) or the rejection bus
/// (som.skills.rejected).
/// </summary>
public sealed class DashboardService : BackgroundService
{
    private readonly ILogger<DashboardService> _logger;
    private readonly KafkaOptions _options;
    private readonly IProducer<string, string> _producer;

    // Track all live WebSocket connections so we can broadcast bus events.
    private readonly ConcurrentDictionary<Guid, WebSocket> _sockets = new();

    // Pending staged outputs awaiting approve/reject decision.
    // Key = warning_id | suggestion_id | enrichment_id
    private readonly ConcurrentDictionary<string, PendingOutput> _pending = new();

    // Most recent story payload seen on som.story.context, keyed by story_id.
    // Used by the re-run endpoint to republish (with bumped sequence_number) and
    // simulate an NRCS update without the user typing anything.
    private readonly ConcurrentDictionary<string, JsonNode> _stories = new();

    public DashboardService(ILogger<DashboardService> logger, IOptions<KafkaOptions> options)
    {
        _logger = logger;
        _options = options.Value;

        var producerConfig = new ProducerConfig
        {
            BootstrapServers = _options.BootstrapServers,
            Acks = Acks.All,
            EnableIdempotence = true,
        };
        ApplyAuth(producerConfig);
        _producer = new ProducerBuilder<string, string>(producerConfig).Build();
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        // Single consumer subscribed to all topics. AutoOffsetReset.Earliest lets late-arriving
        // dashboard sessions replay the bus from the start of the demo.
        var consumerConfig = new ConsumerConfig
        {
            BootstrapServers = _options.BootstrapServers,
            GroupId = $"{_options.DashboardGroupId}-{Guid.NewGuid():N}",
            AutoOffsetReset = AutoOffsetReset.Earliest,
            EnableAutoCommit = true,
            // Detect topic recreation quickly so the reset button works smoothly.
            TopicMetadataRefreshIntervalMs = 3000,
        };
        ApplyAuth(consumerConfig);

        using var consumer = new ConsumerBuilder<string, string>(consumerConfig).Build();
        consumer.Subscribe(new[]
        {
            _options.StoryContextTopic,
            _options.SkillStagingTopic,
            _options.SkillEventsTopic,
            _options.SkillRunsTopic,
            _options.SkillRejectedTopic,
        });

        _logger.LogInformation("Dashboard subscribed to 5 topics");

        await Task.Yield();

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var result = consumer.Consume(TimeSpan.FromSeconds(1));
                if (result is null) continue;

                var node = JsonNode.Parse(result.Message.Value);
                if (node is null) continue;

                // Drop messages produced before the most recent reset so the UI stays clean.
                // Kafka attaches a producer-side timestamp to each message; if it's older
                // than our reset marker, this is a "ghost" from before the reset.
                var msgTimestamp = result.Message.Timestamp.UtcDateTime;
                if (msgTimestamp != default && msgTimestamp < _resetMarker.UtcDateTime)
                    continue;

                // Cache the most-recent story payload by story_id so the re-run endpoint
                // can republish it without round-tripping through Kafka or the seed files.
                if (result.Topic == _options.StoryContextTopic)
                {
                    var sid = (node["payload"]?["story_id"] ?? node["story_id"])?.GetValue<string>();
                    if (sid is not null) _stories[sid] = node;
                }

                // For staged outputs, hold them in the pending queue so the UI can approve/reject.
                if (result.Topic == _options.SkillStagingTopic)
                {
                    var id = ExtractOutputId(node);
                    if (id is not null)
                    {
                        _pending[id] = new PendingOutput(
                            id,
                            result.Message.Key,
                            node,
                            DateTimeOffset.UtcNow);
                    }
                }

                var receivedAt = DateTimeOffset.UtcNow;

                await BroadcastAsync(new
                {
                    type = "bus_event",
                    topic = result.Topic,
                    key = result.Message.Key,
                    partition = result.Partition.Value,
                    offset = result.Offset.Value,
                    received_at = receivedAt,
                    payload = node,
                }, stoppingToken);
            }
            catch (OperationCanceledException) { break; }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Dashboard consume error");
            }
        }

        consumer.Close();
    }

    // ─── WebSocket plumbing ────────────────────────────────────────────────

    public async Task HandleSocketAsync(WebSocket socket, CancellationToken ct)
    {
        var id = Guid.NewGuid();
        _sockets[id] = socket;
        _logger.LogInformation("WebSocket {Id} connected ({Count} total)", id, _sockets.Count);

        try
        {
            // Send the current pending queue on connect so a refreshed dashboard sees state.
            var snapshot = new
            {
                type = "snapshot",
                pending = _pending.Values.Select(p => new
                {
                    id = p.OutputId,
                    story_id = p.StoryKey,
                    staged_at = p.StagedAt,
                    payload = p.Output,
                }).ToArray(),
            };
            await SendAsync(socket, snapshot, ct);

            var buffer = new byte[4096];
            while (socket.State == WebSocketState.Open && !ct.IsCancellationRequested)
            {
                var result = await socket.ReceiveAsync(buffer, ct);
                if (result.MessageType == WebSocketMessageType.Close) break;
                // Inbound messages from clients are not used today.
            }
        }
        catch (OperationCanceledException) { }
        catch (WebSocketException ex)
        {
            _logger.LogDebug(ex, "WebSocket {Id} closed unexpectedly", id);
        }
        finally
        {
            _sockets.TryRemove(id, out _);
            _logger.LogInformation("WebSocket {Id} disconnected ({Count} remaining)", id, _sockets.Count);
        }
    }

    private async Task BroadcastAsync(object message, CancellationToken ct)
    {
        if (_sockets.IsEmpty) return;

        var json = JsonSerializer.Serialize(message);
        var bytes = Encoding.UTF8.GetBytes(json);

        foreach (var (id, socket) in _sockets)
        {
            if (socket.State != WebSocketState.Open)
            {
                _sockets.TryRemove(id, out _);
                continue;
            }

            try
            {
                await socket.SendAsync(bytes, WebSocketMessageType.Text, endOfMessage: true, ct);
            }
            catch
            {
                _sockets.TryRemove(id, out _);
            }
        }
    }

    private static async Task SendAsync(WebSocket socket, object message, CancellationToken ct)
    {
        var json = JsonSerializer.Serialize(message);
        var bytes = Encoding.UTF8.GetBytes(json);
        await socket.SendAsync(bytes, WebSocketMessageType.Text, endOfMessage: true, ct);
    }

    // ─── Approval gate ─────────────────────────────────────────────────────

    public async Task<DecisionResult> DecideAsync(string outputId, string decision, string? reviewer, CancellationToken ct)
    {
        if (!_pending.TryRemove(outputId, out var pending))
            return new DecisionResult(false, "not_found", null);

        var key = pending.StoryKey ?? "";

        if (decision.Equals("approve", StringComparison.OrdinalIgnoreCase))
        {
            // Annotate and republish to the production bus.
            var enriched = pending.Output.DeepClone();
            enriched["approved_by"] = reviewer ?? "dashboard-user";
            enriched["approved_at"] = DateTimeOffset.UtcNow.ToString("o");

            await _producer.ProduceAsync(_options.SkillEventsTopic,
                new Message<string, string> { Key = key, Value = enriched.ToJsonString() }, ct);

            await BroadcastAsync(new
            {
                type = "decision",
                output_id = outputId,
                decision = "approved",
                reviewer = reviewer ?? "dashboard-user",
                at = DateTimeOffset.UtcNow,
            }, ct);

            return new DecisionResult(true, "approved", _options.SkillEventsTopic);
        }

        if (decision.Equals("reject", StringComparison.OrdinalIgnoreCase))
        {
            var enriched = pending.Output.DeepClone();
            enriched["rejected_by"] = reviewer ?? "dashboard-user";
            enriched["rejected_at"] = DateTimeOffset.UtcNow.ToString("o");

            await _producer.ProduceAsync(_options.SkillRejectedTopic,
                new Message<string, string> { Key = key, Value = enriched.ToJsonString() }, ct);

            await BroadcastAsync(new
            {
                type = "decision",
                output_id = outputId,
                decision = "rejected",
                reviewer = reviewer ?? "dashboard-user",
                at = DateTimeOffset.UtcNow,
            }, ct);

            return new DecisionResult(true, "rejected", _options.SkillRejectedTopic);
        }

        // Unknown decision — put back the pending entry so the UI can retry.
        _pending[outputId] = pending;
        return new DecisionResult(false, "invalid_decision", null);
    }

    /// <summary>
    /// Republish the cached story envelope for {storyId} to som.story.context, simulating
    /// an NRCS update. Bumps sequence_number and updated_at so the skill sees a "new"
    /// version. Auto-clears any prior pending warnings for this story since they're against
    /// a superseded version.
    /// </summary>
    public Task<RerunResult> RerunSkillAsync(string storyId, CancellationToken ct) =>
        RepublishAsync(storyId, _ => { /* no mutation; pure re-run */ }, ct);

    // ─── Lifecycle simulator ────────────────────────────────────────────────
    // These mutate the cached story payload to simulate what an NRCS would do
    // when an editor advances the lifecycle, attaches compliance, etc. Each
    // mutation triggers a fresh story.context publish, so the skill re-runs
    // and any pending warnings get cleared as stale.

    private static readonly string[] PhaseOrder = { "PLANNED", "GATHERING", "DEVELOPING", "READY_TO_AIR", "ON_AIR", "PUBLISHED" };
    private static readonly Dictionary<string, string> PhaseAlias = new(StringComparer.OrdinalIgnoreCase)
    {
        ["BREAKING"] = "DEVELOPING",
        ["COMPLETE"] = "PUBLISHED",
    };

    public Task<RerunResult> AdvancePhaseAsync(string storyId, CancellationToken ct) =>
        RepublishAsync(storyId, payload =>
        {
            var lifecycle = payload["lifecycle"] is JsonObject lc ? lc : new JsonObject();
            var current = lifecycle["phase"]?.GetValue<string>() ?? "PLANNED";
            var canonical = PhaseAlias.TryGetValue(current, out var aliased) ? aliased : current;
            var idx = Array.IndexOf(PhaseOrder, canonical);
            if (idx >= 0 && idx < PhaseOrder.Length - 1)
            {
                lifecycle["previous_phase"] = current;
                lifecycle["phase"] = PhaseOrder[idx + 1];
                lifecycle["phase_entered_at"] = DateTimeOffset.UtcNow.ToString("o");
                payload["lifecycle"] = lifecycle;
            }
        }, ct);

    public Task<RerunResult> AddComplianceFlagAsync(
        string storyId, string flagType, string severity, string detail, CancellationToken ct) =>
        RepublishAsync(storyId, payload =>
        {
            var compliance = payload["compliance"] is JsonArray arr ? arr : new JsonArray();
            compliance.Add(new JsonObject
            {
                ["flag_id"] = $"cf-sim-{Guid.NewGuid():N}".Substring(0, 18),
                ["type"] = flagType,
                ["severity"] = severity,
                ["detail"] = detail,
                ["raised_by"] = "dashboard-simulator",
                ["raised_at"] = DateTimeOffset.UtcNow.ToString("o"),
                ["status"] = "ACTIVE",
            });
            payload["compliance"] = compliance;
        }, ct);

    /// <summary>
    /// Shared helper that clones the cached payload, applies the caller's mutation,
    /// bumps version markers, drops stale pending warnings, republishes to story.context,
    /// and broadcasts a dashboard refresh.
    /// </summary>
    private async Task<RerunResult> RepublishAsync(
        string storyId, Action<JsonNode> mutate, CancellationToken ct)
    {
        if (!_stories.TryGetValue(storyId, out var cached))
            return new RerunResult(false, "story_not_seen", 0);

        var clone = cached.DeepClone();
        // TestProducer publishes the payload directly; a real producer would publish a SOM v0.2 envelope wrapping it.
        var payload = clone["payload"] ?? clone;

        mutate(payload);

        var seq = payload["sequence_number"]?.GetValue<int>() ?? 0;
        payload["sequence_number"] = seq + 1;
        payload["updated_at"] = DateTimeOffset.UtcNow.ToString("o");

        var clearedIds = _pending.Where(kv =>
                kv.Value.Output["story_id"]?.GetValue<string>() == storyId)
            .Select(kv => kv.Key)
            .ToList();
        foreach (var id in clearedIds) _pending.TryRemove(id, out _);

        await _producer.ProduceAsync(_options.StoryContextTopic,
            new Message<string, string> { Key = storyId, Value = clone.ToJsonString() }, ct);

        await BroadcastAsync(new
        {
            type = "rerun",
            story_id = storyId,
            new_sequence_number = seq + 1,
            cleared_pending = clearedIds.Count,
            at = DateTimeOffset.UtcNow,
        }, ct);

        return new RerunResult(true, "republished", clearedIds.Count);
    }

    public sealed record RerunResult(bool Ok, string Status, int ClearedPending);

    /// <summary>
    /// Reset the dashboard view: clear the pending queue and tell every connected dashboard
    /// to wipe its UI state. From this moment forward, only NEW bus events show up.
    ///
    /// We deliberately do NOT delete or truncate the underlying Kafka topics — both
    /// approaches (DeleteTopics + recreate, DeleteRecords) leave live consumers in a bad
    /// state in this demo's single-broker setup. Old messages stay on disk for replay via
    /// Kafka UI; for a fully empty bus, run `docker compose down -v && docker compose up -d`.
    /// </summary>
    public async Task<ResetResult> ResetBusAsync(CancellationToken ct)
    {
        var topics = new[]
        {
            _options.StoryContextTopic,
            _options.SkillStagingTopic,
            _options.SkillEventsTopic,
            _options.SkillRejectedTopic,
            _options.SkillRunsTopic,
        };

        _resetMarker = DateTimeOffset.UtcNow;
        _pending.Clear();
        _stories.Clear();

        await BroadcastAsync(new
        {
            type = "reset",
            at = _resetMarker,
            topics,
        }, ct);

        _logger.LogInformation("Dashboard reset at {At} (cleared pending queue, signalled UI wipe)", _resetMarker);
        return new ResetResult(true, topics.Length);
    }

    /// <summary>
    /// Most recent reset timestamp. Bus events received before this are suppressed from
    /// broadcast so the dashboard doesn't show "ghost" history after a reset.
    /// </summary>
    private DateTimeOffset _resetMarker = DateTimeOffset.MinValue;

    public sealed record ResetResult(bool Ok, int TopicsReset);

    public IReadOnlyCollection<object> SnapshotPending() => _pending.Values
        .Select(p => (object)new
        {
            id = p.OutputId,
            story_id = p.StoryKey,
            staged_at = p.StagedAt,
            payload = p.Output,
        })
        .ToArray();

    // ─── Helpers ────────────────────────────────────────────────────────────

    private static string? ExtractOutputId(JsonNode node) =>
        node["warning_id"]?.GetValue<string>()
        ?? node["suggestion_id"]?.GetValue<string>()
        ?? node["enrichment_id"]?.GetValue<string>();

    private void ApplyAuth(ClientConfig config)
    {
        if (_options.SecurityProtocol.Equals("SaslSsl", StringComparison.OrdinalIgnoreCase))
        {
            config.SecurityProtocol = SecurityProtocol.SaslSsl;
            config.SaslMechanism = SaslMechanism.Plain;
            config.SaslUsername = _options.SaslUsername;
            config.SaslPassword = _options.SaslPassword;
        }
    }

    public override void Dispose()
    {
        _producer.Dispose();
        base.Dispose();
    }

    private sealed record PendingOutput(
        string OutputId,
        string? StoryKey,
        JsonNode Output,
        DateTimeOffset StagedAt);

    public sealed record DecisionResult(bool Ok, string Status, string? PublishedTopic);
}
