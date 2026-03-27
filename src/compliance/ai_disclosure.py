"""AI disclosure for Etsy compliance.

Adds required disclosure text for AI-generated content per D-11.
"""

from typing import Optional

# Required AI disclosure text per D-11
AI_DISCLOSURE_TEXT = (
    "This listing was created using AI assistance. Please message me if you have any questions!"
)

# Separator between description and disclosure
DISCLOSURE_SEPARATOR = "\n\n---\n\n"


def add_ai_disclosure(description: str, custom_disclosure: Optional[str] = None) -> str:
    """Add AI disclosure text to listing description.

    Appends disclosure text to the end of the description with a separator.

    Args:
        description: Original listing description
        custom_disclosure: Optional custom disclosure text (defaults to AI_DISCLOSURE_TEXT)

    Returns:
        Description with AI disclosure appended
    """
    disclosure = custom_disclosure or AI_DISCLOSURE_TEXT

    # Check if disclosure already exists to avoid duplicates
    if disclosure in description:
        return description

    return f"{description}{DISCLOSURE_SEPARATOR}{disclosure}"


def prepend_ai_disclosure(description: str, custom_disclosure: Optional[str] = None) -> str:
    """Prepend AI disclosure text to listing description.

    Adds disclosure text at the beginning of the description.

    Args:
        description: Original listing description
        custom_disclosure: Optional custom disclosure text

    Returns:
        Description with AI disclosure prepended
    """
    disclosure = custom_disclosure or AI_DISCLOSURE_TEXT

    # Check if disclosure already exists
    if disclosure in description:
        return description

    return f"{disclosure}{DISCLOSURE_SEPARATOR}{description}"


def has_ai_disclosure(description: str) -> bool:
    """Check if description already contains AI disclosure.

    Args:
        description: Description to check

    Returns:
        True if disclosure text is present
    """
    return AI_DISCLOSURE_TEXT in description
