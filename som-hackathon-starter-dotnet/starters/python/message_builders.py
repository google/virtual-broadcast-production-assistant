"""
SOM message builders — produces JSON shapes identical to the .NET SkillWorker.

Field names, nesting, and types MUST match the .NET version exactly so the
shared dashboard can render outputs from any language starter.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from skill_registry import SkillDefinition
from rule_engine import RuleMatch


def build_warning(skill: SkillDefinition, match: RuleMatch, story_id: str) -> dict:
    """Build a skill.warning.raised message (hackathon brief §8.3)."""
    rule = match.rule
    return {
        "message_type": rule.output_message_type,
        "warning_id": str(uuid.uuid4()),
        "skill_id": skill.id,
        "skill_version": skill.version,
        "story_id": story_id,
        "severity": rule.default_severity,
        "rule_id": rule.rule_id,
        "non_overridable": False,
        "affected_fields": list(rule.affected_fields),
        "detail": match.detail,
        "blocks": [],
        "timestamp": _now_iso(),
    }


def build_suggestion(
    skill: SkillDefinition,
    story_id: str,
    content_type: str,
    variants: list[dict],
    instance_ref: dict | None = None,
) -> dict:
    """Build a skill.suggestion.created message (Amendment 3)."""
    msg = {
        "message_type": "skill.suggestion.created",
        "suggestion_id": str(uuid.uuid4()),
        "skill_id": skill.id,
        "skill_version": skill.version,
        "story_id": story_id,
        "content_type": content_type,
        "variants": variants,
        "human_review_required": True,
        "timestamp": _now_iso(),
    }
    if instance_ref:
        msg["instance_ref"] = instance_ref
    return msg


def build_variant(
    content_type: str,
    fmt: str,
    label: str,
    confidence: float,
    payload: any,
    preview_text: str,
    asset_ref: str | None = None,
) -> dict:
    """Build a variant for use inside skill.suggestion.created."""
    v = {
        "variant_id": str(uuid.uuid4()),
        "content_type": content_type,
        "format": fmt,
        "label": label,
        "confidence": confidence,
        "payload": payload,
        "preview": {"text": preview_text},
    }
    if asset_ref:
        v["asset_ref"] = asset_ref
    return v


def build_enrichment(
    skill: SkillDefinition,
    story_id: str,
    representation_type: str,
    language: str,
    content: str,
    content_key: str,
) -> dict:
    """Build a story.enrichment message (Amendment 5)."""
    return {
        "message_type": "story.enrichment",
        "enrichment_id": str(uuid.uuid4()),
        "skill_id": skill.id,
        "skill_version": skill.version,
        "story_id": story_id,
        "representation_type": representation_type,
        "language": language,
        "content": content,
        "content_key": content_key,
        "timestamp": _now_iso(),
    }


def build_run_record(
    skill: SkillDefinition,
    story_id: str,
    message_key: str | None,
    warning_ids: list[str],
    suggestion_ids: list[str] | None = None,
    enrichment_ids: list[str] | None = None,
    latency_ms: int = 0,
) -> dict:
    """Build skill.run.completed audit record (Amendment 1, hackathon brief §8.1)."""
    return {
        "message_type": "skill.run.completed",
        "run_id": str(uuid.uuid4()),
        "skill_id": skill.id,
        "skill_version": skill.version,
        "story_id": story_id,
        "triggered_by": {
            "event_type": "story.context",
            "message_id": message_key or "",
        },
        "inputs": {
            "reads": list(skill.reads),
            "input_digest": "",  # TODO: sha256 of consumed fields
        },
        "outputs": {
            "suggestion_ids": suggestion_ids or [],
            "warning_ids": warning_ids,
            "enrichment_ids": enrichment_ids or [],
        },
        "latency_ms": latency_ms,
        "outcome": "COMPLETED" if warning_ids else "SKIPPED",
        "human_review_required": len(warning_ids) > 0,
        "timestamp": _now_iso(),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
