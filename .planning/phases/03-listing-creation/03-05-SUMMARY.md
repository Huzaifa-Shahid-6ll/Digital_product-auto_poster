---
phase: 03-listing-creation
plan: 05
subsystem: batch-listing
tags: [batch-listing, sequential-creation, staggered-publishing, compliance]

dependency_graph:
  requires:
    - 03-03 (Image/File Upload)
    - 03-04 (Compliance Layer)
  provides:
    - Batch listing endpoints (/api/listings/batch, /api/listings/batch/{id}, etc.)
    - Batch state management
    - Staggered publishing integration
  affects: [listing-creation, compliance-integration]

tech_stack:
  added: [uuid]
  patterns: [sequential-batch-processing, review-checkpoint, stagger-delays]

key_files:
  modified:
    - src/api/listing_routes.py (added batch endpoints and state management)
  created: []

key_decisions:
  - "D-20: Sequential batch listing - create listings one at a time"
  - "D-21: User reviews each listing before next is created"
  - "D-12 (from 03-04): Staggered publishing - 24 hours between listings"

patterns_established:
  - "Batch Processing: Sequential listing creation with review checkpoints"
  - "Stagger Integration: Batch flow calculates stagger delays between publishes"

requirements_completed: [MK-01, MK-02]

duration: 3min
completed: 2026-03-27
---

# Phase 3 Plan 5: Batch Listing Summary

**Sequential batch listing from approved products with staggered publishing and review checkpoints**

## Performance

- **Duration:** 3 min
- **Tasks:** 3
- **Files modified:** 1

## Accomplishments

All 3 tasks completed in a single execution:

1. **Task 1: Add batch listing endpoints** - POST /api/listings/batch, GET /api/listings/batch/{id}, POST /api/listings/batch/{id}/approve, POST /api/listings/batch/{id}/edit, DELETE /api/listings/batch/{id}

2. **Task 2: Implement batch state management** - BatchListingItem, BatchListingCreateRequest, BatchListingResponse, BatchStatusResponse, BatchApproveResponse, BatchEditResponse models with in-memory storage

3. **Task 3: Integrate stagger with batch** - calculate_stagger_delay, get_stagger_schedule imported and integrated into batch approval flow

## Task Commits

| Task | Name | Commit |
|------|------|--------|
| 1-3 | Batch listing implementation | e9a1db9 |

## What Was Built

### Batch Endpoints (`src/api/listing_routes.py`)

- **POST /api/listings/batch** - Start batch listing from product IDs
  - Input: `{product_ids: list[str], stagger_enabled: bool = true}`
  - Returns: `{batch_id, total, completed, current_index, listings[], next_available_time}`

- **GET /api/listings/batch/{batch_id}** - Get batch status
  - Returns: `{batch_id, total, completed, current_index, status, listings[], next_available_time}`

- **POST /api/listings/batch/{batch_id}/approve** - Approve current, proceed to next
  - Publishes current listing, applies stagger delay, returns next listing
  - Returns: `{success, current_listing, next_listing, next_available_time}`

- **POST /api/listings/batch/{batch_id}/edit** - Edit current listing
  - Input: `{title?, description?, tags?, price?}`
  - Returns: `{success, listing}`

- **DELETE /api/listings/batch/{batch_id}** - Cancel batch

### Batch State Management

- In-memory storage with `_batch_storage` dict
- Tracks: batch_id, product_ids, listings[], current_index, status, stagger_enabled, stagger_schedule, last_published, next_available_time

### Stagger Integration

- Uses `calculate_stagger_delay()` to compute delays between publishes
- Uses `get_stagger_schedule()` to pre-calculate all publish times
- Check on approve: if `now < next_available_time`, returns wait message

## Verification

- ✓ `python -c "from src.api.listing_routes import router; paths = [r.path for r in router.routes]; print('batch' in str(paths).lower())"` → True
- ✓ `python -c "from src.api.listing_routes import BatchListingItem, BatchListingCreateRequest, BatchListingResponse, BatchStatusResponse; print('OK')"` → OK
- ✓ `python -c "from src.compliance.stagger import calculate_stagger_delay; from datetime import timedelta; d = calculate_stagger_delay(1); print(d > timedelta(0))"` → True

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

- Used in-memory storage for batch state (would use DB in production)
- Stagger delay: 24 hours between listings (per D-12 from 03-04)
- Demo mode: listings marked as "active" without Etsy API calls

## Issues Encountered

None

## Next Phase Readiness

- Batch listing endpoints ready for integration with frontend
- Review checkpoint flow implemented (user approves, next listing shown)
- Stagger delays applied between publishes
- Ready for 03-06 (listing publishing workflow) if applicable

---

*Phase: 03-listing-creation*
*Completed: 2026-03-27*