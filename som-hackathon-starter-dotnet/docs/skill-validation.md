# Skill Validation

The dashboard validates every skill at three layers, increasing in cost and depth. Layer 1 runs automatically on every commit; layers 2 and 3 are on-demand. All three are exposed as both REST endpoints and dashboard buttons.

| Layer | Purpose | Speed | Cost | Auto? |
|-------|---------|-------|------|-------|
| **1. Static** | Schema + config sanity | <1ms | free | ✅ runs on every `POST/PUT /api/skills` |
| **2. Dry-run** | Behavioral check against seed stories | ~5ms | free | manual via dashboard or REST |
| **3. AI review** | Editorial-quality review by an LLM | 5-30s | LLM API call | manual; opt-in via env var |

Each layer's source lives in a single file:
- Layer 1 → [`SkillValidation.cs`](../SkillValidation.cs)
- Layer 2 → [`SkillDryRunner.cs`](../SkillDryRunner.cs)
- Layer 3 → [`SkillReviewer.cs`](../SkillReviewer.cs)

---

## Layer 1 — Static validation

**What runs:** A pure C# function that walks the `SkillDefinition` and `SkillRule` records, checking every field and rule-type-specific config requirement.

**When it runs:** Automatically on `POST /api/skills` and `PUT /api/skills/{id}`. Also exposed at `POST /api/skills/validate` for vendors who want to validate without saving (e.g. inside their own CI).

**Errors vs. warnings:**
- **Errors** block the save (HTTP 400 with the structured list).
- **Warnings** allow the save but are returned in the response body and surfaced in the dashboard toast.

**What it checks:**

| Category | Check | Severity |
|----------|-------|----------|
| Identity | `id` present | error |
| Identity | `id` is vendor-prefixed (contains `/`) | warning |
| Identity | `version` present | error |
| Identity | `name`, `description` present | warning |
| Identity | `skill_type` ∈ {broadcaster, vendor, reference} | warning |
| Identity | `disclosure_level` ∈ {L1, L2, L3} | warning |
| Identity | `migration_policy` ∈ {hot, cold, gated} | warning |
| Rules | `rules[]` has at least one entry | warning |
| Per rule | `rule_id` unique within the skill | error |
| Per rule | `type` is one of the 6 supported types | error |
| Per rule | type-specific required `config` keys present | error |
| Per rule | `term_match.terms[]` and `field_value_in.values[]` non-empty | error |
| Per rule | `field_regex.pattern` compiles | error |
| Per rule | `default_severity` ∈ {hold, flag, inform} | error |
| Per rule | `affected_fields[]` non-empty | warning |

**Required config keys per rule type:**

```
term_match               → field, terms[]
phase_with_missing_field → phase, field
field_value_in           → field, values[]
field_present            → field
field_absent             → field
field_regex              → field, pattern
```

**Example error response:**

```json
{
  "error": "validation_failed",
  "errors": [
    { "severity": "error", "path": "rules[0].config.field",
      "message": "Rule type 'term_match' requires config.field." },
    { "severity": "error", "path": "rules[1].rule_id",
      "message": "Duplicate rule_id 'r1' within this skill." },
    { "severity": "error", "path": "rules[2].config.pattern",
      "message": "Invalid regex: Invalid pattern '[' at offset 1. Unterminated [] set." }
  ],
  "warnings": [
    { "severity": "warning", "path": "rules[0].affected_fields",
      "message": "affected_fields is empty. Editors won't see which story field this rule pertains to." }
  ]
}
```

**Adding a new check:** Edit `SkillValidation.Validate(skill)` or `ValidateRule(...)`. Validation is pure data-in/data-out — no logging, no side effects.

---

## Layer 2 — Dry-run

**What it does:** Loads all 5 seed stories from `seed-stories/`, evaluates the skill's rules against each via the production `RuleEngine`, returns `{scenario → matched_rules[]}` without publishing anything to Kafka.

**Why it matters:** The deterministic equivalent of "click every scenario button in the dashboard and observe what fires." Vendors get exact, reproducible feedback on a skill change without polluting the bus.

**Two flavors:**

```
POST /api/skills/dry-run                  ← body: a draft SkillDefinition (not saved)
POST /api/skills/{id}/dry-run             ← uses an already-registered skill
```

**Response shape:**

```json
{
  "skillId": "nbcu/editorial-standards",
  "totalMatches": 3,
  "scenarios": [
    {
      "scenario": "informal",
      "storyId": "lapd-counterfeit-2026-0510",
      "matches": [
        {
          "ruleId": "nbcu-style-001",
          "ruleName": "Informal language in headline",
          "severity": "flag",
          "affectedFields": ["headline"],
          "detail": "Informal term 'cops' in headline. Consider formal alternative."
        },
        { "...": "another match for 'kids'" }
      ],
      "note": null
    },
    {
      "scenario": "clean",
      "storyId": "transit-expansion-2026-0512",
      "matches": [],
      "note": "skill SKIPPED"
    }
  ]
}
```

`note` is `"skill SKIPPED"` when no rules matched, otherwise `null`.

**From the dashboard:** Open the 🤖 Skill modal → click 🧪 Dry-run on any skill row. Results render as one card per scenario, color-coded by match presence.

**From CLI:**

```bash
curl -s -X POST http://localhost:5050/api/skills/nbcu%2Feditorial-standards/dry-run \
  | jq '.scenarios[] | {scenario, matches: (.matches | length)}'
```

**Adding a new seed story:** Drop a JSON file in `seed-stories/` and register it in `TestProducer.ScenarioFiles`. The dry-runner picks it up automatically — no code changes.

---

## Layer 3 — AI review

**What it does:** Sends the skill definition + all 5 seed stories + the dry-run result to a large language model. Asks the model to evaluate the skill across five editorial axes (naming, rule logic, edge cases, descriptions, detail templates) and return structured findings.

**Architecture:**

```
                    POST /api/skills/{id}/ai-review
                                │
                                ▼
                       ISkillReviewer (interface)
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
       GeminiSkillReviewer  AnthropicSkillReviewer  NoopSkillReviewer
       (Google API key)     (Anthropic key)         (no key configured)
              │                 │
              └────────┬────────┘
                       ▼
            SkillReviewPrompt.Build(...)   ← shared prompt
            SkillReviewPrompt.ParseModelReply(...)   ← shared parser
                       │
                       ▼
            SkillReviewResult { findings[] }
```

**Provider auto-selection** (in `SkillReviewerFactory.Create`):

1. `GOOGLE_API_KEY` or `GEMINI_API_KEY` set → **Gemini** (preferred — Google is providing keys for this hackathon)
2. else `ANTHROPIC_API_KEY` set → **Claude**
3. else → `NoopSkillReviewer` (returns `available: false` with an instruction message)

**Default models (override via env var):**

| Provider | Default model | Override env var |
|----------|---------------|------------------|
| Gemini   | `gemini-2.0-flash` | `GEMINI_MODEL` |
| Anthropic | `claude-sonnet-4-5-20250929` | `ANTHROPIC_MODEL` |

**Prompt design** (in `SkillReviewPrompt.Build`): the prompt includes the full skill JSON, a slim summary of each seed story (id + headline + phase), and the dry-run result. It instructs the model to reply with **JSON only** (no markdown fences, no preamble) in a fixed schema. The Gemini call additionally sets `responseMimeType: "application/json"` for stricter JSON-mode output.

**Response shape:**

```json
{
  "available": true,
  "provider": "google/gemini-2.0-flash",
  "summary": "1-2 sentence overall assessment",
  "findings": [
    {
      "severity": "warning",
      "category": "rule_logic",
      "message": "The term_match rule for 'cops' will also match the word 'helicopters'. Add word-boundary anchors.",
      "ruleId": "nbcu-style-001"
    },
    {
      "severity": "suggestion",
      "category": "edge_cases",
      "message": "Consider also flagging 'busted' in subheads, not just headlines.",
      "ruleId": null
    }
  ],
  "error": null,
  "rawResponse": "...full model output for debugging..."
}
```

**Severity values:** `info`, `warning`, `suggestion`, `nit`
**Category values:** `naming`, `rule_logic`, `edge_cases`, `descriptions`, `detail_template`, `other`

**Error handling:** `SkillReviewPrompt.ParseModelReply` is robust to:
- Markdown code fences (```json ... ```)
- Preamble text before the JSON object
- Failed parsing (returns `error: "Could not parse model reply..."` with `rawResponse` populated for inspection)

When the provider returns an HTTP error, `error` carries the status code + truncated body, and `findings` is empty.

**Status check:** `GET /api/skills/ai-review/status` returns `{ available, provider }`. The dashboard shows a badge in the skill registry header — green when configured, muted "AI review off" otherwise.

---

## Activating AI review when the API key arrives

This is the only step that needs to happen when Google delivers the Gemini key.

### 1. Add the key to your environment

**For local dev:**

```bash
# .env (already gitignored)
GOOGLE_API_KEY=AIza...your-key-here

# (optional model override)
GEMINI_MODEL=gemini-2.0-flash    # or gemini-2.0-pro for deeper reviews
```

Then load it before starting:

```bash
export $(cat .env | xargs)
dotnet run
```

**For Docker:**

```bash
docker run -p 8080:8080 \
  -e GOOGLE_API_KEY=AIza... \
  -e KAFKA_BOOTSTRAP_SERVERS=... \
  -e KAFKA_API_KEY=... \
  -e KAFKA_API_SECRET=... \
  som-skill-worker
```

**For Cloud Run / GKE:** mount the key as a Secret Manager-backed env var. The reviewer reads it once at startup; rotation requires a pod restart.

### 2. Verify provider activation

```bash
curl http://localhost:5050/api/skills/ai-review/status
```

Expected:

```json
{ "available": true, "provider": "google/gemini-2.0-flash" }
```

In the dashboard, open 🤖 Skill — the header badge should now read `🤖 google/gemini-2.0-flash` (green).

### 3. Run a review on a known skill

```bash
curl -s -X POST http://localhost:5050/api/skills/nbcu%2Feditorial-standards/ai-review \
  | jq '{summary, finding_count: (.findings | length), provider}'
```

Then click 🤖 AI review on `nbcu/editorial-standards` in the dashboard and confirm the findings render with severity badges and category labels.

### 4. Tune (only if needed)

If the model returns too few findings, too many nits, or non-actionable feedback:

- **Edit the prompt** in `SkillReviewer.cs:SkillReviewPrompt.Build`. The current prompt asks for "3-7 findings, specific and actionable" — adjust this number or change the criteria.
- **Switch model** by setting `GEMINI_MODEL=gemini-2.0-pro` (slower, deeper) or `GEMINI_MODEL=gemini-1.5-flash-8b` (faster, cheaper).
- **Lower temperature** is already at 0.3 for consistency; raise it if you want more creative suggestions.

No code changes are required for the standard hackathon use case — the defaults are tuned for clarity and structure.

### 5. Decide on cron / pre-publish hooks (optional)

The current API is request-scoped: a vendor clicks 🤖 AI review and gets feedback. If you want **automatic AI review on every skill update**, add this to `Program.cs` after the `PUT /api/skills/{id}` handler:

```csharp
// After successful update, trigger background review
_ = Task.Run(async () =>
{
    var dryRun = await dryRunner.RunAsync(skill);
    var samples = await LoadSeedSamples();
    var review = await reviewer.ReviewAsync(skill, samples, dryRun, CancellationToken.None);
    // Persist or push to dashboard
});
```

This fires after the validated save completes, doesn't block the response, and surfaces findings asynchronously. **Not enabled by default** — adds API spend and latency, decide deliberately.

---

## Extending the system

### Adding a new rule type

1. Add the type name to `RuleEngine.Evaluate`'s switch (e.g. `"my_new_type" => EvalMyNewType(rule, story)`)
2. Implement the evaluator method
3. Add required config keys to `SkillValidation.RequiredConfigKeys`
4. Add a hint to `RULE_TYPE_HINTS` in `wwwroot/index.html` (so the rule editor's dropdown auto-fills the config skeleton)

The dry-runner and AI reviewer pick it up automatically — they're driven by the registry, not by the type list.

### Adding a new AI provider

1. Implement `ISkillReviewer` (see `GeminiSkillReviewer` as a template — ~50 lines)
2. Add provider selection to `SkillReviewerFactory.Create` based on a new env var
3. Reuse `SkillReviewPrompt.Build` and `SkillReviewPrompt.ParseModelReply` for prompt + response handling

The dashboard requires no changes — all providers return the same `SkillReviewResult` shape.

### Disabling AI review entirely

If you ship a build that should never call out to LLMs (e.g. air-gapped environments):

```csharp
// In Program.cs, replace SkillReviewerFactory.Create with:
builder.Services.AddSingleton<ISkillReviewer>(_ => new NoopSkillReviewer());
```

The dashboard will show "AI review off" and the endpoint will return the configured-state hint without making any network calls.

---

## Troubleshooting

| Symptom | Likely cause |
|---------|--------------|
| `available: false` after setting `GOOGLE_API_KEY` | Worker wasn't restarted; reviewer reads env vars only on startup |
| `Gemini API 403` | Key invalid, project missing API enable, or quota exceeded |
| `Gemini API 404` on the model | `GEMINI_MODEL` set to a name that doesn't exist or isn't enabled for your key |
| `error: "Could not parse model reply as JSON"` | Model returned prose around the JSON. Inspect `rawResponse`. Lower temperature or adjust prompt |
| Review takes >30s and times out | The HttpClient timeout is 45s; reviews on 5+ rule skills can be slow on `gemini-2.0-pro`. Use `flash` for interactive work |
| `findings: []` with no error | Model couldn't find anything to flag (a clean skill against a permissive prompt). Treat as a soft pass |

---

## Summary

- **Layer 1 (always on)** — catches structural mistakes before they hit the runtime
- **Layer 2 (on-demand)** — proves the skill behaves the way the vendor expects
- **Layer 3 (opt-in)** — adds editorial review the deterministic layers can't provide

When the Google API key arrives: add `GOOGLE_API_KEY=...` to your env, restart, verify via `/api/skills/ai-review/status`. No code changes required.
