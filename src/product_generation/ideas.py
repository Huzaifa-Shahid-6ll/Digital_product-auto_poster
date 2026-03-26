"""Idea generation using OpenAI with structured output.

Per D-01: Hybrid approach - templates provide structure + format, AI generates specific content.
Uses response_format={"type": "json_object"} for structured output validation.
Per D-04: 3 retries with exponential backoff for error handling.
"""

import logging
import time
from typing import Optional

from openai import AsyncOpenAI

from src.product_generation.schemas import IdeaSet, ProductIdea

logger = logging.getLogger(__name__)

# Retry configuration from D-04
INITIAL_INTERVAL = 1.0
BACKOFF_FACTOR = 2.0
MAX_ATTEMPTS = 3


class IdeaGenerator:
    """Generate digital product ideas using OpenAI with structured output.

    Uses GPT-4o with response_format={"type": "json_object"} to generate
    structured product ideas based on a niche input.

    Attributes:
        client: OpenAI async client for API calls.
        model: OpenAI model to use (default: gpt-4o).
    """

    SYSTEM_PROMPT = """You are a digital product ideation expert specializing in 
Etsy-style products (planners, worksheets, guides). Generate 3 diverse product 
ideas that fit the given niche.

For each idea, ensure:
1. VARIETY: Different format types (planner, worksheet, guide) - not all the same
2. SPECIFICITY: Target a specific audience segment, not generic
3. REALISM: Feasible to create, has clear value proposition
4. MARKET FIT: Potential demand on platforms like Etsy

Output a JSON object with structure:
{
  "ideas": [
    {
      "title": "...",
      "format_type": "planner|worksheet|guide",
      "target_audience": "...",
      "unique_angle": "...",
      "key_features": ["...", "..."],
      "rationale": "..."
    }
  ],
  "niche": "...",
  "generated_at": "ISO timestamp"
}"""

    def __init__(self, client: AsyncOpenAI, model: str = "gpt-4o"):
        """Initialize the idea generator.

        Args:
            client: OpenAI async client instance.
            model: OpenAI model to use for generation.
        """
        self.client = client
        self.model = model

    async def generate(self, niche: str, count: int = 3) -> IdeaSet:
        """Generate product ideas for a given niche.

        Args:
            niche: The niche/topic to generate ideas for.
            count: Number of ideas to generate (default 3).

        Returns:
            IdeaSet containing the generated ideas.

        Raises:
            IdeaGenerationError: If all retry attempts fail.
        """
        if not niche or len(niche.strip()) < 3:
            raise ValueError("Niche must be at least 3 characters")

        # Build user prompt with count
        user_prompt = f"""Generate {count} digital product ideas for the niche: {niche}

Consider:
- Format types: planner, worksheet, or guide
- Target audience: Who would benefit most
- Unique angle: What makes this different from existing products
- Key features: What pages/sections the product includes
- Rationale: Why this fits the niche well

Return as JSON with 'ideas' array."""

        # Execute with retry logic
        result = await self._execute_with_retry(user_prompt, niche)

        return result

    async def _execute_with_retry(self, user_prompt: str, niche: str) -> IdeaSet:
        """Execute OpenAI call with exponential backoff retry.

        Per D-04: 3 retries with exponential backoff (initial_interval=1.0,
        backoff_factor=2.0, max_attempts=3).

        Args:
            user_prompt: The user prompt to send to OpenAI.
            niche: The niche for the IdeaSet.

        Returns:
            Validated IdeaSet from the response.

        Raises:
            IdeaGenerationError: If all attempts fail.
        """
        last_error: Optional[Exception] = None
        interval = INITIAL_INTERVAL

        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                logger.info(f"Generating ideas (attempt {attempt}/{MAX_ATTEMPTS})")

                response = await self.client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                )

                # Parse and validate the response
                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from OpenAI")

                # Parse JSON and validate with Pydantic
                import json

                data = json.loads(content)

                # Handle both direct idea array and nested structure
                ideas_data = data.get("ideas", data)
                if not isinstance(ideas_data, list):
                    ideas_data = [ideas_data]

                # Convert to ProductIdea objects
                ideas = [
                    ProductIdea(
                        title=idea.get("title", "Untitled"),
                        format_type=idea.get("format_type", "planner"),
                        target_audience=idea.get("target_audience", "General audience"),
                        unique_angle=idea.get("unique_angle", ""),
                        key_features=idea.get("key_features", []),
                        rationale=idea.get("rationale", ""),
                    )
                    for idea in ideas_data
                ]

                return IdeaSet(ideas=ideas, niche=niche)

            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt} failed: {str(e)}")

                if attempt < MAX_ATTEMPTS:
                    logger.info(f"Retrying in {interval} seconds...")
                    time.sleep(interval)
                    interval *= BACKOFF_FACTOR
                else:
                    logger.error(f"All {MAX_ATTEMPTS} attempts failed")

        raise IdeaGenerationError(f"Failed after {MAX_ATTEMPTS} attempts: {last_error}")


class IdeaGenerationError(Exception):
    """Exception raised when idea generation fails after all retries."""

    pass
