# Phase 3: Listing Creation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 3-listing-creation
**Areas discussed:** Etsy OAuth, Image handling, Listing content, Compliance layer, Pricing, Category selection, File delivery, Inventory handling, Batch listing

---

## Etsy OAuth

| Option | Description | Selected |
|--------|-------------|----------|
| Full OAuth | Standard OAuth with Etsy - user authorizes, we store refresh token, auto-refresh | ✓ |
| API key only | User manually enters API key from Etsy developer portal | |
| Mock shop | Skip OAuth for now, just use mock/test shop for development | |

**User's choice:** Full OAuth (Recommended)
**Notes:** User wants proper OAuth with refresh token handling for production use

## Shop Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Multi-shop support | If user has multiple shops, let them choose which to use | ✓ |
| Single shop only | Assume single shop per account, use first available | |

**User's choice:** Multi-shop support (Recommended)

## Image Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Upload to Etsy CDN | Etsy requires images on their servers - upload to Etsy CDN, get back URLs | ✓ |
| External hosting | Host images externally (S3, Cloudinary), Etsy references external URLs | |
| Mock images | Skip image upload for now, use placeholder images | |

**User's choice:** Upload to Etsy CDN (Recommended)

## Listing Content

| Option | Description | Selected |
|--------|-------------|----------|
| AI + human review | AI generates title/description/tags - user can edit before publishing | ✓ |
| Manual only | User provides all content manually, system just submits to Etsy | |
| Templates only | Template-based with placeholders - no AI generation | |

**User's choice:** AI + human review (Recommended)

## Content Tone

| Option | Description | Selected |
|--------|-------------|----------|
| SEO-focused | Optimized for Etsy search - keywords focused, searchable phrases | ✓ |
| Sales copy | Helpful, friendly tone that sells the benefit | |
| Comprehensive | Detailed, comprehensive - longer descriptions | |

**User's choice:** SEO-focused (Recommended)
**Notes:** Etsy search optimization is critical for discoverability

## Compliance Features

| Option | Description | Selected |
|--------|-------------|----------|
| Keyword filtering | Filter out prohibited keywords from listings | |
| AI disclosure | AI-generated content disclosure required by some platforms | |
| Staggered publishing | Post listings gradually to avoid spam detection | |
| Full compliance | All of the above | ✓ |

**User's choice:** Full compliance (Recommended)

## Pricing

| Option | Description | Selected |
|--------|-------------|----------|
| AI suggestion + user confirm | AI suggests price based on market data, user confirms before publishing | ✓ |
| Manual only | User manually enters price, system just submits it | |
| Fixed formula | Fixed pricing rules - e.g., $X base + $Y per page | |

**User's choice:** AI suggestion + user confirm (Recommended)

## Category Selection

| Option | Description | Selected |
|--------|-------------|----------|
| AI suggestion + confirm | AI recommends best category based on product - user confirms | ✓ |
| Manual only | User picks from Etsy category tree manually | |
| Fixed default | Fixed category for all digital products | |

**User's choice:** AI suggestion + confirm (Recommended)

## File Delivery

| Option | Description | Selected |
|--------|-------------|----------|
| Etsy file hosting | Upload PDF to Etsy, Etsy handles download - simplest | ✓ |
| External download link | User provides download link from external service | |
| Custom delivery | Set up external file delivery service | |

**User's choice:** Etsy file hosting (Recommended)

## Inventory Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Unlimited qty | Digital products have unlimited quantity - set and forget | ✓ |
| Limited quantity | Let user specify max sales or limited quantity | |
| Track and auto-disable | Track sales count and auto-disable after threshold | |

**User's choice:** Unlimited qty (Recommended)

## Batch Listing

| Option | Description | Selected |
|--------|-------------|----------|
| Yes - sequential | Create multiple listings from approved products - sequential or parallel | ✓ |
| No - single only | One listing at a time only | |
| Yes - parallel | Create all listings at once - parallel | |

**User's choice:** Yes - sequential (Recommended)
**Notes:** Allows user to review each listing before the next is created

## Agent Discretion

The following areas were left to agent discretion:
- Retry logic for API failures (per D-04 from Phase 1: 3 retries with exponential backoff)
- Image sizing/cropping for Etsy requirements (square preferred, max 20 images)

## Deferred Ideas

No scope creep was identified — discussion stayed within Phase 3 scope.
