# Vendored SOM JSON Schemas

Machine-readable SOM schemas, **vendored into the repo** so the worker and tests can validate emitted messages without reaching the spec folder.

> **Source of truth is the SOM spec folder, not this copy.** These files are copied from
> `…/OneDrive-NBCUniversal/Documents/SOM/schema/`. Do **not** hand-edit them here — change the
> spec-folder originals (where schema decisions are made), then re-vendor with `sync-from-spec.sh`.

Vendored 2026-06-24 from the SOM v0.3.1 schema set (released v0.3 + `v0.3.1-proposed`).

| File | Validates | Status |
|---|---|---|
| `som-v0.3-envelope.schema.json` | Message envelope (#18 lock; rejects `source`, `signature`) | **Released** |
| `som-v0.3-story-context.schema.json` | `story.context` payload (rejects `instances[]`, `broadcaster_id`, `sources[]`, singular `content_ref`; lifecycle iff ACTIVE) | **Released** |
| `som-v0.3-skill-warning.schema.json` | `skill.warning.raised` twelve-field payload (rejects `instance_ref`, payload `timestamp`) | **Released** |
| `v0.3.1-proposed/som-v0.3.1-story-context.schema.json` | story.context point update (`media_refs`, `voice_count`, `media_range`) | **PENDING** 30 Jun lock |
| `v0.3.1-proposed/som-v0.3.1-link-event.schema.json` | `som.link.committed` / `.gate_changed` / `.withdrawn` | **PENDING** |
| `v0.3.1-proposed/som-v0.3.1-telling-event.schema.json` | `som.telling.started` / `.ended` / `.exposed` | **PENDING** |
| `v0.3.1-proposed/som-v0.3.1-delivery-media-available.schema.json` | `som.delivery.media_available` (TAMS junction) | **PENDING** |
| `examples/`, `v0.3.1-proposed/examples/` | One valid instance per message type | — |

Not yet in any schema (defined in the v0.3.1 spec, awaiting the lock — see the bridge doc / gap analysis):
`asset.authenticity_credential`, `media_refs[].locator` (non-TAMS), `som.system.audit`.

## Validate

```
pip install jsonschema
python3 schema/validate.py        # validates seeds + examples + mos-bridge fixtures; non-zero on failure
```

`validate.py` is the cheapest guard against drift — run it after any change to `seed-stories/`, message builders, or these schemas.

## Keeping in sync (do this whenever schema changes)

The schema can change in two directions; keep this copy current both ways:

1. **Spec changed → re-vendor here.** When the SOM spec folder's schemas change (a v0.3.1 item lands, the 30 Jun lock, etc.), run `bash schema/sync-from-spec.sh` to re-copy, then `python3 schema/validate.py`, and note it in `docs/SOM-v0.3.1-Migration-Log.md`.
2. **Code work needs a schema change → change the spec first.** Don't edit these files to make code pass. Update the spec-folder originals (and check **MOS-bridge impact** per the spec `SOM-MOS-Bridge-v0.3.1` doc), then re-vendor.
