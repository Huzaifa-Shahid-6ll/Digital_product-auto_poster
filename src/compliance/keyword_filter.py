"""Keyword filtering for Etsy compliance.

Filters prohibited keywords from listing content per D-10.
Prohibited terms are specific to digital products (avoiding handmade/made-to-order claims).
"""

import re
from typing import List, Tuple

# Prohibited keywords for digital products per Etsy guidelines and D-10
PROHIBITED_KEYWORDS = [
    # Handmade claims (not applicable to digital)
    "handmade",
    "hand-crafted",
    "handmade with",
    "hand crafted",
    "handmade in",
    # Made to order claims
    "custom made",
    "made to order",
    "made-to-order",
    "custom-designed",
    "custom designed",
    # One of a kind (overused and misleading for digital)
    "one of a kind",
    "one-of-a-kind",
    "ooak",
    # Age/vintage claims that don't apply
    "vintage",
    "antique",
    # Materials claims that don't apply
    "100% cotton",
    "leather",
    "wooden",
    "wood",
    # Authenticity claims
    "authentic",
    "genuine",
    "certified",
    # Limited edition claims (unless truly limited)
    "limited edition",
    "limited run",
    "only X left",
    # Fake scarcity
    "selling fast",
    "almost gone",
    "last chance",
    # Dropshipping indicators
    "dropship",
    "dropshipping",
    "wholesale",
    "bulk order",
]

# Build case-insensitive regex pattern
PROHIBITED_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(kw) for kw in PROHIBITED_KEYWORDS) + r")\b", re.IGNORECASE
)


def filter_keywords(title: str, description: str, tags: List[str]) -> Tuple[str, str, List[str]]:
    """Filter prohibited keywords from listing content.

    Args:
        title: Listing title
        description: Listing description
        tags: List of listing tags

    Returns:
        Tuple of (filtered_title, filtered_description, filtered_tags)
    """
    # Filter title
    filtered_title = _filter_text(title)

    # Filter description
    filtered_description = _filter_text(description)

    # Filter tags
    filtered_tags = [_filter_text(tag) for tag in tags]

    return filtered_title, filtered_description, filtered_tags


def _filter_text(text: str) -> str:
    """Replace prohibited keywords with [filtered] placeholder.

    Args:
        text: Input text to filter

    Returns:
        Text with prohibited keywords replaced
    """
    return PROHIBITED_PATTERN.sub("[filtered]", text)


def filter_single_field(text: str) -> str:
    """Filter a single text field.

    Args:
        text: Input text to filter

    Returns:
        Text with prohibited keywords replaced
    """
    return _filter_text(text)


def is_clean(text: str) -> bool:
    """Check if text contains any prohibited keywords.

    Args:
        text: Text to check

    Returns:
        True if text is clean (no prohibited keywords)
    """
    return PROHIBITED_PATTERN.search(text) is None
