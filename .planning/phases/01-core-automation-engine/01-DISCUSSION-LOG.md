# Phase 1: Core Automation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 1-core-automation-engine
**Areas discussed:** Orchestration framework, Workflow definition format, State persistence, Error handling, User interface

---

## Orchestration Framework

| Option | Description | Selected |
|--------|-------------|----------|
| LangGraph (Recommended) | Production-standard graph-based agent orchestration, best for complex multi-step workflows with state management | ✓ |
| n8n | Visual workflow builder, easier for non-coders, but less flexible for custom AI agents | |
| Custom (DIY) | Full control, highest effort - build your own state machine and routing logic | |
| CrewAI | Open-source alternative to LangGraph, easier setup but less granular control | |

**User's choice:** LangGraph (Recommended)
**Notes:** Production-standard for complex AI workflows with state, retries, and tool calling

---

## Workflow Definition Format

| Option | Description | Selected |
|--------|-------------|----------|
| Code-based (Recommended) | Code-first (Python classes/functions), full flexibility but requires dev to modify | ✓ |
| YAML | Human-readable YAML files, easier to version control but less programmatic control | |
| Visual (JSON-based) | Visual drag-and-drop, easiest for non-coders but harder to version control | |
| Natural language | Natural language prompts, most accessible but least precise | |

**User's choice:** Code-based (Recommended)
**Notes:** Standard for LangGraph - workflows as Python code

---

## State Persistence

| Option | Description | Selected |
|--------|-------------|----------|
| SQLite (Recommended) | Simpler initially, easy to switch to PostgreSQL later | ✓ |
| PostgreSQL | Production standard, ACID compliant, required for production scale | |
| File-based (JSON) | Simple JSON files, easy to understand but no query capability | |
| PostgreSQL + pgvector | More complex but handles embeddings for AI memory | |

**User's choice:** SQLite (Recommended)
**Notes:** Simplest for MVP, PostgreSQL for production

---

## Error Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Retry with fallback (Recommended) | 3 retries with exponential backoff, then fail with clear error | ✓ |
| Fail fast | Attempt once, fail immediately on any error | |
| Human escalation | Pause workflow and notify user to decide | |
| Log and continue | Log error but continue workflow execution | |

**User's choice:** Retry with fallback (Recommended)
**Notes:** 3 retries with exponential backoff, then fail with clear error

---

## User Interface

| Option | Description | Selected |
|--------|-------------|----------|
| CLI first | Command-line interface, simplest to build, fastest to iterate | |
| Web dashboard | Web dashboard with visual workflow builder, most user-friendly but more work | |
| API-only | API-only, let other tools integrate - no built-in UI | |
| CLI + minimal UI | CLI for core, minimal dashboard for monitoring | |
| CLI + Web Dashboard | Both CLI for core functionality AND full web dashboard for workflow monitoring | ✓ |

**User's choice:** CLI + Web Dashboard
**Notes:** Build CLI for core, add minimal dashboard for workflow monitoring and visualization

---

## Agent's Discretion

- Exact retry backoff timing and thresholds
- Dashboard feature scope and complexity
- Logging format and verbosity levels

## Deferred Ideas

None mentioned during discussion