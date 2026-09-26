"""
Modular Skill Loader & Registry
===============================
Discovers and loads general reusable engineering skills from `skills/`.
Separates reusable procedural cheatsheets from project-specific institutional memory (.agent/memory/).
Matches task context dynamically without bloating context window budgets.
"""

import os
import re

from app.core.logging_config import get_logger
from app.intelligence.skills.schema import SkillMetadata

logger = get_logger(__name__)


class SkillRegistry:
    """Discovers, indexes, and queries modular skills."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.skills_dir = os.path.join(self.workspace_root, "skills")
        self._skills: dict[str, SkillMetadata] = {}
        self.discover_skills()

    def discover_skills(self) -> int:
        """Walks skills/ directory and parses all SKILL.md files."""
        self._skills.clear()
        if not os.path.exists(self.skills_dir):
            return 0

        for root, _, files in os.walk(self.skills_dir):
            for file in files:
                if file.lower() == "skill.md":
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_root)
                    skill = self._parse_skill_file(full_path, rel_path)
                    if skill:
                        self._skills[skill.name] = skill

        logger.info(f"Discovered {len(self._skills)} skills in {self.skills_dir}")
        return len(self._skills)

    def _parse_skill_file(self, full_path: str, rel_path: str) -> SkillMetadata | None:
        try:
            with open(full_path, encoding="utf-8") as f:
                content = f.read()

            # Extract YAML frontmatter
            frontmatter_match = re.match(
                r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL
            )
            if not frontmatter_match:
                return None

            fm_text, body = frontmatter_match.groups()
            meta: dict[str, str] = {}
            for line in fm_text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta[key.strip()] = val.strip()

            name = meta.get("name", os.path.basename(os.path.dirname(full_path)))
            category = meta.get("category", "general")
            desc = meta.get("description", "")

            # Parse keywords
            keywords: list[str] = []
            kw_match = re.search(r"keywords:\s*\[(.*?)\]", fm_text)
            if kw_match:
                keywords = [
                    k.strip().lower() for k in kw_match.group(1).split(",") if k.strip()
                ]

            return SkillMetadata(
                name=name,
                category=category,
                description=desc,
                keywords=keywords,
                file_path=rel_path,
                content=body.strip(),
            )
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse skill at {full_path}: {e}")
            return None

    def find_relevant_skills(self, query: str, limit: int = 2) -> list[SkillMetadata]:
        """Match query terms against skill names, categories, and keywords."""
        query_terms = set(re.findall(r"\w+", query.lower()))
        scored: list[tuple[SkillMetadata, int]] = []

        for skill in self._skills.values():
            score = 0
            # Name match
            if skill.name.lower() in query.lower():
                score += 5
            # Category match
            if skill.category.lower() in query_terms:
                score += 3
            # Keyword match
            for kw in skill.keywords:
                if kw in query_terms:
                    score += 2
            if score > 0:
                scored.append((skill, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored[:limit]]

    def format_skills_for_context(
        self, skills: list[SkillMetadata], max_chars: int = 6000
    ) -> str:
        """Format matching skills into compact cheatsheets for prompt injection."""
        if not skills:
            return ""

        sections = ["## Loaded Engineering Skills (Procedural Guides):"]
        current_len = 0
        for s in skills:
            snippet = f"### Skill: {s.name} ({s.category})\n{s.content}\n"
            if current_len + len(snippet) > max_chars:
                remaining_budget = max_chars - current_len
                if remaining_budget > 300:
                    truncated = snippet[: remaining_budget - 40].rstrip()
                    sections.append(f"{truncated}\n... [content truncated to preserve token budget]\n")
                break
            sections.append(snippet)
            current_len += len(snippet)

        if len(sections) == 1:
            return ""

        return "\n".join(sections)
