"""Playbook workflow implementation - 10-step Digital Product Validation Playbook.

This module implements the complete 10-step workflow from VISION.md:
1. pick_niche - User inputs niche keywords
2. check_demand - Verify market demand on Etsy
3. decide_angle - Choose competitor to beat
4. define_product - Plain language product description
5. build_minimum - Create smallest version
6. make_credible - Add professional styling
7. set_price - Price for validation ($9-$19)
8. create_listing - Generate Etsy listing
9. get_traffic - Drive traffic to listing
10. check_results - Analyze performance
"""

from typing import Any

from src.core.state import WorkflowState
from src.workflows.base import BaseWorkflow, StepDefinition


# Step 1: Pick a niche
def handle_pick_niche(state: WorkflowState) -> WorkflowState:
    """Step 1: User inputs niche keywords.

    Accepts niche keywords from user input and stores them in state.
    """
    niche_keywords = state.get("metadata", {}).get("niche_keywords", [])
    state["step_results"]["pick_niche"] = {
        "keywords": niche_keywords,
        "status": "completed",
        "message": f"Niche selected: {', '.join(niche_keywords)}",
    }
    state["current_step"] = "check_demand"
    return state


# Step 2: Check market demand
def handle_check_demand(state: WorkflowState) -> WorkflowState:
    """Step 2: Verify market demand on Etsy.

    Analyzes the selected niche for existing digital products,
    sales volume, and competition level.
    """
    niche = state.get("step_results", {}).get("pick_niche", {}).get("keywords", [])
    # Placeholder: In production, this would call Etsy API
    demand_data = {
        "niche": niche,
        "existing_products": 0,
        "avg_sales": 0,
        "competition_level": "unknown",
        "demand_score": 0,
    }
    state["step_results"]["check_demand"] = {
        "data": demand_data,
        "status": "completed",
        "verdict": "pending_analysis",
    }
    state["current_step"] = "decide_angle"
    return state


# Step 3: Decide angle
def handle_decide_angle(state: WorkflowState) -> WorkflowState:
    """Step 3: Choose competitor to beat.

    Studies competitor products to determine differentiation angle.
    """
    competitor = state.get("metadata", {}).get("competitor_product", None)
    state["step_results"]["decide_angle"] = {
        "competitor": competitor,
        "angle": "to_be_determined",
        "differentiation": "pending",
        "status": "completed",
    }
    state["current_step"] = "define_product"
    return state


# Step 4: Define product
def handle_define_product(state: WorkflowState) -> WorkflowState:
    """Step 4: Plain language product description.

    Creates a one-sentence product definition in the format:
    "A [format] that helps [specific person] [do a specific thing]..."
    """
    angle = state.get("step_results", {}).get("decide_angle", {}).get("angle")
    product_def = {
        "format": "placeholder",
        "target_person": "placeholder",
        "specific_action": "placeholder",
        "outcome": "placeholder",
        "definition": "A [format] that helps [specific person] [do specific thing]...",
        "status": "completed",
    }
    state["step_results"]["define_product"] = product_def
    state["current_step"] = "build_minimum"
    return state


# Step 5: Build minimum version
def handle_build_minimum(state: WorkflowState) -> WorkflowState:
    """Step 5: Create smallest version that still feels valuable.

    Creates the initial digital product - checklists, templates,
    planners, trackers, or short guides.
    """
    product_def = state.get("step_results", {}).get("define_product", {})
    state["step_results"]["build_minimum"] = {
        "format": product_def.get("format"),
        "files": [],
        "quality_check": "pending",
        "status": "completed",
    }
    state["current_step"] = "make_credible"
    return state


# Step 6: Make credible
def handle_make_credible(state: WorkflowState) -> WorkflowState:
    """Step 6: Add professional styling without overdesigning.

    Applies consistent fonts, colors, and structure for a
    professional look that builds trust.
    """
    minimum = state.get("step_results", {}).get("build_minimum", {})
    state["step_results"]["make_credible"] = {
        "original_files": minimum.get("files", []),
        "styled_files": [],
        "preview_images": [],
        "status": "completed",
    }
    state["current_step"] = "set_price"
    return state


# Step 7: Set price
def handle_set_price(state: WorkflowState) -> WorkflowState:
    """Step 7: Price for validation ($9-$19).

    Sets initial price low to reduce friction and get first sales.
    """
    state["step_results"]["set_price"] = {
        "price": 0,
        "pricing_tier": "validation",
        "rationale": "Low price for validation phase",
        "status": "completed",
    }
    state["current_step"] = "create_listing"
    return state


# Step 8: Create listing
def handle_create_listing(state: WorkflowState) -> WorkflowState:
    """Step 8: Generate Etsy listing.

    Creates listing with title, description, tags, and images.
    """
    product = state.get("step_results", {}).get("make_credible", {})
    price = state.get("step_results", {}).get("set_price", {}).get("price", 0)
    state["step_results"]["create_listing"] = {
        "title": "",
        "description": "",
        "tags": [],
        "images": product.get("preview_images", []),
        "price": price,
        "listing_url": None,
        "status": "completed",
    }
    state["current_step"] = "get_traffic"
    return state


# Step 9: Get traffic
def handle_get_traffic(state: WorkflowState) -> WorkflowState:
    """Step 9: Drive traffic to listing.

    Implements traffic method: influencer outreach, community
    posting, short-form content, or paid ads.
    """
    listing = state.get("step_results", {}).get("create_listing", {})
    state["step_results"]["get_traffic"] = {
        "listing_url": listing.get("listing_url"),
        "traffic_method": "pending_selection",
        "outreach_list": [],
        "posts_created": [],
        "status": "completed",
    }
    state["current_step"] = "check_results"
    return state


# Step 10: Check results
def handle_check_results(state: WorkflowState) -> WorkflowState:
    """Step 10: Analyze performance like a scientist.

    Reviews metrics after ~14 days: views, clicks, favorites, sales.
    """
    traffic = state.get("step_results", {}).get("get_traffic", {})
    state["step_results"]["check_results"] = {
        "listing_url": traffic.get("listing_url"),
        "views": 0,
        "clicks": 0,
        "favorites": 0,
        "sales": 0,
        "verdict": "pending_analysis",
        "recommendations": [],
        "status": "completed",
    }
    return state


class PlaybookWorkflow(BaseWorkflow):
    """10-step Digital Product Validation Playbook.

    This workflow implements the complete playbook from VISION.md,
    enabling users to validate digital product ideas through a
    structured, data-driven process.
    """

    def __init__(self):
        """Initialize the playbook workflow with all 10 steps."""
        super().__init__()
        self._step_defs = [
            StepDefinition(name="pick_niche", handler_fn=handle_pick_niche, is_checkpoint=False),
            StepDefinition(name="check_demand", handler_fn=handle_check_demand, is_checkpoint=True),
            StepDefinition(name="decide_angle", handler_fn=handle_decide_angle, is_checkpoint=True),
            StepDefinition(
                name="define_product", handler_fn=handle_define_product, is_checkpoint=True
            ),
            StepDefinition(
                name="build_minimum", handler_fn=handle_build_minimum, is_checkpoint=False
            ),
            StepDefinition(
                name="make_credible", handler_fn=handle_make_credible, is_checkpoint=False
            ),
            StepDefinition(name="set_price", handler_fn=handle_set_price, is_checkpoint=True),
            StepDefinition(
                name="create_listing", handler_fn=handle_create_listing, is_checkpoint=False
            ),
            StepDefinition(name="get_traffic", handler_fn=handle_get_traffic, is_checkpoint=False),
            StepDefinition(
                name="check_results", handler_fn=handle_check_results, is_checkpoint=True
            ),
        ]

    @property
    def steps(self) -> list[StepDefinition]:
        """Return the list of step definitions in execution order."""
        return self._step_defs

    @property
    def name(self) -> str:
        return "Digital Product Validation Playbook"

    @property
    def description(self) -> str:
        return "10-step workflow to validate digital product ideas from niche to first sales"

    def get_initial_state(self) -> WorkflowState:
        """Return initial state for a new playbook execution."""
        return {
            "messages": [],
            "current_step": "pick_niche",
            "step_results": {},
            "errors": [],
            "metadata": {},
        }

    def get_graph(self):
        """Build and return the compiled LangGraph StateGraph.

        Creates a graph with conditional edges for branching based on context.
        Uses create_router for step routing decisions.
        """
        from langgraph.graph import StateGraph, START, END

        # Import the router function from engine
        from src.core.engine import create_router

        graph = StateGraph(WorkflowState)

        # Get step names for routing
        step_names = [step.name for step in self._step_defs]

        # Define custom routing rules for branching
        routing_rules = {
            "check_demand": self._route_after_demand_check,
            "build_minimum": self._route_after_build,
        }

        # Create router with custom rules
        router = create_router(step_names, routing_rules)

        # Add all steps as nodes
        for step in self._step_defs:
            graph.add_node(step.name, step.handler_fn)

        # Connect START to first step
        graph.add_edge(START, "pick_niche")

        # Add conditional edges for each step
        for step in self._step_defs:
            if step.is_checkpoint:
                # Checkpoint steps still use conditional routing but can pause
                graph.add_conditional_edges(step.name, router)
            else:
                # Non-checkpoint steps use conditional routing
                graph.add_conditional_edges(step.name, router)

        return graph.compile()

    def _route_after_demand_check(self, state: WorkflowState) -> str:
        """Route after checking demand - branch based on demand score.

        If demand is low (score < 5), route back to pick_niche to try a new niche.
        If demand is sufficient, proceed to decide_angle.
        """
        demand_result = state.get("step_results", {}).get("check_demand", {})
        demand_score = demand_result.get("data", {}).get("demand_score", 0)

        if demand_score < 5:
            return "pick_niche"  # Retry with different niche
        return "decide_angle"

    def _route_after_build(self, state: WorkflowState) -> str:
        """Route after building minimum - branch based on quality check.

        If quality check fails, route back to build_minimum to retry.
        If quality passes, proceed to make_credible.
        """
        build_result = state.get("step_results", {}).get("build_minimum", {})
        quality = build_result.get("quality_check", "pending")

        if quality == "failed":
            return "build_minimum"  # Retry
        return "make_credible"
