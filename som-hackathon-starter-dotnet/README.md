# SOM Hackathon Starter — .NET 10

> Skill worker template + live dashboard for the IBC 2026 SOM Hackathon

A self-contained .NET 10 starter that demonstrates the full SOM (Story Object Model) skill lifecycle on a Kafka bus, with a built-in browser dashboard for live editorial approval gating. Bring your own skill logic; the bus topology, audit trail, and approval workflow are wired in.

**New here?** [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md) is the front door — concepts, the full demo loop, building your own skill, and integrating your own system, with a map of every other doc.

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

3. Open the dashboard at **http://localhost:5050**

4. Click any seed story button in the header to publish a `story.context` event onto the bus

5. Watch the four-lane pipeline: stories → skill runs → pending approval → decisions

6. **Approve** or **reject** each staged warning to push it to `som.skills.events` or `som.skills.rejected`

## Run modes

Four valid combinations of "how is the app running" × "which Kafka broker." Pick the row that matches your setup:

| | Bundled Kafka (`docker-compose.yml`) | Existing Kafka broker |
|---|---|---|
| **`dotnet run`** | Quick start (above) | [`dotnet run` against an existing broker](#dotnet-run-against-an-existing-broker) |
| **Containerised app** | [Run the app as a container](#run-the-app-as-a-container) | [Container against an existing Kafka broker](#container-against-an-existing-kafka-broker) |

All four use the **same image and the same source**. Only the env vars and network attachment differ — see [Configuration model](#configuration-model) for why.

### Run the app as a container

When you want to exercise the production code path locally — same image, same Kestrel binding, same env-var-driven config that a real deployment uses. No .NET SDK required.

```bash
docker compose -f docker-compose.yml -f docker-compose.app.yml up --build
```

This layers `docker-compose.app.yml` on top of the bundled `docker-compose.yml`, so Kafka + Kafka UI + the app all run on the same Docker network. The app talks to the broker via the internal hostname `kafka:29092` (defined in `docker-compose.yml`'s advertised listeners).

Dashboard at http://localhost:5050 as before. To use a different host port, override `ASPNETCORE_URLS=http://+:6060` and remap with `-p 6060:6060` — see [Configuration model](#configuration-model).

### `dotnet run` against an existing broker

The default config in `appsettings.json` is `localhost:9092` / `Plaintext`. To point at a different local Kafka broker — say one already running on `:19092` — override via env vars without editing the file:

```bash
Kafka__BootstrapServers=localhost:19092 Kafka__SecurityProtocol=Plaintext dotnet run
```

`Kafka__BootstrapServers` (note the **double** underscore — `.NET`'s section delimiter) binds to `Kafka:BootstrapServers` in `IConfiguration`, which every Kafka client in the app reads from.

If your broker has `auto.create.topics.enabled=false`, pre-create the 5 SOM topics first:

```bash
docker exec <broker-container> rpk topic create som.story.context som.skills.events som.skills.rejected som.skills.runs som.skills.staging
```

### Container against an existing Kafka broker

Run the same image against any Kafka broker by overriding env vars at run time. The broker just needs to be reachable from the container by hostname. If your broker advertises an internal listener on a Docker network you can join, that's the cleanest path:

```bash
docker build -t som-skill-worker:local .
docker run --rm -p 5050:5050 --network <broker-network> -e Kafka__BootstrapServers=<broker-host>:<broker-port> -e Kafka__SecurityProtocol=Plaintext som-skill-worker:local
```

If the broker's port is exposed on the Docker host but not on a network the container can join, use `--add-host <broker-host>:host-gateway` instead of `--network`. Either way, what the broker **advertises** to clients (its `advertised.listeners`) must be reachable from inside the container — a broker that advertises `localhost:19092` is unusable from any container, because `localhost` inside the container is its own loopback. See [Configuration model](#configuration-model).

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

The skill worker never publishes directly to `som.skills.events`. Every output flows through `som.skills.staging`; the dashboard's approve/reject API republishes the payload to the production or rejection topic in a fresh dashboard-attributed envelope (new `message_id`/`timestamp`, `causation_id` = the staged message). `approved_by` / `rejected_by` ride `payload.extensions` (`com.ibc-poc.*`) — the envelope schema is closed — and the governance-grade record of the decision lands on `som.system.audit`.

## Project structure

| File | Responsibility |
|------|---------------|
| `skills/*.json` | **Data-driven skill definitions.** Drop a JSON file here to register a new skill — no code changes needed. Each file defines id, version, rules, fields read, and outputs produced. |
| `SkillDefinition.cs` | Record types for skills and rules, with JSON serialization. |
| `SkillRegistry.cs` | In-memory registry backed by `skills/*.json`. Supports CRUD via REST API — changes persist to disk. |
| `RuleEngine.cs` | Generic rule interpreter. Supports 7 rule types: `term_match`, `phase_with_missing_field`, `field_value_in`, `field_present`, `field_absent`, `field_regex`, `field_changed` (compares against the previous story version; supports one `[]` array wildcard, e.g. `assets[].acquisition_state`). |
| `SkillWorker.cs` | Background service. Consumes `som.story.context`, recall-filters skills by their `advert.operates_on`, evaluates rules via the rule engine (keeping a per-story previous snapshot for `field_changed`), publishes matches to `som.skills.staging`. |
| `DashboardService.cs` | Background service. Consumes all 7 topics, fans out via WebSocket, holds pending outputs in-memory, executes approve/reject. Also provides lifecycle simulation (advance phase, add compliance). |
| `MediaCoordinatorService.cs` | **Reference consumer** for `som.delivery.media_available`. Known asset + capture-complete → republishes the story with `acquisition_state: CAPTURED`; unmatched asset → `WITHHELD` audit on `som.system.audit` (or a v0.3.2-preview ORPHAN story with `Coordinator:OrphanPreview=true`). |
| `SimulatorService.cs` | Local-dev fallback for AP ENPS. Scripted multi-step scenarios and auto-stream mode for demos. |
| `MockMamService.cs` | Write-only TAMS stand-in: names Sources (`content/mam-catalog.json`) and emits `som.delivery.media_available`, optionally with the `com.ibc-poc.capture_complete` extension. |
| `TestProducer.cs` | Loads `seed-stories/*.json` and publishes the **full SOM envelope** to `som.story.context` (fresh `message_id`/`timestamp` per publish; the seed's `correlation_id` kept so the story lifecycle threads). |
| `Program.cs` | ASP.NET WebApplication. Hosts all background services + maps REST/WS endpoints + serves static files. |
| `KafkaOptions.cs` | POCO bound from `appsettings.json`. |
| `wwwroot/index.html` | Dashboard SPA — single file, no build step. |
| `seed-stories/*.json` | Six SOM envelopes for demo scenarios (each includes `content_refs[]` where applicable). |
| `content/*.txt` | Canned story body text served by `GET /api/content/{storyId}`. |
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

Six SOM envelopes in `seed-stories/` (v0.3.1-shaped payloads on a `som_version: "0.2.0"` wire), modeled on real broadcast scenarios:

| Scenario | Headline | Phase | Tests |
|----------|----------|-------|-------|
| `breaking` | Jones Sentencing — Federal Court Verdict Overturns Expectations | BREAKING | BREAKING with full compliance — no warnings expected. Carries asset `a2` with a bounded, CAPTURED TAMS `media_refs[]` |
| `breaking-no-compliance` | Explosion Reported at Midtown Manhattan Office Tower | BREAKING | BREAKING without compliance flags — fires `nbcu-compliance-001` |
| `informal` | Cops Bust Ring of Kids Selling Counterfeit Sneakers… | DEVELOPING | Informal language — fires `nbcu-style-001` twice (cops, kids) |
| `clean` | City Council Approves $2.1 Billion Public Transit Expansion | PUBLISHED | Clean copy — no warnings expected |
| `election` | Virginia Governor Race Too Close to Call as Polls Close | DEVELOPING | Standard developing story — no warnings expected |
| `hurricane` | Hurricane Makes Landfall Near Gulf Coast as Category 3 Storm | BREAKING | Live-feed asset `asset-landfall-feed` still **CAPTURING** with an open-ended TAMS range — the story the mock MAM and media coordinator act on |

Each envelope is a full SOM message (`som_version`, `message_id`, `correlation_id`, `originating_system`, `payload`) with rich v0.3.1 `payload` fields including `lifecycle`, `priority`, `compliance[]`, `editorial_gates[]`, `editorial_source[]`, `assets[]` (with `media_refs[]`/`acquisition_state` where media-backed), `skills_config`, and `content_refs[]`.

### content_refs

Each seed story includes a `content_refs` array pointing to `GET /api/content/{story_id}`, which serves canned body text from `content/*.txt`. This matches AP's wire shape where the Kafka message carries metadata only and the full story body lives behind a URI. Each entry includes a `source_id` linking back to the `sources[]` array for provenance. Skills that need the full text (fact-checking, summarization, NLP) should fetch from `content_refs[].uri`.

## Kafka topics

| Topic | Producer | Consumer | Purpose |
|-------|----------|----------|---------|
| `som.story.context` | TestProducer | SkillWorker, Dashboard | Inbound stories from the newsroom |
| `som.skills.staging` | SkillWorker | Dashboard | Skill outputs awaiting human decision |
| `som.skills.events` | Dashboard (on approve) | downstream | Approved outputs on the production bus |
| `som.skills.rejected` | Dashboard (on reject) | audit | Rejected outputs (`rejected_by` in `payload.extensions`) |
| `som.skills.runs` | SkillWorker | Dashboard | Audit record per skill execution (latency, outcome) |
| `som.delivery.media_available` | MockMamService (TAMS stand-in) | **MediaCoordinatorService** (acts) · Dashboard (event log) | Media-arrival announcements — see [`docs/SOM-v0.3.1-distribution-contracts.md`](docs/SOM-v0.3.1-distribution-contracts.md) |
| `som.system.audit` | MediaCoordinatorService (`WITHHELD` non-actions) · Dashboard (gate decisions `CLEARED`/`WITHHELD`) | Dashboard (event log) | Governance trail; WS1 (Aug) adds the remaining producers |

Topics auto-create on first publish in local mode. The coordinator is the participant that *acts* on media arrivals (see below); the dashboard tails both distribution topics for the bus event log (`MEDIA` / `AUDIT` lines + topic chips). Full envelopes: Kafka UI (:8080 with the bundled compose).

### Media coordinator — what happens after `media_available`

`MediaCoordinatorService` is the **reference consumer** for the TAMS junction, so vendors can watch a complete loop in one process. Per the SOM↔TAMS join, an arrival joins to an **existing** story (`asset_id → Asset → Story`) — it never creates one:

| Arrival | Coordinator behaviour |
|---|---|
| Known asset, rolling range | Availability noted (log + event-log `MEDIA` line); no story change — consumers take what exists so far |
| Known asset + `extensions["com.ibc-poc.capture_complete"]` | Republishes the story with the asset flipped `CAPTURING → CAPTURED` and the final bounded range — skills re-run on the new version, and the `nbcu-capture-001` `field_changed` rule fires an inform into Pending Approval |
| Unmatched asset | **Safe-state stop**: records a `WITHHELD` audit on `som.system.audit` ("no story references this asset; declined to act") — the skills-model non-action, observable |
| Unmatched asset, `Coordinator:OrphanPreview=true` | **v0.3.2 preview**: authors a clearly-labeled `story_type: ORPHAN` story wrapping the media instead. Off by default; ORPHAN is not in locked v0.3.1 |

## NBCU Simulator (local-dev fallback for AP ENPS)

In production, **AP ENPS is the canonical native SOM publisher** — it emits `story.context` directly onto the bus. The simulator stands in until AP is wired up, and remains useful afterwards as a self-contained test rig that vendors can run against. The 🎬 Simulator button in the dashboard header opens its control panel — one tab per tool:

1. **Scripted scenarios** — multi-step storylines that play out in real time. One at a time; starting another cancels the current one, and **Stop** cancels all remaining steps (verified: cancelled steps never reach the bus).

   | Scenario | Duration | What it demonstrates |
   |----------|----------|----------------------|
   | `breaking-news-cycle` | ~35s | BREAKING story arrives without compliance, Standards desk attaches a flag, story progresses to PUBLISHED |
   | `multi-vendor-stream` | ~12s | All seed stories published in quick succession — tests vendor skills under newsroom load |
   | `election-night` | ~50s | DEVELOPING election story slowly progresses through phases with a late VOTING_RIGHTS flag attached |
   | `compliance-review` | ~18s | Existing-compliance BREAKING story gets an extra LEGAL_HOLD flag mid-flight |
   | `media-arrival` | ~30s | The full D1·B5 loop: hurricane story (feed CAPTURING) → three growing-range MAM emits → final emit carries capture-complete → coordinator flips the asset to CAPTURED → `nbcu-capture-001` fires into Pending Approval |
   | `media-unmatched` | ~5s | The safe-state path: a UGC clip no story references → coordinator records a `WITHHELD` audit (or authors a v0.3.2-preview ORPHAN story with `Coordinator:OrphanPreview=true`) |

2. **Mock MAM** — per-source **Emit media_available** / **Emit final (capture complete)** buttons over the catalog in [`content/mam-catalog.json`](content/mam-catalog.json). Each click emits one schema-valid envelope for the source's full time range, visible immediately as a `MEDIA` line in the dashboard's bus event log — and the media coordinator reacts (see the coordinator table above). One-off emits with a custom range: `POST /api/mam/emit/{sourceId}` with `{"timeRange": "[0:0_30:0)", "captureComplete": true}` (remember `-H 'Content-Type: application/json'` — without it ASP.NET returns a bare 415).

3. **Auto-stream** — every N seconds, publish a random seed story. Useful for keeping the dashboard alive during demos and giving vendor skills a steady test load. It keeps running after the panel closes — the dashboard header shows an **Auto-stream ON** chip while it's active (click the chip to manage it).

Vendors integrating their own skill against this bus can:
1. Clone the repo
2. `docker compose up -d && dotnet run`
3. Click 🎬 Simulator → ▶ multi-vendor-stream
4. Watch their skill consume `som.story.context` and emit outputs without depending on the live AP feed

### Testing from the UI — the three traffic surfaces

The dashboard has three separate ways to put traffic on the bus. Knowing which is which saves confusion:

| Surface | Where | What it does |
|---------|-------|--------------|
| **Seed buttons** | Header ("Seed stories": Informal, Breaking, Clean, …) | One click = one `story.context` seed published. No timing, no lifecycle. |
| **Simulator panel** | Header 🎬 button | Tabs for scripted scenarios, mock-MAM emits, and the auto-stream firehose (above). |
| **Lifecycle panel** | Click any story card | Mutates *that* story — advance phase, add compliance flag, re-run — and republishes a new version, so skills re-fire. |

**Reset bus** (header 🗑) clears the dashboard *view* only: lanes, pending queue and timeline reset, and only new bus events show afterwards. It deliberately does **not** delete Kafka topics or messages (topic deletion destabilises live consumers on the single-broker setup) — old messages stay replayable via Kafka UI. For a truly empty bus: `docker compose down -v && docker compose up -d`.

The header **? Help** button shows a condensed in-app version of all of this. The full UI walkthrough is [`docs/dashboard-guide.md`](docs/dashboard-guide.md); the end-to-end journey (concepts → demos → build a skill → integrate your system) is [`docs/USER-GUIDE.md`](docs/USER-GUIDE.md).

## Skill validation (3 layers)

Every skill submission is validated. The dashboard exposes all three layers as buttons in the 🤖 Skill registry.

| Layer | What it does | When to use |
|-------|--------------|-------------|
| **1. Static** | Schema + config-key check (required fields, recognized rule types, type-specific config keys, unique rule_ids, valid severity, regex compiles) | Auto-runs on every `POST/PUT /api/skills`. Returns 400 with structured errors. |
| **2. Dry-run** | Evaluates the skill against all seed stories without publishing. Returns `{scenario → matched_rules[]}`. | Click 🧪 Dry-run on any skill. Vendors can iterate on rules and see exactly which stories fire. |
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
| `POST` | `/api/skills/dry-run` | Layer 2: dry-run a draft skill against all seed stories |
| `POST` | `/api/skills/{id}/dry-run` | Layer 2: dry-run a registered skill |
| `GET` | `/api/skills/ai-review/status` | Layer 3: AI provider availability/name |
| `POST` | `/api/skills/{id}/ai-review` | Layer 3: AI review of a registered skill |
| `GET` | `/api/pending` | Staged outputs awaiting approve/reject |
| `POST` | `/api/decision/{id}` | Body: `{decision:"approve"|"reject", reviewer:"..."}` |
| `POST` | `/api/publish/{scenario}` | Publish one seed story to the bus |
| `GET` | `/api/stories` | Story directory: live stories (ACTIVE/PLANNED) as a thin projection — a read-only cache of the bus, not a source of truth |
| `POST` | `/api/stories/{id}/rerun` | Republish cached story → skill re-runs |
| `POST` | `/api/stories/{id}/advance-phase` | Mutate `lifecycle.phase` to next canonical, republish |
| `POST` | `/api/stories/{id}/add-compliance` | Body: `{type, severity, detail}`, append flag and republish |
| `POST` | `/api/reset` | Wipe dashboard view (in-memory + UI broadcast) |
| `GET` | `/api/seed-stories` | List of seed scenario names |
| `GET` | `/api/seed-stories/{scenario}` | Raw SOM v0.2 envelope JSON |
| `GET` | `/api/mam/catalog` | Mock-MAM source catalog (TAMS stand-in) |
| `POST` | `/api/mam/emit/{sourceId}` | Emit `som.delivery.media_available`; optional body `{timeRange, assetId, captureComplete}` |
| `GET` | `/api/simulator/status` | Current sim state (running scenario, auto-stream on/off) |
| `GET` | `/api/simulator/scenarios` | All scripted scenarios available |
| `POST` | `/api/simulator/run/{id}` | Start a scripted scenario |
| `POST` | `/api/simulator/stop` | Cancel the running scenario |
| `POST` | `/api/simulator/auto/start` | Body: `{intervalSeconds: N}`, start auto-stream |
| `POST` | `/api/simulator/auto/stop` | Stop auto-stream |
| `WS` | `/ws` | Live bus event stream (every Kafka message broadcast as JSON) |

## Configuration model

The starter follows the [twelve-factor](https://12factor.net/config) pattern: **build the image once, supply per-environment values via env vars at run time.** The image is identical whether you run it on your laptop, a CI runner, or a real cluster. This is what makes the four [run modes](#run-modes) all work with the same source and Dockerfile.

What lives where:

| Where | What | Example |
|---|---|---|
| `appsettings.json` | Local-dev defaults (loaded when `ASPNETCORE_ENVIRONMENT` is unset or `Development`) | `localhost:9092`, `Plaintext` |
| `appsettings.Production.json` | Things true for **all** production-like deployments. Loaded when `ASPNETCORE_ENVIRONMENT=Production` | `SecurityProtocol: SaslSsl`, lower log level |
| Env vars at run time | Per-environment values: broker address, credentials, ports | `Kafka__BootstrapServers`, `Kafka__SaslPassword` |

**The .NET env-var convention.** Double underscore is .NET's config-section delimiter, so `Kafka__BootstrapServers` binds to the `Kafka:BootstrapServers` key in `IConfiguration`. Single-underscore names like `KAFKA_BOOTSTRAP_SERVERS` do *not* bind — they'd only register as a top-level config key.

| Env var | Binds to | Notes |
|---|---|---|
| `Kafka__BootstrapServers` | `Kafka:BootstrapServers` | Comma-separated `host:port` list |
| `Kafka__SecurityProtocol` | `Kafka:SecurityProtocol` | `Plaintext` or `SaslSsl` |
| `Kafka__SaslUsername` / `Kafka__SaslPassword` | SASL credentials | Only used when `SecurityProtocol=SaslSsl` |
| `Kafka__GroupId` | Consumer group id | Defaults to `nbcu-editorial-standards` |
| `ASPNETCORE_URLS` | Kestrel listen address | `http://+:5050` (in `Dockerfile`); `http://localhost:5050` (default for `dotnet run`) |
| `ASPNETCORE_ENVIRONMENT` | Which `appsettings.{env}.json` is loaded | `Development` (default) or `Production` |

**A broker-side gotcha worth flagging.** Kafka clients connect to the bootstrap, then redo connections to whatever the broker's `advertised.listeners` says. If the broker advertises `localhost:19092` but you connect from a container, the client gets back "go to localhost:19092" and tries its own loopback — which is empty. The broker must advertise a hostname **reachable from the client's network namespace** (e.g. `kafka:29092` for containers on the same Docker network, or `host.docker.internal:19092` from Docker Desktop containers). The bundled `docker-compose.yml` uses dual listeners (`internal://kafka:29092,external://localhost:9092`) so both Mac-native and container clients work.

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

For local exercise of the container path, the easiest route is [Run the app as a container](#run-the-app-as-a-container) — `docker compose -f docker-compose.yml -f docker-compose.app.yml up --build` builds the image and starts it alongside the bundled Kafka.

For ad-hoc builds and direct `docker run` against any broker:

```bash
docker build -t som-skill-worker .
docker run -p 5050:5050 -e ASPNETCORE_ENVIRONMENT=Production -e Kafka__BootstrapServers=... -e Kafka__SaslUsername=... -e Kafka__SaslPassword=... som-skill-worker
```

The dashboard is served on port `5050` both inside the container (via `ASPNETCORE_URLS=http://+:5050` in the Dockerfile) and locally with `dotnet run` — one port everywhere. Override with `ASPNETCORE_URLS=http://+:NNNN` and a matching `-p NNNN:NNNN`.

Update the `Dockerfile` base image tags from `10.0-preview` to `10.0` once .NET 10 reaches GA.

## Deployment to Google Cloud

This repository includes a `terraform` directory for deploying the application to Google Cloud using Managed Service for Apache Kafka and Cloud Run.

Due to circular dependencies between Artifact Registry, Cloud Build, and Cloud Run, follow these steps for the initial deployment:

1.  **Initialize Terraform**:
    ```bash
    cd terraform
    terraform init
    ```
2.  **Enable Artifact Registry API**:
    ```bash
    terraform apply -target=google_project_service.artifactregistry
    ```
3.  **Create the Repository**:
    ```bash
    terraform apply -target=google_artifact_registry_repository.repo
    ```
4.  **Build and Push Image**:
    Use the provided `cloudbuild.yaml` to build and push the image. You may need to update the substitutions in `cloudbuild.yaml` to match your region and repository name.
    ```bash
    cd ..
    gcloud builds submit --config cloudbuild.yaml .
    ```
5.  **Complete Deployment**:
    Run a full apply to create Cloud Run, Kafka resources, and the Tailscale Subnet Router.
    ```bash
    cd terraform
    terraform apply
    ```

### Remote Access & Testing Options

Depending on your laptop environment (personal vs. locked-down corporate device), pick the option that works best for you:

#### Option A: Corporate Laptop / Zero VPN (Recommended for Restricted Devices)

If third-party VPN apps like Tailscale are blocked on your corporate machine:

1. **Use the Live Cloud Run Gateway**:
   - The central skill worker and dashboard are hosted at `https://som-skill-worker-582032169035.europe-west1.run.app`.
   - **Interactive Dashboard**: Open the URL in any web browser to view live story pipelines and approve/reject staged warnings.
   - **Upload Skills via REST API**:
     ```bash
     curl -X POST https://som-skill-worker-582032169035.europe-west1.run.app/api/skills \
       -H "Content-Type: application/json" \
       -d @skills/your-skill.json
     ```
2. **Develop & Test Locally using Docker**:
   - Start local KRaft Kafka: `docker compose up -d`
   - Run the app locally: `dotnet run`
   - Iteratively build and validate your skill on `localhost:9092` before submitting your skill JSON to the central bus.
3. **Browser-Based Google Cloud Shell**:
   - Open [shell.cloud.google.com](https://shell.cloud.google.com) to run `gcloud` and test Kafka topics directly from inside Google Cloud.

---

#### Option B: Tailscale Subnet Router (For Direct Kafka TCP Access)

If you need your local code to connect directly to the Managed Kafka TCP broker (`10.0.0.0/24`):

1. **Install Tailscale**: Download from [tailscale.com/download](https://tailscale.com/download).
2. **Join with Auth Key (Fastest — No Google Login)**:
   ```bash
   tailscale up --authkey=<OBTAIN_KEY_FROM_ORGANIZER> --accept-routes
   ```
3. **Shared Account Access (Fallback)**:
   - If your organization requires joining via the shared Tailscale account, request access credentials directly from the hackathon organizers. *(Note: Credentials are never committed to git or GitHub).*

4. **Run the Application locally against Managed Kafka**:
   ```bash
   gcloud auth application-default login

   export Kafka__BootstrapServers="bootstrap.som-kafka-cluster.europe-west1.managedkafka.ibc-smart-stories.cloud.goog:9092"
   export Kafka__SecurityProtocol="SaslSsl"
   export Kafka__SaslMechanism="Plain"
   export Kafka__SaslUsername="your-email@domain.com"

   dotnet run
   ```


## License

Apache 2.0 — see [LICENSE](LICENSE).
