"""
Multimodal Context & Screenshot Attachment Handler
==================================================
Manages image and screenshot storage in `.agent/blobs/`, calculates sha256
hashes, verifies MIME types, and formats multimodal context for model reasoning.
"""

import base64
import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Any
import uuid

from app.core.logging_config import get_logger

logger = get_logger(__name__)

SUPPORTED_MIME_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
}


class MultimodalStorage:
    """Manages file storage for screenshots, diagrams, and visual attachments."""

    def __init__(self, workspace_root: str = "."):
        self.blob_dir = Path(workspace_root) / ".agent" / "blobs"
        self.blob_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def sanitize_filename(cls, filename: str) -> str:
        """Sanitizes filename against path traversal attacks."""
        sanitized = os.path.basename(filename.replace("\\", "/"))
        if ".." in sanitized or "/" in sanitized or not sanitized:
            return "screenshot.png"
        return sanitized

    def store_base64_attachment(
        self,
        base64_data: str,
        filename: str = "screenshot.png",
        mime_type: str = "image/png",
        mission_id: str = "default",
    ) -> dict[str, Any]:
        """
        Decode base64 image data, sanitize filename, validate magic bytes,
        calculate SHA256, store in .agent/blobs/, and return metadata dict.
        """
        # 1. Path traversal protection: sanitize filename
        sanitized_filename = self.sanitize_filename(filename)

        # 2. Extract base64 payload
        raw_b64 = base64_data
        if "," in base64_data and "base64" in base64_data[:50]:
            header, raw_b64 = base64_data.split(",", 1)
            if "image/" in header:
                parsed_mime = header.split(";")[0].replace("data:", "")
                if parsed_mime in SUPPORTED_MIME_TYPES:
                    mime_type = parsed_mime

        try:
            binary_data = base64.b64decode(raw_b64)
        except Exception as e:
            raise ValueError(f"Invalid base64 image data: {e}")

        file_size = len(binary_data)
        # 3. Size limit: 15 MB
        if file_size > 15 * 1024 * 1024:
            raise ValueError(f"File size exceeds 15MB limit ({file_size} bytes)")

        # 4. Magic-byte validation
        is_valid_image = False
        if binary_data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
            is_valid_image = True
        elif binary_data.startswith(b"\xff\xd8\xff"):
            mime_type = "image/jpeg"
            is_valid_image = True
        elif binary_data.startswith(b"GIF87a") or binary_data.startswith(b"GIF89a"):
            mime_type = "image/gif"
            is_valid_image = True
        elif len(binary_data) >= 12 and binary_data.startswith(b"RIFF") and binary_data[8:12] == b"WEBP":
            mime_type = "image/webp"
            is_valid_image = True
        elif binary_data.startswith(b"BM"):
            mime_type = "image/bmp"
            is_valid_image = True
        elif b"<svg" in binary_data[:100].lower():
            mime_type = "image/svg+xml"
            is_valid_image = True

        if not is_valid_image:
            raise ValueError(f"Invalid image file header or unsupported format for '{sanitized_filename}'")

        sha256 = hashlib.sha256(binary_data).hexdigest()
        ext = SUPPORTED_MIME_TYPES.get(mime_type, ".png")
        storage_filename = f"{sha256[:16]}_{uuid.uuid4().hex[:8]}{ext}"
        storage_path = self.blob_dir / storage_filename

        with open(storage_path, "wb") as f:
            f.write(binary_data)

        logger.info(
            f"Stored multimodal attachment: {storage_filename} ({file_size} bytes, mime={mime_type})"
        )

        return {
            "id": str(uuid.uuid4()),
            "mission_id": mission_id,
            "filename": filename,
            "mime_type": mime_type,
            "file_size": file_size,
            "storage_reference": str(storage_path),
            "sha256_hash": sha256,
            "raw_base64": raw_b64,
        }

    def load_base64(self, storage_reference: str) -> str:
        """Load binary file from storage and return base64 string."""
        path = Path(storage_reference)
        if not path.exists():
            return ""
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")


multimodal_storage = MultimodalStorage()
