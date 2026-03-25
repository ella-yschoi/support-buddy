---
title: CloudSync API Best Practices
category: feature
---

## API Authentication

All CloudSync API requests require authentication via API key or OAuth 2.0 token.

**API Key authentication:**
- Generate keys: Dashboard > Settings > API > "Create API Key"
- Include in requests: `Authorization: Bearer cs_live_xxxxxxxxxxxx`
- Key prefixes: `cs_live_` (production), `cs_test_` (sandbox)
- Keys can be scoped: read-only, read-write, or admin
- Rotate keys every 90 days (Enterprise policy can enforce this)

**OAuth 2.0 (for third-party integrations):**
- Authorization endpoint: `https://app.cloudsync.io/oauth/authorize`
- Token endpoint: `https://app.cloudsync.io/oauth/token`
- Supported grants: authorization_code, client_credentials
- Token expiry: 1 hour (refresh tokens valid for 30 days)

**Common mistakes:**
- Using test keys in production (will return sandbox data)
- Not rotating expired keys (returns AUTH-001 after expiry)
- Sharing API keys in code repositories (revoke immediately if exposed)

## API Pagination

All list endpoints support cursor-based pagination for efficient traversal of large datasets.

**Parameters:**
- `limit`: Number of items per page (default: 50, max: 200)
- `cursor`: Opaque cursor string from previous response
- `sort`: Field to sort by (default varies by endpoint)
- `order`: `asc` or `desc`

**Response format:**
```json
{
  "data": [...],
  "pagination": {
    "has_more": true,
    "next_cursor": "eyJpZCI6MTIzNH0=",
    "total_count": 5432
  }
}
```

**Best practices:**
- Always check `has_more` before making the next request
- Store `next_cursor` and resume from it if interrupted
- Use the maximum `limit` (200) to reduce total API calls
- Do NOT use offset-based pagination (not supported) — always use cursors

## API Error Handling

The CloudSync API uses standard HTTP status codes with structured error responses.

**Error response format:**
```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "API rate limit of 1000 requests/minute exceeded",
    "error_code": "API-001",
    "retry_after": 32
  }
}
```

**Status codes:**
| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad request — invalid parameters | Fix request body/params |
| 401 | Unauthorized — invalid or expired key | Check/rotate API key |
| 403 | Forbidden — insufficient permissions | Check key scope |
| 404 | Not found — resource does not exist | Verify resource ID |
| 409 | Conflict — resource already exists | Handle idempotency |
| 429 | Rate limited | Wait for `retry_after` seconds |
| 500 | Internal server error | Retry with backoff |
| 503 | Service unavailable | Check status page, retry |

**Retry strategy:**
- Implement exponential backoff: 1s, 2s, 4s, 8s, max 60s
- Add jitter (random 0-1s) to avoid thundering herd
- Respect `retry_after` header when present
- Maximum 5 retries before failing

## Batch Operations

Reduce API calls by using batch endpoints for bulk operations.

**Available batch endpoints:**
- `POST /api/v1/files/batch-move` — Move up to 100 files in one request
- `POST /api/v1/files/batch-delete` — Delete up to 100 files
- `POST /api/v1/shares/batch-create` — Share multiple files/folders at once
- `POST /api/v1/users/batch-invite` — Invite up to 50 users

**Batch request format:**
```json
{
  "operations": [
    {"id": "file-001", "destination": "/archive/2024/"},
    {"id": "file-002", "destination": "/archive/2024/"}
  ]
}
```

**Batch response:** Each operation returns individual success/failure status, so partial failures are possible. Always check per-operation results.

**Limits:**
- Maximum 100 operations per batch (50 for user invites)
- Batch requests count as 1 API call for rate limiting purposes
- Timeout: 30 seconds per batch (may need multiple batches for large operations)

## Webhook Signature Verification

Verify that webhook payloads are genuinely from CloudSync by checking the signature.

**How it works:**
1. When creating a webhook, set a signing secret (or let CloudSync generate one)
2. Each delivery includes a `X-CloudSync-Signature` header
3. The signature is a HMAC-SHA256 of the raw request body using your signing secret

**Verification pseudocode:**
```python
import hmac, hashlib

def verify_webhook(payload_body, signature_header, secret):
    expected = hmac.new(
        secret.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)
```

**Important:**
- Always use constant-time comparison (`hmac.compare_digest`) to prevent timing attacks
- Verify BEFORE processing the payload
- Reject requests with missing or invalid signatures
- Webhook signatures expire after 5 minutes — check the `X-CloudSync-Timestamp` header

## API Rate Limit Management

Proactively manage rate limits to avoid disruptions.

**Rate limit headers (included in every response):**
- `X-RateLimit-Limit`: Your plan's limit per minute
- `X-RateLimit-Remaining`: Requests remaining in current window
- `X-RateLimit-Reset`: Unix timestamp when the window resets

**Strategies for high-volume integrations:**
1. Monitor `X-RateLimit-Remaining` and slow down when below 20%
2. Use webhooks instead of polling — eliminates periodic GET calls
3. Use batch endpoints to consolidate operations
4. Cache responses client-side (files metadata changes infrequently)
5. Distribute requests evenly over time instead of bursting
6. For Enterprise: request a custom rate limit increase via support

**Rate limits by plan:**
| Plan | Requests/min | Burst (10s window) |
|------|-------------|-------------------|
| Free | 100 | 20 |
| Pro | 1,000 | 200 |
| Enterprise | 10,000 (default) | 2,000 |
