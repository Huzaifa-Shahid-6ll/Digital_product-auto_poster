"""API routes for product idea generation.

REST endpoints for:
- POST /api/ideas/generate - Generate product ideas for a niche

Mounted at /api/ideas in main app.
"""

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from src.product_generation.ideas import IdeaGenerator, IdeaGenerationError
from src.product_generation.schemas import IdeaSet

# Create router
router = APIRouter(tags=["ideas"])

# Request/Response models


class IdeaGenerateRequest(BaseModel):
    """Request model for idea generation.

    Attributes:
        niche: The niche/topic to generate ideas for.
        count: Optional number of ideas to generate (default 3).
    """

    niche: str = Field(..., min_length=3, description="The niche to generate ideas for")
    count: int = Field(default=3, ge=1, le=10, description="Number of ideas to generate")


class IdeaGenerateResponse(BaseModel):
    """Response model for idea generation."""

    ideas: list[dict]
    niche: str
    generated_at: str


# Dependency for IdeaGenerator


def get_idea_generator() -> IdeaGenerator:
    """Get or create IdeaGenerator instance with OpenAI client.

    Returns:
        Configured IdeaGenerator instance.

    Raises:
        HTTPException: If OpenAI client not configured.
    """
    from src.api.main import get_openai_client

    try:
        client = get_openai_client()
    except HTTPException:
        raise

    return IdeaGenerator(client)


# Routes


@router.post("/generate", response_model=IdeaGenerateResponse, status_code=201)
async def generate_ideas(
    request: IdeaGenerateRequest,
    generator: IdeaGenerator = Depends(get_idea_generator),
) -> IdeaGenerateResponse:
    """Generate product ideas for a given niche.

    Takes a niche as input and returns 3+ product ideas with rationale.
    Each idea includes format type, target audience, unique angle,
    key features, and explanation of niche fit.

    Args:
        request: IdeaGenerateRequest with niche and optional count.
        generator: IdeaGenerator dependency (injected).

    Returns:
        IdeaGenerateResponse with generated ideas.

    Raises:
        HTTPException: If niche validation fails or generation fails.
    """
    try:
        # Generate ideas
        idea_set = await generator.generate(
            niche=request.niche,
            count=request.count,
        )

        # Convert to response format
        return IdeaGenerateResponse(
            ideas=[
                {
                    "title": idea.title,
                    "format_type": idea.format_type,
                    "target_audience": idea.target_audience,
                    "unique_angle": idea.unique_angle,
                    "key_features": idea.key_features,
                    "rationale": idea.rationale,
                }
                for idea in idea_set.ideas
            ],
            niche=idea_set.niche,
            generated_at=idea_set.generated_at.isoformat(),
        )

    except ValueError as e:
        # Validation error (niche too short, etc.)
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
    except IdeaGenerationError as e:
        # Generation failed after retries
        raise HTTPException(
            status_code=503,
            detail=f"Idea generation failed: {str(e)}",
        )
