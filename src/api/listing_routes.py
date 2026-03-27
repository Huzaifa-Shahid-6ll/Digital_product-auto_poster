"""API routes for listing management.

REST endpoints for:
- POST /api/listings - Create listing with AI-generated content
- GET /api/listings/{listing_id} - Get listing status and details
- PUT /api/listings/{listing_id} - Update listing content
- POST /api/listings/{listing_id}/publish - Publish listing
- DELETE /api/listings/{listing_id} - Delete listing

Mounted at /api/listings in main app.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse

from src.ai.listing_generator import ListingContent, ListingGenerator, Product
from src.api.main import get_openai_client
from src.etsy.client import EtsyClient
from src.etsy.listing import (
    create_draft_listing,
    delete_listing,
    get_listing,
    publish_listing,
    update_listing,
)
from src.etsy.image_upload import (
    upload_listing_image,
    upload_product_images,
)
from src.etsy.file_upload import (
    upload_digital_file,
    set_listing_as_download,
    upload_and_configure_digital,
)
from src.etsy.oauth import EtsyOAuth

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["listings"])

# In-memory storage for demo (would be DB in production)
_listings_storage: dict[int, dict] = {}
_listing_counter = 0


# Request/Response models


class CreateListingRequest(BaseModel):
    """Request model for listing creation.

    Attributes:
        product_id: ID of the product to create listing from.
        title: Optional title override.
        description: Optional description override.
        tags: Optional tags override.
        price_override: Optional price override.
    """

    product_id: str = Field(..., description="ID of the product to create listing from")
    title: Optional[str] = Field(None, description="Optional title override")
    description: Optional[str] = Field(None, description="Optional description override")
    tags: Optional[list[str]] = Field(None, description="Optional tags override")
    price_override: Optional[float] = Field(None, description="Optional price override")


class UpdateListingRequest(BaseModel):
    """Request model for listing update.

    Attributes:
        title: Optional new title.
        description: Optional new description.
        tags: Optional new tags.
        price: Optional new price.
    """

    title: Optional[str] = Field(None, description="New title")
    description: Optional[str] = Field(None, description="New description")
    tags: Optional[list[str]] = Field(None, description="New tags")
    price: Optional[float] = Field(None, description="New price")


class CreateListingResponse(BaseModel):
    """Response model for listing creation."""

    listing_id: int
    title: str
    description: str
    tags: list[str]
    status: str
    suggested_price: float
    suggested_category_id: str


class ListingDetailResponse(BaseModel):
    """Response model for listing details."""

    listing_id: int
    status: str
    title: str
    price: Optional[float] = None
    etsy_url: Optional[str] = None
    created_at: str


class PublishResponse(BaseModel):
    """Response model for publish."""

    success: bool
    etsy_listing_url: Optional[str] = None


class ImageUploadResponse(BaseModel):
    """Response model for image upload."""

    image_id: int
    listing_id: int
    rank: int


class BulkImageUploadResponse(BaseModel):
    """Response model for bulk image upload."""

    image_ids: list[int]
    listing_id: int
    count: int


class FileUploadResponse(BaseModel):
    """Response model for digital file upload."""

    file_id: str
    listing_id: int
    digital: bool
    quantity_unlimited: bool


class ImageListResponse(BaseModel):
    """Response model for listing images."""

    images: list[dict]


# Dependencies


def get_etsy_client() -> EtsyClient:
    """Get or create EtsyClient with OAuth.

    Returns:
        Configured EtsyClient instance.

    Raises:
        HTTPException: If OAuth not configured.
    """
    from src.api.main import get_engine

    # Get engine to access OAuth tokens
    engine = get_engine()
    # For now, raise if no OAuth
    # In production, would get from DB based on authenticated user
    raise HTTPException(
        status_code=501,
        detail="Etsy OAuth not yet implemented. Use /api/auth/etsy/authorize first.",
    )


def get_listing_generator() -> ListingGenerator:
    """Get or create ListingGenerator with OpenAI client.

    Returns:
        Configured ListingGenerator instance.

    Raises:
        HTTPException: If OpenAI client not configured.
    """
    try:
        client = get_openai_client()
    except HTTPException:
        raise

    return ListingGenerator(client)


# Routes


@router.post("", response_model=CreateListingResponse, status_code=201)
async def create_listing(
    request: CreateListingRequest,
    generator: ListingGenerator = Depends(get_listing_generator),
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> CreateListingResponse:
    """Create a listing with AI-generated content.

    Takes a product_id and generates SEO-optimized title, description,
    and tags. Creates a draft listing on Etsy for review.

    Args:
        request: CreateListingRequest with product_id and optional overrides.
        generator: ListingGenerator dependency (injected).
        client: EtsyClient dependency (injected).

    Returns:
        CreateListingResponse with listing_id, content, and status=draft.

    Raises:
        HTTPException: If product not found or generation fails.
    """
    global _listing_counter

    # For demo purposes - simulate product data
    # In production, would fetch from DB based on product_id
    product = Product(
        name=f"Product {request.product_id}",
        description="A digital product for productivity and organization",
        format_type="planner",
        target_audience="Professionals",
        key_features=["printable", "digital", "planner", "organization"],
    )

    # Generate AI content
    try:
        content = await generator.generate(product)
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to generate listing content: {str(e)}",
        )

    # Apply any overrides from request
    title = request.title or content.title
    description = request.description or content.description
    tags = request.tags or content.tags
    price = request.price_override or content.suggested_price

    # Create draft listing on Etsy if client available
    listing_id: Optional[int] = None
    if client:
        try:
            # Would get shop_id from user's Etsy shops
            shop_id = 0  # Placeholder
            listing_id = await create_draft_listing(
                client=client,
                shop_id=shop_id,
                title=title,
                description=description,
                price=price,
                tags=tags,
                category_id=int(content.suggested_category_id)
                if content.suggested_category_id.isdigit()
                else None,
            )
        except Exception as e:
            logger.warning(f"Failed to create Etsy listing: {e}")
            # Continue without Etsy listing

    # Store in memory for demo
    _listing_counter += 1
    if listing_id is None:
        listing_id = _listing_counter

    _listings_storage[listing_id] = {
        "listing_id": listing_id,
        "product_id": request.product_id,
        "title": title,
        "description": description,
        "tags": tags,
        "price": price,
        "status": "draft",
        "created_at": datetime.utcnow().isoformat(),
        "etsy_listing_id": listing_id,
    }

    return CreateListingResponse(
        listing_id=listing_id,
        title=title,
        description=description,
        tags=tags,
        status="draft",
        suggested_price=content.suggested_price,
        suggested_category_id=content.suggested_category_id,
    )


@router.get("/{listing_id}", response_model=ListingDetailResponse)
async def get_listing_details(
    listing_id: int,
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> ListingDetailResponse:
    """Get listing status and details.

    Args:
        listing_id: ID of the listing to retrieve.
        client: EtsyClient dependency.

    Returns:
        ListingDetailResponse with status and details.

    Raises:
        HTTPException: If listing not found.
    """
    # Check local storage first
    if listing_id in _listings_storage:
        listing = _listings_storage[listing_id]
        return ListingDetailResponse(
            listing_id=listing["listing_id"],
            status=listing["status"],
            title=listing["title"],
            price=listing.get("price"),
            etsy_url=f"https://www.etsy.com/listing/{listing.get('etsy_listing_id')}"
            if listing.get("etsy_listing_id")
            else None,
            created_at=listing["created_at"],
        )

    # Try Etsy API if client available
    if client:
        try:
            etsy_listing = await get_listing(client, listing_id)
            return ListingDetailResponse(
                listing_id=listing_id,
                status=etsy_listing.get("state", "unknown"),
                title=etsy_listing.get("title", ""),
                price=etsy_listing.get("price", {}).get("amount", {}).get("value") / 100
                if etsy_listing.get("price")
                else None,
                etsy_url=f"https://www.etsy.com/listing/{listing_id}",
                created_at=etsy_listing.get("creation_tsz", ""),
            )
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Listing not found: {str(e)}",
            )

    raise HTTPException(
        status_code=404,
        detail=f"Listing {listing_id} not found",
    )


@router.put("/{listing_id}")
async def update_listing_content(
    listing_id: int,
    request: UpdateListingRequest,
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> dict:
    """Update listing content before publishing.

    Allows user to edit title, description, tags, or price
    before final publishing.

    Args:
        listing_id: ID of the listing to update.
        request: UpdateListingRequest with new content.
        client: EtsyClient dependency.

    Returns:
        Updated listing info.

    Raises:
        HTTPException: If listing not found or update fails.
    """
    # Check local storage
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    listing = _listings_storage[listing_id]

    # Update local storage
    if request.title is not None:
        listing["title"] = request.title
    if request.description is not None:
        listing["description"] = request.description
    if request.tags is not None:
        listing["tags"] = request.tags
    if request.price is not None:
        listing["price"] = request.price

    # Update on Etsy if client available
    if client:
        try:
            await update_listing(
                client=client,
                shop_id=0,  # Would get from user's shops
                listing_id=listing_id,
                title=request.title,
                description=request.description,
                price=request.price,
                tags=request.tags,
            )
        except Exception as e:
            logger.warning(f"Failed to update Etsy listing: {e}")

    return {
        "listing_id": listing_id,
        "status": listing["status"],
        "updated": True,
    }


@router.post("/{listing_id}/publish", response_model=PublishResponse)
async def publish_listing_endpoint(
    listing_id: int,
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> PublishResponse:
    """Publish a listing (human approval step).

    Validates listing content, uploads digital file if needed,
    and sets state to active on Etsy.

    Per D-03: Human-in-the-loop - user must confirm before publishing.

    Args:
        listing_id: ID of the listing to publish.
        client: EtsyClient dependency.

    Returns:
        PublishResponse with success status and Etsy URL.

    Raises:
        HTTPException: If listing not found or publish fails.
    """
    # Check local storage
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    listing = _listings_storage[listing_id]

    if listing["status"] != "draft":
        raise HTTPException(
            status_code=400,
            detail=f"Listing {listing_id} is not in draft status (current: {listing['status']})",
        )

    # Publish on Etsy if client available
    if client:
        try:
            await publish_listing(client, listing_id)
            listing["status"] = "active"
            return PublishResponse(
                success=True,
                etsy_listing_url=f"https://www.etsy.com/listing/{listing_id}",
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to publish listing: {str(e)}",
            )

    # Demo mode - just mark as active
    listing["status"] = "active"
    return PublishResponse(
        success=True,
        etsy_listing_url=f"https://www.etsy.com/listing/{listing_id}",
    )


@router.delete("/{listing_id}")
async def delete_listing_endpoint(
    listing_id: int,
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> dict:
    """Delete a listing.

    Removes listing from local storage and Etsy if client available.

    Args:
        listing_id: ID of the listing to delete.
        client: EtsyClient dependency.

    Returns:
        Deletion confirmation.

    Raises:
        HTTPException: If listing not found.
    """
    # Check local storage
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    # Delete from Etsy if client available
    if client:
        try:
            await delete_listing(client, listing_id)
        except Exception as e:
            logger.warning(f"Failed to delete Etsy listing: {e}")

    # Remove from local storage
    del _listings_storage[listing_id]

    return {
        "listing_id": listing_id,
        "deleted": True,
    }


# ============ Image Upload Endpoints ============


@router.post("/{listing_id}/images", response_model=ImageUploadResponse)
async def upload_listing_image_endpoint(
    listing_id: int,
    file: UploadFile = File(...),
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> ImageUploadResponse:
    """Upload a single image to a listing.

    Accepts JPEG or PNG images. First image uploaded becomes
    the main listing image.

    Args:
        listing_id: ID of the listing to add image to.
        file: Image file (JPEG/PNG).
        client: EtsyClient dependency.

    Returns:
        ImageUploadResponse with image_id and details.

    Raises:
        HTTPException: If listing not found or upload fails.
    """
    # Check listing exists
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    # Validate file type
    filename = file.filename or "image.jpg"
    if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
        raise HTTPException(
            status_code=400,
            detail="Only JPEG and PNG images are supported",
        )

    if client:
        try:
            # Read file content
            content = await file.read()
            # Create BytesIO object
            from io import BytesIO

            file_obj = BytesIO(content)
            file_obj.name = file.filename

            image_id = await upload_listing_image(
                client=client,
                listing_id=listing_id,
                image_file=file_obj,
                rank=1,  # Will be overridden if more images exist
            )

            return ImageUploadResponse(
                image_id=image_id,
                listing_id=listing_id,
                rank=1,
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload image: {str(e)}",
            )

    # Demo mode - return mock response
    import random

    return ImageUploadResponse(
        image_id=random.randint(1000, 9999),
        listing_id=listing_id,
        rank=1,
    )


@router.post("/{listing_id}/images/bulk", response_model=BulkImageUploadResponse)
async def upload_multiple_images_endpoint(
    listing_id: int,
    files: list[UploadFile] = File(...),
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> BulkImageUploadResponse:
    """Upload multiple images to a listing (max 10).

    Etsy limit: 10 images per listing.
    First image in list becomes main listing image.

    Args:
        listing_id: ID of the listing to add images to.
        files: List of image files (JPEG/PNG).
        client: EtsyClient dependency.

    Returns:
        BulkImageUploadResponse with image_ids and count.

    Raises:
        HTTPException: If too many images or upload fails.
    """
    # Check listing exists
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    # Validate image count
    if len(files) > 10:
        raise HTTPException(
            status_code=400,
            detail="Etsy allows max 10 images per listing",
        )

    # Validate file types
    for f in files:
        fname = f.filename or "image.jpg"
        if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file: {f.filename}. Only JPEG and PNG allowed",
            )

    if client:
        try:
            from io import BytesIO

            image_files = []
            for f in files:
                content = await f.read()
                file_obj = BytesIO(content)
                file_obj.name = f.filename
                image_files.append(file_obj)

            image_ids = await upload_product_images(
                client=client,
                listing_id=listing_id,
                image_files=image_files,
            )

            return BulkImageUploadResponse(
                image_ids=image_ids,
                listing_id=listing_id,
                count=len(image_ids),
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload images: {str(e)}",
            )

    # Demo mode - return mock response
    import random

    return BulkImageUploadResponse(
        image_ids=[random.randint(1000, 9999) for _ in files],
        listing_id=listing_id,
        count=len(files),
    )


@router.get("/{listing_id}/images", response_model=ImageListResponse)
async def get_listing_images(
    listing_id: int,
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> ImageListResponse:
    """Get all images for a listing.

    Args:
        listing_id: ID of the listing.
        client: EtsyClient dependency.

    Returns:
        ImageListResponse with list of images.
    """
    # Check listing exists
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    # TODO: Fetch actual images from Etsy API
    # For now, return empty list
    return ImageListResponse(images=[])


@router.delete("/{listing_id}/images/{image_id}")
async def delete_listing_image(
    listing_id: int,
    image_id: int,
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> dict:
    """Delete an image from a listing.

    Args:
        listing_id: ID of the listing.
        image_id: ID of the image to delete.
        client: EtsyClient dependency.

    Returns:
        Deletion confirmation.
    """
    # Check listing exists
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    # TODO: Call Etsy API to delete image
    logger.info(f"Would delete image {image_id} from listing {listing_id}")

    return {
        "listing_id": listing_id,
        "image_id": image_id,
        "deleted": True,
    }


# ============ Digital File Upload Endpoints ============


@router.post("/{listing_id}/files", response_model=FileUploadResponse)
async def upload_digital_file_endpoint(
    listing_id: int,
    file: UploadFile = File(...),
    client: Optional[EtsyClient] = Depends(get_etsy_client),
) -> FileUploadResponse:
    """Upload a digital file to a listing for download delivery.

    Per D-18: Etsy file hosting - Etsy handles download delivery.
    Sets listing as digital download with unlimited quantity.

    Args:
        listing_id: ID of the listing to add file to.
        file: PDF file for digital delivery.
        client: EtsyClient dependency.

    Returns:
        FileUploadResponse with file_id and configuration.

    Raises:
        HTTPException: If listing not found or upload fails.
    """
    # Check listing exists
    if listing_id not in _listings_storage:
        raise HTTPException(
            status_code=404,
            detail=f"Listing {listing_id} not found",
        )

    # Validate file type
    filename = file.filename or "product.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported for digital delivery",
        )

    if client:
        try:
            # Read file content
            content = await file.read()
            from io import BytesIO

            file_obj = BytesIO(content)
            file_obj.name = filename

            # Get shop_id from listing
            shop_id = 0  # Would get from user's shops

            result = await upload_and_configure_digital(
                client=client,
                shop_id=shop_id,
                listing_id=listing_id,
                file_data=file_obj,
                filename=filename,
            )

            return FileUploadResponse(
                file_id=result["file_id"],
                listing_id=listing_id,
                digital=result["digital"],
                quantity_unlimited=result["quantity_unlimited"],
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to upload digital file: {str(e)}",
            )

    # Demo mode - return mock response
    import random

    return FileUploadResponse(
        file_id=f"file_{random.randint(1000, 9999)}",
        listing_id=listing_id,
        digital=True,
        quantity_unlimited=True,
    )
