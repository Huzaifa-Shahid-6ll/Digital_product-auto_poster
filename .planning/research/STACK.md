# Technology Stack

**Project:** Digital Product Auto-Poster
**Researched:** 2026-03-26
**Context:** Automation tool for digital product validation workflow (niche research → product generation → marketplace listing → traffic)

---

## Recommended Stack

### Core Architecture: Hybrid Python + TypeScript

The 2025/2026 standard for AI-powered automation tools is a **split architecture**: TypeScript/Next.js for the product-facing UI and API gateway, Python/FastAPI for AI orchestration layer. This gives you the best of both worlds—fast frontend development with access to the strongest AI ecosystem in Python.

| Layer | Technology | Version | Purpose | Why |
|-------|------------|---------|---------|-----|
| **Frontend** | Next.js | 15.x | UI, dashboard, user interactions | App Router, React 19, Turbopack, native streaming support for AI responses |
| **Frontend UI** | React | 19.x | Component library | Full React 19 integration with use() hook for async data |
| **Frontend Styling** | Tailwind CSS | 3.x | Rapid UI development | Standard for Next.js, responsive, maintainable |
| **Backend (API Gateway)** | Next.js API Routes | - | Request routing, auth | Unified codebase, works with Vercel deployment |
| **AI Orchestration** | FastAPI | 0.115+ | AI workflow management | Async, streaming support, native LangChain/LangGraph integration |
| **Agent Framework** | LangGraph | 0.2.70+ | Multi-step AI workflows | Graph-based state management, tool calling, memory |
| **LLM Integration** | LangChain | 0.3.x | Model abstraction | Unified API for OpenAI, Anthropic, Google models |
| **Database** | PostgreSQL + pgvector | 16+ | Structured data + embeddings | ACID compliance, vector search in one system |
| **Managed DB Option** | Supabase | - | PostgreSQL + Auth + Storage | All-in-one backend, RLS, real-time, MCP server |
| **Queue/Workers** | Redis + BullMQ | 5.x | Async job processing | Agent workflows, background tasks, rate limiting |

### Alternative: Single-Language Node.js Stack

For teams preferring TypeScript everywhere:

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | NestJS or Express | API server |
| AI SDK | Vercel AI SDK | Simple LLM calls (but limited vs LangChain) |
| Agents | CrewAI (via LiteLLM) | Multi-agent orchestration |
| Database | PostgreSQL + pgvector | Same as above |

**Why NOT this:** Python's LangChain/LangGraph ecosystem is significantly more mature for complex AI workflows. Vercel AI SDK is great for simple chat interfaces but lacks the tooling for multi-step agent pipelines with tool calling.

---

## Installation

### Frontend (Next.js 15)

```bash
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"
cd frontend
npm install next@latest react@19 react-dom@19
npm install @vercel/ai ai swr zustand
npm install -D @types/node @types/react @types/react-dom typescript eslint-config-next
```

### Backend (FastAPI + LangGraph)

```bash
mkdir backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Core dependencies
pip install fastapi>=0.115 uvicorn[standard]>=0.30
pip install pydantic>=2.7 pydantic-settings>=2.1

# AI/LLM ecosystem
pip install langchain>=0.3 langgraph>=0.2 langchain-openai langchain-anthropic

# Database
pip install sqlalchemy>=2.0 asyncpg psycopg2-binary
pip install pgvector  # For vector embeddings

# Utilities
pip install python-dotenv httpx python-multipart

# Observability
pip install langfuse  # LLM tracing
```

### Database (PostgreSQL + pgvector)

```bash
# Option 1: Supabase (managed)
# Sign up at supabase.com, create project, get connection string

# Option 2: Self-hosted PostgreSQL with pgvector
docker run -d -e POSTGRES_PASSWORD=yourpassword -p 5432:5432 pgvector/pgvector:pg16
```

---

## Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Puppeteer / Playwright** | Latest | Browser automation | Scraping Etsy listings, competitor analysis |
| **Cheerio** | Latest | Lightweight HTML parsing | Simple scraping tasks |
| **SWR** | Latest | Client-side data fetching | Dashboard analytics, real-time updates |
| **Zustand** | Latest | State management | Simple global state (vs Redux) |
| **Recharts** | Latest | Data visualization | Analytics dashboard charts |
| **Clerk / NextAuth** | Latest | Authentication | User management |
| **Sharp** | Latest | Image processing | Thumbnail generation for product images |
| **Pillow** | Latest | Image manipulation | Basic image editing for deliverables |

---

## Infrastructure & Deployment

### Recommended Hosting

| Component | Provider | Why |
|-----------|----------|-----|
| Frontend | Vercel | Native Next.js support, edge functions, fast deploys |
| Backend API | Railway / Render | Python support, easy scaling, reasonable pricing |
| Database | Supabase | Managed PostgreSQL, connection pooling, built-in auth |
| File Storage | Supabase Storage or AWS S3 | Product images, generated PDFs |
| Observability | Langfuse | LLM-specific tracing, cost tracking |

### Environment Configuration

```
# Frontend (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_key

# Backend (.env)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://...
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| **AI Framework** | LangGraph | CrewAI | LangGraph gives finer control over state, retries, and tool calling. CrewAI is easier but less flexible for complex orchestration. |
| **Database** | PostgreSQL + pgvector | Pinecone / Weaviate | pgvector handles both structured data and embeddings. Keep it simple initially—add dedicated vector DB only if needed at scale. |
| **Managed DB** | Supabase | AWS RDS / Neon | Supabase provides auth, storage, real-time, and MCP server out of the box. Faster MVP development. |
| **Frontend** | Next.js 15 | Remix | Next.js has larger ecosystem, more AI-focused templates, Vercel integration. |
| **Backend** | FastAPI | Express / NestJS | FastAPI's async/await and automatic OpenAPI docs are better for AI pipelines. |
| **Orchestration** | n8n (no-code) | Zapier / Make | n8n is open-source and self-hostable. Good for simpler workflows, but custom AI agents need code. |

---

## Stack Selection Rationale

### Why Python (FastAPI) for AI Layer?

1. **Ecosystem dominance**: LangChain, LangGraph, LlamaIndex, Hugging Face—all Python-first. The best AI tooling arrives in Python first.
2. **Async performance**: FastAPI's async model handles concurrent AI requests efficiently—critical for automation tools processing multiple niches/products simultaneously.
3. **Streaming**: Native support for Server-Sent Events (SSE) enables real-time progress updates as agents work through multi-step workflows.
4. **Tool calling**: LangGraph's structured output and tool calling is production-ready for agents that need to browse Etsy, generate content, call APIs.

### Why Next.js 15 for Frontend?

1. **App Router**: The standard for 2025/2026—nested layouts, server components, streaming with Suspense.
2. **React 19**: Native support for `use()` hook simplifies async data handling in components.
3. **Turbopack**: Now stable—drastically faster dev builds for iteration speed.
4. **AI integration**: Built-in support for streaming responses, edge functions for lightweight AI logic.
5. **Full-stack**: API routes + frontend in one repo—simpler for MVP.

### Why PostgreSQL + pgvector?

1. **Single system**: No separate vector DB initially. Store user data, workflow state, AND embeddings in one place.
2. **ACID**: Agents need reliable state—transactions prevent partial workflow completion.
3. **Supabase option**: If you want managed, Supabase adds auth, storage, real-time subscriptions.

---

## Sources

### Primary (Context7 / Official Docs)

- LangGraph Documentation: https://python.langchain.com/docs/langgraph/
- FastAPI Async Streaming: https://fastapi.tiangolo.com/advanced/streaming-responses/
- Next.js 15 Release Notes: https://nextjs.org/blog/next-15
- Supabase Agent Skills: https://supabase.com/blog/postgres-best-practices-for-ai-agents
- pgvector GitHub: https://github.com/pgvector/pgvector

### Secondary (Community / Industry)

- "Tech Stack for AI Agents in 2026" (techstack.sh): https://techstack.sh/guides/tech-stack-for-ai-agents/
- "Best AI Tech Stack for Startups" (Krishang Technolab): https://www.krishangtechnolab.com/blog/ai-tech-stack-for-startups-guide/
- "Building AI Workflows with FastAPI and LangGraph" (Towards AI): https://pub.towardsai.net/building-ai-workflows-with-fastapi-and-langgraph-step-by-step-guide-599937ab84f3
- Reddit r/automation discussion on AI stacks: https://www.reddit.com/r/automation/comments/1ptqq9y/whats_ai_stack_for_workflow_automation_in_2025/
- "Best Database Solutions for AI Agents" (Fast.io): https://fast.io/resources/best-database-solutions-ai-agents/

---

## Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| **Frontend Stack** | HIGH | Next.js 15 is current stable, widely adopted, well-documented |
| **AI Orchestration** | HIGH | LangGraph + FastAPI is production-validated by multiple projects |
| **Database** | HIGH | PostgreSQL + pgvector is the emerging standard for AI apps |
| **Agent Framework** | MEDIUM | LangGraph is strong but ecosystem still evolving rapidly |
| **Managed Services** | HIGH | Supabase well-documented, actively developed |

---

## Gaps to Address

- **Scraping infrastructure**: Need to research Playwright vs Puppeteer for Etsy scraping (legal/TOS considerations)
- **Marketplace APIs**: Need to verify Etsy API capabilities vs Gumroad vs general approach
- **Traffic automation**: Need research on social media API limits and feasibility
