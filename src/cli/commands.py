"""CLI commands for workflow execution and management.

This module provides the command-line interface for running workflows,
checking status, listing executions, retrying failed workflows, and
viewing error logs.

Per D-05: CLI-first approach for workflow management.
"""

import logging
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.core.engine import create_engine, WorkflowEngine
from src.core.state import WorkflowState
from src.workflows.playbook import PlaybookWorkflow
from src.utils.errors import RetryExhaustedError, StepError

app = typer.Typer(help="Digital Product Auto-Poster CLI")
console = Console()
logger = logging.getLogger(__name__)


@app.command()
def run(
    workflow_name: str = typer.Argument(default="playbook", help="Workflow to run"),
    niche: Optional[str] = typer.Option(None, "--niche", "-n", help="Niche keywords"),
    thread_id: Optional[str] = typer.Option(None, "--thread-id", "-t", help="Thread ID for resume"),
) -> None:
    """Execute a workflow by name.

    Runs the specified workflow with optional niche input.
    Shows progress with spinner and displays errors in red if they occur.
    """
    console.print(f"[bold blue]Starting workflow:[/bold blue] {workflow_name}")

    # Select workflow based on name
    if workflow_name == "playbook" or workflow_name == "validation":
        workflow = PlaybookWorkflow()
    else:
        console.print(f"[red]Unknown workflow: {workflow_name}[/red]")
        raise typer.Exit(1)

    # Add metadata if niche provided
    initial_state = None
    if niche:
        initial_state = {
            "messages": [],
            "current_step": "pick_niche",
            "step_results": {},
            "errors": [],
            "metadata": {"niche_keywords": niche.split(",")},
        }

    # Create engine and run
    engine = create_engine(workflow)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing workflow...", total=None)

        try:
            result = engine.run(initial_state=initial_state, thread_id=thread_id)
            progress.update(task, completed=True)

            # Display results
            console.print("\n[bold green]Workflow completed![/bold green]")

            # Show step results
            step_results = result.get("step_results", {})
            if step_results:
                table = Table(title="Step Results")
                table.add_column("Step", style="cyan")
                table.add_column("Status", style="green")
                table.add_column("Message", style="white")

                for step_name, step_data in step_results.items():
                    status = step_data.get("status", "unknown")
                    message = step_data.get("message", step_data.get("verdict", ""))
                    table.add_row(step_name, status, str(message))

                console.print(table)

            # Show errors if any
            errors = result.get("errors", [])
            if errors:
                console.print("\n[bold red]Errors encountered:[/bold red]")
                for error in errors:
                    console.print(f"  [red]• {error}[/red]")

        except RetryExhaustedError as e:
            progress.stop()
            console.print(f"\n[bold red]Retry exhausted:[/bold red] {e}")
            console.print(f"[red]Step: {e.step_name}, Attempts: {e.attempts}[/red]")
            raise typer.Exit(1)
        except StepError as e:
            progress.stop()
            console.print(f"\n[bold red]Step failed:[/bold red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            progress.stop()
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            logger.exception("Workflow execution failed")
            raise typer.Exit(1)


@app.command()
def status(
    execution_id: str = typer.Argument(..., help="Execution/thread ID to check"),
) -> None:
    """Show execution status including errors.

    Retrieves the current state of a workflow execution and displays
    the current step, all completed steps, and any errors encountered.
    """
    console.print(f"[bold]Checking status for:[/bold] {execution_id}")

    # For now, use in-memory check
    # In production, would query DB for execution state
    console.print("[yellow]Status tracking not yet persisted to database[/yellow]")
    console.print("Use 'list' to see available executions from checkpoint storage.")


@app.command()
def list_executions(
    limit: int = typer.Option(10, "--limit", "-l", help="Number of executions to show"),
) -> None:
    """List all workflow executions with status.

    Shows a table of recent workflow executions including their
    thread IDs, current step, and status (running/completed/failed).
    """
    console.print(f"[bold]Recent Workflow Executions (last {limit}):[/bold]")

    # Create a workflow to get engine
    workflow = PlaybookWorkflow()
    engine = create_engine(workflow)

    try:
        # Try to list executions
        # This uses checkpoint storage
        executions = engine.list_executions(limit=limit)

        if not executions:
            console.print("[yellow]No executions found[/yellow]")
            return

        table = Table()
        table.add_column("Thread ID", style="cyan")
        table.add_column("Checkpoint ID", style="green")
        table.add_column("Metadata", style="white")

        for exec in executions:
            thread_id = exec.get("configurable", {}).get("thread_id", "unknown")
            checkpoint_id = exec.get("checkpoint_id", "N/A")
            metadata = str(exec.get("metadata", {}))[:50]
            table.add_row(thread_id, checkpoint_id, metadata)

        console.print(table)

    except Exception as e:
        console.print(f"[yellow]Could not list executions: {e}[/yellow]")
        console.print("Check that checkpoint database is initialized.")


@app.command()
def retry(
    execution_id: str = typer.Argument(..., help="Execution ID to retry"),
    from_step: Optional[str] = typer.Option(None, "--from", help="Step to restart from"),
) -> None:
    """Retry a failed workflow from the last step.

    Resumes execution from the checkpoint, either from where it failed
    or from an optional specified step. Useful for recovering from
    transient errors.
    """
    console.print(f"[bold]Retrying execution:[/bold] {execution_id}")

    workflow = PlaybookWorkflow()
    engine = create_engine(workflow)

    try:
        # Try to resume from checkpoint
        result = engine.resume(execution_id)

        console.print("[bold green]Retry completed![/bold green]")

        # Show errors from retry
        errors = result.get("errors", [])
        if errors:
            console.print("\n[bold red]Errors during retry:[/bold red]")
            for error in errors:
                console.print(f"  [red]• {error}[/red]")

    except ValueError as e:
        console.print(f"[red]Could not find execution: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Retry failed: {e}[/red]")
        logger.exception("Retry failed")
        raise typer.Exit(1)


@app.command()
def logs(
    execution_id: str = typer.Argument(..., help="Execution ID to show logs for"),
) -> None:
    """Show error logs for a failed execution.

    Displays all error messages that occurred during workflow execution,
    including step context and retry information.
    """
    console.print(f"[bold]Error logs for:[/bold] {execution_id}")

    workflow = PlaybookWorkflow()
    engine = create_engine(workflow)

    try:
        state = engine.get_state(execution_id)

        if state is None:
            console.print(f"[red]No execution found for ID: {execution_id}[/red]")
            raise typer.Exit(1)

        errors = state.get("errors", [])

        if not errors:
            console.print("[yellow]No errors found for this execution[/yellow]")
            return

        console.print(f"\n[bold red]Errors ({len(errors)}):[/bold red]")
        for i, error in enumerate(errors, 1):
            console.print(f"  {i}. {error}")

        # Also show failed steps
        step_results = state.get("step_results", {})
        failed_steps = [
            (name, data.get("error"))
            for name, data in step_results.items()
            if data.get("status") == "failed"
        ]

        if failed_steps:
            console.print(f"\n[bold]Failed Steps:[/bold]")
            for step_name, error in failed_steps:
                console.print(f"  • {step_name}: {error}")

    except Exception as e:
        console.print(f"[red]Could not retrieve logs: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
