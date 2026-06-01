PRAGMA foreign_keys = OFF;

DROP INDEX IF EXISTS idx_engagement_items_status;

ALTER TABLE engagement_items RENAME TO engagement_items_legacy;

CREATE TABLE engagement_threads (
  id TEXT PRIMARY KEY,
  brand_profile_id TEXT NOT NULL,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  external_thread_id TEXT,
  related_post_id TEXT,
  subject TEXT,
  status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'needs_attention', 'resolved', 'archived', 'spam')),
  last_message_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE,
  FOREIGN KEY (related_post_id) REFERENCES published_posts(id) ON DELETE SET NULL
);

CREATE TABLE engagement_items (
  id TEXT PRIMARY KEY,
  brand_profile_id TEXT,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  social_account_id TEXT,
  generated_post_id TEXT,
  scheduled_post_id TEXT,
  published_post_id TEXT,
  external_item_id TEXT,
  thread_id TEXT,
  item_type TEXT NOT NULL DEFAULT 'unknown'
    CHECK (item_type IN (
      'comment', 'reply', 'mention', 'direct_message', 'review',
      'lead_message', 'system_note', 'unknown'
    )),
  direction TEXT NOT NULL DEFAULT 'inbound'
    CHECK (direction IN ('inbound', 'outbound', 'internal')),
  author_name TEXT,
  author_handle TEXT,
  author_profile_url TEXT,
  content TEXT NOT NULL,
  content_redacted TEXT NOT NULL,
  received_at TEXT NOT NULL,
  sentiment TEXT NOT NULL DEFAULT 'unknown'
    CHECK (sentiment IN ('positive', 'neutral', 'negative', 'mixed', 'unknown')),
  intent TEXT NOT NULL DEFAULT 'unknown'
    CHECK (intent IN (
      'praise', 'question', 'price_request', 'booking_request', 'complaint',
      'spam', 'partnership', 'general', 'urgent', 'unknown'
    )),
  priority TEXT NOT NULL DEFAULT 'normal'
    CHECK (priority IN ('low', 'normal', 'high', 'urgent')),
  status TEXT NOT NULL DEFAULT 'new'
    CHECK (status IN (
      'new', 'needs_reply', 'reply_suggested', 'reply_approved',
      'replied_manually', 'ignored', 'archived', 'spam', 'escalated'
    )),
  requires_response INTEGER NOT NULL DEFAULT 0
    CHECK (requires_response IN (0, 1)),
  assigned_to TEXT,
  source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('mock', 'manual', 'platform_api', 'imported_csv')),
  safety_flags_json TEXT NOT NULL DEFAULT '[]',
  raw_data_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE SET NULL,
  FOREIGN KEY (social_account_id) REFERENCES social_accounts(id) ON DELETE SET NULL,
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (published_post_id) REFERENCES published_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (thread_id) REFERENCES engagement_threads(id) ON DELETE SET NULL
);

INSERT INTO engagement_items (
  id,
  platform,
  published_post_id,
  item_type,
  direction,
  author_name,
  content,
  content_redacted,
  received_at,
  status,
  requires_response,
  source,
  safety_flags_json,
  raw_data_json,
  created_at,
  updated_at
)
SELECT
  id,
  platform,
  published_post_id,
  item_type,
  CASE WHEN item_type = 'system_note' THEN 'internal' ELSE 'inbound' END,
  author_label,
  body,
  body,
  received_at,
  status,
  CASE
    WHEN status IN ('needs_reply', 'reply_suggested', 'reply_approved', 'escalated')
      THEN 1
    ELSE 0
  END,
  'manual',
  safety_flags_json,
  metadata_json,
  created_at,
  updated_at
FROM engagement_items_legacy;

DROP TABLE engagement_items_legacy;

CREATE TABLE reply_suggestions (
  id TEXT PRIMARY KEY,
  engagement_item_id TEXT NOT NULL,
  brand_profile_id TEXT NOT NULL,
  suggested_reply TEXT NOT NULL,
  tone TEXT,
  confidence TEXT NOT NULL DEFAULT 'low'
    CHECK (confidence IN ('low', 'medium', 'high')),
  safety_flags_json TEXT NOT NULL DEFAULT '[]',
  reasoning_summary TEXT,
  provider TEXT NOT NULL DEFAULT 'mock',
  prompt_template_id TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'generated'
    CHECK (status IN ('generated', 'edited', 'approved', 'rejected', 'archived')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (engagement_item_id) REFERENCES engagement_items(id) ON DELETE CASCADE,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE reply_approvals (
  id TEXT PRIMARY KEY,
  reply_suggestion_id TEXT,
  engagement_item_id TEXT NOT NULL,
  action TEXT NOT NULL
    CHECK (action IN (
      'suggest', 'edit', 'approve', 'reject', 'mark_replied_manually',
      'archive', 'escalate', 'mark_spam'
    )),
  previous_status TEXT,
  new_status TEXT NOT NULL,
  reason TEXT,
  actor_type TEXT NOT NULL
    CHECK (actor_type IN ('user', 'system', 'ai', 'test')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (reply_suggestion_id) REFERENCES reply_suggestions(id) ON DELETE SET NULL,
  FOREIGN KEY (engagement_item_id) REFERENCES engagement_items(id) ON DELETE CASCADE
);

CREATE TABLE engagement_imports (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL
    CHECK (source IN ('mock', 'manual', 'platform_api', 'imported_csv')),
  platform TEXT
    CHECK (platform IS NULL OR platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  import_type TEXT NOT NULL
    CHECK (import_type IN ('mock_ingestion', 'manual_entry', 'csv_upload', 'platform_sync')),
  status TEXT NOT NULL
    CHECK (status IN ('pending', 'completed', 'partial', 'failed')),
  records_imported INTEGER NOT NULL DEFAULT 0,
  records_skipped INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  imported_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_engagement_threads_brand_status
  ON engagement_threads(brand_profile_id, status);

CREATE INDEX IF NOT EXISTS idx_engagement_items_status
  ON engagement_items(status);

CREATE INDEX IF NOT EXISTS idx_engagement_items_brand_platform_status
  ON engagement_items(brand_profile_id, platform, status);

CREATE INDEX IF NOT EXISTS idx_engagement_items_thread
  ON engagement_items(thread_id);

CREATE INDEX IF NOT EXISTS idx_reply_suggestions_engagement_item
  ON reply_suggestions(engagement_item_id);

CREATE INDEX IF NOT EXISTS idx_reply_approvals_engagement_item
  ON reply_approvals(engagement_item_id);

CREATE INDEX IF NOT EXISTS idx_engagement_imports_source_imported_at
  ON engagement_imports(source, imported_at);

PRAGMA foreign_keys = ON;
