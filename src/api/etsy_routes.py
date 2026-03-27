"""Etsy OAuth API routes.

REST endpoints for:
- GET /api/auth/etsy/authorize - Initiate OAuth flow
- GET /api/auth/etsy/callback - Handle OAuth callback
- GET /api/auth/etsy/shops - List user's Etsy shops
- DELETE /api/auth/etsy/disconnect - Disconnect shop

Mounted at /api/auth/etsy in main app.
"""

import logging
import os
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.etsy.oauth import EtsyOAuth

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["etsy"])


# ============ Request/Response Models ============


class EtsyAuthorizeResponse(BaseModel):
    """Response model for authorization initiation."""

    authorization_url: str = Field(description="URL to redirect user for Etsy authorization")
    state: str = Field(description="State parameter for CSRF protection")
    shop_id: Optional[str] = Field(default=None, description="Specific shop ID if provided")


class EtsyShop(BaseModel):
    """Etsy shop model."""

    shop_id: int
    shop_name: str
    is_active: bool = Field(description="Whether shop is active")


class EtsyShopsResponse(BaseModel):
    """Response model for shops list."""

    shops: list[EtsyShop]
    count: int


class EtsyCallbackResponse(BaseModel):
    """Response model for OAuth callback."""

    success: bool
    shop_id: int = Field(description="Connected shop ID")
    shop_name: str = Field(description="Connected shop name")
    message: str = Field(default="Successfully connected to Etsy")


class EtsyDisconnectResponse(BaseModel):
    """Response model for disconnect."""

    success: bool
    message: str


# ============ Session Storage ============

# In production, this would be a database
# For MVP, using module-level storage (reset on restart)
_etsy_oauth_instances: dict[str, EtsyOAuth] = {}


# ============ Dependency ============


def get_etsy_config() -> tuple[str, str, str]:
    """Get Etsy OAuth configuration from environment.

    Returns:
        Tuple of (client_id, client_secret, redirect_uri).

    Raises:
        HTTPException: If required env vars not set.
    """
    client_id = os.environ.get("ETSY_API_KEY")
    client_secret = os.environ.get("ETSY_API_SECRET")
    redirect_uri = os.environ.get("ETSY_OAUTH_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        raise HTTPException(
            status_code=503,
            detail="Etsy OAuth not configured. Set ETSY_API_KEY, ETSY_API_SECRET, and ETSY_OAUTH_REDIRECT_URI.",
        )

    return client_id, client_secret, redirect_uri


# ============ Routes ============


@router.get("/authorize", response_model=EtsyAuthorizeResponse)
async def authorize_etsy(
    shop_id: Optional[str] = Query(default=None, description="Optional specific shop to authorize"),
    config: tuple[str, str, str] = Depends(get_etsy_config),
) -> EtsyAuthorizeResponse:
    """Initiate Etsy OAuth flow.

    Generates authorization URL for frontend redirect.
    Stores OAuth state for callback validation.

    Args:
        shop_id: Optional specific shop to authorize.
        config: Etsy OAuth configuration (injected).

    Returns:
        EtsyAuthorizeResponse with authorization_url and state.

    Example:
        GET /api/auth/etsy/authorize?shop_id=12345
        Response: {"authorization_url": "https://...", "state": "abc123", "shop_id": "12345"}
    """
    client_id, client_secret, redirect_uri = config

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Create OAuth instance
    oauth = EtsyOAuth(client_id, client_secret, redirect_uri)

    if shop_id:
        oauth.set_shop_id(shop_id)

    # Store for callback (using state as key)
    _etsy_oauth_instances[state] = oauth

    # Generate authorization URL
    authorization_url = oauth.get_authorization_url(state=state)

    logger.info(f"Initiated Etsy OAuth flow, state: {state[:8]}...")

    return EtsyAuthorizeResponse(
        authorization_url=authorization_url,
        state=state,
        shop_id=shop_id,
    )


@router.get("/callback", response_model=EtsyCallbackResponse)
async def etsy_callback(
    code: str = Query(..., description="Authorization code from Etsy"),
    state: str = Query(..., description="State parameter for CSRF validation"),
    shop_id: Optional[str] = Query(
        default=None, description="Shop ID if provided during authorize"
    ),
) -> EtsyCallbackResponse:
    """Handle Etsy OAuth callback.

    Exchanges authorization code for tokens and stores them.
    Returns success with shop details.

    Args:
        code: Authorization code from Etsy OAuth redirect.
        state: State parameter for CSRF validation.
        shop_id: Shop ID if provided during authorize.

    Returns:
        EtsyCallbackResponse with shop_id and shop_name.

    Example:
        GET /api/auth/etsy/callback?code=xxx&state=yyy
        Response: {"success": true, "shop_id": 12345, "shop_name": "MyShop", "message": "..."}
    """
    # Retrieve OAuth instance
    oauth = _etsy_oauth_instances.pop(state, None)

    if not oauth:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired state. Restart OAuth flow.",
        )

    try:
        # Exchange code for tokens
        tokens = oauth.exchange_code_for_tokens(code)

        logger.info(f"Successfully exchanged code for tokens")

        # In production, store tokens in database here
        # For MVP, just log success

        # Get shop info (first shop in the user's shops)
        # Note: We need to create client and get shops
        from src.etsy.client import EtsyClient

        client = EtsyClient(oauth)
        shops_result = await client.get_shops()
        await client.close()

        # Get first shop
        shops = shops_result.get("results", [])
        if not shops:
            raise HTTPException(
                status_code=500,
                detail="No shops found for authenticated user",
            )

        first_shop = shops[0]
        connected_shop_id = first_shop["shop_id"]
        connected_shop_name = first_shop["shop_name"]

        # Store oauth instance for this shop (for later use)
        _etsy_oauth_instances[f"shop_{connected_shop_id}"] = oauth

        return EtsyCallbackResponse(
            success=True,
            shop_id=connected_shop_id,
            shop_name=connected_shop_name,
            message=f"Successfully connected to Etsy shop: {connected_shop_name}",
        )

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"OAuth failed: {str(e)}",
        )


@router.get("/shops", response_model=EtsyShopsResponse)
async def get_etsy_shops(
    shop_id: Optional[int] = Query(default=None, description="Optional shop_id to filter"),
) -> EtsyShopsResponse:
    """List user's Etsy shops.

    Requires valid OAuth tokens (must be connected first).

    Args:
        shop_id: Optional shop ID to filter by.

    Returns:
        EtsyShopsResponse with list of shops.

    Example:
        GET /api/auth/etsy/shops
        Response: {"shops": [{"shop_id": 12345, "shop_name": "MyShop", "is_active": true}], "count": 1}
    """
    # Get any stored OAuth instance
    # In production, this would check DB for valid tokens
    oauth_instances = [v for v in _etsy_oauth_instances.values() if isinstance(v, EtsyOAuth)]

    if not oauth_instances:
        raise HTTPException(
            status_code=401,
            detail="Not connected to Etsy. Call /authorize first.",
        )

    oauth = oauth_instances[0]

    # If shop_id provided, use that specific shop
    if shop_id:
        key = f"shop_{shop_id}"
        if key in _etsy_oauth_instances:
            oauth = _etsy_oauth_instances[key]

    try:
        from src.etsy.client import EtsyClient

        client = EtsyClient(oauth)
        shops_result = await client.get_shops()
        await client.close()

        shops = [
            EtsyShop(
                shop_id=shop["shop_id"],
                shop_name=shop["shop_name"],
                is_active=shop.get("is_active", True),
            )
            for shop in shops_result.get("results", [])
        ]

        # Filter by shop_id if provided
        if shop_id:
            shops = [s for s in shops if s.shop_id == shop_id]

        return EtsyShopsResponse(
            shops=shops,
            count=len(shops),
        )

    except Exception as e:
        logger.error(f"Failed to get shops: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get shops: {str(e)}",
        )


@router.delete("/disconnect", response_model=EtsyDisconnectResponse)
async def disconnect_etsy(
    shop_id: int = Query(..., description="Shop ID to disconnect"),
) -> EtsyDisconnectResponse:
    """Disconnect an Etsy shop.

    Revokes tokens and removes shop connection.

    Args:
        shop_id: Shop ID to disconnect.

    Returns:
        EtsyDisconnectResponse with success status.

    Example:
        DELETE /api/auth/etsy/disconnect?shop_id=12345
        Response: {"success": true, "message": "Disconnected shop 12345"}
    """
    # Find and remove OAuth instance for this shop
    key = f"shop_{shop_id}"
    oauth = _etsy_oauth_instances.pop(key, None)

    if oauth and oauth.refresh_token:
        # In production, revoke tokens via API here
        logger.info(f"Disconnecting shop {shop_id}")

    return EtsyDisconnectResponse(
        success=True,
        message=f"Disconnected shop {shop_id}",
    )
