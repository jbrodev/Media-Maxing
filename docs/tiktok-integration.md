# TikTok Connector Scaffold

The TikTok connector prepares the app for future TikTok video posting while keeping posting and uploads disabled.

Publishing disabled status: TikTok publishing remains disabled in this build.

## What Exists Now

- Platform ID: `tiktok`
- Connector feature status: `mock_only`
- OAuth configuration metadata for TikTok.
- Mock authorization URL support.
- Mock OAuth through the shared OAuth flow service.
- Safe profile-health scaffolding with mocked provider responses.
- Connected Accounts and Social Integration Setup show TikTok setup status.
- Manual export remains the posting fallback.

## Environment Variables

```text
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_REDIRECT_URI=
TIKTOK_ENABLE_REAL_OAUTH=false
TIKTOK_ENABLE_REAL_PUBLISHING=false
```

`TIKTOK_CLIENT_SECRET` must never be shown in the UI or committed. The setup wizard should only show whether it is configured.

## Setup Checklist

For future real OAuth work:

1. Create or choose a TikTok developer app.
2. Add the local redirect URI, for example `http://localhost:8000/api/connect/tiktok/callback`.
3. Add credentials only to local `.env`.
4. Verify exact TikTok scopes and review requirements before real OAuth.
5. Plan for app review and content posting review before any real video posting.
6. Keep posting disabled until a future explicit publishing task adds safety gates.

## Placeholder Scopes

- `user.info.basic`: future profile discovery.
- `video.upload`: future video posting only; disabled in this build.

These scopes are placeholders. Verify current TikTok documentation before production use.

## OAuth Behavior

Mock mode works without credentials and does not call TikTok APIs.

Real OAuth token exchange is not implemented for TikTok in this build. Any future implementation must require global real OAuth flags, TikTok-specific flags, real network flags, state validation, server-side execution, and token security service storage.

## Health Checks

`validateConnection()` can return a safe connector health result. Tests use mocked HTTP responses or mock mode. No real profile data is fetched by default.

Health checks can update:

- `social_accounts.last_validated_at`
- `connector_health_checks`
- `connector_audit_logs`

Safe DTOs do not include tokens, authorization codes, client secrets, or encrypted token blobs.

## Posting

TikTok video posting is disabled by policy. `publishVideo()` returns `disabled_by_policy` and does not call the TikTok API.

Future posting support must require:

- verified API docs
- secure token storage
- explicit account selection
- approved draft/scheduled queue item
- passed preflight
- emergency pause enforcement
- audit logs
- manual export fallback

## How To Test

Run:

```text
python -m unittest tests.test_tiktok_connector
```

The tests cover capabilities, setup instructions, missing TikTok config, mock authorization URL generation, mock OAuth account creation, safe health checks, and disabled posting.
