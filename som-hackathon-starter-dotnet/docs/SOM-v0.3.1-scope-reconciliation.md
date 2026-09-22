# SOM v0.3.1 — `skill.warning.scope` semantics reconciliation

_Branch `som-v031-ibc-readiness` · 24 June 2026 · **PROPOSED**, awaiting ratification by the schema authority._

`scope` is one of the twelve ratified `skill.warning.raised` fields (#21). It answers **"what level did this skill fire against?"** Consumers route, group, and de-duplicate warnings on it. But three repo/spec sources state its system-level meaning three different ways, so authors and the worker can disagree on what to emit.

## The conflict

| Source | What a **system-level** skill scopes to | Destination-specific |
|---|---|---|
| `schema/som-v0.3-skill-warning.schema.json` (`scope.description`) | **Delivery** | the link |
| `SOM/skills` → `som-skills-firing` explainer | **the Asset** | the link (Compliance Gate) |
| `som-message-author` SKILL.md · `SkillWorker.cs` · project `CLAUDE.md` | **`story:{id}`** | `link:{id}` |

`scope` is a free `string` (no enum/pattern), so all three **validate** — this is a semantic inconsistency, not a schema failure. All 13 fixtures pass today regardless. Everyone agrees destination-specific skills scope to the **link**; the disagreement is only the system-level anchor.

## Recommendation — a typed `{level}:{id}` reference, level ∈ `{story, asset, link}`; drop "Delivery"

| `scope` value | Fires when | Replaces |
|---|---|---|
| `link:{link_id}` | destination-specific skill, at a link's Compliance Gate | (unchanged — already agreed) |
| `asset:{asset_id}` | system-level skill evaluating **one specific asset** (the `(asset × *)` firing) | the explainer's "the Asset", made concrete |
| `story:{story_id}` | system-level skill evaluating **story-wide** context (premise, headline, whole-story compliance) — no single asset anchor | validates the worker/author/CLAUDE.md status quo |

**Rationale**
1. At fire time the only structural anchors that exist are the **asset** being checked and the **link** it's heading to; **story** is the honest fallback for genuinely story-wide rules. Those three cover every real firing.
2. **"Delivery" is the wrong layer.** Delivery (`som.delivery.*`) is the distribution/TAMS junction — downstream of the editorial firing decision, and **PENDING the 30 June lock**. Anchoring a *ratified* field's semantics to an *unratified* layer is backwards; nothing the worker emits is Delivery-scoped.
3. Clean, parseable prefix grammar `^(story|asset|link):` — trivial for consumers to route/group on.
4. **Backwards-compatible:** everything already on the wire (`story:{id}`, `link:{id}`) stays valid; all 13 fixtures still pass. A hardening `pattern` is deferred (see below) so we don't bake levels in before the distribution layer lands.

## Consequent edits

### 1. Schema description — via the **spec folder**, then re-vendor (do NOT hand-edit `schema/`)
`SOM/schema/som-v0.3-skill-warning.schema.json`, `properties.scope.description`:

- **from:** `"The level the skill fired at — the link (destination-specific skills) or Delivery (system-level skills)"`
- **to:** `"The firing level as {level}:{id} — link:{link_id} for destination-specific skills (Compliance Gate), asset:{asset_id} for system-level skills evaluating one asset, story:{story_id} for story-wide system-level skills. Never an instance_ref."`
- Then `bash schema/sync-from-spec.sh` → `python3 schema/validate.py` → note in the migration log.
- **Optional, defer to 30 June lock:** add `"pattern": "^(story|asset|link):"`. Tightens validation; hold until we're sure no distribution-layer scope level (e.g. a Delivery-scoped audit skill) is wanted, else it would reject that.

### 2. The `SOM/skills` skills (source-of-truth in OneDrive — edit there, not the repo copy)
- `som-skills-firing`: "system-level skills scope to the Asset" → "system-level skills scope to the **asset** they evaluate (`asset:{asset_id}`), or to the **story** (`story:{story_id}`) when the check is story-wide; destination-specific skills scope to the **link** (`link:{link_id}`)."
- `som-message-author` SKILL.md (`scope is the firing level …`): add `asset:{asset_id}` alongside the existing `story:{id}` / `link:l1` examples.

### 3. `SkillWorker.cs` — applied on this branch
The worker's current rules are **story-wide** (the `RuleEngine` matches whole-story JSON paths; `RuleMatch` is `record RuleMatch(SkillRule Rule, string Detail)` — it carries **no asset_id**). So the emitted value stays `story:{story_id}` — that is *correct* under this model, not a stopgap. Only the explanatory comment changes, to name all three levels and flag the asset-level hook.

**`asset:{asset_id}` emission is a function of the PENDING firing-rule upgrade** (`(evidential_position × outlet/path)` anchor): that work must thread the matched `asset_id` into `RuleMatch` so `BuildWarning` can scope per-asset. Tracked with that upgrade, not here.

### 4. Project `CLAUDE.md` — applied on this branch
Line documenting the scope levels updated from `story:{id} / link:{id}` to `story:{id} / asset:{id} / link:{id}`.

## Validation impact
None today — `scope` is a free string; the description change and the in-repo comment/doc edits don't touch any instance, so `python3 schema/validate.py` stays 13/13. The only validation-affecting item is the **optional** `pattern`, deliberately deferred to the 30 June lock.
