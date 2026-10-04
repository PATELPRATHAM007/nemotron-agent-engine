"""
Three-Tier Memory Architecture & Durability Gate
================================================
Implements clean physical and conceptual separation between:
  1. Tier 1 - Session Memory (Ephemeral, per-mission active task state)
  2. Tier 2 - Project Memory (Durable, per-repo conventions, ADRs, and bug resolutions)
  3. Tier 3 - User Memory (Cross-project, per-developer preferences)

Includes the MemoryDurabilityGate to reject transient one-offs and guarantee
only high-signal, durable architectural and convention facts enter long-term storage.
"""

import json
import os
import re
import time

from app.core.logging_config import get_logger
from app.modules.intelligence.memory.schema import (
    MemoryCandidate,
    ProjectMemoryItem,
    SessionMemory,
    UserPreference,
)

logger = get_logger(__name__)


# Patterns representing transient noise that should never enter durable storage
TRANSIENT_PATTERNS = [
    r"\bfix(?:ed)?\s+typo\b",
    r"\bline\s+\d+\b",
    r"\btemp(?:orary)?\b",
    r"\bdebug\s+(?:print|log)\b",
    r"\btest\s+message\b",
    r"\bbutton\s+color\b",
    r"\bcss\s+margin\b",
    r"\bquick\s+hack\b",
    r"\bscratchpad\b",
    r"\bwip\b",
]

# Patterns indicating durable architectural, convention, or system rules
DURABLE_PATTERNS = [
    r"\balways\b",
    r"\bnever\b",
    r"\bconvention\b",
    r"\barchitecture\b",
    r"\bmigration\b",
    r"\bendpoint\b",
    r"\bschema\b",
    r"\bstandard\b",
    r"\bpattern\b",
    r"\bpostgres\b",
    r"\bsqlite\b",
    r"\bfastapi\b",
    r"\bpydantic\b",
    r"\bpytest\b",
    r"\bsecurity\b",
    r"\bperformance\b",
    r"\bgui?delines?\b",
]


class MemoryDurabilityGate:
    """
    Evaluates proposed memory candidates before persisting to Tier 2 (Project)
    or Tier 3 (User). Filters out transient noise and guarantees durable knowledge retention.
    """

    @classmethod
    def evaluate_candidate(cls, candidate: MemoryCandidate) -> tuple[bool, str]:
        """
        Determines whether a proposed memory candidate possesses durable value.
        Returns (is_durable, reason).
        """
        text = f"{candidate.title} {candidate.content}".lower()

        # 1. Content length check
        if len(candidate.content.strip()) < 15:
            return False, "Candidate content is too short to encode actionable durable knowledge."

        # 2. Check for transient noise patterns
        for pattern in TRANSIENT_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return False, f"Candidate matches transient noise pattern: '{pattern}'."

        # 3. Minimum confidence check
        if candidate.confidence < 0.6:
            return False, f"Confidence score ({candidate.confidence:.2f}) is below durability threshold (0.60)."

        # 4. Durable keyword or category check
        has_durable_keyword = any(re.search(pat, text, re.IGNORECASE) for pat in DURABLE_PATTERNS)
        is_durable_category = candidate.category in {
            "convention", "architecture", "database", "security", "performance", "gotcha", "style"
        }

        if has_durable_keyword or is_durable_category:
            return True, "Candidate exhibits durable architectural, convention, or gotcha properties."

        # Default fallback: allow if candidate explicitly states a reusable guideline
        if len(candidate.content.split()) >= 8:
            return True, "Candidate accepted as actionable reusable pattern."

        return False, "Candidate lacks persistent, reusable repository relevance."


class ThreeTierMemoryStore:
    """
    Manages Tier 1 (Session), Tier 2 (Project), and Tier 3 (User) memory stores.
    """

    def __init__(self, workspace_root: str = ".", user_storage_path: str | None = None):
        self.workspace_root = os.path.abspath(workspace_root)
        self.agent_dir = os.path.join(self.workspace_root, ".agent")
        self.memory_dir = os.path.join(self.agent_dir, "memory")
        self.sessions_dir = os.path.join(self.memory_dir, "sessions")
        self.project_memory_file = os.path.join(self.memory_dir, "project_memory.json")

        # User memory path: defaults to ~/.agent/user_memory.json or local fallback
        if user_storage_path:
            self.user_memory_file = os.path.abspath(user_storage_path)
        else:
            home = os.path.expanduser("~")
            self.user_memory_file = os.path.join(home, ".agent", "user_memory.json")

        self._ensure_dirs()
        self._project_memories: dict[str, ProjectMemoryItem] = {}
        self._user_preferences: dict[str, UserPreference] = {}
        self._active_sessions: dict[str, SessionMemory] = {}

        self._load_project_memory()
        self._load_user_memory()

    def _ensure_dirs(self) -> None:
        os.makedirs(self.sessions_dir, exist_ok=True)
        user_dir = os.path.dirname(self.user_memory_file)
        if user_dir:
            os.makedirs(user_dir, exist_ok=True)

    # ---------------------------------------------------------
    # Tier 1: Session Memory (Ephemeral)
    # ---------------------------------------------------------

    def get_session_memory(self, mission_id: str) -> SessionMemory:
        """Retrieves active session memory for a mission."""
        if mission_id in self._active_sessions:
            return self._active_sessions[mission_id]

        session_file = os.path.join(self.sessions_dir, f"{mission_id}.json")
        if os.path.exists(session_file):
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = SessionMemory(**data)
                self._active_sessions[mission_id] = session
                return session
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to read session memory for {mission_id}: {e}")

        # New blank session
        new_session = SessionMemory(mission_id=mission_id)
        self._active_sessions[mission_id] = new_session
        return new_session

    def save_session_memory(self, memory: SessionMemory) -> None:
        """Persists session memory to disk and updates in-memory cache."""
        memory.updated_at = time.time()
        self._active_sessions[memory.mission_id] = memory

        session_file = os.path.join(self.sessions_dir, f"{memory.mission_id}.json")
        temp_file = f"{session_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(memory.model_dump(), f, indent=2)
            os.replace(temp_file, session_file)
        except OSError as e:
            logger.error(f"Failed to save session memory for {memory.mission_id}: {e}")

    def clear_session_memory(self, mission_id: str) -> None:
        """Clears ephemeral session memory upon mission completion."""
        self._active_sessions.pop(mission_id, None)
        session_file = os.path.join(self.sessions_dir, f"{mission_id}.json")
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except OSError as e:
                logger.error(f"Failed to remove session memory file: {e}")

    # ---------------------------------------------------------
    # Tier 2: Project Memory (Durable, per-repo)
    # ---------------------------------------------------------

    def _load_project_memory(self) -> None:
        if os.path.exists(self.project_memory_file):
            try:
                with open(self.project_memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._project_memories = {
                    item["item_id"]: ProjectMemoryItem(**item) for item in data
                }
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to load project memory: {e}")
                self._project_memories = {}

    def _save_project_memory(self) -> None:
        temp_file = f"{self.project_memory_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    [m.model_dump() for m in self._project_memories.values()],
                    f,
                    indent=2,
                )
            os.replace(temp_file, self.project_memory_file)
        except OSError as e:
            logger.error(f"Failed to persist project memory: {e}")

    def add_project_memory(
        self, candidate: MemoryCandidate, force: bool = False
    ) -> tuple[bool, str]:
        """
        Evaluates memory candidate via MemoryDurabilityGate and saves if approved.
        Returns (saved_bool, reason).
        """
        if not force:
            is_durable, reason = MemoryDurabilityGate.evaluate_candidate(candidate)
            if not is_durable:
                logger.info(f"Memory candidate rejected by Durability Gate: {reason}")
                return False, reason

        item_id = f"PM-{len(self._project_memories) + 1:03d}"
        item = ProjectMemoryItem(
            item_id=item_id,
            category=candidate.category,
            title=candidate.title,
            content=candidate.content,
            confidence_score=candidate.confidence,
        )
        self._project_memories[item_id] = item
        self._save_project_memory()
        return True, f"Saved durable project memory '{item.title}' [{item_id}]."

    def get_project_memories(
        self, category: str | None = None
    ) -> list[ProjectMemoryItem]:
        """Lists all project memories, optionally filtered by category."""
        memories = list(self._project_memories.values())
        if category:
            memories = [m for m in memories if m.category.lower() == category.lower()]
        return memories

    def query_project_memories(self, query: str) -> list[ProjectMemoryItem]:
        """Performs lexical search across project memories."""
        query_words = set(query.lower().split())
        matched: list[tuple[int, ProjectMemoryItem]] = []

        for item in self._project_memories.values():
            haystack = f"{item.title} {item.content} {item.category}".lower()
            score = sum(1 for w in query_words if w in haystack)
            if score > 0:
                matched.append((score, item))

        matched.sort(key=lambda x: (x[0], x[1].confidence_score), reverse=True)
        return [item for _, item in matched]

    # ---------------------------------------------------------
    # Tier 3: User Memory (Cross-project, per-developer)
    # ---------------------------------------------------------

    def _load_user_memory(self) -> None:
        if os.path.exists(self.user_memory_file):
            try:
                with open(self.user_memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._user_preferences = {
                    item["key"]: UserPreference(**item) for item in data
                }
            except (OSError, json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to load user preferences: {e}")
                self._user_preferences = {}

    def _save_user_memory(self) -> None:
        temp_file = f"{self.user_memory_file}.tmp"
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(
                    [p.model_dump() for p in self._user_preferences.values()],
                    f,
                    indent=2,
                )
            os.replace(temp_file, self.user_memory_file)
        except OSError as e:
            logger.error(f"Failed to persist user preferences: {e}")

    def set_user_preference(
        self, key: str, value: str, category: str = "general"
    ) -> None:
        """Sets or updates a developer preference."""
        self._user_preferences[key] = UserPreference(
            key=key, value=value, category=category, last_updated=time.time()
        )
        self._save_user_memory()

    def get_user_preference(self, key: str, default: str | None = None) -> str | None:
        """Gets a developer preference."""
        pref = self._user_preferences.get(key)
        return pref.value if pref else default

    def get_all_user_preferences(self) -> dict[str, str]:
        """Returns all developer preferences as key-value pairs."""
        return {k: p.value for k, p in self._user_preferences.items()}

    # ---------------------------------------------------------
    # Multi-Tier Context Assembly
    # ---------------------------------------------------------

    def assemble_memory_context(self, mission_id: str, query: str = "") -> str:
        """
        Assembles active session state, relevant project conventions,
        and user preferences into a clean markdown block ready for prompt injection.
        """
        sections: list[str] = []

        # 1. Tier 1: Session Memory
        session = self.get_session_memory(mission_id)
        session_lines = []
        if session.active_files:
            session_lines.append(f"- **Active Files**: {', '.join(session.active_files)}")
        if session.active_errors:
            session_lines.append(f"- **Active Errors**: {'; '.join(session.active_errors)}")
        if session.scratchpad:
            session_lines.append(f"- **Scratchpad**: {session.scratchpad}")

        if session_lines:
            sections.append("#### Active Session Working Memory\n" + "\n".join(session_lines))

        # 2. Tier 2: Project Memory
        relevant_project_items = (
            self.query_project_memories(query)
            if query
            else self.get_project_memories()
        )
        if relevant_project_items:
            proj_lines = ["#### Repository Conventions & Knowledge"]
            for item in relevant_project_items[:5]:  # limit to top 5
                proj_lines.append(f"- **[{item.category.upper()}] {item.title}**: {item.content}")
            sections.append("\n".join(proj_lines))

        # 3. Tier 3: User Preferences
        user_prefs = self.get_all_user_preferences()
        if user_prefs:
            pref_lines = ["#### Developer Preferences"]
            for k, v in user_prefs.items():
                pref_lines.append(f"- `{k}`: {v}")
            sections.append("\n".join(pref_lines))

        if not sections:
            return "No persistent memory records available for this task."

        return "\n\n".join(sections)


# Global singleton instance
three_tier_memory_store = ThreeTierMemoryStore()

