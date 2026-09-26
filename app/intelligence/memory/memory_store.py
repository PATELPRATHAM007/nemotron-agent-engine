"""
Institutional Memory Store
==========================
Persists historical lessons, past bug resolutions, and design gotchas in .agent/memory/historical_lessons.json.
Provides adaptive confidence scoring: reinforcement upon successful repair, decay on obsolete lessons.
"""

import json
import os
import time

from app.core.logging_config import get_logger
from app.intelligence.memory.schema import HistoricalLesson

logger = get_logger(__name__)


class InstitutionalMemoryStore:
    """Persistent storage and retrieval engine for institutional agent memory."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.memory_dir = os.path.join(self.workspace_root, ".agent", "memory")
        self.lessons_file = os.path.join(self.memory_dir, "historical_lessons.json")
        self._lessons: dict[str, HistoricalLesson] = {}
        self._load()

    def _ensure_dir(self) -> None:
        os.makedirs(self.memory_dir, exist_ok=True)

    def _load(self) -> None:
        if os.path.exists(self.lessons_file):
            try:
                with open(self.lessons_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._lessons = {
                    item["lesson_id"]: HistoricalLesson(**item) for item in data
                }
            except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Failed to load historical lessons: {e}")
                self._lessons = {}

    def _save(self) -> None:
        self._ensure_dir()
        temp_file = f"{self.lessons_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump([l.model_dump() for l in self._lessons.values()], f, indent=2)
            os.replace(temp_file, self.lessons_file)
        except (OSError, TypeError, ValueError) as e:
            logger.error(f"Failed to save historical lessons: {e}")

    def add_lesson(self, lesson: HistoricalLesson) -> None:
        """Add or update a historical lesson."""
        if lesson.lesson_id in self._lessons:
            existing = self._lessons[lesson.lesson_id]
            existing.occurrences += 1
            existing.confidence_score = min(1.0, existing.confidence_score + 0.05)
            existing.last_updated = time.time()
            existing.resolution = lesson.resolution
        else:
            self._lessons[lesson.lesson_id] = lesson
        self._save()

    def reinforce_lesson(self, lesson_id: str) -> None:
        """Reinforce confidence score upon successful application in a mission."""
        if lesson_id in self._lessons:
            self._lessons[lesson_id].confidence_score = min(
                1.0, self._lessons[lesson_id].confidence_score + 0.1
            )
            self._lessons[lesson_id].last_updated = time.time()
            self._save()

    def penalize_lesson(self, lesson_id: str) -> None:
        """Decay confidence score if lesson was unhelpful or outdated."""
        if lesson_id in self._lessons:
            self._lessons[lesson_id].confidence_score = max(
                0.1, self._lessons[lesson_id].confidence_score - 0.2
            )
            self._lessons[lesson_id].last_updated = time.time()
            self._save()

    def query_lessons(
        self, query: str, min_confidence: float = 0.5
    ) -> list[HistoricalLesson]:
        """Query lessons matching trigger terms above confidence threshold."""
        query_lower = query.lower()
        matches = []
        for lesson in self._lessons.values():
            if lesson.confidence_score < min_confidence:
                continue
            if (
                lesson.trigger_pattern.lower() in query_lower
                or lesson.title.lower() in query_lower
                or any(
                    term in lesson.description.lower() for term in query_lower.split()
                )
            ):
                matches.append(lesson)
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        return matches

    def format_for_prompt(self, lessons: list[HistoricalLesson]) -> str:
        """Format matching lessons for prompt injection."""
        if not lessons:
            return "No specific historical lessons apply to this task."

        lines = ["## Relevant Historical Lessons Learned:"]
        for l in lessons:
            lines.append(
                f"- **[{l.category.value}] {l.title}** (Confidence: {int(l.confidence_score * 100)}%)\n"
                f"  - Pattern: `{l.trigger_pattern}`\n"
                f"  - Solution: {l.resolution}"
            )
        return "\n".join(lines)
