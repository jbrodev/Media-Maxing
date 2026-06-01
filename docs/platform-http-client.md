# Platform HTTP Client

The platform HTTP client is the server-only boundary for future calls to Meta, Google/YouTube, TikTok, LinkedIn, and X APIs.

It does not publish posts, fetch real user data, or call real APIs by default.

## Location

```text
scripts/services/platform_http_client.py
```

Connectors should use this utility for future provider requests instead of calling `urllib`, `requests`, `fetch`, or another HTTP layer directly.

## Network Safety Modes

- `disabled`: external network calls are blocked.
- `mock`: returns configured mock responses or a dry-run mock response.
- `enabled`: allows a connector-approved server-side network call.

Mock mode is the local development path for connector tests and setup screens. It should not contact provider APIs.

Default behavior:

- Test environment: `disabled` unless `ALLOW_NETWORK_IN_TESTS=true`.
- Development: `mock` unless connector code explicitly enables real network calls.
- Production: network calls require explicit flags and connector approval.

## Supported Requests

The client supports:

- `GET`
- `POST`
- `PUT`
- `PATCH`
- `DELETE`
- query parameters
- request headers
- JSON bodies
- form-encoded bodies for OAuth token exchange scaffolding
- default timeout
- safe JSON parsing

## Redaction

The client redacts sensitive values before returning errors, summaries, or normalized provider errors.

Sensitive fields include:

- `access_token`
- `refresh_token`
- `client_secret`
- `authorization`
- bearer tokens
- `code`
- `id_token`
- `appsecret_proof`
- `signed_request`
- long provider token-like values in known secret fields
- `set-cookie` headers

Redaction is a safety backstop. Connector code should still avoid logging raw provider responses.

## Provider Error Shape

Provider errors normalize into:

- `provider`
- `platform`
- `status`
- `code`
- `message`
- `userSafeMessage`
- `retryable`
- `requiresReauth`
- `rateLimited`
- `missingPermission`
- `rawRedacted`

HTTP `401` OAuth/token errors map to `requiresReauth`.

HTTP `429` maps to `rateLimited`.

HTTP `403` or permission/scope errors map to `missingPermission`.

## Connector Usage

Future connector code should:

1. Validate integration flags first.
2. Create a `PlatformHttpClientConfig` with provider and platform.
3. Use `mock` mode for tests and local demos.
4. Use fake transport in tests instead of external calls.
5. Use form-encoded bodies only through `formBody`.
6. Never pass client secrets or tokens to frontend code.
7. Treat publishing methods as disabled until a future real-publishing task changes policy.

## How To Test

Run:

```text
python -m unittest tests.test_platform_http_client
```

The tests verify disabled network behavior, mock responses, form/body redaction, invalid URL handling, and safe provider error normalization.
