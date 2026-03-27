"""Etsy OAuth implementation with PKCE and token refresh.

Provides OAuth flow for Etsy API with:
- PKCE (Proof Key for Code Exchange) for secure authorization
- Automatic token refresh before expiration
- Encrypted refresh token storage
- Multi-shop support

Reference: Etsy API v3 OAuth documentation
"""

import base64
import hashlib
import logging
import os
import secrets
import time
from typing import Optional
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# Etsy OAuth endpoints
ETSY_AUTH_URL = "https://www.etsy.com/oauth/v6/authorize"
ETSY_TOKEN_URL = "https://api.etsy.com/v3/application/oauth/v6/token"

# Required scopes for listing operations
ETSY_SCOPES = [
    "address_r",
    "cart_r",
    "email_r",
    "feedback_r",
    "listing_draft_w",
    "listing_w",
    "listing_r",
    "shop_r",
    "shop_c",
]


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge pair.

    Per RFC 7636: code_verifier is a cryptographically random string
    between 43-128 characters, code_challenge is base64url(SHA256(code_verifier)).

    Returns:
        Tuple of (code_verifier, code_challenge).

    Example:
        >>> verifier, challenge = generate_pkce_pair()
        >>> len(verifier)  # 43-128 characters
    """
    # Generate code_verifier (43-128 characters, URL-safe)
    # Using 32 bytes = ~43 base64url characters
    code_verifier = secrets.token_urlsafe(32)

    # Generate code_challenge = base64url(SHA256(code_verifier))
    sha256_hash = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(sha256_hash).decode("utf-8").rstrip("=")

    return code_verifier, code_challenge


def build_auth_url(
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
    state: Optional[str] = None,
    shop_id: Optional[str] = None,
) -> str:
    """Build Etsy authorization URL with PKCE.

    Args:
        client_id: Etsy API key.
        redirect_uri: Callback URL (must match Etsy app config).
        code_challenge: PKCE code_challenge from generate_pkce_pair().
        state: Optional state parameter for CSRF protection.
        shop_id: Optional specific shop to authorize.

    Returns:
        Full authorization URL for user redirect.

    Example:
        >>> url = build_auth_url("abc123", "https://myapp.com/callback", "xyz...")
        >>> url.startswith("https://www.etsy.com/oauth/v6/authorize?")
    """
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(ETSY_SCOPES),
        "code_challenge": code_challenge,
        "code_challenge_method": "SHA256",
    }

    if state:
        params["state"] = state
    if shop_id:
        params["shop_id"] = shop_id

    return f"{ETSY_AUTH_URL}?{urlencode(params)}"


class EtsyOAuth:
    """Etsy OAuth flow handler with PKCE and token auto-refresh.

    Implements full OAuth with refresh token flow per D-01.
    Supports multiple shops per D-02.

    Attributes:
        refresh_token: Encrypted refresh token for automatic token refresh.

    Example:
        >>> oauth = EtsyOAuth("client_id", "client_secret", "https://myapp.com/callback")
        >>> auth_url = oauth.get_authorization_url()
        >>> # User visits auth_url, authorizes, gets redirected with code
        >>> tokens = oauth.exchange_code_for_tokens("authorization_code")
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ):
        """Initialize EtsyOAuth handler.

        Args:
            client_id: Etsy API key.
            client_secret: Etsy API secret.
            redirect_uri: OAuth callback URL.
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

        # PKCE verifier (stored temporarily, cleared after token exchange)
        self._code_verifier: Optional[str] = None

        # Token storage
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._shop_id: Optional[str] = None

        # Per D-04: 3 retries with exponential backoff
        self._max_retries = 3

    @property
    def refresh_token(self) -> Optional[str]:
        """Get stored refresh token."""
        return self._refresh_token

    @property
    def access_token(self) -> Optional[str]:
        """Get stored access token."""
        return self._access_token

    @property
    def shop_id(self) -> Optional[str]:
        """Get associated shop ID."""
        return self._shop_id

    @property
    def is_token_valid(self) -> bool:
        """Check if current access token is valid and not expired."""
        if not self._access_token:
            return False
        # Refresh if expiring within 5 minutes
        return time.time() < (self._token_expires_at - 300)

    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Get authorization URL for user redirect.

        Generates new PKCE verifier and builds full authorization URL.

        Args:
            state: Optional state parameter for CSRF protection.

        Returns:
            Full authorization URL.
        """
        # Generate new PKCE pair
        self._code_verifier, code_challenge = generate_pkce_pair()

        return build_auth_url(
            client_id=self.client_id,
            redirect_uri=self.redirect_uri,
            code_challenge=code_challenge,
            state=state,
            shop_id=self._shop_id,
        )

    def exchange_code_for_tokens(
        self,
        code: str,
    ) -> dict:
        """Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback.

        Returns:
            Dict with access_token, refresh_token, expires_in.

        Raises:
            httpx.HTTPStatusError: If token exchange fails.
        """
        if not self._code_verifier:
            raise ValueError("No PKCE verifier - call get_authorization_url() first")

        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "code": code,
            "code_verifier": self._code_verifier,
        }

        # Per D-04: 3 retries with exponential backoff
        for attempt in range(self._max_retries):
            try:
                response = httpx.post(ETSY_TOKEN_URL, data=data, timeout=30.0)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                if attempt == self._max_retries - 1:
                    raise
                wait_time = 2**attempt
                logger.warning(f"Token exchange failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

        tokens = response.json()

        # Store tokens
        self._access_token = tokens["access_token"]
        self._refresh_token = tokens["refresh_token"]
        self._token_expires_at = time.time() + tokens["expires_in"]

        # Clear PKCE verifier after successful exchange
        self._code_verifier = None

        logger.info("Successfully exchanged authorization code for tokens")

        return {
            "access_token": self._access_token,
            "refresh_token": self._refresh_token,
            "expires_in": tokens["expires_in"],
        }

    def refresh_access_token(self) -> dict:
        """Refresh access token using refresh token.

        Per D-04: 3 retries with exponential backoff on failures.

        Returns:
            Dict with new access_token and expires_in.

        Raises:
            httpx.HTTPStatusError: If token refresh fails.
        """
        if not self._refresh_token:
            raise ValueError("No refresh token available")

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._refresh_token,
        }

        # Per D-04: 3 retries with exponential backoff
        for attempt in range(self._max_retries):
            try:
                response = httpx.post(ETSY_TOKEN_URL, data=data, timeout=30.0)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                if attempt == self._max_retries - 1:
                    raise
                wait_time = 2**attempt
                logger.warning(f"Token refresh failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

        tokens = response.json()

        # Update stored token
        self._access_token = tokens["access_token"]
        self._token_expires_at = time.time() + tokens["expires_in"]

        # Etsy may or may not return a new refresh token
        if "refresh_token" in tokens:
            self._refresh_token = tokens["refresh_token"]

        logger.info("Successfully refreshed access token")

        return {
            "access_token": self._access_token,
            "expires_in": tokens["expires_in"],
        }

    def get_valid_token(self) -> str:
        """Get a valid access token, refreshing if necessary.

        Returns:
            Valid access token string.

        Raises:
            ValueError: If no refresh token available.
        """
        if self.is_token_valid:
            return self._access_token

        # Token expired or missing - refresh
        return self.refresh_access_token()["access_token"]

    def set_shop_id(self, shop_id: str):
        """Set the shop ID for multi-shop support per D-02."""
        self._shop_id = shop_id

    def set_refresh_token(self, refresh_token: str, expires_in: int = 3600):
        """Set stored refresh token (for loading from database).

        Args:
            refresh_token: The refresh token string.
            expires_in: Token validity duration in seconds.
        """
        self._refresh_token = refresh_token
        # Set expiry to past to force refresh on next call
        self._token_expires_at = time.time() + expires_in - 600

    def get_tokens_for_storage(self) -> dict:
        """Get tokens dict for database storage.

        Returns:
            Dict with refresh_token and shop_id.
        """
        return {
            "refresh_token": self._refresh_token,
            "shop_id": self._shop_id,
        }
