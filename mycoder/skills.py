"""Skill loading and management.

Skills are markdown files with YAML frontmatter that inject instructions
into the model's context. They load from two locations:

  1. Built-in:  mycoder/builtins/*.md   (shipped with the package)
  2. User:      ~/.mycoder/skills/*.md  (your custom skills — override built-ins)

Skill types:
  always  — injected into every system prompt automatically
  prompt  — activated via /skillname, adds instructions for that turn
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path

BUILTIN_DIR = Path(__file__).parent / "builtins"
USER_DIR = Path.home() / ".mycoder" / "skills"


@dataclass
class Skill:
    name: str
    description: str
    type: str
    body: str
    source: str
    path: str = ""


def _parse_skill(path: Path, source: str) -> Skill | None:
    try:
        content = path.read_text()
    except Exception:
        return None

    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", content, re.DOTALL)
    if not match:
        return None

    meta = {}
    for line in match.group(1).split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip().strip("\"'")

    return Skill(
        name=meta.get("name", path.stem),
        description=meta.get("description", ""),
        type=meta.get("type", "prompt"),
        body=match.group(2).strip(),
        source=source,
        path=str(path),
    )


class SkillManager:
    def __init__(self):
        self.skills: dict[str, Skill] = {}
        self.load()

    def load(self):
        self.skills.clear()

        if BUILTIN_DIR.exists():
            for f in sorted(BUILTIN_DIR.glob("*.md")):
                skill = _parse_skill(f, "builtin")
                if skill:
                    self.skills[skill.name] = skill

        if USER_DIR.exists():
            for f in sorted(USER_DIR.glob("*.md")):
                skill = _parse_skill(f, "user")
                if skill:
                    self.skills[skill.name] = skill

    def get(self, name: str) -> Skill | None:
        return self.skills.get(name)

    def always_on(self) -> list[Skill]:
        return [s for s in self.skills.values() if s.type == "always"]

    def invocable(self) -> list[Skill]:
        return [s for s in self.skills.values() if s.type == "prompt"]

    def all(self) -> list[Skill]:
        return list(self.skills.values())

    def system_prompt_additions(self) -> str:
        parts = []
        for skill in self.always_on():
            parts.append(f"## {skill.name}\n{skill.body}")
        return "\n\n".join(parts)

    def init_user_dir(self):
        USER_DIR.mkdir(parents=True, exist_ok=True)
        return USER_DIR
