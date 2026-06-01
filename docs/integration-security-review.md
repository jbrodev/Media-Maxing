# Integration Security Review

This review summarizes the Batch 6 security posture for future social integrations. It is written for local development and handoff. It is not a production security certification.

Real publishing remains disabled.

## Protected Secrets

The app must protect:

- access tokens
- refresh tokens
- authorization codes
- client secrets
- bearer tokens
- encrypted token blobs
- raw OAuth state values
- raw provider responses that contain credentials

These values must not appear in logs, frontend responses, committed docs, fixtures, snapshots, manual exports, diagnostics, or screenshots.

## Redacted Values

The token security service and platform HTTP client redact:

- `access_token`
- `refresh_token`
- `client_secret`
- `Authorization`
- bearer token values
- OAuth authorization `code`
- `id_token`
- `appsecret_proof`
- `signed_request`
- `set-cookie` headers
- long token-like values in known sensitive fields

Redaction is a backstop. Connector code should still avoid handling raw provider responses outside server-only paths.

## Token Storage

The MVP default is:

```text
TOKEN_STORAGE_MODE=placeholder_not_stored
```

In this mode, raw OAuth tokens are not stored. The app may store token metadata such as expiration time, scope, token type, version, and storage status.

Other storage modes are planned but not production-ready:

- `keychain`
- `encrypted_file`
- `encrypted_database`
- `insecure_dev_only`

`insecure_dev_only` must be restricted to development and must never be used for production or real business accounts.

## Current Storage Limitations

Because the current default does not store raw tokens, real OAuth-connected accounts may be limited and may require reauthorization. Token refresh is scaffolded, not operational for real provider tokens.

This is intentional until secure local storage is implemented and reviewed.

## Avoid Committing Secrets

Never commit:

- `.env`
- local SQLite databases
- logs
- exports
- backups
- uploaded media
- provider token files
- screenshots that show credentials

Only commit `.env.example` with empty placeholders and safe defaults.

## Checklist Before Real OAuth

Before enabling real OAuth for a platform:

1. Confirm `ENABLE_REAL_OAUTH=true` and the platform real OAuth flag are intentional.
2. Confirm `ENABLE_REAL_NETWORK_CALLS=true` is intentional.
3. Verify redirect URI settings.
4. Verify scopes against current official platform docs.
5. Confirm token storage mode and limitations.
6. Confirm OAuth state hashing and expiration are tested.
7. Confirm connector audit logs do not contain secrets.
8. Run the security scan.
9. Run connector and OAuth tests.
10. Keep publishing disabled.

## Checklist Before Real Publishing

Before any real publishing work:

1. Implement one platform at a time.
2. Verify official platform publishing docs and API limits.
3. Implement secure token storage.
4. Require explicit account selection.
5. Require approved drafts and passed preflight.
6. Enforce emergency pause.
7. Create post-publish audit logs.
8. Handle rate limits and provider errors.
9. Keep manual export fallback.
10. Update launch checklist and safety docs.
11. Require explicit user confirmation.

## Security Scan

Run:

```text
python -m scripts.qa.integration_security_scan .
```

The scan reports counts only and does not print suspected secret values. It is okay for docs and `.env.example` to mention variable names such as `X_CLIENT_SECRET`; it is not okay to include real-looking secret values.

## Frontend Safety

Frontend-safe account DTOs must not include tokens, authorization codes, client secrets, encrypted token blobs, or raw OAuth state values.

Connected Accounts and Social Integration Setup may show connection status, masked configuration status, redirect URIs, missing scopes, setup instructions, and health status.
