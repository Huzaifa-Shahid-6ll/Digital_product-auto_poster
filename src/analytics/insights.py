"""AI-powered performance insights generator.

Provides InsightsEngine class with:
- generate_insights: Generate AI recommendations for listings
- find_best_tags: Identify top-performing tags
- suggest_pricing: Recommend optimal pricing based on performance

Uses OpenAI with structured output per patterns from niche_research/analyzer.py.
"""

import json
import logging
import os
import uuid
from datetime import datetime
from typing import List, Optional

from openai import AsyncOpenAI

from src.analytics.schemas import Insight
from src.analytics.aggregator import get_all_listings_with_metrics

logger = logging.getLogger(__name__)


class InsightsEngine:
    """Engine for generating AI-powered performance insights."""

    def __init__(self, client: Optional[AsyncOpenAI] = None):
        """Initialize the insights engine.

        Args:
            client: Optional OpenAI client. If not provided, uses default.
        """
        self.client = client

    def _get_client(self) -> AsyncOpenAI:
        """Get or create OpenAI client.

        Returns:
            Configured AsyncOpenAI client.

        Raises:
            ValueError: If OpenAI API key is not configured.
        """
        if self.client:
            return self.client

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY.")

        return AsyncOpenAI(api_key=api_key)

    def generate_insights(self, listing_ids: List[str]) -> List[Insight]:
        """Generate AI-powered insights for listings.

        Uses OpenAI with structured JSON output to generate
        performance recommendations.

        Args:
            listing_ids: List of listing IDs to analyze. Empty = all listings.

        Returns:
            List of Insight objects.
        """
        # Get metrics data
        all_listings = get_all_listings_with_metrics()

        if not all_listings:
            return []

        # Filter to requested listings if specified
        if listing_ids:
            listings = [l for l in all_listings if l.listing_id in listing_ids]
        else:
            listings = all_listings

        if not listings:
            return []

        # Prepare data for AI
        metrics_summary = [
            {
                "listing_id": l.listing_id,
                "views": l.views,
                "favorites": l.favorites,
                "sales": l.sales,
                "conversion_rate": (l.sales / l.views * 100) if l.views > 0 else 0,
            }
            for l in listings
        ]

        # Try to generate AI insights
        try:
            client = self._get_client()

            system_prompt = """You are a digital product analytics expert.
Analyze the listing performance data and generate actionable insights.
For each insight, provide:
- insight_type: tag_performance, pricing, trend, or timing
- title: Short headline
- description: Detailed recommendation
- listing_ids: Related listing IDs

Generate 2-4 insights based on the data."""

            user_prompt = f"""Analyze these listing metrics and generate insights:
{json.dumps(metrics_summary, indent=2)}

Provide insights in JSON format:
{{
    "insights": [
        {{
            "insight_type": "tag_performance|pricing|trend|timing",
            "title": "...",
            "description": "...",
            "listing_ids": ["listing_id_1"]
        }}
    ]
}}
"""

            import asyncio

            # Run async call in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                response = loop.run_until_complete(
                    client.chat.completions.create(
                        model="gpt-4o",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.7,
                    )
                )

                content = response.choices[0].message.content
                if not content:
                    return []

                data = json.loads(content)

                insights = []
                for insight_data in data.get("insights", []):
                    insights.append(
                        Insight(
                            id=str(uuid.uuid4()),
                            insight_type=insight_data.get("insight_type", "trend"),
                            title=insight_data.get("title", "Insight"),
                            description=insight_data.get("description", ""),
                            listing_ids=insight_data.get("listing_ids", []),
                            created_at=datetime.utcnow(),
                        )
                    )

                return insights

            finally:
                loop.close()

        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            # Return empty list - caller should handle gracefully
            return []

    def find_best_tags(self, listing_ids: List[str]) -> List[dict]:
        """Find best performing tags based on listing performance.

        Args:
            listing_ids: List of listing IDs to analyze.

        Returns:
            List of tag performance dictionaries.
        """
        # MVP: This would require tags stored with listings
        # For now, return placeholder
        return [
            {
                "tag": "planner",
                "avg_views": 100,
                "avg_sales": 5,
                "recommendation": "High-performing, consider more products",
            }
        ]

    def suggest_pricing(self, listing_id: str) -> dict:
        """Suggest optimal pricing for a listing.

        Args:
            listing_id: The listing ID to analyze.

        Returns:
            Dict with pricing recommendation.
        """
        # Get metrics for this listing
        listings = get_all_listings_with_metrics()
        listing = next((l for l in listings if l.listing_id == listing_id), None)

        if not listing:
            return {
                "listing_id": listing_id,
                "current_price": None,
                "suggested_price_range": None,
                "rationale": "No performance data available",
            }

        # Simple pricing logic based on conversion
        if listing.sales > 0 and listing.views > 0:
            conversion = listing.sales / listing.views

            # Higher conversion might suggest price is right
            # Lower conversion might suggest testing lower prices
            if conversion > 0.05:
                suggested = "Consider testing slightly higher prices"
                range_low, range_high = 1.1, 1.3
            elif conversion > 0.02:
                suggested = "Price seems optimal"
                range_low, range_high = 0.95, 1.1
            else:
                suggested = "Consider testing lower prices"
                range_low, range_high = 0.7, 0.95
        else:
            suggested = "Need more data to recommend pricing"
            range_low, range_high = 0.8, 1.2

        return {
            "listing_id": listing_id,
            "views": listing.views,
            "sales": listing.sales,
            "conversion_rate": (listing.sales / listing.views * 100) if listing.views > 0 else 0,
            "suggested_price_multiplier": f"{range_low}x - {range_high}x",
            "recommendation": suggested,
        }


# Convenience function
def get_insights_engine() -> InsightsEngine:
    """Get or create insights engine instance.

    Returns:
        InsightsEngine instance.
    """
    return InsightsEngine()
