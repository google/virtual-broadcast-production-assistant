# SOM v0.3.1 — IBC Readiness Gap Analysis

_Service: `som-hackathon-starter-dotnet` · branch `som-v031-ibc-readiness` · 23 June 2026_

Gap analysis of this service against the **SOM v0.3.1** schema (v0.3 Release + the five resolved Section-12 items; see the SOM spec folder `SOM-v0.3.1-Technical-Specification`), scoped to what the **IBC 2026 two-demo deck** (17 June: the hurricane and the verdict) requires.

## Framing

The skill worker is **schema-agnostic**: `RuleEngine` matches dotted JSON paths via `GetByPath` and never deserialises into typed models. So most v0.3.1 renames are **data changes** (seeds, skill defs, config), not C# refactors. The real build is the **distribution-layer message families** the demos need, which the service has no concept of today.

Status legend: **[RATIFIED]** safe to implement now (decisions #1–#22) · **[PENDING]** depends on the v0.3.1 proposal closing (objection window 24 June, lock 30 June) — implement provisionally, flag in the migration log.

---

## 1. New message families — the biggest build  [PENDING]

The service only knows `som.story.context` + `som.skills.*` (`KafkaOptions.cs:12–20`). The demos require four families it can neither produce nor consume:

| Family | Demo beat | Proof |
|---|---|---|
| `som.link.committed` / `.gate_changed` / `.withdrawn` | D1·B4 Reach (digital CLEARED / broadcast BLOCKED); D2·B2 partial fire | Reach, Sync |
| `som.delivery.media_available` | D1·B5 (TAMS junction; `flow_id`) | Media layer |
| `som.system.audit` | D2·B3 (clearance/suppression trail) | Audit |
| `som.telling.started` / `.ended` | derive on-air state | (supports Reach/Sync) |

Work: add topics to `KafkaOptions`/`Program.cs`; producers/consumers; `usage[]` maintenance from `som.link.*` under the §5 idempotent-upsert rules. Payload shapes are in the v0.3.1 spec §5.1–5.4 but remain PENDING ratification.

## 2. `story.context` payload migration — SOM-048  [RATIFIED, partial]

The 5 seeds (`seed-stories/*.json`) are pure v0.2. Per `01-breaking-courthouse.json`:

| Current (v0.2) | v0.3.1 target | Decision |
|---|---|---|
| `source` (envelope) | `originating_system` | #4.1 |
| `payload.sources[]` | `editorial_source[]` | #4.3 |
| `credibility: PRIMARY` / `OFFICIAL` | `TRUSTED` / `ENDORSED` | #11 |
| `instances[]` (lines 144–164) | **removed** (banned); re-expressed via `link`/`usage[]` | #3 |
| `skills_config.broadcaster` | `skills_config.newsroom` | #12 |
| `skill_type: "broadcaster"` | `"NEWSROOM"` | #12 |
| `migration_policy: "gated"`, `skill_priority: "critical"` | `GATED`, `CRITICAL` | #13 |
| `asset.status: LIVE`/`AIRED` | removed (derived from Telling) | #16 |
| _(absent)_ | `evidential_position` on assets | #22 |
| _(absent)_ | `newsroom_id` (top-level) | #12 |
| _(absent)_ | `authenticity_credential`, `media_refs[]`, `voice_count`, `compliance[].media_range` | v0.3.1 **[PENDING]** |

## 3. Lifecycle phase model is wrong vs #19  [RATIFIED]

`DashboardService.cs:293` hardcodes `PhaseOrder = { PLANNED, GATHERING, DEVELOPING, READY_TO_AIR, ON_AIR, PUBLISHED }`. v0.3 is **`DEVELOPING → READY_TO_AIR → BREAKING → PUBLISHED`**. `GATHERING`/`ON_AIR` aren't v0.3 phases; `PLANNED` is a `story_type` not a phase; `BREAKING` is missing; `ON_AIR`/`LIVE`/`AIRED` must be **derived from the Telling**, not stored. Also fix the simulator step descriptions referencing `ON_AIR` (`SimulatorService.cs:14,245`).

## 4. Skill firing rule + output contract  [RATIFIED]

- **Output contract (`SkillWorker.cs:131–149`):** `BuildWarning` emits 10 of the 12 fields — **missing `scope` and `skill_warning_ref`** — and places `timestamp` in the **payload** (line 148), which v0.3 hard-rejects (timestamp → envelope, #18). Warnings are published as **bare payloads** (`SkillWorker.cs:106`) with no envelope; the incoming `correlation_id` is discarded (`:63–67`). Fix: thread `correlation_id`, wrap output in a v0.3.1 envelope, add `scope` (firing level `story:{id}` / `link:{id}`) + `skill_warning_ref`. For the Demo 2 hold, support real `non_overridable: true` + populated `blocks[]`.
- **Skill def (`skills/nbcu-editorial-standards.json`):** `skill_type: "broadcaster"` → `NEWSROOM`; `migration_policy: "gated"` → `GATED`.
- **Firing engine (`RuleEngine.cs`)  [PENDING]:** today field-path matching only. The deck's model is **(evidential_position × outlet/path) → skills** — per-asset iteration + tier-aware firing at the link's Compliance Gate. New rule capability required; largest firing change, scope to the specific demo checks.

## 5. Demo scenarios + schema validation  [PARTIAL]

`SimulatorService`/`TestProducer` have generic scenarios but nothing producing the hurricane/verdict beats. Add two scripted scenarios mirroring the v0.3.1 spec worked examples. There is **no schema validation** in the loop — wire the v0.3.1 JSON Schemas into producer tests/CI (the 14 worked examples are fixtures).

## Already there and reusable

Premise propagation with `change_detected_at` (seed 01:43–44) ≈ Beat 3 (Accuracy); `compliance[]` + `editorial_gates[].blocks[]` cover hold mechanics; the staging→approve dashboard flow is the "a human decides" path; the generic rule-type system is a sound base to extend.

## Suggested order for IBC

1. Payload migration (§2) + phases (§3) — unblocks everything, low risk. **[RATIFIED]**
2. Skill-warning contract (§4 output) — small, high value. **[RATIFIED]**
3. `som.link.*` + gates (§1) — Reach + Sync + Demo 2 partial fire. **[PENDING]**
4. `delivery.media_available` + `media_refs`/`authenticity_credential` — Media + Provenance. **[LANDED — mock MAM producer + media coordinator consumer]**
5. `som.system.audit` (§1) — Demo 2 close. **[PARTIAL — two producers live: coordinator `WITHHELD` non-actions, dashboard gate decisions; WS1 adds the rest]**
6. Firing-rule upgrade (§4) — richest; do last / scope down. **[PENDING]**

See `SOM-v0.3.1-Migration-Log.md` for the running record of changes on this branch.

---

## Status addendum — 9 July 2026

v0.3.1 **locked 30 June** (by email; Source re-key folded in, objection window closed 1 Jul with no objections). Everything above marked [PENDING] on the schema side is now RATIFIED — the remaining gaps are build work, not spec risk.

### Done since 23 June (items 1–2 of the suggested order)

- ✅ §2 payload migration — all 5 seeds validate against the v0.3.1 story-context + envelope schemas.
- ✅ §3 lifecycle phases — `PhaseOrder` fixed to `DEVELOPING → READY_TO_AIR → BREAKING → PUBLISHED`; simulator descriptions updated.
- ✅ §4 output contract — skill-warning envelope, `scope`, `skill_warning_ref`, `correlation_id` threading.
- ✅ MOS→SOM bridge scaffold (`mos-bridge/`, emits `story.context` + `link.committed`).
- ✅ v0.3.1 schemas vendored (`schema/v0.3.1-proposed/` + `validate.py`); **30 Jun Source-re-key re-cut synced on disk but UNCOMMITTED** — commit before hackathon so participants build against the locked shapes.

### Still open (= the August hackathon scope; see `SOM-Hackathon-Aug-2026-Scope.md`)

- ⏳ §1 distribution-layer families — `som.link.*`, `som.telling.*`: topics, producers/consumers, `usage[]` maintenance (§5 idempotent upsert). Biggest remaining build; demo-critical (D1·B4 Reach). ✅ `som.delivery.media_available` and `som.system.audit` landed (items 4–5 above).
- ⏳ §2 media leg on seeds — `media_refs[]` (Source URI + TAMS timerange, NOT `flow_id` — re-keyed 29 Jun), `authenticity_credential`, `voice_count`, `compliance[].media_range`.
- ⏳ §4 firing-rule upgrade — (evidential_position × outlet/path) anchor in `RuleEngine.cs`.
- ⏳ §5 scripted hurricane/verdict scenarios + schema validation wired into producer tests/CI.
- ⏳ Editorial pass on `evidential_position` (everything defaulted TERTIARY on migration).
- ⏳ `dotnet build` on the C# changes (needs the Mac).

### Errata

- ⚠️ **`TRANSCRIPT` missing from `asset_type`** in the vendored `som-v0.3.1-story-context.schema.json` (and the SOM-folder original). TRANSCRIPT-as-Asset was **locked at v0.3.1** (29 Jun AI-outputs decision, glossary v0.345 CONFIRMED) but the 30 Jun re-cut omitted the enum value. Fix both copies — one-line enum addition.

### v0.3.1 / v0.3.2 boundary — the rule for August

**The IBC PoC ships on v0.3.1 only.** v0.3.2 exists solely as a rough draft (`SOM/schema/v0.3.2-proposed/` — assertions[], authorship provenance, ORPHAN story_type, telling.transforms[]); nothing in it is WG-agreed, and its freeze (~1 Aug) lands mid-hackathon. Because the worker is schema-agnostic, v0.3.2 is seed-data + schema work with **no C# refactor implied** — the only code-adjacent v0.3.2 item (the firing-rule anchor) is already on the v0.3.1 list above. Do not vendor v0.3.2 schemas into this branch; a v0.3.2 beat (orphan clip / edge transforms) is a stretch goal on a separate branch **only if** the WG accepts before the freeze.
