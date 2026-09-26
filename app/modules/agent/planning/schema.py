"""
Multi-Stage Planning & 6-Review Loop Schemas
===========================================
Defines the 8 sequential planning stages (Phases A through H)
and the 6 independent architectural review loops.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PlanningStage(str, Enum):
    PHASE_A_DISCOVERY = "PHASE_A_DISCOVERY"
    PHASE_B_RETRIEVAL = "PHASE_B_RETRIEVAL"
    PHASE_C_ARCHITECTURE = "PHASE_C_ARCHITECTURE"
    PHASE_D_IMPACT_ANALYSIS = "PHASE_D_IMPACT_ANALYSIS"
    PHASE_E_DATABASE_ANALYSIS = "PHASE_E_DATABASE_ANALYSIS"
    PHASE_F_IMPLEMENTATION_PLAN = "PHASE_F_IMPLEMENTATION_PLAN"
    PHASE_G_TEST_PLAN = "PHASE_G_TEST_PLAN"
    PHASE_H_RISK_PLAN = "PHASE_H_RISK_PLAN"


class ReviewKind(str, Enum):
    REVIEW_1_ARCHITECTURE = "REVIEW_1_ARCHITECTURE"
    REVIEW_2_CORRECTNESS = "REVIEW_2_CORRECTNESS"
    REVIEW_3_SECURITY = "REVIEW_3_SECURITY"
    REVIEW_4_PERFORMANCE = "REVIEW_4_PERFORMANCE"
    REVIEW_5_MAINTAINABILITY = "REVIEW_5_MAINTAINABILITY"
    REVIEW_6_BEST_PRACTICES = "REVIEW_6_BEST_PRACTICES"


class IndividualReviewResult(BaseModel):
    review_kind: ReviewKind
    passed: bool
    score: float = 1.0  # 0.0 to 1.0
    critique: str
    required_modifications: list[str] = Field(default_factory=list)


class MultiStagePlanContract(BaseModel):
    task_id: str
    goal: str
    target_feature: str
    primary_files: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    database_tables_affected: list[str] = Field(default_factory=list)
    permission_level_required: int = 2
    stage_outputs: dict[str, Any] = Field(default_factory=dict)
    review_results: list[IndividualReviewResult] = Field(default_factory=list)
    all_reviews_passed: bool = False
    readiness_score: float = 0.0
