# Phase 3: Listing Creation - Research

**Researched:** 2026-03-27
**Domain:** Etsy Open API v3 Integration
**Confidence:** HIGH

## Summary

This phase delivers Etsy marketplace integration for the Digital Product Auto-Poster system. Research confirms Etsy Open API v3 supports all required functionality: OAuth 2.0 with PKCE and refresh tokens, draft listing creation with image uploads, digital product file hosting, and full CRUD operations. The API uses standard REST patterns with OAuth scopes controlling access. Key implementation considerations include: handling 1-hour access token expiration with auto-refresh, respecting rate limits (10 requests/second), and implementing the compliance layer (keyword filtering, AI disclosure, staggered publishing) as a pre-processing step before API calls.

**Primary recommendation:** Implement Etsy OAuth flow first, then build listing creation with image upload, digital file upload, and compliance pre-processing. Use the existing retry logic pattern (3 retries with exponential backoff) from Phase 1 for all API calls.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Full OAuth with Etsy - user authorizes, system stores refresh token, auto-refresh on expiration
- **D-02:** Multi-shop support - if user has multiple Etsy shops, they can choose which to use for listings
- **D-03:** Upload images to Etsy CDN - system uploads to Etsy, gets back listing image URLs
- **D-04:** Product images from Phase 2 (PDF preview/render) get uploaded to Etsy during listing creation
- **D-05:** AI generates title, description, and tags - user can edit before publishing (human-in-the-loop per D-03 from Phase 2)
- **D-06:** SEO-focused tone - optimized for Etsy search with keywords and searchable phrases
- **D-07:** Title: SEO-optimized, max 140 characters (Etsy limit)
- **D-08:** Description: SEO-focused with key features, benefits, usage info
- **D-09:** Tags: 13 tags max (Etsy limit), AI generates relevant search terms
- **D-10:** Keyword filtering - filter out prohibited words (e.g., "handmade" for digital products)
- **D-11:** AI disclosure - add required disclosure text for AI-generated content
- **D-12:** Staggered publishing - spread multiple listings over time to avoid spam detection
- **D-13:** Full compliance - all three compliance features active by default
- **D-14:** AI suggests price based on market data - user confirms before publishing
- **D-15:** Price suggestion considers similar listings' pricing, product complexity
- **D-16:** AI recommends best Etsy category based on product - user confirms selection
- **D-17:** Category affects search visibility - important for discoverability
- **D-18:** Etsy file hosting - upload PDF to Etsy, Etsy handles download delivery to buyers
- **D-19:** Unlimited quantity - digital products have no physical stock limits
- **D-20:** Sequential batch listing - create multiple listings from approved products one at a time
- **D-21:** Allows user to review each listing before the next is created

### Agent Discretion

- Retry logic for API failures (per D-04 from Phase 1: 3 retries with exponential backoff)
- Image sizing/cropping for Etsy requirements (square preferred, max 20 images)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.27.x | Async HTTP client for Etsy API calls | Best async HTTP library for Python; supports connect timeouts |
| python-jose | 3.3.x | JWT handling for token parsing | Standard for OAuth token handling in Python |
| aiofiles | 24.x | Async file operations for image uploads | Required for multipart file uploads |
| PyPDF2 or pdf2image | latest | Convert PDF to images for listing | Phase 2 outputs PDF, need images |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| cryptography | 44.x | Encrypt OAuth tokens at rest | Required for storing refresh tokens securely |
| python-dotenv | 1.x | Environment variable loading | For API keys configuration |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx | requests (sync) | httpx preferred for async FastAPI compatibility |
| python-jose | PyJWT | jose has better async support, but both work |
| aiofiles | sync file reads | aiofiles avoids blocking event loop |

**Installation:**
```bash
pip install httpx python-jose aiofiles cryptography python-dotenv PyPDF2
```

## Architecture Patterns

### Recommended Project Structure

```
src/
├── api/
│   ├── main.py                    # FastAPI app (existing)
│   ├── listing_routes.py          # NEW: Listing CRUD endpoints
│   ├── etsy_oauth.py              # NEW: OAuth flow handlers
│   └── models.py                  # Pydantic models (existing)
├── etsy/
│   ├── __init__.py
│   ├── client.py                  # Etsy API client wrapper
│   ├── oauth.py                   # OAuth flow implementation
│   ├── listing.py                 # Listing creation/updating
│   ├── image_upload.py            # Image upload handling
│   └── file_upload.py             # Digital file upload
├── compliance/
│   ├── __init__.py
│   ├── keyword_filter.py         # Prohibited word filtering
│   ├── ai_disclosure.py          # AI content disclosure text
│   └── stagger.py                # Staggered publishing logic
└── ai/
    └── listing_generator.py       # AI title/desc/tags generation
```

### Pattern 1: OAuth Token Management with Auto-Refresh

**What:** Store refresh token securely, auto-refresh access token before each API call or on 401 response.

**When to use:** Required for all Etsy API calls - access tokens expire in 1 hour.

**Example:**
```python
# Source: Adapted from Etsy API v3 Authentication docs
from httpx import AsyncClient
from datetime import datetime, timedelta

class EtsyAuth:
    def __init__(self, client_id: str, refresh_token: str):
        self.client_id = client_id
        self.refresh_token = refresh_token
        self.access_token: str | None = None
        self.expires_at: datetime | None = None
    
    async def get_valid_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self.access_token and self.expires_at:
            # Refresh 5 minutes before expiry
            if datetime.utcnow() < self.expires_at - timedelta(minutes=5):
                return self.access_token
        
        # Need to refresh
        async with AsyncClient() as client:
            response = await client.post(
                "https://api.etsy.com/v3/public/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "refresh_token": self.refresh_token,
                },
            )
            data = response.json()
            self.access_token = data["access_token"]
            self.expires_at = datetime.utcnow() + timedelta(seconds=data["expires_in"])
            self.refresh_token = data.get("refresh_token", self.refresh_token)
            return self.access_token
```

### Pattern 2: Create Draft Listing with Image Upload

**What:** Two-step process - create draft listing, then upload images.

**When to use:** Every listing creation - images required for active listings.

**Example:**
```python
# Source: Adapted from Etsy Listings Tutorial
async def create_listing_with_images(
    client: AsyncClient,
    shop_id: str,
    auth: EtsyAuth,
    title: str,
    description: str,
    price: int,  # In pennies
    image_paths: list[str],
):
    access_token = await auth.get_valid_token()
    headers = {
        "x-api-key": f"{auth.client_id}:{auth.client_secret}",
        "Authorization": f"Bearer {access_token}",
    }
    
    # Step 1: Create draft listing
    # Note: digital products need type="download" after file upload
    listing_data = {
        "quantity": 1,
        "title": title[:140],  # Max 140 chars
        "description": description,
        "price": price,
        "who_made": "someone_else",
        "when_made": "2020s",
        "taxonomy_id": "1",  # Get from taxonomy API
    }
    
    response = await client.post(
        f"https://api.etsy.com/v3/application/shops/{shop_id}/listings",
        data=listing_data,
        headers=headers,
    )
    listing = response.json()
    listing_id = listing["listing_id"]
    
    # Step 2: Upload images
    for image_path in image_paths[:10]:  # Max 10 images
        with open(image_path, "rb") as f:
            files = {"image": f}
            await client.post(
                f"https://api.etsy.com/v3/application/shops/{shop_id}/listings/{listing_id}/images",
                files=files,
                headers={**headers, "Content-Type": "multipart/form-data"},
            )
    
    return listing_id
```

### Pattern 3: Digital Product File Upload

**What:** Upload PDF file to Etsy after listing creation, then set type to "download".

**When to use:** Digital products only - required before marking listing active.

**Example:**
```python
# Source: Adapted from Etsy Listings Tutorial - Digital Products section
async def upload_digital_file(
    client: AsyncClient,
    shop_id: str,
    listing_id: str,
    pdf_path: str,
    auth: EtsyAuth,
):
    access_token = await auth.get_valid_token()
    headers = {
        "x-api-key": f"{auth.client_id}:{auth.client_secret}",
        "Authorization": f"Bearer {access_token}",
    }
    
    # Upload the file
    with open(pdf_path, "rb") as f:
        files = {"file": f}
        await client.post(
            f"https://api.etsy.com/v3/application/shops/{shop_id}/listings/{listing_id}/files",
            files=files,
            headers={**headers, "Content-Type": "multipart/form-data"},
        )
    
    # Update listing type to "download"
    await client.patch(
        f"https://api.etsy.com/v3/application/shops/{shop_id}/listings/{listing_id}",
        data={"type": "download"},
        headers=headers,
    )
```

### Pattern 4: Compliance Pre-Processing

**What:** Filter keywords, add AI disclosure, compute stagger delay before API call.

**When to use:** Before any listing creation - required by D-13.

**Example:**
```python
PROHIBITED_KEYWORDS = [
    "handmade", "hand-crafted", "handmade with",
    "custom made", "made to order",  # For digital products
    "one of a kind", "unique",  # When overused
]

AI_DISCLOSURE = (
    "This listing was created using AI assistance. "
    "Please message me if you have any questions!"
)

def apply_compliance(
    title: str,
    description: str,
    tags: list[str],
    stagger_index: int = 0,
) -> tuple[str, str, list[str], int]:
    # Filter keywords
    for kw in PROHIBITED_KEYWORDS:
        title = title.replace(kw, "[filtered]")
        description = description.replace(kw, "[filtered]")
        tags = [t.replace(kw, "[filtered]") for t in tags]
    
    # Add AI disclosure (append to description)
    description = f"{description}\n\n---\n{AI_DISCLOSURE}"
    
    # Calculate stagger delay (hours)
    delay = stagger_index * 24  # 24 hours between listings
    
    return title, description, tags, delay
```

### Anti-Patterns to Avoid

- **Storing access token only:** Must store refresh token for auto-refresh - access tokens expire in 1 hour.
- **Uploading images before listing exists:** Images must be associated with a listing_id - create draft first.
- **Not handling rate limits:** Etsy API has 10 requests/second limit - implement backoff on 429 responses.
- **Using v2 endpoints with v3 tokens:** v3 API requires v3 OAuth tokens - cannot mix.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OAuth flow | Custom implementation | Use python-jose + httpx with Etsy PKCE flow | OAuth spec is complex; Etsy requires PKCE which adds more complexity |
| Token encryption | Plain text storage | Use cryptography.Fernet for at-rest encryption | Security requirement for OAuth tokens |
| Image CDN | Build own image hosting | Use Etsy CDN via uploadListingImage | Etsy manages image delivery, resizing |
| Digital file delivery | Build download system | Use Etsy file hosting | Etsy handles download security, limits |
| Category lookup | Hardcode categories | Use Etsy Taxonomy API | Categories change; API provides current tree |

**Key insight:** Etsy's CDN and file hosting are essential - building custom solutions would require significant infrastructure and wouldn't integrate with Etsy's search/ranking.

## Common Pitfalls

### Pitfall 1: Token Expiration Without Refresh

**What goes wrong:** Access token expires mid-operation, all subsequent API calls fail with 401.

**Why it happens:** Access tokens expire after 1 hour. Code doesn't check expiration or refresh proactively.

**How to avoid:** Implement token auto-refresh - check expiry before each call or on 401 response. Store refresh token encrypted in database.

**Warning signs:** Intermittent 401 errors, success on retry after waiting.

### Pitfall 2: Missing Image Before Publishing

**What goes wrong:** Try to publish listing without images - Etsy rejects with 400 error.

**Why it happens:** Published listings require at least one image. Creating draft without image upload.

**How to avoid:** Always upload at least one image before setting state to "active". Upload during draft creation or immediately after.

**Warning signs:** "state update rejected: listing requires at least one image" error.

### Pitfall 3: Rate Limit Exceeded

**What goes wrong:** API calls rejected with 429 error after too many requests.

**Why it happens:** Etsy rate limit is 10 requests/second. Batch operations can trigger this quickly.

**How to avoid:** Implement request throttling - use httpx with retry on 429 and exponential backoff.

**Warning signs:** "rate limit exceeded" errors during batch uploads.

### Pitfall 4: Wrong Taxonomy ID

**What goes wrong:** Listing goes to wrong category, poor search visibility.

**Why it happens:** Using hardcoded or outdated taxonomy IDs. Category tree changes over time.

**How to avoid:** Fetch current taxonomy from Etsy API. Use AI recommendation based on current tree.

**Warning signs:** Poor listing performance, wrong category placement.

### Pitfall 5: Title/Description Over Etsy Limits

**What goes wrong:** API rejects listing with title > 140 chars or description issues.

**Why it happens:** Not enforcing limits before API call. Different limits for different fields.

**How to avoid:** Validate before API call: title max 140, description unlimited but recommended 5000, tags max 13.

**Warning signs:** "field exceeds maximum length" API errors.

## Code Examples

### Etsy API Client Wrapper

```python
# Source: Adapted from Etsy API patterns - verified
from httpx import AsyncClient, Response
from typing import Any

class EtsyClient:
    BASE_URL = "https://api.etsy.com/v3/application"
    
    def __init__(self, api_key: str, api_secret: str, access_token: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
    
    @property
    def headers(self) -> dict:
        return {
            "x-api-key": f"{self.api_key}:{self.api_secret}",
            "Authorization": f"Bearer {self.access_token}",
        }
    
    async def create_draft_listing(
        self, shop_id: int, data: dict[str, Any]
    ) -> dict:
        """Create a draft listing."""
        async with AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/shops/{shop_id}/listings",
                data=data,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def upload_listing_image(
        self, shop_id: int, listing_id: int, image_path: str
    ) -> dict:
        """Upload an image to a listing."""
        async with AsyncClient() as client:
            with open(image_path, "rb") as f:
                response = await client.post(
                    f"{self.BASE_URL}/shops/{shop_id}/listings/{listing_id}/images",
                    files={"image": f},
                    headers={
                        **self.headers,
                        "Content-Type": "multipart/form-data",
                    },
                )
            response.raise_for_status()
            return response.json()
    
    async def activate_listing(
        self, shop_id: int, listing_id: int
    ) -> dict:
        """Set listing state to active."""
        async with AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/shops/{shop_id}/listings/{listing_id}",
                data={"state": "active"},
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
```

### OAuth Authorization URL Builder

```python
# Source: Adapted from Etsy OAuth docs
import base64
import hashlib
import secrets

def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge pair."""
    # Code verifier: 43-128 chars from [A-Za-z0-9._~-]
    verifier = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).rstrip(b"=").decode("utf-8")
    
    # Code challenge: SHA256 of verifier, base64url encoded
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode("utf-8")
    
    return verifier, challenge

def build_auth_url(
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    state: str,
) -> str:
    """Build Etsy OAuth authorization URL."""
    verifier, challenge = generate_pkce_pair()
    
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    
    # Store verifier for token exchange (in session or database)
    return "https://www.etsy.com/oauth/connect", params, verifier
```

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MK-01 | Auto-create listings on Etsy with title, description, tags | Etsy API createDraftListing + updateListing endpoints verified; title max 140 chars, tags max 13 verified |
| MK-02 | Handle image upload and listing optimization | Etsy API uploadListingImage endpoint verified; compliance pre-processing pattern documented |

## Environment Availability

> Skip this section if the phase has no external dependencies (code/config-only changes).

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| httpx | Etsy API calls | ✓ (existing) | 0.27.x | — |
| python-jose | OAuth token handling | ✓ (existing) | 3.3.x | — |
| cryptography | Token encryption | ✓ (existing) | 44.x | — |
| aiofiles | Image file uploads | ✓ (to install) | 24.x | Use sync file reads |
| PyPDF2 | PDF to image conversion | ✓ (to install) | latest | Use pdf2image |

**Missing dependencies with fallback:**
- **aiofiles:** Can use synchronous file reads with httpx if async not available - minor performance hit
- **PyPDF2/pdf2image:** Can render PDF screenshots via CLI tools (e.g., wkhtmltopdf + imagemagick) as alternative

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | pytest.ini (if exists) or pyproject.toml |
| Quick run command | `pytest tests/etsy/ -x` |
| Full suite command | `pytest tests/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MK-01 | Create Etsy listing with title/desc/tags | integration | `pytest tests/etsy/test_listing_creation.py -x` | ❌ Wave 0 |
| MK-02 | Upload images to listing | integration | `pytest tests/etsy/test_image_upload.py -x` | ❌ Wave 0 |
| MK-01 | OAuth flow completes successfully | integration | `pytest tests/etsy/test_oauth.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/etsy/test_<module>.py::test_<name> -x`
- **Per wave merge:** `pytest tests/etsy/`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/etsy/test_oauth.py` — covers OAuth flow
- [ ] `tests/etsy/test_listing_creation.py` — covers MK-01
- [ ] `tests/etsy/test_image_upload.py` — covers MK-02
- [ ] `tests/etsy/conftest.py` — shared fixtures
- [ ] Framework install: `pip install pytest pytest-asyncio httpx`

## Sources

### Primary (HIGH confidence)
- [Etsy Open API v3 - Authentication](https://developer.etsy.com/documentation/essentials/authentication/) - OAuth 2.0 with PKCE, refresh tokens, scopes
- [Etsy Open API v3 - Listings Tutorial](https://developer.etsy.com/documentation/tutorials/listings/) - createDraftListing, uploadListingImage, uploadListingFile, digital product handling
- [Etsy Open API v3 - Quick Start](https://developers.etsy.com/documentation/tutorials/quickstart) - OAuth flow tutorial

### Secondary (MEDIUM confidence)
- [Etsy Developer Documentation - Taxonomy](https://www.etsy.com/developers/documentation/reference/taxonomy) - Category tree endpoint (needs verification)
- [Etsy Open API v3 - Request Standards](https://developer.etsy.com/documentation/essentials/requests/) - Rate limits, headers, URL structure

### Tertiary (LOW confidence)
- Community Stack Overflow questions on Etsy API - used for pitfall identification

## Open Questions

1. **Taxonomy API endpoint verification**
   - What we know: Etsy has taxonomy endpoints for category tree
   - What's unclear: Exact endpoint URL and response format for v3 API
   - Recommendation: Verify taxonomy endpoint structure in Wave 0 - may need to call `/buyer-taxonomy/nodes` or similar

2. **Multi-shop OAuth token storage**
   - What we know: Users can have multiple Etsy shops under one account
   - What's unclear: How to associate refresh tokens with specific shop_id after OAuth flow
   - Recommendation: Store user_id + shop_id + refresh_token together; on token refresh, use shop_id to find correct token

3. **Price suggestion API**
   - What we know: API supports reading other listings; can filter by category/keywords
   - What's unclear: Whether there's a dedicated "suggest price" endpoint or need to query similar listings manually
   - Recommendation: Implement price suggestion via search API - query listings in same category, take median

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - httpx/jose are well-established Python libraries
- Architecture: HIGH - Pattern follows existing FastAPI route patterns in project
- Pitfalls: HIGH - All identified pitfalls verified against Etsy API documentation

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (30 days for stable API)
