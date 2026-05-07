"""
Publishes seed story.context messages to som.story.context for local testing.

Usage:
    python test_producer.py                     → publishes all seed stories
    python test_producer.py --story informal    → single scenario
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from confluent_kafka import Producer

from config import TOPICS, build_producer_config

SCENARIO_FILES: dict[str, str] = {
    "breaking": "01-breaking-courthouse.json",
    "election": "02-developing-election.json",
    "informal": "03-informal-headline.json",
    "clean": "04-clean-transit.json",
    "breaking-no-compliance": "05-breaking-no-compliance.json",
}

SCENARIOS = list(SCENARIO_FILES.keys())


def _resolve_seed_path(filename: str) -> Path | None:
    """Find a seed story file, trying several candidate locations."""
    candidates = [
        Path.cwd() / ".." / ".." / "seed-stories" / filename,
        Path(__file__).parent / ".." / ".." / "seed-stories" / filename,
        Path.cwd() / "seed-stories" / filename,
    ]
    for c in candidates:
        resolved = c.resolve()
        if resolved.is_file():
            return resolved
    return None


def _delivery_report(err, msg):
    if err:
        print(f"  ✗ Delivery failed: {err}")
    else:
        print(f"  → Partition {msg.partition()}, Offset {msg.offset()}")


def run_test_producer(scenario: str | None = None) -> None:
    producer = Producer(build_producer_config())
    scenarios = [scenario] if scenario else list(SCENARIO_FILES.keys())

    for name in scenarios:
        filename = SCENARIO_FILES.get(name)
        if not filename:
            print(f"Unknown scenario '{name}'. Available: {', '.join(SCENARIO_FILES.keys())}")
            continue

        path = _resolve_seed_path(filename)
        if not path:
            print(f"Seed file not found: {filename}")
            continue

        data = json.loads(path.read_text())
        payload = data.get("payload")
        if not payload:
            print(f"No payload in {filename}")
            continue

        story_id = payload.get("story_id", "unknown")

        print(f"─── {name.upper()} ───")
        print(f"  Story:    {story_id}")
        print(f"  Headline: {payload.get('headline')}")
        print(f"  Phase:    {payload.get('lifecycle', {}).get('phase')}")
        print(f"  File:     {filename}")

        producer.produce(
            TOPICS["story_context"],
            key=story_id,
            value=json.dumps(payload),
            callback=_delivery_report,
        )
        producer.flush()
        print()

    print("Done. Your skill worker should pick these up.")


if __name__ == "__main__":
    args = sys.argv[1:]
    story_idx = args.index("--story") if "--story" in args else -1
    scenario = args[story_idx + 1] if story_idx >= 0 and story_idx + 1 < len(args) else None
    run_test_producer(scenario)
