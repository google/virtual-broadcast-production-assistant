"""
SOM Skill Worker — Python starter.

Consumes story.context from Kafka, evaluates every registered skill's rules
via the rule engine, and publishes matches to som.skills.staging + audit
records to som.skills.runs.

To add or change skills, drop a JSON file into skills/ — no code changes needed.

Usage:
    python skill_worker.py                              → run the worker
    python skill_worker.py --test-producer              → publish all seed stories
    python skill_worker.py --test-producer --story X    → publish one scenario
"""

from __future__ import annotations

import json
import sys
import time

from confluent_kafka import Consumer, Producer, KafkaError

from config import TOPICS, build_consumer_config, build_producer_config
from skill_registry import SkillRegistry
from rule_engine import evaluate
from message_builders import build_warning, build_run_record


def start_worker() -> None:
    registry = SkillRegistry()
    skills = registry.all()

    if not skills:
        print("WARNING: No skills loaded — check your skills/ directory")

    producer = Producer(build_producer_config())
    consumer = Consumer(build_consumer_config())
    consumer.subscribe([TOPICS["story_context"]])

    print(
        f"SkillWorker subscribed to {TOPICS['story_context']} "
        f"with {len(skills)} skill(s) loaded"
    )

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                print(f"Consumer error: {msg.error()}")
                continue

            try:
                envelope = json.loads(msg.value().decode("utf-8"))
                # SOM v0.2 envelope wraps the story under "payload"; tolerate flat payloads too.
                story_context = envelope.get("payload", envelope)
                story_id = story_context.get("story_id", "unknown")
                message_key = msg.key().decode("utf-8") if msg.key() else None

                print(f"Received story {story_id}")

                # Run every registered skill against this story.
                for skill in registry.all():
                    _evaluate_skill(producer, skill, story_context, story_id, message_key)

            except Exception as e:
                print(f"Skill execution error: {e}")

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        consumer.close()
        producer.flush()


def _evaluate_skill(
    producer: Producer,
    skill,
    story_context: dict,
    story_id: str,
    message_key: str | None,
) -> None:
    start = time.monotonic()
    warning_ids: list[str] = []

    for rule in skill.rules:
        matches = evaluate(rule, story_context)
        for match in matches:
            warning = build_warning(skill, match, story_id)
            warning_ids.append(warning["warning_id"])
            producer.produce(
                TOPICS["skills_staging"],
                key=story_id,
                value=json.dumps(warning),
            )

    latency_ms = int((time.monotonic() - start) * 1000)

    run_record = build_run_record(
        skill=skill,
        story_id=story_id,
        message_key=message_key,
        warning_ids=warning_ids,
        latency_ms=latency_ms,
    )
    producer.produce(
        TOPICS["skills_runs"],
        key=story_id,
        value=json.dumps(run_record),
    )
    producer.flush()

    print(
        f"Skill {skill.id}@{skill.version} on {story_id}: "
        f"{len(warning_ids)} warnings in {latency_ms}ms"
    )


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--test-producer" in args:
        from test_producer import run_test_producer

        story_idx = args.index("--story") if "--story" in args else -1
        scenario = args[story_idx + 1] if story_idx >= 0 and story_idx + 1 < len(args) else None
        run_test_producer(scenario)
    else:
        start_worker()
