"""
Autonomous Mission Module Static Messages
=========================================
Single source of truth for all mission state, planning, and permission messages.
"""

MISSION_CREATED = "Mission created successfully"
MISSION_NOT_FOUND = "Mission not found"
PLAN_NOT_FOUND = "No active plan found for mission"
PLAN_APPROVED = "Plan approved, beginning autonomous execution"
SELECTION_RECORDED = "Selection decision recorded"
PERMISSION_GRANTED = "Execution permission granted"
PERMISSION_DENIED = "Execution permission denied"
MISSION_STOPPED = "Mission execution cancelled by user"
ROLLBACK_SUCCESS = "Working tree reverted to clean git state"
ATTACHMENT_UPLOADED = "Multimodal attachment uploaded successfully"
INVALID_IMAGE_DATA = "Invalid base64 image data or corrupted payload"
INVALID_IMAGE_HEADER = "Invalid image file header or unsupported format"
FILE_SIZE_EXCEEDED = "File size exceeds 15MB limit"
