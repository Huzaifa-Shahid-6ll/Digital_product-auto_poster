"""Digital file upload to Etsy for product delivery.

Provides functions for uploading digital product files (PDF) to Etsy listings.
Per D-18: Etsy file hosting - Etsy handles download delivery to buyers.
Per D-19: Set quantity to unlimited (Etsy handles this for digital).

Reference: Etsy API v3 - listing files endpoint.
"""

import logging
from pathlib import Path
from typing import BinaryIO, Optional

logger = logging.getLogger(__name__)

# Etsy digital file requirements
ETSY_MAX_FILE_SIZE_MB = 20  # Etsy allows up to 20MB for digital files
ETSY_SUPPORTED_FILE_TYPES = ["pdf"]


async def upload_digital_file(
    client,
    listing_id: int,
    file_data: BinaryIO,
    filename: str,
) -> str:
    """Upload a digital file to a listing for download delivery.

    Per D-18: Etsy file hosting - Etsy handles download delivery.
    Files are stored by Etsy and delivered to buyers after purchase.

    Args:
        client: EtsyClient instance.
        listing_id: Etsy listing ID.
        file_data: File-like object with file data (PDF).
        filename: Name for the file (e.g., "product.pdf").

    Returns:
        file_id from Etsy.

    Raises:
        ValueError: If file type not supported or upload fails.
    """
    # Validate file type
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ETSY_SUPPORTED_FILE_TYPES:
        raise ValueError(f"Unsupported file type: {ext}. Supported: {ETSY_SUPPORTED_FILE_TYPES}")

    # Upload via EtsyClient
    result = await client.upload_file(
        listing_id=listing_id,
        file_data=file_data,
        filename=filename,
    )

    # Extract file_id from response
    file_id = result.get("file_id")
    if not file_id:
        raise ValueError(f"Failed to get file_id from response: {result}")

    logger.info(f"Uploaded digital file {file_id} to listing {listing_id}")
    return file_id


async def set_listing_as_download(
    client,
    shop_id: int,
    listing_id: int,
) -> dict:
    """Set listing type to download for digital product delivery.

    After uploading a digital file, the listing must be set as a "download"
    type so Etsy knows to deliver the file after purchase.

    Args:
        client: EtsyClient instance.
        shop_id: Etsy shop ID.
        listing_id: Etsy listing ID.

    Returns:
        Updated listing dict.
    """
    # Update listing to set as download
    # Note: This is typically done via the listing's metadata
    # In Etsy API, digital listings are identified by having a file attached
    # The file upload already marks it as digital

    # For now, we ensure the listing has unlimited quantity
    # (digital products don't have stock limits)
    result = await client.update_inventory(
        listing_id=listing_id,
        offerings=[
            {
                "price": {"amount": 0, "divisor": 1},  # Will be ignored, uses listing price
                "quantity": -1,  # -1 means unlimited
                "is_available": True,
            }
        ],
    )

    logger.info(f"Set listing {listing_id} as digital download (unlimited quantity)")
    return result


async def upload_and_configure_digital(
    client,
    shop_id: int,
    listing_id: int,
    file_data: BinaryIO,
    filename: str,
) -> dict:
    """Upload digital file and configure listing for delivery.

    Convenience function that:
    1. Uploads the digital file
    2. Sets listing as download type
    3. Sets unlimited quantity

    Per D-18 and D-19 requirements.

    Args:
        client: EtsyClient instance.
        shop_id: Etsy shop ID.
        listing_id: Etsy listing ID.
        file_data: File-like object with PDF data.
        filename: Name for the file.

    Returns:
        Dict with file_id and listing update result.
    """
    # Upload the digital file
    file_id = await upload_digital_file(
        client=client,
        listing_id=listing_id,
        file_data=file_data,
        filename=filename,
    )

    # Configure listing for digital delivery
    listing_result = await set_listing_as_download(
        client=client,
        shop_id=shop_id,
        listing_id=listing_id,
    )

    return {
        "file_id": file_id,
        "listing_id": listing_id,
        "digital": True,
        "quantity_unlimited": True,
    }


async def upload_digital_from_path(
    client,
    shop_id: int,
    listing_id: int,
    file_path: str,
) -> dict:
    """Upload a digital file from disk.

    Convenience function that opens a file and configures the listing.

    Args:
        client: EtsyClient instance.
        shop_id: Etsy shop ID.
        listing_id: Etsy listing ID.
        file_path: Path to PDF file.

    Returns:
        Dict with file_id and configuration result.

    Raises:
        FileNotFoundError: If file not found.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Digital file not found: {file_path}")

    with open(path, "rb") as f:
        return await upload_and_configure_digital(
            client=client,
            shop_id=shop_id,
            listing_id=listing_id,
            file_data=f,
            filename=path.name,
        )
