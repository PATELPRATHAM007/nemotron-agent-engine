"""
Architecture Decision Record (ADR) Manager
==========================================
Maintains, parses, and provides query interfaces for repository ADRs.
"""

import os
import re

from app.core.logging_config import get_logger
from app.intelligence.memory.schema import ADRRecord, ADRStatus

logger = get_logger(__name__)


class ADRManager:
    """Manages reading, parsing, and writing Architecture Decision Records."""

    def __init__(self, workspace_root: str):
        self.workspace_root = os.path.abspath(workspace_root)
        self.adr_dir = os.path.join(
            self.workspace_root, ".agent", "architecture", "adrs"
        )

    def ensure_directory(self) -> None:
        """Ensure ADR directory exists."""
        os.makedirs(self.adr_dir, exist_ok=True)

    def list_adrs(self) -> list[ADRRecord]:
        """List and parse all ADR markdown files in the repository."""
        self.ensure_directory()
        adrs = []
        if not os.path.exists(self.adr_dir):
            return []

        for fname in sorted(os.listdir(self.adr_dir)):
            if fname.endswith(".md"):
                path = os.path.join(self.adr_dir, fname)
                parsed = self.parse_adr_file(path)
                if parsed:
                    adrs.append(parsed)
        return adrs

    def parse_adr_file(self, filepath: str) -> ADRRecord | None:
        """Parse standard markdown ADR into ADRRecord."""
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            filename = os.path.basename(filepath)
            adr_id = filename.replace(".md", "").upper()

            # Extract title
            title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else filename

            # Extract status
            status_match = re.search(
                r"\*\*Status\*\*:\s*([A-Za-z]+)", content, re.IGNORECASE
            )
            status_str = status_match.group(1).upper() if status_match else "ACCEPTED"
            try:
                status = ADRStatus(status_str)
            except ValueError:
                status = ADRStatus.ACCEPTED

            # Extract date
            date_match = re.search(r"\*\*Date\*\*:\s*([0-9\-]+)", content)
            date_str = date_match.group(1) if date_match else "2026-09-26"

            # Extract sections
            def extract_section(name: str) -> str:
                pattern = rf"##\s+{name}\s*\n(.*?)(?=\n##|\Z)"
                m = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                return m.group(1).strip() if m else ""

            context = extract_section("Context")
            decision = extract_section("Decision")
            consequences = extract_section("Consequences")

            return ADRRecord(
                adr_id=adr_id,
                title=title,
                status=status,
                date=date_str,
                context=context,
                decision=decision,
                consequences=consequences,
            )
        except (OSError, ValueError, KeyError) as e:
            logger.error(f"Failed to parse ADR at {filepath}: {e}")
            return None

    def write_adr(self, record: ADRRecord) -> str:
        """Write an ADRRecord to disk in standard Markdown format."""
        self.ensure_directory()
        filename = f"{record.adr_id.lower().replace('_', '-')}.md"
        filepath = os.path.join(self.adr_dir, filename)

        md_content = f"""# {record.title}

**Status**: {record.status.value}  
**Date**: {record.date}  

## Context
{record.context}

## Decision
{record.decision}

## Consequences
{record.consequences}
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)

        return filepath
