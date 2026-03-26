"""LangGraph workflow engine with checkpoint persistence.

This module provides the WorkflowEngine class that compiles and executes
workflows using LangGraph's StateGraph with SQLite-based checkpoint persistence.
"""

import uuid
from typing import Any, Callable, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, START, END

from src.core.checkpoint import create_checkpointer
from src.core.state import WorkflowState
from src.workflows.base import BaseWorkflow


def create_router(
    step_names: list[str], routing_rules: Optional[dict[str, Callable[[WorkflowState], str]]] = None
) -> Callable[[WorkflowState], str]:
    """Create a routing function for conditional step execution.

    This function examines workflow state to determine the next step,
    enabling branching based on context rather than just linear progression.

    Args:
        step_names: List of step names in execution order.
        routing_rules: Optional dict mapping step names to routing functions.

    Returns:
        Routing function that takes state and returns next step name.

    Example:
        >>> def route_after_check_demand(state):
        ...     demand = state.get('step_results', {}).get('check_demand', {}).get('demand_score', 0)
        ...     return 'decide_angle' if demand > 5 else 'pick_niche'  # retry if low demand
        >>> router = create_router(['pick_niche', 'check_demand', ...], {'check_demand': route_after_check_demand})
    """
    default_router: dict[str, Callable[[WorkflowState], str]] = {}

    if routing_rules:
        default_router.update(routing_rules)

    def router(state: WorkflowState) -> str:
        """Determine next step based on current state.

        Args:
            state: Current workflow state.

        Returns:
            Name of the next step to execute.
        """
        current = state.get("current_step", "")

        # Check for custom routing rule
        if current in default_router:
            return default_router[current](state)

        # Default: find next step in sequence
        if current in step_names:
            idx = step_names.index(current)
            if idx + 1 < len(step_names):
                return step_names[idx + 1]

        # End of workflow
        return END

    return router


class WorkflowEngine:
    """Engine for compiling and executing LangGraph workflows.

    This class handles:
    - Compiling workflow definitions into executable graphs
    - Executing workflows with state persistence
    - Managing thread/checkpoint state for resume capability

    Attributes:
        workflow: The workflow definition to execute.
        checkpointer: Optional checkpoint saver for state persistence.
        db_path: Path to SQLite database for persistence.
    """

    def __init__(
        self,
        workflow: BaseWorkflow,
        db_path: str = "workflows.db",
        checkpointer: Optional[BaseCheckpointSaver] = None,
    ):
        """Initialize the workflow engine.

        Args:
            workflow: The workflow to execute.
            db_path: Path to SQLite database for checkpoint storage.
            checkpointer: Optional custom checkpointer. If None, creates one.
        """
        self.workflow = workflow
        self.db_path = db_path
        self._checkpointer = checkpointer or create_checkpointer(db_path)
        self._compiled_graph = None

    def compile(self) -> Any:
        """Compile the workflow into an executable LangGraph.

        Returns:
            Compiled LangGraph ready for execution.
        """
        if self._compiled_graph is None:
            self._compiled_graph = self.workflow.get_graph()
            # Attach checkpointer to enable state persistence
            self._compiled_graph.name = self.workflow.name
        return self._compiled_graph

    def run(self, initial_state: Optional[dict] = None, thread_id: Optional[str] = None) -> dict:
        """Execute the workflow from initial state.

        Args:
            initial_state: Initial state dict. Uses workflow.get_initial_state() if None.
            thread_id: Thread identifier for checkpoint persistence. Auto-generated if None.

        Returns:
            Final workflow state after execution.
        """
        if thread_id is None:
            thread_id = str(uuid.uuid4())

        if initial_state is None:
            initial_state = self.workflow.get_initial_state()

        # Compile the graph
        graph = self.compile()

        # Execute with checkpoint config
        config = {"configurable": {"thread_id": thread_id}}

        # Run the workflow
        result = graph.invoke(initial_state, config)

        return result

    def get_state(self, thread_id: str) -> Optional[WorkflowState]:
        """Retrieve current state for a thread.

        Args:
            thread_id: The thread/flow identifier.

        Returns:
            Current WorkflowState or None if not found.
        """
        checkpoint = self._checkpointer.get(thread_id)
        if checkpoint:
            return checkpoint.get("channel_values")
        return None

    def list_executions(self, limit: int = 10) -> list[dict]:
        """List recent workflow executions.

        Args:
            limit: Maximum number of executions to return.

        Returns:
            List of execution records with thread_id and checkpoint info.
        """
        # This would typically query a executions table
        # For now, list checkpoints as proxy
        return self._checkpointer.list("default", limit)

    def resume(self, thread_id: str, new_state: Optional[dict] = None) -> dict:
        """Resume a paused workflow from checkpoint.

        Args:
            thread_id: Thread identifier for the paused execution.
            new_state: Optional state updates to apply before resuming.

        Returns:
            Updated workflow state after resume.
        """
        graph = self.compile()

        config = {"configurable": {"thread_id": thread_id}}

        # Get current checkpoint state
        current_state = self.get_state(thread_id)

        if current_state is None:
            raise ValueError(f"No checkpoint found for thread_id: {thread_id}")

        # Merge with new state if provided
        if new_state:
            current_state.update(new_state)

        # Resume execution
        result = graph.invoke(current_state, config)

        return result


def create_engine(workflow: BaseWorkflow, db_path: str = "workflows.db") -> WorkflowEngine:
    """Factory function to create a configured WorkflowEngine.

    Args:
        workflow: The workflow to execute.
        db_path: Path to SQLite database for persistence.

    Returns:
        Configured WorkflowEngine instance.

    Example:
        >>> from src.workflows.playbook import PlaybookWorkflow
        >>> wf = PlaybookWorkflow()
        >>> engine = create_engine(wf, "my_workflows.db")
        >>> result = engine.run()
    """
    return WorkflowEngine(workflow=workflow, db_path=db_path)
