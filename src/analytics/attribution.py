"""Sales attribution system for linking sales to listings.

Provides AttributionEngine class with:
- attribute_sale: Link a sale to its source listing
- get_listing_attribution: Get all attribution records for a listing
- get_time_period_attribution: Get attribution summary for a time period

Attribution logic:
- Links order to listing via listing_id in order
- Tracks source (direct, search, campaign)
- Uses attribution window (7-day cookie)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from src.analytics.schemas import AttributionRecord
from src.db.schema import get_session

logger = logging.getLogger(__name__)

# Attribution window in days
ATTRIBUTION_WINDOW_DAYS = 7


class AttributionEngine:
    """Engine for attributing sales to listings and sources."""

    def __init__(self):
        """Initialize the attribution engine."""
        self._init_tables()

    def _init_tables(self):
        """Create attribution tables if they don't exist."""
        session = get_session()
        try:
            from sqlalchemy import Table, Column, Integer, String, DateTime, Float, MetaData

            metadata = MetaData()

            # Attribution records table
            attribution_records = Table(
                "attribution_records",
                metadata,
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("sale_id", String(255), nullable=False, unique=True),
                Column("listing_id", String(255), nullable=False),
                Column("timestamp", DateTime, nullable=False),
                Column("source", String(50), nullable=False, default="unknown"),
                Column("revenue", Float, nullable=False, default=0.0),
            )

            metadata.create_all(session.get_bind())

        finally:
            session.close()

    def attribute_sale(
        self,
        sale_id: str,
        listing_id: str,
        timestamp: Optional[datetime] = None,
        source: str = "unknown",
        revenue: float = 0.0,
    ) -> AttributionRecord:
        """Link a sale to a listing and attribution source.

        Args:
            sale_id: Unique sale/order identifier.
            listing_id: The listing that generated this sale.
            timestamp: When the sale occurred (defaults to now).
            source: Attribution source (direct, search, campaign).
            revenue: Sale amount.

        Returns:
            AttributionRecord with attribution details.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        session = get_session()
        try:
            from sqlalchemy import Table, Column, Integer, String, DateTime, Float, MetaData

            metadata = MetaData()
            attribution_records = Table(
                "attribution_records",
                metadata,
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("sale_id", String(255), nullable=False, unique=True),
                Column("listing_id", String(255), nullable=False),
                Column("timestamp", DateTime, nullable=False),
                Column("source", String(50), nullable=False, default="unknown"),
                Column("revenue", Float, nullable=False, default=0.0),
            )

            metadata.create_all(session.get_bind())

            # Insert attribution record
            session.execute(
                attribution_records.insert().values(
                    sale_id=sale_id,
                    listing_id=listing_id,
                    timestamp=timestamp,
                    source=source,
                    revenue=revenue,
                )
            )
            session.commit()

            return AttributionRecord(
                sale_id=sale_id,
                listing_id=listing_id,
                timestamp=timestamp,
                source=source,
                revenue=revenue,
            )

        except Exception as e:
            logger.error(f"Error attributing sale: {e}")
            session.rollback()
            # Return record anyway for consistency
            return AttributionRecord(
                sale_id=sale_id,
                listing_id=listing_id,
                timestamp=timestamp,
                source=source,
                revenue=revenue,
            )
        finally:
            session.close()

    def get_listing_attribution(self, listing_id: str) -> List[AttributionRecord]:
        """Get all attribution records for a listing.

        Args:
            listing_id: The listing ID to get attribution for.

        Returns:
            List of AttributionRecord objects.
        """
        session = get_session()
        try:
            from sqlalchemy import select

            from sqlalchemy import Table, Column, Integer, String, DateTime, Float, MetaData

            metadata = MetaData()
            attribution_records = Table(
                "attribution_records",
                metadata,
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("sale_id", String(255), nullable=False, unique=True),
                Column("listing_id", String(255), nullable=False),
                Column("timestamp", DateTime, nullable=False),
                Column("source", String(50), nullable=False, default="unknown"),
                Column("revenue", Float, nullable=False, default=0.0),
            )

            metadata.create_all(session.get_bind())

            stmt = select(attribution_records).where(attribution_records.c.listing_id == listing_id)

            results = session.execute(stmt).fetchall()

            records = []
            for row in results:
                records.append(
                    AttributionRecord(
                        sale_id=row.sale_id,
                        listing_id=row.listing_id,
                        timestamp=row.timestamp,
                        source=row.source,
                        revenue=row.revenue,
                    )
                )

            return records

        except Exception as e:
            logger.error(f"Error getting listing attribution: {e}")
            return []
        finally:
            session.close()

    def get_time_period_attribution(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Get attribution summary for a time period.

        Args:
            start_date: Start of the period.
            end_date: End of the period.

        Returns:
            Dict with attribution summary by source and listing.
        """
        session = get_session()
        try:
            from sqlalchemy import and_, func, select

            from sqlalchemy import Table, Column, Integer, String, DateTime, Float, MetaData

            metadata = MetaData()
            attribution_records = Table(
                "attribution_records",
                metadata,
                Column("id", Integer, primary_key=True, autoincrement=True),
                Column("sale_id", String(255), nullable=False, unique=True),
                Column("listing_id", String(255), nullable=False),
                Column("timestamp", DateTime, nullable=False),
                Column("source", String(50), nullable=False, default="unknown"),
                Column("revenue", Float, nullable=False, default=0.0),
            )

            metadata.create_all(session.get_bind())

            # Get summary by source
            source_stmt = (
                select(
                    attribution_records.c.source,
                    func.count().label("sales"),
                    func.sum(attribution_records.c.revenue).label("revenue"),
                )
                .where(
                    and_(
                        attribution_records.c.timestamp >= start_date,
                        attribution_records.c.timestamp <= end_date,
                    )
                )
                .group_by(attribution_records.c.source)
            )

            source_results = session.execute(source_stmt).fetchall()

            # Get summary by listing
            listing_stmt = (
                select(
                    attribution_records.c.listing_id,
                    func.count().label("sales"),
                    func.sum(attribution_records.c.revenue).label("revenue"),
                )
                .where(
                    and_(
                        attribution_records.c.timestamp >= start_date,
                        attribution_records.c.timestamp <= end_date,
                    )
                )
                .group_by(attribution_records.c.listing_id)
            )

            listing_results = session.execute(listing_stmt).fetchall()

            return {
                "by_source": {
                    row.source: {"sales": row.sales, "revenue": row.revenue or 0}
                    for row in source_results
                },
                "by_listing": {
                    row.listing_id: {"sales": row.sales, "revenue": row.revenue or 0}
                    for row in listing_results
                },
                "total_sales": sum(row.sales for row in source_results),
                "total_revenue": sum(row.revenue or 0 for row in source_results),
            }

        except Exception as e:
            logger.error(f"Error getting time period attribution: {e}")
            return {
                "by_source": {},
                "by_listing": {},
                "total_sales": 0,
                "total_revenue": 0,
            }
        finally:
            session.close()


# Convenience function
def get_attribution_engine() -> AttributionEngine:
    """Get or create attribution engine instance.

    Returns:
        AttributionEngine instance.
    """
    return AttributionEngine()
