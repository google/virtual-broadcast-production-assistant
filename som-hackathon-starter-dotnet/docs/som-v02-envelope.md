# SOM v0.2 Envelope — Field Reference

This document describes the canonical field paths in a `story.context` message on the SOM bus. Skills read these fields via dot-notation paths (e.g. `lifecycle.phase`, `compliance`). The rule engine's `GetByPath` walks these paths against the `payload` object.

All fields below are relative to `payload`. The outer envelope (`som_version`, `message_id`, `correlation_id`, `source`, `topic`) is stripped before the payload reaches the skill worker.

## Envelope wrapper (outer)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `som_version` | string | yes | Spec version, always `"0.2.0"` |
| `message_id` | string (UUIDv7) | yes | Unique per message |
| `correlation_id` | string (UUIDv7) | yes | Links all messages about the same story lifecycle |
| `message_type` | string | yes | Always `"story.context"` for inbound stories |
| `timestamp` | string (ISO 8601) | yes | When the message was produced |
| `source` | object | yes | Origin system (see below) |
| `topic` | string | yes | Kafka topic name |
| `payload` | object | yes | The story data — everything below |

### `source`

| Field | Type | Description |
|-------|------|-------------|
| `source.system_id` | string | Unique ID of the originating system |
| `source.system_type` | string | System category (e.g. `"ncs"`) |
| `source.system_name` | string | Human-readable name (e.g. `"iNEWS NYC"`) |
| `source.vendor` | string | Vendor name |
| `source.version` | string | System version |

## Payload — top-level fields

| Path | Type | Required | Description |
|------|------|----------|-------------|
| `story_id` | string | yes | Stable story identifier across lifecycle |
| `slug` | string | yes | Short editorial slug (uppercase, hyphenated) |
| `headline` | string | yes | Full headline text |
| `story_type` | string | yes | `"ACTIVE"`, `"KILLED"`, etc. |
| `updated_at` | string (ISO 8601) | yes | Last update timestamp |
| `sequence_number` | integer | yes | Monotonically increasing per story_id |

## `lifecycle`

Tracks the editorial phase of the story.

| Path | Type | Required | Description |
|------|------|----------|-------------|
| `lifecycle.phase` | string | yes | Current phase (see values below) |
| `lifecycle.phase_entered_at` | string (ISO 8601) | yes | When the current phase started |
| `lifecycle.previous_phase` | string | no | Phase before the current one |
| `lifecycle.phase_owner` | object | no | Editor who owns this phase |
| `lifecycle.phase_owner.user_id` | string | — | Editor's system ID |
| `lifecycle.phase_owner.display_name` | string | — | Editor's display name |
| `lifecycle.phase_owner.role` | string | — | Editor's role |

### Canonical lifecycle phases

```
PLANNED → DEVELOPING → READY_TO_AIR → BREAKING → PUBLISHED → KILLED
```

The simulator's `advance-phase` endpoint steps through these in order.

## `priority`

| Path | Type | Required | Description |
|------|------|----------|-------------|
| `priority.level` | string | yes | `"ROUTINE"`, `"ELEVATED"`, `"URGENT"`, `"FLASH"` |
| `priority.reason` | string | no | Why this priority was set |
| `priority.escalated_by` | string | no | System that escalated |
| `priority.escalated_at` | string (ISO 8601) | no | When escalation occurred |

## `premise`

Tracks editorial expectations vs. actual outcomes (e.g. trial verdicts, election results).

| Path | Type | Required | Description |
|------|------|----------|-------------|
| `premise.expected_outcome` | string | no | What the newsroom was preparing for |
| `premise.confidence` | string | no | `"LOW"`, `"MEDIUM"`, `"HIGH"` |
| `premise.premise_changed` | boolean | no | Whether the premise has flipped |
| `premise.previous_outcome` | string | no | What was expected before the change |
| `premise.actual_outcome` | string | no | What actually happened |
| `premise.affected_assets` | string[] | no | Asset IDs invalidated by the change |
| `premise.change_detected_at` | string (ISO 8601) | no | When the change was detected |
| `premise.change_detected_by` | string | no | Source that detected it |

## `compliance[]`

Array of compliance flags attached to the story. A key field for editorial safety skills.

| Path | Type | Required | Description |
|------|------|----------|-------------|
| `compliance[].flag_id` | string | yes | Unique flag identifier |
| `compliance[].type` | string | yes | Flag type (see values below) |
| `compliance[].severity` | string | yes | `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"` |
| `compliance[].detail` | string | yes | Human-readable description |
| `compliance[].jurisdiction` | string | no | Legal jurisdiction (e.g. `"US"`, `"US-CA"`) |
| `compliance[].regulation_ref` | string | no | Regulation reference |
| `compliance[].raised_by` | string | yes | System or person that raised the flag |
| `compliance[].raised_at` | string (ISO 8601) | yes | When the flag was raised |
| `compliance[].status` | string | yes | `"ACTIVE"`, `"RESOLVED"`, `"WAIVED"` |

### Known compliance types

`PREMISE_CONTRADICTION`, `MINOR_INVOLVED`, `LEGAL_REVIEW`, `EDITORIAL_REVIEW`, `LEGAL_HOLD`, `VOTING_RIGHTS`, `DEFAMATION_RISK`

## `editorial_gates[]`

Structured approval gates that block specific actions until resolved.

| Path | Type | Description |
|------|------|-------------|
| `editorial_gates[].gate_id` | string | Unique gate identifier |
| `editorial_gates[].gate_type` | string | Gate category (e.g. `"LEGAL_REVIEW"`) |
| `editorial_gates[].status` | string | `"PENDING"`, `"APPROVED"`, `"REJECTED"` |
| `editorial_gates[].required_by_skill` | string | Skill that requested this gate |
| `editorial_gates[].gate_rule_id` | string | Rule ID that triggered the gate |
| `editorial_gates[].resolution_event_type` | string | Message type to emit on resolution |
| `editorial_gates[].assigned_to` | string | Desk or person responsible |
| `editorial_gates[].blocks` | string[] | Asset IDs blocked until gate resolves |

## `sources[]`

Provenance of the story's information.

| Path | Type | Description |
|------|------|-------------|
| `sources[].source_id` | string | Unique source identifier |
| `sources[].source_type` | string | `"wire"`, `"official"`, `"field_crew"`, `"pool_feed"` |
| `sources[].provider` | string | Source name (e.g. `"Associated Press"`) |
| `sources[].credibility` | string | `"PRIMARY"`, `"VERIFIED"`, `"OFFICIAL"`, `"UNVERIFIED"` |
| `sources[].received_at` | string (ISO 8601) | When the source material arrived |
| `sources[].content_hash` | string | Optional integrity hash |

## `assets[]`

Graphics packs, scripts, lower thirds, packages — the production assets tied to this story.

| Path | Type | Description |
|------|------|-------------|
| `assets[].asset_id` | string | Unique asset identifier |
| `assets[].asset_type` | string | `"graphics_pack"`, `"script"`, `"lower_third"`, `"fullscreen_graphic"`, `"package"` |
| `assets[].status` | string | `"READY"`, `"IN_PRODUCTION"`, `"INVALIDATED"` |
| `assets[].invalidated_by` | string | Compliance flag_id that invalidated it |
| `assets[].standards_clearance` | object | Optional clearance status |
| `assets[].standards_clearance.status` | string | `"CLEARED"`, `"BLOCKED"`, `"PENDING"` |
| `assets[].standards_clearance.blocked_by` | string[] | Flag IDs blocking clearance |
| `assets[].delivery_spec` | object | Optional technical delivery spec |
| `assets[].delivery_spec.format` | string | e.g. `"mxf"` |
| `assets[].delivery_spec.resolution` | string | e.g. `"1920x1080"` |
| `assets[].delivery_spec.frame_rate` | number | e.g. `29.97` |

## `ai_enrichments[]`

AI-generated content attached to the story (summaries, social posts, etc.).

| Path | Type | Description |
|------|------|-------------|
| `ai_enrichments[].enrichment_id` | string | Unique enrichment identifier |
| `ai_enrichments[].model` | string | Model used (e.g. `"claude-sonnet-4-20250514"`) |
| `ai_enrichments[].enrichment_type` | string | `"summary"`, `"social_post"`, `"article"`, `"prompter"` |
| `ai_enrichments[].confidence` | number | 0.0 — 1.0 confidence score |
| `ai_enrichments[].content` | string | The generated text |
| `ai_enrichments[].provenance` | object | Audit trail for the generation |
| `ai_enrichments[].provenance.input_sources` | string[] | Source IDs used as input |
| `ai_enrichments[].provenance.prompt_hash` | string | Hash of the prompt used |
| `ai_enrichments[].provenance.guardrails_applied` | string[] | Safety guardrails active during generation |
| `ai_enrichments[].human_reviewed` | boolean | Whether an editor has reviewed this content |
| `ai_enrichments[].generated_at` | string (ISO 8601) | When the content was generated |

## `instances[]`

Output instances — where this story is being published (linear TV, web, social, etc.).

| Path | Type | Description |
|------|------|-------------|
| `instances[].instance_id` | string | Unique instance identifier |
| `instances[].platform` | string | `"linear"`, `"web"`, `"social"` |
| `instances[].program` | string | Show/property name (e.g. `"NBC Nightly News"`) |
| `instances[].status` | string | `"ACTIVE"`, `"PENDING"`, `"KILLED"` |
| `instances[].instance_assets` | string[] | Asset IDs assigned to this instance |

## `skills_config`

Broadcaster-defined metadata about which skills should run against this story.

| Path | Type | Description |
|------|------|-------------|
| `skills_config.broadcaster` | string | Broadcaster identifier (e.g. `"NBCU"`) |
| `skills_config.skills_spec_version` | string | Skills spec version |
| `skills_config.skill_executor_id` | string | Executor instance running skills |
| `skills_config.scope_context` | string | Editorial scope (e.g. `"NBC Nightly News"`) |
| `skills_config.active_skills[]` | array | Skills configured for this context |
| `skills_config.active_skills[].skill_id` | string | Skill identifier |
| `skills_config.active_skills[].skill_version` | string | Skill version |
| `skills_config.active_skills[].skill_type` | string | `"broadcaster"`, `"vendor"`, `"reference"` |
| `skills_config.active_skills[].disclosure_level` | string | `"L1"`, `"L2"`, `"L3"` |
| `skills_config.active_skills[].migration_policy` | string | `"hot"`, `"cold"`, `"gated"` |
| `skills_config.active_skills[].skill_priority` | string | `"critical"`, `"normal"`, `"low"` |

## Using field paths in rules

The rule engine accesses fields via dot-notation paths relative to the payload root. Examples:

| Rule config `field` value | What it resolves to |
|---------------------------|---------------------|
| `headline` | `payload.headline` (string) |
| `lifecycle.phase` | `payload.lifecycle.phase` (string) |
| `compliance` | `payload.compliance` (array — checked for empty/present) |
| `priority.level` | `payload.priority.level` (string) |
| `premise.premise_changed` | `payload.premise.premise_changed` (boolean) |

Array fields (`compliance`, `sources`, `assets`, etc.) are checked for presence/absence as a whole. The built-in rule engine does not currently iterate into array elements — if you need per-element logic (e.g. "any compliance flag with type X"), implement a custom rule type in `RuleEngine.cs`.

## Seed stories

The 5 included seed stories exercise different combinations of these fields:

| Scenario | Key fields exercised |
|----------|----------------------|
| `breaking` | Full `compliance[]`, `editorial_gates[]`, `premise` with change, `instances[]` across 3 platforms |
| `breaking-no-compliance` | Empty `compliance[]` (fires `phase_with_missing_field`), `priority.level = FLASH` |
| `informal` | `headline` with informal terms (fires `term_match`), `compliance[]` with MINOR_INVOLVED + LEGAL_REVIEW |
| `clean` | All fields present and well-formed — no rules should fire |
| `election` | `DEVELOPING` phase, `premise` with high confidence, `VOTING_RIGHTS` editorial gate |

Use `GET /api/seed-stories/{scenario}` to inspect any envelope in full.
