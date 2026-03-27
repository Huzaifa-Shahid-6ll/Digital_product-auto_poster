"""Google Trends verification and demand scoring for niche recommendations.

Provides verify_demand() function that:
- Fetches real search interest data using pytrends
- Calculates demand scores using the proven formula
- Applies thresholds to flag high/medium/low demand
- Implements rate limiting and caching

Per D-04: 3 retries with exponential backoff.
Rate limit: 1 request per second (Google Trends limit).
Cache: 15-minute TTL.
"""

import time
from datetime import datetime
from typing import Optional

from pytrends.request import TrendReq

from src.niche_research.schemas import NicheRecommendation

# Configuration
RATE_LIMIT_DELAY = 1.0  # seconds between requests (Google Trends limit)
CACHE_TTL = 15 * 60  # 15 minutes in seconds

# Competition factor mapping
COMPETITION_FACTORS = {
    "high": 0.3,
    "medium": 0.6,
    "low": 1.0,
}

# Threshold definitions
VALIDATED_THRESHOLD = 65  # 65+ = validated (only ~1% of niches)
EXPLORE_THRESHOLD = 50  # 50-65 = explore
# <50 = low demand (not recommended)


class VerificationError(Exception):
    """Raised when niche verification fails after all retries."""

    pass


class CacheEntry:
    """Simple cache entry with TTL."""

    def __init__(self, data, ttl: int = CACHE_TTL):
        self.data = data
        self.timestamp = time.time()
        self.ttl = ttl

    def is_valid(self) -> bool:
        return (time.time() - self.timestamp) < self.ttl


# Simple in-memory cache
_verification_cache: dict[str, CacheEntry] = {}


def _get_cache(key: str) -> Optional[dict]:
    """Get cached verification data if valid."""
    entry = _verification_cache.get(key)
    if entry and entry.is_valid():
        return entry.data
    return None


def _set_cache(key: str, data: dict) -> None:
    """Cache verification data."""
    _verification_cache[key] = CacheEntry(data)


def _rate_limit():
    """Apply rate limiting (1 request per second)."""
    time.sleep(RATE_LIMIT_DELAY)


def _calculate_demand_score(
    average_interest: float,
    competition_level: str,
    trend_direction: int,
) -> float:
    """Calculate demand score using the proven formula.

    Formula: search_interest * 0.4 + competition_factor * 0.3 + trend_direction * 0.3

    Args:
        average_interest: Google Trends average (0-100)
        competition_level: low, medium, or high
        trend_direction: +1 (rising), 0 (stable), -1 (declining)

    Returns:
        Demand score (0-100)
    """
    competition_factor = COMPETITION_FACTORS.get(competition_level, 0.5)
    score = (
        (average_interest * 0.4) + (competition_factor * 0.3) + ((trend_direction + 1) * 0.15 * 100)
    )
    return min(100, max(0, score))


def _determine_trend_direction(values: list) -> str:
    """Determine trend direction from time series data.

    Args:
        values: List of search interest values over time

    Returns:
        'rising', 'stable', or 'declining'
    """
    if len(values) < 2:
        return "stable"

    # Compare first half average to second half average
    mid = len(values) // 2
    first_half = sum(values[:mid]) / mid if mid > 0 else values[0]
    second_half = sum(values[mid:]) / len(values[mid:]) if len(values[mid:]) > 0 else values[-1]

    if second_half > first_half * 1.1:
        return "rising"
    elif second_half < first_half * 0.9:
        return "declining"
    return "stable"


def _determine_trend_direction_value(direction: str) -> int:
    """Convert trend direction string to numeric value for scoring."""
    trend_map = {"rising": 1, "stable": 0, "declining": -1}
    return trend_map.get(direction, 0)


def verify_demand(
    recommendations: list[NicheRecommendation],
    retries: int = 3,
    initial_interval: float = 1.0,
    backoff_factor: float = 2.0,
) -> list[dict]:
    """Verify niche recommendations with real market data from Google Trends.

    Takes a list of NicheRecommendation objects, fetches real search interest
    data, calculates demand scores using the proven formula, and applies
    threshold logic.

    Args:
        recommendations: List of NicheRecommendation from analysis.
        retries: Number of retry attempts (default: 3).
        initial_interval: Initial backoff interval in seconds (default: 1.0).
        backoff_factor: Exponential backoff multiplier (default: 2.0).

    Returns:
        List of verified niche dictionaries with demand scores and verification data.
    """
    from datetime import datetime

    verified_niches = []

    # Build keyword list from recommendations
    for recommendation in recommendations:
        niche_keyword = recommendation.niche

        # Check cache first
        cache_key = f"verify_{niche_keyword.lower()}"
        cached_data = _get_cache(cache_key)

        if cached_data:
            verified_niches.append(cached_data)
            continue

        # Retry logic per D-04
        last_error: Optional[Exception] = None

        for attempt in range(retries):
            try:
                # Create pytrends request
                pytrends = TrendReq(hl="en-US", tz=360)
                pytrends.build_payload([niche_keyword], timeframe="today 12-m")

                # Fetch interest over time
                interest_data = pytrends.interest_over_time()

                if interest_data.empty:
                    # No data available - use fallback
                    average_interest = 0
                    values = []
                    peak_month = None
                else:
                    # Calculate average interest
                    values = interest_data[niche_keyword].tolist()
                    average_interest = sum(values) / len(values) if values else 0
                    peak_idx = values.index(max(values)) if values else 0
                    peak_month = (
                        interest_data.index[peak_idx].strftime("%Y-%m")
                        if peak_idx < len(interest_data)
                        else None
                    )

                # Determine trend direction
                trend_direction = _determine_trend_direction(values)
                trend_direction_value = _determine_trend_direction_value(trend_direction)

                # Calculate demand score
                demand_score = _calculate_demand_score(
                    average_interest=average_interest,
                    competition_level=recommendation.competition_level,
                    trend_direction=trend_direction_value,
                )

                # Apply thresholds
                if demand_score >= VALIDATED_THRESHOLD:
                    verified_demand = True
                    category = "validated"
                elif demand_score >= EXPLORE_THRESHOLD:
                    verified_demand = True
                    category = "explore"
                else:
                    verified_demand = False
                    category = "low_demand"

                # Build verification data
                verification_data = {
                    "average_interest": round(average_interest, 2),
                    "peak_month": peak_month,
                    "trend_direction": trend_direction,
                    "values_count": len(values),
                    "queried_at": datetime.utcnow().isoformat(),
                    "source": f"https://trends.google.com/trends/explore?q={niche_keyword}",
                }

                # Create verified niche dict
                verified_niche = {
                    "recommendation": {
                        "niche": recommendation.niche,
                        "target_audience": recommendation.target_audience,
                        "demand_estimate": recommendation.demand_estimate,
                        "competition_level": recommendation.competition_level,
                        "recommended_formats": recommendation.recommended_formats,
                        "rationale": recommendation.rationale,
                        "sources": recommendation.sources,
                    },
                    "demand_score": round(demand_score, 1),
                    "trend_direction": trend_direction,
                    "verification_data": verification_data,
                    "verified_demand": verified_demand,
                    "category": category,
                    "user_approved": False,
                }

                # Cache the result
                _set_cache(cache_key, verified_niche)

                verified_niches.append(verified_niche)

                # Rate limiting
                _rate_limit()

                break  # Success - exit retry loop

            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    wait_time = initial_interval * (backoff_factor**attempt)
                    time.sleep(wait_time)
                # Continue to next attempt

        else:
            # All retries exhausted - raise error
            raise VerificationError(
                f"Failed to verify niche '{recommendation.niche}' after {retries} attempts: {last_error}"
            )

    return verified_niches


def get_verification_summary(verified_niches: list[dict]) -> dict:
    """Generate summary statistics from verified niches.

    Args:
        verified_niches: List of verified niche dictionaries.

    Returns:
        Summary dict with counts by category.
    """
    categories = {"validated": 0, "explore": 0, "low_demand": 0}

    for niche in verified_niches:
        category = niche.get("category", "low_demand")
        if category in categories:
            categories[category] += 1

    return {
        "total": len(verified_niches),
        "validated": categories["validated"],
        "explore": categories["explore"],
        "low_demand": categories["low_demand"],
    }
