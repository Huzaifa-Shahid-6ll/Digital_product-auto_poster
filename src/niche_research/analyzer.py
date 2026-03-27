"""AI-powered niche analyzer using OpenAI GPT-4o.

Provides analyze_niche() function that:
- Takes keywords as input
- Returns structured NicheRecommendation objects
- Uses response_format={"type": "json_object"} for structured output
- Includes source citations to prevent hallucinations
- Implements retry logic with exponential backoff (3 retries)

Per D-04: 3 retries with exponential backoff (initial_interval=1.0, backoff_factor=2.0, max_attempts=3)
"""

import json
import time
from typing import Optional

from openai import AsyncOpenAI

from src.niche_research.schemas import NicheRecommendation
from src.niche_research.sources import DEFAULT_SOURCES, SourceTracker

# Retry configuration per D-04
INITIAL_INTERVAL = 1.0
BACKOFF_FACTOR = 2.0
MAX_ATTEMPTS = 3


class NicheAnalysisError(Exception):
    """Raised when niche analysis fails after all retries."""

    pass


async def analyze_niche(
    keywords: list[str],
    client: Optional[AsyncOpenAI] = None,
) -> list[NicheRecommendation]:
    """Analyze keywords and return niche recommendations.

    Uses OpenAI GPT-4o with structured JSON output to generate
    3+ niche recommendations with demand estimates, competition levels,
    and source citations.

    Args:
        keywords: List of keyword strings to analyze.
        client: Optional OpenAI client. If not provided, uses default.

    Returns:
        List of NicheRecommendation objects.

    Raises:
        NicheAnalysisError: If analysis fails after all retries.
    """
    if not client:
        client = AsyncOpenAI()

    tracker = SourceTracker()
    # Add default sources
    for source in DEFAULT_SOURCES:
        tracker.add_source(source.url, source.name)

    system_prompt = """You are a market research analyst specializing in digital products.
Analyze the given keywords and recommend profitable niche opportunities for digital products.

For each recommendation, provide:
- niche: The niche name/topic
- target_audience: Who would buy this product
- demand_estimate: high, medium, or low
- competition_level: low, medium, or high
- recommended_formats: List of suitable digital product formats (planner, worksheet, guide, template, etc.)
- rationale: Why this niche is promising
- sources: List of source URLs you used for research (use [Source: name](url) format)

Generate at least 3 recommendations. Cite your sources using [Source: name](url) format to prevent hallucinations.
"""

    user_prompt = f"""Analyze these keywords and recommend profitable niches for digital products:
Keywords: {", ".join(keywords)}

Provide recommendations in JSON format with the following structure:
{{
    "recommendations": [
        {{
            "niche": "...",
            "target_audience": "...",
            "demand_estimate": "high|medium|low",
            "competition_level": "low|medium|high",
            "recommended_formats": ["planner", "worksheet"],
            "rationale": "...",
            "sources": ["https://...", "https://..."]
        }}
    ]
}}
"""

    # Retry loop with exponential backoff (per D-04)
    last_error: Optional[Exception] = None

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )

            # Parse the JSON response
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")

            data = json.loads(content)

            # Validate against Pydantic models
            recommendations = []
            for rec_data in data.get("recommendations", []):
                # Ensure sources is a list
                if isinstance(rec_data.get("sources"), str):
                    rec_data["sources"] = [rec_data["sources"]]
                elif not rec_data.get("sources"):
                    rec_data["sources"] = []

                recommendation = NicheRecommendation(**rec_data)
                recommendations.append(recommendation)

            if not recommendations:
                raise ValueError("No recommendations in response")

            return recommendations

        except Exception as e:
            last_error = e
            if attempt < MAX_ATTEMPTS - 1:
                # Calculate backoff: 1.0, 2.0, 4.0
                wait_time = INITIAL_INTERVAL * (BACKOFF_FACTOR**attempt)
                time.sleep(wait_time)
            # Continue to next attempt

    # All retries exhausted
    raise NicheAnalysisError(f"Niche analysis failed after {MAX_ATTEMPTS} attempts: {last_error}")
