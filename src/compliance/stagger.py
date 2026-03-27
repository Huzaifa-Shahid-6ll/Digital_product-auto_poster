"""Staggered publishing for Etsy compliance.

Calculates delay between listings to avoid spam detection per D-12.
"""

from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel


class StaggerConfig(BaseModel):
    """Configuration for staggered publishing.

    Per D-12: Spread multiple listings over time to avoid spam detection.
    """

    delay_hours: int = 24  # Default 24 hours between listings
    max_listings_per_day: int = 5
    min_delay_hours: int = 1
    max_delay_hours: int = 72


# Default configuration
DEFAULT_STAGGER_CONFIG = StaggerConfig()


def calculate_stagger_delay(
    listing_index: int,
    config: Optional[StaggerConfig] = None,
    last_published: Optional[datetime] = None,
) -> timedelta:
    """Calculate stagger delay for a listing in a batch.

    Per D-12: Spread multiple listings over time to avoid spam detection.

    Args:
        listing_index: Position of listing in batch (0-indexed)
        config: Stagger configuration (defaults to DEFAULT_STAGGER_CONFIG)
        last_published: Timestamp of last published listing (if available)

    Returns:
        Timedelta representing when to publish this listing
    """
    cfg = config or DEFAULT_STAGGER_CONFIG

    # First listing has no delay (or minimal if last_published provided)
    if listing_index == 0:
        if last_published:
            # Calculate time since last published
            elapsed = datetime.now() - last_published
            if elapsed < timedelta(hours=cfg.min_delay_hours):
                return timedelta(hours=cfg.min_delay_hours) - elapsed
        return timedelta(hours=0)

    # Calculate delay based on position in batch
    # Use linear scaling: each listing gets cfg.delay_hours more delay
    # This ensures listings are spread out evenly
    delay_hours = listing_index * cfg.delay_hours

    # Cap at max_delay_hours
    delay_hours = min(delay_hours, cfg.max_delay_hours)

    return timedelta(hours=delay_hours)


def get_next_available_time(
    listing_index: int,
    config: Optional[StaggerConfig] = None,
    last_published: Optional[datetime] = None,
) -> datetime:
    """Get the next available publish time for a listing.

    Args:
        listing_index: Position of listing in batch
        config: Stagger configuration
        last_published: Timestamp of last published listing

    Returns:
        Datetime when listing can be published
    """
    delay = calculate_stagger_delay(listing_index, config, last_published)
    base_time = last_published or datetime.now()
    return base_time + delay


def should_stagger(batch_size: int, config: Optional[StaggerConfig] = None) -> bool:
    """Determine if a batch should be staggered.

    Args:
        batch_size: Number of listings in batch
        config: Stagger configuration

    Returns:
        True if batch should be staggered
    """
    cfg = config or DEFAULT_STAGGER_CONFIG
    return batch_size > cfg.max_listings_per_day


def get_stagger_schedule(
    batch_size: int, config: Optional[StaggerConfig] = None, start_time: Optional[datetime] = None
) -> list[datetime]:
    """Get a full stagger schedule for a batch of listings.

    Args:
        batch_size: Number of listings
        config: Stagger configuration
        start_time: When to start publishing (defaults to now)

    Returns:
        List of datetime objects representing when each listing should be published
    """
    cfg = config or DEFAULT_STAGGER_CONFIG
    start = start_time or datetime.now()

    schedule = []
    for i in range(batch_size):
        delay = calculate_stagger_delay(i, cfg)
        schedule.append(start + delay)

    return schedule
