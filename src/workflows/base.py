"""Base workflow abstraction for defining multi-step workflows.

This module provides the abstract base class for defining workflows
that can be executed by the WorkflowEngine with LangGraph.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Optional

from src.core.state import WorkflowState

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph


@dataclass
class StepDefinition:
    """Definition of a single step in a workflow.

    Attributes:
        name: Unique identifier for the step.
        handler_fn: The function that executes this step.
        retry_policy: Optional retry configuration (max_attempts, backoff).
        is_checkpoint: Whether this step requires human verification.
    """

    name: str
    handler_fn: Callable[[WorkflowState], WorkflowState]
    retry_policy: Optional[dict[str, Any]] = None
    is_checkpoint: bool = False


class BaseWorkflow(ABC):
    """Abstract base class for defining multi-step workflows.

    Subclass this to define your own workflow with custom steps.
    The WorkflowEngine will compile your workflow into a LangGraph
    and execute it with state persistence.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the workflow name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return the workflow description."""
        pass

    @property
    @abstractmethod
    def steps(self) -> list[StepDefinition]:
        """Return the list of step definitions in execution order."""
        pass

    @abstractmethod
    def get_initial_state(self) -> WorkflowState:
        """Return the initial state for a new workflow execution."""
        pass

    def add_step(
        self,
        name: str,
        handler_fn: Callable[[WorkflowState], WorkflowState],
        is_checkpoint: bool = False,
        retry_policy: Optional[dict[str, Any]] = None,
    ) -> StepDefinition:
        """Helper to create and register a step definition.

        Args:
            name: Unique step name.
            handler_fn: Function that processes this step.
            is_checkpoint: Whether this step needs human verification.
            retry_policy: Optional retry configuration.

        Returns:
            StepDefinition that was added to the workflow.
        """
        step = StepDefinition(
            name=name, handler_fn=handler_fn, is_checkpoint=is_checkpoint, retry_policy=retry_policy
        )
        return step

    @abstractmethod
    def get_graph(self):
        """Return the compiled LangGraph StateGraph.

        The WorkflowEngine calls this to get the graph structure.
        Subclasses should build and compile their graph here.
        """
        pass
