# Token Security

This project is local-first and mock/demo-first. Real OAuth token exchange readiness exists for Meta, but raw token storage is not enabled by default.

## Current Strategy

The current MVP storage mode is:

```text
TOKEN_STORAGE_MODE=placeholder_not_stored
```

That means the database can remember that a mock or future account exists, but it does not store real access tokens or refresh tokens. If a guarded real Meta token exchange is manually tested while placeholder mode is active, raw token storage is refused and only placeholder metadata is stored.

The token security service lives in `scripts/services/token_security.py`.

## Storage Modes

Supported storage modes are:

- `keychain`: planned OS keychain storage. Not implemented yet.
- `encrypted_file`: planned encrypted local file storage. Not implemented yet.
- `encrypted_database`: planned encrypted SQLite token blob storage. Not implemented yet.
- `placeholder_not_stored`: current default. Refuses raw token storage.
- `insecure_dev_only`: development-only raw storage for future local experiments.

`insecure_dev_only` is blocked unless both are true:

```text
APP_ENV=development
ALLOW_INSECURE_TOKEN_STORAGE=true
```

Do not use `insecure_dev_only` with real business accounts or real customer data.

`platform_tokens` rows may store token metadata such as:

- social account ID
- platform
- token type
- scope string
- token version
- expiry timestamps
- encryption status

For `placeholder_not_stored` and `missing`, token blob fields must stay null.

## Tables

Token-related tables are:

- `social_accounts`: safe account metadata only.
- `platform_tokens`: token metadata and future encrypted/keychain references.
- `oauth_states`: hashed OAuth state tracking.
- `connector_audit_logs`: redacted connector audit events.
- `connector_health_checks`: local connector readiness snapshots.

## What Must Never Be Stored In Plain Text

Do not store or log:

- access tokens
- refresh tokens
- authorization codes
- client secrets
- API keys
- bearer tokens
- raw OAuth state values
- raw OAuth provider responses that may contain credentials

## OAuth State

OAuth state values must be generated securely by a future OAuth service.

The database stores only:

- `state_hash`
- platform
- redirect URI
- requested scopes
- expiry time
- consumed time
- safe error text

Raw state values are never stored.

## Frontend Safety

Frontend-facing account data must use safe DTOs. Normal account queries should not include:

- `encrypted_access_token`
- `encrypted_refresh_token`
- access tokens
- refresh tokens
- authorization codes
- client secrets
- raw OAuth state values
- state hashes

The helper `list_safe_social_accounts` returns account metadata plus token storage status, not token values.

`TokenSecurityService.list_safe_social_account_dtos()` returns a smaller frontend-safe shape:

- `id`
- `platform`
- `displayName`
- `username`
- `accountType`
- `connectionStatus`
- `capabilities`
- `grantedScopes`
- `missingScopes`
- `requiresReauth`
- `lastConnectedAt`
- `lastValidatedAt`
- `tokenStorageStatus`

It does not include token values, encrypted token blobs, authorization codes, client secrets, full OAuth state values, or state hashes.

## Redaction

Use `redact_token_data` before writing connector metadata to logs, diagnostics, or audit records.

The redaction utility redacts:

- `access_token`
- `refresh_token`
- `client_secret`
- authorization codes
- bearer authorization values
- token-like long strings in known token fields

Redaction is a safety backstop, not permission to log raw provider responses.

## Expiration And Reauth

The token security service includes helpers for:

- checking whether a token expiry timestamp has passed
- deciding whether an account requires reauthorization

Accounts require reauth when:

- the account row already says reauth is required
- connection status is `expired`, `revoked`, `disconnected`, `error`, or `requires_reauth`
- the access token expiry is in the past
- the refresh token expiry is in the past

## Current Limitation

No keychain or encrypted local token vault exists yet. Until one is implemented and tested, guarded real OAuth token exchange can only create limited account metadata and placeholder token rows.

Limited Meta accounts created after a successful guarded token exchange should be treated as setup progress, not production-ready connections:

- account discovery is not implemented
- long-lived token exchange is not implemented
- `requiresReauth` may remain true
- real publishing remains disabled

Future secure storage work should add:

- keychain or encrypted local token storage
- redacted diagnostics
- token backup exclusion
- revoke/disconnect behavior
- tests proving tokens are never exposed to frontend DTOs

## Future OS Keychain Or Encryption Design

A future secure implementation should:

- keep token access server-side only
- store raw token material in OS keychain where available, or encrypted local storage with a key outside the database
- store only token references and safe metadata in SQLite
- exclude token material from backups and diagnostics by default
- redact provider responses before audit logging
- require explicit development-only opt-in before any insecure local token experiment
- keep frontend DTOs limited to safe account status and scope metadata

Real OAuth should remain off until this storage path is implemented and tested.

## How To Test

Run:

```text
python -m unittest tests.test_token_security_service tests.test_social_connection_models
```

These tests cover redaction, placeholder storage refusal, safe DTOs, database constraints, OAuth state hash storage, token metadata rows, and reauth helpers.
