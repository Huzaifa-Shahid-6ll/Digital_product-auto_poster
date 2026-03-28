"""Overview page - aggregate metrics across all listings.

Displays:
- Summary metric cards (total views, favorites, sales)
- Line chart for trends over time
- Key performance indicators
"""

import streamlit as st
from datetime import datetime


def render_page(start_date: datetime, end_date: datetime):
    """Render the overview page.

    Args:
        start_date: Start of date range.
        end_date: End of date range.
    """
    # Try to import analytics - show placeholder if not available
    try:
        from src.analytics.aggregator import get_overview_metrics, aggregate_time_series

        # Fetch overview metrics
        metrics = get_overview_metrics(start_date=start_date, end_date=end_date)

        # Top-level metrics
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Views",
                f"{metrics['total_views']:,}",
                delta=None,
            )

        with col2:
            st.metric(
                "Total Favorites",
                f"{metrics['total_favorites']:,}",
                delta=None,
            )

        with col3:
            st.metric(
                "Total Sales",
                f"{metrics['total_sales']:,}",
                delta=None,
            )

        with col4:
            st.metric(
                "Active Listings",
                f"{metrics['listing_count']}",
                delta=None,
            )

        # Chart section
        st.markdown("---")
        st.subheader("📈 Trends Over Time")

        # Get time series data for charts
        listing_ids = []  # Empty means all listings
        try:
            from src.analytics.collector import get_all_listing_ids

            listing_ids = get_all_listing_ids()
        except Exception:
            pass

        if listing_ids:
            # Get views time series
            views_data = aggregate_time_series(
                listing_ids=listing_ids,
                metric="views",
                start_date=start_date,
                end_date=end_date,
            )

            if views_data:
                # Convert to DataFrame for chart
                import pandas as pd

                chart_data = pd.DataFrame([{"date": d.date, "views": d.value} for d in views_data])

                if not chart_data.empty:
                    st.line_chart(chart_data.set_index("date"))
                else:
                    st.info(
                        "Not enough data for trends chart yet. Add some listings to see trends."
                    )
            else:
                st.info(
                    "No trend data available yet. Start tracking listings to see performance trends."
                )
        else:
            # No listings yet
            st.info(
                "No listings with analytics data yet. "
                "Connect your Etsy shop and create listings to see metrics here."
            )

        # Performance summary
        st.markdown("---")
        st.subheader("📊 Performance Summary")

        # Calculate conversion rate if we have data
        if metrics["total_views"] > 0:
            conversion_rate = (metrics["total_sales"] / metrics["total_views"]) * 100
            favorites_rate = (metrics["total_favorites"] / metrics["total_views"]) * 100

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Conversion Rate",
                    f"{conversion_rate:.2f}%",
                    delta="Sales / Views",
                )

            with col2:
                st.metric(
                    "Favorites Rate",
                    f"{favorites_rate:.2f}%",
                    delta="Favorites / Views",
                )
        else:
            st.info("Not enough data to calculate rates yet.")

    except ImportError as e:
        st.error(f"Analytics module not available: {e}")
        st.info("Run the analytics backend first to see metrics.")
    except Exception as e:
        st.error(f"Error loading metrics: {e}")
        st.info("Make sure the analytics backend is running.")


if __name__ == "__main__":
    # Allow direct testing
    from datetime import timedelta

    today = datetime.now()
    render_page(start_date=today - timedelta(days=30), end_date=today)
