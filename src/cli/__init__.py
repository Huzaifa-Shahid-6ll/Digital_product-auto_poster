"""CLI commands and entry point for Digital Product Auto-Poster.

This module provides the command-line interface for:
- Running workflows (python -m src.cli run)
- Checking execution status
- Listing executions
- Retrying failed workflows
- Viewing error logs

Per D-05: CLI first - primary interface for MVP.
"""

# Re-export the app and commands for CLI entry point
from src.cli.commands import app

# Define __main__ block so CLI can run with: python -m src.cli
if __name__ == "__main__":
    app()
