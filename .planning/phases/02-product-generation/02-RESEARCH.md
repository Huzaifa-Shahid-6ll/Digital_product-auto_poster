# Phase 2: Product Generation - Research

**Researched:** 2026-03-26
**Domain:** AI-powered digital product generation (PDF planners/templates/guides)
**Confidence:** MEDIUM

## Summary

Phase 2 focuses on generating product ideas based on niche input and auto-creating digital deliverables. The key technical challenge is combining template-based structure with AI-generated content to produce consistent, high-quality PDF products.

**Primary recommendation:** Use a hybrid approach - templates provide structure (product category, format type, target audience), AI generates specific content. For PDF generation, use ReportLab for programmatic control or markdown-to-PDF conversion via WeasyPrint/Playwright.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Hybrid approach — templates provide structure + format, AI generates specific content
- **D-02:** PDF only for MVP — planners and worksheets (high demand on Etsy)
- **D-03:** AI + Human review — AI does initial assessment, user does final approval
- **D-04:** Approve then create — user reviews ideas, selects one, system generates product
- **D-05:** Web dashboard for review and approval

### the agent's Discretion
- Exact template structure and prompts
- Specific AI model and parameters
- File naming conventions

### Deferred Ideas (OUT OF SCOPE)
- Support for multiple formats (Canva, Notion, Excel) — future phase
- Iterative feedback workflow — if user wants more refinement later

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PG-01 | Generate digital product ideas based on niche research | AI prompt engineering patterns, template-based generation |
| PG-02 | Auto-generate digital product deliverables (planners, templates, guides) | PDF generation libraries, content-to-PDF pipelines |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| openai | ^1.12.0 | AI content generation | Industry standard, GPT-4o for product content |
| reportlab | ^4.0.9 | PDF generation (Python) | Mature, programmatic PDF creation |
| jinja2 | ^3.1.3 | Template rendering | Standard Python templating |
| pydantic | ^2.5.0 | Data validation | LangGraph ecosystem alignment |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| markdown | ^3.5.2 | Markdown to PDF conversion | If generating from markdown content |
| weasyprint | ^60.0 | HTML to PDF | Alternative to ReportLab for HTML-based layouts |
| playwright | ^1.41.0 | Browser PDF generation | Complex layouts, visual fidelity |
| python-multipart | ^2.0.0 | File uploads | Dashboard image/file handling |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ReportLab | WeasyPrint | ReportLab = more programmatic control, WeasyPrint = easier HTML/CSS layouts |
| OpenAI | Anthropic Claude | Both work, Claude slightly better at reasoning but OpenAI more established |
| Custom prompts | LangChain prompts | Custom prompts fine for MVP, LangChain for complex chains |

**Installation:**
```bash
pip install openai reportlab jinja2 pydantic markdown weasyprint
npm install playwright
```

## Architecture Patterns

### Recommended Project Structure
```
src/
├── product_generation/
│   ├── __init__.py
│   ├── ideas.py          # Idea generation logic
│   ├── templates/        # Product templates
│   │   ├── planner.py
│   │   ├── worksheet.py
│   │   └── guide.py
│   ├── generator.py      # PDF/content generation
│   ├── validator.py      # Quality validation
│   └── schemas.py        # Pydantic models
├── api/
│   └── product_routes.py # FastAPI endpoints
└── cli/
    └── commands.py       # CLI entry points
```

### Pattern 1: Template-AI Hybrid Generation
**What:** Templates define structure, AI fills content
**When to use:** Consistent product quality with AI flexibility
**Example:**
```python
from jinja2 import Template
from openai import OpenAI

class ProductGenerator:
    def __init__(self, client: OpenAI):
        self.client = client
        self.templates = {
            "planner": Template(PLANNER_TEMPLATE),
            "worksheet": Template(WORKSHEET_TEMPLATE),
        }
    
    async def generate(self, idea: ProductIdea, format_type: str) -> bytes:
        # 1. Render template with structure
        template_data = self.templates[format_type].render(
            audience=idea.target_audience,
            topic=idea.topic,
        )
        # 2. AI fills specific content
        content = await self._generate_content(idea, template_data)
        # 3. Convert to PDF
        return self._to_pdf(content, format_type)
```

### Pattern 2: Human-in-the-Loop Review
**What:** AI generates draft, human approves before final
**When to use:** Quality-critical outputs, user agency required
**Example:**
```python
async def review_workflow(idea: ProductIdea) -> ProductOutput:
    # Step 1: Generate ideas (AI)
    ideas = await idea_generator.generate(niche=idea.niche, count=3)
    
    # Step 2: User reviews and selects (Human)
    selected = await dashboard.present_for_review(ideas)
    
    # Step 3: Generate product from selected
    product = await generator.generate(selected)
    
    # Step 4: Validate quality
    validation = await validator.validate(product)
    
    return product
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF layout | Custom positioning logic | ReportLab's SimpleDocTemplate or Platypus | Complex pagination, headers, tables handled |
| AI prompts | Simple f-strings | Pydantic + system prompts | Structured output, validation |
| File storage | Custom local storage | SQLite + phase 1's SqliteSaver | Persistence already exists |

## Runtime State Inventory

> This is a greenfield feature — no existing runtime state to migrate.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — new feature | None |
| Live service config | None — new feature | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

## Common Pitfalls

### Pitfall 1: AI-Generated Content Inconsistency
**What goes wrong:** Different quality across products, missing sections
**Why it happens:** No structured prompts, no validation of output
**How to avoid:** 
- Use Pydantic schemas to validate AI output structure
- Implement quality scoring before returning to user
- Include "must include" sections in prompts
**Warning signs:** "Good enough" fallback, no structured validation

### Pitfall 2: Template Content Mismatch
**What goes wrong:** Generated content doesn't fit template layout
**Why it happens:** No content length estimation, fixed page counts
**How to avoid:**
- Estimate content length before generation
- Use dynamic page count with ReportLab's flowables
- Test with various content lengths
**Warning signs:** Truncated content, broken pagination

### Pitfall 3: Single-Pass Generation Without Validation
**What goes wrong:** User receives poor quality product, must regenerate
**Why it happens:** No automated quality check before user sees output
**How to avoid:**
- Run validation pass before presenting to user
- Score: completeness, formatting, coherence
- Flag issues for human review

## Code Examples

### Product Idea Generation with Structured Output
```python
from pydantic import BaseModel
from openai import OpenAI

class ProductIdea(BaseModel):
    title: str
    format: str  # planner, worksheet, guide
    target_audience: str
    unique_angle: str
    key_features: list[str]
    rationale: str  # Why this fits the niche

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "Generate 3 product ideas for..."},
        {"role": "user", "content": f"Niche: {niche}"}
    ]
)
ideas = [ProductIdea.model_validate_json(idea) for idea in parsed["ideas"]]
```

### PDF Generation with ReportLab
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_pdf(content: dict) -> bytes:
    doc = SimpleDocTemplate("product.pdf", pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    story.append(Paragraph(content["title"], styles['Title']))
    story.append(Spacer(1, 12))
    
    for section in content["sections"]:
        story.append(Paragraph(section["heading"], styles['Heading2']))
        story.append(Paragraph(section["body"], styles['BodyText']))
        story.append(Spacer(1, 12))
    
    doc.build(story)
    return buffer.getvalue()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based templates | AI + hybrid templates | 2023+ LLMs | Much more personalized content |
| Fixed layouts | Dynamic flowable-based | ReportLab 4.0+ | Better content adaptation |
| Manual review only | AI + human validation | 2024 | Faster iteration, consistent quality |

**Deprecated/outdated:**
- WeasyPrint standalone: Now used primarily as part of HTML-to-PDF pipeline, not standalone
- HTML-based generation: Direct PDF generation (ReportLab) now preferred for programmatic control

## Open Questions

1. **Content length estimation**
   - What we know: AI can generate variable length content
   - What's unclear: How to predict page count before generation
   - Recommendation: Generate first, validate, adjust if needed

2. **Template vs AI boundary**
   - What we know: Templates provide structure, AI provides content
   - What's unclear: How much structure to hardcode vs generate
   - Recommendation: Start with minimal templates, expand based on user feedback

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
| PG-01 | Generate 3+ product ideas with rationale | unit | `pytest tests/test_ideas.py -x` | ❌ Wave 0 |
| PG-02 | Auto-generate PDF from selected idea | integration | `pytest tests/test_generator.py -x` | ❌ Wave 0 |
| PG-02 | Quality validation passes | unit | `pytest tests/test_validator.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_product_generation/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ideas.py` — covers PG-01
- [ ] `tests/test_generator.py` — covers PG-02 generation
- [ ] `tests/test_validator.py` — covers PG-02 validation
- [ ] `tests/conftest.py` — shared fixtures
- [ ] `tests/__init__.py` — package marker

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Core runtime | ✓ | 3.11+ | — |
| OpenAI API | Content generation | ✓ | Latest | Anthropic Claude |
| ReportLab | PDF generation | ✓ (via pip) | 4.0.9 | WeasyPrint |
| Node.js | Dashboard frontend | ✓ | 20+ | — |
| Playwright | Browser PDF (optional) | ✓ (via npm) | 1.41 | Skip, use ReportLab |

**Missing dependencies with no fallback:**
- None identified

**Missing dependencies with fallback:**
- Playwright (optional) — ReportLab sufficient for MVP

---

## Sources

### Primary (HIGH confidence)
- OpenAI API docs - Structured output with Pydantic
- ReportLab documentation - PDF generation patterns

### Secondary (MEDIUM confidence)
- WebSearch: "best PDF generation Python 2024" - Confirmed ReportLab as standard

### Tertiary (LOW confidence)
- WebSearch only: Template best practices (need to validate in practice)

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH - Verified via Context7/official docs
- Architecture: MEDIUM - Based on Phase 1 patterns, adapted for product generation
- Pitfalls: MEDIUM - Common patterns across AI+PDF projects

**Research date:** 2026-03-26
**Valid until:** 2026-04-23 (30 days for stable patterns)