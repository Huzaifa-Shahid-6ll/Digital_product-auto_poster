"""Image upload to Etsy CDN.

Provides functions for uploading product images to Etsy listings.
Per D-03: Upload to Etsy CDN.
Per D-04: Product images from Phase 2 get uploaded.

Reference: Etsy API v3 - listing images endpoint.
"""

import logging
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional

logger = logging.getLogger(__name__)

# Etsy image requirements
ETSY_MAX_IMAGES = 10
ETSY_SUPPORTED_FORMATS = ["jpeg", "jpg", "png"]


async def upload_listing_image(
    client,
    listing_id: int,
    image_file: BinaryIO,
    rank: int = 1,
) -> int:
    """Upload a single image to a listing.

    Args:
        client: EtsyClient instance.
        listing_id: Etsy listing ID.
        image_file: File-like object with image data (JPEG/PNG).
        rank: Image rank (1-based). First image = main listing image.

    Returns:
        image_id from Etsy.

    Raises:
        ValueError: If image format not supported.
    """
    # Validate format
    filename = getattr(image_file, "name", "image.jpg")
    ext = Path(filename).suffix.lower().lstrip(".")

    if ext not in ETSY_SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported image format: {ext}. Supported: {ETSY_SUPPORTED_FORMATS}")

    # Upload via EtsyClient
    result = await client.upload_image(
        listing_id=listing_id,
        image_file=image_file,
        rank=rank,
    )

    # Extract image_id from response
    image_id = result.get("image_id")
    if not image_id:
        raise ValueError(f"Failed to get image_id from response: {result}")

    logger.info(f"Uploaded image {image_id} to listing {listing_id} (rank={rank})")
    return image_id


async def upload_product_images(
    client,
    listing_id: int,
    image_files: list[BinaryIO],
) -> list[int]:
    """Upload multiple images to a listing.

    Per Etsy limit: max 10 images per listing.
    First image uploaded becomes main listing image.

    Args:
        client: EtsyClient instance.
        listing_id: Etsy listing ID.
        image_files: List of file-like objects with image data.

    Returns:
        List of image_ids from Etsy.

    Raises:
        ValueError: If more than 10 images provided.
    """
    if len(image_files) > ETSY_MAX_IMAGES:
        raise ValueError(f"Too many images: {len(image_files)}. Etsy limit: {ETSY_MAX_IMAGES}")

    image_ids = []
    for i, image_file in enumerate(image_files):
        rank = i + 1  # 1-based ranking
        image_id = await upload_listing_image(
            client=client,
            listing_id=listing_id,
            image_file=image_file,
            rank=rank,
        )
        image_ids.append(image_id)

    logger.info(f"Uploaded {len(image_ids)} images to listing {listing_id}")
    return image_ids


def convert_pdf_to_images(
    pdf_path: str,
    output_dir: Optional[str] = None,
    dpi: int = 150,
    fmt: str = "PNG",
) -> list[str]:
    """Convert PDF pages to images for Etsy upload.

    Per D-04: Product images from Phase 2 (PDF preview) get uploaded.
    Uses pdf2image to convert PDF to image files.
    Etsy prefers square images, but will auto-crop.

    Args:
        pdf_path: Path to PDF file.
        output_dir: Directory to save images. If None, uses temp directory.
        dpi: Resolution for conversion (default 150).
        fmt: Output image format (default PNG).

    Returns:
        List of paths to generated image files.

    Raises:
        ImportError: If pdf2image not installed.
        FileNotFoundError: If PDF file not found.
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning("pdf2image not installed. Install with: pip install pdf2image")
        return []

    pdf = Path(pdf_path)
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Determine output directory
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = pdf.parent / f"{pdf.stem}_images"

    output_path.mkdir(parents=True, exist_ok=True)

    # Convert PDF to images
    images = convert_from_path(
        pdf_path,
        dpi=dpi,
        fmt=fmt.lower(),
        output_folder=str(output_path),
        output_prefix=pdf.stem,
    )

    # Save images to files
    image_paths = []
    for i, image in enumerate(images):
        # Limit to 10 images (Etsy max)
        if i >= ETSY_MAX_IMAGES:
            logger.warning(f"Limiting to {ETSY_MAX_IMAGES} images (Etsy limit)")
            break

        image_path = output_path / f"{pdf.stem}_{i + 1}.{fmt.lower()}"
        image.save(str(image_path), fmt.upper())
        image_paths.append(str(image_path))

    logger.info(f"Converted {len(image_paths)} pages from {pdf_path} to images")
    return image_paths


async def upload_from_path(
    client,
    listing_id: int,
    image_path: str,
    rank: int = 1,
) -> int:
    """Upload an image file from disk.

    Convenience function that opens a file and uploads it.

    Args:
        client: EtsyClient instance.
        listing_id: Etsy listing ID.
        image_path: Path to image file.
        rank: Image rank (1-based).

    Returns:
        image_id from Etsy.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with open(path, "rb") as f:
        return await upload_listing_image(
            client=client,
            listing_id=listing_id,
            image_file=f,
            rank=rank,
        )


async def upload_multiple_from_paths(
    client,
    listing_id: int,
    image_paths: list[str],
) -> list[int]:
    """Upload multiple image files from disk.

    Convenience function that opens files and uploads them.

    Args:
        client: EtsyClient instance.
        listing_id: Etsy listing ID.
        image_paths: List of paths to image files.

    Returns:
        List of image_ids from Etsy.
    """
    image_files = []
    for path_str in image_paths:
        path = Path(path_str)
        if not path.exists():
            logger.warning(f"Image not found, skipping: {path_str}")
            continue
        image_files.append(open(path, "rb"))

    # Close files after upload
    try:
        return await upload_product_images(
            client=client,
            listing_id=listing_id,
            image_files=image_files,
        )
    finally:
        for f in image_files:
            f.close()
