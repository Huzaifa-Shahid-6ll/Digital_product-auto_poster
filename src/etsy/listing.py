"""Etsy listing operations module.

Higher-level listing operations that wrap EtsyClient.
Provides create, update, publish, and get operations.

Per D-04: 3 retries with exponential backoff (handled by EtsyClient).
"""

import logging
from typing import Any, Optional

from src.etsy.client import EtsyClient

logger = logging.getLogger(__name__)


class ListingOperationsError(Exception):
    """Error during listing operations."""

    pass


async def create_draft_listing(
    client: EtsyClient,
    shop_id: int,
    title: str,
    description: str,
    price: float,
    tags: list[str],
    category_id: Optional[int] = None,
    file_upload: Optional[Any] = None,
    image_files: Optional[list[Any]] = None,
) -> int:
    """Create a draft listing on Etsy.

    Args:
        client: EtsyClient instance.
        shop_id: Etsy shop ID.
        title: Listing title (max 400 chars).
        description: Listing description.
        price: Price in USD.
        tags: List of tags (max 13).
        category_id: Optional Etsy category ID.
        file_upload: Optional file-like object for digital download.
        image_files: Optional list of image file objects.

    Returns:
        listing_id: The ID of the created listing.

    Raises:
        ListingOperationsError: If creation fails.
    """
    try:
        result = await client.create_draft_listing(
            shop_id=shop_id,
            title=title,
            description=description,
            price=price,
            tags=tags,
            category_id=category_id,
            file_upload=file_upload,
            image_files=image_files,
        )
        listing_id = result.get("listing_id")
        if not listing_id:
            raise ListingOperationsError(f"No listing_id in response: {result}")
        logger.info(f"Created draft listing {listing_id} for shop {shop_id}")
        return listing_id
    except Exception as e:
        raise ListingOperationsError(f"Failed to create draft listing: {e}") from e


async def update_listing(
    client: EtsyClient,
    shop_id: int,
    listing_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    price: Optional[float] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Update a listing's content.

    Args:
        client: EtsyClient instance.
        shop_id: Etsy shop ID.
        listing_id: Listing ID to update.
        title: Optional new title.
        description: Optional new description.
        price: Optional new price.
        tags: Optional new tags.

    Returns:
        Updated listing dict.

    Raises:
        ListingOperationsError: If update fails.
    """
    # Note: shop_id not needed for update - listing_id is sufficient
    # but we keep it for API consistency
    try:
        result = await client.update_listing(
            listing_id=listing_id,
            title=title,
            description=description,
            price=price,
            tags=tags,
        )
        logger.info(f"Updated listing {listing_id}")
        return result
    except Exception as e:
        raise ListingOperationsError(f"Failed to update listing {listing_id}: {e}") from e


async def publish_listing(client: EtsyClient, listing_id: int) -> dict:
    """Publish a listing (set state to active).

    Per D-18: After file upload, set type="download" for digital.
    Note: Etsy API handles this automatically when file is uploaded.

    Args:
        client: EtsyClient instance.
        listing_id: Listing ID to publish.

    Returns:
        Updated listing dict with state=active.

    Raises:
        ListingOperationsError: If publish fails.
    """
    try:
        result = await client.publish_listing(listing_id)
        logger.info(f"Published listing {listing_id}")
        return result
    except Exception as e:
        raise ListingOperationsError(f"Failed to publish listing {listing_id}: {e}") from e


async def get_listing(client: EtsyClient, listing_id: int) -> dict:
    """Get listing details and status.

    Args:
        client: EtsyClient instance.
        listing_id: Listing ID to retrieve.

    Returns:
        Listing dict with all details including state/status.

    Raises:
        ListingOperationsError: If retrieval fails.
    """
    try:
        result = await client.get_listing(listing_id)
        return result
    except Exception as e:
        raise ListingOperationsError(f"Failed to get listing {listing_id}: {e}") from e


async def delete_listing(client: EtsyClient, listing_id: int) -> dict:
    """Delete a listing (remove from shop).

    Note: Etsy API doesn't have a direct delete - use state=draft
    and then delete via Etsy dashboard, or use delete endpoint.

    Args:
        client: EtsyClient instance.
        listing_id: Listing ID to delete.

    Returns:
        Deletion result dict.

    Raises:
        ListingOperationsError: If deletion fails.
    """
    # Try to delete - if no delete endpoint exists, this may fail
    # Etsy typically uses DELETE /listings/{listing_id}
    try:
        # Use EtsyClient's internal request method
        result = await client._request("DELETE", f"/application/listings/{listing_id}")
        logger.info(f"Deleted listing {listing_id}")
        return result
    except Exception as e:
        raise ListingOperationsError(f"Failed to delete listing {listing_id}: {e}") from e


async def upload_digital_file(
    client: EtsyClient,
    listing_id: int,
    file_data: Any,
    filename: str,
) -> dict:
    """Upload a digital file to a listing.

    Per D-18: Etsy file hosting - upload PDF to Etsy.

    Args:
        client: EtsyClient instance.
        listing_id: Listing ID.
        file_data: File-like object with file data.
        filename: Name for the file.

    Returns:
        File upload result dict.

    Raises:
        ListingOperationsError: If upload fails.
    """
    try:
        result = await client.upload_file(listing_id, file_data, filename)
        logger.info(f"Uploaded digital file {filename} to listing {listing_id}")
        return result
    except Exception as e:
        raise ListingOperationsError(f"Failed to upload digital file: {e}") from e


async def upload_listing_image(
    client: EtsyClient,
    listing_id: int,
    image_file: Any,
    rank: int = 1,
) -> dict:
    """Upload an image to a listing.

    Per D-03: Upload images to Etsy CDN.

    Args:
        client: EtsyClient instance.
        listing_id: Listing ID.
        image_file: File-like object with image data.
        rank: Image rank (1-based).

    Returns:
        Image upload result dict.

    Raises:
        ListingOperationsError: If upload fails.
    """
    try:
        result = await client.upload_image(listing_id, image_file, rank)
        logger.info(f"Uploaded image to listing {listing_id} at rank {rank}")
        return result
    except Exception as e:
        raise ListingOperationsError(f"Failed to upload image: {e}") from e
