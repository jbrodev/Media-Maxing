PRAGMA foreign_keys = ON;

ALTER TABLE scheduled_posts
  ADD COLUMN schedule_metadata_json TEXT NOT NULL DEFAULT '{}';
