# SOM Hackathon Starter — User Guide

_The front door for hackathon participants and vendors. This guide takes you from zero to driving the full SOM loop and building your own skill, and tells you which reference doc to open when you need depth. Nothing here replaces the schemas — when this guide and a schema disagree, the schema wins._

**The documentation map** — where everything lives:

| You want… | Read |
|---|---|
| This journey, start to finish | **this guide** |
| Setup, run modes, config, deployment | [`../README.md`](../README.md) |
| Every dashboard control and lane | [`dashboard-guide.md`](./dashboard-guide.md) |
| The distribution-layer message contracts (delivery / link / telling / audit) + envelope rules | [`SOM-v0.3.1-distribution-contracts.md`](./SOM-v0.3.1-distribution-contracts.md) |
| The skill-output message contracts (warnings, runs) | [`message-contracts.md`](./message-contracts.md) |
| Skill validation (static / dry-run / AI review) in depth | [`skill-validation.md`](./skill-validation.md) |
| System architecture | [`architecture.md`](./architecture.md) |
| The JSON Schemas themselves (source of truth) | [`../schema/`](../schema/) — validate anything with `python3 schema/validate.py` |

---

## 1. The big picture — SOM in five minutes

**SOM (Story Object Model)** is an open JSON pub/sub standard for sharing *story context* across every tool in a newsroom — NRCS, MAM, transcription, graphics, compliance, playout. Instead of point-to-point integrations, every system reads and writes typed messages on a message bus. (SOM itself is transport-agnostic; **Kafka is this starter's transport**, so "topic" here means a Kafka topic.)

The core loop this starter demonstrates:

```
 NRCS / seed button                    you (the editor)
        │ story.context                       │ approve / reject
        ▼                                     ▼
   som.story.context ──► SkillWorker ──► som.skills.staging ──► Dashboard ──┬─► som.skills.events
                            │                                               └─► som.skills.rejected
                            └────────► som.skills.runs (audit)
```

- A **story** is published as a `story.context` snapshot — the full editorial state (headline, lifecycle phase, compliance flags, assets, sources) every time it changes.
- **Skills** are passive, data-driven automations (a compliance check, a style check). An **executor** (the `SkillWorker` here) watches the bus, works out which skills apply, and runs their rules against each snapshot.
- Skill outputs go to a **staging** topic and wait for a **human decision** — nothing reaches the production bus without approval. That gate is the dashboard.
- Every message is wrapped in a **SOM envelope** (`som_version`, `message_id`, `correlation_id`, `message_type`, `timestamp`, `originating_system`, `topic`, `payload`) — including the starter's own seed publishes. Five rules bite integrators — see [§7](#7-integrating-your-own-system). (Consumers here also tolerate bare payloads from producers still on the old v0.2 shortcut, but publish full envelopes from yours.)

On top of the core loop sits the **distribution layer** (v0.3.1): media arrivals (`som.delivery.media_available`), asset-to-destination links (`som.link.*`), on-air state (`som.telling.*`), and the governance trail (`som.system.audit`). This starter runs the delivery + audit halves live; link/telling are the August build.

## 2. Getting running

Short version (full detail: [README quick start](../README.md#quick-start)):

```bash
cd som-hackathon-starter-dotnet
docker compose up -d     # Kafka + Kafka UI (:8080)
dotnet run               # everything else — dashboard on :5050
```

**Verify your setup in 60 seconds:**

1. Open http://localhost:5050 — the ws pill (top right) should say **connected**.
2. Click the **Informal** seed button — a story lands in *Stories on Bus*, two style warnings appear in *Pending Approval* within a second or two.
3. Approve one, reject the other — both show up in *Decisions*, and the bus event log (bottom) shows the full message trail.

If any step fails, see [Troubleshooting](#9-troubleshooting).

## 3. The dashboard in one paragraph

Four lanes left-to-right mirror the loop: **Stories on Bus** (latest version of each story) → **Skill Runs** (every execution, with latency and outcome) → **Pending Approval** (staged outputs awaiting your call) → **Decisions**. The **bus event log** at the bottom shows every message on every topic, filterable by topic chip. Three separate surfaces generate traffic: the **seed buttons** (one-shot story publishes), the **Simulator** (tabs for scripted scenarios / mock MAM / auto-stream), and the **per-story Lifecycle panel** (click a story card to mutate that story). Full tour: [`dashboard-guide.md`](./dashboard-guide.md).

## 4. The story lifecycle

- `story_type: ACTIVE` stories carry a `lifecycle.phase`: `DEVELOPING → READY_TO_AIR → BREAKING → PUBLISHED` (only ACTIVE stories have a lifecycle block — that's a schema rule, not a convention).
- A story is **republished in full** every time it changes — `sequence_number` increments, `updated_at` moves. Consumers keep the latest version per `story_id`; there are no deltas.
- Skills re-run on **every** new version. That's what makes mutation demos work: advance a phase or add a compliance flag in the Lifecycle panel and watch the skills fire again against the new snapshot.
- `correlation_id` threads every message about one story lifecycle together — skill outputs echo the inbound envelope's correlation id, and republished story versions keep it (each republish gets a fresh `message_id`/`timestamp` but the same correlation). Follow one story's traffic in the bus event log and you'll see the whole chain share it.

## 5. Media and the TAMS junction

The starter models the v0.3.1 media story end to end (this is demo beat D1·B5):

- An **asset** on a story can reference stored media by a TAMS Source URI: `assets[].media_refs[] = { source: "tams://store/id", time_range: "[0:0_134:0)" }`. A feed still being recorded has `acquisition_state: CAPTURING` and an **open-ended** range `[0:0_)`.
- When media actually arrives in (or grows inside) a store, the store announces it: **`som.delivery.media_available`** — the availability handshake. It carries `source` + `asset_id` + `time_range`, never a `story_id`; the story is resolved by walking `asset_id → Asset → Story`.
- The **mock MAM** (Simulator → Mock MAM tab, or `POST /api/mam/emit/{sourceId}`) plays the store's role. The **media coordinator** plays the consuming participant:

| Arrival | Coordinator reaction |
|---|---|
| Known asset, rolling range | Noted; no story change (consumers take what exists so far) |
| Known asset + capture-complete extension | Story republished: asset flips `CAPTURING → CAPTURED`, range bounded — skills re-run, and `nbcu-capture-001` files an inform ("run the final compliance pass") |
| Matches no story | Safe-state stop: `WITHHELD` audit recorded on `som.system.audit` — a story is **never** created (that's the v0.3.2 ORPHAN direction, previewable via `Coordinator:OrphanPreview=true`) |

Run the whole thing with the **media-arrival** scenario (matched path) and **media-unmatched** (safe-state path). Message shapes: [`SOM-v0.3.1-distribution-contracts.md`](./SOM-v0.3.1-distribution-contracts.md).

## 6. Building your own skill — the vendor core path

A skill is **data, not code**: one JSON file. The executor interprets it; you never touch C#.

### 6.1 Anatomy

Abridged from the shipped [`skills/nbcu-editorial-standards.json`](../skills/nbcu-editorial-standards.json):

```json
{
  "id": "acme/my-skill",
  "version": "0.1.0",
  "name": "Acme Example Skill",
  "description": "What it checks and why.",
  "skill_type": "VENDOR",
  "disclosure_level": "L2",
  "migration_policy": "GATED",
  "reads": ["headline", "assets"],
  "produces": ["skill.warning.raised", "skill.run.completed"],
  "advert": {
    "role": "compliance check",
    "operates_on": ["story.context"],
    "produces": ["skill.warning.raised"],
    "fires_on": ["headline", "assets[].acquisition_state"]
  },
  "rules": [ { "...": "see 6.2" } ]
}
```

The **`advert`** is the machine-readable claim of what your skill reads, fires on, and produces (the skills model's recall = deterministic advert matching). If `advert.operates_on` doesn't include `story.context`, the executor **skips your skill** — and logs exactly that at Information level, once, so check the app log if your skill never runs.

### 6.2 Rule types

Each rule has `rule_id`, `type`, `config`, `default_severity` (`hold` / `flag` / `inform` — lower-case, one of the two deliberate exceptions to UPPER_SNAKE enums, the other being `x-`/`com.{vendor}` extension values), `affected_fields`, and a `detail_template` with `{placeholder}` substitutions. The seven types:

| Type | Config | Fires when | Substitutions |
|---|---|---|---|
| `term_match` | `field`, `terms[]`, `case_sensitive?` | field's text contains a term (once per term) | `{term}` `{field}` `{value}` |
| `phase_with_missing_field` | `phase`, `field`, `phase_field?` | story is in `phase` AND `field` is empty | `{phase}` `{field}` |
| `field_value_in` | `field`, `values[]` | field equals one of `values` | `{value}` `{field}` |
| `field_present` | `field` | field exists and is non-empty | `{field}` |
| `field_absent` | `field` | field is missing or empty | `{field}` |
| `field_regex` | `field`, `pattern`, `case_sensitive?` | field matches the regex | `{match}` `{field}` `{value}` |
| `field_changed` | `field`, `to?`, `from?` | field's value **differs from the previous story version** (optionally only for a given transition) | `{field}` `{item}` `{from}` `{to}` |

`field` is a dotted path (`lifecycle.phase`). `field_changed` additionally supports **one** `[]` array wildcard — `assets[].acquisition_state` — matching array items across versions by their `asset_id`/`source_id`/`flag_id`/`id`. Change rules stay quiet on the first sighting of a story (there's nothing to compare against — including right after an app restart).

### 6.3 The iteration loop

1. **Register**: dashboard **Skills** modal → add, or `POST /api/skills` (Layer 1 static validation runs automatically — unknown rule types, missing config keys, and bad regexes come back as structured 400s).
2. **Dry-run** (`🧪` button or `POST /api/skills/{id}/dry-run`): evaluates your rules against every seed story **without touching the bus** — you see exactly which stories fire which rules. Note: dry-run has no "previous version", so `field_changed` rules can't fire there; test those live (step 4).
3. Optional **AI review** (`🤖`): ships your skill + seeds + dry-run result to an LLM for structured feedback ([setup](../README.md#skill-validation-3-layers)).
4. **Go live**: publish seeds / run scenarios and watch your skill's run cards and staged outputs. For a `field_changed` rule, mutate a story (Lifecycle panel, or the media-arrival scenario for `acquisition_state`) so there's a transition to detect.

Your outputs ride the same approval gate as everything else: staged → human decision → `som.skills.events` or `som.skills.rejected`, stamped with the reviewer.

## 7. Integrating your own system

You don't have to run inside this process — anything that speaks Kafka + JSON can join. What to implement depends on your role:

| You are… | Consume | Produce | Start here |
|---|---|---|---|
| **NRCS / story source** | — | `story.context` on `som.story.context` | Copy a seed envelope (the dashboard's SOM JSON button shows the full envelope files — exactly the wire shape), keep `story_id` stable, bump `sequence_number` per change, fresh `message_id`/`timestamp` per publish, same `correlation_id` per story lifecycle |
| **Skill vendor (external executor)** | `som.story.context` | `skill.warning.raised` etc. on `som.skills.staging` | [`message-contracts.md`](./message-contracts.md) — the 12-field warning payload |
| **MAM / media store** | — | `delivery.media_available` on `som.delivery.media_available` | [`SOM-v0.3.1-distribution-contracts.md`](./SOM-v0.3.1-distribution-contracts.md) — Source URIs + TAMS timeranges |
| **Media-hungry tool** (transcription, ML) | `som.story.context` + `som.delivery.media_available` | your outputs, via staging or your own topic | The delivery event tells you *when the essence is reachable and where* |

**Envelope rules that bite** (the five-item checklist — full detail in the contracts doc):

1. `som_version` stays `"0.2.0"` on the wire even though payloads are v0.3.1-shaped (SOM-048). Don't gate on it.
2. `correlation_id` is **required** — thread it end-to-end.
3. `timestamp` lives on the **envelope**, never in the payload.
4. `originating_system` (not `source`) identifies you: `system_id`, `system_type` from the v0.3 enum, `vendor`, `version`.
5. Message-type names are **suffixed** on the wire: `skill.warning.raised`, not `skill.warning`.

**Anything the spec doesn't cover yet** goes under `payload.extensions["com.{yourvendor}.{field}"]` — the *designed* escape hatch, not a workaround. Consumers must silently ignore keys they don't recognise. Two live examples in this repo: `com.ibc-poc.capture_complete` on delivery events, `com.nbcu.citations` on warnings.

**Validate before you publish**: drop your candidate payload next to the examples in `schema/v0.3.1-proposed/examples/` and run `python3 schema/validate.py` — same harness the repo's own fixtures use.

## 8. Curl cookbook — the whole loop from a shell

```bash
B=http://localhost:5050

# 1. Publish the hurricane story (live feed CAPTURING, open-ended range)
curl -X POST $B/api/publish/hurricane

# 2. See the mock MAM's catalog
curl $B/api/mam/catalog

# 3. Rolling arrival — coordinator notes it, no story change
curl -X POST $B/api/mam/emit/landfall-feed-01 \
  -H 'Content-Type: application/json' -d '{"timeRange":"[0:0_30:0)"}'

# 4. Final arrival — coordinator flips the asset to CAPTURED, skills re-run,
#    nbcu-capture-001 lands an inform in Pending Approval
curl -X POST $B/api/mam/emit/landfall-feed-01 \
  -H 'Content-Type: application/json' -d '{"captureComplete":true}'

# 5. See what's pending, then decide
curl $B/api/pending
curl -X POST $B/api/decision/<warning_id> \
  -H 'Content-Type: application/json' -d '{"decision":"approve","reviewer":"me"}'

# 6. The safe-state path — an asset no story references
curl -X POST $B/api/mam/emit/ugc-flood-77aa41b0   # → WITHHELD on som.system.audit

# Scripted equivalents of 1–4 and 6:
curl -X POST $B/api/simulator/run/media-arrival
curl -X POST $B/api/simulator/run/media-unmatched
```

Full endpoint list: [README → API endpoints](../README.md#api-endpoints).

## 9. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Dashboard values render `undefined` | Browser is running an old copy of the page — reload (Cmd+R) |
| Lanes flooding with random stories | Auto-stream is on — click the green **Auto-stream ON** header chip → Stop |
| My skill never runs, but dry-run fires | Its `advert.operates_on` doesn't cover `story.context` — the app log says so (once per skill) when the next story arrives; fix the advert |
| `field_changed` rule never fires | No previous version this session (first sighting, or app restarted). Republish the story once, then trigger the transition. Dry-run can never fire change rules |
| Emitted the UGC clip and "nothing happened" | It matched no story → `WITHHELD` audit on the `som.system.audit` chip. By design |
| Emit final didn't flip the asset | Story not on the bus yet (the coordinator re-checks for ~1s, then gives up) — publish the seed first; or the asset is already CAPTURED |
| `POST /api/mam/emit` returns bare 415 | Missing `-H 'Content-Type: application/json'` on a curl with a body |
| Everything frozen, ws pill "reconnecting…" | The app is down — restart `dotnet run`; the page reconnects itself |
| Kafka refuses connections from a container | Advertised-listener mismatch — see [README → Configuration model](../README.md#configuration-model) |

## 10. Glossary

| Term | Meaning |
|---|---|
| **Story** | The editorial unit; published as full `story.context` snapshots, keyed by `story_id` |
| **Asset** | A piece of content on a story (video, script, graphic) with editorial `status` and, for media, `media_refs[]` + `acquisition_state` |
| **Source (TAMS)** | The stable editorial idea of a piece of media (`tams://store/id`); a Flow is one technical rendition of it. SOM references Sources, never Flows |
| **Delivery** | The availability handshake: media became reachable in a store (`delivery.media_available`) |
| **Link** | An Asset-to-Destination commitment, with a per-destination compliance gate (August build) |
| **Telling** | An on-air exposure event; on-air state is derived from Tellings, never stored on the asset (August build) |
| **Skill** | A passive, data-driven newsroom automation; the executor runs it |
| **Advert** | A skill's machine-readable declaration of what it operates on / fires on / produces |
| **Recall** | The executor's deterministic advert-matching step — deciding which skills run |
| **Staging** | The pre-approval topic; nothing reaches the production bus without a human decision |
| **Safe-state stop** | When the correct action is unclear, do nothing and *record* the non-action (`WITHHELD` on `som.system.audit`). `WITHHELD` is also how the dashboard records a human **reject** — a terminal non-action on that output instance |
| **Envelope** | The outer wrapper every SOM message shares; the payload inside is what schemas validate |
| **Extension** | `payload.extensions["com.{vendor}.{field}"]` — the sanctioned place for not-yet-ratified fields |
