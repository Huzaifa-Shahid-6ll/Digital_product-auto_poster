"""Analytics module for tracking listing performance and metrics.

This module provides:
- Pydantic schemas for analytics data models
- Data collectors for fetching metrics from Etsy
- Aggregators for computing metrics over time periods
- Attribution engine for linking sales to listings
- AI-powered insights generation

Per AN-01: Track listing performance and enable data-driven validation.
"""

from src.analytics.schemas import (
    AnalyticsEvent,
    AttributionRecord,
    Insight,
    ListingMetrics,
    TimeSeriesData,
)

__all__ = [
    "ListingMetrics",
    "AnalyticsEvent",
    "TimeSeriesData",
    "AttributionRecord",
    "Insight",
]
