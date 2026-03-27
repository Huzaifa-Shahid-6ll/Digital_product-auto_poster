"""LangGraph workflow for niche research with human verification checkpoint.

This module implements the complete research workflow that:
1. Analyzes keywords using AI (from analyzer.py)
2. Verifies recommendations using Google Trends (from verifier.py)
3. Pauses at checkpoint for user approval
4. Routes based on user decision (proceed/retry/cancel)

Uses state-based checkpoint pattern (simpler than interrupt for MVP).
"""

import uuid
from typing import Any, Optional

from langgraph.graph import END, StateGraph

from src.core.state import WorkflowState
from src.niche_research.analyzer import analyze_niche, NicheAnalysisError
from src.niche_research.schemas import NicheRecommendation
from src.niche_research.verifier import VerificationError, verify_demand
from src.workflows.base import BaseWorkflow, StepDefinition


# Research-specific state keys
KEYWORDS = "keywords"
RECOMMENDATIONS = "recommendations"
VERIFIED_NICHES = "verified_niches"
CHECKPOINT_DATA = "checkpoint_data"
USER_DECISION = "user_decision"
THREAD_ID = "thread_id"


def create_research_state() -> WorkflowState:
    """Create initial state for research workflow.

    Returns:
        WorkflowState with empty defaults.
    """
    return {
        "messages": [],
        "current_step": "idle",
        "step_results": {},
        "errors": [],
        "metadata": {},
    }


# Step 1: Analyze keywords and generate recommendations
async def analyze_step(state: WorkflowState, client: Any = None) -> WorkflowState:
    """Analyze step - calls analyze_niche() with keywords.

    Args:
        state: Current workflow state containing keywords.
        client: Optional OpenAI client.

    Returns:
        Updated state with recommendations.
    """
    keywords = state["metadata"].get(KEYWORDS, [])

    try:
        recommendations = await analyze_niche(keywords, client)

        state["step_results"]["recommendations"] = [
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
        ]
        state["current_step"] = "analyze"

    except NicheAnalysisError as e:
        state["errors"].append(f"Analysis failed: {str(e)}")
        state["current_step"] = "analyze_error"

    return state


# Step 2: Verify recommendations with Google Trends
def verify_step(state: WorkflowState) -> WorkflowState:
    """Verify step - calls verify_demand() with recommendations.

    Args:
        state: Current workflow state containing recommendations.

    Returns:
        Updated state with verified niches.
    """
    recommendations = state["step_results"].get("recommendations", [])

    if not recommendations:
        state["errors"].append("No recommendations to verify")
        state["current_step"] = "verify_error"
        return state

    try:
        # Convert dicts back to NicheRecommendation objects
        rec_objects = [NicheRecommendation(**rec) for rec in recommendations]

        verified_niches = verify_demand(rec_objects)

        state["step_results"]["verified_niches"] = [
            {
                "niche": vn["recommendation"]["niche"],
                "target_audience": vn["recommendation"]["target_audience"],
                "demand_score": vn["demand_score"],
                "demand_level": vn["category"],
                "search_interest": vn["verification_data"]["average_interest"],
                "competition_factor": 1.0
                if vn["recommendation"]["competition_level"] == "low"
                else 0.6
                if vn["recommendation"]["competition_level"] == "medium"
                else 0.3,
                "trend_direction": vn["trend_direction"],
                "verified_at": vn["verification_data"]["queried_at"],
                "sources": vn["verification_data"]["source"],
            }
            for vn in verified_niches
        ]
        state["current_step"] = "verify"

    except VerificationError as e:
        state["errors"].append(f"Verification failed: {str(e)}")
        state["current_step"] = "verify_error"

    return state


# Step 3: Checkpoint - prepare data for human review
def checkpoint_step(state: WorkflowState) -> WorkflowState:
    """Checkpoint step - sets checkpoint_data for UI review.

    This is a state-based checkpoint (not interrupt) - simpler for MVP.
    The workflow pauses here and waits for user decision via API.

    Args:
        state: Current workflow state with verified niches.

    Returns:
        State with checkpoint_data populated for UI review.
    """
    verified_niches = state["step_results"].get("verified_niches", [])

    # Prepare checkpoint data for UI
    checkpoint_data = {
        "verified_niches": verified_niches,
        "summary": {
            "total": len(verified_niches),
            "validated": sum(1 for n in verified_niches if n.get("demand_level") == "validated"),
            "explore": sum(1 for n in verified_niches if n.get("demand_level") == "explore"),
            "low_demand": sum(1 for n in verified_niches if n.get("demand_level") == "low_demand"),
        },
        "review_options": [
            {
                "value": "proceed",
                "label": "Approve & Continue",
                "description": "Proceed to product generation with top niches",
            },
            {
                "value": "retry",
                "label": "Request Retry",
                "description": "Get new recommendations with different keywords",
            },
            {
                "value": "cancel",
                "label": "Cancel Workflow",
                "description": "Stop the research workflow",
            },
        ],
    }

    state["step_results"][CHECKPOINT_DATA] = checkpoint_data
    state["current_step"] = "checkpoint"

    return state


# Step 4: Decision router - routes based on user decision
def decision_router(state: WorkflowState) -> str:
    """Decision router - routes based on user_decision.

    Args:
        state: Current workflow state with user_decision.

    Returns:
        Next step name or END.
    """
    user_decision = state["metadata"].get(USER_DECISION, "")

    if user_decision == "proceed":
        return "proceed"
    elif user_decision == "retry":
        return "retry"
    else:
        # Default to cancel (also for empty decision)
        return END


class NicheResearchWorkflow(BaseWorkflow):
    """LangGraph workflow for niche research with human checkpoint.

    Flow: analyze -> verify -> checkpoint -> decision_router
                                    |
                          (pauses, waits for user)
                                    |
                          proceed/retry/cancel

    Uses state-based checkpoint pattern (simpler than interrupt for MVP).
    """

    def __init__(self):
        """Initialize the research workflow."""
        self._graph: Optional[StateGraph] = None

    @property
    def name(self) -> str:
        """Return the workflow name."""
        return "niche_research"

    @property
    def description(self) -> str:
        """Return the workflow description."""
        return "AI-powered niche research with human verification checkpoint"

    @property
    def steps(self) -> list[StepDefinition]:
        """Return the list of step definitions.

        Returns:
            List of steps: analyze, verify, checkpoint, decision_router
        """
        return [
            StepDefinition(name="analyze", handler_fn=analyze_step, is_checkpoint=False),
            StepDefinition(name="verify", handler_fn=verify_step, is_checkpoint=False),
            StepDefinition(name="checkpoint", handler_fn=checkpoint_step, is_checkpoint=True),
            StepDefinition(name="decision_router", handler_fn=decision_router, is_checkpoint=False),
        ]

    def get_initial_state(self) -> WorkflowState:
        """Return the initial state for a new workflow execution.

        Returns:
            WorkflowState with defaults for research workflow.
        """
        return create_research_state()

    def get_graph(self) -> StateGraph:
        """Build and return the compiled LangGraph StateGraph.

        Returns:
            Compiled StateGraph with research workflow nodes.
        """
        from src.api.main import get_openai_client

        # Get client inside graph to avoid initialization issues
        def analyze_with_client(state: WorkflowState) -> WorkflowState:
            client = get_openai_client()
            return analyze_step(state, client)

        # Build the graph
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("analyze", analyze_with_client)
        workflow.add_node("verify", verify_step)
        workflow.add_node("checkpoint", checkpoint_step)

        # Add edges
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "verify")
        workflow.add_edge("verify", "checkpoint")

        # Add conditional edge from checkpoint to decision
        workflow.add_conditional_edges(
            "checkpoint",
            decision_router,
            {
                "proceed": END,
                "retry": "analyze",  # Loop back to analyze for retry
                END: END,
            },
        )

        # Compile
        self._graph = workflow.compile()
        return self._graph

    def start(
        self,
        keywords: list[str],
        thread_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Start the research workflow.

        Args:
            keywords: List of keywords to analyze.
            thread_id: Optional thread ID for checkpoint persistence.

        Returns:
            Dict with thread_id, checkpoint_data, and status.
        """
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        # Initialize state with keywords
        state = create_research_state()
        state["metadata"][KEYWORDS] = keywords
        state["metadata"][THREAD_ID] = thread_id

        # Run the graph synchronously (for MVP)
        graph = self.get_graph()

        # Run through analyze -> verify -> checkpoint
        # Note: This runs synchronously - checkpoint pauses automatically
        final_state = graph.invoke(state)

        return {
            "thread_id": thread_id,
            "checkpoint_data": final_state["step_results"].get(CHECKPOINT_DATA),
            "current_step": final_state["current_step"],
            "errors": final_state["errors"],
        }

    def get_status(self, thread_id: str) -> Optional[dict[str, Any]]:
        """Get workflow status for a thread.

        Args:
            thread_id: The thread ID to check.

        Returns:
            Dict with status or None if not found.
        """
        # For MVP, we store state in memory
        # TODO: Persist to SQLite for production
        return None  # Will be implemented with checkpoint storage

    def approve(
        self,
        thread_id: str,
        decision: str,
    ) -> dict[str, Any]:
        """Submit user decision to resume workflow.

        Args:
            thread_id: The thread ID.
            decision: User decision (proceed/retry/cancel).

        Returns:
            Dict with final result or trigger for retry.
        """
        # TODO: Load persisted state
        # For now, return the decision response
        return {
            "thread_id": thread_id,
            "decision": decision,
            "status": "decision_received",
            "next_action": "proceed_to_product_generation"
            if decision == "proceed"
            else ("restart_workflow" if decision == "retry" else "workflow_cancelled"),
        }


# Global workflow instance
_workflow: Optional[NicheResearchWorkflow] = None


def get_research_workflow() -> NicheResearchWorkflow:
    """Get or create the global research workflow instance.

    Returns:
        NicheResearchWorkflow instance.
    """
    global _workflow
    if _workflow is None:
        _workflow = NicheResearchWorkflow()
    return _workflow
