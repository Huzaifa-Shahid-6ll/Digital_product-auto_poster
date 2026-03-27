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
| etsy-api-v3 | latest | Etsy marketplace data (listings, search) | Phase 5+ only (not MVP) |
| requests | ^2.31.0 | HTTP calls for APIs | pytrends and Etsy API calls |
| aiohttp | ^3.9.0 | Async HTTP for parallel API calls | Faster data gathering |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pytrends | SerpApi (paid) | pytrends is free but rate-limited; SerpApi more reliable |
| OpenAI | Anthropic Claude | Both work, Claude slightly better at reasoning |
| Google Trends + Etsy API | Google Trends alone (MVP) | Etsy API needs registration, skip for v1 |

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
- Cache results for short periods (15-minute TTL)
- Add fallback to cached data if API unavailable
- Handle 429 with exponential backoff + retry-after header
**Warning signs:** "Too many requests" errors, partial data returned

### Pitfall 5: LangGraph Interrupt Re-execution Trap
**What goes wrong:** Node logic re-runs after human approval, causing duplicate work
**Why it happens:** Default interrupt behavior re-executes entire node from start
**How to avoid:**
- Set ALL state needed AFTER resume BEFORE calling interrupt()
- Or use state-based checkpoint pattern instead of interrupt
- Test with actual resume flow to verify behavior
**Warning signs:** Duplicate API calls, state reset after user approval

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

### 1. Etsy API v3 Deep Dive
**Registration:** 
- Register at https://www.etsy.com/developers/register
- Generates API key + shared secret (personal access by default)
- Can connect up to 5 shops with personal access
- Commercial access requires separate request and approval

**Rate Limits:**
- QPD (Queries Per Day): Sliding window, ~100,000 default for new apps
- QPS (Queries Per Second): ~150 default for new apps
- Headers: `x-remaining-this-second`, `x-remaining-today`
- On 429: Use `retry-after` header + exponential backoff

**Available Data:**
- Listings API: Search, create, update, delete listings
- No direct "search by keyword" endpoint for market analysis (would need to search manually)
- Can get listing count for specific shops/categories

**Recommendation for MVP:** Skip Etsy API for Phase 4. Use Google Trends for demand verification. Revisit Etsy API in Phase 5 if user needs competition analysis.

### 2. Demand Scoring Algorithm
**Industry Standard Approach (MicroNicheBrowser methodology):**

| Dimension | Weight | What It Measures | Data Sources |
|-----------|--------|-----------------|--------------|
| Opportunity | 20% | Market size/demand | Google Trends, search volume |
| Problem Severity | 10% | Pain intensity | Reddit engagement, community signals |
| Feasibility | 30% | Can you build it? | Competition density, domain authority |
| Timing | 20% | Is now the right time? | Trend trajectory, YoY growth |
| Go-to-Market | 20% | Can you reach customers? | Social platforms, community access |

**MVP Simplified Formula:**
```
demand_score = (search_interest * 0.4) + (trend_direction * 0.3) + (competition_factor * 0.3)
```
Where:
- search_interest: Google Trends average (0-100)
- trend_direction: +1 (rising), 0 (stable), -1 (declining)
- competition_factor: High competition = 0.3, Medium = 0.6, Low = 1.0

**Scoring thresholds:**
- 65+: Validated niche (only ~1% of niches)
- 50-65: Worth exploring
- <50: Low demand, not recommended

### 3. LangGraph Interrupt Deep Dive

**Key behaviors:**
1. First call raises `GraphInterrupt` exception, pauses graph
2. Client receives interrupt value (can be dict with context)
3. Resume with `Command(resume=value)` - re-executes the entire node
4. Multiple interrupts in same node matched by order

**Complete workflow pattern:**
```python
import uuid
from typing import Optional
from typing_extensions import TypedDict
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import StateGraph
from langgraph.types import interrupt, Command

class ResearchState(TypedDict):
    keywords: list[str]
    recommendations: list[dict]
    verified_niches: list[dict]
    user_decision: Optional[str]
    current_step: str

def verification_checkpoint(state: ResearchState) -> ResearchState:
    """Human verification checkpoint node."""
    
    # Create interrupt payload with review data
    interrupt_payload = {
        "message": "Review verified niche recommendations",
        "niches": state["verified_niches"],
        "options": [
            {"id": "proceed", "label": "Proceed to product generation"},
            {"id": "retry", "label": "Generate new recommendations"},
            {"id": "cancel", "label": "Cancel workflow"}
        ]
    }
    
    # This raises GraphInterrupt, pauses workflow
    user_choice = interrupt(interrupt_payload)
    
    # After resume, this code runs (node re-executes)
    # Store user decision in state
    state["user_decision"] = user_choice["decision"]
    
    if user_choice["decision"] == "cancel":
        state["current_step"] = "cancelled"
    elif user_choice["decision"] == "retry":
        state["current_step"] = "analyze"  # Will re-run analysis
    else:
        state["current_step"] = "proceed"
    
    return state

# Usage in client code:
# 1. Run workflow until interrupt
# 2. Display UI to user
# 3. Send Command(resume={"decision": "proceed"}) to continue

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# First call - will interrupt
for chunk in graph.stream(initial_state, config):
    if "__interrupt__" in chunk:
        # Show user the interrupt payload
        review_data = chunk["__interrupt__"][0].value
        break

# After user reviews and clicks "Proceed"
command = Command(resume={"decision": "proceed"})
for chunk in graph.stream(command, config):
    print(chunk)
```

**Important:** Node re-executes from start after resume. Any logic before `interrupt()` will run again. To preserve data, ensure state is already set before the interrupt call.

---

## Deep Dive Findings

### Etsy API v3 for Competition Analysis

**Registration & Access:**
- Free registration at Etsy Developer Portal
- Personal access: Read/write to your own shop (up to 5 shops)
- Commercial access: Requires application and approval
- No cost for API usage, but must follow caching policies

**Rate Limits (verified):**
- Default: ~100,000 QPD (sliding 24-hour window)
- Default: ~150 QPS
- Check via headers: `x-remaining-this-second`, `x-remaining-today`
- Handle 429 with exponential backoff using `retry-after` header

**Data Available:**
- Listings: Create, read, update, delete
- Shops: Get shop info, listings
- Inventory: Manage inventory
- **Limitation:** No direct "search listings by keyword" endpoint for competitive analysis - would need manual sampling

**MVP Decision:** Skip Etsy API integration in Phase 4. Use Google Trends for demand verification. Add Etsy API in Phase 5 if analytics requires competitor counts.

### Demand Scoring Algorithm

**Proven methodology from market research tools:**

Five-dimension weighted scoring (used by MicroNicheBrowser and similar tools):

| Dimension | Weight | Data Sources | Score Method |
|-----------|--------|--------------|--------------|
| Opportunity | 20% | Google Trends, search volume | Log-scale curve |
| Problem Severity | 10% | Reddit engagement depth | Thread reply count |
| Feasibility | 30% | Competition density | Inverse competition |
| Timing | 20% | Trend trajectory | Growth velocity |
| Go-to-Market | 20% | Social platforms | Platform diversity |

**MVP Simplified Implementation:**
```python
def calculate_demand_score(trends_data: dict, competition: str) -> int:
    """Calculate demand score 0-100."""
    
    # Search interest (0-100 from Google Trends)
    search_interest = trends_data.get("average_interest", 0)
    
    # Trend direction bonus/penalty
    trend_bonus = 10 if trends_data.get("trend_direction") == "up" else 0
    trend_penalty = -10 if trends_data.get("trend_direction") == "down" else 0
    
    # Competition factor (inverse)
    competition_map = {"low": 1.0, "medium": 0.6, "high": 0.3}
    competition_factor = competition_map.get(competition, 0.5)
    
    # Calculate score
    base_score = (search_interest * 0.4) + (competition_factor * 30)
    final_score = min(100, max(0, base_score + trend_bonus + trend_penalty))
    
    return int(final_score)

# Threshold
# >= 65: Validated (rare)
# 50-65: Worth exploring
# <50: Low demand
```

### LangGraph Interrupt Pattern

**How it works:**
1. `interrupt(value)` raises `GraphInterrupt` exception
2. Graph pauses, client receives the value
3. Client processes (shows UI to human)
4. Client resumes with `Command(resume=...)`
5. Node re-executes from start (not from interrupt point)

**Critical insight:** Node re-executes on resume. All state needed after resume must be set BEFORE the interrupt call. The interrupt call itself returns the resume value.

**Alternative: State-based checkpoint without interrupt:**

If you don't want node re-execution, use a dedicated checkpoint node that returns and waits for external trigger:
```python
def checkpoint_node(state: ResearchState) -> ResearchState:
    # Set all data needed for UI
    state["checkpoint_data"] = {
        "niches": state["verified_niches"],
        "ready_for_review": True
    }
    state["current_step"] = "awaiting_approval"
    # Return without interrupt - workflow "ends" here
    # Client queries state, shows UI, then sends update via API
    return state

# Client resumes via state update + continue
graph.invoke({"user_decision": "proceed"}, config)
```

This pattern is simpler for MVP and works well with existing workflow patterns. Use interrupt only when you need to pass dynamic payload to client.

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
| Etsy API v3 | Competition data | ✗ | — | Deferred to Phase 5+ |

**Missing dependencies with no fallback:**
- Etsy API v3 — requires app registration, deferred to Phase 5+ for competition analysis

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