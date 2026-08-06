---
name: atomise-and-bond
desk: standards
triggers:
  - "atomize"
  - "fact graph"
  - "extract atoms"
  - "verification bonds"
requires_review: standards
confidence_threshold: 0.85
owners:
  editorial: standards@hypercontent.ai
  engineering: som-eng@hypercontent.ai
version: 0.2.0
som_schema_version: "0.3"
skill_priority: standard
som:
  subscribes:
    - story.lifecycle.changed
    - story.premise.updated
    - story.enrichment.added
  publishes:
    - skill.suggestion.created
  reads:
    - headline
    - premise
    - story_meaning
    - sources
    - content_refs
  writes:
    - suggestions
  scope:
    shows: []
    desks: []
  migration: cold
  tools:
    - atomise_and_bond
---

# Atomise & Bond

Authored by HyperContent for the Smart Stories skills library. Public attribution requested —
credit HyperContent as author.

**Tier 3 (autonomous agent).** HyperContent's core capability: it decomposes a story into a
**fact-graph** — an ordered set of **atoms** (single factual claims, each carrying its source
attribution) linked by **bonds**. A bond of kind `must-travel-with` ties a fact to the caveat it
cannot be shown without: an unverified casualty figure is bonded to its *"not independently
verified"* caveat, so any downstream telling (a reel, a brief, a children's edition) that keeps the
figure **structurally cannot drop the caveat**. The fact-graph is the substrate the reach and
governance skills stand on — `reshape-per-path` recombines atoms (never inventing facts), and
`flag-on-omission` / `gate-treatment-by-sensitivity` are enforceable *because* the required
companions are bonded, not merely hoped for.

## What it produces

A story enrichment published as `skill.suggestion.created` (a producer accepts it into the story
context), carrying:

- **atoms** — `{ id, text, source_ref, span, required }`. `source_ref` is who the claim is
  attributed to; `span` locates it in the source; `required: true` marks a claim that must not be
  dropped from any telling.
- **bonds** — `{ from, to, kind }`, where `kind: "must-travel-with"` means the `to` atom (a caveat,
  attribution, or qualifier) must accompany the `from` atom in every derived telling.

## What stays private

Only the fact-graph *shape* above goes on the wire. **How** atoms are typed and **how** bonds are
derived — HyperContent's atom taxonomy, the bond-derivation model, the prompts — live entirely in
the agent ([`../../agent/`](../../agent/), tool `atomise_and_bond` → HyperContent's
`/v1/som/atomize`) and never appear in the skill or on the bus. The skill advertises the capability;
the method is HyperContent's.

## Escalation

Atoms marked `required` and every `must-travel-with` bond are surfaced to the standards desk as the
non-droppable core of the story. Verified end-to-end against the SOM reference implementation.
