from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.seed_demo import DEMO_BRAND_ID, seed_demo_database
from scripts.db.settings import update_app_settings
from scripts.services.analytics import (
    AnalyticsService,
    AnalyticsServiceError,
    calculate_analytics_rates,
    calculate_performance_score,
)


class AnalyticsServiceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        seed_demo_database(db_path)
        return db_path

    def test_rate_and_score_formulas_handle_zero_values(self):
        rates = calculate_analytics_rates({})
        score = calculate_performance_score({})

        self.assertEqual(rates["engagementRate"], 0)
        self.assertEqual(rates["clickThroughRate"], 0)
        self.assertEqual(rates["leadRate"], 0)
        self.assertEqual(score, 0)

    def test_create_update_and_list_manual_snapshot(self):
        db_path = self._database()
        service = AnalyticsService(db_path)

        created = service.create_manual_snapshot(
            brand_profile_id=DEMO_BRAND_ID,
            platform="facebook",
            snapshot_date="2026-06-11",
            generated_post_id="demo-post-gutter-reminder",
            impressions=500,
            reach=420,
            likes=20,
            comments=4,
            shares=3,
            saves=5,
            clicks=12,
            leads=2,
            website_clicks=8,
            notes="Manual local entry.",
        )

        self.assertEqual(created.source, "manual")
        self.assertEqual(created.snapshotDate, "2026-06-11T00:00:00Z")
        self.assertEqual(created.websiteClicks, 8)
        self.assertGreater(created.engagementRate, 0)
        self.assertGreater(created.clickThroughRate, 0)
        self.assertGreater(created.leadRate, 0)

        updated = service.update_snapshot(
            created.id,
            {"clicks": 15, "leads": 3, "notes": "Updated manual local entry."},
        )
        self.assertEqual(updated.clicks, 15)
        self.assertEqual(updated.leads, 3)
        self.assertEqual(updated.notes, "Updated manual local entry.")
        self.assertGreater(updated.leadRate, created.leadRate)

        listed = service.list_snapshots(
            brand_profile_id=DEMO_BRAND_ID,
            platform="facebook",
            start="2026-06-10",
            end="2026-06-12",
            source="manual",
        )
        self.assertEqual([snapshot.id for snapshot in listed], [created.id])

    def test_duplicate_manual_snapshot_for_same_post_date_is_rejected(self):
        db_path = self._database()
        service = AnalyticsService(db_path)
        values = {
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "facebook",
            "snapshot_date": "2026-06-11",
            "generated_post_id": "demo-post-gutter-reminder",
            "impressions": 100,
        }

        service.create_manual_snapshot(**values)

        with self.assertRaises(AnalyticsServiceError) as context:
            service.create_manual_snapshot(**values)
        self.assertIn("duplicate_snapshot", context.exception.error_codes)

    def test_generate_mock_snapshots_is_deterministic_and_avoids_duplicates(self):
        db_path = self._database()
        service = AnalyticsService(db_path)

        first = service.generate_mock_snapshots(
            brand_profile_id=DEMO_BRAND_ID,
            snapshot_date="2026-06-15",
        )
        second = service.generate_mock_snapshots(
            brand_profile_id=DEMO_BRAND_ID,
            snapshot_date="2026-06-15",
        )

        self.assertGreaterEqual(first.createdCount, 1)
        self.assertEqual(second.createdCount, 0)
        self.assertGreaterEqual(second.skippedCount, 1)
        for snapshot in service.list_snapshots(
            brand_profile_id=DEMO_BRAND_ID,
            source="mock",
            start="2026-06-15",
            end="2026-06-16",
        ):
            self.assertEqual(snapshot.source, "mock")
            self.assertTrue(snapshot.rawMetrics["demo"])

    def test_mock_generation_is_blocked_outside_development_without_explicit_request(self):
        db_path = self._database()
        update_app_settings(db_path, {"appEnvironment": "production"})
        service = AnalyticsService(db_path)

        with self.assertRaises(AnalyticsServiceError) as context:
            service.generate_mock_snapshots(
                brand_profile_id=DEMO_BRAND_ID,
                snapshot_date="2026-06-15",
            )
        self.assertIn("mock_generation_not_allowed", context.exception.error_codes)

        explicit = service.generate_mock_snapshots(
            brand_profile_id=DEMO_BRAND_ID,
            snapshot_date="2026-06-15",
            explicitly_requested=True,
        )
        self.assertGreaterEqual(explicit.createdCount, 1)

    def test_performance_summary_uses_latest_snapshot_per_post(self):
        db_path = self._database()
        service = AnalyticsService(db_path)
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                """
                UPDATE generated_posts
                SET content_goal = 'educate_customer',
                    content_angle = 'educational'
                WHERE id = 'demo-post-gutter-reminder'
                """
            )
            connection.commit()

        service.create_manual_snapshot(
            brand_profile_id=DEMO_BRAND_ID,
            platform="facebook",
            snapshot_date="2026-06-10",
            generated_post_id="demo-post-gutter-reminder",
            impressions=100,
            reach=90,
            likes=5,
            saves=2,
            clicks=4,
            leads=1,
        )
        service.create_manual_snapshot(
            brand_profile_id=DEMO_BRAND_ID,
            platform="facebook",
            snapshot_date="2026-06-11",
            generated_post_id="demo-post-gutter-reminder",
            impressions=180,
            reach=150,
            likes=12,
            comments=2,
            saves=7,
            clicks=9,
            leads=2,
        )

        performance = service.compute_post_performance_metrics(
            brand_profile_id=DEMO_BRAND_ID,
            source="manual",
        )
        dashboard = service.compute_dashboard_summary(
            brand_profile_id=DEMO_BRAND_ID,
            source="manual",
            start="2026-06-10",
            end="2026-06-12",
        )

        self.assertEqual(len(performance), 1)
        self.assertEqual(performance[0].totalImpressions, 180)
        self.assertEqual(performance[0].trend, "improving")
        self.assertEqual(dashboard["totalPosts"], 1)
        self.assertEqual(dashboard["totalImpressions"], 180)

    def test_breakdowns_rank_top_and_underperforming_posts(self):
        db_path = self._database()
        service = AnalyticsService(db_path)
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                """
                UPDATE generated_posts
                SET content_goal = 'educate_customer',
                    content_angle = 'educational'
                WHERE id = 'demo-post-gutter-reminder'
                """
            )
            connection.execute(
                """
                UPDATE generated_posts
                SET content_goal = 'build_trust',
                    content_angle = 'behind_the_scenes'
                WHERE id = 'demo-post-crew-prep'
                """
            )
            connection.commit()

        service.create_manual_snapshot(
            brand_profile_id=DEMO_BRAND_ID,
            platform="facebook",
            snapshot_date="2026-06-11",
            generated_post_id="demo-post-gutter-reminder",
            impressions=500,
            reach=420,
            likes=30,
            comments=10,
            shares=4,
            saves=20,
            clicks=20,
            leads=4,
        )
        service.create_manual_snapshot(
            brand_profile_id=DEMO_BRAND_ID,
            platform="threads",
            snapshot_date="2026-06-11",
            generated_post_id="demo-post-crew-prep",
            impressions=90,
            reach=80,
            likes=1,
        )

        platform = service.compute_platform_breakdown(
            brand_profile_id=DEMO_BRAND_ID,
            source="manual",
        )
        angle = service.compute_content_angle_breakdown(
            brand_profile_id=DEMO_BRAND_ID,
            source="manual",
        )
        goal = service.compute_content_goal_breakdown(
            brand_profile_id=DEMO_BRAND_ID,
            source="manual",
        )
        top = service.identify_top_posts(
            brand_profile_id=DEMO_BRAND_ID,
            source="manual",
        )
        weak = service.identify_underperforming_posts(
            brand_profile_id=DEMO_BRAND_ID,
            source="manual",
        )

        self.assertEqual(platform[0]["platform"], "facebook")
        self.assertEqual(angle[0]["contentAngle"], "educational")
        self.assertEqual(goal[0]["contentGoal"], "educate_customer")
        self.assertEqual(top[0].generatedPostId, "demo-post-gutter-reminder")
        self.assertEqual(weak[0].generatedPostId, "demo-post-crew-prep")

    def test_rule_based_insights_and_import_records_are_stored_idempotently(self):
        db_path = self._database()
        service = AnalyticsService(db_path)
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                """
                UPDATE generated_posts
                SET content_goal = 'show_transformation',
                    content_angle = 'transformation',
                    call_to_action = 'Ask about exterior cleaning options.'
                WHERE id = 'demo-post-driveway-transformation'
                """
            )
            connection.commit()

        import_record = service.record_analytics_import(
            source="manual",
            import_type="manual_entry",
            platform="instagram",
            records_imported=1,
        )
        first = service.create_content_insights(brand_profile_id=DEMO_BRAND_ID)
        second = service.create_content_insights(brand_profile_id=DEMO_BRAND_ID)

        self.assertEqual(import_record.source, "manual")
        self.assertEqual(import_record.importType, "manual_entry")
        self.assertGreaterEqual(len(first), 1)
        self.assertEqual([insight.id for insight in first], [insight.id for insight in second])

        with closing(sqlite3.connect(db_path)) as connection:
            stored = connection.execute(
                """
                SELECT COUNT(*)
                FROM content_insights
                WHERE brand_profile_id = ?
                """,
                (DEMO_BRAND_ID,),
            ).fetchone()[0]
        self.assertGreaterEqual(stored, 1)
        self.assertLessEqual(stored, len(first) + 1)

    def test_cli_summary_serializes_top_post_safely(self):
        db_path = self._database()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.services.analytics",
                "--database",
                str(db_path),
                "--brand-profile-id",
                DEMO_BRAND_ID,
            ],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('"topPost":', result.stdout)
        self.assertIn("real_platform_analytics=false", result.stdout)


if __name__ == "__main__":
    unittest.main()
