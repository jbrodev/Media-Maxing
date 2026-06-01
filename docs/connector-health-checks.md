# Connector Health Checks

Connector health checks verify local connected-account readiness without publishing, reading comments, fetching analytics, or calling real APIs by default.

## What Exists Now

- Meta connectors expose `getAccountProfile()` and `validateConnection()`.
- YouTube, TikTok, LinkedIn, and X expose scaffolded `getAccountProfile()` and `validateConnection()` methods for mock/local readiness checks.
- Health checks can update `social_accounts.last_validated_at`.
- Health checks create safe `connector_health_checks` rows.
- Health checks create `connector_audit_logs` entries with safe metadata only.
- Browser Connected Accounts can run a mock/local **Check connection** action.

## Health Statuses

- `healthy`: local metadata and mocked provider response look usable.
- `limited`: discovery is incomplete or the account type needs confirmation.
- `expired`: token metadata or provider auth response requires reauthorization.
- `revoked`: reserved for future provider revoke signals.
- `missing_permissions`: required scopes or permissions are missing.
- `missing_config`: reserved for setup/config failures.
- `network_disabled`: real provider calls are blocked by safety policy.
- `error`: a safe non-secret provider or local error occurred.

## Meta Discovery Scaffold

The Meta scaffold supports Facebook, Instagram, and Threads profile discovery shapes:

- Facebook: Page/account display name, account type `page`, platform account ID.
- Instagram: Business/Creator display name or username, platform account ID, business-account warnings.
- Threads: display name or username, platform account ID.

Real discovery endpoints are centralized in `scripts/connectors/meta/oauth.py` and marked TODO for future API verification. Tests use mocked HTTP responses.

## Non-Meta Platform Scaffolds

YouTube, TikTok, LinkedIn, and X health checks are scaffolded for local readiness. They can validate local account records, run mock HTTP responses, update `last_validated_at`, and record safe health/audit rows.

Real profile discovery for these platforms is future work. It must stay behind global and platform-specific real OAuth/network flags, and tests must continue to mock provider responses by default.

## Missing Token Behavior

If a real token is missing because `TOKEN_STORAGE_MODE=placeholder_not_stored`, the connector should return `limited`, `expired`, or `requires_reauth` depending on the local metadata available. It should not crash or ask the frontend for a token.

## Expired Token Behavior

Expired token metadata should mark the account as requiring reauthorization. Provider `401` errors should map to `expired` or `requires_reauth` without exposing raw provider responses.

## Missing Permissions Behavior

Missing scopes or provider permission errors should return `missing_permissions` or `limited` with user-safe warnings. Manual export should remain available when content preflight otherwise passes.

## Network Disabled Behavior

When network calls are disabled, health checks should return `network_disabled` instead of attempting a provider request. This is the default posture in tests and unconfigured local development.

## UI Behavior

Connected Accounts can show health status, last checked time, missing scopes, requires-reauth status, and safe warnings. It must never show tokens, client secrets, authorization codes, encrypted token blobs, or raw OAuth state values.

## Safety Rules

- No publishing occurs.
- No comments, replies, or analytics are fetched.
- Network calls are disabled unless connector flags and the server-only HTTP client explicitly allow them.
- Raw token values, authorization codes, client secrets, and raw provider credential responses must not be logged or shown.
- `rawProviderResponseRedacted` is available only for debug/test-safe output.

## How To Test

Run:

```text
python -m unittest tests.test_meta_account_health
```

These tests cover mocked healthy discovery, Instagram missing permissions, expired token metadata, network-disabled behavior, provider 401 reauth mapping, and safe profile DTO output.
