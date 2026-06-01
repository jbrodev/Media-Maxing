ALTER TABLE reply_suggestions
  ADD COLUMN recommended_action TEXT NOT NULL DEFAULT 'reply'
    CHECK (recommended_action IN (
      'reply', 'ask_for_more_info', 'invite_to_call', 'invite_to_message',
      'escalate', 'ignore', 'mark_spam'
    ));

ALTER TABLE reply_suggestions
  ADD COLUMN needs_human_review INTEGER NOT NULL DEFAULT 1
    CHECK (needs_human_review IN (0, 1));

ALTER TABLE reply_suggestions
  ADD COLUMN blocking_flags_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE reply_suggestions
  ADD COLUMN safety_review_json TEXT NOT NULL DEFAULT '{}';
