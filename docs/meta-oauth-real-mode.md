# Meta OAuth Real Mode Readiness

Meta real OAuth readiness exists so future Facebook, Instagram, and Threads connection testing can be added carefully. It does not publish posts, read comments, fetch analytics, or send replies.

Real OAuth is off by default. Mock mode remains the normal local path.

## Required Environment Variables

Meta OAuth testing requires:

```text
INTEGRATIONS_MODE=real_oauth
ENABLE_REAL_OAUTH=true
ENABLE_REAL_NETWORK_CALLS=true
META_ENABLE_REAL_OAUTH=true
META_CLIENT_ID=
META_CLIENT_SECRET=
META_REDIRECT_URI=
META_GRAPH_API_VERSION=
```

`META_CLIENT_SECRET` must stay server-side. Do not show it in the browser, logs, docs, fixtures, screenshots, or committed files.

Publishing flags also exist:

```text
ENABLE_REAL_PUBLISHING=false
META_ENABLE_REAL_PUBLISHING=false
```

Publishing remains disabled even if those values are accidentally set to `true`.

## OAuth Start Flow

The OAuth start flow:

1. Validates the platform is Facebook, Instagram, or Threads.
2. Checks integration feature flags.
3. Generates a secure OAuth state value.
4. Stores only a hash of the state in `oauth_states`.
5. Stores requested scopes and redirect URI.
6. Builds an authorization URL.
7. Creates a connector audit log.

The raw state value is returned only as part of the local redirect flow. The state hash is never exposed to frontend code.

## OAuth Callback Flow

The callback flow:

1. Validates platform and callback state.
2. Rejects missing, wrong, expired, or reused state.
3. Rejects missing authorization codes.
4. Checks all real OAuth and network flags again.
5. Exchanges the code only when every guard passes.
6. Marks the state consumed.
7. Creates connector audit logs.

Authorization codes are never logged.

## Token Exchange Behavior

The Meta token exchange path uses the server-only platform HTTP client. It supports form-encoded token requests and provider error normalization.

If real OAuth is disabled, network calls are disabled, config is missing, or state is invalid, the exchange returns a safe error and does not call Meta.

Provider responses are redacted before they can appear in errors or audit metadata. HTTP `401` maps to a reauthorization-required result. HTTP `429` maps to a rate-limited result.

## Token Storage Behavior

Tokens must pass through the token security service.

The current MVP default is:

```text
TOKEN_STORAGE_MODE=placeholder_not_stored
```

In `placeholder_not_stored` mode, raw tokens are refused and token metadata is stored instead. Accounts created from this mode may be marked `limited` and `requires_reauth` because the app cannot refresh or use the real token later.

Future secure storage may use OS keychain, encrypted files, or encrypted database storage, but that must be implemented and reviewed separately.

## Account Discovery Limitations

The current token exchange can create a limited connected account when the token response does not include profile or account data.

Meta account discovery is scaffolded separately through connector health checks. Real discovery endpoints require future verification against current Meta API docs and app review requirements.

## App Review Notes

Before real Meta OAuth is used beyond local testing, review:

- requested scopes
- redirect URI configuration
- Facebook Page access requirements
- Instagram Business or Creator requirements
- Threads API requirements
- Meta app review status
- rate limits and error handling

## Publishing Disabled Note

Meta publishing remains disabled. Manual export is the safe path until a future explicit real-publishing task adds platform-specific tests, approval gates, emergency pause enforcement, audit logs, and user confirmation.

## How To Test

Run:

```text
python -m unittest tests.test_meta_oauth_exchange_readiness
```

The tests use mocked HTTP responses and prove that disabled flags, missing config, and invalid state prevent network calls.
