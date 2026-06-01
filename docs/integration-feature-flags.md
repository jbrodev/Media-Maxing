# Integration Feature Flags

This app is mock-first. Integration flags make future real OAuth testing explicit, reviewable, and safe.

Real publishing is disabled in this batch even if a publishing flag is set to `true`.

Mock mode is the default local experience. It allows setup screens, mock OAuth, mock connected accounts, and manual export workflows without provider credentials or network calls.

Publishing remains disabled until a future explicit real-publishing task changes the policy with tests and documentation.

## Global Flags

- `INTEGRATIONS_MODE`: `mock`, `disabled`, or `real_oauth`.
- `ENABLE_REAL_NETWORK_CALLS`: defaults to `false`.
- `ENABLE_REAL_OAUTH`: defaults to `false`.
- `ENABLE_REAL_PUBLISHING`: defaults to `false` and is blocked by policy in this batch.
- `ALLOW_NETWORK_IN_TESTS`: defaults to `false`.
- `TOKEN_STORAGE_MODE`: `keychain`, `encrypted_file`, `encrypted_database`, `placeholder_not_stored`, or `insecure_dev_only`.

## Platform Flags

Meta/Facebook/Instagram/Threads:

- `META_CLIENT_ID`
- `META_CLIENT_SECRET`
- `META_REDIRECT_URI`
- `META_GRAPH_API_VERSION`
- `META_ENABLE_REAL_OAUTH`
- `META_ENABLE_REAL_PUBLISHING`

Google/YouTube:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`
- `GOOGLE_ENABLE_REAL_OAUTH`
- `GOOGLE_ENABLE_REAL_PUBLISHING`

TikTok:

- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_REDIRECT_URI`
- `TIKTOK_ENABLE_REAL_OAUTH`
- `TIKTOK_ENABLE_REAL_PUBLISHING`

LinkedIn:

- `LINKEDIN_CLIENT_ID`
- `LINKEDIN_CLIENT_SECRET`
- `LINKEDIN_REDIRECT_URI`
- `LINKEDIN_ENABLE_REAL_OAUTH`
- `LINKEDIN_ENABLE_REAL_PUBLISHING`

X:

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_REDIRECT_URI`
- `X_ENABLE_REAL_OAUTH`
- `X_ENABLE_REAL_PUBLISHING`

## Statuses

- `disabled`: integrations or a platform path are off.
- `mock_ready`: mock/demo setup is available without credentials.
- `missing_config`: real OAuth was requested, but required env vars are missing.
- `real_oauth_ready`: flags and required env vars are present for guarded OAuth testing.
- `real_network_disabled`: OAuth flags are set, but network calls remain blocked.
- `publishing_disabled_by_policy`: publishing was requested but is blocked in this build.
- `invalid_config`: enum or boolean values are invalid.
- `error`: an unexpected validation error occurred.

## Safe Defaults

Default local setup should stay:

```text
INTEGRATIONS_MODE=mock
ENABLE_REAL_NETWORK_CALLS=false
ENABLE_REAL_OAUTH=false
ENABLE_REAL_PUBLISHING=false
ALLOW_NETWORK_IN_TESTS=false
TOKEN_STORAGE_MODE=placeholder_not_stored
```

With these values, the app can show setup guidance and mock connections without calling provider APIs.

## Frontend Safety

Frontend-safe configuration can show:

- whether a variable is configured
- masked client IDs
- redirect URIs
- setup status
- user-friendly setup messages

Frontend-safe configuration must never show:

- client secrets
- access tokens
- refresh tokens
- authorization codes
- bearer headers
- raw OAuth state values

## Source Of Truth

The central service is:

```text
scripts/services/integration_flags.py
```

The Social Integration Setup service uses this model so the setup wizard and server-side checks agree.

## How To Test

Run:

```text
python -m unittest tests.test_integration_flags tests.test_integration_setup_service
```

These tests verify safe defaults, missing config, real OAuth readiness, publishing policy blocking, invalid values, and frontend-safe masking.
