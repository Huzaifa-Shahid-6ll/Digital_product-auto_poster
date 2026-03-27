# Phase 2: Product Generation - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate product ideas and auto-create digital deliverables based on niche input. User inputs a niche, receives 3+ product ideas with rationale, selects an idea, system generates a PDF product, validates quality, user reviews and approves.

</domain>

<decisions>
## Implementation Decisions

### Idea Generation
- **D-01:** Hybrid approach — templates provide structure + format, AI generates specific content
- Templates define: product category, format type, target audience
- AI generates: specific content, unique angle, differentiated features

### Product Formats
- **D-02:** PDF only for MVP — planners and worksheets (high demand on Etsy)
- Expand to other formats in later phases

### Quality Validation
- **D-03:** AI + Human review — AI does initial assessment, user does final approval
- AI checks: completeness, formatting consistency, content coherence
- User validates: quality, market fit, differentiation

### Approval Workflow
- **D-04:** Approve then create — user reviews ideas, selects one, system generates product
- **D-05:** Web dashboard for review and approval — visual interface for viewing ideas, providing feedback, approving

### Agent's Discretion
- Exact template structure and prompts
- Specific AI model and parameters
- File naming conventions

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — PG-01 (Generate product ideas), PG-02 (Auto-generate deliverables)
- `.planning/ROADMAP.md` — Phase 2 success criteria

### Prior Phase
- `.planning/phases/01-core-automation-engine/01-CONTEXT.md` — Phase 1 decisions (LangGraph, SQLite, CLI-first + dashboard)

### Project Context
- `.planning/PROJECT.md` — Core value: "set and forget" automation
- `.planning/STATE.md` — Current progress, accumulated decisions

[No external specs — requirements fully captured in decisions above]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- BaseWorkflow class from Phase 1 — can be extended for product generation workflows
- SqliteSaver from Phase 1 — stores workflow state and product metadata
- CLI commands structure — can add product generation commands

### Established Patterns
- LangGraph for workflow orchestration
- SQLite for persistence
- Human-in-the-loop verification (from Phase 1)

### Integration Points
- Product generation connects to workflow engine (LangGraph)
- Uses state management from Phase 1
- Dashboard for user interaction (from Phase 1 decision)

</code_context>

<specifics>
## Specific Ideas

- Templates provide category + format, AI generates specific content
- PDF format for high Etsy demand
- User approves ideas before product creation
- Dashboard for visual review

</specifics>

<deferred>
## Deferred Ideas

- Support for multiple formats (Canva, Notion, Excel) — future phase
- Iterative feedback workflow — if user wants more refinement later

</deferred>

---

*Phase: 02-product-generation*
*Context gathered: 2026-03-26*