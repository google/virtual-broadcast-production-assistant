# SOM v0.3.1 schemas — RATIFIED (folder name is historical)

Companion to **SOM v0.3.1 Proposal — Closing the Open Items at Release**. The objection window closed 24 June EOD UK and the content **locked on 30 June 2026** (all items accepted, incl. the 29-Jun Source re-key and `som.system.audit`; the 15-Jul TRANSCRIPT `asset_type` errata is folded in). These are **ratified contracts — integrate against them.**

The `-proposed` folder name and `$id` segment predate the lock. They are promoted **once**, in a coordinated move with the SOM spec folder (the source of truth this copy is vendored from), at the **`schema-lock-v0.3.1-errata1`** tag. Until then: **pin the tag, not the path** — content is stable, the path moves exactly once.

| File | Proposal item | Validates |
|---|---|---|
| `som-v0.3.1-link-event.schema.json` | §3.1 | `link.committed` / `link.gate_changed` / `link.withdrawn` payloads. Conditionals: committed requires committer fields; only withdrawn carries `withdrawn`. |
| `som-v0.3.1-telling-event.schema.json` | §3.2 | `telling.started` / `telling.ended` / `telling.exposed` payloads, enforcing the ratified event-pair semantics per message_type. |
| `som-v0.3.1-delivery-media-available.schema.json` | §3.3 | The TAMS junction event: Source URI (`tams://store/id`) + optional `time_range` + arrival metadata. Source re-key 29 Jun (was `flow_id`). |
| `som-v0.3.1-story-context.schema.json` | §3.3, §4, §5 | Point update of the released story-context schema, generated from it programmatically: adds `asset.media_refs[]` (Source URI + TAMS `time_range`; Source re-key 29 Jun, `flow_id` removed; `locator {store, ref}` for non-TAMS), `asset.voice_count`, `asset.authenticity_credential`, `compliance[].media_range` (Source+time restricted stretch). Everything else byte-identical in intent to the release. |
| `som-v0.3.1-system-audit.schema.json` | 30-Jun recut | `som.system.audit` governance trail: `action` ∈ CLEARED/SUPPRESSED/WITHHELD/OVERRIDDEN, `target {kind, id}`, system/user actor. |
| `examples/` | — | One valid instance per new message type. |

The released v0.3 schemas in the parent folder are untouched. The fork fields (`verification_status`/`provider_type`) remain absent here — proposal §1 resolves the fork by dropping both, with a migration map.

---

**ERRATA — 15 July 2026:** `asset_type` gains `TRANSCRIPT` in `som-v0.3.1-story-context.schema.json`. TRANSCRIPT-as-Asset was **locked at v0.3.1** (29 Jun AI-outputs decision; glossary v0.345 CONFIRMED) but the 30 Jun re-cut omitted the enum value — caught by Janet Gardner (corrections doc, 1 Jul). One-line additive fix; all existing examples unaffected. Applied to this copy and the repo-vendored copy.
