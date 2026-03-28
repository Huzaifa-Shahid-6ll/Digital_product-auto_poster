"""Comparison page - side-by-side listing comparison.

Displays:
- Multi-select listing picker
- Side-by-side metrics comparison
- Bar chart comparison
- Sort by any metric
"""

import streamlit as st
from datetime import datetime


def render_page(start_date: datetime, end_date: datetime):
    """Render the comparison page.

    Args:
        start_date: Start of date range.
        end_date: End of date range.
    """
    try:
        from src.analytics.aggregator import get_all_listings_with_metrics

        # Fetch all listings with metrics
        listings = get_all_listings_with_metrics()

        if not listings:
            st.info(
                "No listings with analytics data yet. "
                "Connect your Etsy shop and create listings to compare performance."
            )
            return

        # Multi-select for listings
        listing_options = [l.listing_id for l in listings]
        selected_listings = st.multiselect(
            "Select listings to compare",
            listing_options,
            default=listing_options[:3] if len(listing_options) >= 3 else listing_options,
        )

        if not selected_listings:
            st.warning("Please select at least one listing to compare.")
            return

        # Get metrics for selected listings
        selected_metrics = [l for l in listings if l.listing_id in selected_listings]

        # Convert to comparison data
        import pandas as pd

        data = []
        for m in selected_metrics:
            data.append(
                {
                    "Listing ID": m.listing_id,
                    "Views": m.views,
                    "Favorites": m.favorites,
                    "Sales": m.sales,
                    "Conversion Rate": ((m.sales / m.views * 100) if m.views > 0 else 0),
                }
            )

        df = pd.DataFrame(data)

        # Display metrics comparison
        st.subheader("⚖️ Metrics Comparison")

        # Metrics cards for each listing
        cols = st.columns(len(selected_listings))

        for idx, listing_id in enumerate(selected_listings):
            with cols[idx]:
                m = next(m for m in selected_metrics if m.listing_id == listing_id)
                st.markdown(f"**{listing_id[:8]}...**")
                st.metric("Views", f"{m.views:,}")
                st.metric("Favorites", f"{m.favorites:,}")
                st.metric("Sales", f"{m.sales:,}")

        # Bar chart comparison
        st.markdown("---")
        st.subheader("📊 Visual Comparison")

        # Prepare chart data
        chart_data = pd.DataFrame(
            {
                "Listing": [l[:8] + "..." for l in selected_listings],
                "Views": [m.views for m in selected_metrics],
                "Favorites": [m.favorites for m in selected_metrics],
                "Sales": [m.sales for m in selected_metrics],
            }
        ).set_index("Listing")

        # Chart type selector
        chart_type = st.radio(
            "Chart type",
            ["Bar chart", "Normalized"],
            horizontal=True,
        )

        if chart_type == "Bar chart":
            st.bar_chart(chart_data)
        else:
            # Normalized (percentage of total)
            totals = chart_data.sum()
            normalized = chart_data.div(totals) * 100
            st.bar_chart(normalized)

        # Sort by metric
        st.markdown("---")
        st.subheader("🏆 Rankings")

        sort_by = st.selectbox(
            "Rank by",
            ["Views", "Favorites", "Sales", "Conversion Rate"],
        )

        if sort_by == "Views":
            ranked_df = df.sort_values("Views", ascending=False)
        elif sort_by == "Favorites":
            ranked_df = df.sort_values("Favorites", ascending=False)
        elif sort_by == "Sales":
            ranked_df = df.sort_values("Sales", ascending=False)
        else:
            ranked_df = df.sort_values("Conversion Rate", ascending=False)

        # Add rank column
        ranked_df.insert(0, "Rank", range(1, len(ranked_df) + 1))

        st.dataframe(
            ranked_df,
            use_container_width=True,
            hide_index=True,
        )

    except ImportError as e:
        st.error(f"Analytics module not available: {e}")
        st.info("Run the analytics backend first to see metrics.")
    except Exception as e:
        st.error(f"Error loading comparison: {e}")
        st.info("Make sure the analytics backend is running.")


if __name__ == "__main__":
    from datetime import timedelta

    today = datetime.now()
    render_page(start_date=today - timedelta(days=30), end_date=today)
