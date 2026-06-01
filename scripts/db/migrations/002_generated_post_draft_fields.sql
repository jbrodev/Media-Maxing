PRAGMA foreign_keys = ON;

ALTER TABLE generated_posts ADD COLUMN headline TEXT;
ALTER TABLE generated_posts ADD COLUMN hook TEXT;
ALTER TABLE generated_posts ADD COLUMN short_caption TEXT;
ALTER TABLE generated_posts ADD COLUMN long_caption TEXT;
ALTER TABLE generated_posts ADD COLUMN call_to_action TEXT;
ALTER TABLE generated_posts ADD COLUMN content_goal TEXT;
ALTER TABLE generated_posts ADD COLUMN content_angle TEXT;
ALTER TABLE generated_posts ADD COLUMN target_audience TEXT;
ALTER TABLE generated_posts ADD COLUMN campaign_name TEXT;
ALTER TABLE generated_posts ADD COLUMN offer_context TEXT;
ALTER TABLE generated_posts ADD COLUMN user_instructions TEXT;
ALTER TABLE generated_posts ADD COLUMN suggested_post_time TEXT;
ALTER TABLE generated_posts ADD COLUMN alt_text TEXT;
ALTER TABLE generated_posts ADD COLUMN notes TEXT;
ALTER TABLE generated_posts ADD COLUMN score_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE generated_posts ADD COLUMN prompt_template_id TEXT;
ALTER TABLE generated_posts ADD COLUMN prompt_version TEXT;
ALTER TABLE generated_posts ADD COLUMN generation_timestamp TEXT;

CREATE INDEX IF NOT EXISTS idx_generated_posts_prompt_template_id
  ON generated_posts(prompt_template_id);
