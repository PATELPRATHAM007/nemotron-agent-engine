"""
Constitution Module API Controllers
===================================
"""

import os
from fastapi import HTTPException, status
from app.modules.constitution import messages
from app.modules.constitution.schemas import RuleDetailResponse, ScaffoldResponse
from app.modules.constitution.service import ConstitutionScaffolder
from app.modules.constitution.validation import ConstitutionValidator


async def scaffold_constitution(workspace_root: str = "."):
    """Scaffold .agent/ constitution files."""
    scaffolder = ConstitutionScaffolder(workspace_root)
    created = scaffolder.scaffold()
    return ScaffoldResponse(
        success=True,
        created_files=created,
        message=messages.CONSTITUTION_SCAFFOLDED,
    )


async def list_rules(workspace_root: str = "."):
    """List available constitutional rules."""
    scaffolder = ConstitutionScaffolder(workspace_root)
    if not os.path.exists(scaffolder.rules_dir):
        return []
    rules = [
        f[:-3] for f in os.listdir(scaffolder.rules_dir) if f.endswith(".md")
    ]
    return sorted(rules)


async def get_rule_detail(rule_name: str, workspace_root: str = "."):
    """Get the markdown content of a specific rule."""
    ConstitutionValidator.validate_rule_name(rule_name)
    scaffolder = ConstitutionScaffolder(workspace_root)
    content = scaffolder.load_rule(rule_name)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.RULE_NOT_FOUND,
        )
    return RuleDetailResponse(rule_name=rule_name, content=content)
