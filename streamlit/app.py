"""Main Streamlit dashboard application.

Provides sidebar navigation with 4 pages:
- Overview: Aggregate metrics across all listings
- Listings: Per-listing performance
- Comparison: Side-by-side comparison
- Insights: AI-generated recommendations

Uses session state for data caching.
"""

import streamlit as st
from datetime import datetime, timedelta

# Page configuration
st.set_page_config(
    page_title="Digital Product Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Session state initialization
if "data_cache" not in st.session_state:
    st.session_state.data_cache = {}

if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = None


def get_cached_data(key: str, fetch_func, ttl_seconds: int = 300):
    """Get cached data or fetch fresh data.

    Args:
        key: Cache key.
        fetch_func: Function to call if cache is stale.
        ttl_seconds: Time-to-live in seconds.

    Returns:
        Cached or fresh data.
    """
    now = datetime.now()
    cache = st.session_state.data_cache.get(key)

    if cache is None:
        # No cache - fetch data
        data = fetch_func()
        st.session_state.data_cache[key] = {"data": data, "timestamp": now}
        return data

    # Check if cache is stale
    age = (now - cache["timestamp"]).total_seconds()
    if age > ttl_seconds:
        # Cache expired - fetch fresh data
        data = fetch_func()
        st.session_state.data_cache[key] = {"data": data, "timestamp": now}
        return data

    return cache["data"]


def clear_cache():
    """Clear all cached data."""
    st.session_state.data_cache = {}
    st.session_state.last_refresh = None


# Sidebar navigation
st.sidebar.title("📊 Analytics Dashboard")

# Navigation
page = st.sidebar.radio(
    "Navigate",
    ["Overview", "Listings", "Comparison", "Insights"],
)

# Date range selector in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Date Range")

date_range = st.sidebar.selectbox(
    "Select period",
    ["Last 7 days", "Last 30 days", "Last 90 days", "All time"],
    index=1,
)

# Calculate date range
today = datetime.now()
if date_range == "Last 7 days":
    start_date = today - timedelta(days=7)
elif date_range == "Last 30 days":
    start_date = today - timedelta(days=30)
elif date_range == "Last 90 days":
    start_date = today - timedelta(days=90)
else:
    start_date = None

# Cache controls
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data"):
    clear_cache()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption("Digital Product Auto-Poster Analytics")

# Main content based on selected page
if page == "Overview":
    st.title("📈 Overview")
    st.markdown("Aggregate metrics across all your listings")
    from streamlit.pages.overview import render_page

    render_page(start_date=start_date, end_date=today)

elif page == "Listings":
    st.title("📋 Listings")
    st.markdown("Performance details for each listing")
    from streamlit.pages.listings import render_page

    render_page(start_date=start_date, end_date=today)

elif page == "Comparison":
    st.title("⚖️ Comparison")
    st.markdown("Compare performance across multiple listings")
    from streamlit.pages.comparison import render_page

    render_page(start_date=start_date, end_date=today)

elif page == "Insights":
    st.title("💡 Insights")
    st.markdown("AI-generated performance recommendations")
    from streamlit.pages.insights import render_page

    render_page(start_date=start_date, end_date=today)
