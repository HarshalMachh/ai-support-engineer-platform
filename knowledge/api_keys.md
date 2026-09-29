# API Keys, Authentication and Rate Limits

The Acme Cloud REST API is available at `https://api.acme-cloud.dev/v2`.

## Creating API keys

API keys are created in the dashboard under **Settings → Developers → API keys**.
Only account owners and admins can create keys. A key is shown **only once** at creation time;
if it is lost, create a new key and revoke the old one.

Keys are scoped to one environment. Production keys start with `ak_live_` and sandbox keys start
with `ak_test_`. A sandbox key used against production resources returns `401 Unauthorized`.

## Sending the key

Send the key in the `Authorization` header:

```
Authorization: Bearer ak_live_xxxxxxxxxxxx
```

Keys sent as query parameters are rejected with `400 Bad Request` for security reasons.

## Common API errors

- **401 Unauthorized**: the key is missing, revoked, expired, or belongs to a different environment.
  Check the key prefix and confirm the key is still listed as active in the dashboard.
- **403 Forbidden**: the key is valid but lacks the required scope. Keys have scopes such as
  `tickets:read`, `billing:read` and `projects:write`. Edit the key to add scopes.
- **429 Too Many Requests**: the rate limit was exceeded. See below.
- **5xx errors**: retry with exponential backoff. If errors persist for more than 5 minutes,
  check the status page and contact support with the `X-Request-Id` response header.

## Rate limits

Default limits are **100 requests per minute** per key on the Starter plan and **1,000 requests per
minute** on the Business plan. Every response includes these headers:

- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-RateLimit-Reset` (Unix timestamp when the window resets)

Clients receiving 429 should wait until `X-RateLimit-Reset` before retrying.

## Key rotation

Rotate keys at least every 90 days. Recommended process:

1. Create a new key with the same scopes.
2. Deploy the new key to your application.
3. Confirm traffic uses the new key (the dashboard shows "last used" time).
4. Revoke the old key.

Revoking a key takes effect within 60 seconds globally.

## Webhooks

Webhook deliveries are signed with the `X-Acme-Signature` header using HMAC-SHA256 and the
webhook signing secret. Failed deliveries are retried 5 times over 24 hours.
