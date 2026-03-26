# Phase 1: Core Automation Engine - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the agent orchestration backbone that all downstream work connects to. This includes the workflow engine, state management, error handling, and user-facing interface (CLI + dashboard) for defining and executing the 10-step playbook automation.

</domain>

<decisions>
## Implementation Decisions

### Orchestration Framework
- **D-01:** Use LangGraph for agent orchestration — production-standard for complex multi-step AI workflows with built-in state management, retries, and tool calling

### Workflow Definition Format
- **D-02:** Use code-based workflow definitions (Python classes/functions) — standard LangGraph approach, provides full flexibility for complex playbook steps

### State Persistence
- **D-03:** Use SQLite for MVP — simple to start, easy to migrate to PostgreSQL later when scale requires

### Error Handling
- **D-04:** Retry with fallback strategy — 3 retries with exponential backoff, then fail with clear error message. Log failures for debugging

### User Interface
- **D-05:** CLI first + Web Dashboard — build CLI for core functionality, add minimal dashboard for workflow monitoring and visualization

### Agent's Discretion
- Exact retry backoff timing and thresholds
- Dashboard feature scope and complexity
- Logging format and verbosity levels

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Research Findings
- `.planning/research/STACK.md` — Technology stack recommendations (Next.js 15, FastAPI, LangGraph, PostgreSQL)
- `.planning/research/ARCHITECTURE.md` — Five-layer agentic architecture pattern
- `.planning/research/PITFALLS.md` — Critical pitfalls including premature full automation

### Requirements
- `.planning/REQUIREMENTS.md` — v1 requirements mapping (no specific requirements for Phase 1 - infrastructure phase)

### Project Context
- `.planning/PROJECT.md` — Core value: "set and forget" automation system
- `.planning/ROADMAP.md` — Phase 1 success criteria and goals

[No external specs — requirements fully captured in decisions above]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None yet — greenfield project for the automation engine

### Established Patterns
- Hybrid Python + TypeScript architecture from research (FastAPI + LangGraph for backend, Next.js 15 for frontend)
- Sequential pipeline with agentic routing pattern
- Human-in-the-loop verification for critical steps

### Integration Points
- LangGraph will orchestrate all downstream phases (research, product generation, listing, analytics)
- SQLite state storage will persist workflow execution history
- CLI and dashboard will provide user interaction layer

</code_context>

<specifics>
## Specific Ideas

- User wants "everything" from the playbook automated
- Focus on "set and forget" system that handles full workflow
- Build incrementally - core engine first, then connect each playbook step

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-core-automation-engine*
*Context gathered: 2026-03-26*