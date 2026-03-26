"""API routes for review workflow - human-in-the-loop approval.

REST endpoints for:
- POST /api/reviews/ideas - Submit ideas for review, returns review_id
- POST /api/reviews/select - User selects an idea, triggers product generation
- POST /api/reviews/approve - User approves the product
- POST /api/reviews/reject - User rejects, returns to idea generation
- GET /api/reviews/{review_id} - Get current review state and contents

Per D-04: Approve then create pattern.
Per D-05: Web dashboard for review and approval.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.product_generation.schemas import ProductIdea
from src.workflows.product_review import (
    ReviewApproveRequest,
    ReviewApproveResponse,
    ReviewEvent,
    ReviewRejectRequest,
    ReviewRejectResponse,
    ReviewSelectRequest,
    ReviewSelectResponse,
    ReviewSession,
    ReviewSessionCreate,
    ReviewSessionResponse,
    ReviewState,
    get_review_workflow,
)

# Create router
router = APIRouter(prefix="/reviews", tags=["reviews"])

# Global instances
_generator = None
_validator = None


def set_generator(generator):
    """Set the global product generator instance."""
    global _generator
    _generator = generator


def set_validator(validator):
    """Set the global product validator instance."""
    global _validator
    _validator = validator


def get_generator():
    """Get or create ProductGenerator instance."""
    global _generator
    if _generator is None:
        try:
            from src.product_generation.generator import ProductGenerator
            from openai import OpenAI
            import os

            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                _generator = ProductGenerator(client=OpenAI(api_key=api_key))
            else:
                _generator = ProductGenerator(client=None)
        except ImportError:
            from src.product_generation.generator import ProductGenerator

            _generator = ProductGenerator(client=None)
    return _generator


def get_validator():
    """Get or create ProductValidator instance."""
    global _validator
    if _validator is None:
        try:
            from src.product_generation.validator import ProductValidator
            from openai import OpenAI
            import os

            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                _validator = ProductValidator(client=OpenAI(api_key=api_key))
            else:
                _validator = ProductValidator(client=None)
        except ImportError:
            from src.product_generation.validator import ProductValidator

            _validator = ProductValidator(client=None)
    return _validator


# Routes


@router.post("/ideas", response_model=ReviewSessionResponse, status_code=201)
async def submit_ideas_for_review(request: ReviewSessionCreate) -> ReviewSessionResponse:
    """Submit ideas for review.

    Creates a new review session with the provided ideas.
    Returns review_id and state (IDEAS_GENERATED).

    Args:
        request: ReviewSessionCreate with niche and ideas.

    Returns:
        ReviewSessionResponse with review_id and initial state.
    """
    workflow = get_review_workflow()

    # Convert request ideas to ProductIdea objects
    ideas = [ProductIdea(**idea.model_dump()) for idea in request.ideas]

    # Create review session
    session = workflow.create_session(niche=request.niche, ideas=ideas)

    return ReviewSessionResponse(
        review_id=session.review_id,
        state=session.state,
        niche=session.niche,
        ideas=session.ideas,
        selected_idea_id=session.selected_idea_id,
        product_data=session.product_data,
        validation_score=session.validation_score,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.post("/select", response_model=ReviewSelectResponse)
async def select_idea(request: ReviewSelectRequest) -> ReviewSelectResponse:
    """User selects an idea from the review session.

    Transitions to IDEA_SELECTED state, then generates the product.
    Returns product data and validation score.

    Args:
        request: ReviewSelectRequest with review_id and selected_idea_id.

    Returns:
        ReviewSelectResponse with product data and validation score.

    Raises:
        HTTPException: If review session not found or invalid state.
    """
    workflow = get_review_workflow()

    # Get session to find the selected idea
    session = workflow.get_session(request.review_id)
    if not session:
        raise HTTPException(
            status_code=404, detail=f"Review session '{request.review_id}' not found"
        )

    # First, transition to IDEA_SELECTED
    session, error = workflow.select_idea(request.review_id, request.selected_idea_id)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # Now generate the product
    # Find the selected idea details
    selected_idea = None
    for idea in session.ideas:
        if idea["id"] == request.selected_idea_id:
            selected_idea = idea
            break

    if not selected_idea:
        raise HTTPException(status_code=400, detail=f"Idea '{request.selected_idea_id}' not found")

    # Generate product
    generator = get_generator()
    product_idea = ProductIdea(
        title=selected_idea["title"],
        format_type=selected_idea["format_type"],
        target_audience=selected_idea["target_audience"],
        unique_angle=selected_idea["unique_angle"],
        key_features=selected_idea["key_features"],
        rationale=selected_idea["rationale"],
    )

    # Generate the product
    try:
        product = generator.generate(product_idea)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product generation failed: {str(e)}")

    # Validate the product
    validator = get_validator()
    try:
        validation = validator.validate(product)
    except Exception as e:
        # Validation failed but product exists - use default score
        validation = type("obj", (object,), {"score": 50.0, "passed": False, "issues": [str(e)]})()

    # Update session with product data
    session, error = workflow.generate_product(
        request.review_id,
        product_data={
            "product_id": product.idea_id,
            "format": product.format,
            "title": product.title,
            "content": product.content.model_dump() if product.content else None,
            "generated_at": product.generated_at.isoformat() if product.generated_at else None,
        },
        validation_score=validation.score,
    )

    if error:
        raise HTTPException(status_code=500, detail=error)

    return ReviewSelectResponse(
        review_id=request.review_id,
        state=session.state,
        product_data={
            "product_id": product.idea_id,
            "format": product.format,
            "title": product.title,
            "content": product.content.model_dump() if product.content else None,
            "generated_at": product.generated_at.isoformat() if product.generated_at else None,
        },
        validation_score=validation.score,
    )


@router.post("/approve", response_model=ReviewApproveResponse)
async def approve_product(request: ReviewApproveRequest) -> ReviewApproveResponse:
    """User approves the generated product.

    Transitions to APPROVED state.
    Product is now ready for marketplace listing (Phase 3).

    Args:
        request: ReviewApproveRequest with review_id.

    Returns:
        ReviewApproveResponse with approval confirmation.

    Raises:
        HTTPException: If review session not found or invalid state.
    """
    workflow = get_review_workflow()

    session, error = workflow.approve(request.review_id)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return ReviewApproveResponse(
        review_id=request.review_id,
        state=ReviewState.APPROVED,
        product_id=session.product_data["product_id"] if session.product_data else "unknown",
        next_steps="Ready for Phase 3 - Marketplace Listing",
    )


@router.post("/reject", response_model=ReviewRejectResponse)
async def reject_product(request: ReviewRejectRequest) -> ReviewRejectResponse:
    """User rejects the generated product.

    Transitions to REJECTED state.
    User can provide feedback for regeneration.

    Args:
        request: ReviewRejectRequest with review_id and optional feedback.

    Returns:
        ReviewRejectResponse with rejection confirmation.

    Raises:
        HTTPException: If review session not found or invalid state.
    """
    workflow = get_review_workflow()

    session, error = workflow.reject(request.review_id, request.feedback)
    if error:
        raise HTTPException(status_code=400, detail=error)

    return ReviewRejectResponse(
        review_id=request.review_id,
        state=ReviewState.REJECTED,
        message="Product rejected. Submit new ideas to start a new review.",
    )


@router.get("/{review_id}", response_model=ReviewSessionResponse)
async def get_review(review_id: str) -> ReviewSessionResponse:
    """Get current review state and contents.

    Args:
        review_id: The review session ID.

    Returns:
        ReviewSessionResponse with current state and contents.

    Raises:
        HTTPException: If review session not found.
    """
    workflow = get_review_workflow()
    session = workflow.get_session(review_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Review session '{review_id}' not found")

    return ReviewSessionResponse(
        review_id=session.review_id,
        state=session.state,
        niche=session.niche,
        ideas=session.ideas,
        selected_idea_id=session.selected_idea_id,
        product_data=session.product_data,
        validation_score=session.validation_score,
        created_at=session.created_at.isoformat(),
        updated_at=session.updated_at.isoformat(),
    )


@router.get("/", response_model=list[ReviewSessionResponse])
async def list_reviews() -> list[ReviewSessionResponse]:
    """List all review sessions.

    Returns:
        List of all ReviewSessionResponse objects.
    """
    workflow = get_review_workflow()
    sessions = workflow.list_sessions()

    return [
        ReviewSessionResponse(
            review_id=session.review_id,
            state=session.state,
            niche=session.niche,
            ideas=session.ideas,
            selected_idea_id=session.selected_idea_id,
            product_data=session.product_data,
            validation_score=session.validation_score,
            created_at=session.created_at.isoformat(),
            updated_at=session.updated_at.isoformat(),
        )
        for session in sessions
    ]
