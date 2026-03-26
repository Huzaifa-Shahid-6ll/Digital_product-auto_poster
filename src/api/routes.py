"""API routes for workflow management.

Defines REST endpoints for:
- POST /workflows - Start a workflow execution
- GET /executions/{execution_id} - Get execution status
- GET /executions - List all executions with pagination and filtering

Per D-05: Minimal dashboard - status + history only.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from src.api.models import (
    ExecutionListResponse,
    ExecutionStatusResponse,
    WorkflowStartRequest,
    WorkflowStartResponse,
)
from src.workflows.playbook import PlaybookWorkflow

# Create router
router = APIRouter(tags=["workflows"])

# Global engine reference - will be set by main.py
_engine = None


def set_engine(engine):
    """Set the global engine instance."""
    global _engine
    _engine = engine


def get_engine():
    """Get the global engine instance."""
    global _engine
    return _engine


@router.post("/workflows", response_model=WorkflowStartResponse, status_code=201)
async def start_workflow(request: WorkflowStartRequest) -> WorkflowStartResponse:
    """Start a workflow execution.

    Creates a new execution of the specified workflow and returns
    the execution ID for tracking.

    Args:
        request: Workflow start request with workflow_name and optional inputs.

    Returns:
        Execution ID and initial status.

    Raises:
        HTTPException: If workflow is not found or cannot be started.
    """
    # Select workflow based on name
    if request.workflow_name in ("playbook", "validation"):
        workflow = PlaybookWorkflow()
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Workflow '{request.workflow_name}' not found",
        )

    # Generate execution ID (thread_id)
    execution_id = request.initial_inputs.get("thread_id") if request.initial_inputs else None
    if execution_id is None:
        import uuid

        execution_id = str(uuid.uuid4())

    # Prepare initial state
    initial_state = None
    if request.initial_inputs:
        initial_state = {
            "messages": [],
            "current_step": "pick_niche",
            "step_results": {},
            "errors": [],
            "metadata": request.initial_inputs.get("metadata", {}),
        }

    # Run workflow asynchronously - for now, run synchronously
    # In production, use background tasks for long-running workflows
    engine = get_engine()
    try:
        result = engine.run(initial_state=initial_state, thread_id=execution_id)
        # Workflow completed - get final state
        status = "completed" if not result.get("errors") else "failed"
        current_step = result.get("current_step", "unknown")
    except Exception as e:
        # Workflow failed during execution
        raise HTTPException(
            status_code=500,
            detail=f"Workflow execution failed: {str(e)}",
        )

    return WorkflowStartResponse(
        execution_id=execution_id,
        status=status,
        message=f"Workflow '{request.workflow_name}' started",
    )


@router.get("/executions/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution(execution_id: str) -> ExecutionStatusResponse:
    """Get execution status by ID.

    Retrieves the current state of a workflow execution, including
    current step, status, and any errors.

    Args:
        execution_id: The execution/thread ID to query.

    Returns:
        Execution status details.

    Raises:
        HTTPException: If execution not found.
    """
    engine = get_engine()
    state = engine.get_state(execution_id)

    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Execution '{execution_id}' not found",
        )

    # Determine status from state
    errors = state.get("errors", [])
    current_step = state.get("current_step", "unknown")

    if errors:
        status = "failed"
    elif current_step == "check_results":
        status = "completed"
    else:
        status = "running"

    # Get workflow name from execution
    # For now, default to playbook
    workflow_name = "Digital Product Validation Playbook"

    # Use current time as placeholder for timestamps
    # In production, store timestamps in database
    now = datetime.utcnow()

    return ExecutionStatusResponse(
        id=execution_id,
        workflow_name=workflow_name,
        status=status,
        current_step=current_step,
        error_message=errors[-1] if errors else None,
        created_at=now,
        updated_at=now,
    )


@router.get("/executions", response_model=ExecutionListResponse)
async def list_executions(
    limit: int = Query(default=10, ge=1, le=100, description="Number of executions to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
) -> ExecutionListResponse:
    """List all workflow executions with pagination and filtering.

    Returns a paginated list of recent workflow executions,
    optionally filtered by status.

    Args:
        limit: Maximum number of executions to return.
        offset: Number of executions to skip (for pagination).
        status: Optional filter by status (running/completed/failed).

    Returns:
        List of execution status objects with pagination info.
    """
    engine = get_engine()

    try:
        # Get executions from engine
        executions_data = engine.list_executions(limit=limit + offset)
    except Exception as e:
        # If no executions yet, return empty list
        executions_data = []

    # Convert to response format
    executions = []
    now = datetime.utcnow()

    for exec_data in executions_data:
        thread_id = exec_data.get("configurable", {}).get("thread_id", "unknown")
        checkpoint_id = exec_data.get("checkpoint_id", "")

        # For now, status is unknown without DB lookup
        # In production, query database for accurate status
        exec_status = "completed"  # Placeholder

        # Apply status filter
        if status and exec_status != status:
            continue

        executions.append(
            ExecutionStatusResponse(
                id=thread_id,
                workflow_name="Digital Product Validation Playbook",
                status=exec_status,
                current_step=checkpoint_id or "unknown",
                error_message=None,
                created_at=now,
                updated_at=now,
            )
        )

    # Apply pagination
    paginated = executions[offset : offset + limit]

    return ExecutionListResponse(
        executions=paginated,
        total=len(executions),
        limit=limit,
        offset=offset,
    )
