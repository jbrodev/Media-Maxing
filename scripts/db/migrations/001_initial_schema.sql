PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version TEXT PRIMARY KEY,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  email TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS brand_profiles (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  business_name TEXT NOT NULL,
  description TEXT,
  voice TEXT,
  services_json TEXT NOT NULL DEFAULT '[]',
  locations_json TEXT NOT NULL DEFAULT '[]',
  target_audience TEXT,
  supported_claims_json TEXT NOT NULL DEFAULT '[]',
  blocked_phrases_json TEXT NOT NULL DEFAULT '[]',
  preferences_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS app_settings (
  id TEXT PRIMARY KEY,
  user_id TEXT,
  automation_level TEXT NOT NULL DEFAULT 'approval_queue'
    CHECK (automation_level IN (
      'manual_assist',
      'approval_queue',
      'semi_auto_scheduling',
      'safe_auto_posting',
      'autonomous_content_engine'
    )),
  require_approval_before_publishing INTEGER NOT NULL DEFAULT 1,
  require_approval_before_replying INTEGER NOT NULL DEFAULT 1,
  emergency_pause_enabled INTEGER NOT NULL DEFAULT 0,
  kill_switch_enabled INTEGER NOT NULL DEFAULT 0,
  integrations_mode TEXT NOT NULL DEFAULT 'mock'
    CHECK (integrations_mode IN ('mock', 'disabled', 'testing', 'real')),
  enable_real_network_calls INTEGER NOT NULL DEFAULT 0,
  enable_real_oauth INTEGER NOT NULL DEFAULT 0,
  enable_real_publishing INTEGER NOT NULL DEFAULT 0,
  token_storage_mode TEXT NOT NULL DEFAULT 'placeholder_not_stored'
    CHECK (token_storage_mode IN (
      'placeholder_not_stored',
      'keychain',
      'encrypted_local',
      'development_insecure'
    )),
  settings_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS media_assets (
  id TEXT PRIMARY KEY,
  media_type TEXT NOT NULL DEFAULT 'unknown'
    CHECK (media_type IN ('image', 'video', 'audio', 'document', 'unknown')),
  original_path TEXT NOT NULL,
  processed_path TEXT,
  thumbnail_path TEXT,
  file_name TEXT NOT NULL,
  mime_type TEXT,
  file_size_bytes INTEGER,
  tags_json TEXT NOT NULL DEFAULT '[]',
  job_context_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_ideas (
  id TEXT PRIMARY KEY,
  brand_profile_id TEXT,
  goal TEXT NOT NULL,
  angle TEXT NOT NULL,
  target_platforms_json TEXT NOT NULL DEFAULT '[]',
  media_asset_ids_json TEXT NOT NULL DEFAULT '[]',
  notes TEXT,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'used', 'archived', 'rejected')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS generated_posts (
  id TEXT PRIMARY KEY,
  content_idea_id TEXT,
  brand_profile_id TEXT NOT NULL,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  caption TEXT NOT NULL,
  hashtags_json TEXT NOT NULL DEFAULT '[]',
  media_asset_ids_json TEXT NOT NULL DEFAULT '[]',
  approval_status TEXT NOT NULL DEFAULT 'needs_review'
    CHECK (approval_status IN (
      'draft',
      'needs_review',
      'approved',
      'rejected',
      'revision_requested',
      'archived'
    )),
  safety_flags_json TEXT NOT NULL DEFAULT '[]',
  generation_provider TEXT NOT NULL DEFAULT 'mock'
    CHECK (generation_provider IN ('mock', 'openai', 'anthropic', 'local')),
  prompt_metadata_json TEXT NOT NULL DEFAULT '{}',
  provider_metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (content_idea_id) REFERENCES content_ideas(id) ON DELETE SET NULL,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scheduled_posts (
  id TEXT PRIMARY KEY,
  generated_post_id TEXT NOT NULL,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  scheduled_for TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'scheduled'
    CHECK (status IN ('scheduled', 'ready', 'blocked', 'canceled', 'completed')),
  caption_snapshot TEXT NOT NULL,
  media_snapshot_json TEXT NOT NULL DEFAULT '[]',
  preflight_snapshot_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS published_posts (
  id TEXT PRIMARY KEY,
  scheduled_post_id TEXT,
  generated_post_id TEXT,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  publish_mode TEXT NOT NULL
    CHECK (publish_mode IN ('mock', 'manual_export', 'platform_api')),
  external_post_id TEXT,
  permalink TEXT,
  published_at TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS engagement_items (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  published_post_id TEXT,
  item_type TEXT NOT NULL DEFAULT 'unknown'
    CHECK (item_type IN (
      'comment',
      'reply',
      'mention',
      'direct_message',
      'review',
      'lead_message',
      'system_note',
      'unknown'
    )),
  status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN (
      'new',
      'needs_reply',
      'reply_suggested',
      'reply_approved',
      'replied_manually',
      'ignored',
      'archived',
      'spam',
      'escalated'
    )),
  author_label TEXT,
  body TEXT NOT NULL,
  received_at TEXT NOT NULL,
  safety_flags_json TEXT NOT NULL DEFAULT '[]',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (published_post_id) REFERENCES published_posts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS analytics_snapshots (
  id TEXT PRIMARY KEY,
  published_post_id TEXT,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  source TEXT NOT NULL
    CHECK (source IN ('manual', 'mock', 'platform_api', 'imported_csv', 'estimated')),
  captured_at TEXT NOT NULL,
  impressions INTEGER,
  reach INTEGER,
  views INTEGER,
  likes INTEGER,
  comments INTEGER,
  shares INTEGER,
  saves INTEGER,
  clicks INTEGER,
  leads INTEGER,
  metrics_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (published_post_id) REFERENCES published_posts(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS approval_logs (
  id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  actor_label TEXT NOT NULL DEFAULT 'local_user',
  notes TEXT,
  changed_fields_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_memory (
  id TEXT PRIMARY KEY,
  brand_profile_id TEXT,
  memory_type TEXT NOT NULL
    CHECK (memory_type IN (
      'brand_rule',
      'content_preference',
      'audience_learning',
      'platform_learning',
      'performance_learning',
      'safety_learning',
      'user_preference',
      'rejected_strategy',
      'approved_strategy'
    )),
  summary TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'low'
    CHECK (confidence IN ('low', 'medium', 'high')),
  evidence_json TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'archived', 'superseded')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_profiles_user_id ON brand_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_posts_brand_profile_id ON generated_posts(brand_profile_id);
CREATE INDEX IF NOT EXISTS idx_generated_posts_approval_status ON generated_posts(approval_status);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_scheduled_for ON scheduled_posts(scheduled_for);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_status ON scheduled_posts(status);
CREATE INDEX IF NOT EXISTS idx_engagement_items_status ON engagement_items(status);
CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_published_post_id ON analytics_snapshots(published_post_id);
CREATE INDEX IF NOT EXISTS idx_approval_logs_entity ON approval_logs(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_ai_memory_brand_profile_id ON ai_memory(brand_profile_id);

INSERT OR IGNORE INTO app_settings (
  id,
  automation_level,
  require_approval_before_publishing,
  require_approval_before_replying,
  emergency_pause_enabled,
  kill_switch_enabled,
  integrations_mode,
  enable_real_network_calls,
  enable_real_oauth,
  enable_real_publishing,
  token_storage_mode,
  settings_json
) VALUES (
  'default',
  'approval_queue',
  1,
  1,
  0,
  0,
  'mock',
  0,
  0,
  0,
  'placeholder_not_stored',
  '{}'
);
