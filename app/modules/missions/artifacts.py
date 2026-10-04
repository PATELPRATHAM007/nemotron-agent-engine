"""
Structured Mission Artifact Delivery System
===========================================
Generates and manages structured, reviewable artifacts stored in PostgreSQL / local fallback:
  - Plan Artifact: Multi-stage plan with approval buttons.
  - Diff Artifact: Syntax-highlighted git diff with file modifications.
  - Test Report Artifact: Pytest execution matrix with duration and logs.
  - Visual Screenshot Artifact: UI visual verification captures.
"""

from enum import Enum
import json
import time
from typing import Any
from pydantic import BaseModel, Field

from app.core.logging_config import get_logger
from app.modules.missions.repository import mission_repository

logger = get_logger(__name__)


class ArtifactType(str, Enum):
    PLAN = "PLAN"
    DIFF = "DIFF"
    TEST_REPORT = "TEST_REPORT"
    VISUAL_SCREENSHOT = "VISUAL_SCREENSHOT"


class ArtifactManager:
    """Factory and manager for generating structured mission artifacts."""

    def __init__(self):
        self.repo = mission_repository

    def _persist(
        self,
        mission_id: str,
        title: str,
        artifact_type: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Saves artifact with JSON-encoded content string."""
        content_str = json.dumps(data)
        saved = self.repo.save_artifact(
            mission_id=mission_id,
            artifact_type=artifact_type,
            title=title,
            content=content_str,
        )
        # Ensure 'data' dict is available on return
        result = dict(saved)
        result["data"] = data
        return result

    def save_plan_artifact(
        self,
        mission_id: str,
        title: str,
        steps: list[dict[str, Any]],
        summary: str,
        status: str = "PROPOSED",
    ) -> dict[str, Any]:
        """Saves a structured planning artifact."""
        data = {
            "summary": summary,
            "status": status,
            "steps": steps,
            "step_count": len(steps),
        }
        return self._persist(
            mission_id=mission_id,
            title=title,
            artifact_type=ArtifactType.PLAN.value,
            data=data,
        )

    def save_diff_artifact(
        self,
        mission_id: str,
        title: str,
        diff_text: str,
        files_modified: list[str],
    ) -> dict[str, Any]:
        """Saves a code modification diff artifact."""
        data = {
            "diff": diff_text,
            "files_modified": files_modified,
            "additions_count": sum(1 for line in diff_text.splitlines() if line.startswith("+") and not line.startswith("+++")),
            "deletions_count": sum(1 for line in diff_text.splitlines() if line.startswith("-") and not line.startswith("---")),
        }
        return self._persist(
            mission_id=mission_id,
            title=title,
            artifact_type=ArtifactType.DIFF.value,
            data=data,
        )

    def save_test_report_artifact(
        self,
        mission_id: str,
        title: str,
        tests_passed: int,
        tests_failed: int,
        duration_seconds: float,
        log_output: str,
    ) -> dict[str, Any]:
        """Saves a test execution matrix artifact."""
        total = tests_passed + tests_failed
        success_rate = (tests_passed / total * 100) if total > 0 else 100.0
        data = {
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "total_tests": total,
            "success_rate_percent": round(success_rate, 1),
            "duration_seconds": duration_seconds,
            "log_output": log_output[:4000],
        }
        return self._persist(
            mission_id=mission_id,
            title=title,
            artifact_type=ArtifactType.TEST_REPORT.value,
            data=data,
        )

    def save_visual_screenshot_artifact(
        self,
        mission_id: str,
        title: str,
        image_url_or_path: str,
        caption: str,
        dimensions: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Saves a visual UI screenshot artifact."""
        data = {
            "image_url_or_path": image_url_or_path,
            "caption": caption,
            "dimensions": dimensions or {"width": 1280, "height": 720},
            "timestamp": time.time(),
        }
        return self._persist(
            mission_id=mission_id,
            title=title,
            artifact_type=ArtifactType.VISUAL_SCREENSHOT.value,
            data=data,
        )

    def get_mission_artifacts(self, mission_id: str) -> list[dict[str, Any]]:
        """Retrieves all artifacts produced during a mission and parses data if JSON."""
        raw_artifacts = self.repo.get_artifacts(mission_id)
        enriched: list[dict[str, Any]] = []

        for art in raw_artifacts:
            item = dict(art)
            content = item.get("content", "")
            if isinstance(content, str) and (content.startswith("{") or content.startswith("[")):
                try:
                    item["data"] = json.loads(content)
                except json.JSONDecodeError:
                    item["data"] = {}
            else:
                item["data"] = {}
            enriched.append(item)

        return enriched


artifact_manager = ArtifactManager()
