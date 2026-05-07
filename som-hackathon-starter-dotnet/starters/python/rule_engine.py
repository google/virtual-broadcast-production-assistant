"""
Generic rule interpreter — matches the .NET RuleEngine exactly.

Supported rule types:
    term_match               — fires once per matching term in a field
    phase_with_missing_field — fires when phase matches AND a field is null/empty
    field_value_in           — fires when a field matches one of a set of values
    field_present            — fires when a field exists and is not null/empty
    field_absent             — fires when a field is missing or null/empty
    field_regex              — fires when a field matches a regex pattern
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from skill_registry import SkillRule


@dataclass
class RuleMatch:
    rule: SkillRule
    detail: str


def evaluate(rule: SkillRule, story: dict) -> list[RuleMatch]:
    """Evaluate a single rule against a story context. Returns 0..N matches."""
    evaluators = {
        "term_match": _eval_term_match,
        "phase_with_missing_field": _eval_phase_missing_field,
        "field_value_in": _eval_field_value_in,
        "field_present": lambda r, s: _eval_field_present(r, s, expect_present=True),
        "field_absent": lambda r, s: _eval_field_present(r, s, expect_present=False),
        "field_regex": _eval_field_regex,
    }
    fn = evaluators.get(rule.type)
    return fn(rule, story) if fn else []


# ── Rule type implementations ────────────────────────────────────


def _eval_term_match(rule: SkillRule, story: dict) -> list[RuleMatch]:
    field = rule.config.get("field")
    terms = rule.config.get("terms", [])
    case_sensitive = rule.config.get("case_sensitive", False)
    if not field or not terms:
        return []

    value = get_by_path(story, field)
    if not isinstance(value, str) or not value:
        return []

    haystack = value if case_sensitive else value.lower()
    matches = []
    for term in terms:
        needle = term if case_sensitive else term.lower()
        if needle in haystack:
            matches.append(RuleMatch(
                rule=rule,
                detail=_render_detail(rule, term=term, field=field, value=value),
            ))
    return matches


def _eval_phase_missing_field(rule: SkillRule, story: dict) -> list[RuleMatch]:
    phase_field = rule.config.get("phase_field", "lifecycle.phase")
    phase = rule.config.get("phase")
    field = rule.config.get("field")
    if not phase or not field:
        return []

    actual_phase = get_by_path(story, phase_field)
    if not isinstance(actual_phase, str):
        return []
    if actual_phase.lower() != phase.lower():
        return []

    if _is_empty(get_by_path(story, field)):
        return [RuleMatch(rule=rule, detail=_render_detail(rule, phase=phase, field=field))]
    return []


def _eval_field_value_in(rule: SkillRule, story: dict) -> list[RuleMatch]:
    field = rule.config.get("field")
    values = rule.config.get("values", [])
    if not field or not values:
        return []

    actual = get_by_path(story, field)
    if not isinstance(actual, str):
        return []

    for v in values:
        if actual.lower() == v.lower():
            return [RuleMatch(rule=rule, detail=_render_detail(rule, value=v, field=field))]
    return []


def _eval_field_present(rule: SkillRule, story: dict, *, expect_present: bool) -> list[RuleMatch]:
    field = rule.config.get("field")
    if not field:
        return []

    present = not _is_empty(get_by_path(story, field))
    if present == expect_present:
        return [RuleMatch(rule=rule, detail=_render_detail(rule, field=field))]
    return []


def _eval_field_regex(rule: SkillRule, story: dict) -> list[RuleMatch]:
    field = rule.config.get("field")
    pattern = rule.config.get("pattern")
    case_sensitive = rule.config.get("case_sensitive", False)
    if not field or not pattern:
        return []

    value = get_by_path(story, field)
    if not isinstance(value, str):
        return []

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        m = re.search(pattern, value, flags)
    except re.error:
        return []

    if m:
        return [RuleMatch(
            rule=rule,
            detail=_render_detail(rule, match=m.group(0), field=field, value=value),
        )]
    return []


# ── Helpers ──────────────────────────────────────────────────────


def get_by_path(obj: Any, path: str) -> Any:
    """Walk a dotted path, e.g. 'lifecycle.phase' → obj['lifecycle']['phase']."""
    current = obj
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _render_detail(rule: SkillRule, **subs: str) -> str:
    template = rule.detail_template or rule.description or rule.name
    for k, v in subs.items():
        template = template.replace(f"{{{k}}}", v)
    return template
