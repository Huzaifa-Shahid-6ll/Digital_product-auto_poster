"""Pydantic schemas for analytics data.

Defines structured data models for:
- ListingMetrics: Views, favorites, and sales for a listing
- AnalyticsEvent: Individual events (views, clicks, purchases)
- TimeSeriesData: Time-bucketed metric data for charts
- AttributionRecord: Sales attribution to listings

Used for API response formatting and internal data validation.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ListingMetrics(BaseModel):
    """Metrics for a single listing.

    Attributes:
        listing_id: Unique identifier for the listing.
        views: Total number of views.
        favorites: Total number of favorites/likes.
        sales: Total number of sales.
        period: Time period these metrics cover (day, week, month).
        start_date: Start of the measurement period.
        end_date: End of the measurement period.
    """

    listing_id: str = Field(..., description="Unique identifier for the listing")
    views: int = Field(default=0, ge=0, description="Total number of views")
    favorites: int = Field(default=0, ge=0, description="Total number of favorites")
    sales: int = Field(default=0, ge=0, description="Total number of sales")
    period: Literal["day", "week", "month", "all"] = Field(
        default="all", description="Time period these metrics cover"
    )
    start_date: Optional[datetime] = Field(
        default=None, description="Start of the measurement period"
    )
    end_date: Optional[datetime] = Field(default=None, description="End of the measurement period")


class AnalyticsEvent(BaseModel):
    """A single analytics event.

    Attributes:
        id: Unique event identifier.
        listing_id: Associated listing ID.
        event_type: Type of event (view, favorite, click, purchase).
        timestamp: When the event occurred.
        metadata: Additional event data (source, referrer, etc.).
    """

    id: str = Field(..., description="Unique event identifier")
    listing_id: str = Field(..., description="Associated listing ID")
    event_type: Literal["view", "favorite", "click", "purchase"] = Field(
        ..., description="Type of analytics event"
    )
    timestamp: datetime = Field(..., description="When the event occurred")
    metadata: dict[str, str] = Field(default_factory=dict, description="Additional event metadata")


class TimeSeriesData(BaseModel):
    """Time-bucketed metric data for charting.

    Attributes:
        date: The date/timestamp for this data point.
        value: The metric value.
        metric_type: Type of metric (views, favorites, sales).
    """

    date: datetime = Field(..., description="Date for this data point")
    value: float = Field(..., ge=0, description="Metric value")
    metric_type: Literal["views", "favorites", "sales"] = Field(..., description="Type of metric")


class AttributionRecord(BaseModel):
    """Record linking a sale to a listing and attribution source.

    Attributes:
        sale_id: Unique sale/order identifier.
        listing_id: The listing that generated this sale.
        timestamp: When the sale occurred.
        source: Attribution source (direct, search, campaign).
        revenue: Sale amount.
    """

    sale_id: str = Field(..., description="Unique sale/order identifier")
    listing_id: str = Field(..., description="Listing that generated this sale")
    timestamp: datetime = Field(..., description="When the sale occurred")
    source: Literal["direct", "search", "campaign", "unknown"] = Field(
        default="unknown", description="Attribution source"
    )
    revenue: float = Field(default=0.0, ge=0, description="Sale amount")


class Insight(BaseModel):
    """AI-generated performance insight.

    Attributes:
        id: Unique insight identifier.
        insight_type: Type of insight (tag_performance, pricing, trend).
        title: Short title/headline.
        description: Detailed explanation.
        listing_ids: Related listings.
        created_at: When the insight was generated.
    """

    id: str = Field(..., description="Unique insight identifier")
    insight_type: Literal["tag_performance", "pricing", "trend", "timing"] = Field(
        ..., description="Type of insight"
    )
    title: str = Field(..., description="Short insight title")
    description: str = Field(..., description="Detailed explanation")
    listing_ids: list[str] = Field(default_factory=list, description="Related listing IDs")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When insight was generated"
    )
