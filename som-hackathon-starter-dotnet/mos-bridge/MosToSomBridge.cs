using System.Text.Json.Nodes;
using System.Xml.Linq;

namespace SomSkillWorker.MosBridge;

/// <summary>
/// SCAFFOLD — MOS v4.0 → SOM v0.3.1 translator (ingest direction only).
///
/// Pure translation functions: parse a MOS XML message and return the SOM message(s)
/// the bridge would publish. No transport wiring (Kafka/WebSocket) — wire these into a
/// host service when integrating. See mos-bridge/README.md for the message map and the
/// companion spec "SOM ↔ MOS Bridge — Compatibility & Migration (v0.3.1)".
///
/// Object-model mapping (spec §3): NCS→originating_system, Running Order→Destination,
/// RO Story→story.context + a link, RO Item/object→Asset + link, MEM→extensions.
///
/// [PENDING] Fields/records that depend on the v0.3.1 Destination + rundown_context
/// shape (not yet ratified — 30 June lock) are marked PENDING inline. They are emitted
/// on a best-effort basis and finalise with the schema lock.
/// </summary>
public static class MosToSomBridge
{
    private const string SomVersion = "0.2.0";   // wire version until v0.3 ratifies (SOM-048)
    private const string BridgeId   = "mos-bridge-london-01";

    /// <summary>Top-level dispatch: MOS message element → the SOM messages to publish.</summary>
    public static IEnumerable<JsonObject> Translate(XElement mos, string correlationId)
    {
        switch (mos.Name.LocalName)
        {
            // Running-order create/replace → Destination + a story.context + link per story.
            case "roCreate":
            case "roReplace":
                foreach (var msg in TranslateRunningOrder(mos, correlationId)) yield return msg;
                break;

            // Story placed/sent into the rundown → story.context + link.committed.
            case "roStorySend":
            case "roStoryInsert":
            case "roStoryAppend":
            case "roStoryReplace":
                foreach (var msg in TranslateStory(mos, RoId(mos), correlationId)) yield return msg;
                break;

            // Reorder → position update on the link.
            case "roStoryMove":
                yield return Envelope("link.gate_changed", "som.link.gate_changed", correlationId,
                    LinkPayload(StoryId(mos), DestinationId(RoId(mos)), "PENDING")); // position carried in rundown_context [PENDING]
                break;

            // Story removed from the rundown → withdraw the link (the Story/Asset persist).
            case "roStoryDelete":
                yield return Envelope("link.withdrawn", "som.link.withdrawn", correlationId,
                    WithdrawPayload(StoryId(mos), DestinationId(RoId(mos)), "Removed from running order"));
                break;

            // Ready-to-air → lifecycle transition (decision #19).
            case "roReadyToAir":
                yield return Envelope("story.context", $"som.story.{StoryId(mos)}", correlationId,
                    new JsonObject
                    {
                        ["story_id"] = StoryId(mos),
                        ["story_type"] = "ACTIVE",
                        ["lifecycle"] = new JsonObject { ["phase"] = "READY_TO_AIR", ["phase_entered_at"] = Now() },
                    });
                break;

            // Unified element op — dispatch on the action verb (spec §4).
            case "roElementAction":
                foreach (var msg in TranslateElementAction(mos, correlationId)) yield return msg;
                break;

            // Liveness.
            case "heartbeat":
            case "keepAlive":
                yield return Envelope("system.health", "som.system.health", correlationId,
                    new JsonObject { ["status"] = "ALIVE", ["bridge_id"] = BridgeId });
                break;

            // Catalogue/query traffic and ACKs are bridge-internal: emit nothing.
            default:
                yield break;
        }
    }

    // ─── Running order → Destination + stories ──────────────────────────────
    private static IEnumerable<JsonObject> TranslateRunningOrder(XElement ro, string cid)
    {
        var roId = RoId(ro);
        // [PENDING Destination] — emitted illustratively; Destination + rundown_context
        // shapes finalise with the v0.3.1 lock. See README.
        yield return Envelope("destination.upserted", "som.destination.upserted", cid, new JsonObject
        {
            ["destination_id"] = DestinationId(roId),
            ["platform"] = "LINEAR",
            ["rundown_context"] = new JsonObject
            {
                ["ro_id"] = roId,
                ["ro_slug"] = (string?)ro.Element("roSlug") ?? roId,
                ["channel"] = (string?)ro.Element("roChannel"),
            },
        });

        foreach (var story in ro.Elements("story"))
            foreach (var msg in TranslateStory(story, roId, cid)) yield return msg;
    }

    // ─── RO story → story.context (+ link.committed for its placement) ───────
    private static IEnumerable<JsonObject> TranslateStory(XElement story, string roId, string cid)
    {
        var storyId = (string?)story.Element("storyID") ?? StoryId(story);
        var slug    = (string?)story.Element("storySlug") ?? storyId;

        // A rundown story is PLANNED until it goes ACTIVE — no lifecycle block (decision #19).
        yield return Envelope("story.context", $"som.story.{storyId}", cid, new JsonObject
        {
            ["story_id"] = storyId,
            ["slug"] = slug,
            ["headline"] = (string?)story.Element("storySlug") ?? slug,
            ["story_type"] = "PLANNED",
            ["sequence_number"] = 1,
            ["updated_at"] = Now(),
            ["newsroom_id"] = "nbc-news",
            ["extensions"] = MosExtension(roId, storyId),
        });

        // Its placement in the running order is a committed link.
        yield return Envelope("link.committed", "som.link.committed", cid,
            LinkPayload(storyId, DestinationId(roId), "PENDING"));
    }

    // ─── roElementAction → link event by verb ───────────────────────────────
    private static IEnumerable<JsonObject> TranslateElementAction(XElement ea, string cid)
    {
        var op = ((string?)ea.Attribute("operation") ?? "").ToUpperInvariant();
        var storyId = StoryId(ea);
        var destId  = DestinationId(RoId(ea));
        switch (op)
        {
            case "INSERT":
                yield return Envelope("link.committed", "som.link.committed", cid,
                    LinkPayload(storyId, destId, "PENDING"));
                break;
            case "MOVE":
            case "REPLACE":
            case "SWAP":
                yield return Envelope("link.gate_changed", "som.link.gate_changed", cid,
                    LinkPayload(storyId, destId, "PENDING"));
                break;
            case "DELETE":
                yield return Envelope("link.withdrawn", "som.link.withdrawn", cid,
                    WithdrawPayload(storyId, destId, $"roElementAction {op}"));
                break;
        }
    }

    // ─── Payload + envelope builders ────────────────────────────────────────
    private static JsonObject LinkPayload(string assetOrStoryId, string destId, string gate) => new()
    {
        ["message_type"] = "link.committed",
        ["link_id"] = Guid.NewGuid().ToString(),
        ["asset_id"] = assetOrStoryId,
        ["destination_id"] = destId,
        ["committed_by"] = BridgeId,
        ["committed_at"] = Now(),
        ["compliance_gate_status"] = gate, // PENDING → resolved by SOM compliance skills, not the bridge
    };

    private static JsonObject WithdrawPayload(string assetOrStoryId, string destId, string reason) => new()
    {
        ["message_type"] = "link.withdrawn",
        ["link_id"] = Guid.NewGuid().ToString(),
        ["asset_id"] = assetOrStoryId,
        ["destination_id"] = destId,
        ["compliance_gate_status"] = "BLOCKED",
        ["withdrawn"] = new JsonObject
        {
            ["withdrawn_by"] = BridgeId,
            ["withdrawn_at"] = Now(),
            ["reason"] = reason,
        },
    };

    /// <summary>
    /// SOM v0.3.1 envelope. Identity reconciled (spec §7): the bridge is the
    /// originating_system; the MOS device identity rides in extensions, NOT the
    /// envelope. Message signing was removed in the #18 envelope lock — no signature.
    /// </summary>
    private static JsonObject Envelope(string messageType, string topic, string correlationId, JsonObject payload) => new()
    {
        ["som_version"] = SomVersion,
        ["message_id"] = Guid.NewGuid().ToString(),
        ["correlation_id"] = correlationId,
        ["message_type"] = messageType,
        ["timestamp"] = Now(),
        ["originating_system"] = new JsonObject
        {
            ["system_id"] = BridgeId,
            ["system_type"] = "ncs",
            ["system_name"] = "MOS-SOM Bridge",
            ["vendor"] = "NBCU",
        },
        ["topic"] = topic,
        ["payload"] = payload,
    };

    private static JsonObject MosExtension(string roId, string storyId) => new()
    {
        ["com.som.mos-bridge"] = new JsonObject
        {
            ["bridge_id"] = BridgeId,
            ["ro_id"] = roId,
            ["mos_story_id"] = storyId,
        },
    };

    // ─── Helpers ────────────────────────────────────────────────────────────
    private static string Now() => DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.ffffffZ");
    private static string RoId(XElement e) => (string?)e.Element("roID") ?? (string?)e.Attribute("roID") ?? "ro-unknown";
    private static string StoryId(XElement e) => (string?)e.Element("storyID") ?? (string?)e.Attribute("storyID") ?? "story-unknown";
    private static string DestinationId(string roId) => $"d-{roId.ToLowerInvariant()}";
}
