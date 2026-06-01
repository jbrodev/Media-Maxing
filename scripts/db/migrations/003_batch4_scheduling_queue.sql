PRAGMA foreign_keys = OFF;

CREATE TABLE scheduled_posts_batch4 (
  id TEXT PRIMARY KEY,
  generated_post_id TEXT NOT NULL,
  brand_profile_id TEXT NOT NULL,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  scheduled_for TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'America/New_York',
  status TEXT NOT NULL DEFAULT 'scheduled'
    CHECK (status IN (
      'scheduled',
      'queued',
      'missed',
      'canceled',
      'completed',
      'failed',
      'needs_attention'
    )),
  caption_snapshot TEXT NOT NULL,
  media_asset_ids_json TEXT NOT NULL DEFAULT '[]',
  media_snapshot_json TEXT NOT NULL DEFAULT '[]',
  platform_account_id TEXT,
  publish_queue_item_id TEXT,
  recurrence_rule TEXT,
  is_recurring_template INTEGER NOT NULL DEFAULT 0,
  user_notes TEXT,
  preflight_snapshot_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  canceled_at TEXT,
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE CASCADE,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

INSERT INTO scheduled_posts_batch4 (
  id,
  generated_post_id,
  brand_profile_id,
  platform,
  scheduled_for,
  timezone,
  status,
  caption_snapshot,
  media_asset_ids_json,
  media_snapshot_json,
  preflight_snapshot_json,
  created_at,
  updated_at
)
SELECT
  scheduled_posts.id,
  scheduled_posts.generated_post_id,
  generated_posts.brand_profile_id,
  scheduled_posts.platform,
  scheduled_posts.scheduled_for,
  'America/New_York',
  CASE scheduled_posts.status
    WHEN 'ready' THEN 'queued'
    WHEN 'blocked' THEN 'needs_attention'
    ELSE scheduled_posts.status
  END,
  scheduled_posts.caption_snapshot,
  scheduled_posts.media_snapshot_json,
  scheduled_posts.media_snapshot_json,
  scheduled_posts.preflight_snapshot_json,
  scheduled_posts.created_at,
  scheduled_posts.updated_at
FROM scheduled_posts
JOIN generated_posts ON generated_posts.id = scheduled_posts.generated_post_id;

DROP TABLE scheduled_posts;
ALTER TABLE scheduled_posts_batch4 RENAME TO scheduled_posts;

PRAGMA foreign_keys = ON;

ALTER TABLE generated_posts
  ADD COLUMN last_scheduled_at TEXT;

ALTER TABLE generated_posts
  ADD COLUMN publish_readiness_status TEXT NOT NULL DEFAULT 'not_scheduled'
    CHECK (publish_readiness_status IN (
      'not_scheduled',
      'scheduled',
      'queued',
      'waiting',
      'ready',
      'blocked',
      'mock_published',
      'manually_exported',
      'failed',
      'canceled',
      'skipped'
    ));

CREATE TABLE IF NOT EXISTS publish_queue_items (
  id TEXT PRIMARY KEY,
  scheduled_post_id TEXT NOT NULL,
  generated_post_id TEXT NOT NULL,
  brand_profile_id TEXT NOT NULL,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  queue_status TEXT NOT NULL DEFAULT 'waiting'
    CHECK (queue_status IN (
      'waiting',
      'ready',
      'blocked',
      'processing',
      'mock_published',
      'manually_exported',
      'failed',
      'canceled',
      'skipped'
    )),
  due_at TEXT NOT NULL,
  timezone TEXT NOT NULL DEFAULT 'America/New_York',
  priority INTEGER NOT NULL DEFAULT 100,
  preflight_status TEXT NOT NULL DEFAULT 'not_checked'
    CHECK (preflight_status IN ('not_checked', 'passed', 'warnings', 'errors', 'blocked')),
  preflight_errors_json TEXT NOT NULL DEFAULT '[]',
  preflight_warnings_json TEXT NOT NULL DEFAULT '[]',
  mock_publish_enabled INTEGER NOT NULL DEFAULT 0,
  manual_export_required INTEGER NOT NULL DEFAULT 1,
  last_checked_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id) ON DELETE CASCADE,
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE CASCADE,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS publish_attempts (
  id TEXT PRIMARY KEY,
  publish_queue_item_id TEXT NOT NULL,
  scheduled_post_id TEXT NOT NULL,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  attempt_type TEXT NOT NULL
    CHECK (attempt_type IN (
      'preflight',
      'mock_publish',
      'manual_export',
      'future_real_publish'
    )),
  attempt_status TEXT NOT NULL
    CHECK (attempt_status IN ('started', 'succeeded', 'failed', 'skipped', 'blocked')),
  started_at TEXT NOT NULL,
  finished_at TEXT,
  error_code TEXT,
  error_message TEXT,
  provider_response_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (publish_queue_item_id) REFERENCES publish_queue_items(id) ON DELETE CASCADE,
  FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_brand_profile_id
  ON scheduled_posts(brand_profile_id);

CREATE INDEX IF NOT EXISTS idx_scheduled_posts_publish_queue_item_id
  ON scheduled_posts(publish_queue_item_id);

CREATE INDEX IF NOT EXISTS idx_publish_queue_items_status
  ON publish_queue_items(queue_status);

CREATE INDEX IF NOT EXISTS idx_publish_queue_items_due_at
  ON publish_queue_items(due_at);

CREATE INDEX IF NOT EXISTS idx_publish_queue_items_scheduled_post_id
  ON publish_queue_items(scheduled_post_id);

CREATE INDEX IF NOT EXISTS idx_publish_attempts_queue_item_id
  ON publish_attempts(publish_queue_item_id);
