"""
Model Gateway Router
====================
Mounts gateway and admin controllers from apis.py.
"""

from fastapi import APIRouter
from app.modules.gateway import apis

router = APIRouter(prefix="/models", tags=["Model Gateway"])
admin_router = APIRouter(prefix="/admin", tags=["Model Gateway Administration"])

# Model Endpoints
router.get("")(apis.list_authorized_models)
router.get("/usage")(apis.list_usage_metrics)
router.get("/quotas")(apis.get_quotas)
router.get("/{model_name}")(apis.get_model_details)
router.post("/generate")(apis.generate_response)
router.post("/stream")(apis.stream_response)

# Admin Endpoints
admin_router.post("/providers")(apis.register_provider)
admin_router.post("/models")(apis.register_model)
admin_router.post("/model-credentials/{credential_id}/rotate")(apis.rotate_credential)
