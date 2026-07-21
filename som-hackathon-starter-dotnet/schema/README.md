# Vendored SOM JSON Schemas

Machine-readable SOM schemas, **vendored into the repo** so the worker and tests can validate emitted messages without reaching the spec folder.

> **Source of truth is the SOM spec folder, not this copy.** These files are copied from
> `…/OneDrive-NBCUniversal/Documents/SOM/schema/`. Do **not** hand-edit them here — change the
> spec-folder originals (where schema decisions are made), then re-vendor with `sync-from-spec.sh`.

Vendored 2026-06-24 from the SOM v0.3.1 schema set (released v0.3 + `v0.3.1-proposed`); re-vendored 2026-07-17 with the 30-Jun lock recut (Source re-key, `som.system.audit`) and the 15-Jul TRANSCRIPT errata.

> **Status: v0.3.1 is RATIFIED.** The objection window closed 24 Jun and the content **locked on 30 Jun 2026** (plus the 15-Jul TRANSCRIPT `asset_type` errata). The `v0.3.1-proposed/` folder name and the `-proposed` segment in each `$id` are **historical** and will be promoted **once**, in a coordinated move with the spec folder, at the **`schema-lock-v0.3.1-errata1`** tag (due 25 Jul 2026). **Partners: pin the tag, not the `$id` path** — the content is stable; the path moves exactly once at promotion.

| File | Validates | Status |
|---|---|---|
| `som-v0.3-envelope.schema.json` | Message envelope (#18 lock; rejects `source`, `signature`) | **Released** |
| `som-v0.3-story-context.schema.json` | `story.context` payload (rejects `instances[]`, `broadcaster_id`, `sources[]`, singular `content_ref`; lifecycle iff ACTIVE) | **Released** |
| `som-v0.3-skill-warning.schema.json` | `skill.warning.raised` twelve-field payload (rejects `instance_ref`, payload `timestamp`) | **Released** |
| `v0.3.1-proposed/som-v0.3.1-story-context.schema.json` | story.context point update (`media_refs` incl. `locator`, `voice_count`, `media_range`, `authenticity_credential`) | **LOCKED** 30 Jun |
| `v0.3.1-proposed/som-v0.3.1-link-event.schema.json` | `som.link.committed` / `.gate_changed` / `.withdrawn` | **LOCKED** 30 Jun |
| `v0.3.1-proposed/som-v0.3.1-telling-event.schema.json` | `som.telling.started` / `.ended` / `.exposed` | **LOCKED** 30 Jun |
| `v0.3.1-proposed/som-v0.3.1-delivery-media-available.schema.json` | `som.delivery.media_available` (TAMS junction) | **LOCKED** 30 Jun |
| `v0.3.1-proposed/som-v0.3.1-system-audit.schema.json` | `som.system.audit` governance trail | **LOCKED** 30 Jun |
| `examples/`, `v0.3.1-proposed/examples/` | One valid instance per message type | — |

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
