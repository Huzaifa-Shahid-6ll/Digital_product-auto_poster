# Phase 3: Listing Creation - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase delivers Etsy marketplace integration: users connect their Etsy shop via OAuth, AI generates optimized listing content (title, description, tags), images upload to Etsy CDN, compliance layer filters keywords/adds AI disclosure/staggers publishing, and listings go live with AI-suggested pricing that users confirm.

Scope includes: Etsy OAuth (multi-shop support), image upload to Etsy CDN, AI-generated listing content with SEO focus, full compliance layer (keyword filtering, AI disclosure, staggered publishing), category selection (AI suggestion + confirm), file delivery via Etsy, unlimited inventory for digital products, and sequential batch listing capability.

</domain>

<decisions>
## Implementation Decisions

### Etsy OAuth
- **D-01:** Full OAuth with Etsy - user authorizes, system stores refresh token, auto-refresh on expiration
- **D-02:** Multi-shop support - if user has multiple Etsy shops, they can choose which to use for listings

### Image Handling
- **D-03:** Upload images to Etsy CDN - system uploads to Etsy, gets back listing image URLs
- **D-04:** Product images from Phase 2 (PDF preview/render) get uploaded to Etsy during listing creation

### Listing Content
- **D-05:** AI generates title, description, and tags - user can edit before publishing (human-in-the-loop per D-03 from Phase 2)
- **D-06:** SEO-focused tone - optimized for Etsy search with keywords and searchable phrases
- **D-07:** Title: SEO-optimized, max 140 characters (Etsy limit)
- **D-08:** Description: SEO-focused with key features, benefits, usage info
- **D-09:** Tags: 13 tags max (Etsy limit), AI generates relevant search terms

### Compliance Layer
- **D-10:** Keyword filtering - filter out prohibited words (e.g., "handmade" for digital products)
- **D-11:** AI disclosure - add required disclosure text for AI-generated content
- **D-12:** Staggered publishing - spread multiple listings over time to avoid spam detection
- **D-13:** Full compliance - all three compliance features active by default

### Pricing
- **D-14:** AI suggests price based on market data - user confirms before publishing
- **D-15:** Price suggestion considers similar listings' pricing, product complexity

### Category Selection
- **D-16:** AI recommends best Etsy category based on product - user confirms selection
- **D-17:** Category affects search visibility - important for discoverability

### File Delivery
- **D-18:** Etsy file hosting - upload PDF to Etsy, Etsy handles download delivery to buyers

### Inventory Handling
- **D-19:** Unlimited quantity - digital products have no physical stock limits

### Batch Listing
- **D-20:** Sequential batch listing - create multiple listings from approved products one at a time
- **D-21:** Allows user to review each listing before the next is created

### Agent Discretion
- Retry logic for API failures (per D-04 from Phase 1: 3 retries with exponential backoff)
- Image sizing/cropping for Etsy requirements (square preferred, max 20 images)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Core value, requirements, constraints
- `.planning/REQUIREMENTS.md` — MK-01, MK-02 requirements for this phase
- `.planning/STATE.md` — Phase 2 decisions, current project state
- `.planning/ROADMAP.md` — Phase 3 goal and success criteria

### Prior Phase Context
- `.planning/phases/02-product-generation/02-CONTEXT.md` — (if exists) Product generation decisions
- `.planning/phases/02-product-generation/02-SUMMARY.md` — What was built in Phase 2

### Codebase Patterns
- `src/api/main.py` — FastAPI app setup, route registration pattern
- `src/api/idea_routes.py` — Example of API routes with dependency injection
- `src/product_generation/generator.py` — Product generation with PDF output
- `src/workflows/product_review.py` — State machine pattern for workflow

### External References
- Etsy API v3 documentation — For OAuth flow and listing creation endpoints
- Etsy Developer Portal — API key registration, OAuth configuration

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/api/idea_routes.py`, `src/api/product_routes.py`, `src/api/review_routes.py` — Route patterns to follow
- `src/product_generation/generator.py` — Already generates PDF products (input to listing)
- `src/workflows/product_review.py` — State machine pattern for review workflow
- FastAPI dependency injection pattern used throughout API routes

### Established Patterns
- AsyncOpenAI client for AI calls (per Phase 2)
- Pydantic models for request/response validation
- Retry logic with exponential backoff (per D-04 from Phase 1)
- Human-in-the-loop review before publishing (per D-03 from Phase 2)
- WebSocket for real-time updates (already in main.py)

### Integration Points
- New listing routes will mount at `/api/listings` (new router)
- OAuth routes mount at `/api/auth/etsy` (new router)
- Connects to: product generation (approved products from Phase 2), review workflow (approval triggers listing)
- Uses existing OpenAI client from main.py

</code_context>

<specifics>
## Specific Ideas

- Etsy OAuth should redirect user to Etsy authorization, then callback to store tokens
- Images: ProductGenerator creates PDF, need to render/screenshot PDF for listing images
- Compliance: Keyword filter list needs to be maintained (prohibited terms for digital)
- Staggered publishing: configurable delay between listings (e.g., 1 hour, 1 day)
- Category: Use Etsy API category endpoint to get category tree for suggestions
- Pricing: Query similar listings via Etsy API to get price suggestions

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-listing-creation*
*Context gathered: 2026-03-26*