import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.engagement_models import (
    CRITICAL_REPLY_SAFETY_FLAGS,
    ENGAGEMENT_DIRECTIONS,
    ENGAGEMENT_IMPORT_STATUSES,
    ENGAGEMENT_ITEM_TYPES,
    ENGAGEMENT_PRIORITIES,
    ENGAGEMENT_SOURCES,
    ENGAGEMENT_STATUSES,
    ENGAGEMENT_THREAD_STATUSES,
    REPLY_APPROVAL_ACTIONS,
    REPLY_RECOMMENDED_ACTIONS,
    REPLY_SAFETY_SEVERITIES,
    REPLY_SUGGESTION_STATUSES,
)
from scripts.db.init_db import MIGRATIONS_DIR, initialize_database


EXPECTED_ENGAGEMENT_ITEM_COLUMNS = {
    "id",
    "brand_profile_id",
    "platform",
    "social_account_id",
    "generated_post_id",
    "scheduled_post_id",
    "published_post_id",
    "external_item_id",
    "thread_id",
    "item_type",
    "direction",
    "author_name",
    "author_handle",
    "author_profile_url",
    "content",
    "content_redacted",
    "received_at",
    "sentiment",
    "intent",
    "priority",
    "status",
    "requires_response",
    "assigned_to",
    "source",
    "safety_flags_json",
    "raw_data_json",
    "created_at",
    "updated_at",
}


class Batch7EngagementModelsTest(unittest.TestCase):
    def test_engagement_constants_are_available(self):
        self.assertIn("lead_message", ENGAGEMENT_ITEM_TYPES)
        self.assertIn("internal", ENGAGEMENT_DIRECTIONS)
        self.assertIn("urgent", ENGAGEMENT_PRIORITIES)
        self.assertIn("reply_approved", ENGAGEMENT_STATUSES)
        self.assertIn("mock", ENGAGEMENT_SOURCES)
        self.assertIn("needs_attention", ENGAGEMENT_THREAD_STATUSES)
        self.assertIn("approved", REPLY_SUGGESTION_STATUSES)
        self.assertIn("mark_replied_manually", REPLY_APPROVAL_ACTIONS)
        self.assertIn("mark_spam", REPLY_RECOMMENDED_ACTIONS)
        self.assertIn("critical", REPLY_SAFETY_SEVERITIES)
        self.assertIn("unsupported_guarantee", CRITICAL_REPLY_SAFETY_FLAGS)
        self.assertIn("completed", ENGAGEMENT_IMPORT_STATUSES)

    def test_initialize_database_creates_engagement_tables_and_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"

            initialize_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertTrue(
                    {
                        "engagement_items",
                        "engagement_threads",
                        "reply_suggestions",
                        "reply_approvals",
                        "engagement_imports",
                    }.issubset(tables)
                )
                self.assertTrue(
                    EXPECTED_ENGAGEMENT_ITEM_COLUMNS.issubset(
                        self._columns(connection, "engagement_items")
                    )
                )
                self.assertTrue(
                    {
                        "id",
                        "brand_profile_id",
                        "platform",
                        "external_thread_id",
                        "related_post_id",
                        "subject",
                        "status",
                        "last_message_at",
                        "created_at",
                        "updated_at",
                    }.issubset(self._columns(connection, "engagement_threads"))
                )
                self.assertTrue(
                    {
                        "id",
                        "engagement_item_id",
                        "brand_profile_id",
                        "suggested_reply",
                        "tone",
                        "confidence",
                        "safety_flags_json",
                        "reasoning_summary",
                        "provider",
                        "prompt_template_id",
                        "prompt_version",
                        "recommended_action",
                        "needs_human_review",
                        "blocking_flags_json",
                        "safety_review_json",
                        "status",
                        "created_at",
                        "updated_at",
                    }.issubset(self._columns(connection, "reply_suggestions"))
                )

    def test_engagement_migration_preserves_legacy_item(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"

            with closing(sqlite3.connect(db_path)) as connection:
                for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                    if migration_path.name.startswith("008_"):
                        break
                    connection.executescript(migration_path.read_text(encoding="utf-8"))
                    connection.execute(
                        "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)",
                        (migration_path.stem,),
                    )
                connection.execute(
                    """
                    INSERT INTO engagement_items (
                      id, platform, item_type, status, author_label, body,
                      received_at, safety_flags_json, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "legacy-engagement",
                        "facebook",
                        "comment",
                        "needs_reply",
                        "Legacy local label",
                        "Legacy local comment.",
                        "2026-05-30T12:00:00Z",
                        "[]",
                        '{"legacy": true}',
                    ),
                )
                connection.commit()

            initialize_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                row = connection.execute(
                    """
                    SELECT author_name, content, content_redacted, direction,
                      sentiment, intent, priority, status, requires_response,
                      source, raw_data_json
                    FROM engagement_items
                    WHERE id = 'legacy-engagement'
                    """
                ).fetchone()
                self.assertEqual(
                    row[:10],
                    (
                        "Legacy local label",
                        "Legacy local comment.",
                        "Legacy local comment.",
                        "inbound",
                        "unknown",
                        "unknown",
                        "normal",
                        "needs_reply",
                        1,
                        "manual",
                    ),
                )
                self.assertEqual(row[10], '{"legacy": true}')

    @staticmethod
    def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


if __name__ == "__main__":
    unittest.main()
