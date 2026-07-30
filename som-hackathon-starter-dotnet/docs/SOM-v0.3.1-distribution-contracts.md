# SOM v0.3.1 — Distribution-Layer Message Contracts

_Service: `som-hackathon-starter-dotnet` · schema pack: [`schema/v0.3.1-proposed/`](../schema/v0.3.1-proposed/) · companion to [`message-contracts.md`](./message-contracts.md) (skill outputs) and [`som-v02-envelope.md`](./som-v02-envelope.md) (envelope)._

This is the partner-facing reference for the **v0.3.1 distribution layer** — the message families that sit under `som.link.*`, `som.telling.*`, `som.delivery.*`, and `som.system.*`. For each family: the topic, the JSON Schema, one canonical example, and which IBC demo beat it proves. Every payload here validates against the vendored schemas via [`schema/validate.py`](../schema/validate.py).

> **Schema vs producer status.** All the schemas below are **ratified v0.3.1** and safe to build against. The reference implementation covers them unevenly — `som.delivery.media_available` has a mock producer (`MockMamService`) **and a reference consumer** (`MediaCoordinatorService`, which flips `acquisition_state` on capture-complete and records `WITHHELD` audits for unmatched arrivals); `som.system.audit` has **two** live producers (the coordinator's `WITHHELD` non-actions and the dashboard's human gate decisions — approve → `CLEARED`, reject → `WITHHELD`); `som.link.*` and `som.telling.*` are the 6 Aug hackathon build (WS1). "Producer" columns say which is which. The contract is stable regardless of implementation status — integrate against the schema.

---

## Envelope (all messages)

Every message on every topic is a JSON **envelope** wrapping a typed `payload`. The example files in [`schema/v0.3.1-proposed/examples/`](../schema/v0.3.1-proposed/examples/) show the **payloads only** (that is what the schemas validate); on the wire each is wrapped like this:

```json
{
  "som_version": "0.2.0",
  "message_id": "<uuid>",
  "correlation_id": "<uuid>",
  "message_type": "delivery.media_available",
  "timestamp": "2026-06-12T09:30:00.000000Z",
  "originating_system": {
    "system_id": "mock-mam",
    "system_type": "archive",
    "system_name": "Mock MAM (TAMS stand-in for IBC PoC)",
    "vendor": "ibc-poc",
    "version": "0.1"
  },
  "topic": "som.delivery.media_available",
  "payload": { "...": "the typed payload — schema-validated" }
}
```

Envelope rules that bite integrators:
- **`som_version` stays `"0.2.0"`** even though payloads are v0.3.1-shaped. The wire version does not bump until v0.3 ratifies on the wire (tracked as SOM-048). This is deliberate — don't gate on it.
- **`correlation_id` is required** and MUST be threaded end-to-end so a downstream event can be traced to the story/action that caused it.
- **`timestamp` lives on the envelope, never in the payload** (decision #18). There is no `signature` field (removed, #18).
- `originating_system` replaces the old `source` envelope field (#4.1). `system_type` is from the v0.3 enum (`ncs`, `archive`, `automation`, `skill_worker`, …) — note the newsroom system value is **`ncs`**, there is no `newsroom` value.

---

## Topic reference

| Topic | Message types | Producer | Consumer | Status |
|---|---|---|---|---|
| `som.story.context` | `story.context` | AP / TestProducer | SkillWorker, Dashboard | ✅ live |
| `som.skills.staging` | `skill.warning.raised`, `skill.suggestion.created` | SkillWorker | Dashboard (Pending lane) | ✅ live |
| `som.skills.events` | approved skill outputs | Dashboard (approve) | downstream | ✅ live |
| `som.skills.rejected` | rejected skill outputs | Dashboard (reject) | audit | ✅ live |
| `som.skills.runs` | `skill.run.completed` | SkillWorker | Dashboard (audit) | ✅ live |
| `som.delivery.media_available` | `delivery.media_available` | MockMamService (TAMS stand-in) | MediaCoordinatorService (reference consumer) | 🟡 mock producer + reference consumer |
| `som.link.committed` · `.gate_changed` · `.withdrawn` | `link.committed`, `link.gate_changed`, `link.withdrawn` | (WS1) | (WS1) → maintains `usage[]` | ⏳ schema ready, Aug build |
| `som.telling.started` · `.ended` · `.exposed` | `telling.started`, `telling.ended`, `telling.exposed` | (WS1) | (WS1) → derives on-air state | ⏳ schema ready, Aug build |
| `som.system.audit` | `system.audit` | MediaCoordinatorService (`WITHHELD` non-actions) · Dashboard (gate decisions `CLEARED`/`WITHHELD`) · (WS1 for the rest) | audit / dashboard | 🟡 two producers live |

Message-type names are the **suffixed** forms on the wire (e.g. `skill.warning.raised`, not `skill.warning`).

---

## `som.delivery.media_available` — the TAMS junction

**Topic:** `som.delivery.media_available` · **Schema:** [`som-v0.3.1-delivery-media-available.schema.json`](../schema/v0.3.1-proposed/som-v0.3.1-delivery-media-available.schema.json)

Announces that media has **arrived in (or is growing inside) a TAMS/MAM store**. This is the MAM→bus junction and nothing more — SOM never queries the MAM. `source` **MUST** be a fully-qualified TAMS Source URI (`tams://store/id`), re-keyed 29 Jun from the old `flow_id`. A recording that is still being captured is addressable: emit repeatedly with a **growing** `time_range`.

```json
{
  "message_type": "delivery.media_available",
  "delivery_id": "0190a000-0000-7000-8000-00000000aaa1",
  "asset_id": "a2",
  "source": "tams://tams-gcp-store/9f2e7c1a",
  "time_range": "[0:0_134:0)",
  "arrived_in": "tams-gcp-store",
  "arrived_at": "2026-06-12T09:30:00Z"
}
```

- `source` resolves to the same Source referenced by the asset's `story.context` → `assets[].media_refs[].source`, so the arrival event joins back to the asset. No `story_id` copy — resolve the story through `asset_id`.
- `time_range` is a TAMS timerange (or list): bracketed `seconds:nanoseconds` bounds, e.g. `[0:0_134:0)`. Open-ended start/end permitted.
- **Proves:** D1·B5 — media-arrival without a MAM participant. Drive it locally with the `media-arrival` simulator scenario, the Mock MAM panel in the dashboard's Simulator modal, or `POST /api/mam/emit/{sourceId}`.

**What consumers do with it.** The event is an availability handshake — pub/sub, no orchestration. The reference consumer (`MediaCoordinatorService`) demonstrates the canonical reactions: a known asset's story is republished with `acquisition_state: CAPTURING → CAPTURED` when the arrival carries the capture-complete extension (below), rolling arrivals are noted without a state change, and an arrival matching **no** story yields a `WITHHELD` record on `som.system.audit` — never a new story (story-from-media is the v0.3.2 ORPHAN direction). "Capture finished" is not a first-class v0.3.1 delivery field, so the reference implementation carries it exactly the way partners are told to carry their own pre-ratification concepts:

```json
"extensions": { "com.ibc-poc.capture_complete": true }
```

**After the announcement — fetching the bytes.** The delivery event says the essence is reachable; it carries no credentials and no bytes. Retrieval is a store concern below the SOM boundary: authenticate to the TAMS store and read via its API — for this PoC's GCP deployment see [`tams/DEVELOPER_AUTH_GUIDE.md`](../../tams/DEVELOPER_AUTH_GUIDE.md) at the repo root. SOM never proxies media.

**Cold consumers — resolving `asset_id` with no cached story.** The event deliberately carries no `story_id`; you resolve `asset_id → Asset → Story` from `story.context`. A consumer that joins late has three options, in preference order: (1) replay `som.story.context` from the earliest retained offset and keep the latest version per `story_id` (what this starter's dashboard does); (2) hold the arrival briefly — stories republish in full on every change, so the next version is rarely far away (the reference coordinator re-checks for ~1s); (3) after a bounded wait, treat it as unmatched (the coordinator then records the `WITHHELD` audit). There is no story query API in v0.3.1 — resolution is stream-first by design.

**Who emits on the shared dev broker.** The shared dev server runs the **broker only** — no vendor code, no mock MAM. `MockMamService` runs inside whichever participant runs the starter (locally, pointed at the shared broker). A consumer-only partner who sees no delivery traffic isn't broken — nobody is emitting; run the starter yourself or agree on who drives the scenario.

**Not the right carrier for a public livestream URL you want to transcribe** — that is a *live ingest source*, not arrived TAMS media. See [Vendor extensions](#vendor-extensions--adding-fields-without-breaking-the-spec) for how to carry an ingest URL today.

---

## `som.link.*` — Asset ↔ Destination

**Topics:** `som.link.committed` · `som.link.gate_changed` · `som.link.withdrawn` · **Schema:** [`som-v0.3.1-link-event.schema.json`](../schema/v0.3.1-proposed/som-v0.3.1-link-event.schema.json)

A **link** is the connection between an Asset and a Destination (decision #3). `story.context` → `assets[].usage[]` is maintained **only** from these events, under the §5 idempotent-upsert rules (committed-only, fail-closed). `compliance_gate_status` is **per-destination** — the same asset can be `CLEARED` on a digital link and `BLOCKED` on a broadcast link at the same time.

```json
{
  "message_type": "link.committed",
  "link_id": "0190a000-0000-7000-8000-00000000aaa1",
  "asset_id": "a1",
  "destination_id": "d1",
  "committed_by": "producer-7",
  "committed_at": "2026-06-12T10:00:00Z",
  "compliance_gate_status": "PENDING"
}
```

- `link.committed` requires `committed_by` + `committed_at`; `link.withdrawn` requires a `withdrawn` object (`withdrawn_by`, `withdrawn_at`, optional `reason`) and only withdrawn may carry it; `link.gate_changed` carries the new `compliance_gate_status`.
- **Proves:** D1·B4 Reach (digital `CLEARED` while broadcast `BLOCKED`); D2·B2 partial fire.

---

## `som.telling.*` — on-air state (derived, never stored)

**Topics:** `som.telling.started` · `som.telling.ended` · `som.telling.exposed` · **Schema:** [`som-v0.3.1-telling-event.schema.json`](../schema/v0.3.1-proposed/som-v0.3.1-telling-event.schema.json)

On-air state is **derived from the Telling stream**, never stored on the asset — this is why `asset.status` has no `LIVE`/`AIRED` value (#16). `exposure_start`/`exposure_end` are immutable and event-stamped; `scheduled_start` is mutable intended-air and is **never** used to derive on-air state.

```json
{
  "message_type": "telling.started",
  "telling_id": "0190a000-0000-7000-8000-00000000aaa2",
  "link_id": "0190a000-0000-7000-8000-00000000aaa1",
  "exposure_start": "2026-06-12T18:00:00Z",
  "scheduled_start": "2026-06-12T18:00:00Z"
}
```

- `telling.started` requires `exposure_start` and MUST NOT carry `exposure_end`; `telling.ended` requires `exposure_end`; `telling.exposed` (instantaneous) requires both, with `exposure_start == exposure_end`.
- `link_id` references the link this Telling followed from — referenced, not duplicated.

---

## `som.system.audit` — governance trail

**Topic:** `som.system.audit` · **Schema:** [`som-v0.3.1-system-audit.schema.json`](../schema/v0.3.1-proposed/som-v0.3.1-system-audit.schema.json)

The clearance/suppression audit trail. Distinct from `som.skills.runs` (which records skill executions). A **suppression targets the held ASSET** — the non-airing branch never gets a link, so the audit points at the asset, not a link.

```json
{
  "audit_id": "0190e000-0008-7000-8000-0000000000f3",
  "action": "SUPPRESSED",
  "target": { "kind": "ASSET", "id": "pkg-acquit" },
  "actor": { "actor_id": "automation-01", "actor_type": "system" },
  "reason": "Acquit package suppressed; never linked to air",
  "recorded_at": "2026-06-23T14:30:02.000000Z"
}
```

- `action` ∈ `CLEARED` · `SUPPRESSED` · `WITHHELD` · `OVERRIDDEN`. `target.kind` ∈ `LINK` · `ASSET` · `TELLING`.
- **Proves:** D2·B3 clearance/suppression trail. `WITHHELD` also carries the "safe-state stop / non-action report" from the skills-model work — any actor, system **or human**, records that it declined to act.

**Live producers today.** The media coordinator (`WITHHELD` on unmatched arrivals — the system safe-state stop) and the dashboard's human gate (**approve → `CLEARED`**, **reject → `WITHHELD`**, `actor_type: "user"`, `causation_id` = the staged output's `message_id`). A human reject is `WITHHELD`, not `SUPPRESSED`, by decision: rejection is **terminal for that output instance** (a re-run mints a new output) — "no outstanding decision changes this" — whereas `SUPPRESSED` is about held *content* never linked to air. WS1 (Aug) adds the remaining producers.

**Target mapping for gate decisions.** A staged output maps onto the locked `LINK | ASSET | TELLING` set most-specific-first: an explicit `link:{id}`/`asset:{id}` scope wins; else an `assets.{id}.…` affected-field names the asset; else a bare `assets` affected-field resolves through the story cache when the story has exactly **one** asset. A **story-scoped** decision has no honest home in the locked set — the record ships `kind: ASSET` carrying the **story** key and says so explicitly in `reason`. Consumers MUST NOT join such an id against assets; a `STORY` target kind is a v0.3.2 candidate.

Partition keys are mixed on this topic by design — the coordinator keys audits by **asset id**, the dashboard by **story key**. Do not rely on per-key ordering across producers.

---

## Vendor extensions — adding fields without breaking the spec

Anything outside the canonical schema rides under `payload.extensions.com.{vendor}.{field}` (reverse-DNS short form, e.g. `com.trint.*`, `com.nbcu.*`). Consumers that don't recognise a key MUST ignore it silently. Anything that later graduates to the spec drops its `com.{vendor}.` prefix. This is the **designed** place for the improvisations partners need before a concept is ratified — using it is correct, not a workaround.

Two current partner patterns and their recommended homes:

| Need | Today (spec-legal) | Target-state direction |
|---|---|---|
| **Livestream URL to transcribe** (a live ingest source, not arrived stored media) | `extensions.com.{vendor}.livestream_url` on `story.context` | To be **proposed** as a first-class "live ingest source" field in the v0.3.2 window — not yet in the v0.3.2 scaffold. Its natural companion IS already drafted there: locator-on-arrival generalises `delivery.media_available` beyond TAMS (`anyOf(source \| locator)`, mirroring `media_refs[]`). |
| **"Monitor for X" directive** (e.g. "casualty figures") — a skill/task parameter | `extensions.com.{vendor}.monitor_prompt` on `story.context` | First-class **skill directive / task parameter** — part of the skills-model alignment work (declared skill conditions + parameters). |
| **"Capture finished" signal** on a delivery event | `extensions.com.ibc-poc.capture_complete` on `delivery.media_available` — **live in this repo**: the mock MAM emits it, the media coordinator acts on it | Candidate first-class delivery field alongside locator-on-arrival; until then it's the working example of the extension mechanism |

Example on a `story.context` payload:

```json
"extensions": {
  "com.trint.livestream_url": "https://example.com/live/hurricane-report.m3u8",
  "com.trint.monitor_prompt": "casualty figures"
}
```

---

## Demo beat → topic map

| Demo beat | Topic(s) | Message type(s) |
|---|---|---|
| D1·B4 Reach (digital CLEARED / broadcast BLOCKED) | `som.link.*` | `link.committed`, `link.gate_changed` |
| D1·B5 Media junction (TAMS) | `som.delivery.media_available` | `delivery.media_available` |
| D2·B2 Partial fire (one link fires, not the other) | `som.link.*` + `som.skills.staging` | `link.gate_changed`, `skill.warning.raised` |
| D2·B3 Clearance / suppression trail | `som.system.audit` | `system.audit` |
| On-air state (any beat that airs) | `som.telling.*` | `telling.started`, `telling.ended` |

---

## Where the schemas live in GitHub — and how to pin them

`som-hackathon-starter-dotnet/schema/v0.3.1-proposed/` on this repo — five schemas plus one valid example per message type under `examples/`. Validate any instance locally with `python3 schema/validate.py`.

**Pinning note:** the content is ratified (locked 30 Jun + 15-Jul errata), but the folder name and `$id` still carry a historical `-proposed` segment. Both are promoted **once**, at the **`schema-lock-v0.3.1-errata1`** tag — **pin that tag, not the path**. Nothing about the shapes changes at promotion.
