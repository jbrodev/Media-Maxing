import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.seed_demo import DEMO_BRAND_ID, seed_demo_database
from scripts.services.engagement import EngagementService


class EngagementServiceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        seed_demo_database(db_path)
        return db_path

    def test_mock_ingestion_creates_safe_demo_scenarios(self):
        db_path = self._database()
        service = EngagementService(db_path)

        result = service.ingest_mock_engagement(brand_profile_id=DEMO_BRAND_ID)
        items = service.list_items(brand_profile_id=DEMO_BRAND_ID, source="mock")

        self.assertEqual(result.createdCount, 8)
        self.assertEqual(result.skippedCount, 0)
        self.assertEqual(len(items), 8)
        self.assertEqual(
            {item.intent for item in items},
            {
                "praise",
                "price_request",
                "booking_request",
                "complaint",
                "spam",
                "general",
                "urgent",
            },
        )
        self.assertTrue(all(item.source == "mock" for item in items))
        self.assertTrue(all(item.content == item.contentRedacted for item in items))
        self.assertTrue(all("Demo" in (item.authorName or "") for item in items))
        self.assertTrue(any(item.priority == "urgent" for item in items))
        self.assertTrue(any(item.status == "escalated" for item in items))
        self.assertTrue(any(item.status == "spam" for item in items))

    def test_mock_ingestion_is_idempotent_and_audits_skips(self):
        db_path = self._database()
        service = EngagementService(db_path)

        first = service.ingest_mock_engagement(brand_profile_id=DEMO_BRAND_ID)
        second = service.ingest_mock_engagement(brand_profile_id=DEMO_BRAND_ID)

        self.assertEqual(first.createdCount, 8)
        self.assertEqual(second.createdCount, 0)
        self.assertEqual(second.skippedCount, 8)
        self.assertNotEqual(first.importId, second.importId)
        with closing(sqlite3.connect(db_path)) as connection:
            item_count = connection.execute(
                "SELECT COUNT(*) FROM engagement_items WHERE source = 'mock'"
            ).fetchone()[0]
            latest_import = connection.execute(
                """
                SELECT source, import_type, status, records_imported, records_skipped
                FROM engagement_imports
                WHERE id = ?
                """,
                (second.importId,),
            ).fetchone()
        self.assertEqual(item_count, 8)
        self.assertEqual(latest_import, ("mock", "mock_ingestion", "completed", 0, 8))

    def test_mock_items_link_demo_post_and_never_claim_real_fetch(self):
        db_path = self._database()
        service = EngagementService(db_path)

        service.ingest_mock_engagement(brand_profile_id=DEMO_BRAND_ID)

        with closing(sqlite3.connect(db_path)) as connection:
            rows = connection.execute(
                """
                SELECT published_post_id, raw_data_json
                FROM engagement_items
                WHERE source = 'mock'
                """
            ).fetchall()
        self.assertTrue(any(row[0] == "demo-published-driveway-export" for row in rows))
        self.assertTrue(all('"realPlatformFetch": false' in row[1] for row in rows))

    def test_mock_items_never_link_mismatched_social_account_platform(self):
        db_path = self._database()
        service = EngagementService(db_path)

        service.ingest_mock_engagement(brand_profile_id=DEMO_BRAND_ID)

        with closing(sqlite3.connect(db_path)) as connection:
            linked_platforms = connection.execute(
                """
                SELECT engagement_items.platform, social_accounts.platform
                FROM engagement_items
                JOIN social_accounts
                  ON social_accounts.id = engagement_items.social_account_id
                WHERE engagement_items.source = 'mock'
                """
            ).fetchall()
        self.assertTrue(linked_platforms)
        self.assertTrue(
            all(item_platform == account_platform for item_platform, account_platform in linked_platforms)
        )

    def test_cli_ingests_mock_items_without_external_calls(self):
        db_path = self._database()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.services.engagement",
                "--database",
                str(db_path),
                "--ingest-mock",
                "--brand-profile-id",
                DEMO_BRAND_ID,
            ],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mock_engagement_created=8", result.stdout)
        self.assertIn("real_platform_fetch=false", result.stdout)
        self.assertIn("real_reply_send=false", result.stdout)


if __name__ == "__main__":
    unittest.main()
