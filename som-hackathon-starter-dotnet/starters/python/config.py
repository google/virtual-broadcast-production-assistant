"""
Kafka configuration — reads from env vars with sensible local-dev defaults.

For Confluent Cloud: set KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET.
"""

import os

BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# TODO: Change to your vendor's consumer group
GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "my-skill-group")

TOPICS = {
    "story_context": os.environ.get("KAFKA_STORY_CONTEXT_TOPIC", "som.story.context"),
    "skills_staging": os.environ.get("KAFKA_SKILLS_STAGING_TOPIC", "som.skills.staging"),
    "skills_runs": os.environ.get("KAFKA_SKILLS_RUNS_TOPIC", "som.skills.runs"),
}

KAFKA_API_KEY = os.environ.get("KAFKA_API_KEY", "")
KAFKA_API_SECRET = os.environ.get("KAFKA_API_SECRET", "")


def build_producer_config() -> dict:
    """Build confluent-kafka producer config, auto-detecting SaslSsl."""
    config = {
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "acks": "all",
        "enable.idempotence": True,
    }
    _apply_auth(config)
    return config


def build_consumer_config() -> dict:
    """Build confluent-kafka consumer config."""
    config = {
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": GROUP_ID,
        "auto.offset.reset": "latest",
        "enable.auto.commit": True,
    }
    _apply_auth(config)
    return config


def _apply_auth(config: dict) -> None:
    if KAFKA_API_KEY and KAFKA_API_SECRET:
        config["security.protocol"] = "SASL_SSL"
        config["sasl.mechanisms"] = "PLAIN"
        config["sasl.username"] = KAFKA_API_KEY
        config["sasl.password"] = KAFKA_API_SECRET
