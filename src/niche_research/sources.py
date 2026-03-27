"""Source citation tracking for niche research.

Provides Source and SourceTracker classes to:
- Track sources used in AI-powered analysis
- Format citations as [Source: name](url)
- Inject sources into AI prompts for grounded responses
- Parse AI responses to extract cited sources

This helps prevent hallucinations by ensuring AI references real sources.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Source:
    """A single source reference.

    Attributes:
        url: The URL of the source.
        name: A readable name for the source.
        accessed_at: Timestamp when the source was accessed.
    """

    url: str
    name: str
    accessed_at: datetime = field(default_factory=datetime.utcnow)

    def to_citation(self) -> str:
        """Format source as markdown citation.

        Returns:
            Markdown-formatted citation: [Source: name](url)
        """
        return f"[Source: {self.name}]({self.url})"


class SourceTracker:
    """Tracks sources used in niche analysis.

    Provides methods to:
    - Add sources to the tracking list
    - Format all sources as citations
    - Inject sources into AI prompts
    - Extract sources from AI responses

    Example:
        tracker = SourceTracker()
        tracker.add_source("https://example.com", "Example Site")
        citations = tracker.get_all_citations()
        prompt_context = tracker.get_prompt_context()
    """

    def __init__(self):
        """Initialize empty source tracker."""
        self._sources: list[Source] = []

    def add_source(self, url: str, name: str) -> None:
        """Add a source to the tracker.

        Args:
            url: The URL of the source.
            name: A readable name for the source.
        """
        source = Source(url=url, name=name)
        self._sources.append(source)

    def get_all_citations(self) -> list[str]:
        """Get all sources formatted as markdown citations.

        Returns:
            List of markdown-formatted citations.
        """
        return [source.to_citation() for source in self._sources]

    def get_prompt_context(self) -> str:
        """Get sources formatted for injection into AI prompts.

        Returns:
            A string listing all sources with their URLs and names.
        """
        if not self._sources:
            return "No sources available."

        lines = ["Research Sources:"]
        for source in self._sources:
            lines.append(f"- {source.name}: {source.url}")

        return "\n".join(lines)

    @staticmethod
    def extract_sources_from_response(response: str) -> list[str]:
        """Extract source URLs from an AI response.

        Searches for markdown link pattern: [Source: name](url)

        Args:
            response: The AI response text to parse.

        Returns:
            List of unique source URLs found in the response.
        """
        import re

        # Match [Source: name](url) pattern
        pattern = r"\[Source: [^\]]+\]\(([^)]+)\)"
        matches = re.findall(pattern, response)

        # Return unique URLs
        return list(dict.fromkeys(matches))

    def get_sources(self) -> list[Source]:
        """Get all tracked sources.

        Returns:
            List of Source objects.
        """
        return self._sources.copy()

    def clear(self) -> None:
        """Clear all tracked sources."""
        self._sources.clear()


# Default sources for initial niche analysis (can be extended)
DEFAULT_SOURCES = [
    Source(
        url="https://www.etsy.com",
        name="Etsy",
        accessed_at=datetime.utcnow(),
    ),
    Source(
        url="https://trends.google.com",
        name="Google Trends",
        accessed_at=datetime.utcnow(),
    ),
    Source(
        url="https://www.google.com/search",
        name="Google Search",
        accessed_at=datetime.utcnow(),
    ),
]
