# SOM Skill Worker Starter — Python

Skill-worker-only template for the IBC 2026 SOM Hackathon. Consumes `story.context` events from Kafka, evaluates data-driven skill rules, and publishes warnings to the staging bus.

This starter does **not** include a dashboard — use the shared .NET dashboard at `http://localhost:5050` to see skill outputs, approve/reject, and run simulator scenarios.

## Quick start

**Prerequisites:** Python 3.11+, Docker Desktop.

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
   pip install -e .
   ```

4. Run the skill worker:

   ```bash
   python skill_worker.py
   ```

5. Publish test stories (in another terminal):

   ```bash
   python test_producer.py
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

3. **For custom rule types**, add a new case in `rule_engine.py:evaluate()`.

4. **Test** with seed stories:

   ```bash
   python test_producer.py                          # all 5 scenarios
   python test_producer.py --story informal         # single scenario
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

### Fetching story body text (content_refs)

Each seed story includes a `content_refs` array with URIs pointing to story body text. Locally these resolve to `GET /api/content/{story_id}` on the .NET dashboard (port 5050). On hackathon day, AP stories will point to AP-hosted URLs (open access).

```python
import httpx

for ref in payload.get("content_refs", []):
    resp = httpx.get(ref["uri"])
    body = resp.text  # plain-text story
    # ref["source_id"] links back to payload["sources"] for provenance
```

## Confluent Cloud

Set env vars from `.env.example`:

```bash
export KAFKA_BOOTSTRAP_SERVERS=pkc-xxxxx.confluent.cloud:9092
export KAFKA_API_KEY=your-key
export KAFKA_API_SECRET=your-secret
python skill_worker.py
```

SaslSsl is auto-detected when `KAFKA_API_KEY` and `KAFKA_API_SECRET` are set.

## Project structure

| File | Purpose |
|------|---------|
| `skill_worker.py` | Entry point + Kafka consumer loop, evaluates all skills per message |
| `rule_engine.py` | Generic rule interpreter (6 types) |
| `skill_registry.py` | Loads skills from `skills/*.json` |
| `message_builders.py` | `build_warning`, `build_run_record`, `build_suggestion`, `build_enrichment`, `build_variant` |
| `test_producer.py` | Loads seed stories, publishes to `som.story.context` |
| `config.py` | Kafka broker, topics, auth from env vars |
| `skills/*.json` | Data-driven skill definitions |
| `pyproject.toml` | Project metadata + dependencies |
