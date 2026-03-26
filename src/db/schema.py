"""Database initialization and schema management.

This module provides functions to initialize the SQLite database,
create tables, and provide session management.
"""

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.models import Base


# Default database path in project root
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "workflow.db"

# Database URL
DATABASE_URL: str = f"sqlite:///{DEFAULT_DB_PATH}"


def get_engine(database_url: Optional[str] = None):
    """Create and return a SQLAlchemy engine.

    Args:
        database_url: Optional database URL. Defaults to SQLite at data/workflow.db.

    Returns:
        SQLAlchemy Engine instance.
    """
    url = database_url or DATABASE_URL

    # Create engine with appropriate settings
    engine = create_engine(
        url, echo=False, connect_args={"check_same_thread": False} if "sqlite" in url else {}
    )

    return engine


def init_db(database_url: Optional[str] = None) -> None:
    """Initialize the database - create all tables.

    This function creates the database file if it doesn't exist,
    and creates all necessary tables based on the models.

    Args:
        database_url: Optional database URL. Defaults to SQLite at data/workflow.db.
    """
    # Ensure data directory exists first
    db_path = DEFAULT_DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = get_engine(database_url)

    # Create all tables
    Base.metadata.create_all(engine)


def get_session(database_url: Optional[str] = None) -> Session:
    """Create and return a new database session.

    Args:
        database_url: Optional database URL. Defaults to SQLite at data/workflow.db.

    Returns:
        SQLAlchemy Session instance.
    """
    engine = get_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


# Convenience: create tables on module import
if __name__ != "__main__":
    try:
        init_db()
    except Exception:
        pass  # Ignore errors during import - will be initialized properly later
