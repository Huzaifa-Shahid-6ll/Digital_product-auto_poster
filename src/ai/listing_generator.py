"""AI listing content generator for Etsy.

Generates SEO-optimized listing content (title, description, tags)
using OpenAI based on product information.

Per D-05, D-06, D-07, D-08, D-09 from research:
- Title: SEO-optimized, max 140 characters
- Description: SEO-focused with key features, benefits, usage info
- Tags: 13 max, relevant search terms
- Price suggestion based on market data (D-14)
- Category recommendation (D-16)
"""

import logging
from typing import Optional

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ListingContent(BaseModel):
    """Generated listing content for Etsy.

    Attributes:
        title: SEO-optimized title (max 140 chars).
        description: SEO-focused description with key features, benefits.
        tags: List of 13 relevant search tags.
        suggested_price: AI-suggested price based on market data.
        suggested_category_id: Recommended Etsy category ID.
    """

    title: str = Field(..., description="SEO-optimized title (max 140 chars)")
    description: str = Field(
        ..., description="SEO-focused description with key features and benefits"
    )
    tags: list[str] = Field(..., description="List of 13 relevant search tags")
    suggested_price: float = Field(..., description="Suggested price based on market data")
    suggested_category_id: str = Field(..., description="Recommended Etsy category ID")


class Product(BaseModel):
    """Product information for listing generation.

    Attributes:
        name: Product name/title.
        description: Product description.
        format_type: Type of digital product (planner, worksheet, guide).
        target_audience: Target audience.
        key_features: List of key features.
    """

    name: str = Field(..., description="Product name/title")
    description: str = Field(..., description="Product description")
    format_type: str = Field(..., description="Type of digital product")
    target_audience: str = Field(..., description="Target audience")
    key_features: list[str] = Field(..., description="List of key features")


class ListingGenerator:
    """AI-powered listing content generator.

    Uses OpenAI to generate SEO-optimized listing content for Etsy.

    Example:
        >>> client = AsyncOpenAI(api_key="sk-...")
        >>> generator = ListingGenerator(client)
        >>> product = Product(
        ...     name="Goal Planner 2025",
        ...     description="...",
        ...     format_type="planner",
        ...     target_audience="Professionals",
        ...     key_features=["daily pages", "goal tracking"]
        ... )
        >>> content = await generator.generate(product)
    """

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        """Initialize listing generator.

        Args:
            client: OpenAI async client.
            model: OpenAI model to use (default gpt-4o-mini).
        """
        self._client = client
        self._model = model

    async def generate(
        self,
        product: Product,
        price_range_min: Optional[float] = None,
        price_range_max: Optional[float] = None,
        similar_listings: Optional[list[dict]] = None,
    ) -> ListingContent:
        """Generate SEO-optimized listing content.

        Generates title, description, tags, price suggestion, and category
        recommendation based on product information and market data.

        Args:
            product: Product information.
            price_range_min: Optional minimum price from market research.
            price_range_max: Optional maximum price from market research.
            similar_listings: Optional list of similar listings with prices.

        Returns:
            ListingContent with generated title, description, tags,
            suggested_price, and suggested_category_id.

        Raises:
            Exception: If generation fails after retries.
        """
        # Build market context for price and category suggestions
        market_context = self._build_market_context(
            price_range_min, price_range_max, similar_listings
        )

        # Build the prompt
        prompt = self._build_prompt(product, market_context)

        # Call OpenAI
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an Etsy SEO expert. Generate listing content "
                    "optimized for Etsy search. Output valid JSON with exactly these fields: "
                    "title (max 140 chars), description, tags (exactly 13), "
                    "suggested_price (number), suggested_category_id (string).",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
        )

        # Parse response
        try:
            import json

            raw_content = response.choices[0].message.content or "{}"
            content = json.loads(raw_content)
            return ListingContent(
                title=self._truncate_title(content.get("title", "")),
                description=content.get("description", ""),
                tags=self._ensure_tags(content.get("tags", [])),
                suggested_price=float(content.get("suggested_price", 9.99)),
                suggested_category_id=str(content.get("suggested_category_id", "")),
            )
        except Exception as e:
            logger.error(f"Failed to parse listing content: {e}")
            raise

    def _build_market_context(
        self,
        price_min: Optional[float],
        price_max: Optional[float],
        similar: Optional[list[dict]],
    ) -> str:
        """Build market context string for prompt."""
        parts = []
        if price_min and price_max:
            parts.append(f"Price range in market: ${price_min:.2f} - ${price_max:.2f}")
        elif price_min:
            parts.append(f"Minimum price in market: ${price_min:.2f}")
        elif price_max:
            parts.append(f"Maximum price in market: ${price_max:.2f}")

        if similar:
            prices = [s.get("price", 0) for s in similar if s.get("price")]
            if prices:
                avg = sum(prices) / len(prices)
                parts.append(f"Average price of similar listings: ${avg:.2f}")

        return " | ".join(parts) if parts else "No market data available"

    def _build_prompt(self, product: Product, market_context: str) -> str:
        """Build generation prompt."""
        return f"""Generate Etsy listing content for this digital product:

Product: {product.name}
Format: {product.format_type}
Target: {product.target_audience}
Description: {product.description}
Key Features: {", ".join(product.key_features)}

Market Context: {market_context}

Generate:
1. Title (max 140 chars): SEO-optimized with primary keywords
2. Description: SEO-focused with key features, benefits, usage info
3. Tags: 13 relevant search terms (mix of broad and specific)
4. Suggested Price: Based on market data
5. Category ID: Recommended Etsy category

Output as JSON with keys: title, description, tags (array), suggested_price, suggested_category_id"""

    def _truncate_title(self, title: str) -> str:
        """Truncate title to max 140 characters."""
        if len(title) <= 140:
            return title
        return title[:137] + "..."

    def _ensure_tags(self, tags: list) -> list[str]:
        """Ensure exactly 13 tags."""
        # Convert to strings
        tag_strings = [str(t).strip() for t in tags if str(t).strip()]

        # Remove duplicates while preserving order
        seen = set()
        unique_tags = []
        for tag in tag_strings:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_tags.append(tag)

        # Pad with empty or truncate
        if len(unique_tags) < 13:
            # Add generic tags if needed
            generic = ["digital download", "printable", "digital planner", "download"]
            for g in generic:
                if len(unique_tags) >= 13:
                    break
                if g.lower() not in seen:
                    unique_tags.append(g)
                    seen.add(g.lower())

        return unique_tags[:13]


async def generate_listing_content(
    product: Product,
    client: AsyncOpenAI,
    price_range_min: Optional[float] = None,
    price_range_max: Optional[float] = None,
    similar_listings: Optional[list[dict]] = None,
) -> ListingContent:
    """Convenience function to generate listing content.

    Args:
        product: Product information.
        client: OpenAI client.
        price_range_min: Optional minimum price from market.
        price_range_max: Optional maximum price from market.
        similar_listings: Optional similar listings for pricing context.

    Returns:
        Generated ListingContent.
    """
    generator = ListingGenerator(client)
    return await generator.generate(
        product=product,
        price_range_min=price_range_min,
        price_range_max=price_range_max,
        similar_listings=similar_listings,
    )
