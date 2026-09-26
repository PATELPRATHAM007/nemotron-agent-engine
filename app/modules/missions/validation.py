"""
Mission Validation & Multimodal Image Inspection
================================================
Sanitizes filenames against directory traversal, validates image headers
against known magic bytes, and enforces size constraints.
"""

import os
from app.modules.missions import messages

SUPPORTED_IMAGE_MIMES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/svg+xml": ".svg",
}


class MissionValidator:
    """Validates files, paths, and commands for safe autonomous execution."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitizes filename against path traversal attacks."""
        clean = os.path.basename(filename.replace("\\", "/"))
        if ".." in clean or "/" in clean or not clean:
            return "screenshot.png"
        return clean

    @staticmethod
    def validate_image_bytes(binary_data: bytes, filename: str = "screenshot.png") -> str:
        """
        Validates image header against known magic byte signatures.
        Raises ValueError if corrupted or unrecognized.
        """
        file_size = len(binary_data)
        if file_size > 15 * 1024 * 1024:
            raise ValueError(messages.FILE_SIZE_EXCEEDED)

        if binary_data.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        elif binary_data.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        elif binary_data.startswith(b"GIF87a") or binary_data.startswith(b"GIF89a"):
            return "image/gif"
        elif len(binary_data) >= 12 and binary_data.startswith(b"RIFF") and binary_data[8:12] == b"WEBP":
            return "image/webp"
        elif binary_data.startswith(b"BM"):
            return "image/bmp"
        elif b"<svg" in binary_data[:100].lower():
            return "image/svg+xml"

        raise ValueError(f"{messages.INVALID_IMAGE_HEADER} for '{filename}'")
