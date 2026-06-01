# Social Connectors

This document describes the connector foundation for future social platform integrations.

The current connector layer is scaffold-only. It does not call real platform APIs, does not store tokens, does not publish posts, and does not send replies.

## Supported Platforms

The platform identifiers are:

- `facebook`
- `instagram`
- `threads`
- `youtube`
- `tiktok`
- `linkedin`
- `x`

Use these IDs consistently in database rows, services, UI adapters, preflight checks, and manual export metadata.

## Connector Responsibilities

Each connector exposes:

- platform identity
- capabilities
- OAuth configuration metadata
- authorization URL builder
- OAuth callback handler
- token refresh placeholder
- connection validation placeholder
- local disconnect placeholder
- safe account profile access
- required permission scopes
- setup instructions

The Python source of truth lives in `scripts/connectors/`.

Shared frontend-facing TypeScript shapes live in `packages/types/index.ts`.

## Feature Statuses

Supported feature statuses are:

- `unavailable`
- `planned`
- `scaffolded`
- `mock_only`
- `requires_credentials`
- `requires_app_review`
- `ready_for_testing`
- `enabled`

Meta platforms now use dedicated `mock_only` connector scaffolds:

- Facebook
- Instagram
- Threads

YouTube Shorts now also uses a dedicated `mock_only` connector scaffold for OAuth readiness and mocked channel health checks.

TikTok now uses a dedicated `mock_only` connector scaffold for OAuth readiness, mocked profile health checks, and future video posting setup.

LinkedIn now uses a dedicated `mock_only` connector scaffold for OAuth readiness, mocked profile health checks, Product access planning, and future personal/company posting setup.

X now uses a dedicated `mock_only` connector scaffold for OAuth readiness, mocked profile health checks, API access/pricing planning, and future posting setup.

## Safe Defaults

All connector capabilities default to safe values:

- real publishing disabled
- real comment replies disabled
- real token refresh disabled
- real network checks disabled
- manual export fallback supported

Publishing helper methods return `disabled_by_policy`. This is intentional. Real publishing requires a future explicit platform implementation with OAuth, secure token storage, preflight tests, approval gates, emergency pause enforcement, and documentation.

## Platform Registry

The central registry can:

- list supported platforms
- return connector metadata
- retrieve a connector by platform
- list platform capabilities
- list setup statuses
- identify mock-only platforms
- identify platforms that are not configured

Unknown platform IDs return a useful error instead of silently falling back.

## How To Add A Connector

When adding a new connector:

1. Add or update the platform connector class under `scripts/connectors/`.
2. Register it in `scripts/connectors/registry.py`.
3. Define safe capabilities first. Publishing and replies must stay false unless a future real-platform task explicitly enables them.
4. Add required scopes as `PlatformPermissionScope` records.
5. Add setup instructions in plain language.
6. Add missing-config behavior that does not call the provider.
7. Add tests for registry lookup, capabilities, setup status, and disabled publishing.
8. Update docs and `.env.example` if new environment variables are needed.

Do not add real API calls during connector registration work. Network behavior belongs behind explicit feature flags and later platform-specific tests.

## Batch 5 Status

Batch 5 now includes the first social account and token metadata tables:

- `social_accounts`
- `platform_tokens`
- `oauth_states`
- `connector_audit_logs`
- `connector_health_checks`

The current token storage strategy is `placeholder_not_stored`, documented in `docs/token-security.md`.

Batch 5 also includes safe OAuth start/callback scaffolding in `scripts/services/oauth_flow.py`.

Dedicated Meta scaffold modules live in `scripts/connectors/meta/`. See `docs/meta-integration.md` for Meta config variables, setup instructions, OAuth behavior, and disabled publishing policy.

The YouTube scaffold lives in `scripts/connectors/youtube.py`. See `docs/youtube-integration.md` for Google env vars, OAuth readiness, mock channel health, and disabled upload policy.

The TikTok scaffold lives in `scripts/connectors/tiktok.py`. See `docs/tiktok-integration.md` for TikTok env vars, OAuth readiness, mock profile health, and disabled posting policy.

The LinkedIn scaffold lives in `scripts/connectors/linkedin.py`. See `docs/linkedin-integration.md` for LinkedIn env vars, OAuth readiness, mock profile health, Product access notes, and disabled publishing policy.

The X scaffold lives in `scripts/connectors/x.py`. See `docs/x-integration.md` for X env vars, OAuth readiness, mock profile health, access/pricing notes, and disabled publishing policy.

Connected Accounts and Social Integration Setup now exist in the static web app. They use mock/demo local state until an API bridge is built.

## Future Work

Batch 6 may add guarded real OAuth readiness and additional platform scaffolds. Real publishing still remains disabled until a later explicit task enables one platform behind safety gates.
