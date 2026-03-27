# Integration Check Report - Phase 3: Listing Creation

**Date:** 2026-03-27  
**Phase:** 03-listing-creation  
**Status:** INTEGRATION ISSUES FOUND

---

## Wiring Summary

| Status | Count |
|--------|-------|
| Connected | 8 |
| Orphaned | 2 |
| Missing | 3 |

### Connected Exports

| Export | From Phase | Used By | Status |
|--------|------------|---------|--------|
| `ListingGenerator` | 03-02 | listing_routes.py | ✓ CONNECTED |
| `EtsyClient` | 03-01 | listing_routes.py | ✓ CONNECTED |
| `calculate_stagger_delay` | 03-04 | listing_routes.py | ✓ CONNECTED |
| `get_stagger_schedule` | 03-04 | listing_routes.py | ✓ CONNECTED |
| `ProductIdea`, `ProductOutput` | 02-01 | product_routes.py, review_routes.py | ✓ CONNECTED |
| `ProductGenerator` | 02-02 | product_routes.py | ✓ CONNECTED |
| `WorkflowEngine` | 01-04 | main.py | ✓ CONNECTED |
| `AsyncOpenAI` | main.py | listing_routes.py | ✓ CONNECTED |

### Orphaned Exports

| Export | From Phase | Reason |
|--------|------------|--------|
| `apply_compliance` | 03-04 | Defined in compliance/apply.py but never called in listing_routes.py |
| `filter_keywords` | 03-04 | Exported but not imported anywhere |

### Missing Connections

| Expected Connection | From | To | Reason |
|---------------------|------|-----|--------|
| Listing routes mounted | listing_routes.py | main.py | Router not included in app |
| Compliance applied to listings | compliance/apply.py | listing_routes.py | apply_compliance() never called |
| Product data passed to batch | product_routes.py (_products_storage) | listing_routes.py (batch) | Each has independent storage |

---

## API Coverage

### Routes Created by Phase 3

| Route | Handler | Mounted? |
|-------|---------|----------|
| `/api/auth/etsy/authorize` | etsy_routes.py | ✓ Yes |
| `/api/auth/etsy/callback` | etsy_routes.py | ✓ Yes |
| `/api/auth/etsy/shops` | etsy_routes.py | ✓ Yes |
| `/api/listings` | listing_routes.py | ✗ **NO** |
| `/api/listings/{id}` | listing_routes.py | ✗ **NO** |
| `/api/listings/{id}/publish` | listing_routes.py | ✗ **NO** |
| `/api/listings/{id}/images` | listing_routes.py | ✗ **NO** |
| `/api/listings/{id}/files` | listing_routes.py | ✗ **NO** |
| `/api/listings/batch` | listing_routes.py | ✗ **NO** |

**API Routes Consumed:** 4 (etsy_routes)  
**API Routes NOT mounted:** 9 (listing_routes)

---

## E2E Flows

### Flow 1: Product Idea → Listing Creation

```
POST /api/ideas/generate → IdeaGenerator (Phase 2)
         ↓
POST /api/products/generate → ProductGenerator (Phase 2)
         ↓
POST /api/review/approve → ReviewWorkflow (Phase 2)
         ↓
POST /api/listings → ListingGenerator (Phase 3) ← NOT MOUNTED
         ↓
Compliance applied (MISSING: apply_compliance not called)
         ↓
Etsy API → publish
```

**Status:** BROKEN AT LISTING CREATION  
**Break Point:** Listing routes not mounted in main.py

### Flow 2: Batch Listing from Approved Products

```
POST /api/listings/batch → listing_routes.py (NOT MOUNTED)
         ↓
For each product_id:
  - ListingGenerator.generate()
  - Store in _listings_storage (independent from Phase 2)
  - Apply stagger delays
         ↓
POST /api/listings/batch/{id}/approve
         ↓
publish_listing()
```

**Status:** BROKEN  
**Issue 1:** Batch endpoint not accessible (not mounted)  
**Issue 2:** Products come from Phase 2 but stored independently (no shared state)

### Flow 3: OAuth → Listing

```
GET /api/auth/etsy/authorize → OAuth flow (Phase 3)
         ↓
GET /api/auth/etsy/callback → Token stored
         ↓
POST /api/listings → Uses OAuth tokens
```

**Status:** BROKEN (depends on Flow 1)

---

## Requirements Integration Map

| Requirement | Integration Path | Status | Issue |
|-------------|-----------------|--------|-------|
| MK-01 | Phase 2 products → Phase 3 listing_routes → Etsy API | **UNWIRED** | listing_routes not mounted in main.py |
| MK-02 | image_upload.py → listing_routes → Etsy CDN | **UNWIRED** | listing_routes not mounted |
| PG-01 | idea_routes → Phase 2 ideas → Phase 3 listing | **PARTIAL** | Phase 2 wired, Phase 3 not mounted |
| PG-02 | product_routes → Phase 2 products → Phase 3 batch | **PARTIAL** | Phase 2 wired, batch listing not accessible |

### Requirements with No Cross-Phase Wiring

| Requirement | Status | Notes |
|-------------|--------|-------|
| MK-01 (Auto-create listings) | UNWIRED | Endpoint exists but not mounted |
| MK-02 (Image upload) | UNWIRED | Endpoint exists but not mounted |

---

## Detailed Findings

### BLOCKING Issue 1: Listing Routes Not Mounted

**Location:** `src/api/main.py`

**Problem:** The listing_routes router is never included in the FastAPI application. All Phase 3 listing endpoints are inaccessible.

**Evidence:**
- `src/api/main.py` lines 114-136 show routing registration
- Missing: `app.include_router(listing_routes.router, prefix="/api/listings")`
- listing_routes.py defines router but it's never imported in main.py

**Fix Required:**
```python
# Add to main.py after other route registrations
from src.api import listing_routes as listing_api_routes
app.include_router(listing_api_routes.router, prefix="/api")
```

---

### BLOCKING Issue 2: Compliance Not Applied

**Location:** `src/api/listing_routes.py`

**Problem:** The `apply_compliance()` function from `src/compliance/apply.py` is never called in listing creation. All listing content passes through without keyword filtering or AI disclosure.

**Evidence:**
- `src/compliance/apply.py` defines `apply_compliance()` and exports it
- `src/compliance/__init__.py` exports `apply_compliance`
- listing_routes.py imports from `compliance.stagger` but never imports or calls `apply_compliance()`
- Line 306-375 in listing_routes.py: content generated but compliance NOT applied

**Fix Required:**
```python
# Add import at top of listing_routes.py
from src.compliance import apply_compliance

# In create_listing() after content generation:
content = await generator.generate(product)
# ADD: Apply compliance
compliance_result = apply_compliance(
    title=content.title,
    description=content.description,
    tags=content.tags,
)
title = compliance_result.title
description = compliance_result.description
tags = compliance_result.tags
```

---

### MINOR Issue 3: Independent Storage

**Location:** Phase 2 vs Phase 3

**Problem:** Products stored in Phase 2 (`product_routes._products_storage`) are not accessible to Phase 3 batch listing. The batch endpoint receives product_ids but has no way to retrieve actual product data.

**Impact:** Batch listing creates mock products instead of using Phase 2 generated products.

---

## Summary

| Category | Count |
|----------|-------|
| Critical Issues | 2 |
| Minor Issues | 1 |
| End-to-End Flows | 3 |
| Flows Working | 0 |
| Flows Broken | 3 |

---

## Next Steps

1. **Mount listing routes** in main.py (BLOCKING)
2. **Integrate compliance** in listing creation (BLOCKING)
3. **Connect product storage** between phases (optional for MVP - use demo mode)

---

*Report generated by gsd-integration-checker*
