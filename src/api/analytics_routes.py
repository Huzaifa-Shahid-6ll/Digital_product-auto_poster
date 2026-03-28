"""API routes for analytics endpoints.

REST endpoints for:
- GET /api/analytics/overview - Aggregate metrics
- GET /api/analytics/listings - Listing performance
- GET /api/analytics/attribution - Sales attribution
- GET /api/analytics/insights - AI insights

Mounted at /api/analytics in main app.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.analytics.aggregator import (
    aggregate_listing_metrics,
    aggregate_time_series,
    get_all_listings_with_metrics,
    get_overview_metrics,
)
from src.analytics.attribution import get_attribution_engine
from src.analytics.insights import get_insights_engine
from src.analytics.schemas import AttributionRecord, ListingMetrics, TimeSeriesData

# Create router
router = APIRouter(tags=["analytics"])


# Request/Response models


class OverviewResponse(BaseModel):
    """Response model for overview endpoint."""

    total_views: int
    total_favorites: int
    total_sales: int
    listing_count: int


class ListingMetricsResponse(BaseModel):
    """Response model for listing metrics."""

    listing_id: str
    views: int
    favorites: int
    sales: int
    period: str


class TimeSeriesRequest(BaseModel):
    """Request model for time series data."""

    listing_ids: List[str] = Field(..., description="List of listing IDs")
    metric: str = Field(..., description="Metric type: views, favorites, sales")
    start_date: str = Field(..., description="Start date ISO string")
    end_date: str = Field(..., description="End date ISO string")


class AttributionResponse(BaseModel):
    """Response model for attribution endpoint."""

    sale_id: str
    listing_id: str
    timestamp: str
    source: str
    revenue: float


class InsightsResponse(BaseModel):
    """Response model for insights endpoint."""

    insights: List[dict]
    generated_at: str


# Routes


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    start_date: Optional[str] = Query(None, description="Start date (ISO)"),
    end_date: Optional[str] = Query(None, description="End date (ISO)"),
) -> OverviewResponse:
    """Get aggregate metrics across all listings.

    Args:
        start_date: Optional start date.
        end_date: Optional end date.

    Returns:
        OverviewResponse with aggregate metrics.
    """
    try:
        # Parse dates if provided
        start = None
        end = None

        if start_date:
            start = datetime.fromisoformat(start_date)
        if end_date:
            end = datetime.fromisoformat(end_date)

        metrics = get_overview_metrics(start_date=start, end_date=end)

        return OverviewResponse(
            total_views=metrics["total_views"],
            total_favorites=metrics["total_favorites"],
            total_sales=metrics["total_sales"],
            listing_count=metrics["listing_count"],
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings", response_model=List[ListingMetricsResponse])
async def get_listings() -> List[ListingMetricsResponse]:
    """Get performance metrics for all listings.

    Returns:
        List of ListingMetricsResponse for each listing.
    """
    try:
        listings = get_all_listings_with_metrics()

        return [
            ListingMetricsResponse(
                listing_id=l.listing_id,
                views=l.views,
                favorites=l.favorites,
                sales=l.sales,
                period=l.period,
            )
            for l in listings
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/listings/{listing_id}", response_model=ListingMetricsResponse)
async def get_listing_metrics(
    listing_id: str,
    period: str = Query("all", description="Period: day, week, month, all"),
    start_date: Optional[str] = Query(None, description="Start date (ISO)"),
    end_date: Optional[str] = Query(None, description="End date (ISO)"),
) -> ListingMetricsResponse:
    """Get metrics for a specific listing.

    Args:
        listing_id: The listing ID.
        period: Time period.
        start_date: Optional start date.
        end_date: Optional end date.

    Returns:
        ListingMetricsResponse with listing metrics.
    """
    try:
        # Parse dates if provided
        start = None
        end = None

        if start_date:
            start = datetime.fromisoformat(start_date)
        if end_date:
            end = datetime.fromisoformat(end_date)

        metrics = aggregate_listing_metrics(
            listing_id=listing_id,
            period=period,
            start_date=start,
            end_date=end,
        )

        return ListingMetricsResponse(
            listing_id=metrics.listing_id,
            views=metrics.views,
            favorites=metrics.favorites,
            sales=metrics.sales,
            period=metrics.period,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeseries")
async def get_time_series(
    listing_ids: str = Query(..., description="Comma-separated listing IDs"),
    metric: str = Query(..., description="Metric type: views, favorites, sales"),
    start_date: str = Query(..., description="Start date (ISO)"),
    end_date: str = Query(..., description="End date (ISO)"),
) -> List[dict]:
    """Get time series data for listings.

    Args:
        listing_ids: Comma-separated list of listing IDs.
        metric: Metric type.
        start_date: Start date.
        end_date: End date.

    Returns:
        List of time series data points.
    """
    try:
        listing_id_list = listing_ids.split(",")
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)

        data = aggregate_time_series(
            listing_ids=listing_id_list,
            metric=metric,
            start_date=start,
            end_date=end,
        )

        return [
            {
                "date": d.date.isoformat(),
                "value": d.value,
                "metric_type": d.metric_type,
            }
            for d in data
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attribution/{listing_id}", response_model=List[AttributionResponse])
async def get_listing_attribution(listing_id: str) -> List[AttributionResponse]:
    """Get attribution records for a listing.

    Args:
        listing_id: The listing ID.

    Returns:
        List of AttributionResponse.
    """
    try:
        engine = get_attribution_engine()
        records = engine.get_listing_attribution(listing_id)

        return [
            AttributionResponse(
                sale_id=r.sale_id,
                listing_id=r.listing_id,
                timestamp=r.timestamp.isoformat(),
                source=r.source,
                revenue=r.revenue,
            )
            for r in records
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/attribution")
async def get_attribution_summary(
    start_date: Optional[str] = Query(None, description="Start date (ISO)"),
    end_date: Optional[str] = Query(None, description="End date (ISO)"),
) -> dict:
    """Get attribution summary for a time period.

    Args:
        start_date: Optional start date.
        end_date: Optional end date.

    Returns:
        Dict with attribution summary.
    """
    try:
        start = None
        end = None

        if start_date:
            start = datetime.fromisoformat(start_date)
        if end_date:
            end = datetime.fromisoformat(end_date)

        engine = get_attribution_engine()
        summary = engine.get_time_period_attribution(start, end)

        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/attribution")
async def create_attribution(
    sale_id: str = Query(..., description="Sale ID"),
    listing_id: str = Query(..., description="Listing ID"),
    source: str = Query("unknown", description="Attribution source"),
    revenue: float = Query(0.0, description="Sale revenue"),
) -> AttributionResponse:
    """Create an attribution record.

    Args:
        sale_id: Sale ID.
        listing_id: Listing ID.
        source: Attribution source.
        revenue: Sale revenue.

    Returns:
        AttributionResponse with created record.
    """
    try:
        engine = get_attribution_engine()
        record = engine.attribute_sale(
            sale_id=sale_id,
            listing_id=listing_id,
            source=source,
            revenue=revenue,
        )

        return AttributionResponse(
            sale_id=record.sale_id,
            listing_id=record.listing_id,
            timestamp=record.timestamp.isoformat(),
            source=record.source,
            revenue=record.revenue,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    listing_ids: Optional[str] = Query(
        None, description="Comma-separated listing IDs (empty = all)"
    ),
) -> InsightsResponse:
    """Get AI-generated insights for listings.

    Args:
        listing_ids: Optional comma-separated list of listing IDs.

    Returns:
        InsightsResponse with generated insights.
    """
    try:
        engine = get_insights_engine()

        listing_id_list = []
        if listing_ids:
            listing_id_list = listing_ids.split(",")

        insights = engine.generate_insights(listing_id_list)

        return InsightsResponse(
            insights=[
                {
                    "id": i.id,
                    "insight_type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "listing_ids": i.listing_ids,
                    "created_at": i.created_at.isoformat(),
                }
                for i in insights
            ],
            generated_at=datetime.utcnow().isoformat(),
        )

    except ValueError as e:
        # OpenAI not configured
        raise HTTPException(
            status_code=503,
            detail=f"Insights not available: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
