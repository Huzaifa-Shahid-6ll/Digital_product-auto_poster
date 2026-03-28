"""Listings page - per-listing performance details.

Displays:
- DataFrame table of all listings with metrics
- Sorting and filtering
- Click to view individual listing details
"""

import streamlit as st
from datetime import datetime


def render_page(start_date: datetime, end_date: datetime):
    """Render the listings page.

    Args:
        start_date: Start of date range.
        end_date: End of date range.
    """
    try:
        from src.analytics.aggregator import get_all_listings_with_metrics
        from src.analytics.collector import collect_analytics_events

        # Fetch all listings with metrics
        listings = get_all_listings_with_metrics()

        if not listings:
            st.info(
                "No listings with analytics data yet. "
                "Connect your Etsy shop and create listings to track performance."
            )
            return

        # Convert to DataFrame for display
        import pandas as pd

        data = []
        for listing in listings:
            data.append(
                {
                    "Listing ID": listing.listing_id,
                    "Views": listing.views,
                    "Favorites": listing.favorites,
                    "Sales": listing.sales,
                    "Conversion Rate": (
                        f"{(listing.sales / listing.views * 100):.2f}%"
                        if listing.views > 0
                        else "0.00%"
                    ),
                }
            )

        df = pd.DataFrame(data)

        # Sorting controls
        st.subheader("📋 All Listings")

        sort_col = st.selectbox(
            "Sort by",
            ["Views", "Favorites", "Sales", "Conversion Rate"],
            index=2,
        )

        # Sort the dataframe
        if sort_col == "Views":
            df = df.sort_values("Views", ascending=False)
        elif sort_col == "Favorites":
            df = df.sort_values("Favorites", ascending=False)
        elif sort_col == "Sales":
            df = df.sort_values("Sales", ascending=False)
        else:
            # Sort by conversion rate - need to extract numeric value
            df["_conv_num"] = df["Conversion Rate"].str.rstrip("%").astype(float)
            df = df.sort_values("_conv_num", ascending=False)
            df = df.drop("_conv_num", axis=1)

        # Display as interactive table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        # Listing detail section
        st.markdown("---")
        st.subheader("🔍 Listing Details")

        # Select a listing to view details
        listing_ids = [l.listing_id for l in listings]
        selected_id = st.selectbox(
            "Select a listing to view details",
            listing_ids,
        )

        if selected_id:
            # Get metrics for selected listing
            from src.analytics.aggregator import aggregate_listing_metrics

            metrics = aggregate_listing_metrics(
                listing_id=selected_id,
                start_date=start_date,
                end_date=end_date,
            )

            # Display metrics
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Views", f"{metrics.views:,}")

            with col2:
                st.metric("Favorites", f"{metrics.favorites:,}")

            with col3:
                st.metric("Sales", f"{metrics.sales:,}")

            # Get recent events
            events = collect_analytics_events(
                listing_id=selected_id,
                start_date=start_date,
                end_date=end_date,
            )

            if events:
                st.markdown("#### Recent Events")
                events_data = []
                for event in events[-20:]:  # Last 20 events
                    events_data.append(
                        {
                            "Type": event.event_type,
                            "Timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M"),
                        }
                    )

                events_df = pd.DataFrame(events_data)
                st.dataframe(
                    events_df,
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No events recorded for this listing in the selected period.")

    except ImportError as e:
        st.error(f"Analytics module not available: {e}")
        st.info("Run the analytics backend first to see metrics.")
    except Exception as e:
        st.error(f"Error loading listings: {e}")
        st.info("Make sure the analytics backend is running.")


if __name__ == "__main__":
    from datetime import timedelta

    today = datetime.now()
    render_page(start_date=today - timedelta(days=30), end_date=today)
