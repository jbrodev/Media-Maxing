import sqlite3
import json
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.init_db import initialize_database
from scripts.db.seed_demo import seed_demo_database


EXPECTED_DEMO_COUNTS = {
    "users": 1,
    "brand_profiles": 1,
    "media_assets": 5,
    "content_ideas": 3,
    "generated_posts": 3,
    "scheduled_posts": 2,
    "publish_queue_items": 2,
    "publish_attempts": 2,
    "social_accounts": 1,
    "platform_tokens": 1,
    "connector_audit_logs": 2,
    "connector_health_checks": 1,
    "published_posts": 1,
    "analytics_snapshots": 1,
    "post_performance_metrics": 1,
    "analytics_imports": 1,
    "content_insights": 1,
    "ai_memory": 1,
    "weekly_reports": 1,
}


class DemoSeedTest(unittest.TestCase):
    def test_seed_demo_database_creates_safe_idempotent_demo_records(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"
            initialize_database(db_path)

            seed_demo_database(db_path)
            seed_demo_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                for table_name, expected_count in EXPECTED_DEMO_COUNTS.items():
                    count = connection.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    ).fetchone()[0]
                    self.assertEqual(count, expected_count, table_name)

                settings = connection.execute(
                    """
                    SELECT automation_level, require_approval_before_publishing,
                      require_approval_before_replying, enable_real_publishing,
                      token_storage_mode
                    FROM app_settings
                    WHERE id = 'default'
                    """
                ).fetchone()
                self.assertEqual(
                    settings,
                    ("approval_queue", 1, 1, 0, "placeholder_not_stored"),
                )

                drafts_waiting = connection.execute(
                    """
                    SELECT COUNT(*) FROM generated_posts
                    WHERE approval_status = 'needs_review'
                    """
                ).fetchone()[0]
                self.assertEqual(drafts_waiting, 1)

                approved_count = connection.execute(
                    """
                    SELECT COUNT(*) FROM generated_posts
                    WHERE approval_status = 'approved'
                    """
                ).fetchone()[0]
                self.assertEqual(approved_count, 2)

                queue_rows = connection.execute(
                    """
                    SELECT queue_status, preflight_status, mock_publish_enabled,
                      manual_export_required
                    FROM publish_queue_items
                    ORDER BY id
                    """
                ).fetchall()
                self.assertEqual(len(queue_rows), 2)
                self.assertIn(
                    ("manually_exported", "passed", 0, 1),
                    queue_rows,
                )
                self.assertIn(
                    ("waiting", "passed", 0, 1),
                    queue_rows,
                )

                attempt_rows = connection.execute(
                    """
                    SELECT attempt_type, attempt_status, provider_response_json
                    FROM publish_attempts
                    ORDER BY id
                    """
                ).fetchall()
                self.assertEqual(len(attempt_rows), 2)
                for attempt_type, attempt_status, provider_response_json in attempt_rows:
                    self.assertIn(attempt_type, {"preflight", "manual_export"})
                    self.assertIn(attempt_status, {"succeeded", "started"})
                    provider_response = json.loads(provider_response_json)
                    self.assertFalse(provider_response["real_platform_publish"])

                account_row = connection.execute(
                    """
                    SELECT platform, display_name, connection_status, account_type,
                      granted_scopes_json
                    FROM social_accounts
                    WHERE id = 'demo-social-facebook-page'
                    """
                ).fetchone()
                self.assertEqual(
                    account_row[:4],
                    ("facebook", "Brightside Demo Facebook Page", "connected", "page"),
                )
                self.assertIn("pages_show_list", json.loads(account_row[4]))

                token_row = connection.execute(
                    """
                    SELECT token_type, encrypted_access_token, encrypted_refresh_token,
                      encryption_status
                    FROM platform_tokens
                    WHERE social_account_id = 'demo-social-facebook-page'
                    """
                ).fetchone()
                self.assertEqual(
                    token_row,
                    ("page_access", None, None, "placeholder_not_stored"),
                )

                approval_log_count = connection.execute(
                    "SELECT COUNT(*) FROM approval_logs"
                ).fetchone()[0]
                self.assertGreaterEqual(approval_log_count, 4)

                media_row = connection.execute(
                    """
                    SELECT tags_json, job_context_json, metadata_json
                    FROM media_assets
                    WHERE id = 'demo-media-driveway-after'
                    """
                ).fetchone()
                tags = json.loads(media_row[0])
                job_context = json.loads(media_row[1])
                metadata = json.loads(media_row[2])

                self.assertIn("driveway", tags)
                self.assertEqual(metadata["title"], "Driveway after cleaning")
                self.assertEqual(metadata["usageStatus"], "ready_for_generation")
                self.assertEqual(metadata["qualityRating"], 5)
                self.assertEqual(job_context["serviceType"], "pressure washing")
                self.assertEqual(job_context["contentAngle"], "before_after")


if __name__ == "__main__":
    unittest.main()
