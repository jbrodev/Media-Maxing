# X Connector Scaffold

The X connector prepares the app for possible future X posting while keeping publishing disabled.

X API access, product tiers, limits, and pricing can change. Treat all real X integration work as future, explicit, and gated.

## What Exists Now

- Platform ID: `x`
- Connector feature status: `mock_only`
- OAuth configuration metadata for X.
- Mock authorization URL support.
- Mock OAuth through the shared OAuth flow service.
- Safe profile-health scaffolding with mocked provider responses.
- Connected Accounts and Social Integration Setup show X setup status.
- Manual export remains the posting fallback.

## Environment Variables

```text
X_CLIENT_ID=
X_CLIENT_SECRET=
X_REDIRECT_URI=
X_ENABLE_REAL_OAUTH=false
X_ENABLE_REAL_PUBLISHING=false
```

`X_CLIENT_SECRET` must never be shown in the UI or committed. The setup wizard should only show whether it is configured.

## Setup Checklist

For future real OAuth work:

1. Create or choose an X developer app.
2. Add the local redirect URI, for example `http://localhost:8000/api/connect/x/callback`.
3. Add credentials only to local `.env`.
4. Review X API access, pricing, product tiers, rate limits, and policy requirements.
5. Verify exact scopes before real OAuth or posting.
6. Keep publishing disabled until a future explicit publishing task adds safety gates.

## Placeholder Scopes

- `users.read`: future profile discovery.
- `tweet.read`: future readiness checks only; reading timelines/comments is disabled in this build.
- `tweet.write`: future posting only; disabled in this build.
- `offline.access`: future token refresh support only; disabled until secure storage exists.

These scopes are placeholders. Verify current X documentation, API tier, pricing, and product access before production use.

## OAuth Behavior

Mock mode works without credentials and does not call X APIs.

Real OAuth token exchange is not implemented for X in this build. Any future implementation must require global real OAuth flags, X-specific flags, real network flags, state validation, server-side execution, and token security service storage.

## Health Checks

`validateConnection()` can return a safe connector health result. Tests use mocked HTTP responses or mock mode. No real profile, comments, timelines, or analytics data is fetched by default.

Health checks can update:

- `social_accounts.last_validated_at`
- `connector_health_checks`
- `connector_audit_logs`

Safe DTOs do not include tokens, authorization codes, client secrets, or encrypted token blobs.

## Publishing

X text, image, and video publishing are disabled by policy. `publishText()`, `publishImage()`, and `publishVideo()` return `disabled_by_policy` and do not call X APIs.

Future publishing support must require:

- verified API docs
- access/pricing review
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
python -m unittest tests.test_x_connector
```

The tests cover capabilities, setup instructions, missing X config, mock authorization URL generation, mock OAuth account creation, safe health checks, and disabled publishing.
