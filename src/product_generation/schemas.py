"""Pydantic schemas for product idea generation.

Defines structured data models for:
- ProductIdea: Individual product idea with all details
- IdeaSet: Collection of ideas for a given niche

Used for AI structured output validation and API response formatting.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ProductIdea(BaseModel):
    """A single digital product idea.

    Attributes:
        title: Product name/title.
        format_type: Type of digital product (planner, worksheet, guide).
        target_audience: Who the product is designed for.
        unique_angle: What makes this product different from competitors.
        key_features: List of main features included in the product.
        rationale: Explanation of why this idea fits the given niche.
    """

    title: str = Field(..., description="Product name/title")
    format_type: Literal["planner", "worksheet", "guide"] = Field(
        ..., description="Type of digital product"
    )
    target_audience: str = Field(..., description="Target audience for the product")
    unique_angle: str = Field(..., description="Unique selling proposition/angle")
    key_features: list[str] = Field(..., description="List of key features included in the product")
    rationale: str = Field(..., description="Why this idea fits the given niche")


class IdeaSet(BaseModel):
    """A collection of product ideas for a specific niche.

    Attributes:
        ideas: List of ProductIdea objects.
        niche: The input niche that the ideas are based on.
        generated_at: Timestamp when the ideas were generated.
    """

    ideas: list[ProductIdea] = Field(..., description="List of product ideas")
    niche: str = Field(..., description="The niche the ideas are based on")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when ideas were generated"
    )


class ProductSection(BaseModel):
    """A section within a generated product.

    Attributes:
        title: Section heading.
        content: Section content (text, instructions, prompts, etc.).
    """

    title: str = Field(..., description="Section heading")
    content: str = Field(..., description="Section content")


class ProductContent(BaseModel):
    """The content structure of a generated product.

    Attributes:
        sections: List of content sections.
        intro: Optional introduction text.
        conclusion: Optional conclusion text.
    """

    sections: list[ProductSection] = Field(..., description="Content sections")
    intro: Optional[str] = Field(default=None, description="Introduction text")
    conclusion: Optional[str] = Field(default=None, description="Conclusion text")


class ProductOutput(BaseModel):
    """The output of product generation - a generated digital product.

    Attributes:
        idea_id: ID of the source product idea.
        format: Format type (planner, worksheet, guide).
        title: Generated product title.
        content: Structured content with sections.
        generated_at: Timestamp when product was generated.
        quality_score: Optional quality score (0-100), None if not yet validated.
    """

    idea_id: str = Field(..., description="ID of the source product idea")
    format: Literal["planner", "worksheet", "guide"] = Field(..., description="Product format type")
    title: str = Field(..., description="Generated product title")
    content: ProductContent = Field(..., description="Structured content with sections")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Timestamp when product was generated"
    )
    quality_score: Optional[float] = Field(
        default=None, description="Quality score (0-100), None if not validated"
    )
