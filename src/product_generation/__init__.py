"""Product generation module for digital product ideas and creation.

This module provides:
- Idea generation using OpenAI with structured output
- Pydantic schemas for validating product ideas
- API routes for REST endpoint

Per D-01: Hybrid approach - templates provide structure, AI generates content.
"""

from src.product_generation.ideas import IdeaGenerator, IdeaGenerationError
from src.product_generation.schemas import IdeaSet, ProductIdea

__all__ = [
    "IdeaGenerator",
    "IdeaGenerationError",
    "IdeaSet",
    "ProductIdea",
]
