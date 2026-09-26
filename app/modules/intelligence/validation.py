"""
Intelligence Module Validation
==============================
"""

import os
from fastapi import HTTPException, status
from app.modules.intelligence import messages


class IntelligenceValidator:
    """Validates intelligence queries and prevents directory traversal."""

    @staticmethod
    def validate_file_path(file_path: str, workspace_root: str = ".") -> str:
        """Ensure file path is relative and within workspace boundaries."""
        if not file_path or not file_path.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=messages.FILE_PATH_REQUIRED,
            )
        abs_root = os.path.abspath(workspace_root)
        target = os.path.abspath(os.path.join(abs_root, file_path.strip()))
        if not target.startswith(abs_root):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Security violation: Path traversal outside workspace boundary",
            )
        return file_path.strip()
