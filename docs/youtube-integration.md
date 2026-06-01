# YouTube Connector Scaffold

The YouTube connector prepares the app for future YouTube Shorts/channel support while keeping upload and publishing disabled.

## What Exists Now

- Platform ID: `youtube`
- Connector feature status: `mock_only`
- OAuth configuration metadata for Google/YouTube.
- Mock authorization URL support.
- Mock OAuth through the shared OAuth flow service.
- Safe channel-profile health scaffolding with mocked provider responses.
- Connected Accounts and Social Integration Setup show YouTube setup status.
- Manual export remains the posting fallback.

## Environment Variables

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GOOGLE_ENABLE_REAL_OAUTH=false
GOOGLE_ENABLE_REAL_PUBLISHING=false
```

`GOOGLE_CLIENT_SECRET` must never be shown in the UI or committed. The setup wizard should only show whether it is configured.

## Setup Checklist

For future real OAuth work:

1. Create or choose a Google Cloud project.
2. Configure the OAuth consent screen.
3. Add the local redirect URI, for example `http://localhost:8000/api/connect/youtube/callback`.
4. Enable the YouTube Data API only after reviewing current Google requirements and quotas.
5. Verify exact scopes and app verification requirements before real OAuth.
6. Keep upload/publishing disabled until a future explicit publishing task adds safety gates.

## Placeholder Scopes

- `https://www.googleapis.com/auth/youtube.readonly`: future channel/profile discovery.
- `https://www.googleapis.com/auth/youtube.upload`: future upload work only; disabled in this build.

These scopes are placeholders. Verify current Google documentation before production use.

## OAuth Behavior

Mock mode works without credentials and does not call Google APIs.

Real OAuth token exchange is not implemented for YouTube in this build. Any future implementation must require global real OAuth flags, Google-specific flags, real network flags, state validation, server-side execution, and token security service storage.

## Health Checks

`validateConnection()` can return a safe connector health result. Tests use mocked HTTP responses or mock mode. No real channel data is fetched by default.

Health checks can update:

- `social_accounts.last_validated_at`
- `connector_health_checks`
- `connector_audit_logs`

Safe DTOs do not include tokens, authorization codes, client secrets, or encrypted token blobs.

## Upload And Publishing

Video upload is disabled by policy. `publishVideo()` returns `disabled_by_policy` and does not call the YouTube API.

Future upload support must require:

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
python -m unittest tests.test_youtube_connector
```

The tests cover capabilities, setup instructions, missing Google config, mock authorization URL generation, mock OAuth account creation, safe health checks, and disabled upload.
