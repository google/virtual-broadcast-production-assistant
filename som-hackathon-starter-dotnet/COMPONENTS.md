# SOM Hackathon Starter — High-Level Components

Map of the `som-hackathon-starter-dotnet/` codebase, oriented toward a team taking the **story-publisher role** on the SOM bus (replacing the AP ENPS stand-in).

## At a glance

```
┌──────────────────────────┐
│  1. Story ingress        │ ← your seat
│  TestProducer / Simulator│
└──────────┬───────────────┘
           │ som.story.context
           ▼
┌──────────────────────────┐
│  2. Skill execution      │
│  SkillWorker + RuleEngine│
│  + SkillRegistry         │
└──────────┬───────────────┘
           │ som.skills.staging   + som.skills.runs (audit)
           ▼
┌──────────────────────────┐
│  3. Approval gate        │
│  DashboardService + UI   │
└──────────┬───────────────┘
   approve │ reject
           ▼
   som.skills.events / som.skills.rejected
```

Everything below the ingress layer is consumer-side and untouched by a publisher integration.

---

## 1. Story ingress (your seat)

| Component | File | Role |
|---|---|---|
| `TestProducer` | `TestProducer.cs` | Load `seed-stories/*.json`, publish to `som.story.context`. CLI: `dotnet run -- --test-producer`. |
| `SimulatorService` | `SimulatorService.cs` | Scripted scenarios + auto-stream. REST + dashboard 🎬 panel. |
| Seed envelopes | `seed-stories/*.json` | 5 SOM v0.2 reference messages (breaking, election, informal, clean, no-compliance). |
| Story body hosting | `content/*.txt` + `GET /api/content/{id}` in `Program.cs` | Body served behind URI per `content_refs[]`. AP wire shape — Kafka carries metadata, body lives at HTTP URI. |

**To replace:** publish a SOM v0.2 envelope to `som.story.context` with `key = story_id`. Host body somewhere reachable, list URI in `content_refs[]`. Re-publish on phase changes / compliance updates.

---

## 2. Skill execution engine (consumer-side)

| Component | File | Role |
|---|---|---|
| `SkillWorker` | `SkillWorker.cs` | `BackgroundService`. Consume `som.story.context` → run every registered skill → publish staging warnings + run audit. |
| `RuleEngine` | `RuleEngine.cs` | Generic interpreter. 6 rule types: `term_match`, `phase_with_missing_field`, `field_value_in`, `field_present`, `field_absent`, `field_regex`. Pure function `(rule, story) → matches`. |
| `SkillRegistry` | `SkillRegistry.cs` | `ConcurrentDictionary` backed by `skills/*.json` on disk. CRUD persists through to filesystem. |
| `SkillDefinition` | `SkillDefinition.cs` | Record types (`SkillDefinition`, `SkillRule`, `Citation`) + JSON serialization options. |
| Vendor skills | `skills/*.json` | Data-driven rule definitions. Includes `nbcu-editorial-standards`, `ap-demographics-advisor`, `ap-follow-up-ideas`, `ap-wire-fact-check`. |

---

## 3. Approval gate + audit

| Component | File | Role |
|---|---|---|
| `DashboardService` | `DashboardService.cs` | Consume all 5 topics. WebSocket fan-out. Hold pending outputs in memory. Execute approve/reject → republish to `events`/`rejected` with `approved_by`/`rejected_by`. Also: lifecycle mutations (advance-phase, add-compliance, rerun). |
| Dashboard SPA | `wwwroot/index.html` | 112 KB single-file SPA. 4-lane pipeline view + skill registry panel + simulator panel. No build step. |

---

## 4. Skill validation (3 layers)

| Layer | Component | File | Role |
|---|---|---|---|
| 1. Static | `SkillValidation` | `SkillValidation.cs` | Schema + config-key check, regex compile, unique rule_ids. Runs on every `POST`/`PUT /api/skills`. |
| 2. Dry-run | `SkillDryRunner` | `SkillDryRunner.cs` | Evaluate skill against the 5 seed stories without publishing. Returns `{scenario → matched_rules[]}`. |
| 3. AI review | `SkillReviewer` | `SkillReviewer.cs` | LLM review. Provider chain: Gemini (`GOOGLE_API_KEY` / `GEMINI_API_KEY`) → Claude (`ANTHROPIC_API_KEY`) → no-op. |

---

## 5. Kafka plumbing

| Component | File | Role |
|---|---|---|
| `KafkaOptions` | `KafkaOptions.cs` | POCO bound from `appsettings*.json` and env vars (`Kafka__BootstrapServers`, etc.). |
| `KafkaAuthHelper` | `KafkaAuthHelper.cs` | Plaintext / SaslSsl / OAuth (GCP Managed Kafka). Builder hooks for producer/consumer. |

### Topics

| Topic | Producer | Consumer | Purpose |
|---|---|---|---|
| `som.story.context` | **publisher (you)** | SkillWorker, Dashboard | Inbound stories |
| `som.skills.staging` | SkillWorker | Dashboard | Outputs awaiting human decision |
| `som.skills.events` | Dashboard (approve) | downstream | Approved outputs — production bus |
| `som.skills.rejected` | Dashboard (reject) | audit | Rejected outputs |
| `som.skills.runs` | SkillWorker | Dashboard | One audit record per skill execution |

---

## 6. Host + transport

| Component | File | Role |
|---|---|---|
| `Program.cs` | ASP.NET `WebApplication` | DI registration, hosted services, REST endpoints, WebSocket `/ws`, static file serving. |
| `appsettings.json` | config | Local dev: Plaintext + `localhost:9092`. |
| `appsettings.Production.json` | config | SaslSsl placeholders; env vars populate at runtime. |
| `.env.example` | template | Confluent Cloud credentials shape. |

---

## 7. Infrastructure / deploy

| Component | File | Role |
|---|---|---|
| Local Kafka | `docker-compose.yml` | KRaft Kafka + Kafka UI on `:8080`. Dual listeners (`kafka:29092` internal, `localhost:9092` external). |
| App overlay | `docker-compose.app.yml` | Runs the app container alongside bundled Kafka on the same Docker network. |
| Image | `Dockerfile` | Multi-stage .NET 10. Kestrel `:5050`. |
| GCP infra | `terraform/` | Managed Service for Apache Kafka + Cloud Run + Artifact Registry. |
| GCP build | `cloudbuild.yaml` | Image build pipeline. |

---

## 8. Non-.NET starters (peer skill workers)

| Path | Role |
|---|---|
| `starters/node` | TypeScript skill worker template. Own `skills/`. |
| `starters/python` | Python skill worker template. Own `skills/`. |

These are independent vendor skeletons — they consume the same bus, not part of the main app.

---

## For the story-publisher integration

Concrete contract you owe the bus:

1. **Topic:** `som.story.context`.
2. **Key:** `story_id` (string — drives partitioning so updates for the same story land in order).
3. **Value:** SOM v0.2 envelope JSON. Required top-level fields: `som_version`, `message_id`, `correlation_id`, `source`, `payload`.
4. **Payload shape:** `story_id`, `lifecycle.phase`, `headline`, `priority`, `premise`, `compliance[]`, `editorial_gates[]`, `sources[]`, `assets[]`, `ai_enrichments[]`, `instances[]`, `skills_config`, `content_refs[]`. See `docs/som-v02-envelope.md` for the canonical spec and `seed-stories/*.json` for working examples.
5. **Content hosting:** if the body is non-trivial, publish metadata only and serve the body at the HTTP URI listed in `content_refs[].uri`. The starter does this via `GET /api/content/{story_id}` reading from `content/*.txt`. Each `content_refs` entry includes a `source_id` linking back to `sources[]` for provenance.
6. **Updates:** when story state changes (phase advances, compliance flag added, headline rewritten), re-publish a new envelope under the same `story_id`. The worker re-evaluates and the dashboard sees the new pass.
7. **Auth:** match the target cluster. For Confluent Cloud / GCP Managed Kafka, set `Kafka__BootstrapServers`, `Kafka__SaslUsername`, `Kafka__SaslPassword` env vars; the starter's `KafkaAuthHelper` shows the producer config wiring.

### Reference reading order

1. `docs/som-v02-envelope.md` — canonical envelope spec.
2. `docs/message-contracts.md` — full bus message catalog (story.context, skill.warning.raised, skill.run.completed, etc.).
3. `docs/architecture.md` — system-level diagram and rationale.
4. `docs/skill-validation.md` — only relevant if you also plan to publish skill definitions.
5. `seed-stories/01-breaking-courthouse.json` (and siblings) — working SOM v0.2 envelopes to crib from.
