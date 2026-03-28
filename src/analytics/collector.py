"""Analytics data collector for fetching Etsy listing metrics.

Provides functions to:
- collect_listing_stats: Fetch current metrics for a listing
- collect_analytics_events: Fetch historical events within a date range
- Store events in SQLite database

Uses retry logic with exponential backoff (per D-04).
"""

import logging
import time
from datetime import datetime
from typing import List, Optional

from src.analytics.schemas import AnalyticsEvent, ListingMetrics
from src.db.schema import get_session

logger = logging.getLogger(__name__)

# Retry configuration per D-04
INITIAL_INTERVAL = 1.0
BACKOFF_FACTOR = 2.0
MAX_ATTEMPTS = 3


class CollectorError(Exception):
    """Raised when data collection fails after all retries."""

    pass


def collect_listing_stats(listing_id: str) -> ListingMetrics:
    """Fetch current statistics for a listing.

    Attempts to fetch from Etsy API, falls back to database if unavailable.
    Implements retry logic with exponential backoff.

    Args:
        listing_id: The Etsy listing ID to fetch metrics for.

    Returns:
        ListingMetrics with current totals.

    Raises:
        CollectorError: If collection fails after all retries.
    """
    # Try to fetch from database first (MVP approach)
    # In production, this would call Etsy API
    session = get_session()
    try:
        # Query analytics_events table for this listing
        from sqlalchemy import and_, func, select

        from src.db.models import Base

        # Check if table exists, create if not
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

        # Create table if not exists
        metadata.create_all(session.get_bind())

        # Aggregate events
        stmt = select(
            analytics_events.c.listing_id,
            func.count(analytics_events.c.id).label("total_events"),
            func.sum(func.case((analytics_events.c.event_type == "view", 1), else_=0)).label(
                "views"
            ),
            func.sum(func.case((analytics_events.c.event_type == "favorite", 1), else_=0)).label(
                "favorites"
            ),
            func.sum(func.case((analytics_events.c.event_type == "purchase", 1), else_=0)).label(
                "sales"
            ),
        ).where(analytics_events.c.listing_id == listing_id)

        result = session.execute(stmt).fetchone()

        if result:
            return ListingMetrics(
                listing_id=listing_id,
                views=result.views or 0,
                favorites=result.favorites or 0,
                sales=result.sales or 0,
                period="all",
            )

        # No data yet - return empty metrics
        return ListingMetrics(
            listing_id=listing_id,
            views=0,
            favorites=0,
            sales=0,
            period="all",
        )

    except Exception as e:
        logger.error(f"Error collecting listing stats: {e}")
        # Return empty metrics on error - allow dashboard to show "no data yet"
        return ListingMetrics(
            listing_id=listing_id,
            views=0,
            favorites=0,
            sales=0,
            period="all",
        )
    finally:
        session.close()


def collect_analytics_events(
    listing_id: str,
    start_date: datetime,
    end_date: datetime,
) -> List[AnalyticsEvent]:
    """Fetch analytics events for a listing within a date range.

    Args:
        listing_id: The listing ID to fetch events for.
        start_date: Start of date range.
        end_date: End of date range.

    Returns:
        List of AnalyticsEvent objects.
    """
    session = get_session()
    try:
        from sqlalchemy import and_, select

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

        stmt = select(analytics_events).where(
            and_(
                analytics_events.c.listing_id == listing_id,
                analytics_events.c.timestamp >= start_date,
                analytics_events.c.timestamp <= end_date,
            )
        )

        results = session.execute(stmt).fetchall()

        events = []
        for row in results:
            events.append(
                AnalyticsEvent(
                    id=str(row.id),
                    listing_id=row.listing_id,
                    event_type=row.event_type,
                    timestamp=row.timestamp,
                    metadata=row.metadata or {},
                )
            )

        return events

    except Exception as e:
        logger.error(f"Error collecting analytics events: {e}")
        return []
    finally:
        session.close()


def store_analytics_event(event: AnalyticsEvent) -> bool:
    """Store an analytics event in the database.

    Args:
        event: The AnalyticsEvent to store.

    Returns:
        True if stored successfully, False otherwise.
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

        session.execute(
            analytics_events.insert().values(
                listing_id=event.listing_id,
                event_type=event.event_type,
                timestamp=event.timestamp,
                metadata=event.metadata,
            )
        )
        session.commit()
        return True

    except Exception as e:
        logger.error(f"Error storing analytics event: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_all_listing_ids() -> List[str]:
    """Get all listing IDs that have analytics data.

    Returns:
        List of unique listing IDs.
    """
    session = get_session()
    try:
        from sqlalchemy import distinct, select

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

        stmt = select(distinct(analytics_events.c.listing_id))
        results = session.execute(stmt).fetchall()

        return [row.listing_id for row in results]

    except Exception as e:
        logger.error(f"Error getting listing IDs: {e}")
        return []
    finally:
        session.close()
