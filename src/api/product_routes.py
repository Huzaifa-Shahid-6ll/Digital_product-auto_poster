"""API routes for product generation and validation.

REST endpoints for:
- POST /api/products/generate - Generate a product from an idea
- POST /api/products/validate - Validate a generated product
- GET /api/products/{product_id} - Retrieve a generated product

Per D-03: AI does initial assessment, human does final approval via dashboard.
Per D-04: User reviews ideas, selects one, system generates product.
"""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.product_generation.generator import ProductGenerator
from src.product_generation.schemas import ProductIdea, ProductOutput
from src.product_generation.validator import ProductValidator, ValidationResult

# Create router
router = APIRouter(tags=["products"])

# Global instances (will be set by app)
_generator: Optional[ProductGenerator] = None
_validator: Optional[ProductValidator] = None


def set_generator(generator: ProductGenerator):
    """Set the global product generator instance."""
    global _generator
    _generator = generator


def set_validator(validator: ProductValidator):
    """Set the global product validator instance."""
    global _validator
    _validator = validator


def get_generator() -> ProductGenerator:
    """Get or create ProductGenerator instance.

    Returns:
        Configured ProductGenerator instance.

    Raises:
        HTTPException: If generator not configured.
    """
    global _generator
    if _generator is None:
        # Try to create with OpenAI client if key available
        try:
            from openai import OpenAI

            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)
                _generator = ProductGenerator(client=client)
            else:
                # Use mock generator without client
                _generator = ProductGenerator(client=None)
        except ImportError:
            # OpenAI not available, use mock
            _generator = ProductGenerator(client=None)

    return _generator


def get_validator() -> ProductValidator:
    """Get or create ProductValidator instance.

    Returns:
        Configured ProductValidator instance.
    """
    global _validator
    if _validator is None:
        try:
            from openai import OpenAI

            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                client = OpenAI(api_key=api_key)
                _validator = ProductValidator(client=client)
            else:
                _validator = ProductValidator(client=None)
        except ImportError:
            _validator = ProductValidator(client=None)

    return _validator


# Request/Response models


class ProductGenerateRequest(BaseModel):
    """Request model for product generation.

    Attributes:
        idea_id: ID of the product idea to generate from.
        format: Optional format type (planner, worksheet, guide).
        title: Product title.
        target_audience: Who the product is for.
        unique_angle: What makes it unique.
        key_features: List of key features.
        rationale: Why this fits the niche.
    """

    idea_id: str = Field(..., description="ID of the source product idea")
    format: str = Field(default="planner", description="Product format type")
    title: str = Field(..., min_length=3, description="Product title")
    target_audience: str = Field(..., description="Target audience")
    unique_angle: str = Field(..., description="Unique angle/proposition")
    key_features: list[str] = Field(..., min_length=1, description="Key features")
    rationale: str = Field(..., description="Why this fits the niche")


class ProductGenerateResponse(BaseModel):
    """Response model for product generation."""

    product_id: str
    idea_id: str
    format: str
    title: str
    quality_score: Optional[float]
    validation_passed: bool
    validation_issues: list[str]
    pdf_path: Optional[str]
    generated_at: str


class ProductValidateRequest(BaseModel):
    """Request model for product validation."""

    product_id: str = Field(..., description="ID of the product to validate")
    idea_id: str = Field(..., description="ID of the source idea")
    format: str = Field(..., description="Product format type")
    title: str = Field(..., description="Product title")
    content: dict = Field(..., description="Product content structure")
    quality_score: Optional[float] = Field(default=None, description="Existing quality score")


class ProductValidateResponse(BaseModel):
    """Response model for product validation."""

    product_id: str
    passed: bool
    score: float
    recommendation: str
    issues: list[str]


class ProductDetailResponse(BaseModel):
    """Response model for product retrieval."""

    product_id: str
    idea_id: str
    format: str
    title: str
    content: dict
    quality_score: Optional[float]
    generated_at: str
    pdf_path: Optional[str]


# In-memory storage for generated products (would be database in production)
_products_storage: dict[str, dict] = {}


# Routes


@router.post("/generate", response_model=ProductGenerateResponse, status_code=201)
async def generate_product(
    request: ProductGenerateRequest,
    generator: ProductGenerator = Depends(get_generator),
    validator: ProductValidator = Depends(get_validator),
) -> ProductGenerateResponse:
    """Generate a digital product from a product idea.

    Creates a PDF product based on the provided idea details,
    then validates it for quality before returning.

    Args:
        request: ProductGenerateRequest with idea details.
        generator: ProductGenerator dependency.
        validator: ProductValidator dependency.

    Returns:
        ProductGenerateResponse with generated product and validation results.

    Raises:
        HTTPException: If generation fails.
    """
    try:
        # Create ProductIdea from request
        product_idea = ProductIdea(
            title=request.title,
            format_type=request.format,  # type: ignore
            target_audience=request.target_audience,
            unique_angle=request.unique_angle,
            key_features=request.key_features,
            rationale=request.rationale,
        )

        # Generate product
        product = generator.generate(product_idea)

        # Override the idea_id with the one from request
        product.idea_id = request.idea_id

        # Validate product
        validation = validator.validate(product)

        # Update product with validation score
        product.quality_score = validation.score

        # Save PDF
        pdf_path = None
        try:
            pdf_path = generator.save_pdf(product)
        except Exception as e:
            # PDF saving failed - continue without path
            pdf_path = None

        # Store in memory (would be database in production)
        product_data = {
            "product_id": product.idea_id,
            "idea_id": product.idea_id,
            "format": product.format,
            "title": product.title,
            "content": product.content.model_dump(),
            "quality_score": product.quality_score,
            "generated_at": product.generated_at.isoformat(),
            "pdf_path": pdf_path,
        }
        _products_storage[product.idea_id] = product_data

        return ProductGenerateResponse(
            product_id=product.idea_id,
            idea_id=product.idea_id,
            format=product.format,
            title=product.title,
            quality_score=validation.score,
            validation_passed=validation.passed,
            validation_issues=validation.issues,
            pdf_path=pdf_path,
            generated_at=product.generated_at.isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Product generation failed: {str(e)}",
        )


@router.post("/validate", response_model=ProductValidateResponse)
async def validate_product(
    request: ProductValidateRequest,
    validator: ProductValidator = Depends(get_validator),
) -> ProductValidateResponse:
    """Validate a generated product for quality.

    Runs completeness, formatting, and coherence checks,
    returning a score and recommendation.

    Args:
        request: ProductValidateRequest with product details.
        validator: ProductValidator dependency.

    Returns:
        ProductValidateResponse with validation results.

    Raises:
        HTTPException: If validation fails.
    """
    try:
        # Reconstruct ProductOutput from request
        from src.product_generation.schemas import ProductContent

        content_dict = request.content
        content = ProductContent(**content_dict)

        product = ProductOutput(
            idea_id=request.idea_id,
            format=request.format,  # type: ignore
            title=request.title,
            content=content,
            quality_score=request.quality_score,
        )

        # Validate
        result = validator.validate(product)

        return ProductValidateResponse(
            product_id=request.product_id,
            passed=result.passed,
            score=result.score,
            recommendation=result.recommendation,
            issues=result.issues,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}",
        )


@router.get("/{product_id}", response_model=ProductDetailResponse)
async def get_product(product_id: str) -> ProductDetailResponse:
    """Retrieve a generated product by ID.

    Args:
        product_id: The product ID to retrieve.

    Returns:
        ProductDetailResponse with product details.

    Raises:
        HTTPException: If product not found.
    """
    if product_id not in _products_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Product '{product_id}' not found",
        )

    product_data = _products_storage[product_id]

    return ProductDetailResponse(
        product_id=product_data["product_id"],
        idea_id=product_data["idea_id"],
        format=product_data["format"],
        title=product_data["title"],
        content=product_data["content"],
        quality_score=product_data["quality_score"],
        generated_at=product_data["generated_at"],
        pdf_path=product_data["pdf_path"],
    )
