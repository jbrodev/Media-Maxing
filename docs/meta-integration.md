# Meta Integration Scaffold

This document describes the current Meta connector scaffold for Facebook, Instagram, and Threads.

The scaffold is not a real publishing integration yet. It does not publish, fetch comments, fetch analytics, or call Meta APIs by default. A guarded short-lived OAuth token exchange path now exists for future manual testing, but it is blocked unless explicit real OAuth and network flags are enabled.

## Connector Modules

Meta connector code lives under `scripts/connectors/meta/`:

- `facebook.py`: Facebook Page connector scaffold.
- `instagram.py`: Instagram Business/Creator connector scaffold.
- `threads.py`: Threads connector scaffold.
- `config.py`: safe Meta environment configuration loader.
- `oauth.py`: mock authorization URL helpers, real authorization URL helpers, and guarded token exchange request building.
- `oauth.py`: also contains the centralized profile discovery request scaffold, marked TODO for API verification.
- `errors.py`: normalized, redacted Meta error shapes.
- `base.py`: shared Meta connector behavior.

The central registry in `scripts/connectors/registry.py` returns these connectors for:

- `facebook`
- `instagram`
- `threads`

## Environment Variables

The config loader reads:

```text
META_CLIENT_ID=
META_CLIENT_SECRET=
META_REDIRECT_URI=
META_GRAPH_API_VERSION=
META_ENABLE_REAL_OAUTH=false
META_ENABLE_REAL_PUBLISHING=false
```

`META_GRAPH_API_VERSION` defaults to a placeholder version when unset. Exact API version and permissions must be verified before real OAuth is enabled.

The loader only exposes whether `META_CLIENT_SECRET` is configured. It should not print, log, or return the secret value.

## OAuth Behavior

Mock mode can build a local mock authorization URL without credentials.

Real OAuth token exchange is setup-gated:

- missing `META_CLIENT_ID`, `META_CLIENT_SECRET`, or `META_REDIRECT_URI` returns `setup_required`
- real OAuth requires `ENABLE_REAL_OAUTH=true` or `INTEGRATIONS_MODE=real_oauth`
- real OAuth also requires `ENABLE_REAL_NETWORK_CALLS=true`
- real OAuth also requires `META_ENABLE_REAL_OAUTH=true`
- OAuth state must be validated by `OAuthFlowService`
- the callback must include an authorization code
- the server-only platform HTTP client must allow the request

If any requirement is missing, no network call is made and the callback returns a safe setup/disabled result.

When all gates pass, `OAuthFlowService` builds a Meta token request through `scripts/connectors/meta/oauth.py` and sends it through `scripts/services/platform_http_client.py`. Tests use mocked HTTP responses only.

## Token And Account Behavior

The token response is passed to `TokenSecurityService`.

With the current default:

```text
TOKEN_STORAGE_MODE=placeholder_not_stored
```

raw token values are refused and are not stored. The app stores placeholder token metadata only, with null token blob fields.

Because account discovery is not implemented yet, a successful token exchange creates a limited local account:

- `connectionStatus=limited`
- `platformAccountId` uses an unknown local placeholder
- `requiresReauth=true`
- safe frontend DTO only
- warning that account discovery is not implemented

Long-lived token exchange is not implemented yet. That future step must verify current Meta docs, token lifetimes, app review requirements, and secure token storage first.

## Account Discovery And Health

Meta connectors now expose:

- `getAccountProfile()`
- `validateConnection()`

The current discovery path is a safe scaffold. Tests inject mocked provider responses through the server-only platform HTTP client. Real discovery is not called by default.

Health checks can return:

- `healthy`
- `limited`
- `expired`
- `missing_permissions`
- `network_disabled`
- `error`

Health checks update `last_validated_at`, store safe connector health rows, and write safe audit logs. Provider auth failures such as HTTP 401 map to `expired` and `requires_reauth`. Missing scopes map to `missing_permissions`. Network-disabled mode returns a safe health result instead of crashing.

## Publishing Behavior

Publishing is disabled by policy.

`META_ENABLE_REAL_PUBLISHING=true` does not enable publishing in this batch. Meta connector publishing methods return `disabled_by_policy` and report `realPublishingEnabled=false`.

Real publishing requires a future explicit platform task with:

- real OAuth
- secure token storage
- verified Meta API docs
- app review requirements understood
- account selection
- platform preflight tests
- approval gates
- emergency pause enforcement
- post-publish audit logs
- manual export fallback
- explicit user confirmation

## Setup Instructions

Each connector exposes setup instructions for:

- Meta developer app setup
- redirect URI
- placeholder scopes
- required account type
- app review warning
- local development notes
- publishing-disabled safety notice

Current scope names are placeholders for planning and tests. Verify exact scopes against official Meta documentation before enabling real OAuth.

## Practical Setup Checklist

For later real OAuth work:

1. Create or select a Meta developer app.
2. Add the local callback URL as `META_REDIRECT_URI`.
3. Add `META_CLIENT_ID` and `META_CLIENT_SECRET` only to local `.env`, never to committed files.
4. Keep `META_ENABLE_REAL_OAUTH=false` until the guarded real OAuth task begins.
5. Keep `META_ENABLE_REAL_PUBLISHING=false`; this flag does not enable publishing in Batch 6.
6. Confirm whether the Facebook Page, Instagram Business/Creator account, or Threads profile requires app review.
7. Run mock OAuth and Connected Accounts tests before touching real credentials.
8. Update docs with verified official API requirements before making network calls.

## Error Handling

Meta errors are normalized into a safe shape:

- `code`
- `message`
- `userSafeMessage`
- `retryable`
- `requiresReauth`
- `missingConfig`
- `rawErrorRedacted`

Raw provider details are redacted before storage or display. Do not log authorization codes, token values, bearer values, or client secrets.

## How To Test

Run:

```text
python -m unittest tests.test_meta_connectors
python -m unittest tests.test_meta_oauth_exchange_readiness
python -m unittest tests.test_meta_account_health
```

These tests cover missing config, mock authorization URL generation, setup instructions, disabled publishing behavior, redacted Meta error normalization, guarded token exchange, placeholder token storage, safe account DTOs, and provider 401/429 handling.
