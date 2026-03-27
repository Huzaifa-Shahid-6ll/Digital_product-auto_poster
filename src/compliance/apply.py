"""Combined compliance application for Etsy listings.

Applies all three compliance features per D-13:
- Keyword filtering
- AI disclosure
- Staggered publishing

This is the main entry point for compliance processing before listing creation.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from .keyword_filter import filter_keywords
from .ai_disclosure import add_ai_disclosure, AI_DISCLOSURE_TEXT
from .stagger import calculate_stagger_delay, StaggerConfig, DEFAULT_STAGGER_CONFIG


class ComplianceResult(BaseModel):
    """Result of applying compliance to listing content."""

    title: str
    description: str
    tags: List[str]
    stagger_delay: timedelta
    next_available_time: Optional[datetime] = None
    was_filtered: bool = False
    ai_disclosure_added: bool = False


def apply_compliance(
    title: str,
    description: str,
    tags: List[str],
    stagger_index: int = 0,
    stagger_config: Optional[StaggerConfig] = None,
    last_published: Optional[datetime] = None,
    enable_keyword_filter: bool = True,
    enable_ai_disclosure: bool = True,
    enable_stagger: bool = True,
) -> ComplianceResult:
    """Apply all compliance features to listing content.

    Per D-13: Full compliance - all three compliance features active by default.

    Args:
        title: Listing title
        description: Listing description
        tags: List of listing tags
        stagger_index: Position in batch for stagger calculation
        stagger_config: Stagger configuration
        last_published: Timestamp of last published listing
        enable_keyword_filter: Enable keyword filtering (default True)
        enable_ai_disclosure: Enable AI disclosure (default True)
        enable_stagger: Enable stagger calculation (default True)

    Returns:
        ComplianceResult with processed content and metadata
    """
    # Track modifications
    was_filtered = False
    ai_disclosure_added = False

    # Step 1: Keyword filtering
    if enable_keyword_filter:
        title, description, tags = filter_keywords(title, description, tags)
        # Check if anything was actually filtered
        was_filtered = (
            "[filtered]" in title
            or "[filtered]" in description
            or any("[filtered]" in tag for tag in tags)
        )

    # Step 2: AI disclosure
    if enable_ai_disclosure:
        original_len = len(description)
        description = add_ai_disclosure(description)
        ai_disclosure_added = len(description) > original_len

    # Step 3: Calculate stagger delay
    stagger_delay = timedelta(hours=0)
    next_available_time = None

    if enable_stagger:
        cfg = stagger_config or DEFAULT_STAGGER_CONFIG
        stagger_delay = calculate_stagger_delay(stagger_index, cfg, last_published)
        if last_published:
            next_available_time = last_published + stagger_delay
        else:
            next_available_time = datetime.now() + stagger_delay

    return ComplianceResult(
        title=title,
        description=description,
        tags=tags,
        stagger_delay=stagger_delay,
        next_available_time=next_available_time,
        was_filtered=was_filtered,
        ai_disclosure_added=ai_disclosure_added,
    )


def apply_compliance_batch(
    listings: List[dict],
    stagger_config: Optional[StaggerConfig] = None,
    last_published: Optional[datetime] = None,
    enable_keyword_filter: bool = True,
    enable_ai_disclosure: bool = True,
    enable_stagger: bool = True,
) -> List[ComplianceResult]:
    """Apply compliance to a batch of listings.

    Args:
        listings: List of listing dicts with 'title', 'description', 'tags'
        stagger_config: Stagger configuration
        last_published: Timestamp of last published listing
        enable_keyword_filter: Enable keyword filtering
        enable_ai_disclosure: Enable AI disclosure
        enable_stagger: Enable stagger calculation

    Returns:
        List of ComplianceResult objects
    """
    results = []
    last_time = last_published

    for i, listing in enumerate(listings):
        result = apply_compliance(
            title=listing.get("title", ""),
            description=listing.get("description", ""),
            tags=listing.get("tags", []),
            stagger_index=i,
            stagger_config=stagger_config,
            last_published=last_time,
            enable_keyword_filter=enable_keyword_filter,
            enable_ai_disclosure=enable_ai_disclosure,
            enable_stagger=enable_stagger,
        )
        results.append(result)

        # Update last_published for next iteration
        if result.next_available_time:
            last_time = result.next_available_time

    return results
