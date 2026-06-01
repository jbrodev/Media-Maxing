import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.init_db import initialize_database
from scripts.db.scheduling_models import (
    PREFLIGHT_STATUSES,
    PUBLISH_ATTEMPT_STATUSES,
    PUBLISH_ATTEMPT_TYPES,
    PUBLISH_QUEUE_STATUSES,
    SCHEDULED_POST_STATUSES,
)


EXPECTED_TABLES = {
    "users",
    "brand_profiles",
    "app_settings",
    "media_assets",
    "content_ideas",
    "generated_posts",
    "scheduled_posts",
    "publish_queue_items",
    "publish_attempts",
    "social_accounts",
    "platform_tokens",
    "oauth_states",
    "connector_audit_logs",
    "connector_health_checks",
    "local_job_locks",
    "published_posts",
    "engagement_items",
    "engagement_threads",
    "reply_suggestions",
    "reply_approvals",
    "engagement_imports",
    "analytics_snapshots",
    "post_performance_metrics",
    "analytics_imports",
    "content_insights",
    "weekly_reports",
    "approval_logs",
    "ai_memory",
}

EXPECTED_SCHEDULED_POST_COLUMNS = {
    "id",
    "generated_post_id",
    "brand_profile_id",
    "platform",
    "scheduled_for",
    "timezone",
    "status",
    "caption_snapshot",
    "media_asset_ids_json",
    "platform_account_id",
    "publish_queue_item_id",
    "recurrence_rule",
    "is_recurring_template",
    "user_notes",
    "created_at",
    "updated_at",
    "canceled_at",
}

EXPECTED_PUBLISH_QUEUE_COLUMNS = {
    "id",
    "scheduled_post_id",
    "generated_post_id",
    "brand_profile_id",
    "platform",
    "queue_status",
    "due_at",
    "timezone",
    "priority",
    "preflight_status",
    "preflight_errors_json",
    "preflight_warnings_json",
    "mock_publish_enabled",
    "manual_export_required",
    "last_checked_at",
    "created_at",
    "updated_at",
}

EXPECTED_PUBLISH_ATTEMPT_COLUMNS = {
    "id",
    "publish_queue_item_id",
    "scheduled_post_id",
    "platform",
    "attempt_type",
    "attempt_status",
    "started_at",
    "finished_at",
    "error_code",
    "error_message",
    "provider_response_json",
    "created_at",
}


class DatabaseInitializationTest(unittest.TestCase):
    def test_batch4_status_constants_are_available(self):
        self.assertIn("needs_attention", SCHEDULED_POST_STATUSES)
        self.assertIn("waiting", PUBLISH_QUEUE_STATUSES)
        self.assertIn("manual_export", PUBLISH_ATTEMPT_TYPES)
        self.assertIn("blocked", PUBLISH_ATTEMPT_STATUSES)
        self.assertIn("errors", PREFLIGHT_STATUSES)

    def test_initialize_database_creates_core_tables_and_default_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"

            initialize_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                table_rows = connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
                tables = {row[0] for row in table_rows}

                self.assertTrue(EXPECTED_TABLES.issubset(tables))

                settings = connection.execute(
                    """
                    SELECT
                      automation_level,
                      require_approval_before_publishing,
                      require_approval_before_replying,
                      emergency_pause_enabled,
                      integrations_mode,
                      enable_real_publishing,
                      token_storage_mode
                    FROM app_settings
                    """
                ).fetchone()

                self.assertEqual(
                    settings,
                    (
                        "approval_queue",
                        1,
                        1,
                        0,
                        "mock",
                        0,
                        "placeholder_not_stored",
                    ),
                )

                self.assertTrue(
                    EXPECTED_SCHEDULED_POST_COLUMNS.issubset(
                        self._columns(connection, "scheduled_posts")
                    )
                )
                self.assertTrue(
                    EXPECTED_PUBLISH_QUEUE_COLUMNS.issubset(
                        self._columns(connection, "publish_queue_items")
                    )
                )
                self.assertTrue(
                    EXPECTED_PUBLISH_ATTEMPT_COLUMNS.issubset(
                        self._columns(connection, "publish_attempts")
                    )
                )

    def test_batch4_status_constraints_allow_local_workflow_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"

            initialize_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute(
                    """
                    INSERT INTO brand_profiles (
                      id, business_name, services_json, locations_json,
                      supported_claims_json, blocked_phrases_json, preferences_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("brand-status-test", "Status Test Brand", "[]", "[]", "[]", "[]", "{}"),
                )
                connection.execute(
                    """
                    INSERT INTO generated_posts (
                      id, brand_profile_id, platform, caption, approval_status,
                      safety_flags_json, generation_provider
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "post-status-test",
                        "brand-status-test",
                        "facebook",
                        "Approved local draft.",
                        "approved",
                        "[]",
                        "mock",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO scheduled_posts (
                      id, generated_post_id, brand_profile_id, platform,
                      scheduled_for, timezone, status, caption_snapshot,
                      media_asset_ids_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "scheduled-status-test",
                        "post-status-test",
                        "brand-status-test",
                        "facebook",
                        "2026-06-10T13:00:00Z",
                        "America/New_York",
                        "needs_attention",
                        "Approved local draft.",
                        "[]",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO publish_queue_items (
                      id, scheduled_post_id, generated_post_id, brand_profile_id,
                      platform, queue_status, due_at, timezone, preflight_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "queue-status-test",
                        "scheduled-status-test",
                        "post-status-test",
                        "brand-status-test",
                        "facebook",
                        "blocked",
                        "2026-06-10T13:00:00Z",
                        "America/New_York",
                        "errors",
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO publish_attempts (
                      id, publish_queue_item_id, scheduled_post_id, platform,
                      attempt_type, attempt_status, started_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "attempt-status-test",
                        "queue-status-test",
                        "scheduled-status-test",
                        "facebook",
                        "preflight",
                        "blocked",
                        "2026-06-10T13:01:00Z",
                    ),
                )

                with self.assertRaises(sqlite3.IntegrityError):
                    connection.execute(
                        """
                        INSERT INTO publish_queue_items (
                          id, scheduled_post_id, generated_post_id, brand_profile_id,
                          platform, queue_status, due_at, timezone
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "queue-invalid-status",
                            "scheduled-status-test",
                            "post-status-test",
                            "brand-status-test",
                            "facebook",
                            "real_published",
                            "2026-06-10T13:00:00Z",
                            "America/New_York",
                        ),
                    )

    @staticmethod
    def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


if __name__ == "__main__":
    unittest.main()
