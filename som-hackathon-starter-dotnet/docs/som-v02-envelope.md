# SOM Envelope & Field-Path Reference

This document covers the SOM envelope on the wire and how skill rules address fields inside it. Skills read fields via dot-notation paths (e.g. `lifecycle.phase`, `compliance`); the rule engine's `GetByPath` walks these paths against the `payload` object.

> **Payload shapes live in the schemas, not here.** Earlier versions of this file duplicated the full `story.context` field tables and drifted badly out of date. The authoritative shapes are the vendored JSON Schemas in [`schema/`](../schema/) — `story.context` is [`schema/v0.3.2-proposed/som-v0.3.2-story-context.schema.json`](../schema/v0.3.2-proposed/som-v0.3.2-story-context.schema.json) — and the spec-side *SOM Full Schema Reference v0.3.2* renders every field, enum and constraint readably. (The filename keeps its historical `som-v02-` prefix so inbound links don't break.)

All rule paths are relative to `payload`. Messages travel as full SOM envelopes on the wire; the skill worker unwraps `payload` on consume (and tolerates bare payloads from producers still on the old v0.2 shortcut).

## Envelope wrapper (outer)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `som_version` | string | yes | The **schema pack version** the payload conforms to — `"0.3.2"` on the current pack. (The SOM-048 `0.2.0` wire freeze was retired 12 Aug 2026; traffic recorded before then reads `0.2.0`.) Informative only — never branch on it; `message_type` identifies the payload family. |
| `message_id` | string (UUIDv7) | yes | Unique per message |
| `correlation_id` | string (UUIDv7) | yes | Links all messages about the same story lifecycle — thread it end-to-end |
| `causation_id` | string (UUIDv7) | no | The message that directly caused this one |
| `message_type` | string | yes | Payload family, e.g. `"story.context"`, `"skill.warning.raised"` |
| `timestamp` | string (ISO 8601) | yes | When the message was produced — lives HERE, never in the payload (decision #18) |
| `originating_system` | object | yes | Origin system: `system_id` + `system_type` required; `system_name`, `vendor`, `version` optional. (Renamed from `source` at v0.3.) |
| `topic` | string | yes | Kafka topic name (`som.` prefix) |
| `payload` | object | yes | The typed payload |
| `extensions` | object | no | Vendor fields, reverse-domain namespaced (`com.{vendor}.*`); consumers ignore-if-unknown |

The envelope is a **closed object** — unknown top-level fields fail validation, and legacy `source` / `signature` are hard-rejected.

## Renames that bite old rule configs

If a rule config predates the v0.3.x migration, these payload paths moved:

| Old path | Now |
|----------|-----|
| `sources[]` | `editorial_source[]` (credibility enum: `TRUSTED` \| `VERIFIED` \| `ENDORSED` \| `UNVERIFIED`) |
| `skills_config.broadcaster` | `skills_config.newsroom` |
| `instances[]` | **hard-rejected** since v0.3.1 — links/tellings model distribution |
| `ai_enrichments[]` | **hard-rejected** since v0.3.2 — generative output that publishes is an `assets[]` entry with `provenance` (authorship + review state); claims about content are `assertions[]` |
| `collaboration.version` | `collaboration.editing_version` |

## Using field paths in rules

The rule engine accesses fields via dot-notation paths relative to the payload root. Examples:

| Rule config `field` value | What it resolves to |
|---------------------------|---------------------|
| `headline` | `payload.headline` (string) |
| `lifecycle.phase` | `payload.lifecycle.phase` (string) |
| `compliance` | `payload.compliance` (array — checked for empty/present) |
| `priority.level` | `payload.priority.level` (string) |
| `premise.premise_changed` | `payload.premise.premise_changed` (boolean) |

Array fields (`compliance`, `assets`, etc.) are checked for presence/absence as a whole by most rule types. The `field_changed` rule type additionally supports one `[]` array wildcard (e.g. `assets[].acquisition_state`) — elements are matched across story versions by `asset_id`/`source_id`/`flag_id`/`id`. For other per-element logic (e.g. "any compliance flag with type X"), implement a custom rule type in `RuleEngine.cs`.

## `content_refs[]` in local dev

The SOM message on Kafka carries metadata only — story body text lives behind the URIs in `content_refs[]`. Skills that need to process story text (fact-checking, summarization, etc.) fetch from the `uri` field.

In the local dev environment, the starter serves canned body text at `GET /api/content/{story_id}` with open access. The `content/` directory contains `.txt` files keyed by `story_id` that the local endpoint serves. To add body text for a new seed story, drop a `{story_id}.txt` file in that directory.

## Seed stories

The 6 included seed stories exercise different combinations of fields:

| Scenario | Key fields exercised |
|----------|----------------------|
| `breaking` | Full `compliance[]`, `editorial_gates[]`, `premise` with change, `government_approval` |
| `breaking-no-compliance` | Empty `compliance[]` (fires `phase_with_missing_field`), `priority.level = FLASH` |
| `informal` | `headline` with informal terms (fires `term_match`), `compliance[]` with MINOR_INVOLVED + LEGAL_REVIEW |
| `clean` | All fields present and well-formed — no rules should fire |
| `election` | `DEVELOPING` phase, `premise` with high confidence, `VOTING_RIGHTS` editorial gate |
| `hurricane` | `acquisition_state` CAPTURING → CAPTURED (fires `field_changed` on the second publish), `media_refs[]` TAMS Source URIs |

Use `GET /api/seed-stories/{scenario}` to inspect any envelope in full.
