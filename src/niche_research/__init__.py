"""Niche research module.

Provides AI-powered niche analysis, verification, and recommendations.
"""

from src.niche_research.schemas import (
    NicheAnalysisRequest,
    NicheAnalysisResponse,
    NicheRecommendation,
)
from src.niche_research.verifier import verify_demand, get_verification_summary

__all__ = [
    "NicheRecommendation",
    "NicheAnalysisRequest",
    "NicheAnalysisResponse",
    "verify_demand",
    "get_verification_summary",
]
