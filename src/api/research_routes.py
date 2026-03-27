"""API routes for niche research.

REST endpoints for:
- POST /api/research/analyze - Analyze keywords and get niche recommendations
- POST /api/research/verify - Verify niche recommendations with Google Trends

Mounted at /api/research in main app.
"""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.niche_research.analyzer import NicheAnalysisError, analyze_niche
from src.niche_research.schemas import NicheRecommendation
from src.niche_research.verifier import VerificationError, get_verification_summary, verify_demand

# Create router
router = APIRouter(tags=["research"])


# Dependency for OpenAI client


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI client.

    Returns:
        Configured AsyncOpenAI client instance.

    Raises:
        HTTPException: If OpenAI client not configured.
    """
    import os

    from src.api.main import get_openai_client as get_client

    try:
        client = get_client()
    except HTTPException:
        raise

    return client


# Request/Response models


class ResearchAnalyzeRequest(BaseModel):
    """Request model for niche analysis.

    Attributes:
        keywords: List of keyword strings to analyze.
    """

    keywords: list[str] = Field(..., min_length=1, description="Keywords to analyze")


class ResearchAnalyzeResponse(BaseModel):
    """Response model for niche analysis."""

    recommendations: list[dict]
    analyzed_at: str


# Request model for verification endpoint
class ResearchVerifyRequest(BaseModel):
    """Request model for verifying niche recommendations.

    Attributes:
        recommendations: List of NicheRecommendation objects to verify.
    """

    recommendations: list[dict] = Field(..., description="Niche recommendations to verify")


class ResearchVerifyResponse(BaseModel):
    """Response model for verification endpoint."""

    verified_niches: list[dict]
    summary: dict[str, int]
    verified_at: str


# Routes


@router.post("/analyze", response_model=ResearchAnalyzeResponse, status_code=201)
async def analyze_niche_endpoint(
    request: ResearchAnalyzeRequest,
    client: AsyncOpenAI = Depends(get_openai_client),
) -> ResearchAnalyzeResponse:
    """Analyze keywords and return niche recommendations.

    Takes a list of keywords as input and returns 3+ AI-generated
    niche recommendations with demand estimates, competition levels,
    target audiences, and source citations.

    Args:
        request: ResearchAnalyzeRequest with keywords list.
        client: OpenAI client dependency (injected).

    Returns:
        ResearchAnalyzeResponse with generated recommendations.

    Raises:
        HTTPException: If analysis fails or validation fails.
    """
    try:
        # Call the analyzer
        recommendations = await analyze_niche(
            keywords=request.keywords,
            client=client,
        )

        return ResearchAnalyzeResponse(
            recommendations=[
                {
                    "niche": rec.niche,
                    "target_audience": rec.target_audience,
                    "demand_estimate": rec.demand_estimate,
                    "competition_level": rec.competition_level,
                    "recommended_formats": rec.recommended_formats,
                    "rationale": rec.rationale,
                    "sources": rec.sources,
                }
                for rec in recommendations
            ],
            analyzed_at=datetime.utcnow().isoformat(),
        )

    except ValueError as e:
        # Validation error
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
    except NicheAnalysisError as e:
        # Analysis failed after retries
        raise HTTPException(
            status_code=503,
            detail=f"Niche analysis failed: {str(e)}",
        )


@router.post("/verify", response_model=ResearchVerifyResponse, status_code=201)
async def verify_niches_endpoint(request: ResearchVerifyRequest) -> ResearchVerifyResponse:
    """Verify niche recommendations with real market data from Google Trends.

    Takes a list of NicheRecommendation objects, fetches real search interest
    data from Google Trends, calculates demand scores using the proven formula,
    and applies threshold logic.

    Args:
        request: ResearchVerifyRequest with list of recommendations.

    Returns:
        ResearchVerifyResponse with verified niches and demand scores.

    Raises:
        HTTPException: If verification fails or rate limit exceeded.
    """
    try:
        # Convert dict back to NicheRecommendation objects
        recommendations: list[NicheRecommendation] = []
        for rec_dict in request.recommendations:
            recommendation = NicheRecommendation(**rec_dict)
            recommendations.append(recommendation)

        # Call the verifier
        verified_niches = verify_demand(recommendations)

        # Generate summary
        summary = get_verification_summary(verified_niches)

        return ResearchVerifyResponse(
            verified_niches=verified_niches,
            summary=summary,
            verified_at=datetime.utcnow().isoformat(),
        )

    except VerificationError as e:
        # Google Trends rate limit or API error
        raise HTTPException(
            status_code=429,
            detail=f"Niche verification failed (rate limit): {str(e)}",
        )
    except ValueError as e:
        # Validation error
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
