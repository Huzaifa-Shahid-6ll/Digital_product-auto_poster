"""Insights page - AI-generated performance recommendations.

Displays:
- Best performing tags list
- Optimal pricing recommendations
- Performance trends and predictions
- Refresh button to regenerate

Note: Full AI insights require Attribution & Insights plan (05-03).
This page shows placeholder insights until Plan 03 is complete.
"""

import streamlit as st
from datetime import datetime


def render_page(start_date: datetime, end_date: datetime):
    """Render the insights page.

    Args:
        start_date: Start of date range.
        end_date: End of date range.
    """
    try:
        from src.analytics.insights import InsightsEngine

        # Try to load AI insights
        try:
            engine = InsightsEngine()
            insights = engine.generate_insights(listing_ids=[])

            if insights:
                # Display insights
                st.subheader("💡 AI-Generated Insights")

                for insight in insights:
                    with st.expander(f"📌 {insight.title}", expanded=True):
                        st.markdown(insight.description)

                        if insight.listing_ids:
                            st.caption(f"Related listings: {', '.join(insight.listing_ids[:3])}")

                # Refresh button
                if st.button("🔄 Regenerate Insights"):
                    st.rerun()
            else:
                show_placeholder_insights()

        except ImportError:
            show_placeholder_insights()

    except ImportError as e:
        show_placeholder_insights()
    except Exception as e:
        show_placeholder_insights()


def show_placeholder_insights():
    """Show placeholder insights when AI module is not available."""
    st.info(
        "AI-powered insights will be available after completing Plan 05-03 "
        "(Attribution & Insights)."
    )

    st.markdown("---")
    st.subheader("💡 What's Coming")

    st.markdown("""
    ### Expected Insights
    
    Once the Attribution & Insights module is complete, you'll see:
    
    1. **Tag Performance** - Which tags drive the most views and sales
    2. **Pricing Recommendations** - Optimal price points based on performance
    3. **Trend Analysis** - Performance predictions and seasonal patterns
    4. **Timing Insights** - Best times to list and promote products
    
    ### How It Works
    
    The AI analyzes your listing metrics and generates actionable recommendations
    using OpenAI's structured output. Insights are cached and can be regenerated
    on demand.
    """)

    # Show basic metrics-based insights if data exists
    try:
        from src.analytics.aggregator import get_all_listings_with_metrics

        listings = get_all_listings_with_metrics()

        if listings:
            st.markdown("---")
            st.subheader("📊 Quick Analysis")

            # Find top performer
            top_listing = max(listings, key=lambda l: l.sales)

            col1, col2 = st.columns(2)

            with col1:
                st.metric("🏆 Top Performer", top_listing.listing_id[:12] + "...")

            with col2:
                st.metric("💰 Total Sales", f"{sum(l.sales for l in listings)}")

            # Conversion insights
            performers = [l for l in listings if l.views > 0]
            if performers:
                avg_conversion = sum(l.sales / l.views for l in performers) / len(performers)
                st.metric("📈 Avg Conversion Rate", f"{avg_conversion * 100:.2f}%")

    except Exception:
        pass


if __name__ == "__main__":
    from datetime import timedelta

    today = datetime.now()
    render_page(start_date=today - timedelta(days=30), end_date=today)
