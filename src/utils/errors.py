"""Custom error classes for workflow automation.

This module provides a hierarchy of exceptions for different error scenarios
in the workflow execution. Each error includes context like step_name, timestamp,
and original error for debugging purposes.

Per D-04: Clear error messages with failure context.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ErrorType(Enum):
    """Classification of error types for retry decisions."""

    TRANSIENT = "transient"
    """Errors that can be retried (network issues, timeouts)."""

    PERMANENT = "permanent"
    """Errors that should not be retried (bad input, auth failures)."""

    UNKNOWN = "unknown"
    """Unclassified errors - default to transient for safety."""


class WorkflowError(Exception):
    """Base exception for all workflow errors.

    All custom exceptions inherit from this to provide a common interface
    for catching workflow-specific errors.

    Attributes:
        message: Human-readable error message.
        step_name: Name of the step where the error occurred.
        timestamp: When the error was raised.
        original_error: The underlying exception that triggered this error.
    """

    def __init__(
        self,
        message: str,
        step_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.step_name = step_name
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.original_error = original_error

    def __str__(self) -> str:
        parts = [self.message]
        if self.step_name:
            parts.append(f"Step: {self.step_name}")
        parts.append(f"Time: {self.timestamp}")
        return " | ".join(parts)


class StepError(WorkflowError):
    """Raised when a specific step in the workflow fails.

    This exception includes the step name for precise error tracking.
    Use this for step-specific failures that need context.

    Attributes:
        step_name: The name of the step that failed.
        step_output: Any partial output from the step before failure.
    """

    def __init__(
        self,
        step_name: str,
        message: str,
        timestamp: Optional[str] = None,
        original_error: Optional[Exception] = None,
        step_output: Optional[dict[str, Any]] = None,
    ):
        super().__init__(
            message=message, step_name=step_name, timestamp=timestamp, original_error=original_error
        )
        self.step_output = step_output or {}

    def __str__(self) -> str:
        return f"Step '{self.step_name}' failed: {self.message}"


class RetryExhaustedError(WorkflowError):
    """Raised after all retry attempts have been exhausted.

    Per D-04: Raised with clear error message after 3 retries with
    exponential backoff fail.

    Attributes:
        attempts: Number of retry attempts made.
        last_error: The error from the final attempt.
        step_name: The step that exhausted retries.
    """

    def __init__(
        self,
        step_name: str,
        attempts: int,
        last_error: Exception,
        timestamp: Optional[str] = None,
    ):
        message = f"Step '{step_name}' failed after {attempts} attempts: {last_error}"
        super().__init__(
            message=message,
            step_name=step_name,
            timestamp=timestamp,
            original_error=last_error,
        )
        self.attempts = attempts
        self.last_error = last_error

    def __str__(self) -> str:
        return f"Retry exhausted for step '{self.step_name}' after {self.attempts} attempts: {self.last_error}"


class TransientError(WorkflowError):
    """Marker exception for errors that should be retried.

    Use this for errors like network timeouts, rate limits, or temporary
    service unavailability. The retry logic will automatically handle
    these with exponential backoff.

    Per D-04: Transient errors trigger retry with backoff.
    """

    def __init__(
        self,
        message: str,
        step_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message, step_name=step_name, timestamp=timestamp, original_error=original_error
        )


class PermanentError(WorkflowError):
    """Marker exception for errors that should not be retried.

    Use this for errors like invalid input, authentication failures,
    or configuration issues. These will skip retrying and move to
    error handling directly.

    Per D-04: Permanent errors skip retry, go straight to error handler.
    """

    def __init__(
        self,
        message: str,
        step_name: Optional[str] = None,
        timestamp: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ):
        super().__init__(
            message=message, step_name=step_name, timestamp=timestamp, original_error=original_error
        )


def classify_error(error: Exception) -> ErrorType:
    """Classify an error as transient or permanent for retry decisions.

    This helper examines an exception and determines whether it should
    be retried or treated as a permanent failure.

    Args:
        error: The exception to classify.

    Returns:
        ErrorType indicating whether to retry or not.

    Per D-04: Classification determines retry behavior.
    """
    # Already marked as transient/permanent
    if isinstance(error, TransientError):
        return ErrorType.TRANSIENT
    if isinstance(error, PermanentError):
        return ErrorType.PERMANENT

    # Check for common transient error patterns
    error_msg = str(error).lower()
    transient_patterns = [
        "timeout",
        "connection",
        "network",
        "rate limit",
        "temporary",
        "unavailable",
        "503",
        "429",
        "refused",
    ]

    for pattern in transient_patterns:
        if pattern in error_msg:
            return ErrorType.TRANSIENT

    # Check for common permanent error patterns
    permanent_patterns = [
        "authentication",
        "unauthorized",
        "forbidden",
        "invalid",
        "not found",
        "400",
        "401",
        "403",
        "404",
    ]

    for pattern in permanent_patterns:
        if pattern in error_msg:
            return ErrorType.PERMANENT

    # Default to transient - safe to retry
    return ErrorType.UNKNOWN
