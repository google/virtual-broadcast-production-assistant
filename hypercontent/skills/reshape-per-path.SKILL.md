---
name: reshape-per-path
desk: distribution
triggers:
  - "publish"
  - "editorial gate cleared"
  - "reshape for path"
  - "render per outlet"
requires_review: none
confidence_threshold: 0.80
owners:
  editorial: standards@hypercontent.ai
  engineering: som-eng@hypercontent.ai
version: 0.2.0
som_schema_version: "0.3"
skill_priority: standard
som:
  subscribes:
    - story.lifecycle.changed
    - story.editorial.updated
    - story.assets.updated
  publishes:
    - skill.suggestion.created
  reads:
    - premise
    - sources
    - editorial_gates
    - planning
    - assets
    - content_refs
  writes:
    - suggestions
  scope:
    shows: []
    desks: []
    lifecycle_phases: []
  migration: cold
  tools:
    - render_telling
---

# Reshape per Path

Contributed by HyperContent to the Smart Stories skills library. Public attribution requested —
credit HyperContent as author.

**Tier 3 (autonomous agent), not a Tier-2 rule.** Reshaping is generative, so it isn't a
declarative rule dropped into the reference rule engine — it runs as HyperContent's own agent
(`../../agent/som_reshape_agent.py`): consume `story.context` → reshape into a Telling per
outlet/path → publish `skill.suggestion.created` to `som.skills.staging` for the editorial gate.
This SKILL.md is the advert; the method lives in the agent, not on the wire — exactly as a vendor
capability skill should. Verified end-to-end against the SOM reference implementation.

## When this applies

Activate when a story's editorial gate clears for a destination path — the same publish decision
Beat 5 already carries. In SOM v0.3 terms, each destination path is an **outlet**, and rendering a
story's asset for that outlet produces a **Telling** (the runtime cross-point where an Asset meets
an Outlet). The firing key is *asset category × outlet/path*: the same cleared story fans out into
one Telling per path.

## What to produce

For each destination path whose gate is `clear`, produce one Telling in that path's native format —
an article page, a feed card, a vertical video, a newsletter item, an audience edition. Emit a
single `skill.suggestion.created` carrying one variant per `(path, format)`. Each variant stages
`PENDING` on `som.skills.staging` for the gate; a human accepts, rejects, or modifies it, which the
bus records as `skill.suggestion.resolved`. The executor proposes; it never applies.

## Hard rules

- **Reshape, never generate.** Every Telling is a recombination of the story's *own* elements
  (`premise`, `sources`, and the body fetched from `content_refs[].uri`). A Telling must not
  introduce a fact that is not already in the story.
- **Held facts never render.** A fact held by its editorial gate (or by a `hold`-severity
  `skill.warning.raised` from another skill) MUST NOT appear in any Telling, in any format.
- **One publish event, every format.** Format decisions ride the same story state as the publish
  decision — no second gate, no divergent copy per path.

## Escalation

If a path's gate state is ambiguous, or a required element is held with no cleared alternative, do
not render that path's Telling; leave it for the producer. Absence of an expected Telling is
observable (see `flag-on-omission`), so nothing is dropped silently.

## Pairs with

- `flag-on-omission` — guards that each rendered Telling keeps its required elements.
- `gate-treatment-by-sensitivity` — constrains which outlets/audiences may be rendered at all.
