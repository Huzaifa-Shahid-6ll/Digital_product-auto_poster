"""SQLAlchemy database models for workflow persistence.

This module defines the database schema for persisting workflow
execution state and step history.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ExecutionStatus(PyEnum):
    """Status of a workflow execution.

    Represents the lifecycle of a workflow run from initialization
    through completion or failure.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


class WorkflowExecution(Base):
    """Stores workflow execution state for persistence.

    This model tracks the overall execution of a workflow, including
    its current state, status, and any error information.
    """

    __tablename__ = "workflow_executions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    """Unique identifier - corresponds to thread_id for LangGraph."""

    workflow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Name of the workflow being executed."""

    status: Mapped[ExecutionStatus] = mapped_column(
        Enum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING
    )
    """Current execution status."""

    current_step: Mapped[str] = mapped_column(String(255), nullable=True)
    """Name of the current step being executed."""

    state_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    """Serialized LangGraph state data."""

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Error message if execution failed."""

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    """When the execution was created."""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    """Last time the execution was updated."""

    # Relationship to steps
    steps: Mapped[list["WorkflowStep"]] = relationship(
        "WorkflowStep", back_populates="execution", cascade="all, delete-orphan"
    )


class WorkflowStep(Base):
    """Stores individual step execution history.

    This model tracks each step within a workflow execution,
    enabling detailed audit trails and debugging.
    """

    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """Auto-incrementing step ID."""

    execution_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False
    )
    """Foreign key to parent workflow execution."""

    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Name of the step (e.g., 'research_niche', 'generate_ideas')."""

    status: Mapped[str] = mapped_column(String(50), nullable=False)
    """Step status: 'started', 'completed', 'failed'."""

    input_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    """Input data passed to the step."""

    output_data: Mapped[dict] = mapped_column(JSON, nullable=True)
    """Output data produced by the step."""

    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Error message if step failed."""

    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    """When the step started executing."""

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """When the step completed (null if still running)."""

    # Relationship to parent execution
    execution: Mapped["WorkflowExecution"] = relationship(
        "WorkflowExecution", back_populates="steps"
    )
