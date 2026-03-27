# Phase 5: Analytics & Measurement - Research

**Gathered:** 2026-03-27
**Phase:** 05-analytics-measurement

---

## User Constraints

**From ROADMAP.md:**
- Depends on: Phase 3 (Listing Creation)
- Requirements: AN-01
- UI hint: yes

**No CONTEXT.md available** — planning from requirements only.

---

## Phase Description

**Goal:** Track listing performance and enable data-driven validation

**Success Criteria (from ROADMAP.md):**
1. User can view dashboard showing listing views, favorites, and sales
2. System attributes sales to specific listings and time periods
3. User can compare performance across multiple listings
4. System surfaces insights (best performing tags, optimal pricing)

---

## Standard Stack

### Dashboard Framework Options

| Framework | Pros | Cons | Recommendation |
|-----------|------|------|----------------|
| **Streamlit** | Fastest dev, great widgets, Python-only | Limited customization, no multi-page routing by default | **RECOMMENDED** for MVP |
| Dash (Plotly) | Full flexibility, great charts | More verbose, steeper learning curve | Alternative |
| Panel | Good for complex apps | Less popular, fewer resources | Skip |
| FastAPI + Custom HTML/JS | Full control, aligns with project stack | More dev time | Phase 3+ later |

**Recommendation:** Use **Streamlit** for MVP analytics dashboard. Aligns with Python-only stack, fastest time-to-value, excellent data visualization widgets.

### Data Visualization

- **Streamlit native** — `st.metric`, `st.bar_chart`, `st.line_chart` for basic metrics
- **Plotly** — For interactive charts (included with Streamlit)
- **Altair** — Alternative, good for simple visualizations

### Storage

- Continue with SQLite (existing from Phase 1)
- Add analytics tables for listing performance data

---

## Architecture Patterns

### Dashboard Structure

```
/analytics
  /overview     # Main dashboard with key metrics
  /listings     # Per-listing performance
  /comparison   # Multi-listing comparison
  /insights     # AI-generated insights
```

### Data Flow

1. Etsy API (or manual input) → Analytics data collection
2. Data stored in SQLite (analytics_events table)
3. Dashboard queries aggregated metrics
4. Insights generated from trend analysis

### Key Components

| Component | Purpose |
|-----------|---------|
| `src/analytics/collector.py` | Fetch/store Etsy analytics data |
| `src/analytics/aggregator.py` | Compute metrics (views, favorites, sales) |
| `src/analytics/insights.py` | Generate performance insights |
| `streamlit/app.py` | Main dashboard UI |

---

## Don't Hand-Roll

- **Charts** — Use Streamlit/Plotly built-ins, not custom D3.js
- **Data tables** — Use Streamlit `st.dataframe` with sorting/filtering
- **Authentication** — Reuse existing FastAPI auth patterns

---

## Common Pitfalls

### Etsy API Limitations

**Issue:** Etsy Open API has limited analytics endpoints.
**Mitigation:** 
- Focus on available data (listings, orders)
- Manual import option for seller stats
- Track internal attribution for sales made through the system

### Data Freshness

**Issue:** Analytics data becomes stale quickly
**Mitigation:**
- Show "last updated" timestamp
- Add refresh button for manual refresh
- Consider background job for periodic sync

---

## Validation Architecture

**How to verify analytics work correctly:**

| Verification | Method |
|--------------|--------|
| Dashboard loads | HTTP GET / returns 200 |
| Metrics display | Assert views/favorites/sales > 0 in test |
| Attribution works | Link sale to listing via order ID |
| Comparison works | Sort multiple listings by metric |
| Insights generate | Check insight text is non-empty |

---

## Code Examples

### Streamlit Dashboard Pattern

```python
import streamlit as st

st.title("Analytics Dashboard")

# Metrics row
col1, col2, col3 = st.columns(3)
col1.metric("Views", 1234)
col2.metric("Favorites", 56)
col3.metric("Sales", 12)

# Chart
st.line_chart(data)
```

### Analytics Data Collection

```python
def collect_listing_stats(listing_id: str) -> dict:
    # Fetch from Etsy API or database
    return {"views": x, "favorites": y, "sales": z}
```

---

## Confidence Level

**MEDIUM** — Dashboard frameworks well-understood. Etsy API limitations require verification.

---

## Next Steps

1. Create analytics module with collector, aggregator, insights
2. Build Streamlit dashboard with 4 views
3. Wire to existing FastAPI backend for data
4. Test with mock data, then real Etsy data

---

*Research: 05-analytics-measurement*
*Generated: 2026-03-27*