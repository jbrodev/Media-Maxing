PRAGMA foreign_keys = OFF;

DROP INDEX IF EXISTS idx_analytics_snapshots_published_post_id;

ALTER TABLE analytics_snapshots RENAME TO analytics_snapshots_batch6;

CREATE TABLE analytics_snapshots (
  id TEXT PRIMARY KEY,
  published_post_id TEXT,
  scheduled_post_id TEXT,
  generated_post_id TEXT,
  brand_profile_id TEXT,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  source TEXT NOT NULL
    CHECK (source IN ('manual', 'mock', 'platform_api', 'imported_csv', 'estimated')),
  snapshot_date TEXT NOT NULL,
  impressions INTEGER NOT NULL DEFAULT 0,
  reach INTEGER NOT NULL DEFAULT 0,
  views INTEGER NOT NULL DEFAULT 0,
  likes INTEGER NOT NULL DEFAULT 0,
  comments INTEGER NOT NULL DEFAULT 0,
  shares INTEGER NOT NULL DEFAULT 0,
  saves INTEGER NOT NULL DEFAULT 0,
  clicks INTEGER NOT NULL DEFAULT 0,
  profile_visits INTEGER NOT NULL DEFAULT 0,
  follows INTEGER NOT NULL DEFAULT 0,
  leads INTEGER NOT NULL DEFAULT 0,
  messages INTEGER NOT NULL DEFAULT 0,
  calls INTEGER NOT NULL DEFAULT 0,
  website_clicks INTEGER NOT NULL DEFAULT 0,
  engagement_rate REAL NOT NULL DEFAULT 0,
  click_through_rate REAL NOT NULL DEFAULT 0,
  lead_rate REAL NOT NULL DEFAULT 0,
  raw_metrics_json TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (published_post_id) REFERENCES published_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE SET NULL
);

INSERT INTO analytics_snapshots (
  id,
  published_post_id,
  scheduled_post_id,
  generated_post_id,
  brand_profile_id,
  platform,
  source,
  snapshot_date,
  impressions,
  reach,
  views,
  likes,
  comments,
  shares,
  saves,
  clicks,
  leads,
  engagement_rate,
  click_through_rate,
  lead_rate,
  raw_metrics_json,
  created_at,
  updated_at
)
SELECT
  analytics_snapshots_batch6.id,
  analytics_snapshots_batch6.published_post_id,
  published_posts.scheduled_post_id,
  published_posts.generated_post_id,
  generated_posts.brand_profile_id,
  analytics_snapshots_batch6.platform,
  analytics_snapshots_batch6.source,
  analytics_snapshots_batch6.captured_at,
  COALESCE(analytics_snapshots_batch6.impressions, 0),
  COALESCE(analytics_snapshots_batch6.reach, 0),
  COALESCE(analytics_snapshots_batch6.views, 0),
  COALESCE(analytics_snapshots_batch6.likes, 0),
  COALESCE(analytics_snapshots_batch6.comments, 0),
  COALESCE(analytics_snapshots_batch6.shares, 0),
  COALESCE(analytics_snapshots_batch6.saves, 0),
  COALESCE(analytics_snapshots_batch6.clicks, 0),
  COALESCE(analytics_snapshots_batch6.leads, 0),
  CAST(
    COALESCE(analytics_snapshots_batch6.likes, 0)
    + COALESCE(analytics_snapshots_batch6.comments, 0)
    + COALESCE(analytics_snapshots_batch6.shares, 0)
    + COALESCE(analytics_snapshots_batch6.saves, 0)
    AS REAL
  ) / MAX(
    COALESCE(analytics_snapshots_batch6.reach, 0),
    COALESCE(analytics_snapshots_batch6.impressions, 0),
    COALESCE(analytics_snapshots_batch6.views, 0),
    1
  ),
  CAST(COALESCE(analytics_snapshots_batch6.clicks, 0) AS REAL) / MAX(
    COALESCE(analytics_snapshots_batch6.impressions, 0),
    COALESCE(analytics_snapshots_batch6.views, 0),
    COALESCE(analytics_snapshots_batch6.reach, 0),
    1
  ),
  CAST(COALESCE(analytics_snapshots_batch6.leads, 0) AS REAL) / MAX(
    COALESCE(analytics_snapshots_batch6.clicks, 0),
    COALESCE(analytics_snapshots_batch6.impressions, 0),
    COALESCE(analytics_snapshots_batch6.views, 0),
    1
  ),
  analytics_snapshots_batch6.metrics_json,
  analytics_snapshots_batch6.created_at,
  analytics_snapshots_batch6.created_at
FROM analytics_snapshots_batch6
LEFT JOIN published_posts
  ON published_posts.id = analytics_snapshots_batch6.published_post_id
LEFT JOIN generated_posts
  ON generated_posts.id = published_posts.generated_post_id;

DROP TABLE analytics_snapshots_batch6;

ALTER TABLE ai_memory
  ADD COLUMN title TEXT;

ALTER TABLE ai_memory
  ADD COLUMN content TEXT;

ALTER TABLE ai_memory
  ADD COLUMN source TEXT NOT NULL DEFAULT 'manual';

UPDATE ai_memory
SET
  title = COALESCE(title, summary),
  content = COALESCE(content, summary);

CREATE TABLE IF NOT EXISTS post_performance_metrics (
  id TEXT PRIMARY KEY,
  generated_post_id TEXT,
  scheduled_post_id TEXT,
  published_post_id TEXT,
  brand_profile_id TEXT NOT NULL,
  platform TEXT NOT NULL
    CHECK (platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  content_goal TEXT,
  content_angle TEXT,
  media_asset_ids_json TEXT NOT NULL DEFAULT '[]',
  posted_at TEXT,
  first_snapshot_at TEXT,
  latest_snapshot_at TEXT,
  total_impressions INTEGER NOT NULL DEFAULT 0,
  total_reach INTEGER NOT NULL DEFAULT 0,
  total_views INTEGER NOT NULL DEFAULT 0,
  total_likes INTEGER NOT NULL DEFAULT 0,
  total_comments INTEGER NOT NULL DEFAULT 0,
  total_shares INTEGER NOT NULL DEFAULT 0,
  total_saves INTEGER NOT NULL DEFAULT 0,
  total_clicks INTEGER NOT NULL DEFAULT 0,
  total_leads INTEGER NOT NULL DEFAULT 0,
  engagement_rate REAL NOT NULL DEFAULT 0,
  lead_rate REAL NOT NULL DEFAULT 0,
  performance_score REAL NOT NULL DEFAULT 0,
  trend TEXT NOT NULL DEFAULT 'unknown'
    CHECK (trend IN ('improving', 'flat', 'declining', 'unknown')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (generated_post_id) REFERENCES generated_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (scheduled_post_id) REFERENCES scheduled_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (published_post_id) REFERENCES published_posts(id) ON DELETE SET NULL,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analytics_imports (
  id TEXT PRIMARY KEY,
  source TEXT NOT NULL
    CHECK (source IN ('manual', 'mock', 'platform_api', 'imported_csv', 'estimated')),
  platform TEXT
    CHECK (platform IS NULL OR platform IN ('facebook', 'instagram', 'threads', 'youtube', 'tiktok', 'linkedin', 'x')),
  import_type TEXT NOT NULL
    CHECK (import_type IN ('manual_entry', 'mock_sync', 'csv_upload', 'platform_sync')),
  status TEXT NOT NULL
    CHECK (status IN ('pending', 'completed', 'partial', 'failed')),
  records_imported INTEGER NOT NULL DEFAULT 0,
  records_skipped INTEGER NOT NULL DEFAULT 0,
  error_message TEXT,
  imported_at TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_insights (
  id TEXT PRIMARY KEY,
  brand_profile_id TEXT NOT NULL,
  insight_type TEXT NOT NULL
    CHECK (insight_type IN (
      'best_content_type',
      'best_platform',
      'best_hook',
      'best_time',
      'weak_content_type',
      'audience_signal',
      'lead_signal',
      'hashtag_signal',
      'media_signal',
      'safety_signal',
      'recommendation'
    )),
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  confidence TEXT NOT NULL DEFAULT 'low'
    CHECK (confidence IN ('low', 'medium', 'high')),
  related_post_ids_json TEXT NOT NULL DEFAULT '[]',
  related_media_asset_ids_json TEXT NOT NULL DEFAULT '[]',
  recommended_action TEXT,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'dismissed', 'applied', 'archived')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weekly_reports (
  id TEXT PRIMARY KEY,
  brand_profile_id TEXT NOT NULL,
  week_start_date TEXT NOT NULL,
  week_end_date TEXT NOT NULL,
  summary TEXT NOT NULL,
  wins_json TEXT NOT NULL DEFAULT '[]',
  concerns_json TEXT NOT NULL DEFAULT '[]',
  recommendations_json TEXT NOT NULL DEFAULT '[]',
  top_posts_json TEXT NOT NULL DEFAULT '[]',
  platform_breakdown_json TEXT NOT NULL DEFAULT '{}',
  metric_totals_json TEXT NOT NULL DEFAULT '{}',
  generated_by TEXT NOT NULL
    CHECK (generated_by IN ('system', 'ai_mock', 'ai_provider', 'manual')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (brand_profile_id) REFERENCES brand_profiles(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_published_post_id
  ON analytics_snapshots(published_post_id);

CREATE INDEX IF NOT EXISTS idx_analytics_snapshots_brand_platform_date
  ON analytics_snapshots(brand_profile_id, platform, snapshot_date);

CREATE INDEX IF NOT EXISTS idx_post_performance_metrics_brand_platform
  ON post_performance_metrics(brand_profile_id, platform);

CREATE INDEX IF NOT EXISTS idx_analytics_imports_source_imported_at
  ON analytics_imports(source, imported_at);

CREATE INDEX IF NOT EXISTS idx_content_insights_brand_status
  ON content_insights(brand_profile_id, status);

CREATE INDEX IF NOT EXISTS idx_weekly_reports_brand_week
  ON weekly_reports(brand_profile_id, week_start_date);

PRAGMA foreign_keys = ON;
