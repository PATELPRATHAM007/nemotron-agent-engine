# This file is intentional so that Alembic/DB utils can import 'Base' and all models from one place
from app.db.session import Base
from app.intelligence.cost.models import CostRecord  # noqa: F401

__all__ = ["Base", "CostRecord"]
