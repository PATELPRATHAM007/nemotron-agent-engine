from app.intelligence.skills.loader import SkillRegistry


def test_skill_registry_discovery():
    registry = SkillRegistry(workspace_root=".")
    count = registry.discover_skills()
    assert count >= 4
    assert "query-optimization" in registry._skills
    assert "database-safety" in registry._skills
    assert "fastapi-development" in registry._skills
    assert "clean-architecture" in registry._skills


def test_skill_registry_matching():
    registry = SkillRegistry(workspace_root=".")

    # Database matching
    db_skills = registry.find_relevant_skills("How do I eliminate N+1 queries in SQL?")
    assert len(db_skills) > 0
    assert db_skills[0].name == "query-optimization"

    # API matching
    api_skills = registry.find_relevant_skills("Create new FastAPI endpoint route")
    assert len(api_skills) > 0
    assert api_skills[0].name == "fastapi-development"


def test_skill_registry_formatting():
    registry = SkillRegistry(workspace_root=".")
    skills = registry.find_relevant_skills("database safety migrations")
    formatted = registry.format_skills_for_context(skills)

    assert "## Loaded Engineering Skills" in formatted
    assert "database-safety" in formatted
    assert "Default Read-Only Mode" in formatted
