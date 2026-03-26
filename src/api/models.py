"""Pydantic models for API request/response schemas.

Defines the data structures for workflow management API endpoints:
- Workflow start requests/responses
- Execution status queries
- Real-time streaming updates
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkflowStartRequest(BaseModel):
    """Request to start a workflow execution.

    Attributes:
        workflow_name: Name of the workflow to execute (e.g., 'playbook').
        initial_inputs: Optional dict of initial state values.
    """

    workflow_name: str = Field(default="playbook", description="Workflow to execute")
    initial_inputs: Optional[dict[str, Any]] = Field(
        default=None, description="Initial state values"
    )


class WorkflowStartResponse(BaseModel):
    """Response from starting a workflow.

    Attributes:
        execution_id: Unique thread ID for this execution.
        status: Initial status (typically 'running').
        message: Human-readable message about the start.
    """

    execution_id: str = Field(description="Unique execution identifier (thread_id)")
    status: str = Field(default="running", description="Initial execution status")
    message: str = Field(default="Workflow started", description="Status message")


class ExecutionStatusResponse(BaseModel):
    """Execution status details.

    Attributes:
        id: Execution/thread ID.
        workflow_name: Name of the workflow.
        status: Current status (pending/running/completed/failed).
        current_step: Name of the step currently executing.
        error_message: Error details if failed.
        created_at: When execution started.
        updated_at: Last update time.
    """

    id: str = Field(description="Execution ID")
    workflow_name: str = Field(description="Workflow name")
    status: str = Field(description="Execution status")
    current_step: Optional[str] = Field(default=None, description="Current step name")
    error_message: Optional[str] = Field(default=None, description="Error if failed")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class ExecutionListResponse(BaseModel):
    """List of workflow executions.

    Attributes:
        executions: List of execution status objects.
        total: Total count of executions.
        limit: Number requested.
        offset: Offset for pagination.
    """

    executions: list[ExecutionStatusResponse] = Field(description="Execution list")
    total: int = Field(description="Total count")
    limit: int = Field(description="Items per page")
    offset: int = Field(description="Page offset")


class WorkflowStreamUpdate(BaseModel):
    """Real-time workflow state update via WebSocket.

    Attributes:
        execution_id: The thread ID this update applies to.
        current_step: Name of current step.
        status: Overall execution status.
        step_results: Results from completed steps.
        errors: Any errors encountered.
        timestamp: When this update was generated.
    """

    execution_id: str = Field(description="Execution ID")
    current_step: str = Field(description="Current step name")
    status: str = Field(description="Overall status")
    step_results: dict[str, Any] = Field(default_factory=dict, description="Step outcomes")
    errors: list[str] = Field(default_factory=list, description="Errors encountered")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Update time")
