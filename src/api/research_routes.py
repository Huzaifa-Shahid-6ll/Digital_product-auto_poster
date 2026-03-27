"""API routes for niche research.

REST endpoints for:
- POST /api/research/analyze - Analyze keywords and get niche recommendations
- POST /api/research/verify - Verify niche recommendations with Google Trends

Mounted at /api/research in main app.
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.niche_research.analyzer import NicheAnalysisError, analyze_niche
from src.niche_research.schemas import NicheRecommendation
from src.niche_research.verifier import VerificationError, get_verification_summary, verify_demand
from src.workflows.research import get_research_workflow, USER_DECISION

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


# Request model for starting research workflow
class ResearchStartRequest(BaseModel):
    """Request model for starting the research workflow.

    Attributes:
        keywords: List of keyword strings to research.
        thread_id: Optional thread ID for checkpoint persistence.
    """

    keywords: list[str] = Field(..., min_length=1, description="Keywords to research")
    thread_id: Optional[str] = Field(None, description="Optional thread ID")


class ResearchStartResponse(BaseModel):
    """Response model for starting research workflow."""

    thread_id: str
    checkpoint_data: dict[str, Any]
    current_step: str
    errors: list[str]


# Request model for user approval/decision
class ResearchApproveRequest(BaseModel):
    """Request model for user decision on verified niches.

    Attributes:
        thread_id: Thread ID from checkpoint response.
        decision: User decision - proceed|retry|cancel
    """

    thread_id: str = Field(..., description="Thread ID from checkpoint")
    decision: str = Field(..., pattern="^(proceed|retry|cancel)$", description="User decision")


class ResearchApproveResponse(BaseModel):
    """Response model for user decision."""

    thread_id: str
    decision: str
    status: str
    next_action: str


# Request model for status endpoint
class ResearchStatusResponse(BaseModel):
    """Response model for workflow status."""

    thread_id: str
    current_step: str
    checkpoint_data: Optional[dict[str, Any]]
    user_decision: Optional[str]
    errors: list[str]


# In-memory storage for workflow states (MVP - should use SQLite in production)
_workflow_states: dict[str, dict[str, Any]] = {}


# Workflow control endpoints


@router.post("/start", response_model=ResearchStartResponse, status_code=201)
async def start_research_workflow(request: ResearchStartRequest) -> ResearchStartResponse:
    """Start the complete research workflow.

    Runs analyze + verify + checkpoint in sequence, then returns
    checkpoint_data for user review. The workflow pauses at checkpoint.

    Args:
        request: ResearchStartRequest with keywords.

    Returns:
        ResearchStartResponse with thread_id and checkpoint_data.

    Raises:
        HTTPException: If workflow fails.
    """
    try:
        workflow = get_research_workflow()

        # Run the workflow
        result = workflow.start(
            keywords=request.keywords,
            thread_id=request.thread_id,
        )

        # Store state for later retrieval
        if request.thread_id:
            _workflow_states[request.thread_id] = result

        return ResearchStartResponse(**result)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Workflow failed: {str(e)}",
        )


@router.post("/approve", response_model=ResearchApproveResponse, status_code=200)
async def approve_research_workflow(request: ResearchApproveRequest) -> ResearchApproveResponse:
    """Submit user decision to resume workflow.

    After reviewing checkpoint_data, user submits decision:
    - proceed: Continue to product generation
    - retry: Restart with new keywords
    - cancel: Stop the workflow

    Args:
        request: ResearchApproveRequest with thread_id and decision.

    Returns:
        ResearchApproveResponse with next_action.

    Raises:
        HTTPException: If thread not found or invalid decision.
    """
    # Get stored state
    state = _workflow_states.get(request.thread_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Thread {request.thread_id} not found",
        )

    # Update with user decision
    workflow = get_research_workflow()
    result = workflow.approve(
        thread_id=request.thread_id,
        decision=request.decision,
    )

    # Update stored state
    state["user_decision"] = request.decision
    state["decision_status"] = result["status"]
    _workflow_states[request.thread_id] = state

    return ResearchApproveResponse(**result)


@router.get("/status/{thread_id}", response_model=ResearchStatusResponse)
async def get_research_status(thread_id: str) -> ResearchStatusResponse:
    """Get workflow status for a thread.

    Returns current step, checkpoint_data (if at checkpoint),
    and user_decision (if decided).

    Args:
        thread_id: The thread ID to check.

    Returns:
        ResearchStatusResponse with current status.

    Raises:
        HTTPException: If thread not found.
    """
    state = _workflow_states.get(thread_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail=f"Thread {thread_id} not found",
        )

    return ResearchStatusResponse(
        thread_id=thread_id,
        current_step=state.get("current_step", "unknown"),
        checkpoint_data=state.get("checkpoint_data"),
        user_decision=state.get("user_decision"),
        errors=state.get("errors", []),
    )
