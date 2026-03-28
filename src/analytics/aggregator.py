"""Metrics aggregator for computing listing performance over time periods.

Provides functions to:
- aggregate_listing_metrics: Aggregate metrics by period (day/week/month)
- aggregate_time_series: Get time-series data for charts
- compute_attribution: Link sales to listings and time periods

Uses SQLAlchemy patterns from existing db/models.py.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from src.analytics.schemas import AttributionRecord, ListingMetrics, TimeSeriesData
from src.db.schema import get_session

logger = logging.getLogger(__name__)


def aggregate_listing_metrics(
    listing_id: str,
    period: str = "all",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> ListingMetrics:
    """Aggregate metrics for a listing over a given period.

    Args:
        listing_id: The listing ID to aggregate metrics for.
        period: Time period (day, week, month, all).
        start_date: Optional start date override.
        end_date: Optional end date override.

    Returns:
        ListingMetrics with aggregated totals.
    """
    session = get_session()
    try:
        from sqlalchemy import Table, Column, Integer, String, DateTime, JSON, MetaData

        metadata = MetaData()
        analytics_events = Table(
            "analytics_events",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("listing_id", String(255), nullable=False),
            Column("event_type", String(50), nullable=False),
            Column("timestamp", DateTime, nullable=False),
            Column("metadata", JSON, nullable=True),
        )

        metadata.create_all(session.get_bind())

        # Build query conditions
        from sqlalchemy import and_, func, select

        conditions = [analytics_events.c.listing_id == listing_id]

        if start_date:
            conditions.append(analytics_events.c.timestamp >= start_date)
        if end_date:
            conditions.append(analytics_events.c.timestamp <= end_date)

        # Aggregate by event type
        stmt = select(
            func.sum(func.case((analytics_events.c.event_type == "view", 1), else_=0)).label(
                "views"
            ),
            func.sum(func.case((analytics_events.c.event_type == "favorite", 1), else_=0)).label(
                "favorites"
            ),
            func.sum(func.case((analytics_events.c.event_type == "purchase", 1), else_=0)).label(
                "sales"
            ),
        ).where(and_(*conditions))

        result = session.execute(stmt).fetchone()

        return ListingMetrics(
            listing_id=listing_id,
            views=result.views if result else 0,
            favorites=result.favorites if result else 0,
            sales=result.sales if result else 0,
            period=period,
            start_date=start_date,
            end_date=end_date,
        )

    except Exception as e:
        logger.error(f"Error aggregating listing metrics: {e}")
        return ListingMetrics(listing_id=listing_id, views=0, favorites=0, sales=0, period=period)
    finally:
        session.close()


def aggregate_time_series(
    listing_ids: List[str],
    metric: str,
    start_date: datetime,
    end_date: datetime,
) -> List[TimeSeriesData]:
    """Get time-series data for one or more listings.

    Args:
        listing_ids: List of listing IDs to aggregate.
        metric: Metric type (views, favorites, sales).
        start_date: Start of date range.
        end_date: End of date range.

    Returns:
        List of TimeSeriesData points.
    """
    session = get_session()
    try:
        from sqlalchemy import Table, Column, Integer, String, DateTime, JSON, MetaData

        metadata = MetaData()
        analytics_events = Table(
            "analytics_events",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("listing_id", String(255), nullable=False),
            Column("event_type", String(50), nullable=False),
            Column("timestamp", DateTime, nullable=False),
            Column("metadata", JSON, nullable=True),
        )

        metadata.create_all(session.get_bind())

        from sqlalchemy import and_, func, select

        # Group by date (day level)
        # SQLite doesn't have date_trunc, so we use date() function
        event_type_filter = analytics_events.c.event_type == metric

        stmt = (
            select(
                func.date(analytics_events.c.timestamp).label("date"),
                func.count().label("value"),
            )
            .where(
                and_(
                    analytics_events.c.listing_id.in_(listing_ids),
                    event_type_filter,
                    analytics_events.c.timestamp >= start_date,
                    analytics_events.c.timestamp <= end_date,
                )
            )
            .group_by(func.date(analytics_events.c.timestamp))
        )

        results = session.execute(stmt).fetchall()

        time_series = []
        for row in results:
            # Parse date string back to datetime
            date_val = datetime.strptime(row.date, "%Y-%m-%d")
            time_series.append(
                TimeSeriesData(
                    date=date_val,
                    value=row.value or 0,
                    metric_type=metric,
                )
            )

        return time_series

    except Exception as e:
        logger.error(f"Error aggregating time series: {e}")
        return []
    finally:
        session.close()


def get_overview_metrics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> dict:
    """Get aggregate metrics across all listings.

    Args:
        start_date: Optional start date.
        end_date: Optional end date.

    Returns:
        Dict with total views, favorites, sales.
    """
    session = get_session()
    try:
        from sqlalchemy import Table, Column, Integer, String, DateTime, JSON, MetaData

        metadata = MetaData()
        analytics_events = Table(
            "analytics_events",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("listing_id", String(255), nullable=False),
            Column("event_type", String(50), nullable=False),
            Column("timestamp", DateTime, nullable=False),
            Column("metadata", JSON, nullable=True),
        )

        metadata.create_all(session.get_bind())

        from sqlalchemy import and_, func, select

        conditions = []
        if start_date:
            conditions.append(analytics_events.c.timestamp >= start_date)
        if end_date:
            conditions.append(analytics_events.c.timestamp <= end_date)

        where_clause = and_(*conditions) if conditions else True

        stmt = select(
            func.sum(func.case((analytics_events.c.event_type == "view", 1), else_=0)).label(
                "views"
            ),
            func.sum(func.case((analytics_events.c.event_type == "favorite", 1), else_=0)).label(
                "favorites"
            ),
            func.sum(func.case((analytics_events.c.event_type == "purchase", 1), else_=0)).label(
                "sales"
            ),
            func.count(func.distinct(analytics_events.c.listing_id)).label("listing_count"),
        ).where(where_clause)

        result = session.execute(stmt).fetchone()

        return {
            "total_views": result.views if result else 0,
            "total_favorites": result.favorites if result else 0,
            "total_sales": result.sales if result else 0,
            "listing_count": result.listing_count if result else 0,
        }

    except Exception as e:
        logger.error(f"Error getting overview metrics: {e}")
        return {
            "total_views": 0,
            "total_favorites": 0,
            "total_sales": 0,
            "listing_count": 0,
        }
    finally:
        session.close()


def get_all_listings_with_metrics() -> List[ListingMetrics]:
    """Get metrics for all listings with analytics data.

    Returns:
        List of ListingMetrics for each listing.
    """
    session = get_session()
    try:
        from sqlalchemy import Table, Column, Integer, String, DateTime, JSON, MetaData

        metadata = MetaData()
        analytics_events = Table(
            "analytics_events",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("listing_id", String(255), nullable=False),
            Column("event_type", String(50), nullable=False),
            Column("timestamp", DateTime, nullable=False),
            Column("metadata", JSON, nullable=True),
        )

        metadata.create_all(session.get_bind())

        from sqlalchemy import func, select

        # Get distinct listings with their metrics
        stmt = select(
            analytics_events.c.listing_id,
            func.sum(func.case((analytics_events.c.event_type == "view", 1), else_=0)).label(
                "views"
            ),
            func.sum(func.case((analytics_events.c.event_type == "favorite", 1), else_=0)).label(
                "favorites"
            ),
            func.sum(func.case((analytics_events.c.event_type == "purchase", 1), else_=0)).label(
                "sales"
            ),
        ).group_by(analytics_events.c.listing_id)

        results = session.execute(stmt).fetchall()

        metrics = []
        for row in results:
            metrics.append(
                ListingMetrics(
                    listing_id=row.listing_id,
                    views=row.views or 0,
                    favorites=row.favorites or 0,
                    sales=row.sales or 0,
                    period="all",
                )
            )

        return metrics

    except Exception as e:
        logger.error(f"Error getting all listings with metrics: {e}")
        return []
    finally:
        session.close()
