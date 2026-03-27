"""Pydantic schemas for niche research.

Defines structured data models for:
- NicheRecommendation: Individual niche recommendation with all details
- NicheAnalysisRequest: Request model for analyzing niches
- NicheAnalysisResponse: Response model with list of recommendations

Used for AI structured output validation and API response formatting.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class NicheRecommendation(BaseModel):
    """A single niche recommendation.

    Attributes:
        niche: The niche name/topic.
        target_audience: Who the product is designed for.
        demand_estimate: Estimated demand level (high/medium/low).
        competition_level: Estimated competition level (low/medium/high).
        recommended_formats: List of recommended digital product formats.
        rationale: Explanation of why this niche is promising.
        sources: List of source URLs used for research.
    """

    niche: str = Field(..., description="The niche name/topic")
    target_audience: str = Field(..., description="Target audience for the niche")
    demand_estimate: Literal["high", "medium", "low"] = Field(
        ..., description="Estimated demand level"
    )
    competition_level: Literal["low", "medium", "high"] = Field(
        ..., description="Estimated competition level"
    )
    recommended_formats: list[str] = Field(
        ..., description="Recommended digital product formats for this niche"
    )
    rationale: str = Field(..., description="Why this niche is promising")
    sources: list[str] = Field(default_factory=list, description="Source URLs used for research")


class NicheAnalysisRequest(BaseModel):
    """Request model for niche analysis.

    Attributes:
        keywords: List of keyword strings to analyze.
    """

    keywords: list[str] = Field(..., min_length=1, description="Keywords to analyze")


class NicheAnalysisResponse(BaseModel):
    """Response model for niche analysis.

    Attributes:
        recommendations: List of NicheRecommendation objects.
        analyzed_at: Timestamp when the analysis was performed.
    """

    recommendations: list[NicheRecommendation] = Field(
        ..., description="List of niche recommendations"
    )
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when analysis was performed"
    )
