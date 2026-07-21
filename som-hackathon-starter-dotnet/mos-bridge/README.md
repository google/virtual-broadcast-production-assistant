# MOS ↔ SOM Bridge — sample adapter (scaffold)

Reference scaffold for translating **MOS v4.0 → SOM v0.3.1** so brownfield MOS newsrooms can join the SOM bus incrementally. Ingest direction only (MOS → SOM); the reverse (SOM driving a MOS rundown) is a v0.4 candidate.

Companion spec: **"SOM ↔ MOS Bridge — Compatibility & Migration (v0.3.1)"** in the SOM spec folder. Read §3 (object-model mapping) and §4 (message map) alongside this code.

## What's here

| File | Purpose |
|---|---|
| `MosToSomBridge.cs` | Pure translator: `Translate(XElement mos, string correlationId)` → the SOM message(s) to publish. No transport wiring. |
| `samples/roCreate.xml` | A sample MOS v4.0 running-order create. |
| `samples/story.context.expected.json` | SOM `story.context` the bridge emits (validated against the v0.3.1 schema). |
| `samples/link.committed.expected.json` | SOM `som.link.committed` the bridge emits (validated). |

The two `expected` fixtures are **validated against the v0.3.1 JSON Schemas** (`schema/v0.3.1-proposed`) and serve as golden outputs.

## Object-model mapping (the key idea)

A MOS **Running Order is a SOM `Destination`**, and a story's place in it is a **`link`** — not a property of the story.

```
NCS (ncsID)            → originating_system (system_type: ncs)
Running Order (roID)   → Destination + rundown_context      [PENDING shape]
RO Story (storyID)     → story.context  +  link (placement)
RO Item / Object       → Asset          +  link
mosExternalMetadata    → extensions.com.{vendor}.*
```

## Message map (implemented in `Translate`)

| MOS v4.0 | SOM v0.3.1 |
|---|---|
| `roCreate` / `roReplace` | `Destination` upsert + `story.context` per story + `link.committed` per placement |
| `roStorySend/Insert/Append/Replace` | `story.context` + `link.committed` |
| `roStoryMove` | `link.gate_changed` (position) |
| `roStoryDelete` | `link.withdrawn` |
| `roReadyToAir` | `story.context` lifecycle `READY_TO_AIR` |
| `roElementAction` INSERT/MOVE/REPLACE/SWAP/DELETE | `link.committed` / `link.gate_changed` / `link.withdrawn` |
| `heartbeat` / `keepAlive` | `som.system.health` |
| `mosReq*` / `mosAck` (queries, ACKs) | — (bridge-internal) |

## Identity & trust (reconciled to v0.3.1)

- The bridge is the `originating_system`; the **MOS device identity rides in `extensions.com.som.mos-bridge`**, not the envelope (`source` → `originating_system`, #4.1).
- **No message signing** — the `signature` field was removed in the #18 envelope lock. Integrity rides `modification_header` + `som.system.audit` + `correlation_id`/`causation_id`; transport security (mTLS/ACLs) is a deployment concern.
- The bridge **MUST NOT** increment `story_version`; it echoes the NCS's.

## PENDING (waiting on the 30 June v0.3.1 lock)

- **`Destination` + `rundown_context`** are not yet ratified — the `destination.upserted` emission and `rundown_context` fields are best-effort and finalise with the lock.
- `compliance_gate_status` is emitted `PENDING`; SOM compliance **skills** (not the bridge) drive it to `CLEARED`/`BLOCKED`.

## Wiring it up

`MosToSomBridge` is transport-free by design. To run it live: parse inbound MOS (WebSocket for v4.0, TCP for v2.8.5) into `XElement`, call `Translate(...)`, and publish each returned `JsonObject` to its `topic` via the same Kafka producer the worker uses (`KafkaOptions`). This is left unwired in the scaffold.
