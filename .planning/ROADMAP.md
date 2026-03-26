# Roadmap

## Phases

- [ ] **Phase 1: Core Automation Engine** - Build the orchestrator backbone and state management
- [ ] **Phase 2: Product Generation** - Generate product ideas and create digital deliverables
- [ ] **Phase 3: Listing Creation** - Create Etsy listings with compliance layer
- [ ] **Phase 4: Research & Validation** - Niche research with human-in-the-loop verification
- [ ] **Phase 5: Analytics & Measurement** - Track performance and validate results

## Phase Details

### Phase 1: Core Automation Engine

**Goal**: Build the agent orchestration backbone that all downstream work connects to

**Depends on**: Nothing (first phase)

**Requirements**: (No v1 requirements - infrastructure phase)

**Success Criteria** (what must be TRUE):
1. User can define a playbook workflow with multiple steps
2. Workflow state persists across executions (save/resume)
3. Agent can route between workflow steps based on context
4. System handles errors gracefully with retry logic

**Plans**: TBD

---

### Phase 2: Product Generation

**Goal**: Generate product ideas and auto-create digital deliverables

**Depends on**: Phase 1

**Requirements**: PG-01, PG-02

**Success Criteria** (what must be TRUE):
1. User can input a niche and receive 3+ product ideas with rationale
2. System auto-generates a digital product (PDF planner/template/guide) based on selected idea
3. Generated product passes quality validation (formatting, completeness)
4. User can review and approve product before publishing

**Plans**: TBD

---

### Phase 3: Listing Creation

**Goal**: Create Etsy listings with compliance built-in from day one

**Depends on**: Phase 2

**Requirements**: MK-01, MK-02

**Success Criteria** (what must be TRUE):
1. User can connect Etsy shop via OAuth
2. System generates listing title, description, and tags optimized for search
3. User can upload product images and they appear in listing
4. System includes compliance layer (keyword filtering, AI disclosure, staggered publishing)
5. Listing goes live on Etsy with correct pricing

**Plans**: TBD

**UI hint**: yes

---

### Phase 4: Research & Validation

**Goal**: AI-powered niche research with human verification checkpoints

**Depends on**: Phase 1 (can run in parallel with Phase 2-3)

**Requirements**: NR-01, NR-02

**Success Criteria** (what must be TRUE):
1. User can input niche keywords and receive AI-generated niche recommendations
2. System verifies recommendations with real market data (demand, competition)
3. Human-in-the-loop checkpoint requires user confirmation before proceeding to product generation
4. System cites sources for market data (no hallucinations)

**Plans**: TBD

---

### Phase 5: Analytics & Measurement

**Goal**: Track listing performance and enable data-driven validation

**Depends on**: Phase 3

**Requirements**: AN-01

**Success Criteria** (what must be TRUE):
1. User can view dashboard showing listing views, favorites, and sales
2. System attributes sales to specific listings and time periods
3. User can compare performance across multiple listings
4. System surfaces insights (best performing tags, optimal pricing)

**Plans**: TBD

**UI hint**: yes

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Automation Engine | 0/1 | Not started | - |
| 2. Product Generation | 0/4 | Not started | - |
| 3. Listing Creation | 0/5 | Not started | - |
| 4. Research & Validation | 0/4 | Not started | - |
| 5. Analytics & Measurement | 0/4 | Not started | - |

---

*Last updated: 2026-03-26*