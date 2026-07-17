# SOM v0.3.1 PROPOSED schemas (12 June 2026)

Companion to **SOM v0.3.1 Proposal — Closing the Open Items at Release**. These are **proposals**, not released contracts — objection window closes 24 June EOD UK; accepted items fold into the locked v0.3 on 30 June and this folder merges into `schema/`.

| File | Proposal item | Validates |
|---|---|---|
| `som-v0.3.1-link-event.schema.json` | §3.1 | `link.committed` / `link.gate_changed` / `link.withdrawn` payloads. Conditionals: committed requires committer fields; only withdrawn carries `withdrawn`. |
| `som-v0.3.1-telling-event.schema.json` | §3.2 | `telling.started` / `telling.ended` / `telling.exposed` payloads, enforcing the ratified event-pair semantics per message_type. |
| `som-v0.3.1-delivery-media-available.schema.json` | §3.3 | The TAMS junction event: Source URI (`tams://store/id`) + optional `time_range` + arrival metadata. Source re-key 29 Jun (was `flow_id`). |
| `som-v0.3.1-story-context.schema.json` | §3.3, §4, §5 | Point update of the released story-context schema, generated from it programmatically: adds `asset.media_refs[]` (Source URI + TAMS `time_range`; Source re-key 29 Jun, `flow_id` removed), `asset.voice_count`, `compliance[].media_range` (Source+time restricted stretch). Everything else byte-identical in intent to the release. |
| `examples/` | — | One valid instance per new message type. |

The released v0.3 schemas in the parent folder are untouched. The fork fields (`verification_status`/`provider_type`) remain absent here — proposal §1 resolves the fork by dropping both, with a migration map.
