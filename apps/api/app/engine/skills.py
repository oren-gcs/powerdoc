from __future__ import annotations

from pathlib import Path

from app.config import get_settings


def load_skills() -> list[dict]:
    root = Path(get_settings().skills_path)
    skills = []
    if not root.exists():
        return skills
    for skill_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        md = skill_dir / "SKILL.md"
        if not md.exists():
            continue
        text = md.read_text(encoding="utf-8")
        name = skill_dir.name
        description = ""
        for line in text.splitlines():
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"')
                break
            if line.startswith("# "):
                description = line[2:].strip()
                break
        skills.append({"id": name, "name": name.replace("-", " ").title(), "description": description, "instructions": text, "path": str(md)})
    return skills


def get_skill(skill_id: str) -> dict | None:
    for s in load_skills():
        if s["id"] == skill_id:
            return s
    return None
