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
| `seed-stories/*.json` | Five SOM v0.2 envelopes for demo scenarios (each includes `content_refs[]`). |
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

Five SOM v0.2 envelopes in `seed-stories/`, modeled on real broadcast scenarios:

| Scenario | Headline | Phase | Tests |
|----------|----------|-------|-------|
| `breaking` | Jones Sentencing — Federal Court Verdict Overturns Expectations | BREAKING | BREAKING with full compliance — no warnings expected |
| `breaking-no-compliance` | Explosion Reported at Midtown Manhattan Office Tower | BREAKING | BREAKING without compliance flags — fires `nbcu-compliance-001` |
| `informal` | Cops Bust Ring of Kids Selling Counterfeit Sneakers… | DEVELOPING | Informal language — fires `nbcu-style-001` twice (cops, kids) |
| `clean` | City Council Approves $2.1 Billion Public Transit Expansion | PUBLISHED | Clean copy — no warnings expected |
| `election` | Virginia Governor Race Too Close to Call as Polls Close | DEVELOPING | Standard developing story — no warnings expected |

Each envelope is a full SOM v0.2 message (`som_version`, `message_id`, `correlation_id`, `source`, `payload`) with rich `payload` fields including `lifecycle`, `priority`, `premise`, `compliance[]`, `editorial_gates[]`, `sources[]`, `assets[]`, `ai_enrichments[]`, `instances[]`, `skills_config`, and `content_refs[]`.

### content_refs

Each seed story includes a `content_refs` array pointing to `GET /api/content/{story_id}`, which serves canned body text from `content/*.txt`. This matches AP's wire shape where the Kafka message carries metadata only and the full story body lives behind a URI. Each entry includes a `source_id` linking back to the `sources[]` array for provenance. Skills that need the full text (fact-checking, summarization, NLP) should fetch from `content_refs[].uri`.

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

### Connecting Remotely via Tailscale (for Developers)

To subscribe to Managed Kafka topics or run a local skill worker against the cloud cluster, developers need network-level access to the GCP VPC. We use Tailscale as a subnet router.

#### 1. Administrator Setup (Once after deployment)
If you did not provide a `tailscale_auth_key` in `terraform.tfvars`, the subnet router VM was provisioned but not authenticated.
1. SSH into the router VM using the command from Terraform outputs:
   ```bash
   gcloud compute ssh som-tailscale-router --tunnel-through-iap --project <project_id> --zone <zone>
   ```
2. Run `sudo tailscale up --advertise-routes=10.0.0.0/24` and follow the printed URL to authenticate.
3. In your **Tailscale Admin Console**:
   - Locate the `som-tailscale-router` device.
   - Go to **Route settings** (under the meatball menu next to the device).
   - Enable the advertised route `10.0.0.0/24`.
   - Optionally disable key expiry on this device so it doesn't disconnect.

#### 2. Developer Laptop Configuration
Each developer who needs to connect from their local machine must do the following:

1. **Install Tailscale**: Download and install Tailscale from [tailscale.com](https://tailscale.com).
2. **Join the Tailnet**: Log in to the same Tailscale network used by the project.
3. **Accept Subnet Routes**:
   - **macOS / Windows**: Open Tailscale settings and ensure **Use Subnet Routes** (or "Accept Subnet Routes") is toggled ON.
   - **Linux**: Run `sudo tailscale up --accept-routes`.
4. **Authenticate with GCP (ADC)**:
   Ensure you have the GCP SDK installed, then run:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
   *Note: Your GCP user account must be granted the `roles/managedkafka.client` role in the GCP project to authenticate with Kafka.*
5. **Run the Application**:
   Configure the application to use the GCP Managed Kafka bootstrap server (find the actual URL in your terraform outputs or ask the administrator):
   ```bash
   export Kafka__BootstrapServers="bootstrap.som-kafka-cluster.[...].managedkafka.[...].cloud.goog:9092"
   export Kafka__SecurityProtocol="SaslSsl"
   export Kafka__SaslMechanism="Plain"
   export Kafka__SaslUsername="YOUR_GCP_EMAIL@example.com" # must match the ADC login identity
   
   dotnet run
   ```


## License

Apache 2.0 — see [LICENSE](LICENSE).
