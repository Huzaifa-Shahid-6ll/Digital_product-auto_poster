"""Review workflow for human-in-the-loop approval.

This module provides the ReviewWorkflow state machine that manages the
review process from idea generation through product approval.

Per D-04: Approve then create pattern - user reviews ideas, selects one,
system generates product, user approves for marketplace listing.

Per D-05: Web dashboard for review and approval.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from src.product_generation.schemas import ProductIdea


class ReviewState(str, Enum):
    """States in the review workflow.

    IDEAS_GENERATED: Ideas created, waiting for user selection
    IDEA_SELECTED: User selected an idea, ready for product generation
    PRODUCT_GENERATED: Product created, waiting for user review
    APPROVED: User approved product, ready for marketplace
    REJECTED: User rejected, needs regeneration
    """

    IDEAS_GENERATED = "IDEAS_GENERATED"
    IDEA_SELECTED = "IDEA_SELECTED"
    PRODUCT_GENERATED = "PRODUCT_GENERATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ReviewEvent(str, Enum):
    """Events that drive state transitions in review workflow.

    SELECT_IDEA: User picks an idea
    GENERATE_PRODUCT: System creates product from selected idea
    REVIEW_PRODUCT: User views product (with validation score)
    APPROVE: User approves final product
    REJECT: User rejects, return to IDEAS_GENERATED
    """

    SELECT_IDEA = "SELECT_IDEA"
    GENERATE_PRODUCT = "GENERATE_PRODUCT"
    REVIEW_PRODUCT = "REVIEW_PRODUCT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"


# State transition map
TRANSITIONS: dict[ReviewState, dict[ReviewEvent, ReviewState]] = {
    ReviewState.IDEAS_GENERATED: {
        ReviewEvent.SELECT_IDEA: ReviewState.IDEA_SELECTED,
    },
    ReviewState.IDEA_SELECTED: {
        ReviewEvent.GENERATE_PRODUCT: ReviewState.PRODUCT_GENERATED,
    },
    ReviewState.PRODUCT_GENERATED: {
        ReviewEvent.APPROVE: ReviewState.APPROVED,
        ReviewEvent.REJECT: ReviewState.REJECTED,
    },
    ReviewState.REJECTED: {
        ReviewEvent.SELECT_IDEA: ReviewState.IDEA_SELECTED,  # Allow re-selection after reject
    },
    ReviewState.APPROVED: {},  # Terminal state
}


@dataclass
class ReviewSession:
    """A single review session containing ideas, selection, and product.

    Attributes:
        review_id: Unique identifier for this review session.
        niche: The niche the ideas are based on.
        ideas: List of generated product ideas.
        selected_idea_id: ID of the user-selected idea.
        product_data: Generated product data (if any).
        validation_score: Product validation score (if generated).
        state: Current state in the review workflow.
        created_at: When this review session was created.
        updated_at: Last update timestamp.
        feedback: User feedback (if rejected).
    """

    review_id: str
    niche: str
    ideas: list[dict] = field(default_factory=list)
    selected_idea_id: Optional[str] = None
    product_data: Optional[dict] = None
    validation_score: Optional[float] = None
    state: ReviewState = ReviewState.IDEAS_GENERATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    feedback: Optional[str] = None


class ReviewSessionCreate(BaseModel):
    """Request model for creating a review session."""

    niche: str
    ideas: list[ProductIdea]


class ReviewSessionResponse(BaseModel):
    """Response model for review session."""

    review_id: str
    state: ReviewState
    niche: str
    ideas: list[dict]
    selected_idea_id: Optional[str] = None
    product_data: Optional[dict] = None
    validation_score: Optional[float] = None
    created_at: str
    updated_at: str


class ReviewSelectRequest(BaseModel):
    """Request model for selecting an idea."""

    review_id: str
    selected_idea_id: str


class ReviewApproveRequest(BaseModel):
    """Request model for approving a product."""

    review_id: str


class ReviewRejectRequest(BaseModel):
    """Request model for rejecting a product."""

    review_id: str
    feedback: Optional[str] = None


class ReviewSelectResponse(BaseModel):
    """Response model for idea selection."""

    review_id: str
    state: ReviewState
    product_data: dict
    validation_score: float


class ReviewApproveResponse(BaseModel):
    """Response model for product approval."""

    review_id: str
    state: ReviewState
    product_id: str
    next_steps: str


class ReviewRejectResponse(BaseModel):
    """Response model for product rejection."""

    review_id: str
    state: ReviewState
    message: str


class ReviewWorkflow:
    """Review workflow state machine.

    Manages the review process:
    1. User submits ideas for review (IDEAS_GENERATED)
    2. User selects an idea (IDEA_SELECTED)
    3. System generates product (PRODUCT_GENERATED)
    4. User reviews and approves/rejects (APPROVED or REJECTED)

    Per D-04: Approve then create pattern.
    Per D-05: Web dashboard for review and approval.
    """

    def __init__(self):
        """Initialize the review workflow."""
        self._sessions: dict[str, ReviewSession] = {}

    def create_session(self, niche: str, ideas: list[ProductIdea]) -> ReviewSession:
        """Create a new review session with generated ideas.

        Args:
            niche: The niche the ideas are based on.
            ideas: List of ProductIdea objects to review.

        Returns:
            New ReviewSession in IDEAS_GENERATED state.
        """
        review_id = str(uuid.uuid4())
        session = ReviewSession(
            review_id=review_id,
            niche=niche,
            ideas=[
                {
                    "id": str(uuid.uuid4()),
                    "title": idea.title,
                    "format_type": idea.format_type,
                    "target_audience": idea.target_audience,
                    "unique_angle": idea.unique_angle,
                    "key_features": idea.key_features,
                    "rationale": idea.rationale,
                }
                for idea in ideas
            ],
            state=ReviewState.IDEAS_GENERATED,
        )
        self._sessions[review_id] = session
        return session

    def get_session(self, review_id: str) -> Optional[ReviewSession]:
        """Get a review session by ID.

        Args:
            review_id: The review session ID.

        Returns:
            ReviewSession if found, None otherwise.
        """
        return self._sessions.get(review_id)

    def select_idea(
        self, review_id: str, selected_idea_id: str
    ) -> tuple[Optional[ReviewSession], str]:
        """Transition to IDEA_SELECTED state by selecting an idea.

        Args:
            review_id: The review session ID.
            selected_idea_id: The ID of the idea to select.

        Returns:
            Tuple of (updated session or None, error message if any).
        """
        session = self._sessions.get(review_id)
        if not session:
            return None, "Review session not found"

        if session.state != ReviewState.IDEAS_GENERATED:
            return None, f"Cannot select idea in state: {session.state.value}"

        # Verify the selected idea exists
        idea_ids = [idea["id"] for idea in session.ideas]
        if selected_idea_id not in idea_ids:
            return None, f"Idea '{selected_idea_id}' not found in review session"

        session.selected_idea_id = selected_idea_id
        session.state = ReviewState.IDEA_SELECTED
        session.updated_at = datetime.utcnow()
        return session, ""

    def generate_product(
        self, review_id: str, product_data: dict, validation_score: float
    ) -> tuple[Optional[ReviewSession], str]:
        """Transition to PRODUCT_GENERATED state after generating product.

        Args:
            review_id: The review session ID.
            product_data: The generated product data.
            validation_score: The product validation score.

        Returns:
            Tuple of (updated session or None, error message if any).
        """
        session = self._sessions.get(review_id)
        if not session:
            return None, "Review session not found"

        if session.state != ReviewState.IDEA_SELECTED:
            return None, f"Cannot generate product in state: {session.state.value}"

        session.product_data = product_data
        session.validation_score = validation_score
        session.state = ReviewState.PRODUCT_GENERATED
        session.updated_at = datetime.utcnow()
        return session, ""

    def approve(self, review_id: str) -> tuple[Optional[ReviewSession], str]:
        """Transition to APPROVED state - user approves the product.

        Args:
            review_id: The review session ID.

        Returns:
            Tuple of (updated session or None, error message if any).
        """
        session = self._sessions.get(review_id)
        if not session:
            return None, "Review session not found"

        if session.state != ReviewState.PRODUCT_GENERATED:
            return None, f"Cannot approve in state: {session.state.value}"

        session.state = ReviewState.APPROVED
        session.updated_at = datetime.utcnow()
        return session, ""

    def reject(
        self, review_id: str, feedback: Optional[str] = None
    ) -> tuple[Optional[ReviewSession], str]:
        """Transition to REJECTED state - user rejects the product.

        Args:
            review_id: The review session ID.
            feedback: Optional user feedback for rejection.

        Returns:
            Tuple of (updated session or None, error message if any).
        """
        session = self._sessions.get(review_id)
        if not session:
            return None, "Review session not found"

        if session.state != ReviewState.PRODUCT_GENERATED:
            return None, f"Cannot reject in state: {session.state.value}"

        session.state = ReviewState.REJECTED
        session.feedback = feedback
        session.updated_at = datetime.utcnow()
        return session, ""

    def list_sessions(self) -> list[ReviewSession]:
        """List all review sessions.

        Returns:
            List of all ReviewSession objects.
        """
        return list(self._sessions.values())


# Global workflow instance
_workflow: Optional[ReviewWorkflow] = None


def get_review_workflow() -> ReviewWorkflow:
    """Get or create the global review workflow instance.

    Returns:
        ReviewWorkflow instance.
    """
    global _workflow
    if _workflow is None:
        _workflow = ReviewWorkflow()
    return _workflow
