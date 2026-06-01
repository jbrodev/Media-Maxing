# Connected Accounts

Connected Accounts is the local setup area for future social platform integrations.

The current build is mock/demo only. It helps a user see which platforms are planned, what account type may be needed, which permissions/scopes are expected later, and whether a local mock account is connected.

## What Works Now

- Platform cards exist for Facebook, Instagram, Threads, YouTube, TikTok, LinkedIn, and X.
- Facebook and Instagram can be mock connected from the browser UI.
- Mock connected accounts persist in local browser storage.
- Disconnect marks a mock account disconnected locally.
- Check connection validates mock/local health status and records a safe audit event.
- A small local audit log records mock connect and disconnect events.
- The UI shows only safe account details.
- Publish Queue preflight can use connected account status as a local readiness signal.

## What Is Not Real Yet

- No real social platform APIs are called.
- No real OAuth exchange is performed from the UI.
- No real publishing is enabled.
- No comments, replies, analytics, or profile data are fetched.
- No real credentials are required.

## Account Statuses

Connected account records can use these statuses:

- `not_connected`
- `connecting`
- `connected`
- `limited`
- `expired`
- `revoked`
- `disconnected`
- `error`
- `requires_reauth`

Only `connected` and some `limited` mock/demo accounts are useful for local readiness display. Expired, revoked, disconnected, error, and requires-reauth accounts do not satisfy future real publishing readiness.

## Token Safety

The browser UI must not show or store platform secret values. The current mock connection records use `placeholder_not_stored` for storage mode.

Future real OAuth work should use the server-side OAuth state service and token security service. Frontend responses should only include safe account DTO fields such as display name, platform, status, scopes, and timestamps.

## Mock Connect Flow

1. Open Connected Accounts.
2. Choose **Connect mock** for Facebook or Instagram.
3. The app creates a fake local account record.
4. The account appears in the connected account list.
5. Real publishing remains disabled.

## Disconnect Flow

1. Choose **Disconnect** on a mock account.
2. Confirm the local disconnect.
3. The account is marked disconnected.
4. A local audit entry is created.
5. No external revoke is attempted.

## Reauth And Missing Scopes

Reauth is needed when an account is expired, revoked, disconnected, in error, or explicitly marked `requires_reauth`.

Missing scopes are stored as safe metadata. They tell the user what a future OAuth setup may need. Missing scopes do not expose tokens and do not block manual export by themselves.

## Health Checks

Connected Accounts includes a **Check connection** action. In the current static web app this is a mock/local check only. It updates health status, last validated time, missing permissions, warnings, and audit history in local browser storage.

The Python Meta connectors also expose `validateConnection()` and `getAccountProfile()` for server-side health scaffolding. Those methods can use mocked provider responses in tests and update local SQLite records. Real provider discovery remains gated and disabled by default.

## Publish Queue Readiness

Connected account status is shown in Publish Queue cards and detail panels.

Current rules:

- Missing account: warning only for manual export; future real publishing would be blocked.
- Mock connected account: satisfies mock/demo account checks, but real publishing stays disabled.
- Expired, revoked, error, or requires-reauth account: warning in the UI and future real publishing blocked.
- Limited account: shown with missing scopes or setup warnings.
- Multiple accounts for one platform: the app uses a safe local default and warns that account selection will be needed later.

Manual export remains the fallback when content preflight passes. No tokens are shown and no platform API calls are made.

## Future Work

- Wire the web UI to `apps/api/connect_handlers.py`.
- Add real OAuth only behind explicit feature flags.
- Keep publishing disabled until a future real-publishing task adds platform-specific safety gates, tests, and documentation.

## How To Test

Run:

```text
python -m unittest tests.test_social_connection_models tests.test_web_connected_accounts_screen
python -m unittest tests.test_meta_account_health
```

These tests cover safe mock account storage, placeholder token rows, safe frontend DTOs, browser UI token-field exclusions, and Connected Accounts screen wiring.
