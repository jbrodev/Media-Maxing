# OAuth Flow

This document describes the current OAuth scaffolding for connected social accounts.

The implementation is safe local-first OAuth scaffolding. Mock OAuth remains the default. A guarded Meta short-lived token exchange path exists for future manual testing, but it does not run unless explicit safety flags and credentials are configured. The app still does not publish content.

## Current Implementation

The source-of-truth service is:

```text
scripts/services/oauth_flow.py
```

Because the repo does not have a real API framework yet, route-shaped handler functions are also provided in:

```text
apps/api/connect_handlers.py
```

Planned route shapes are:

- `POST /api/connect/:platform/start`
- `GET /api/connect/:platform/callback`
- `POST /api/connect/:platform/disconnect`
- `GET /api/connect/accounts`
- `GET /api/connect/platforms`

## Start Flow

OAuth start:

1. Validates the platform ID.
2. Loads the platform connector.
3. Confirms the connector supports OAuth.
4. Generates a secure random state value.
5. Stores only `state_hash` in `oauth_states`.
6. Stores redirect URI and requested scopes.
7. Sets an expiration timestamp.
8. Creates a safe connector audit log.
9. Returns a mock authorization URL.

The raw state value appears only inside the authorization URL so the callback can validate it later. The state hash is never returned to frontend code.

## Callback Flow

OAuth callback:

1. Validates the platform ID.
2. Requires a state value.
3. Hashes the callback state and looks up the stored hash.
4. Rejects missing, wrong, expired, reused, or failed states.
5. Requires a code value, but does not log it.
6. In mock mode, creates a local mock social account.
7. In guarded Meta real OAuth mode, validates feature flags and configuration before any network call.
8. Creates a placeholder token metadata row with `placeholder_not_stored`, or delegates token storage to the token security service.
9. Marks the OAuth state consumed after a successful callback path.
10. Creates safe connector audit logs.
11. Returns a frontend-safe account DTO.

## Guarded Meta Token Exchange

Meta token exchange is available only through server-side code.

It requires:

- `ENABLE_REAL_OAUTH=true` or `INTEGRATIONS_MODE=real_oauth`
- `ENABLE_REAL_NETWORK_CALLS=true`
- `META_ENABLE_REAL_OAUTH=true`
- `META_CLIENT_ID`
- `META_CLIENT_SECRET`
- `META_REDIRECT_URI`
- valid, unexpired, unused OAuth state
- callback authorization code

If any requirement is missing, no network call is made.

The exchange sends a form-encoded request through the server-only platform HTTP client. Provider responses and errors are redacted before audit logs or returned error objects are created.

With `TOKEN_STORAGE_MODE=placeholder_not_stored`, raw token storage is refused. The app creates a limited connected account and placeholder token metadata so UI and preflight can represent the connection without exposing token material.

## Failure Cases

The OAuth service returns safe failures for:

- unsupported platform
- missing state
- wrong state
- expired state
- reused state
- missing authorization code
- OAuth provider error parameter
- real OAuth disabled by flags
- real network calls disabled
- missing Meta configuration
- provider token exchange errors
- provider reauthorization errors
- provider rate limits

Failures should create safe audit logs where useful, but must not log raw state values, authorization codes, access tokens, refresh tokens, or client secrets.

## Mock OAuth Mode

Mock mode is the default:

```text
INTEGRATIONS_MODE=mock
```

Mock OAuth:

- works without API keys
- creates local demo account records
- stores no real tokens
- uses `placeholder_not_stored`
- is suitable for Connected Accounts UI development

Mock connected accounts are not real platform connections.

## State Expiration

OAuth state expires after 10 minutes:

```text
DEFAULT_OAUTH_STATE_TTL_SECONDS = 600
```

Expired state is rejected and marked `expired`.

Consumed state is rejected if reused.

Invalid state is rejected without revealing whether any other state exists.

## Audit Logs

The flow writes `connector_audit_logs` for:

- `oauth_start`
- `oauth_callback`
- `disconnect`

Audit metadata must not include:

- raw state values
- state hashes
- authorization codes
- access tokens
- refresh tokens
- client secrets
- raw provider responses

## Real OAuth Future Work

Before real OAuth becomes operator-ready, the app still needs:

- verified official platform OAuth docs
- secure token storage/keychain or encrypted local token vault
- account/profile discovery tests
- connector health checks
- explicit safety documentation

Real publishing remains disabled even after OAuth is added.

## How To Test

Run:

```text
python -m unittest tests.test_oauth_flow_service
python -m unittest tests.test_meta_oauth_exchange_readiness
```

These tests cover valid mock callback, missing/wrong/expired/reused state, state hash storage, safe route handler shapes, unsupported platform handling, guarded Meta token exchange, no-network blocked cases, placeholder token storage, and safe provider errors.
