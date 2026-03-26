"""SQLite-based checkpoint persistence for workflow state.

This module provides checkpoint persistence using SQLite, enabling
workflow state to survive interruptions and resume from where it left off.
"""

import sqlite3
from pathlib import Path
from typing import Any, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver


class SqliteSaver(BaseCheckpointSaver):
    """SQLite-based checkpoint saver for LangGraph state persistence.

    This implementation stores checkpoints in a SQLite database,
    enabling workflow state to persist across executions and support
    interruption recovery.

    Args:
        db_path: Path to SQLite database file. Use ":memory:" for in-memory.
    """

    def __init__(self, db_path: str = "checkpoints.db"):
        """Initialize the SQLite checkpointer.

        Args:
            db_path: Path to SQLite database file.
        """
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                thread_id TEXT NOT NULL,
                checkpoint_id TEXT NOT NULL,
                parent_checkpoint_id TEXT,
                channel_values TEXT,
                channel_metadata TEXT,
                pending_writes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (thread_id, checkpoint_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_thread_created 
            ON checkpoints(thread_id, created_at DESC)
        """)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(
                self.db_path, check_same_thread=False, isolation_level=None
            )
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def get(self, thread_id: str, checkpoint_id: Optional[str] = None) -> Optional[dict]:
        """Retrieve a checkpoint by ID or latest for a thread.

        Args:
            thread_id: The thread/flow identifier.
            checkpoint_id: Specific checkpoint ID (None for latest).

        Returns:
            Checkpoint dict or None if not found.
        """
        conn = self._get_conn()
        if checkpoint_id:
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE thread_id = ? AND checkpoint_id = ?",
                (thread_id, checkpoint_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE thread_id = ? ORDER BY created_at DESC LIMIT 1",
                (thread_id,),
            ).fetchone()

        if row:
            return {
                "checkpoint_id": row["checkpoint_id"],
                "parent_checkpoint_id": row["parent_checkpoint_id"],
                "channel_values": self._deserialize(row["channel_values"]),
                "channel_metadata": self._deserialize(row["channel_metadata"]),
            }
        return None

    def put(
        self,
        thread_id: str,
        checkpoint_id: str,
        channel_values: dict,
        parent_checkpoint_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Store a checkpoint.

        Args:
            thread_id: The thread/flow identifier.
            checkpoint_id: Unique checkpoint identifier.
            channel_values: The state data to store.
            parent_checkpoint_id: Parent checkpoint ID for versioning.
            metadata: Optional metadata for the checkpoint.
        """
        conn = self._get_conn()
        conn.execute(
            """INSERT OR REPLACE INTO checkpoints 
               (thread_id, checkpoint_id, parent_checkpoint_id, channel_values, channel_metadata)
               VALUES (?, ?, ?, ?, ?)""",
            (
                thread_id,
                checkpoint_id,
                parent_checkpoint_id,
                self._serialize(channel_values),
                self._serialize(metadata or {}),
            ),
        )
        conn.commit()

    def list(self, thread_id: str, limit: int = 10) -> list[dict]:
        """List checkpoints for a thread.

        Args:
            thread_id: The thread/flow identifier.
            limit: Maximum number of checkpoints to return.

        Returns:
            List of checkpoint dictionaries.
        """
        conn = self._get_conn()
        rows = conn.execute(
            """SELECT checkpoint_id, parent_checkpoint_id, created_at 
               FROM checkpoints WHERE thread_id = ? 
               ORDER BY created_at DESC LIMIT ?""",
            (thread_id, limit),
        ).fetchall()

        return [
            {
                "checkpoint_id": row["checkpoint_id"],
                "parent_checkpoint_id": row["parent_checkpoint_id"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def _serialize(self, data: Any) -> str:
        """Serialize data to JSON string."""
        import json

        return json.dumps(data)

    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to data."""
        import json

        return json.loads(data) if data else None


def create_checkpointer(db_path: str = "checkpoints.db") -> SqliteSaver:
    """Create a SQLite checkpointer for workflow state persistence.

    Args:
        db_path: Path to SQLite database file. Use ":memory:" for in-memory.

    Returns:
        SqliteSaver instance configured and ready to use.

    Example:
        >>> checkpointer = create_checkpointer("workflows.db")
        >>> engine = WorkflowEngine(workflow, checkpointer=checkpointer)
    """
    return SqliteSaver(db_path=db_path)
