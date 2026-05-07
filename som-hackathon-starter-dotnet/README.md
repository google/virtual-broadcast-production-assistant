# SOM Hackathon Starter — .NET 10

> Skill worker template + live dashboard for the IBC 2026 SOM Hackathon

A self-contained .NET 10 starter that demonstrates the full SOM (Semantic Object Model) v0.2 skill lifecycle on a Kafka bus, with a built-in browser dashboard for live editorial approval gating. Bring your own skill logic; the bus topology, audit trail, and approval workflow are wired in.

## Quick start

**Prerequisites:** .NET 10 SDK, Docker Desktop.

1. Start Kafka and Kafka UI

   ```bash
   docker compose up -d
   ```

2. Run the skill worker + dashboard

   ```bash
   dotnet run
   ```

   Listens on http://localhost:5050.

### Pointing at an existing broker (e.g. Redpanda on a non-default port)

The default config in `appsettings.json` is `localhost:9092` / `Plaintext`. To point at any other local broker — for example a Redpanda already running on `:19092` — override via env vars without editing the file:

```bash
Kafka__BootstrapServers=localhost:19092 \
  Kafka__SecurityProtocol=Plaintext \
  dotnet run
```

`Kafka__BootstrapServers` (note the **double** underscore — `.NET`'s section delimiter) binds to `Kafka:BootstrapServers` in `IConfiguration`, which every Kafka client in the app reads from.

If your broker has `auto.create.topics.enabled=false`, pre-create the 5 SOM topics first:

```bash
docker exec <broker-container> rpk topic create \
  som.story.context som.skills.events som.skills.rejected som.skills.runs som.skills.staging
```

3. Open the dashboard at **http://localhost:5050**

4. Click any seed story button in the header to publish a `story.context` event onto the bus

5. Watch the four-lane pipeline: stories → skill runs → pending approval → decisions

6. **Approve** or **reject** each staged warning to push it to `som.skills.events` or `som.skills.rejected`

## Architecture

```
                  TestProducer
                       │ som.story.context
                       ▼
                   SkillWorker
                    ╱       ╲
   som.skills.runs       som.skills.staging
   (audit-only)                │
                               ▼
                     DashboardService
                     (approval gate · WS fanout)
                       ╱             ╲
                  ✓ approve         ✗ reject
                      │                 │
            som.skills.events   som.skills.rejected
            (production bus)
```

The skill worker never publishes directly to `som.skills.events`. Every output flows through `som.skills.staging`; the dashboard's approve/reject API republishes the message to the production or rejection topic, annotating with `approved_by` / `rejected_by` for audit.

## Project structure

| File | Responsibility |
|------|---------------|
| `skills/*.json` | **Data-driven skill definitions.** Drop a JSON file here to register a new skill — no code changes needed. Each file defines id, version, rules, fields read, and outputs produced. |
| `SkillDefinition.cs` | Record types for skills and rules, with JSON serialization. |
| `SkillRegistry.cs` | In-memory registry backed by `skills/*.json`. Supports CRUD via REST API — changes persist to disk. |
| `RuleEngine.cs` | Generic rule interpreter. Supports 6 rule types: `term_match`, `phase_with_missing_field`, `field_value_in`, `field_present`, `field_absent`, `field_regex`. |
| `SkillWorker.cs` | Background service. Consumes `som.story.context`, evaluates every registered skill's rules via the rule engine, publishes matches to `som.skills.staging`. |
| `DashboardService.cs` | Background service. Consumes all 5 topics, fans out via WebSocket, holds pending outputs in-memory, executes approve/reject. Also provides lifecycle simulation (advance phase, add compliance). |
| `SimulatorService.cs` | Local-dev fallback for AP ENPS. Scripted multi-step scenarios and auto-stream mode for demos. |
| `TestProducer.cs` | Loads `seed-stories/*.json`, extracts the payload, publishes to `som.story.context`. |
| `Program.cs` | ASP.NET WebApplication. Hosts all background services + maps REST/WS endpoints + serves static files. |
| `KafkaOptions.cs` | POCO bound from `appsettings.json`. |
| `wwwroot/index.html` | Dashboard SPA — single file, no build step. |
| `seed-stories/*.json` | Five SOM v0.2 envelopes for demo scenarios. |
| `appsettings.json` | Local dev config (Plaintext + localhost broker). |
| `appsettings.Production.json` | Confluent Cloud SaslSsl placeholders, populated from env vars. |
| `docker-compose.yml` | Local KRaft Kafka + Kafka UI on port 8080. |
| `Dockerfile` | Multi-stage image for Cloud Run / container deploys. |

## How to build your skill

Skills are **data-driven** — you define rules in a JSON file and the rule engine evaluates them automatically. No C# code changes required for most skills.

1. **Create a skill JSON file** in `skills/` (e.g., `skills/your-vendor-name.json`). Use `skills/nbcu-editorial-standards.json` as a template. Define your `id`, `version`, `name`, `description`, and `rules[]` array.

2. **Define rules** using the 6 built-in rule types:
   - `term_match` — flag specific terms in a field (e.g., informal language)
   - `phase_with_missing_field` — fire when a lifecycle phase is active but a field is missing
   - `field_value_in` — fire when a field matches one of a set of values
   - `field_present` / `field_absent` — fire based on whether a field exists
   - `field_regex` — fire when a field matches a regex pattern

3. **Or use the REST API** to manage skills at runtime:
   - `POST /api/skills` with your skill JSON body — persists to `skills/`
   - `PUT /api/skills/{id}` to update, `DELETE /api/skills/{id}` to remove
   - The dashboard's **🤖 Skill** panel shows all registered skills

4. **Test with seed stories**: either use the dashboard's scenario buttons, the simulator, or the CLI:

   ```bash
   dotnet run -- --test-producer --story informal
   dotnet run -- --test-producer                # publishes all five
   ```

5. **For custom rule types** beyond the 6 built-in, add a new case in `RuleEngine.cs:Evaluate()`.

The bus topology, dashboard, approval gate, audit trail, and WebSocket stream all keep working unchanged.

## Seed stories

Five SOM v0.2 envelopes in `seed-stories/`, modeled on real broadcast scenarios:

| Scenario | Headline | Phase | Tests |
|----------|----------|-------|-------|
| `breaking` | Jones Sentencing — Federal Court Verdict Overturns Expectations | BREAKING | BREAKING with full compliance — no warnings expected |
| `breaking-no-compliance` | Explosion Reported at Midtown Manhattan Office Tower | BREAKING | BREAKING without compliance flags — fires `nbcu-compliance-001` |
| `informal` | Cops Bust Ring of Kids Selling Counterfeit Sneakers… | DEVELOPING | Informal language — fires `nbcu-style-001` twice (cops, kids) |
| `clean` | City Council Approves $2.1 Billion Public Transit Expansion | PUBLISHED | Clean copy — no warnings expected |
| `election` | Virginia Governor Race Too Close to Call as Polls Close | DEVELOPING | Standard developing story — no warnings expected |

Each envelope is a full SOM v0.2 message (`som_version`, `message_id`, `correlation_id`, `source`, `payload`) with rich `payload` fields including `lifecycle`, `priority`, `premise`, `compliance[]`, `editorial_gates[]`, `sources[]`, `assets[]`, `ai_enrichments[]`, `instances[]`, and `skills_config`.

## Kafka topics

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `som.story.context` | TestProducer | SkillWorker, Dashboard | Inbound stories from the newsroom |
| `som.skills.staging` | SkillWorker | Dashboard | Skill outputs awaiting human decision |
| `som.skills.events` | Dashboard (on approve) | downstream | Approved outputs on the production bus |
| `som.skills.rejected` | Dashboard (on reject) | audit | Rejected outputs (with `rejected_by`) |
| `som.skills.runs` | SkillWorker | Dashboard | Audit record per skill execution (latency, outcome) |

Topics auto-create on first publish in local mode.

## NBCU Simulator (local-dev fallback for AP ENPS)

In production, **AP ENPS is the canonical native SOM publisher** — it emits `story.context` directly onto the bus. The simulator stands in until AP is wired up, and remains useful afterwards as a self-contained test rig that vendors can run against. The 🎬 Simulator button in the dashboard header opens its control panel.

Two modes:

1. **Scripted scenarios** — multi-step storylines that play out in real time:

   | Scenario | Duration | What it demonstrates |
   |----------|----------|----------------------|
   | `breaking-news-cycle` | ~35s | BREAKING story arrives without compliance, Standards desk attaches a flag, story progresses to PUBLISHED |
   | `multi-vendor-stream` | ~12s | All 5 seed stories published in quick succession — tests vendor skills under newsroom load |
   | `election-night` | ~50s | DEVELOPING election story slowly progresses through phases with a late VOTING_RIGHTS flag attached |
   | `compliance-review` | ~18s | Existing-compliance BREAKING story gets an extra LEGAL_HOLD flag mid-flight |

2. **Auto-stream** — every N seconds, publish a random seed story. Useful for keeping the dashboard alive during demos and giving vendor skills a steady test load. Toggle from the simulator panel.

Vendors integrating their own skill against this bus can:
1. Clone the repo
2. `docker compose up -d && dotnet run`
3. Click 🎬 Simulator → ▶ multi-vendor-stream
4. Watch their skill consume `som.story.context` and emit outputs without depending on the live AP feed

## Skill validation (3 layers)

Every skill submission is validated. The dashboard exposes all three layers as buttons in the 🤖 Skill registry.

| Layer | What it does | When to use |
|-------|--------------|-------------|
| **1. Static** | Schema + config-key check (required fields, recognized rule types, type-specific config keys, unique rule_ids, valid severity, regex compiles) | Auto-runs on every `POST/PUT /api/skills`. Returns 400 with structured errors. |
| **2. Dry-run** | Evaluates the skill against all 5 seed stories without publishing. Returns `{scenario → matched_rules[]}`. | Click 🧪 Dry-run on any skill. Vendors can iterate on rules and see exactly which stories fire. |
| **3. AI review** | Ships skill JSON + seed-story samples + dry-run result to an LLM. Returns structured findings (severity / category / message). | Click 🤖 AI review. Provider auto-selects: Gemini (preferred, since Google is providing keys) → Anthropic Claude → no-op. |

**AI review setup:** Set one of these env vars and restart:
- `GOOGLE_API_KEY` or `GEMINI_API_KEY` — uses Gemini (default model `gemini-2.0-flash`, override with `GEMINI_MODEL`)
- `ANTHROPIC_API_KEY` — uses Claude (default model `claude-sonnet-4-5-20250929`, override with `ANTHROPIC_MODEL`)

The skill registry header in the dashboard shows a status badge: `🤖 google/gemini-2.0-flash` when configured, `🤖 AI review off` otherwise.

**Full reference:** [`docs/skill-validation.md`](docs/skill-validation.md) — covers all three layers in depth, the AI activation runbook, and how to extend with new rule types or AI providers.

## API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/skills` | List of registered skills (multi-skill registry) |
| `GET` | `/api/skills/{id}` | One skill's full manifest |
| `POST` | `/api/skills` | Add a new skill (validated; 400 on validation_failed) |
| `PUT` | `/api/skills/{id}` | Update a skill (validated) |
| `DELETE` | `/api/skills/{id}` | Remove a skill |
| `POST` | `/api/skills/validate` | Layer 1: static schema check (no save) |
| `POST` | `/api/skills/dry-run` | Layer 2: dry-run a draft skill against all 5 seed stories |
| `POST` | `/api/skills/{id}/dry-run` | Layer 2: dry-run a registered skill |
| `GET` | `/api/skills/ai-review/status` | Layer 3: AI provider availability/name |
| `POST` | `/api/skills/{id}/ai-review` | Layer 3: AI review of a registered skill |
| `GET` | `/api/pending` | Staged outputs awaiting approve/reject |
| `POST` | `/api/decision/{id}` | Body: `{decision:"approve"|"reject", reviewer:"..."}` |
| `POST` | `/api/publish/{scenario}` | Publish one seed story to the bus |
| `POST` | `/api/stories/{id}/rerun` | Republish cached story → skill re-runs |
| `POST` | `/api/stories/{id}/advance-phase` | Mutate `lifecycle.phase` to next canonical, republish |
| `POST` | `/api/stories/{id}/add-compliance` | Body: `{type, severity, detail}`, append flag and republish |
| `POST` | `/api/reset` | Wipe dashboard view (in-memory + UI broadcast) |
| `GET` | `/api/seed-stories` | List of seed scenario names |
| `GET` | `/api/seed-stories/{scenario}` | Raw SOM v0.2 envelope JSON |
| `GET` | `/api/simulator/status` | Current sim state (running scenario, auto-stream on/off) |
| `GET` | `/api/simulator/scenarios` | All scripted scenarios available |
| `POST` | `/api/simulator/run/{id}` | Start a scripted scenario |
| `POST` | `/api/simulator/stop` | Cancel the running scenario |
| `POST` | `/api/simulator/auto/start` | Body: `{intervalSeconds: N}`, start auto-stream |
| `POST` | `/api/simulator/auto/stop` | Stop auto-stream |
| `WS` | `/ws` | Live bus event stream (every Kafka message broadcast as JSON) |

## Confluent Cloud (production)

For shared cluster deployments:

1. Copy `.env.example` to `.env` and fill in your Confluent Cloud values
2. Export the variables (or feed them to your runtime)
3. Run with `ASPNETCORE_ENVIRONMENT=Production` so `appsettings.Production.json` is loaded:

   ```bash
   export $(cat .env | xargs)
   ASPNETCORE_ENVIRONMENT=Production dotnet run
   ```

`appsettings.Production.json` sets `SecurityProtocol=SaslSsl` and leaves the bootstrap server and SASL credentials unset — the env vars (`Kafka__BootstrapServers`, `Kafka__SaslUsername`, `Kafka__SaslPassword`) populate them at runtime via `IConfiguration`'s env-var provider. Double underscores (`__`) are `.NET`'s section delimiter and bind to `Kafka:BootstrapServers` etc.

## Building a container image

```bash
docker build -t som-skill-worker .
docker run -p 5050:5050 \
  -e ASPNETCORE_ENVIRONMENT=Production \
  -e Kafka__BootstrapServers=... \
  -e Kafka__SaslUsername=... \
  -e Kafka__SaslPassword=... \
  som-skill-worker
```

The dashboard is served on port `5050` both inside the container (via `ASPNETCORE_URLS=http://+:5050` in the Dockerfile) and locally with `dotnet run` — one port everywhere.

Update the `Dockerfile` base image tags from `10.0-preview` to `10.0` once .NET 10 reaches GA.

## License

Apache 2.0 — see [LICENSE](LICENSE).
