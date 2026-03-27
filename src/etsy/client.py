"""Etsy API client with automatic token refresh.

Provides wrapper around Etsy API v3 with:
- Automatic token refresh before expiration
- Retry logic with exponential backoff (per D-04)
- All listing operations

Reference: Etsy API v3 documentation
"""

import logging
import time
from typing import BinaryIO, Optional

import httpx

from src.etsy.oauth import EtsyOAuth

logger = logging.getLogger(__name__)

# Etsy API base URL
ETSY_API_BASE = "https://api.etsy.com/v3/application"


class EtsyClient:
    """Etsy API client with token auto-refresh.

    Wraps Etsy API v3 with automatic token management.
    All API calls use get_valid_token() before making requests.

    Example:
        >>> oauth = EtsyOAuth("id", "secret", "http://localhost")
        >>> oauth.set_refresh_token("stored_token")
        >>> client = EtsyClient(oauth)
        >>> shops = client.get_shops()
    """

    def __init__(self, oauth: EtsyOAuth):
        """Initialize EtsyClient.

        Args:
            oauth: EtsyOAuth instance with valid tokens.
        """
        self._oauth = oauth

        # Per D-04: 3 retries with exponential backoff
        self._max_retries = 3

        # httpx client for connection pooling
        self._http: Optional[httpx.AsyncClient] = None

    async def _get_http(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http is None:
            self._http = httpx.AsyncClient(timeout=30.0)
        return self._http

    async def close(self):
        """Close the HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None

    def _get_auth_header(self) -> dict:
        """Get authorization header with valid token."""
        token = self._oauth.get_valid_token()
        return {"Authorization": f"Bearer {token}"}

    def _get_api_key_header(self) -> dict:
        """Get x-api-key header."""
        # Format: base64(client_id:client_secret)
        import base64

        credentials = f"{self._oauth.client_id}:{self._oauth.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"x-api-key": encoded}

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> dict:
        """Make API request with token refresh and retry logic.

        Per D-04: 3 retries with exponential backoff.

        Args:
            method: HTTP method.
            path: API path (appended to base URL).
            **kwargs: Additional kwargs for httpx request.

        Returns:
            Response JSON dict.

        Raises:
            httpx.HTTPStatusError: If request fails after retries.
        """
        url = f"{ETSY_API_BASE}{path}"
        headers = {
            **self._get_api_key_header(),
            **self._get_auth_header(),
            **kwargs.pop("headers", {}),
        }

        http = await self._get_http()

        for attempt in range(self._max_retries):
            try:
                response = await http.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                # If 401, token likely expired - try refreshing once
                if e.response.status_code == 401 and attempt == 0:
                    logger.warning("Token expired, refreshing...")
                    self._oauth.refresh_access_token()
                    # Update auth header with new token
                    headers = {
                        **self._get_api_key_header(),
                        **self._get_auth_header(),
                        **kwargs.pop("headers", {}),
                    }
                    continue

                if attempt == self._max_retries - 1:
                    raise
                wait_time = 2**attempt
                logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                await http.aclose()
                self._http = httpx.AsyncClient(timeout=30.0)
                await time.sleep(wait_time)

        return response.json()

    # ============ Shop Operations ============

    async def get_shops(self) -> dict:
        """Get list of shops the authenticated user owns.

        Returns:
            Dict with count and results array.

        Example:
            >>> result = await client.get_shops()
            >>> for shop in result.get("results", []):
            ...     print(shop["shop_id"], shop["shop_name"])
        """
        return await self._request("GET", "/application/shops")

    async def get_shop(self, shop_id: int) -> dict:
        """Get specific shop details.

        Args:
            shop_id: Etsy shop ID.

        Returns:
            Shop data dict.
        """
        return await self._request("GET", f"/application/shops/{shop_id}")

    # ============ Listing Operations ============

    async def create_draft_listing(
        self,
        shop_id: int,
        title: str,
        description: str,
        price: float,
        tags: list[str],
        category_id: Optional[int] = None,
        file_upload: Optional[BinaryIO] = None,
        image_files: Optional[list[BinaryIO]] = None,
    ) -> dict:
        """Create a draft listing.

        Args:
            shop_id: Etsy shop ID.
            title: Listing title (max 400 chars).
            description: Listing description.
            price: Price in USD.
            tags: List of tags (max 13).
            category_id: Optional Etsy category ID.
            file_upload: Optional file-like object for digital download.
            image_files: Optional list of image file objects (max 10).

        Returns:
            Created listing dict with listing_id.

        Example:
            >>> listing = await client.create_draft_listing(
            ...     shop_id=12345,
            ...     title="My Digital Product",
            ...     description="Great product!",
            ...     price=9.99,
            ...     tags=["digital", "printable"],
            ... )
        """
        # Prepare listing data
        data = {
            "title": title,
            "description": description,
            "price": price,
            "tags": ",".join(tags),
            "who_made": "i_did",
            "is_supply": "false",
            "when_made": "made_to_order",
            "state": "draft",
        }

        if category_id:
            data["category_id"] = category_id

        files = {}

        # Add images if provided
        if image_files:
            for i, img in enumerate(image_files):
                files[f"image_{i}"] = (img.name, img.read(), "image/jpeg")

        # Add file upload if provided
        if file_upload:
            files["file"] = (file_upload.name, file_upload.read(), "application/octet-stream")

        return await self._request(
            "POST",
            f"/application/shops/{shop_id}/listings",
            data=data,
            files=files if files else None,
        )

    async def get_listing(self, listing_id: int) -> dict:
        """Get listing details.

        Args:
            listing_id: Etsy listing ID.

        Returns:
            Listing data dict.
        """
        return await self._request("GET", f"/application/listings/{listing_id}")

    async def update_listing(
        self,
        listing_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        tags: Optional[list[str]] = None,
        state: Optional[str] = None,
    ) -> dict:
        """Update a listing.

        Args:
            listing_id: Etsy listing ID.
            title: Optional new title.
            description: Optional new description.
            price: Optional new price.
            tags: Optional new tags.
            state: Optional new state ("draft", "active").

        Returns:
            Updated listing dict.
        """
        data = {}
        if title is not None:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if price is not None:
            data["price"] = price
        if tags is not None:
            data["tags"] = ",".join(tags)
        if state is not None:
            data["state"] = state

        return await self._request(
            "PUT",
            f"/application/listings/{listing_id}",
            data=data,
        )

    async def publish_listing(self, listing_id: int) -> dict:
        """Publish a listing (set state to active).

        Args:
            listing_id: Etsy listing ID.

        Returns:
            Updated listing dict.
        """
        return await self.update_listing(listing_id, state="active")

    # ============ Image Operations ============

    async def upload_image(
        self,
        listing_id: int,
        image_file: BinaryIO,
        rank: int = 1,
    ) -> dict:
        """Upload an image to a listing.

        Args:
            listing_id: Etsy listing ID.
            image_file: File-like object with image data.
            rank: Image rank (1-based).

        Returns:
            Image upload result dict.
        """
        files = {
            "image": (image_file.name, image_file.read(), "image/jpeg"),
        }
        data = {"rank": rank}

        return await self._request(
            "POST",
            f"/application/listings/{listing_id}/images",
            data=data,
            files=files,
        )

    # ============ File Operations (Digital Downloads) ============

    async def upload_file(
        self,
        listing_id: int,
        file_data: BinaryIO,
        filename: str,
    ) -> dict:
        """Upload a digital file to a listing.

        Args:
            listing_id: Etsy listing ID.
            file_data: File-like object with file data.
            filename: Name for the file.

        Returns:
            File upload result dict.
        """
        files = {
            "file": (filename, file_data.read(), "application/octet-stream"),
        }

        return await self._request(
            "POST",
            f"/application/listings/{listing_id}/files",
            files=files,
        )

    # ============ Inventory Operations ============

    async def get_inventory(self, listing_id: int) -> dict:
        """Get listing inventory.

        Args:
            listing_id: Etsy listing ID.

        Returns:
            Inventory data dict.
        """
        return await self._request("GET", f"/application/listings/{listing_id}/inventory")

    async def update_inventory(
        self,
        listing_id: int,
        offerings: list[dict],
    ) -> dict:
        """Update listing offerings (price, quantity, etc).

        Args:
            listing_id: Etsy listing ID.
            offerings: List of offering dicts with price and quantity.

        Returns:
            Updated inventory dict.
        """
        data = {"offerings": offerings}

        return await self._request(
            "PUT",
            f"/application/listings/{listing_id}/inventory",
            json=data,
        )
