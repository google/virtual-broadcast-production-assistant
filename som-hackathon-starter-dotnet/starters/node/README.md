# SOM Skill Worker Starter — Node/TypeScript

Skill-worker-only template for the IBC 2026 SOM Hackathon. Consumes `story.context` events from Kafka, evaluates data-driven skill rules, and publishes warnings to the staging bus.

This starter does **not** include a dashboard — use the shared .NET dashboard at `http://localhost:5050` to see skill outputs, approve/reject, and run simulator scenarios.

## Quick start

**Prerequisites:** Node 20+, Docker Desktop.

1. Start Kafka (from the repo root):

   ```bash
   docker compose up -d
   ```

2. Start the shared dashboard (from `dashboard/` or the .NET project root):

   ```bash
   dotnet run
   ```

3. Install dependencies:

   ```bash
   npm install
   ```

4. Run the skill worker:

   ```bash
   npm start
   ```

5. Publish test stories (in another terminal):

   ```bash
   npm run test-producer
   ```

6. Open **http://localhost:5050** to see warnings in the dashboard pipeline.

## How to build your skill

1. **Edit `skills/example-skill.json`** (or create a new file in `skills/`). Define your `id`, `version`, `name`, and `rules[]`.

2. **Define rules** using the 6 built-in types:

   | Type | Fires when... |
   |------|--------------|
   | `term_match` | A field contains one of the specified terms |
   | `phase_with_missing_field` | Lifecycle phase matches AND a field is null/empty |
   | `field_value_in` | A field matches one of a set of values |
   | `field_present` | A field exists and is not null/empty |
   | `field_absent` | A field is missing or null/empty |
   | `field_regex` | A field matches a regex pattern |

3. **For custom rule types**, add a new case in `src/rule-engine.ts:evaluate()`.

4. **Test** with seed stories:

   ```bash
   npm run test-producer                                    # all 5 scenarios
   npx tsx src/index.ts --test-producer --story informal    # single scenario
   ```

## Seed stories

Five SOM v0.2 envelopes in `../../seed-stories/` (shared with all starters):

| Scenario | Tests |
|----------|-------|
| `breaking` | BREAKING with full compliance — no warnings expected |
| `breaking-no-compliance` | BREAKING without compliance — fires compliance rule |
| `informal` | Informal headline language — fires term_match rules |
| `clean` | Clean copy — no warnings expected |
| `election` | Developing story — no warnings expected |

## Confluent Cloud

Set env vars from `.env.example`:

```bash
export KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.confluent.cloud:9092
export KAFKA_API_KEY=your-key
export KAFKA_API_SECRET=your-secret
npm start
```

SaslSsl is auto-detected when `KAFKA_API_KEY` and `KAFKA_API_SECRET` are set.

## Project structure

| File | Purpose |
|------|---------|
| `src/index.ts` | Entry point: `--test-producer` mode or worker mode |
| `src/skill-worker.ts` | Kafka consumer loop, evaluates all skills per message |
| `src/rule-engine.ts` | Generic rule interpreter (6 types) |
| `src/skill-registry.ts` | Loads skills from `skills/*.json` |
| `src/message-builders.ts` | `buildWarning`, `buildRunRecord`, `buildSuggestion`, `buildEnrichment`, `buildVariant` |
| `src/test-producer.ts` | Loads seed stories, publishes to `som.story.context` |
| `src/config.ts` | Kafka broker, topics, auth from env vars |
| `skills/*.json` | Data-driven skill definitions |
