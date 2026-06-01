# Social Integration Setup

The Social Integration Setup screen helps a non-coder understand what is ready, what is missing, and what can stay in mock mode for now.

This setup helper does not publish posts, call real social APIs, fetch comments, fetch analytics, or store real tokens.

## What The Wizard Shows

- Supported platforms: Facebook, Instagram, Threads, YouTube Shorts, TikTok, LinkedIn, and X.
- Current setup status: mock ready, missing configuration, real OAuth ready, real network disabled, disabled, publishing disabled by policy, invalid config, or error.
- Required and optional environment variables.
- OAuth redirect URI to copy into a future developer app.
- Required account type and placeholder future scopes.
- Mock connection test availability.
- Real OAuth availability.
- Real publishing availability, which remains disabled in this build.
- Per-platform setup checklist.
- Developer docs placeholders that must be verified before real integrations are enabled.

## Mock Mode

Mock mode is the default and safest path.

In mock mode:

- No API keys are required.
- Facebook, Instagram, YouTube, TikTok, LinkedIn, and X can run a local mock connection test from the browser UI.
- Mock connected accounts are local demo records.
- No token is stored.
- Manual export remains the safe posting path.

## Real Mode

Real OAuth is planned for a later batch. It must stay disabled unless a future task explicitly enables one platform with safety gates.

Before real OAuth is used, the app must have:

- Server-side OAuth handling.
- Hashed OAuth state validation.
- Secure token storage or an approved placeholder strategy.
- Redacted logs.
- Safe frontend account DTOs.
- Platform-specific setup docs verified against official provider docs.

Real publishing is still disabled even if environment flags are accidentally set to true.

## Environment Validation

The server-side validation service is `scripts/services/integration_setup.py`.

It checks:

- `APP_ENV` is known.
- `LOCAL_DATA_DIR` exists.
- `INTEGRATIONS_MODE` is known.
- `TOKEN_STORAGE_MODE` is known.
- Required platform environment variables are present.
- Redirect URI variables are present.
- Real OAuth flags are disabled by default.
- Real publishing flags are disabled by default.
- Secret values are never returned in validation output.

The localhost browser UI consumes masked validation output from
`GET /api/integration-setup`. Opening the HTML file directly uses a temporary
demo mirror for static inspection only.

## Secret Masking

Client secrets, token-like fields, and API-key-like fields must not be displayed.

The setup helper shows:

- `Not configured` for blank values.
- `Configured, hidden` for secret values.
- Masked client IDs where useful.
- Full redirect URIs because redirect URIs are not secrets.

## Required Env Vars By Platform

Meta platforms: Facebook, Instagram, Threads

- `META_CLIENT_ID`
- `META_CLIENT_SECRET`
- `META_REDIRECT_URI`

YouTube Shorts

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI`

YouTube setup also requires a future Google Cloud project, OAuth consent screen, YouTube Data API enablement review, and app verification review before any real OAuth or upload work.

TikTok

- `TIKTOK_CLIENT_KEY`
- `TIKTOK_CLIENT_SECRET`
- `TIKTOK_REDIRECT_URI`

TikTok setup also requires a future TikTok developer app, redirect URI configuration, scope verification, app review planning, and content posting review planning before any real OAuth or video posting work.

LinkedIn

- `LINKEDIN_CLIENT_ID`
- `LINKEDIN_CLIENT_SECRET`
- `LINKEDIN_REDIRECT_URI`

LinkedIn setup also requires a future LinkedIn Developer app, redirect URI configuration, Product access review, organization/page access planning, and app review planning before any real OAuth or publishing work.

X

- `X_CLIENT_ID`
- `X_CLIENT_SECRET`
- `X_REDIRECT_URI`

X setup also requires a future X developer app, redirect URI configuration, API access/pricing review, product tier review, scope verification, and rate-limit review before any real OAuth or publishing work.

## Adding API Keys Later

When you are ready for future real OAuth work:

1. Start from `.env.example` in the repo root.
2. Copy it to `.env`.
3. Add credentials only in `.env`.
4. Do not edit `.env.example` with real values.
5. Keep real OAuth and real publishing flags set to `false` unless a future prompt explicitly tells you otherwise.
6. Open Social Integration Setup and check which values are still missing.

Important files:

- Root template: `.env.example`
- API template: `apps/api/.env.example`
- Browser-safe template: `apps/web/.env.example`
- Do not commit: `.env`, `apps/api/.env`, local databases, logs, exports, backups, or media files.

## What The Env Vars Mean

- `APP_ENV`: local app environment such as `development`.
- `LOCAL_DATA_DIR`: folder for local app data.
- `DATABASE_URL`: local SQLite connection path.
- `INTEGRATIONS_MODE`: defaults to `mock`; allowed values are `mock`, `disabled`, and `real_oauth`.
- `ENABLE_REAL_NETWORK_CALLS`: must stay `false` until real integration work.
- `ENABLE_REAL_OAUTH`: must stay `false` until guarded OAuth work.
- `ENABLE_REAL_PUBLISHING`: must stay `false`; publishing is not implemented.
- `TOKEN_STORAGE_MODE`: defaults to `placeholder_not_stored`.
- Platform client IDs: identify a future developer app and are masked in UI.
- Platform client secrets: secret values that must never be displayed or committed.
- Platform redirect URIs: callback URLs to copy into provider developer settings.
- Per-platform OAuth/publishing flags: future safety flags; publishing remains disabled even if accidentally set.

## Confirming Setup Status

Use the Social Integration Setup screen in the web app:

1. Run `python -m apps.api.local_server --database data/app.sqlite --port 8000`.
2. Open `http://127.0.0.1:8000/#setup`.
3. Select a platform.
4. Review missing env vars, redirect URI, setup checklist, and mock connection availability.
5. Choose **I will add API keys later** to stay safely in mock mode.

The localhost bridge loads the repo-root `.env` file when present and returns
only masked validation status. The server-side validation service in
`scripts/services/integration_setup.py` uses
`scripts/services/integration_flags.py` as the source of truth.

See also:

- `docs/integration-feature-flags.md`
- `docs/platform-http-client.md`
- `docs/meta-oauth-real-mode.md`
- `docs/connector-health-checks.md`
- `docs/youtube-integration.md`
- `docs/tiktok-integration.md`
- `docs/linkedin-integration.md`
- `docs/x-integration.md`
- `docs/integration-security-review.md`

## How To Verify Locally

Run:

```text
python -m unittest tests.test_integration_setup_service
python -m unittest tests.test_integration_flags
python -m unittest tests.test_web_social_setup_screen
```

To inspect the current environment safely from Python, call `validate_social_integration_setup()` and use `to_dict()`. Do not print raw `.env` values.
