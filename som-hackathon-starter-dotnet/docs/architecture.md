# Architecture

This document describes the system architecture of the SOM hackathon starter, the Kafka bus topology, message flow, and where vendor skill code plugs in.

## System overview

The starter is a single .NET 10 process that hosts three background services and a REST/WebSocket API behind Kestrel. In production, AP ENPS publishes `story.context` messages directly onto the Kafka bus. For local development, the built-in simulator and test producer stand in as story sources.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        .NET 10 Process (:5050)                         │
│                                                                        │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────────┐  │
│  │ SkillWorker  │  │ DashboardService │  │ SimulatorService         │  │
│  │ (consumer)   │  │ (consumer + WS)  │  │ (story generator)       │  │
│  └──────┬───────┘  └──────┬───────────┘  └──────────────────────────┘  │
│         │                 │                                            │
│  ┌──────┴─────────────────┴──────────────────────────────────────────┐ │
│  │                     REST API + WebSocket                          │ │
│  │  /api/skills   /api/pending   /api/decision   /api/simulator     │ │
│  │  /api/publish  /api/stories   /api/reset      /ws                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Static Files: wwwroot/index.html (dashboard SPA)                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Kafka (KRaft mode)  │
              │   5 topics            │
              └───────────────────────┘
```

## Kafka bus topology

Five topics form the bus. Arrows show producer → consumer relationships.

```
                    AP ENPS / Simulator / TestProducer
                                  │
                                  ▼
                        som.story.context ─────────────────┐
                                  │                        │
                                  ▼                        ▼
                            SkillWorker              DashboardService
                            ╱         ╲                    │
                           ▼           ▼                   │
                 som.skills.runs   som.skills.staging       │
                 (audit only)          │                    │
                                       ▼                   │
                                 DashboardService ◄────────┘
                                 (approval gate)
                                  ╱           ╲
                                 ▼             ▼
                       som.skills.events   som.skills.rejected
                       (production bus)    (audit trail)
                              │
                              ▼
                        Downstream consumers
                        (your production systems)
```

### Topic reference

| Topic | Purpose | Producer(s) | Consumer(s) |
|-------|---------|-------------|-------------|
| `som.story.context` | Inbound stories from the newsroom | AP ENPS, Simulator, TestProducer | SkillWorker, DashboardService |
| `som.skills.staging` | Skill outputs awaiting human approval | SkillWorker | DashboardService |
| `som.skills.events` | Approved skill outputs — the production bus | DashboardService (on approve) | Downstream systems |
| `som.skills.rejected` | Rejected outputs for audit | DashboardService (on reject) | Audit systems |
| `som.skills.runs` | Execution audit records (latency, outcome) | SkillWorker | DashboardService |

Topics auto-create on first publish in local mode (KRaft). In Confluent Cloud, pre-create them or let auto-create handle it.

## Message flow

### 1. Story arrives

A `story.context` message lands on `som.story.context`. In production this comes from AP ENPS. In local dev, it comes from the simulator (scripted scenarios or auto-stream), the test producer (seed stories via CLI or REST), or the dashboard buttons.

### 2. Skill evaluation

The **SkillWorker** consumes the story. For every skill registered in the **SkillRegistry**, it runs the skill's rules through the **RuleEngine**. Each matching rule produces a `skill.warning.raised` output.

```
story.context → SkillRegistry.All() → RuleEngine.Evaluate(rule, story) → RuleMatch[]
```

The worker never publishes directly to the production bus (`som.skills.events`). All outputs go to `som.skills.staging` for human review. A `skill.run.completed` audit record goes to `som.skills.runs` with latency and match counts.

### 3. Approval gate

The **DashboardService** consumes `som.skills.staging` and holds outputs in memory. Editors see them in the dashboard's "Pending" lane and decide:

- **Approve** → message is republished to `som.skills.events` with `approved_by` annotation
- **Reject** → message is republished to `som.skills.rejected` with `rejected_by` annotation

This is the core safety pattern: no skill output reaches production without a human decision.

### 4. Dashboard fanout

The DashboardService consumes all 5 topics and fans out every message to connected browsers via WebSocket. The dashboard SPA renders them in a 4-lane pipeline view: Stories → Runs → Pending → Decisions.

## Component responsibilities

### SkillRegistry

In-memory `ConcurrentDictionary` of `SkillDefinition` records, backed by JSON files in `skills/`. Supports CRUD via REST API — changes persist to disk immediately. New skills are picked up on the next story without restarting the worker.

### RuleEngine

Stateless interpreter that evaluates a `SkillRule` against a `JsonNode` story payload. Six built-in rule types cover most editorial logic. Each type has required `config` keys validated by Layer 1 (static validation). Returns `RuleMatch` records with detail strings rendered from `detail_template`.

Field access uses dot-notation paths (e.g. `lifecycle.phase`) walked via `GetByPath`. See [SOM v0.2 envelope reference](som-v02-envelope.md) for all available paths.

### SkillWorker

Background service (`IHostedService`). Runs a Kafka consumer loop on `som.story.context`. For each message:

1. Deserializes the SOM envelope and extracts `payload`
2. Iterates all registered skills
3. Evaluates each skill's rules via `RuleEngine`
4. Publishes `skill.warning.raised` messages to `som.skills.staging`
5. Publishes a `skill.run.completed` audit record to `som.skills.runs`

### DashboardService

Background service. Runs a Kafka consumer on all 5 topics with a separate consumer group. Responsibilities:

- WebSocket fanout to connected browsers
- In-memory pending queue for approval gate
- Approve/reject decisions with topic republishing
- Lifecycle simulation (advance phase, add compliance, rerun skills)
- Bus reset (wipe in-memory state, broadcast to clients)

### SimulatorService

Local-dev story source. Two modes:

- **Scripted scenarios** — multi-step storylines that play out in real time (e.g. breaking news cycle: story arrives → compliance flag added → phase advances → published)
- **Auto-stream** — publish a random seed story every N seconds for sustained demo load

### Skill validation (3 layers)

| Layer | File | Purpose |
|-------|------|---------|
| 1. Static | `SkillValidation.cs` | Schema + config key checks. Runs on every POST/PUT. |
| 2. Dry-run | `SkillDryRunner.cs` | Evaluate against all 5 seed stories without publishing. |
| 3. AI review | `SkillReviewer.cs` | LLM-based editorial review (Gemini or Claude). |

See [skill-validation.md](skill-validation.md) for the full reference.

## Where vendor code plugs in

Most vendors only need to create a skill JSON file. No code changes required.

```
┌─────────────────────────────────────────────────────┐
│                 Vendor touchpoints                   │
│                                                      │
│  1. skills/your-vendor.json        ◄── START HERE    │
│     Define rules using 6 built-in types              │
│                                                      │
│  2. RuleEngine.cs (optional)                         │
│     Add a custom rule type if needed                 │
│                                                      │
│  3. seed-stories/06-your-scenario.json (optional)    │
│     Add a test scenario if none of the 5 match       │
│                                                      │
│  Everything else stays unchanged:                    │
│  - Bus topology ✓                                    │
│  - Dashboard ✓                                       │
│  - Approval gate ✓                                   │
│  - Audit trail ✓                                     │
│  - Validation pipeline ✓                             │
│  - WebSocket stream ✓                                │
└─────────────────────────────────────────────────────┘
```

### For vendors building external consumers

If your skill runs as a separate process (using the Node or Python starters, or your own consumer):

1. Consume `som.story.context` from Kafka
2. Run your skill logic against the story payload
3. Publish `skill.warning.raised` (or `skill.suggestion.created`, `story.enrichment`) to `som.skills.staging`
4. Publish `skill.run.completed` to `som.skills.runs`

The dashboard's approval gate and audit trail work the same regardless of which language produced the output — it just reads from `som.skills.staging`.

## Infrastructure

### Local development

```bash
docker compose up -d    # KRaft Kafka (no ZooKeeper) + Kafka UI on :8080
dotnet run              # Worker + dashboard on :5050
```

### Confluent Cloud

Set env vars `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_API_KEY`, `KAFKA_API_SECRET` and run with `ASPNETCORE_ENVIRONMENT=Production`. The `appsettings.Production.json` binds these to SaslSsl config automatically.

### Container deployment

```bash
docker build -t som-skill-worker .
docker run -p 8080:8080 -e ASPNETCORE_ENVIRONMENT=Production \
  -e KAFKA_BOOTSTRAP_SERVERS=... -e KAFKA_API_KEY=... -e KAFKA_API_SECRET=... \
  som-skill-worker
```

## Message types reference

| Message type | Direction | Schema |
|-------------|-----------|--------|
| `story.context` | Inbound | Full SOM v0.2 envelope (see [som-v02-envelope.md](som-v02-envelope.md)) |
| `skill.warning.raised` | Outbound | `severity` (hold/flag/inform), `rule_id`, `affected_fields[]`, `detail` |
| `skill.suggestion.created` | Outbound | `variants[]` with confidence scores (Amendment 3) |
| `story.enrichment` | Outbound | `representation_type` (prompter/article/summary/social_post) (Amendment 5) |
| `skill.run.completed` | Audit | `latency_ms`, `inputs.reads[]`, `outputs.{warning_ids, suggestion_ids, enrichment_ids}` |
