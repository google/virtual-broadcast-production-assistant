# SOM v0.3.2 schemas — the IBC pack (scaffolded 9 July 2026)

**v0.3.2 is the IBC target** (decided early Aug 2026; open items dispositioned 12 Aug — see below). Point updates generated programmatically from the locked `v0.3.1-proposed/` set (30 June lock + Source re-key). **Only changed schemas live here** — `link-event` and `system-audit` are unchanged at v0.3.2 and remain authoritative in `../v0.3.1-proposed/`. `som_version` on the wire now carries the **pack version (`0.3.2`)** — the SOM-048 `0.2.0` wire freeze is retired (12 Aug 2026): hackathon users read `0.2.0` against v0.3.1-shaped payloads and reasonably concluded they were on the wrong schema.

| File | Changes | Provenance |
|---|---|---|
| `som-v0.3.2-story-context.schema.json` | (1) `asset_type` + `TRANSCRIPT` (**locked v0.3.1** 29 Jun — the 30 Jun re-cut omitted it; restored by the 15 Jul v0.3.1 errata, carried here) + `SUMMARY`/`SOCIAL_POST`/`ARTICLE`/`ANALYSIS` (generative promotions; registry direction). (2) `asset.provenance` — authorship-general object (`author` HUMAN/MODEL; `model` only when MODEL; `confidence` optional/asset-type-specific; shared `review` state). (3) `assertions[]` — FACT_CHECK/DETECTION/MATCH with `target` (audit target set), typed `claim`, `review` PENDING/CONFIRMED/REJECTED; **`ai_enrichments[]` hard-rejected** (narrowed to assertions; `human_reviewed` boolean retired — REJECTED entries are marked, not deleted). (4) `story_type` + `ORPHAN` — minimal shell story for unmatched UGC clips (**PROPOSED, pending WG**). (5) `editorial_gate.blocks[]` contract restored — `{kind ASSET\|PHASE, ref}`; bare strings deprecated. | AI-outputs refactor note (29 Jun, ratified); Morag 5 Jul asks + John 9 Jul reply; element-level-hold reply 1 Jul; Janet corrections 1 Jul |
| `som-v0.3.2-telling-event.schema.json` | `transforms[]` — edge reshapes on the Telling: application-ordered, **append-only**, `{transform_type, params, applied_by, applied_at}`; `transform_type` a governed-but-extensible registry (seed CROP/TRIM/CAPTION_BURN, `x-` vendor). Invariant: a telling-side transform **never lifts** a `compliance[].media_range` hold (holds evaluate against the Source range). Boundary: reshape pushed into TAMS → new Source as today. | Morag 5 Jul ask §3 + John 9 Jul reply |
| `som-v0.3.2-delivery-media-available.schema.json` | **Locator-on-arrival** — the arrival event gains `anyOf(source \| locator)`, mirroring asset-side `media_refs[]`. Media in SOM is any media, not just TAMS: locked v0.3.1 lets an asset *reference* non-TAMS media via `locator` but requires a `tams://` source to *announce* its arrival — this closes that asymmetry. OPEN: `time_range` semantics against a non-TAMS locator. | John, 9 Jul (out of Janet's diagram review) |
| `examples/` | Hurricane Beat 6 (Janet's corrected sample, **re-corrected**: no embedded `links[]` — link records are bus events per decision #3, `usage[]` is the asset-side index; per-destination clearance stays `link.compliance_gate_status` on the link events); orphan shell + MATCH-PENDING assertion; telling with TRIM→CROP→CAPTION_BURN. | — |
| `validate.py` | 22 checks: 3 schema-validity, 4 v0.3.2 examples, 2 v0.3.1 regressions (delivery-tams; example sans `ai_enrichments`), 13 negative cases. `python3 validate.py` (needs `jsonschema`). | — |

## Deferred at the v0.3.2 pack (12 Aug 2026)

Dispositioned by the schema authority; none of these holds the IBC pack. Interim rules are normative until the deferred item lands (v0.4 unless noted).

- **`ORPHAN`** — ships in v0.3.2 as specified (Option-B; shell ALWAYS retires to ARCHIVED, Morag accepted 13 Jul). Residual debate — reject semantics, two-shells-one-story — tracks to the v0.4 review.
- **DETECTION `claim` shape** — deferred to the registry work (v0.4). FACT_CHECK (`metric`+`value`) and MATCH (`story_id`) stay pinned as-is. Interim: DETECTION `claim` is a free object; consumers tolerate unknown keys.
- **`transforms[].params` per-type shapes** — settle with the transform-type registry (v0.4). Interim: per-type objects as documented (CROP / TRIM / CAPTION_BURN); consumers ignore unknown keys.
- **`time_range` on a non-TAMS `locator`** — deferred to v0.4. Interim: well-defined only against a TAMS `source`; producers SHOULD omit it on a bare `locator`, consumers MUST NOT assume offset-from-zero.
- **"Live ingest source" as a first-class story field** — no shape drafted before the pack, so it slips to v0.4 (per its own rule). Continues to ride `extensions.com.{vendor}.livestream_url` (proposed out of Trint's integration, 15 Jul; a public livestream URL to transcribe is a live ingest input, not store-managed media, so it is neither a `media_refs[]` entry nor an arrival event).

## Still owed (process debt — does not change shapes)

- **MOS-bridge reconciliation notes** (per the schema-change checklist): the Asset-shape/Telling changes here (assertions, provenance, transforms) each need their one-liner in the bridge doc before the lock note circulates.
- **Migration guidance**: `ai_enrichments` → assets/assertions is breaking; the ANALYSIS disambiguation rule (does it ever get a Telling?) belongs in the migration note.
