"""
In-memory registry of skill definitions, backed by JSON files in skills/.
Loads all *.json files on startup.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SkillRule:
    rule_id: str
    name: str
    description: str
    type: str
    config: dict[str, Any]
    default_severity: str
    output_message_type: str
    affected_fields: list[str]
    detail_template: str | None = None


@dataclass
class SkillDefinition:
    id: str
    version: str
    name: str
    description: str
    skill_type: str
    disclosure_level: str
    migration_policy: str
    reads: list[str]
    produces: list[str]
    rules: list[SkillRule]

    @classmethod
    def from_dict(cls, data: dict) -> SkillDefinition:
        rules = [
            SkillRule(
                rule_id=r["rule_id"],
                name=r["name"],
                description=r["description"],
                type=r["type"],
                config=r.get("config", {}),
                default_severity=r["default_severity"],
                output_message_type=r["output_message_type"],
                affected_fields=r.get("affected_fields", []),
                detail_template=r.get("detail_template"),
            )
            for r in data.get("rules", [])
        ]
        return cls(
            id=data["id"],
            version=data["version"],
            name=data["name"],
            description=data["description"],
            skill_type=data.get("skill_type", "vendor"),
            disclosure_level=data.get("disclosure_level", "L2"),
            migration_policy=data.get("migration_policy", "gated"),
            reads=data.get("reads", []),
            produces=data.get("produces", []),
            rules=rules,
        )


class SkillRegistry:
    def __init__(self, skills_dir: str | None = None):
        self._skills: dict[str, SkillDefinition] = {}
        directory = skills_dir or self._resolve_skills_dir()
        self._load_all(directory)

    def all(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self._skills.get(skill_id)

    def _load_all(self, directory: str) -> None:
        path = Path(directory)
        if not path.is_dir():
            print(f"Skills directory not found at {directory} — starting empty")
            return

        for file in sorted(path.glob("*.json")):
            try:
                data = json.loads(file.read_text())
                skill = SkillDefinition.from_dict(data)
                self._skills[skill.id] = skill
                print(f"Loaded skill {skill.id}@{skill.version} from {file.name}")
            except Exception as e:
                print(f"Failed to load skill from {file.name}: {e}")

    @staticmethod
    def _resolve_skills_dir() -> str:
        candidates = [
            os.path.join(os.getcwd(), "skills"),
            os.path.join(os.path.dirname(__file__), "skills"),
        ]
        for c in candidates:
            if os.path.isdir(c):
                return c
        return candidates[0]
