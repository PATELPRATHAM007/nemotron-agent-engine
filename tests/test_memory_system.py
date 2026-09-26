import os

import pytest

from app.constitution.scaffold import ConstitutionScaffolder
from app.intelligence.memory.adr_manager import ADRManager
from app.intelligence.memory.memory_store import InstitutionalMemoryStore
from app.intelligence.memory.schema import (
    ADRRecord,
    ADRStatus,
    HistoricalLesson,
    LessonCategory,
)


def test_constitution_scaffolder(tmp_path):
    scaffolder = ConstitutionScaffolder(str(tmp_path))
    created = scaffolder.scaffold()

    assert "coding_standards.md" in created
    assert "architecture_rules.md" in created
    assert "testing_rules.md" in created
    assert "git_rules.md" in created
    assert "adr-001-repository-intelligence.md" in created

    # Read back rule
    coding_rule = scaffolder.load_rule("coding_standards")
    assert "Type Annotations" in coding_rule


def test_adr_manager_read_and_write(tmp_path):
    adr_manager = ADRManager(str(tmp_path))
    adr_manager.ensure_directory()

    # Write custom ADR
    record = ADRRecord(
        adr_id="ADR-002",
        title="Async SQLite for Local State Storage",
        status=ADRStatus.ACCEPTED,
        date="2026-09-26",
        context="We need lightweight persistence.",
        decision="Adopt aiosqlite.",
        consequences="Fast local storage without heavy services.",
    )
    written_path = adr_manager.write_adr(record)
    assert os.path.exists(written_path)

    # Parse it back
    parsed = adr_manager.parse_adr_file(written_path)
    assert parsed is not None
    assert parsed.adr_id == "ADR-002"
    assert parsed.title == "Async SQLite for Local State Storage"
    assert parsed.status == ADRStatus.ACCEPTED
    assert "Adopt aiosqlite." in parsed.decision


def test_institutional_memory_store_lifecycle(tmp_path):
    store = InstitutionalMemoryStore(str(tmp_path))

    lesson = HistoricalLesson(
        lesson_id="L-001",
        category=LessonCategory.BUG_FIX,
        title="Pydantic V2 dict serialization",
        description="Do not use .dict() in Pydantic v2; use .model_dump().",
        trigger_pattern="model_dump",
        resolution="Always call model.model_dump().",
        confidence_score=0.8,
    )
    store.add_lesson(lesson)

    # Query matching lessons
    results = store.query_lessons("How do I fix model_dump serialization?")
    assert len(results) == 1
    assert results[0].lesson_id == "L-001"

    # Reinforce
    store.reinforce_lesson("L-001")
    assert store._lessons["L-001"].confidence_score == pytest.approx(0.9, 0.01)

    # Penalize
    store.penalize_lesson("L-001")
    assert store._lessons["L-001"].confidence_score == pytest.approx(0.7, 0.01)

    # Format for prompt
    prompt_str = store.format_for_prompt(results)
    assert "Relevant Historical Lessons Learned:" in prompt_str
    assert "Pydantic V2 dict serialization" in prompt_str
