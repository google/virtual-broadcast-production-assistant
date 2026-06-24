# SOM v0.3.1 — IBC Readiness Migration Log

_Branch `som-v031-ibc-readiness`. Running record of changes. Companion to `SOM-v0.3.1-IBC-Gap-Analysis.md`._

**Convention:** ✅ done & verified · 🟡 done, needs `dotnet build` on the Mac (no compiler in this environment) · ⏳ deferred pending final schema (v0.3.1 lock, 30 June). JSON data files are validated against the v0.3.1 schemas; C# is edited but not compiled here.

---

## 2026-06-23

### Docs
- ✅ Added `docs/SOM-v0.3.1-IBC-Gap-Analysis.md` — full gap analysis vs v0.3.1, scoped to the IBC two-demo deck.
- ✅ Added this migration log.

### Pending decisions that gate later work (waiting on schema)
- ⏳ `som.link.*` / `som.telling.*` / `som.delivery.*` / `som.system.audit` **payload shapes** — v0.3.1 proposal §5, objection window to 24 June, lock 30 June.
- ⏳ `authenticity_credential` exact shape (`{present, standard?, claim?, validated_by?}` proposed).
- ⏳ `media_refs[]` `flow_id` vs non-TAMS `locator` form (proposed; not yet in `schema/v0.3.1-proposed/`).
- ⏳ `voice_count` (#22) and `compliance[].media_range` — proposed, not yet in released schema.

> Items above are implemented **provisionally** where the demo needs them, using the shapes in the v0.3.1 spec, and will be reconciled when the schema locks.

### Changes (this session)

**Lifecycle phases (#19)** — 🟡 `DashboardService.cs`
- `PhaseOrder` → `{ DEVELOPING, READY_TO_AIR, BREAKING, PUBLISHED }` (was `{ PLANNED, GATHERING, DEVELOPING, READY_TO_AIR, ON_AIR, PUBLISHED }`).
- `PhaseAlias` corrected: `BREAKING` is no longer aliased to `DEVELOPING` (it's a real phase); added legacy maps `PLANNED/GATHERING→DEVELOPING`, `ON_AIR→BREAKING`, `COMPLETE→PUBLISHED`.

**Skill definition** — ✅ `skills/nbcu-editorial-standards.json`
- `skill_type: "broadcaster"` → `"NEWSROOM"` (#12); `migration_policy: "gated"` → `"GATED"` (#13).

**Skill-output contract (#18, #21)** — 🟡 `SkillWorker.cs` + `DashboardService.cs`
- `BuildWarning` now emits the full twelve-field `SkillWarning`: added `scope` (`story:{id}`, the firing level) and `skill_warning_ref`; removed the payload-level `timestamp` (hard-rejected — belongs on the envelope) and `message_type` (moved to envelope).
- New `BuildEnvelope(...)` wraps warnings and run records in a SOM envelope (`som_version`, `message_id`, `correlation_id`, `message_type`, `timestamp`, `originating_system{skill_worker}`, `topic`, `payload`). `correlation_id` is now echoed from the inbound `story.context` (previously discarded).
- `BuildRunRecord` returns payload only (message_type/timestamp moved to envelope).
- `DashboardService.ExtractOutputId` made envelope-aware (`node["payload"] ?? node`) so the approve/reject queue keeps working now that staged outputs are enveloped. **Integration fix — verify on the Mac.**

**Seed migration — SOM-048 (#3,#11,#12,#13,#16,#17,#19,#22)** — ✅ all 5 `seed-stories/*.json`, validated
- `source` → `originating_system`; `sources[]` → `editorial_source[]`.
- `credibility`: `PRIMARY→TRUSTED`, `OFFICIAL→ENDORSED` (VERIFIED unchanged); `source_type` upper-cased.
- `instances[]` **removed** (banned). _(Re-expression via `link`/`usage[]` deferred — needs the §5.1 link payload, ⏳ PENDING.)_
- `skills_config.broadcaster` → `newsroom`; `skill_type broadcaster→NEWSROOM`; `migration_policy/skill_priority/disclosure_level` upper-cased; added top-level `newsroom_id`.
- `government_approval.status` and `ai_enrichments[].enrichment_type` upper-cased.
- `asset.status` `LIVE/AIRED` → `READY` (derived from the Telling); added `evidential_position` to every asset (defaulted `TERTIARY`, the #22 safe side — **needs editorial review per asset**).
- Seed 02 reconciled: `story_type: "DEVELOPING"` → `ACTIVE` with `lifecycle.phase: DEVELOPING` (#19). Legacy `lifecycle.previous_phase: PLANNED` normalised.
- **Verification:** all 5 seeds now PASS both the v0.3.1 `story-context` schema and the `envelope` schema.

### Schema questions raised by the migration (for the WG / final answers)
- ⚠️ **`compliance[].resolved_at`** — the seeds carried it on 2 resolved flags; the v0.3.1 `compliance_flag` def has no such field (`additionalProperties:false`). Dropped to validate. **Should `compliance_flag` carry `resolved_at`?** If yes, add to the schema rather than the seeds losing it.
- ⚠️ **`evidential_position` defaulting** — applied `TERTIARY` to all migrated assets as the safe default. Real values (PRIMARY for raw feeds/SOTs, etc.) need an editorial pass; relevant to the Provenance proof.

### Still pending (waiting on final schema)
- ⏳ Distribution-layer producers/consumers: `som.link.*`, `som.telling.*`, `som.delivery.media_available`, `som.system.audit` (topics + payloads).
- ⏳ Asset `media_refs[]` / `authenticity_credential` / `voice_count`, `compliance[].media_range` on the seeds that need them for the demos.
- ⏳ Firing-rule upgrade to the (evidential_position × outlet/path) anchor in `RuleEngine.cs`.
- 🟡 **All C# changes need `dotnet build` on the Mac** — no compiler in this environment.

## 2026-06-24 — MOS↔SOM bridge

- ✅ **Scaffolded `mos-bridge/`** — reference MOS v4.0 → SOM v0.3.1 ingest translator:
  - `MosToSomBridge.cs` — pure translator (`Translate(XElement, correlationId)`), no transport wiring. Message map: `roCreate/roReplace`→Destination+`story.context`+`link.committed`; `roStory*`→`story.context`+`link.committed`; `roStoryMove`→`link.gate_changed`; `roStoryDelete`→`link.withdrawn`; `roElementAction`→link event by verb; `roReadyToAir`→lifecycle; `heartbeat`→`system.health`.
  - `samples/roCreate.xml` (sample MOS input) + `samples/story.context.expected.json` + `samples/link.committed.expected.json` — **both fixtures validated** against the v0.3.1 envelope/story-context/link schemas.
  - `README.md` — object-model mapping, identity/trust reconciliation, PENDING items.
- Identity reconciled: bridge is `originating_system`; MOS device id in `extensions.com.som.mos-bridge`; **no signing** (#18 removed `signature`).
- ⏳ **PENDING:** `Destination` + `rundown_context` shapes (the `destination.upserted` emission is best-effort); bidirectional SOM→MOS (v0.4).
- 📌 **Process rule added** (also in SOM `schema/README.md` and the SOM working-context): **any schema change to envelope / story.context / distribution layer / identity must be checked against the MOS-bridge map** before it lands. Companion spec: `SOM-MOS-Bridge-v0.3.1`.

## 2026-06-24 — schemas vendored + validation

- ✅ **Vendored the SOM JSON Schemas into `schema/`** (released `som-v0.3-*` + `v0.3.1-proposed/*` + examples), copied from the SOM spec folder (source of truth). The repo can now validate without reaching OneDrive.
- ✅ **`schema/validate.py`** — validates `seed-stories/*`, `schema/examples/*`, `v0.3.1-proposed/examples/*`, and `mos-bridge/samples/*.expected.json` (envelope + payload-by-type). **13/13 PASS.**
- ✅ **`schema/sync-from-spec.sh`** — one-command re-vendor from the spec folder (`SOM_SPEC_DIR` overridable).
- 📌 **Sync rule** (`schema/README.md` + root `CLAUDE.md`): spec changes → `sync-from-spec.sh` then `validate.py`; code-driven schema needs → change the spec original first (check MOS-bridge impact), never hand-edit vendored files. Run `validate.py` after touching `seed-stories/` or the message builders.

## 2026-06-24 — `skill.warning.scope` semantics reconciliation

- ⚠️ **Conflict found** checking the `SOM/skills` Claude-skill proposals against the vendored schema: system-level `scope` is stated three ways — schema description says **Delivery**, the `som-skills-firing` skill says **the Asset**, the worker + `som-message-author` + `CLAUDE.md` say **`story:{id}`**. All validate (`scope` is a free string), so it's semantic drift, not a schema failure.
- ✅ **Proposal written:** `docs/SOM-v0.3.1-scope-reconciliation.md` — recommend a typed `{level}:{id}` reference, level ∈ `story`/`asset`/`link`; **drop "Delivery"** (wrong layer + PENDING). PROPOSED, awaiting schema-authority ratification.
- 🟡 **Applied in-repo:** `SkillWorker.cs` comment (emitted value stays `story:{story_id}` — correct for the current story-wide `RuleEngine`; `RuleMatch` carries no `asset_id`) + `CLAUDE.md` scope-levels line. `dotnet build` re-verified green.
- ⏳ **At source (not applied here):** the schema-description edit lands in the SOM spec folder then re-vendors (`sync-from-spec.sh`); the `SOM/skills` edits land in OneDrive. Optional `scope` `pattern: ^(story|asset|link):` deferred to the 30 June lock. `asset:{id}` emission belongs to the PENDING firing-rule upgrade.
