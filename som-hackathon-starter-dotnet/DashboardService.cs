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
            // Bounded: with librdkafka's 5-min default, a broker outage hangs an
            // approve/reject click for minutes before failing.
            MessageTimeoutMs = 10000,
        };
        ApplyAuth(producerConfig);
        var pb = new ProducerBuilder<string, string>(producerConfig);
        KafkaAuthHelper.AttachOAuth(pb, _options);
        _producer = pb.Build();
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
        var cb = new ConsumerBuilder<string, string>(consumerConfig);
        KafkaAuthHelper.AttachOAuth(cb, _options);

        using var consumer = cb.Build();
        consumer.Subscribe(new[]
        {
            _options.StoryContextTopic,
            _options.SkillStagingTopic,
            _options.SkillEventsTopic,
            _options.SkillRunsTopic,
            _options.SkillRejectedTopic,
            // Observed for the bus event log only — MediaCoordinatorService is the delivery
            // consumer that acts; the dashboard just shows the traffic.
            _options.DeliveryTopic,
            _options.AuditTopic,
        });

        _logger.LogInformation("Dashboard subscribed to 7 topics");

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
                    var sidNode = node["payload"]?["story_id"] ?? node["story_id"];
                    var sid = sidNode is JsonValue sv && sv.TryGetValue<string>(out var s) ? s : null;
                    if (sid is not null)
                    {
                        _stories[sid] = node;
                        // Warn ONCE, at ingest, when a story can never appear in the
                        // /api/stories directory — the read path skips silently (it runs
                        // per poll), so this line is the only log evidence explaining why.
                        var st = (node["payload"] ?? node) is JsonObject po
                            && po["story_type"] is JsonValue stv && stv.TryGetValue<string>(out var stVal) ? stVal : null;
                        if (st is not ("ACTIVE" or "PLANNED" or "KILLED" or "SPIKED" or "ARCHIVED" or "ORPHAN"))
                            _logger.LogWarning(
                                "Story {StoryId} cached with missing/unknown story_type ({StoryType}) — it will not appear in the /api/stories directory",
                                sid, st ?? "∅");
                    }
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
            // Annotate and republish to the production bus. If the produce fails, put the
            // pending item BACK — a broker blip must not silently discard a staged warning.
            var enriched = pending.Output.DeepClone();
            enriched["approved_by"] = reviewer ?? "dashboard-user";
            enriched["approved_at"] = DateTimeOffset.UtcNow.ToString("o");

            try
            {
                await _producer.ProduceAsync(_options.SkillEventsTopic,
                    new Message<string, string> { Key = key, Value = enriched.ToJsonString() }, ct);
            }
            catch
            {
                _pending[outputId] = pending;
                throw;
            }

            await BroadcastAsync(new
            {
                type = "decision",
                output_id = outputId,
                decision = "approved",
                reviewer = reviewer ?? "dashboard-user",
                at = DateTimeOffset.UtcNow,
            }, ct);

            // Post-commit, post-broadcast: the audit rides neither the request token nor
            // the UI's critical path — on a degraded broker the operator's confirmation
            // must not wait up to 10s behind the audit produce. Failure inside is logged,
            // never thrown.
            await EmitDecisionAuditAsync(pending, "CLEARED", reviewer ?? "dashboard-user");

            return new DecisionResult(true, "approved", _options.SkillEventsTopic);
        }

        if (decision.Equals("reject", StringComparison.OrdinalIgnoreCase))
        {
            var enriched = pending.Output.DeepClone();
            enriched["rejected_by"] = reviewer ?? "dashboard-user";
            enriched["rejected_at"] = DateTimeOffset.UtcNow.ToString("o");

            try
            {
                await _producer.ProduceAsync(_options.SkillRejectedTopic,
                    new Message<string, string> { Key = key, Value = enriched.ToJsonString() }, ct);
            }
            catch
            {
                _pending[outputId] = pending;
                throw;
            }

            await BroadcastAsync(new
            {
                type = "decision",
                output_id = outputId,
                decision = "rejected",
                reviewer = reviewer ?? "dashboard-user",
                at = DateTimeOffset.UtcNow,
            }, ct);

            // Post-commit, post-broadcast (see the approve branch).
            await EmitDecisionAuditAsync(pending, "WITHHELD", reviewer ?? "dashboard-user");

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

    // SOM v0.3 lifecycle phases (decision #19): nested under story_type ACTIVE,
    // traversed in this order. LIVE/AIRED are NOT phases — they are derived from
    // the Telling (decision #16). PLANNED is a story_type, not a phase.
    private static readonly string[] PhaseOrder = { "DEVELOPING", "READY_TO_AIR", "BREAKING", "PUBLISHED" };
    // Tolerate legacy/v0.2 phase values on inbound seeds by mapping them onto the v0.3 set.
    private static readonly Dictionary<string, string> PhaseAlias = new(StringComparer.OrdinalIgnoreCase)
    {
        ["PLANNED"]   = "DEVELOPING",   // PLANNED is a story_type in v0.3; treat as the first active phase here
        ["GATHERING"] = "DEVELOPING",
        ["ON_AIR"]    = "BREAKING",     // on-air is derived from the Telling; nearest editorial phase is BREAKING
        ["COMPLETE"]  = "PUBLISHED",
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
        // Messages are SOM envelopes (payload-wrapped); tolerate bare payloads from
        // external producers still on the v0.2 shortcut.
        var payload = clone["payload"] ?? clone;

        mutate(payload);

        var seq = payload["sequence_number"]?.GetValue<int>() ?? 0;
        payload["sequence_number"] = seq + 1;
        payload["updated_at"] = DateTimeOffset.UtcNow.ToString("o");

        // A republish is a NEW message: fresh message_id + timestamp on the envelope,
        // same correlation_id so the story lifecycle stays threaded.
        if (clone["payload"] is not null)
        {
            clone["message_id"] = Guid.NewGuid().ToString();
            clone["timestamp"] = DateTimeOffset.UtcNow.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'");
        }

        var clearedIds = _pending.Where(kv =>
                ((kv.Value.Output["payload"] ?? kv.Value.Output)?["story_id"]?.GetValue<string>()) == storyId)
            .Select(kv => kv.Key)
            .ToList();

        // Produce FIRST, clear after: if the publish fails, the pending warnings must
        // survive — otherwise a failed republish silently loses them with no new version.
        await _producer.ProduceAsync(_options.StoryContextTopic,
            new Message<string, string> { Key = storyId, Value = clone.ToJsonString() }, ct);

        foreach (var id in clearedIds) _pending.TryRemove(id, out _);

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
    /// Resolve the story that references {assetId} in its assets[] — the upward half of the
    /// SOM↔TAMS join (delivery event → asset_id → Asset → Story). Returns null if no cached
    /// story references the asset.
    /// </summary>
    public string? FindStoryIdByAssetId(string assetId)
    {
        foreach (var (storyId, node) in _stories)
        {
            // Tolerant reads throughout: one malformed story (e.g. a vendor publishing a
            // non-string asset_id) must not poison the lookup for every other arrival.
            var assets = (node["payload"] ?? node) is JsonObject p ? p["assets"] as JsonArray : null;
            if (assets is null) continue;
            foreach (var asset in assets)
            {
                if (asset?["asset_id"] is JsonValue v && v.TryGetValue<string>(out var id) && id == assetId)
                    return storyId;
            }
        }
        return null;
    }

    /// <summary>
    /// Public republish-with-mutation for other in-process participants (the media
    /// coordinator). Same semantics as the lifecycle-simulator endpoints: bump
    /// sequence_number, stamp updated_at, clear stale pending, republish.
    /// </summary>
    public Task<RerunResult> MutateStoryAsync(string storyId, Action<JsonNode> mutate, CancellationToken ct) =>
        RepublishAsync(storyId, mutate, ct);

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
            _options.DeliveryTopic,
            _options.AuditTopic,
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

    /// <summary>
    /// The story-directory projection: a thin, SOM-shaped listing of the live story set
    /// materialised from the bus. This is a read-only CACHE of the bus, never a second
    /// home for the truth — and serving it is a role any participant could fill, not a
    /// privilege of this process. Live set = story_type ACTIVE/PLANNED only: closed
    /// types (KILLED/SPIKED/ARCHIVED) are over, and ORPHAN is v0.3.2 preview scaffolding
    /// that must not leak into a directory partners browse.
    /// </summary>
    public IReadOnlyCollection<JsonObject> SnapshotStories()
    {
        var rows = new List<(DateTimeOffset UpdatedAt, JsonObject Row)>();
        foreach (var (storyId, node) in _stories)
        {
            // Tolerant reads: one malformed story must not poison the directory. The
            // typed guards cover wrong-typed fields; the try covers what guards cannot —
            // JsonObject materializes nested objects lazily and THROWS on duplicate JSON
            // keys, and nothing touches a cached story's lifecycle internals before here,
            // so without it one hand-crafted envelope 500s the endpoint for everyone.
            try
            {
                if ((node["payload"] ?? node) is not JsonObject p) continue;
                if (p["story_type"] is not JsonValue tv || !tv.TryGetValue<string>(out var storyType)) continue;
                if (storyType is not ("ACTIVE" or "PLANNED")) continue;

                var updated = p["updated_at"] is JsonValue uv && uv.TryGetValue<string>(out var u) ? u : null;
                var row = new JsonObject
                {
                    ["story_id"] = storyId,
                    ["slug"] = p["slug"] is JsonValue sv && sv.TryGetValue<string>(out var slug) ? slug : null,
                    ["headline"] = p["headline"] is JsonValue hv && hv.TryGetValue<string>(out var headline) ? headline : null,
                    ["story_type"] = storyType,
                    ["updated_at"] = updated,
                };
                // lifecycle iff the story carries one (ACTIVE-only, decision #19) — the
                // projection mirrors the schema rule rather than flattening it away.
                if (p["lifecycle"] is JsonObject lc && lc["phase"] is JsonValue pv && pv.TryGetValue<string>(out var phase))
                    row["lifecycle"] = new JsonObject { ["phase"] = phase };

                // The bus carries mixed timestamp shapes ("…Z" seeds vs "o"-format
                // republishes), so ordinal string order can invert near-ties — parse.
                rows.Add((DateTimeOffset.TryParse(updated, out var ts) ? ts : DateTimeOffset.MinValue, row));
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex,
                    "Story directory: cached story {StoryId} is unreadable — omitted from /api/stories", storyId);
            }
        }
        return rows.OrderByDescending(r => r.UpdatedAt).Select(r => r.Row).ToArray();
    }

    // ─── Helpers ────────────────────────────────────────────────────────────

    private static string? ExtractOutputId(JsonNode node)
    {
        // Skill outputs are now wrapped in a SOM envelope (the typed fields live under
        // "payload"); tolerate both enveloped and legacy bare-payload messages.
        var p = node["payload"] ?? node;
        return p["warning_id"]?.GetValue<string>()
            ?? p["suggestion_id"]?.GetValue<string>()
            ?? p["enrichment_id"]?.GetValue<string>();
    }

    private void ApplyAuth(ClientConfig config)
    {
        KafkaAuthHelper.Configure(config, _options);
    }

    public override void Dispose()
    {
        _producer.Dispose();
        base.Dispose();
    }

    /// <summary>
    /// Record a human gate decision on som.system.audit — the governance-grade act.
    /// approve → CLEARED; reject → WITHHELD (terminal for this output instance; a
    /// re-run creates a new output). Mirrors MediaCoordinatorService's audit envelope:
    /// same correlation_id as the staged output, causation_id = the staged message_id.
    /// Audit failure is logged loudly but never undoes the decision — the republish
    /// has already happened; the record must not be able to veto the act.
    /// </summary>
    private async Task EmitDecisionAuditAsync(PendingOutput pending, string action, string reviewer)
    {
        try
        {
            var envelope = pending.Output as JsonObject;
            var payload = envelope?["payload"] as JsonObject ?? envelope;
            var (targetKind, targetId, storyFallback) = ResolveAuditTarget(payload);
            var skillId = payload?["skill_id"] is JsonValue skv && skv.TryGetValue<string>(out var sk) ? sk : "unknown-skill";
            var storyId = payload?["story_id"] is JsonValue sidv && sidv.TryGetValue<string>(out var sid) ? sid : null;
            var now = DateTimeOffset.UtcNow;

            var auditPayload = new JsonObject
            {
                ["message_type"] = "system.audit",
                ["audit_id"] = Guid.NewGuid().ToString(),
                ["action"] = action,
                ["target"] = new JsonObject { ["kind"] = targetKind, ["id"] = targetId },
                ["actor"] = new JsonObject { ["actor_id"] = reviewer, ["actor_type"] = "user" },
                ["reason"] = $"Dashboard gate decision '{action}' on staged output '{pending.OutputId}' from skill '{skillId}'"
                    + (storyId is null ? "" : $" (story '{storyId}')")
                    + (storyFallback
                        ? " — story-scoped: target.id is the STORY key, not an asset id (no STORY target kind in v0.3.1; v0.3.2 candidate)"
                        : ""),
                ["recorded_at"] = now.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'"),
            };

            var auditEnvelope = new JsonObject
            {
                ["som_version"] = "0.2.0",
                ["message_id"] = Guid.NewGuid().ToString(),
                // Thread the staged output's lifecycle: same correlation, caused by the staged message.
                ["correlation_id"] = envelope?["correlation_id"] is JsonValue cv && cv.TryGetValue<string>(out var corr) ? corr : Guid.NewGuid().ToString(),
                ["message_type"] = "system.audit",
                ["timestamp"] = now.UtcDateTime.ToString("yyyy-MM-dd'T'HH:mm:ss.ffffff'Z'"),
                ["originating_system"] = new JsonObject
                {
                    ["system_id"] = "ibc-poc-dashboard",
                    ["system_type"] = "editorial_dashboard",
                    ["system_name"] = "Staging Dashboard (human approval gate)",
                    ["vendor"] = "ibc-poc",
                    ["version"] = "0.1",
                },
                ["topic"] = _options.AuditTopic,
                ["payload"] = auditPayload,
            };
            if (envelope?["message_id"] is JsonValue mv && mv.TryGetValue<string>(out var causation))
                auditEnvelope["causation_id"] = causation;

            // Deliberately no cancellation token: this is post-commit work and must not be
            // abandonable; the producer's 10s MessageTimeoutMs bounds it.
            await _producer.ProduceAsync(_options.AuditTopic,
                new Message<string, string> { Key = pending.StoryKey ?? pending.OutputId, Value = auditEnvelope.ToJsonString() });
            _logger.LogInformation(
                "Dashboard: decision audit {Action} for output {OutputId} recorded on {Topic} (reviewer {Reviewer})",
                action, pending.OutputId, _options.AuditTopic, reviewer);
        }
        catch (Exception ex)
        {
            // Same posture as MediaCoordinator's WITHHELD path: if the audit can't be
            // recorded, say exactly that — the decision stands but is unrecorded. No OCE
            // carve-out: with no token in play, cancellation isn't a legitimate signal
            // here, and letting one escape would skip this log and the caller's broadcast.
            _logger.LogError(ex,
                "Dashboard: decision audit {Action} for output {OutputId} could NOT be confirmed on {Topic} — the clearance may exist only in topic annotations",
                action, pending.OutputId, _options.AuditTopic);
        }
    }

    /// <summary>
    /// Map a staged output onto the locked audit target set (LINK | ASSET | TELLING), most
    /// specific tier first: an explicit link:/asset: scope wins; else any affected_fields
    /// path "assets.{id}.…" names the asset; else a bare "assets"/"assets[]…" field
    /// resolves through the story cache when the story has exactly ONE asset (multi-asset
    /// stories stay story-scoped — precise per-asset anchors arrive with the firing-anchor
    /// upgrade). Story-scoped remainder returns StoryFallback=true: v0.3.1 has no STORY
    /// target kind (v0.3.2 candidate), so the caller must label the id as a story key.
    /// </summary>
    private (string Kind, string Id, bool StoryFallback) ResolveAuditTarget(JsonObject? payload)
    {
        var scope = payload?["scope"] is JsonValue scv && scv.TryGetValue<string>(out var sc) ? sc : null;
        if (scope is not null && scope.StartsWith("link:", StringComparison.Ordinal))
            return ("LINK", scope["link:".Length..], false);
        if (scope is not null && scope.StartsWith("asset:", StringComparison.Ordinal))
            return ("ASSET", scope["asset:".Length..], false);

        var storyId = payload?["story_id"] is JsonValue sv2 && sv2.TryGetValue<string>(out var s2) ? s2 : null;

        if (payload?["affected_fields"] is JsonArray fields)
        {
            var sawBareAssets = false;
            foreach (var field in fields)
            {
                if (field is not JsonValue fv || !fv.TryGetValue<string>(out var f)) continue;
                var parts = f.Split('.');
                if (parts[0] == "assets" && parts.Length >= 2 && parts[1].Length > 0)
                    return ("ASSET", parts[1], false);
                if (parts[0] is "assets" or "assets[]") sawBareAssets = true;
            }
            if (sawBareAssets && SingleAssetIdFor(storyId) is { } onlyAsset)
                return ("ASSET", onlyAsset, false);
        }

        return ("ASSET", storyId ?? "unknown", true);
    }

    /// <summary>The story's asset_id iff the cached story has exactly one asset — the only
    /// case where a bare "assets" affected-field pins to an asset without guessing.</summary>
    private string? SingleAssetIdFor(string? storyId)
    {
        if (storyId is null || !_stories.TryGetValue(storyId, out var node)) return null;
        var story = (node as JsonObject)?["payload"] as JsonObject ?? node as JsonObject;
        if (story?["assets"] is not JsonArray { Count: 1 } assets) return null;
        return assets[0] is JsonObject a && a["asset_id"] is JsonValue v && v.TryGetValue<string>(out var id) ? id : null;
    }

    private sealed record PendingOutput(
        string OutputId,
        string? StoryKey,
        JsonNode Output,
        DateTimeOffset StagedAt);

    public sealed record DecisionResult(bool Ok, string Status, string? PublishedTopic);
}
