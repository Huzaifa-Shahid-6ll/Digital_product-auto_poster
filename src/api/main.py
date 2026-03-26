"""FastAPI application for Digital Product Auto-Poster API.

Provides REST API and WebSocket endpoints for workflow management:
- POST /workflows - Start a workflow execution
- GET /executions/{id} - Get execution status
- GET /executions - List all executions
- GET /executions/{id}/stream - WebSocket for real-time updates
- GET /health - Health check endpoint

Per D-05: CLI first + Web Dashboard - this module provides the web API.
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from src.api.models import (
    ExecutionListResponse,
    ExecutionStatusResponse,
    WorkflowStartRequest,
    WorkflowStartResponse,
    WorkflowStreamUpdate,
)
from src.api.routes import router
from src.core.engine import WorkflowEngine, create_engine
from src.db.models import ExecutionStatus
from src.workflows.playbook import PlaybookWorkflow

logger = logging.getLogger(__name__)

# Global engine instance - initialized on startup
_engine: Optional[WorkflowEngine] = None

# Global OpenAI client - initialized on startup
_openai_client: Optional[AsyncOpenAI] = None


def get_engine() -> WorkflowEngine:
    """Get or create the global workflow engine.

    Returns:
        Configured WorkflowEngine instance.
    """
    global _engine
    if _engine is None:
        workflow = PlaybookWorkflow()
        _engine = create_engine(workflow)
    return _engine


def get_openai_client() -> AsyncOpenAI:
    """Get or create the global OpenAI client.

    Returns:
        Configured AsyncOpenAI client instance.

    Raises:
        HTTPException: If OPENAI_API_KEY is not set.
    """
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable.",
            )
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler - startup and shutdown.

    Initializes the workflow engine on startup and logs on shutdown.
    """
    # Startup
    logger.info("Starting Digital Product Auto-Poster API")
    engine = get_engine()  # Initialize engine
    # Wire engine to routes
    from src.api import routes as api_routes

    api_routes.set_engine(engine)
    yield
    # Shutdown
    logger.info("Shutting down Digital Product Auto-Poster API")


# Create FastAPI application
app = FastAPI(
    title="Digital Product Auto-Poster API",
    description="API for workflow automation - start, monitor, and manage digital product validation workflows",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware - allow all origins for MVP development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
from src.api import routes as api_routes

app.include_router(api_routes.router, prefix="/api/v1")

# Register idea generation routes
from src.api import idea_routes as idea_api_routes

app.include_router(idea_api_routes.router, prefix="/api")

# Register product generation routes
from src.api import product_routes as product_api_routes

app.include_router(product_api_routes.router, prefix="/api")

# Register review workflow routes
from src.api import review_routes as review_api_routes

app.include_router(review_api_routes.router, prefix="/api")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status response.
    """
    return {"status": "healthy", "service": "digital-product-auto-poster"}


# WebSocket connection manager for real-time updates
class ConnectionManager:
    """Manages WebSocket connections for real-time workflow updates."""

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, execution_id: str, websocket: WebSocket):
        """Accept a new WebSocket connection.

        Args:
            execution_id: The execution ID to subscribe to.
            websocket: The WebSocket connection.
        """
        await websocket.accept()
        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = []
        self.active_connections[execution_id].append(websocket)
        logger.info(f"WebSocket connected for execution: {execution_id}")

    def disconnect(self, execution_id: str, websocket: WebSocket):
        """Remove a WebSocket connection.

        Args:
            execution_id: The execution ID unsubscribe from.
            websocket: The WebSocket connection to remove.
        """
        if execution_id in self.active_connections:
            if websocket in self.active_connections[execution_id]:
                self.active_connections[execution_id].remove(websocket)
            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]

    async def send_update(self, execution_id: str, update: WorkflowStreamUpdate):
        """Send an update to all connections for an execution.

        Args:
            execution_id: The execution ID to send updates for.
            update: The update data to send.
        """
        if execution_id in self.active_connections:
            for connection in self.active_connections[execution_id]:
                try:
                    await connection.send_json(update.model_dump())
                except Exception as e:
                    logger.error(f"Error sending WebSocket update: {e}")


# Global connection manager
manager = ConnectionManager()


@app.websocket("/ws/executions/{execution_id}")
async def websocket_executions(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for real-time execution updates.

    Streams workflow state every second until completion or error.

    Args:
        execution_id: The execution ID to stream updates for.
        websocket: The WebSocket connection.
    """
    await manager.connect(execution_id, websocket)
    try:
        engine = get_engine()

        # Send initial state
        state = engine.get_state(execution_id)
        if state:
            update = WorkflowStreamUpdate(
                execution_id=execution_id,
                current_step=state.get("current_step", "unknown"),
                status=state.get("status", "running"),
                step_results=state.get("step_results", {}),
                errors=state.get("errors", []),
            )
            await manager.send_update(execution_id, update)

        # Stream updates - in production, this would be async/background
        # For MVP, we just send current state once
        # The client can poll GET /executions/{id} for updates
        await websocket.send_json({"message": "Connected to execution stream"})

    except WebSocketDisconnect:
        manager.disconnect(execution_id, websocket)
        logger.info(f"WebSocket disconnected for execution: {execution_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(execution_id, websocket)


# Exception handlers for workflow errors
@app.exception_handler(Exception)
async def workflow_exception_handler(request, exc):
    """Handle workflow-related exceptions.

    Args:
        request: The incoming request.
        exc: The exception that was raised.

    Returns:
        HTTP error response.
    """
    logger.error(f"Workflow error: {exc}")
    raise HTTPException(status_code=500, detail=str(exc))
