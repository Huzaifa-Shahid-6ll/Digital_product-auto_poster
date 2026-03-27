"""Pydantic schemas for niche research.

Defines structured data models for:
- NicheRecommendation: Individual niche recommendation with all details
- VerifiedNiche: Verified niche with demand scoring
- NicheAnalysisRequest: Request model for analyzing niches
- NicheAnalysisResponse: Response model with list of recommendations
- VerificationResult: Response model for verification endpoint

Used for AI structured output validation and API response formatting.
"""

from datetime import datetime
from typing import Any, Literal, Optional

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


class VerifiedNiche(BaseModel):
    """Verified niche with demand scoring from Google Trends.

    Attributes:
        recommendation: The original NicheRecommendation.
        demand_score: Demand score (0-100) calculated using the formula.
        trend_direction: Direction of search interest trend.
        verification_data: Raw Google Trends data for source citation.
        verified_demand: Whether niche meets minimum threshold (50+).
        user_approved: Whether user has approved this niche.
    """

    recommendation: NicheRecommendation = Field(..., description="Original niche recommendation")
    demand_score: float = Field(..., description="Demand score (0-100)")
    trend_direction: Literal["rising", "stable", "declining"] = Field(
        ..., description="Trend direction"
    )
    verification_data: dict[str, Any] = Field(
        default_factory=dict, description="Raw Google Trends data"
    )
    verified_demand: bool = Field(..., description="Meets minimum threshold (50+)")
    category: Literal["validated", "explore", "low_demand"] = Field(
        ..., description="Category based on demand score"
    )
    user_approved: bool = Field(default=False, description="User has approved this niche")


class VerificationResult(BaseModel):
    """Response model for verification endpoint.

    Attributes:
        verified_niches: List of VerifiedNiche objects.
        summary: Summary counts by category.
        verified_at: Timestamp when verification was performed.
    """

    verified_niches: list[VerifiedNiche] = Field(
        ..., description="List of verified niche recommendations"
    )
    summary: dict[str, int] = Field(default_factory=dict, description="Summary counts by category")
    verified_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when verification was performed"
    )


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
