# LinkedIn Connector Scaffold

The LinkedIn connector prepares the app for future personal and organization posting while keeping publishing disabled.

## What Exists Now

- Platform ID: `linkedin`
- Connector feature status: `mock_only`
- OAuth configuration metadata for LinkedIn.
- Mock authorization URL support.
- Mock OAuth through the shared OAuth flow service.
- Safe profile-health scaffolding with mocked provider responses.
- Connected Accounts and Social Integration Setup show LinkedIn setup status.
- Manual export remains the posting fallback.

## Environment Variables

```text
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=
LINKEDIN_ENABLE_REAL_OAUTH=false
LINKEDIN_ENABLE_REAL_PUBLISHING=false
```

`LINKEDIN_CLIENT_SECRET` must never be shown in the UI or committed. The setup wizard should only show whether it is configured.

## Setup Checklist

For future real OAuth work:

1. Create or choose a LinkedIn Developer app.
2. Add the local redirect URI, for example `http://localhost:8000/api/connect/linkedin/callback`.
3. Add credentials only to local `.env`.
4. Verify Product access requirements for posting, comments, organization pages, and analytics.
5. Add organization/page selection before future company posting.
6. Keep publishing disabled until a future explicit publishing task adds safety gates.

## Placeholder Scopes

- `openid`: future identity readiness.
- `profile`: future personal profile discovery.
- `w_member_social`: future member posting only; disabled in this build.
- `w_organization_social`: future organization/page posting only; disabled in this build.
- `r_organization_social`: future comments and analytics readiness only; disabled in this build.

These scopes are placeholders. Verify current LinkedIn documentation and Product access requirements before production use.

## OAuth Behavior

Mock mode works without credentials and does not call LinkedIn APIs.

Real OAuth token exchange is not implemented for LinkedIn in this build. Any future implementation must require global real OAuth flags, LinkedIn-specific flags, real network flags, state validation, server-side execution, and token security service storage.

## Health Checks

`validateConnection()` can return a safe connector health result. Tests use mocked HTTP responses or mock mode. No real profile, company page, comments, or analytics data is fetched by default.

Health checks can update:

- `social_accounts.last_validated_at`
- `connector_health_checks`
- `connector_audit_logs`

Safe DTOs do not include tokens, authorization codes, client secrets, or encrypted token blobs.

## Publishing

LinkedIn text, image, and video publishing are disabled by policy. `publishText()`, `publishImage()`, and `publishVideo()` return `disabled_by_policy` and do not call LinkedIn APIs.

Future publishing support must require:

- verified API docs
- Product access approval
- secure token storage
- explicit personal or organization account selection
- approved draft/scheduled queue item
- passed preflight
- emergency pause enforcement
- audit logs
- manual export fallback

## How To Test

Run:

```text
python -m unittest tests.test_linkedin_connector
```

The tests cover capabilities, setup instructions, missing LinkedIn config, mock authorization URL generation, mock OAuth account creation, safe health checks, and disabled publishing.
