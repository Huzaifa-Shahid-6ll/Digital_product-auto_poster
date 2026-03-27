# Phase 4: Research & Validation - Research

**Researched:** 2026-03-27
**Domain:** AI-powered niche research with market demand verification
**Confidence:** HIGH

## Summary

Phase 4 implements AI-powered niche research with human verification checkpoints. The core challenge is combining AI-generated niche recommendations with real market data verification (demand, competition) while ensuring the AI cites sources and avoids hallucinations.

**Primary recommendation:** Use a hybrid approach - AI generates niche recommendations using GPT-4o with structured output, verify demand via Google Trends API (pytrends) and Etsy marketplace data, implement human-in-the-loop verification using LangGraph's interrupt pattern, and use retrieval-augmented generation (RAG) patterns with citations to ensure factual grounding.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Hybrid Python + TypeScript architecture** - Next.js 15 + FastAPI + LangGraph
- **Sequential pipeline with agentic routing pattern** - Per Phase 1 research
- **Human-in-the-loop verification required** - For niche research, user must confirm before product generation
- **TypedDict for LangGraph state** - Not Pydantic, per Phase 1
- **SQLite with SQLAlchemy ORM** - For MVP persistence
- **BaseWorkflow ABC with StepDefinition** - For workflow contract
- **3 retries with exponential backoff** - Per D-04 (initial_interval=1.0, backoff_factor=2.0, max_attempts=3)

### the agent's Discretion
- Exact market data sources (Google Trends vs alternatives)
- Specific verification metrics (demand score algorithm)
- Citation format and display

### Deferred Ideas (OUT OF SCOPE)
- Real-time competitor pricing analysis — future phase
- Multi-marketplace research (Etsy + Gumroad + Creative Market) — focus on Etsy first

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| NR-01 | AI-powered market analysis to find profitable niches | LLMs with structured output + market data APIs |
| NR-02 | Verify niche demand with real market data | Google Trends API + Etsy marketplace data |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | ^1.12.0 | AI content generation with structured output | Industry standard, GPT-4o for analysis |
| pytrends | ^4.9.2 | Google Trends data for demand verification | Free, comprehensive search interest data |
| langgraph | ^0.2.x | Human-in-the-loop workflow with interrupts | Already in project stack |
| pydantic | ^2.5.0 | Structured output validation | LangGraph ecosystem alignment |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| etsy-api-v3 | latest | Etsy marketplace data (listings, search) | Competition analysis |
| requests | ^2.31.0 | HTTP calls for APIs | pytrends and Etsy API calls |
| aiohttp | ^3.9.0 | Async HTTP for parallel API calls | Faster data gathering |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytrends | SerpApi (paid) | pytrends is free but rate-limited; SerpApi more reliable |
| OpenAI | Anthropic Claude | Both work, Claude slightly better at reasoning |
| Google Trends | Etsy API alone | Google Trends provides broader search interest data |

**Installation:**
```bash
pip install openai pytrends requests aiohttp pydantic langgraph
```

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── niche_research/
│   ├── __init__.py
│   ├── analyzer.py       # AI-powered niche analysis
│   ├── verifier.py      # Demand verification with market data
│   ├── schemas.py       # Pydantic models for niche data
│   └── sources.py       # Citation tracking and formatting
├── api/
│   └── research_routes.py  # FastAPI endpoints
└── workflows/
    └── research.py      # LangGraph workflow definition
```

### Pattern 1: AI Market Analysis with Structured Output
**What:** AI generates niche recommendations with structured data
**When to use:** Initial niche suggestion phase
**Example:**
```python
from pydantic import BaseModel
from openai import AsyncOpenAI

class NicheRecommendation(BaseModel):
    niche: str
    target_audience: str
    demand_estimate: str  # high/medium/low
    competition_level: str  # high/medium/low
    recommended_formats: list[str]
    rationale: str
    sources: list[str]  # URLs or data sources cited

async def analyze_niche(client: AsyncOpenAI, keywords: list[str]) -> list[NicheRecommendation]:
    response = await client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "Analyze niches and recommend profitable options..."},
            {"role": "user", "content": f"Keywords: {keywords}"}
        ]
    )
    # Parse and validate with Pydantic
    data = json.loads(response.choices[0].message.content)
    return [NicheRecommendation(**rec) for rec in data["recommendations"]]
```

### Pattern 2: Demand Verification with Google Trends
**What:** Fetch real search interest data to verify AI recommendations
**When to use:** After AI generates recommendations, before presenting to user
**Example:**
```python
from pytrends.request import TrendReq
import asyncio

async def verify_demand(niches: list[str]) -> dict:
    """Verify niche demand using Google Trends."""
    pytrends = TrendReq(hl='en-US', tz=360)
    results = {}
    
    for niche in niches:
        pytrends.build_payload(kw_list=[niche], timeframe='today 12-m')
        interest = pytrends.interest_over_time()
        results[niche] = {
            "average_interest": interest.mean() if not interest.empty else 0,
            "trend_direction": "up" if interest.iloc[-1] > interest.iloc[0] else "down",
            "peak_month": interest.idxmax() if not interest.empty else None
        }
    
    return results
```

### Pattern 3: Human-in-the-Loop with LangGraph Interrupt
**What:** Pause workflow at verification checkpoint, wait for human approval
**When to use:** After niche recommendations generated, before proceeding to product generation
**Example:**
```python
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

def create_research_workflow():
    """Create niche research workflow with human verification checkpoint."""
    
    def analyze_step(state: WorkflowState) -> WorkflowState:
        # AI generates niche recommendations
        recommendations = analyze_niche(state["keywords"])
        state["recommendations"] = recommendations
        return state
    
    def verify_step(state: WorkflowState) -> WorkflowState:
        # Verify with market data
        verified = verify_with_trends(state["recommendations"])
        state["verified_niches"] = verified
        return state
    
    def checkpoint_step(state: WorkflowState) -> WorkflowState:
        # INTERRUPT: Wait for human verification
        # This pauses execution and returns control to user
        user_decision = interrupt({
            "message": "Review these niche recommendations",
            "niches": state["verified_niches"],
            "options": ["proceed", "retry", "cancel"]
        })
        state["user_decision"] = user_decision
        return state
    
    # Build graph
    graph = StateGraph(WorkflowState)
    graph.add_node("analyze", analyze_step)
    graph.add_node("verify", verify_step)
    graph.add_node("checkpoint", checkpoint_step)
    
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "verify")
    graph.add_edge("verify", "checkpoint")
    graph.add_edge("checkpoint", END)
    
    return graph.compile(checkpointer=checkpointer)
```

### Pattern 4: Source Citation for Hallucination Prevention
**What:** Include source URLs/data in AI output to verify claims
**When to use:** Ensuring market data claims are grounded in real data
**Example:**
```python
async def generate_with_citations(client: AsyncOpenAI, query: str, sources: list[str]) -> str:
    """Generate content with explicit source citations."""
    
    # Include sources in system prompt
    system_prompt = f"""You are a market research analyst. 
    When making claims about market demand or trends, cite your sources.
    Available data sources:
    {chr(10).join([f'- {s}' for s in sources])}
    
    Format citations as: [Source: name](url)"""
    
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]
    )
    return response.choices[0].message.content
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Search interest data | Custom web scraping | pytrends library | Free, reliable, rate-limited but sufficient for MVP |
| Structured AI output | Raw text parsing | Pydantic models | Type safety, validation, cleaner code |
| Human verification | Custom state management | LangGraph interrupt | Native support, checkpoint persistence |
| Market competition | Manual Etsy search | Etsy API v3 | Programmatic, scalable, real data |

**Key insight:** The project's existing LangGraph infrastructure already supports human-in-the-loop patterns. Reuse the BaseWorkflow ABC and StepDefinition pattern rather than building custom workflow logic.

---

## Common Pitfalls

### Pitfall 1: AI-Generated Demand Claims Without Verification
**What goes wrong:** AI claims a niche has "high demand" with no real data backing
**Why it happens:** No verification step, AI confuses plausibility with reality
**How to avoid:**
- Always run Google Trends verification after AI generates recommendations
- Score each claim against actual search data
- Flag discrepancies between AI claims and verified data
**Warning signs:** "This niche is growing fast" with no source, confidence mismatched with data

### Pitfall 2: Hallucinated Market Statistics
**What goes wrong:** AI cites fake Etsy stats, fake competitor numbers
**Why it happens:** AI generates plausible-sounding but fabricated numbers
**How to avoid:**
- Use retrieval-augmented generation: fetch real data first, then have AI summarize
- Never let AI cite its own training data as current market info
- Verify any specific numbers (e.g., "2,340 listings") against actual API
**Warning signs:** Very specific numbers without source URLs, round numbers without decimals

### Pitfall 3: No Human Checkpoint Before Product Generation
**What goes wrong:** System auto-proceeds to product generation on bad niche
**Why it happens:** Missing verification checkpoint, fully automated flow
**How to avoid:**
- Use LangGraph interrupt at verification step
- Require explicit user confirmation before proceeding
- Store user decision in workflow state for audit trail
**Warning signs:** No pause in workflow, user sees product before approving niche

### Pitfall 4: Rate Limit Errors on Market APIs
**What goes wrong:** Google Trends or Etsy API calls fail due to rate limits
**Why it happens:** No throttling, too many parallel requests
**How to avoid:**
- Implement request throttling (1 request per second for pytrends)
- Cache results for short periods
- Add fallback to cached data if API unavailable
**Warning signs:** "Too many requests" errors, partial data returned

---

## Code Examples

### Niche Recommendation Schema
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NicheRecommendation(BaseModel):
    """Structured output for niche recommendations."""
    niche: str
    target_audience: str
    demand_score: int  # 1-10 scale
    competition_level: str  # low/medium/high
    recommended_formats: list[str]
    rationale: str
    
    # Source citation fields (hallucination prevention)
    google_trends_data: Optional[dict] = None
    etsy_listing_count: Optional[int] = None
    source_urls: list[str] = []

class VerifiedNiche(BaseModel):
    """Niche with verified market data."""
    recommendation: NicheRecommendation
    verified_demand: bool
    verification_data: dict
    user_approved: bool = False
```

### Workflow State (TypedDict per project patterns)
```python
from typing import TypedDict

class ResearchState(TypedDict):
    """State for niche research workflow."""
    keywords: list[str]
    recommendations: list[dict]  # Raw AI recommendations
    verified_niches: list[VerifiedNiche]
    user_decision: Optional[str]  # proceed/retry/cancel
    current_step: str
    errors: list[str]
    step_results: dict
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual keyword research | AI + market data verification | 2023+ LLMs | Faster, more comprehensive |
| Single-source data | Multi-source verification (Trends + Etsy) | 2024 | Better accuracy, cross-verification |
| No source citation | RAG with citations | 2025 | Reduced hallucinations |
| Fully automated | Human-in-the-loop checkpoints | 2024 LangGraph | User control, quality gate |

**Deprecated/outdated:**
- Single LLM call without verification: Now requires data grounding
- Static keyword lists: Now replaced with AI-generated + validated suggestions

---

## Open Questions

1. **Google Trends rate limiting**
   - What we know: pytrends has unofficial rate limits
   - What's unclear: Exact limits, best throttling strategy
   - Recommendation: Start with 1 req/sec, implement caching

2. **Etsy API access for MVP**
   - What we know: Etsy API v3 exists but requires app registration
   - What's unclear: How quickly new apps get API access
   - Recommendation: Start with Google Trends, add Etsy API in Phase 5 if needed

3. **Demand score algorithm**
   - What we know: Search interest + listing count + competition = demand
   - What's unclear: Exact weighting formula
   - Recommendation: Simple formula first, refine based on user feedback

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest.ini (root) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| NR-01 | Generate 3+ niche recommendations with demand estimates | unit | `pytest tests/test_niche_research/test_analyzer.py -x` | ❌ Wave 0 |
| NR-01 | Structured output validation | unit | `pytest tests/test_niche_research/test_schemas.py -x` | ❌ Wave 0 |
| NR-02 | Google Trends verification returns data | integration | `pytest tests/test_niche_research/test_verifier.py -x` | ❌ Wave 0 |
| NR-02 | Human checkpoint pauses workflow | integration | `pytest tests/test_niche_research/test_workflow.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_niche_research/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_niche_research/` — new test directory
- [ ] `tests/test_niche_research/test_analyzer.py` — covers NR-01
- [ ] `tests/test_niche_research/test_verifier.py` — covers NR-02
- [ ] `tests/test_niche_research/test_workflow.py` — covers checkpoint behavior
- [ ] `tests/conftest.py` — shared fixtures (may already exist)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Core runtime | ✓ | 3.11+ | — |
| OpenAI API | AI analysis | ✓ | Latest | Anthropic Claude |
| pytrends | Google Trends | ✓ (via pip) | 4.9.2 | Skip, use cached data |
| LangGraph | Workflow | ✓ (in project) | 0.2.x | — |
| Etsy API v3 | Competition data | ✗ | — | Skip for MVP |

**Missing dependencies with no fallback:**
- Etsy API v3 — requires app registration, skip for MVP

**Missing dependencies with fallback:**
- None — all core dependencies available

---

## Sources

### Primary (HIGH confidence)
- OpenAI API docs - Structured output with Pydantic
- pytrends PyPI - Google Trends API usage
- LangGraph docs - Human-in-the-loop patterns
- Etsy API v3 docs - Marketplace data structure

### Secondary (MEDIUM confidence)
- Codesearch: "LangGraph human in loop verification checkpoint" - Verified interrupt pattern
- Codesearch: "LLM fact checking citations grounding" - RAG patterns

### Tertiary (LOW confidence)
- WebSearch (limited): Market research tools - Need to validate in practice

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - Based on existing project patterns + verified APIs
- Architecture: HIGH - LangGraph patterns already in project, verified with codesearch
- Pitfalls: MEDIUM - Common patterns across market research AI projects

**Research date:** 2026-03-27
**Valid until:** 2026-04-26 (30 days for stable patterns)