"""LangGraph state schema for workflow execution.

This module defines the TypedDict state that flows through every node
in the LangGraph workflow graph.
"""

from typing import Annotated, TypedDict

from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage


class WorkflowState(TypedDict):
    """State flows through every node in the graph.

    This TypedDict defines the state structure used by LangGraph
    for workflow execution. Each field tracks a specific aspect
    of the workflow progress.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    """History of all messages sent and received during workflow execution.
    
    The add_messages reducer appends new messages to the existing list,
    preserving conversation history for context-aware nodes.
    """

    current_step: str
    """Name of the current step being executed.
    
    This tracks which node/step is currently active in the workflow.
    Used for progress tracking and debugging.
    """

    step_results: dict
    """Results from each completed step.
    
    Dictionary mapping step names to their output data.
    Enables downstream steps to access previous step outputs.
    """

    errors: list[str]
    """Error messages encountered during execution.
    
    Accumulates errors as they occur, allowing the workflow
    to handle them gracefully rather than failing immediately.
    """

    metadata: dict
    """Additional context and metadata for the workflow.
    
    Contains workflow-specific data like niche info, product details,
    marketplace credentials, etc.
    """
