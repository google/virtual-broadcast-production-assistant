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
- ⏳ Distribution-layer producers/consumers: `som.link.*`, `som.telling.*` (WS1, Aug). ✅ `som.delivery.media_available` (mock MAM producer + media coordinator consumer) and `som.system.audit` (coordinator `WITHHELD` non-actions + dashboard gate decisions) are live.
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

## 2026-07-09 — Mock MAM (TAMS stand-in) scaffold

- ✅ **`MockMamService.cs`** — no MAM participant in the IBC PoC, so this stands in for the TAMS media store's bus contract: naming authority for `tams://mock-mam-store/<id>` Source URIs + `som.delivery.media_available` producer. Full v0.3.1 envelopes (`originating_system.system_type: "archive"`), Source URI + TAMS timerange per the 29 Jun re-key (no `flow_id`). **Write-only on the bus by design** — no query API, nothing other participants read. Payload + envelope shapes verified against the vendored schemas (offline validation; see `docs/SOM-Hackathon-Aug-2026-Scope.md` WS2a).
- ✅ **`content/mam-catalog.json`** — 3 catalogued Sources (courthouse pool feed keyed to worked-example `a2`; hurricane landfall feed for D1·B5; UGC clip reserved for the v0.3.2 orphan stretch). WS2 wires these IDs into the seeds' `media_refs[]`.
- ✅ **`KafkaOptions.DeliveryTopic`** (+ `appsettings.json`) — first distribution-layer topic; `som.link.*` / `som.telling.*` remain WS1 (`som.system.audit` has since landed: coordinator + dashboard producers).
- ✅ **Simulator** — new `media-available` action + `media-arrival` scenario: publish → three growing-timerange emits (`[0:0_30:0)` → `[0:0_75:0)` → `[0:0_1260:0)`), mimicking a TAMS recording addressable while still growing. `SimAction` gains `SourceId`/`TimeRange`.
- ✅ **Endpoints** — `GET /api/mam/catalog`, `POST /api/mam/emit/{sourceId}` (optional body `{timeRange, assetId}`).
- 🟡 **Not yet compiled** — written off-Mac; `dotnet build` + smoke-test is the first hackathon-prep step.

## 2026-08-12 — v0.3.2 pack vendored + wire version carries the pack

- 📌 **Decision context:** v0.3.2 is the IBC target (WG, early Aug); the four open v0.3.2 shapes were dispositioned as **deferred to v0.4** with interim rules (12 Aug — see spec `schema/v0.3.2-proposed/README.md`). The SOM-048 `0.2.0` wire freeze is **retired** (12 Aug): `som_version` now carries the schema pack version — hackathon users read `0.2.0` against v0.3.1 payloads and reasonably concluded they were on the wrong schema.
- ✅ **`SomEnvelope.Version` constant** (`SomEnvelope.cs`) replaces the six scattered `"0.2.0"` literals across SkillWorker / DashboardService (decision + audit) / MediaCoordinatorService / MockMamService / MosToSomBridge. Seeds + mos-bridge golden fixtures bumped to `0.3.2`; `validate.py` `PACK_VERSION` fails any repo-owned envelope fixture that drifts.
- ✅ **Vendored `schema/v0.3.2-proposed/`** (3 changed schemas + README + 4 examples) via the extended `sync-from-spec.sh`. Per pack invariant #8: envelope + skill-warning stay flat `som-v0.3-*`, link-event + system-audit stay `v0.3.1-proposed/`.
- ✅ **Sync also picked up today's spec-side description fixes**: `skill.warning.scope` now states the ratified `{level}:{id}` semantics (closes the 24 Jun reconciliation's "at source" item — drop "Delivery"); envelope `som_version` description documents the pack-version rule; story-context descriptions no longer claim the wire is `0.2.0`.
- ✅ **`validate.py` rewired to the v0.3.2 pack**: telling/delivery → v0.3.2 schemas (additive — v0.3.1 fixtures still pass), new `v0.3.2-proposed/examples` group (min 4). `story.context` flips to the v0.3.2 schema together with the seed `ai_enrichments` migration (hard-rejected in v0.3.2 — same change, next entry). **19/19 PASS.**

## 2026-08-12 — seeds migrated off `ai_enrichments` (v0.3.2 AI-outputs refactor)

- ✅ **5 enrichment entries across 4 seeds converted to first-class assets** (the Telling test: publishes → is an Asset): `enrichment_id` → `asset_id`, `enrichment_type` → the promoted `asset_type` (SUMMARY ×3, ANALYSIS, SOCIAL_POST), `human_reviewed: true/false` → `provenance.review.state CONFIRMED/PENDING` (+ `status READY/IN_PRODUCTION`), model split into `model` + `model_version`, `input_sources`/`prompt_hash` carried 1:1 into `authorship_provenance`. Seed 05's empty `ai_enrichments: []` removed.
- 📌 **Dropped, deliberately:** `content` strings (nothing rendered them; v0.3.2 carries no inline content on story.context — content lives off-bus by design) and `guardrails_applied` (no v0.3.2 home, no readers).
- ✅ **`validate.py` `story.context` → the v0.3.2 schema** (`ai_enrichments` hard-rejected — seeds passing is proof of migration). No skill rule and no C#/dashboard code read `ai_enrichments` (verified) — the demo firing map is untouched. **19/19 PASS.**

## 2026-08-12 — review round on the v0.3.2 switch (pre-PR)

- ✅ **`validate.py` now pins C# ↔ validator**: `main()` reads `SomEnvelope.cs` and hard-fails if `SomEnvelope.Version != PACK_VERSION` (mutation-tested) — the constant, the seeds and the validator can no longer drift apart. Also: seed minimum 5→6, envelope-intent hardening (a fixture with `payload` but no `som_version` is treated as a broken envelope, not silently reclassified as a bare payload), actionable error when a vendored schema is missing.
- ✅ **`sync-from-spec.sh`**: the v0.3.2 schema `cp` is no longer error-suppressed and the script asserts the three schemas exist before printing success — a renamed spec folder now fails loudly instead of "Vendored." over a no-op.
- ✅ **Flat v0.3 example re-stamped `som_version: "0.3.0"`** (spec-side + re-vendored): it demonstrates the flat v0.3 target shape (which allows `ai_enrichments`) and must not claim the v0.3.2 pack.
- 📌 **`schema/v0.3.1-proposed/som-v0.3.1-telling-event.schema.json` and `-delivery-media-available.schema.json` are retained but no longer exercised** — validate.py routes telling/delivery to the v0.3.2 schemas (the v0.3.1 example fixtures passing against them is the additivity proof).
- ✅ Doc corrections from review: seed-count 5→6 sweep (CONTRIBUTING, starters, dashboard hints, architecture, dashboard-guide), distribution-contracts re-pointed at the v0.3.2 pack (telling/delivery schema links, pack statement), message-contracts wire-baseline updated, envelope reference table completed (`modification_header`/`_actors`/`@context`) and two wrong seed-table rows fixed (seed 05 is URGENT with the `compliance` key absent; seed 02's gate is `EDITORIAL_HOLD`), the in-app `field_present` hint no longer teaches the hard-rejected `ai_enrichments`, and the wire-visible audit reason no longer bakes in version-churn prose.

## 2026-08-15 — re-sync to the 13 Aug spec + schema tools vendored + drift gate

- 📌 **Two-day silent drift caught and closed**: the spec folder moved on 13 Aug (post-vendoring) and nothing signalled it. The sharp one: the repo's `delivery-media-available` still said time_range-on-locator was **DEFERRED to v0.4 / "consumers MUST NOT assume offset-from-zero"** while the spec had **PINNED the opposite** (offset from the referenced file's own zero — the point Jon raised). Message validation could never see it: `validate.py` stayed 19/19 green throughout.
- ✅ **Re-vendored `schema/v0.3.2-proposed/`** via `sync-from-spec.sh`: the PINNED time_range wording (schema description + `time_range` field), two som_lint-caught description fixes (`assertion.target` no longer claims to "reuse the audit target set" it exceeds — STORY is deliberately the wider set; the same stale claim in the schema's ROOT description and the README's assertions row survived the 13 Aug spec edit and was fixed spec-side in this round; ORPHAN description now states the ASSOCIATED audit action is proposed, not available), the DETECTION claim constraint (`assertion_type: DETECTION` → `claim.detection_class` + `claim.verdict` required — producer-affecting for DETECTION emitters; no repo code or seed emits assertions, verified), README + two example touch-ups (dates, model names). `validate.py` **19/19 PASS**; no C# changes needed for *validation* — but note the reference consumer still requires `source` (`MediaCoordinatorService.cs:158`) and silently skips locator-only arrivals, so the freshly-pinned locator `time_range` semantics have zero consumption coverage (pre-existing gap, tracked as an IBC follow-up, not this sync).
- ✅ **Schema tools vendored** (`som_lint.py`, `som_diff.py`, `SCHEMA-TOOLS.md` — see SCHEMA-TOOLS.md for what each answers) and `sync-from-spec.sh` now vendors them alongside the schemas.
- ✅ **`sync-from-spec.sh --check`**: no-write drift gate — vendors to a temp dir, byte-compares the vendored file set, exit 1 with a `DRIFT:` line per file. Run it before trusting the repo copy; it would have turned this drift into a red check on day one.
- ✅ **`som_diff.py` classifier fix (spec-side first, then vendored)**: a new subschema under an always-applied combinator (`allOf`/`then`/`else`/`not`/`contains`) narrows what validates and is now priced **PRODUCERS** — previously it fell into "field added — breaks nobody" and the DETECTION constraint above priced as non-breaking, exit 0. Symmetric removals handled (`anyOf`/`oneOf` branch removed → PRODUCERS; narrowing removed → NOBODY); brand-new structures exempt (a narrowing branch inside a wholly new object is part of an optional addition — 0.3.1→0.3.2 output verified byte-identical pre/post-patch); rollup no longer folds a PRODUCERS child under a less-severe parent.

## 2026-08-18 — `tags[]`: the subject axis, and the engine change that makes it readable

- 📌 **Why it exists.** Every axis on story-context carried lifecycle, priority, compliance or provenance — none said what a story is *about*. A skill trigger policy had no field to resolve on and fell back to substring matching on headline text (the failure mode that fired a safety gate on 5 of 6 seeds because `graphic` matched "graphics"). The skill library was already demoing `story.category`, a field that existed in **no schema version**.
- ✅ **Spec-side first, then vendored** (`sync-from-spec.sh`): `tags[]` on story-context + `$defs/story_tag`. **Ordered** — `tags[0]` is primary and a policy matching more than one entry resolves on the earliest, so a story that is genuinely both sport and politics routes deterministically. **Scheme-qualified** `{scheme, value, label?}` with scheme ∈ `newsroom` | `iptc-mediatopic` | `com.{vendor}.{name}`: IPTC Media Topics is the broadcast standard and appears in the archived v0.1/v0.3/v0.3B drafts, so bare strings invite "why not IPTC?". The scheme namespace is governed; the value vocabulary belongs to the scheme owner — over-constraining a taxonomy makes it wrong for every newsroom at once. `uniqueItems`. Priced with som_diff: **0 producer-breaking · 0 consumer-affecting · 2 non-breaking**.
- ✅ **MOS reconciliation (required by the bridge rule).** MOS carries **no standard story-category element**. `storySlug` is a rundown label, not a subject taxonomy — a bridge must **not** synthesise tags from it. NCS categories arrive via `mosExternalMetadata`, already mapped to `extensions.com.{vendor}.*`; promoting one to a `com.{vendor}.{name}`-schemed tag is a per-vendor decision, never automatic. The scheme qualifier is what makes that promotion expressible.
- ✅ **`RuleEngine` — the part that would have shipped a dead field.** `GetByPath` splits on `.` and walks objects only, so an array path resolved to **null** for every rule type except `field_changed` (the sole user of `GetByPathMulti`). `field_value_in` — precisely the rule type a trigger policy resolves with — would have read `tags[].value` as null and silently never fired. Fixed: `GetByPath` now understands the `[]` wildcard (first node in document order) via a new `GetByPathAll`, and `field_value_in` walks candidates **in order, earliest match wins** — which is the ordered rule from the schema, implemented. Audited first: only one existing rule uses `[]` (`nbcu-editorial-standards`, `field_changed`), so no rule changes behaviour.
- ✅ **Verified, not assumed.** 10-case harness over the real `RuleEngine`: earliest-match both ways (`sport,politics`→sport; `politics,sport`→politics), unmapped-then-mapped (`business,sport`→sport), mixed schemes, untagged, plus scalar regressions. **Mutation-tested** against the pre-fix engine — 5 of 5 tag cases return NO MATCH, scalars unaffected, proving the tests exercise the fix. `dotnet build` clean, `validate.py` **19/19 PASS**, `som_lint` 0 errors / 7 warnings (unchanged).
- ✅ **Seeds carry tags** so the feature is demonstrable, not theoretical: 02 and 04 are deliberately two-tag (primary first) to exercise ordering; 06 pairs a house tag with an IPTC id to show schemes coexisting; **03 is left untagged on purpose** — an absent array means untagged, never a default desk.
- ⏳ **Not done here, deliberately:** the skill library's `watched_field: "story.category"` (in `SOM-Transcription-Walk-Demo.html`, spec-side) still points at the field that never existed and needs repointing to `tags[].value` — that walkthrough is under review with Alex, so it is his edit, not a silent one. The other walkthrough decks use `watched_field` generically against `premise.actual_outcome` and need no change. No partner zip cut: the pack re-cut still owes Janet's beat6 fix, and both should ship in one disruption.
