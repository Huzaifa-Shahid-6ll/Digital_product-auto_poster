# Phase 1: Core Automation Engine - Research

**Researched:** 2026-03-26
**Domain:** AI Agent Orchestration / Workflow Automation
**Confidence:** HIGH

## Summary

Phase 1 requires building the core automation engine that orchestrates all downstream work. Research confirms **LangGraph + SQLite + FastAPI + CLI** is the optimal stack for MVP. LangGraph provides production-grade state management, checkpointing, and retry policies. SQLite suffices for MVP with a clear migration path to PostgreSQL. Typer offers the best CLI experience for Python with type-hint-driven argument parsing.

**Primary recommendation:** Implement LangGraph workflow engine with SQLite persistence, expose via FastAPI, provide CLI interface with Typer, and add minimal dashboard for monitoring.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Implementation Decisions (Locked)
- **D-01:** Use LangGraph for agent orchestration — production-standard for complex multi-step AI workflows with built-in state management, retries, and tool calling
- **D-02:** Use code-based workflow definitions (Python classes/functions) — standard LangGraph approach
- **D-03:** Use SQLite for MVP — simple to start, easy to migrate to PostgreSQL later
- **D-04:** Retry with fallback strategy — 3 retries with exponential backoff, then fail with clear error message
- **D-05:** CLI first + Web Dashboard — build CLI for core functionality, add minimal dashboard for workflow monitoring

### the agent's Discretion
- Exact retry backoff timing and thresholds
- Dashboard feature scope and complexity
- Logging format and verbosity levels

### Deferred Ideas (OUT OF SCOPE)
None

</user_constraints>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **LangGraph** | 0.2.70+ | Multi-step AI workflow orchestration | Graph-based state management, checkpointing, retry policies, human-in-the-loop |
| **FastAPI** | 0.115+ | REST API backend | Async support, native LangChain integration, auto-generated docs |
| **SQLite** | 3.x | Local database for MVP | Zero-config, file-based, easy migration to PostgreSQL |
| **SQLAlchemy** | 2.0+ | ORM for database operations | Type-safe, declarative models, async support |
| **Typer** | 0.15+ | CLI framework | Type-hint driven, auto-completion, built on Click |
| **Rich** | 13.x | Terminal output formatting | Tables, progress bars, beautiful CLI output |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Pydantic** | 2.7+ | Data validation | Request/response models, state schemas |
| **Uvicorn** | 0.30+ | ASGI server | Run FastAPI app |
| **Tenacity** | — | Retry logic | Alternative to LangGraph RetryPolicy for custom retry needs |
| **Alembic** | — | Database migrations | Schema evolution as project grows |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangGraph | CrewAI | CrewAI is easier but less flexible for complex orchestration |
| SQLite | PostgreSQL | PostgreSQL is overkill for MVP, easier to start SQLite and migrate |
| Typer | Click | Click gives more control but more boilerplate; Typer is more Pythonic |
| Rich | Colorama | Rich is higher-level and easier; Colorama requires more manual work |

**Installation:**
```bash
# Core dependencies
pip install langgraph>=0.2.70 fastapi>=0.115 uvicorn[standard]>=0.30
pip install pydantic>=2.7 pydantic-settings>=2.1

# Database
pip install sqlalchemy>=2.0 aiosqlite

# CLI
pip install typer rich

# Utilities
pip install python-dotenv httpx
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── core/
│   ├── engine.py          # LangGraph workflow engine
│   ├── state.py           # State definitions and schemas
│   └── checkpoint.py      # SQLite checkpointer setup
├── workflows/
│   ├── base.py            # Base workflow class
│   └── playbook.py        # 10-step playbook implementation
├── api/
│   ├── main.py            # FastAPI application
│   ├── routes.py          # API endpoints
│   └── models.py          # Pydantic request/response models
├── cli/
│   ├── __init__.py        # CLI entry point
│   ├── commands.py        # CLI command definitions
│   └── output.py          # Rich formatting utilities
├── db/
│   ├── models.py           # SQLAlchemy models
│   ├── schema.py          # Database schema
│   └── migrations/        # Alembic migrations
└── utils/
    ├── logging.py         # Logging configuration
    └── errors.py          # Custom error classes
```

### Pattern 1: LangGraph State Management

**What:** Define state as TypedDict with optional reducer annotations for merging updates.

**When to use:** Every LangGraph workflow needs explicit state schema.

**Example:**
```python
# Source: LangGraph Documentation
from typing import Annotated, TypedDict
from langgraph.graph import add_messages

class WorkflowState(TypedDict):
    """State flows through every node in the graph."""
    messages: Annotated[list[BaseMessage], add_messages]  # Appends, doesn't replace
    current_step: str
    step_results: dict
    errors: list[str]
    metadata: dict
```

**Key insight:** Use `Annotated[..., add_messages]` reducer for message history. Without it, LangGraph replaces the entire field instead of appending.

### Pattern 2: Checkpoint Persistence

**What:** Save workflow state to SQLite after each node execution, enabling resume from interruption.

**When to use:** Production workflows that need persistence and recovery.

**Example:**
```python
# Source: LangGraph Documentation
from langgraph.checkpoint.sqlite import SqliteSaver

# For development (in-memory)
memory = SqliteSaver.from_conn_string(":memory:")

# For production (file-based)
checkpointer = SqliteSaver.from_conn_string("sqlite:///workflows.db")

# Compile graph with checkpointing
app = workflow.compile(checkpointer=checkpointer)

# Execute with thread ID for persistence
config = {"configurable": {"thread_id": "playbook-run-123"}}
result = app.invoke(initial_state, config=config)
```

### Pattern 3: Retry Policies

**What:** Configure automatic retries with exponential backoff on specific nodes.

**When to use:** Nodes that call external APIs or perform network operations.

**Example:**
```python
# Source: LangGraph RetryPolicy Documentation
from langgraph.types import RetryPolicy

retry_policy = RetryPolicy(
    initial_interval=1.0,    # Seconds before first retry
    backoff_factor=2.0,       # Multiply interval each retry
    max_interval=30.0,        # Cap at 30 seconds
    max_attempts=3,           # Maximum 3 retries
    jitter=True,              # Add randomness to prevent thundering herd
)

# Attach to node
graph.add_node("call_api", external_api_node, retry_policy=retry_policy)
```

### Pattern 4: Conditional Edge Fallbacks

**What:** Route to error handler node when a node fails, enabling graceful degradation.

**When to use:** Workflows that need fallback strategies instead of hard failures.

**Example:**
```python
# Source: LangGraph Advanced Patterns
def should_continue(state: WorkflowState) -> str:
    """Route based on execution status."""
    if state.get("errors"):
        return "error_handler"
    if state.get("is_complete"):
        return END
    return "next_step"

workflow.add_conditional_edges(
    "process_step",
    should_continue,
    {
        "error_handler": "error_handler_node",
        "next_step": "next_step",
        END: END,
    }
)
```

### Pattern 5: CLI with Typer + Rich

**What:** Type-hint driven CLI with beautiful terminal output.

**When to use:** Building user-friendly command-line tools.

**Example:**
```python
# Source: Typer Documentation
import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer()
console = Console()

@app.command()
def list_workflows():
    """List all workflow executions."""
    workflows = get_workflows()
    table = Table(title="Workflow Executions")
    table.add_column("ID")
    table.add_column("Status")
    table.add_column("Created")
    
    for w in workflows:
        table.add_row(w.id, w.status, w.created_at)
    
    console.print(table)

if __name__ == "__main__":
    app()
```

### Pattern 6: FastAPI + WebSocket Dashboard

**What:** Real-time workflow monitoring via WebSocket connections.

**When to use:** Dashboard needs live updates as workflow progresses.

**Example:**
```python
# Source: FastAPI WebSocket Documentation
from fastapi import WebSocket
from starlette.websockets import WebSocketState

@app.websocket("/ws/{execution_id}")
async def websocket_endpoint(websocket: WebSocket, execution_id: str):
    await websocket.accept()
    try:
        while True:
            # Get current workflow state
            state = await get_workflow_state(execution_id)
            await websocket.send_json(state)
            await asyncio.sleep(1)  # Poll every second
    except Exception:
        await websocket.close()
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| **Agent orchestration** | Custom workflow engine | LangGraph | Built-in state management, checkpointing, retries, human-in-the-loop |
| **CLI argument parsing** | argparse or manual parsing | Typer | Type-hint driven, auto-completion, less boilerplate |
| **Terminal formatting** | Print statements | Rich | Tables, progress bars, colors, beautiful output out of the box |
| **Database migrations** | Manual schema changes | Alembic | Version-controlled schema, easy rollback, team collaboration |
| **Retry logic** | Custom try/except loops | LangGraph RetryPolicy | Built-in exponential backoff, jitter, configurable per-node |

**Key insight:** The AI agent ecosystem has converged on LangGraph as the orchestration standard. Building custom orchestration is reinventing the wheel and missing built-in features like checkpointing and human-in-the-loop hooks.

---

## Runtime State Inventory

> This section is N/A for Phase 1 — greenfield infrastructure project with no runtime state to migrate.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — new SQLite database | N/A |
| Live service config | None — no external services yet | N/A |
| OS-registered state | None — no scheduled tasks | N/A |
| Secrets/env vars | None defined yet | Define in implementation |
| Build artifacts | None yet | N/A |

---

## Common Pitfalls

### Pitfall 1: State Schema Too Broad
**What goes wrong:** Putting everything in state causes serialization issues and slow checkpointing.
**Why it happens:** Tendency to pass all data through state rather than using external storage.
**How to avoid:** Keep state lightweight. Store references (IDs, file paths) not large data. Use external databases for heavy data.
**Warning signs:** Checkpoints taking >1 second, state size >1MB.

### Pitfall 2: Missing Error Classification
**What goes wrong:** Treating all errors the same — retrying everything or failing on everything.
**Why it happens:** Not distinguishing transient errors from permanent failures.
**How to avoid:** Classify errors: transient (retry), LLM-recoverable (reformulate), human-required (escalate).
**Warning signs:** Infinite retry loops, silent failures, user confusion.

### Pitfall 3: No Recursion Limit
**What goes wrong:** Graph runs forever in infinite loops, consuming resources.
**Why it happens:** Missing `recursion_limit` in graph configuration.
**How to avoid:** Set reasonable limit (default 1000 in LangGraph 1.0.6+), monitor `remaining_steps`.
**Warning signs:** Graph never terminates, CPU at 100%, memory growing.

### Pitfall 4: Checkpointing Every Change
**What goes wrong:** Checkpointing after every node causes performance issues.
**Why it happens:** Not understanding LangGraph's checkpoint timing.
**How to avoid:** LangGraph checkpoints after each super-step automatically. Don't add manual checkpoints.
**Warning signs:** Slow execution, database size growing rapidly.

### Pitfall 5: CLI as Afterthought
**What goes wrong:** Building API-first, adding CLI later with poor UX.
**Why it happens:** Not designing CLI as first-class interface.
**How to avoid:** Design CLI alongside API. Use Typer's type hints to generate both.
**Warning signs:** Duplicate validation logic, inconsistent behavior between CLI and API.

---

## Code Examples

### LangGraph Basic Workflow
```python
# Source: LangGraph Getting Started
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class AgentState(TypedDict):
    messages: list[str]
    next_action: str

def step_1(state: AgentState) -> AgentState:
    return {"next_action": "step_2"}

def step_2(state: AgentState) -> AgentState:
    return {"next_action": END}

# Build graph
workflow = StateGraph(AgentState)
workflow.add_node("step_1", step_1)
workflow.add_node("step_2", step_2)
workflow.add_edge(START, "step_1")
workflow.add_edge("step_1", "step_2")
workflow.add_edge("step_2", END)

# Compile and run
app = workflow.compile()
result = app.invoke({"messages": [], "next_action": ""})
```

### SQLite Schema for Workflow State
```python
# Source: SQLAlchemy Documentation
from sqlalchemy import Column, Integer, String, DateTime, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

class ExecutionStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class WorkflowExecution(Base):
    __tablename__ = "workflow_executions"
    
    id = Column(String, primary_key=True)  # thread_id
    workflow_name = Column(String, nullable=False)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    current_step = Column(String)
    state_data = Column(JSON)  # Serialized LangGraph state
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    execution_id = Column(String, nullable=False)
    step_name = Column(String, nullable=False)
    status = Column(String)  # started, completed, failed
    input_data = Column(JSON)
    output_data = Column(JSON)
    error = Column(String, nullable=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime, nullable=True)
```

### Typer CLI with Subcommands
```python
# Source: Typer Documentation
import typer
from typing import Optional

app = typer.Typer()

@app.command()
def start(
    workflow: str = typer.Argument(..., help="Workflow to run"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Execution name"),
):
    """Start a workflow execution."""
    execute_workflow(workflow, name)

@app.command()
def status(execution_id: str = typer.Argument(...)):
    """Check workflow execution status."""
    result = get_status(execution_id)
    print(f"Status: {result.status}")

@app.command()
def list():
    """List all workflow executions."""
    for ex in list_executions():
        print(f"{ex.id}: {ex.status}")

if __name__ == "__main__":
    app()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Linear chains (LangChain) | Graph-based workflows (LangGraph) | 2024 | Enables cycles, conditional routing, human-in-the-loop |
| In-memory state | Checkpoint persistence | LangGraph 0.2+ | Enables resume after crash, state inspection |
| Manual retry loops | Built-in RetryPolicy | LangGraph 0.2.24+ | Simpler code, exponential backoff built-in |
| Argparse CLIs | Typer with type hints | 2023+ | Less boilerplate, auto-completion, better errors |

**Deprecated/outdated:**
- **LangChain Chains:** Replaced by LangGraph for complex workflows
- **argparse for CLIs:** Outpaced by Typer's type-hint approach
- **In-memory checkpointer:** Not suitable for production; use SQLite or PostgreSQL

---

## Open Questions

1. **Dashboard complexity for MVP**
   - What we know: User wants CLI-first with minimal dashboard
   - What's unclear: How much monitoring is "minimal"? Status + logs? Or basic metrics?
   - Recommendation: Start with status endpoint + execution history. Add charts only if phase 5 (Analytics) warrants it.

2. **Workflow definition format**
   - What we know: Code-based definitions (D-02)
   - What's unclear: Should workflows be defined in Python files, YAML, or database?
   - Recommendation: Python classes for MVP. Add YAML registry later if users want to define workflows without code.

3. **Error handling granularity**
   - What we know: 3 retries with exponential backoff (D-04)
   - What's unclear: Should retry policy vary by node type (LLM vs API vs file)?
   - Recommendation: Default to 3 retries, allow per-node override for API calls.

---

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified)

This phase has no external service dependencies — all components run locally:
- LangGraph: Python package
- SQLite: Built into Python
- FastAPI: Python package
- CLI: Local execution

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| N/A | Phase 1 has no v1 requirements — infrastructure only | N/A | N/A | N/A |

### Wave 0 Gaps
- [ ] `tests/test_engine.py` — covers workflow execution
- [ ] `tests/test_state.py` — covers state management
- [ ] `tests/test_cli.py` — covers CLI commands
- [ ] `tests/conftest.py` — shared fixtures
- [ ] Framework install: `pip install pytest` — if not present

---

## Sources

### Primary (HIGH confidence)
- LangGraph Documentation — State management, checkpointing, retry policies
- LangGraph Checkpoint SQLite — SqliteSaver implementation
- Typer Documentation — CLI with type hints
- FastAPI WebSocket — Real-time dashboard patterns
- LangGraph RetryPolicy — Official RetryPolicy class definition

### Secondary (MEDIUM confidence)
- "LangGraph Patterns & Best Practices Guide (2025)" — Production patterns
- "Building Multi-Agent Systems with LangGraph" — Multi-agent patterns
- "FastAPI SQLite Database Integration" — SQLAlchemy integration
- "Python CLI Tools with Click and Typer" — CLI best practices

### Tertiary (LOW confidence)
- Community tutorials on LangGraph error handling — Need verification
- Various dashboard implementation guides — Patterns vary widely

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — LangGraph, FastAPI, Typer are well-documented and production-validated
- Architecture: HIGH — Patterns are canonical LangGraph patterns
- Pitfalls: HIGH — Identified from production experience documented in community
- Database schema: MEDIUM — SQLAlchemy patterns well-established, specific schema needs validation

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (30 days for stable technology)

---

*Research complete. Ready for planning.*