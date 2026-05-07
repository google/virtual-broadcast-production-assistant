# Contributing — SOM Hackathon Starter

This guide covers how to submit a skill for the IBC 2026 SOM Hackathon.

## Before you start

1. Clone the repo and get the dashboard running locally:

   ```bash
   docker compose up -d
   dotnet run
   ```

2. Open http://localhost:5050 and click a few scenario buttons to see the built-in `nbcu/editorial-standards` skill in action.

3. Read the [README](README.md) for architecture context and the [skill validation docs](docs/skill-validation.md) for the full testing pipeline.

## Skill naming conventions

Every skill must have a vendor-prefixed `id` using the format:

```
<vendor>/<skill-name>
```

Examples: `vizrt/graphics-validator`, `ross/template-checker`, `avid/rundown-gaps`.

The prefix should match your company or product name. The skill name should be lowercase, hyphenated, and describe what the skill does — not how it does it.

Rule IDs within a skill should also be prefixed for uniqueness:

```
<vendor>-<category>-<nnn>
```

Examples: `vizrt-gfx-001`, `ross-tmpl-002`.

## Creating your skill

### Option A — Drop a JSON file (recommended)

1. Copy `skills/nbcu-editorial-standards.json` as a starting point.
2. Create `skills/<your-vendor>.json` with your skill definition.
3. The worker picks it up automatically on next restart — no code changes needed.

### Option B — REST API at runtime

```bash
curl -X POST http://localhost:5050/api/skills \
  -H "Content-Type: application/json" \
  -d @skills/your-vendor.json
```

Changes persist to `skills/` on disk. You can also use `PUT /api/skills/{id}` and `DELETE /api/skills/{id}`.

### Required fields

| Field | Required | Notes |
|-------|----------|-------|
| `id` | yes | Vendor-prefixed (`vendor/name`) |
| `version` | yes | Semver string |
| `name` | recommended | Human-readable display name |
| `description` | recommended | What the skill does, for editors |
| `skill_type` | recommended | `vendor`, `broadcaster`, or `reference` |
| `disclosure_level` | recommended | `L1`, `L2`, or `L3` |
| `rules[]` | yes | At least one rule |

### Rule types

The rule engine supports 6 built-in types. Each has specific `config` keys:

| Type | Config keys | What it does |
|------|-------------|--------------|
| `term_match` | `field`, `terms[]`, `case_sensitive?` | Flags matching terms in a text field |
| `phase_with_missing_field` | `phase_field?`, `phase`, `field` | Fires when lifecycle phase matches but a field is empty |
| `field_value_in` | `field`, `values[]` | Fires when a field matches one of a set of values |
| `field_present` | `field` | Fires when a field exists and is non-empty |
| `field_absent` | `field` | Fires when a field is missing or empty |
| `field_regex` | `field`, `pattern`, `case_sensitive?` | Fires when a field matches a regex |

If your skill logic can't be expressed with these 6 types, you can add a custom type in `RuleEngine.cs` — see the [extending section](docs/skill-validation.md#adding-a-new-rule-type).

## Testing requirements

Before submitting, your skill must pass all three validation layers.

### Layer 1 — Static validation (automatic)

Runs on every `POST /api/skills`. Checks schema, config keys, rule ID uniqueness, severity values, regex compilation. Must pass with zero errors. Warnings are acceptable but should be reviewed.

### Layer 2 — Dry-run (required before submission)

Run your skill against all 5 seed stories:

```bash
curl -s -X POST http://localhost:5050/api/skills/<your-vendor-id>/dry-run | jq .
```

Or click **🧪 Dry-run** in the dashboard's skill panel.

**Minimum requirement:** your skill must match at least one seed story. If none of the 5 scenarios trigger your rules, either your rules are too narrow or you need to add a seed story that demonstrates your use case (see below).

### Layer 3 — AI review (recommended)

If a Gemini or Anthropic API key is configured, click **🤖 AI review** on your skill for editorial-quality feedback. Not required, but strongly encouraged — the model catches edge cases and naming issues that static checks miss.

## Adding a seed story

If the existing 5 scenarios don't exercise your skill:

1. Create a JSON file in `seed-stories/` following the SOM v0.2 envelope format (see [docs/som-v02-envelope.md](docs/som-v02-envelope.md)).
2. Register it in `TestProducer.cs` by adding an entry to `ScenarioFiles`.
3. The dry-runner and dashboard pick it up automatically.

Name your file with a two-digit prefix for ordering: `06-your-scenario.json`.

## Submission checklist

Before committing to the shared repo:

- [ ] Skill `id` is vendor-prefixed (`vendor/skill-name`)
- [ ] All rule IDs are unique and vendor-prefixed
- [ ] `version` is set (start with `0.1.0`)
- [ ] `name` and `description` are present and editor-friendly
- [ ] Layer 1 passes with zero errors
- [ ] Layer 2 dry-run matches at least one seed story
- [ ] Layer 3 AI review run (if available) — no unresolved warnings
- [ ] `detail_template` on each rule produces a clear, actionable message
- [ ] No hardcoded file paths or environment-specific config in your skill JSON

## Pull request expectations

1. **One skill per PR.** Keep vendor skills isolated so they can be reviewed independently.
2. **Include dry-run output** in the PR description showing which scenarios your skill matches.
3. **Don't modify other vendors' skills.** If you find an issue, open a separate issue or PR.
4. **Don't modify core infrastructure** (`SkillWorker.cs`, `DashboardService.cs`, `Program.cs`, etc.) unless you're fixing a bug — and call that out clearly.
5. **Seed stories are shared.** If you add one, make sure it doesn't break existing skills' dry-run expectations. Run all skills' dry-runs before pushing.

## Directory structure

```
skills/
  nbcu-editorial-standards.json    ← broadcaster reference skill
  your-vendor.json                 ← your skill goes here
  another-vendor.json

seed-stories/
  01-breaking-courthouse.json      ← shared across all skills
  02-developing-election.json
  03-informal-headline.json
  04-clean-transit.json
  05-breaking-no-compliance.json
  06-your-scenario.json            ← optional, if needed
```

All skills live in a flat `skills/` directory (no vendor subdirectories). The filename should match your skill's `id` with `/` replaced by `-`.

## Questions?

Open an issue in the repo or reach out on the hackathon Slack channel.
