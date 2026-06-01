CREATE TABLE IF NOT EXISTS social_accounts (
  id TEXT PRIMARY KEY,
  brand_profile_id TEXT NULL REFERENCES brand_profiles(id) ON DELETE SET NULL,
  platform TEXT NOT NULL CHECK (
    platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')
  ),
  platform_account_id TEXT NULL,
  display_name TEXT NOT NULL,
  username TEXT NULL,
  profile_url TEXT NULL,
  profile_image_url TEXT NULL,
  account_type TEXT NOT NULL DEFAULT 'unknown' CHECK (
    account_type IN (
      'personal', 'business', 'creator', 'page', 'channel', 'organization', 'unknown'
    )
  ),
  connection_status TEXT NOT NULL DEFAULT 'not_connected' CHECK (
    connection_status IN (
      'not_connected', 'connecting', 'connected', 'limited', 'expired',
      'revoked', 'disconnected', 'error', 'requires_reauth'
    )
  ),
  capabilities_json TEXT NOT NULL DEFAULT '{}',
  granted_scopes_json TEXT NOT NULL DEFAULT '[]',
  missing_scopes_json TEXT NOT NULL DEFAULT '[]',
  requires_reauth INTEGER NOT NULL DEFAULT 0 CHECK (requires_reauth IN (0, 1)),
  last_connected_at TEXT NULL,
  last_validated_at TEXT NULL,
  disconnected_at TEXT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(platform, platform_account_id)
);

CREATE INDEX IF NOT EXISTS idx_social_accounts_platform
  ON social_accounts(platform);

CREATE INDEX IF NOT EXISTS idx_social_accounts_brand_profile
  ON social_accounts(brand_profile_id);

CREATE INDEX IF NOT EXISTS idx_social_accounts_connection_status
  ON social_accounts(connection_status);

CREATE TABLE IF NOT EXISTS platform_tokens (
  id TEXT PRIMARY KEY,
  social_account_id TEXT NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
  platform TEXT NOT NULL CHECK (
    platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')
  ),
  token_type TEXT NOT NULL DEFAULT 'unknown' CHECK (
    token_type IN (
      'oauth_access', 'oauth_refresh', 'long_lived_access', 'page_access',
      'app_token_placeholder', 'unknown'
    )
  ),
  encrypted_access_token TEXT NULL,
  encrypted_refresh_token TEXT NULL,
  access_token_expires_at TEXT NULL,
  refresh_token_expires_at TEXT NULL,
  scope TEXT NOT NULL DEFAULT '',
  token_version INTEGER NOT NULL DEFAULT 1 CHECK (token_version >= 1),
  encryption_status TEXT NOT NULL DEFAULT 'placeholder_not_stored' CHECK (
    encryption_status IN (
      'encrypted', 'keychain', 'placeholder_not_stored',
      'insecure_dev_only', 'missing'
    )
  ),
  last_refresh_at TEXT NULL,
  revoked_at TEXT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    encryption_status NOT IN ('placeholder_not_stored', 'missing')
    OR (encrypted_access_token IS NULL AND encrypted_refresh_token IS NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_platform_tokens_social_account
  ON platform_tokens(social_account_id);

CREATE INDEX IF NOT EXISTS idx_platform_tokens_platform
  ON platform_tokens(platform);

CREATE TABLE IF NOT EXISTS oauth_states (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL CHECK (
    platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')
  ),
  state_hash TEXT NOT NULL UNIQUE,
  redirect_uri TEXT NOT NULL,
  code_verifier_hash TEXT NULL,
  requested_scopes_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'created' CHECK (
    status IN ('created', 'consumed', 'expired', 'failed')
  ),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expires_at TEXT NOT NULL,
  consumed_at TEXT NULL,
  error_message TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_oauth_states_platform
  ON oauth_states(platform);

CREATE INDEX IF NOT EXISTS idx_oauth_states_status_expires
  ON oauth_states(status, expires_at);

CREATE TABLE IF NOT EXISTS connector_audit_logs (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL CHECK (
    platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')
  ),
  social_account_id TEXT NULL REFERENCES social_accounts(id) ON DELETE SET NULL,
  action TEXT NOT NULL CHECK (
    action IN (
      'oauth_start', 'oauth_callback', 'token_exchange', 'token_refresh',
      'connection_validate', 'disconnect', 'reauth_required', 'error'
    )
  ),
  status TEXT NOT NULL,
  message TEXT NOT NULL,
  safe_metadata_json TEXT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_connector_audit_logs_platform
  ON connector_audit_logs(platform);

CREATE INDEX IF NOT EXISTS idx_connector_audit_logs_social_account
  ON connector_audit_logs(social_account_id);

CREATE TABLE IF NOT EXISTS connector_health_checks (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL CHECK (
    platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')
  ),
  social_account_id TEXT NULL REFERENCES social_accounts(id) ON DELETE SET NULL,
  health_status TEXT NOT NULL,
  feature_status TEXT NOT NULL,
  message TEXT NOT NULL,
  safe_metadata_json TEXT NULL,
  checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_connector_health_checks_platform
  ON connector_health_checks(platform);

CREATE INDEX IF NOT EXISTS idx_connector_health_checks_social_account
  ON connector_health_checks(social_account_id);
