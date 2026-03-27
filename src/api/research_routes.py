"""API routes for niche research.

REST endpoints for:
- POST /api/research/analyze - Analyze keywords and get niche recommendations

Mounted at /api/research in main app.
"""

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.niche_research.analyzer import NicheAnalysisError, analyze_niche

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

        # Convert to response format
        from datetime import datetime

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
