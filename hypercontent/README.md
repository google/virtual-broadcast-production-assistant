# HyperContent — SOM integration

HyperContent is a content-personalization layer for publishers. On the Story Object Model bus it
plays two roles, contributed here as a vendor:

## Tier 2 — declarative skills (run in the reference engine)

Two skills authored in the reference rule-engine format live in
[`../som-hackathon-starter-dotnet/skills/`](../som-hackathon-starter-dotnet/skills/) and fire in
the starter with no code:

- **`hypercontent-gate-treatment-by-sensitivity.json`** — a safety gate. When a story's subject is
  sensitive, it raises `skill.warning.raised` (`severity: hold`) so a children's edition or a
  gamified/"exciting" reel of a grave story is held for standards review. It gates on the
  *audience × treatment*, never the story: a serious subject is fully reportable for a general
  audience.
- **`hypercontent-flag-on-omission.json`** — raises `skill.warning.raised` (`severity: flag`) when a
  figure or claim risks losing its required caveat/attribution as it is reshaped into a smaller
  format.

## Tier 3 — HyperContent's own agent (method stays in HC infrastructure)

Two capabilities run as HyperContent's own executor against `story.context` and publish
`skill.suggestion.created` — the skill *declares*; the method runs in HC infrastructure (as AP's
skills do). The declarations are in [`skills/`](skills/):

- **`reshape-per-path`** — one story → a *Telling* per outlet/path (article, brief, explainer, …),
  each a recombination of the story's own facts.
- **`atomise-and-bond`** — the story's **fact-graph**: atoms (facts + source attribution) linked by
  `must-travel-with` **bonds**, so a required caveat cannot be dropped from any derived telling
  (e.g. an unverified casualty figure is bonded to its "not independently verified" caveat).

## What is not here

HyperContent's atomization taxonomy, bond-derivation, and reshaping models are the vendor's method
and run in HyperContent's own executor and API — only the skill declarations and the on-wire
message shapes appear in this repository, mirroring the vendor-capability model the standard
describes.

*Contributed by HyperContent to the IBC Smart Stories accelerator.*
