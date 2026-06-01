import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.analytics_models import (
    AI_MEMORY_TYPES,
    ANALYTICS_SOURCES,
    CONTENT_INSIGHT_STATUSES,
    CONTENT_INSIGHT_TYPES,
    PERFORMANCE_TRENDS,
    WEEKLY_REPORT_GENERATORS,
)
from scripts.db.init_db import initialize_database
from scripts.db.init_db import MIGRATIONS_DIR
from scripts.db.seed_demo import seed_demo_database


EXPECTED_ANALYTICS_SNAPSHOT_COLUMNS = {
    "id",
    "published_post_id",
    "scheduled_post_id",
    "generated_post_id",
    "brand_profile_id",
    "platform",
    "source",
    "snapshot_date",
    "impressions",
    "reach",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "clicks",
    "profile_visits",
    "follows",
    "leads",
    "messages",
    "calls",
    "website_clicks",
    "engagement_rate",
    "click_through_rate",
    "lead_rate",
    "raw_metrics_json",
    "notes",
    "created_at",
    "updated_at",
}

EXPECTED_POST_PERFORMANCE_COLUMNS = {
    "id",
    "generated_post_id",
    "scheduled_post_id",
    "published_post_id",
    "brand_profile_id",
    "platform",
    "content_goal",
    "content_angle",
    "media_asset_ids_json",
    "posted_at",
    "first_snapshot_at",
    "latest_snapshot_at",
    "total_impressions",
    "total_reach",
    "total_views",
    "total_likes",
    "total_comments",
    "total_shares",
    "total_saves",
    "total_clicks",
    "total_leads",
    "engagement_rate",
    "lead_rate",
    "performance_score",
    "trend",
    "created_at",
    "updated_at",
}


class Batch7AnalyticsLearningModelsTest(unittest.TestCase):
    def test_batch7_constants_are_available(self):
        self.assertEqual(
            ANALYTICS_SOURCES,
            ("manual", "mock", "platform_api", "imported_csv", "estimated"),
        )
        self.assertIn("improving", PERFORMANCE_TRENDS)
        self.assertIn("recommendation", CONTENT_INSIGHT_TYPES)
        self.assertIn("applied", CONTENT_INSIGHT_STATUSES)
        self.assertIn("ai_mock", WEEKLY_REPORT_GENERATORS)
        self.assertIn("performance_learning", AI_MEMORY_TYPES)

    def test_initialize_database_creates_batch7_tables_and_columns(self):
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
                        "analytics_snapshots",
                        "post_performance_metrics",
                        "analytics_imports",
                        "content_insights",
                        "ai_memory",
                        "weekly_reports",
                    }.issubset(tables)
                )
                self.assertTrue(
                    EXPECTED_ANALYTICS_SNAPSHOT_COLUMNS.issubset(
                        self._columns(connection, "analytics_snapshots")
                    )
                )
                self.assertTrue(
                    EXPECTED_POST_PERFORMANCE_COLUMNS.issubset(
                        self._columns(connection, "post_performance_metrics")
                    )
                )
                self.assertTrue(
                    {"title", "content", "source"}.issubset(
                        self._columns(connection, "ai_memory")
                    )
                )

    def test_demo_seed_labels_analytics_and_learning_rows_as_mock(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"

            seed_demo_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                snapshot = connection.execute(
                    """
                    SELECT source, raw_metrics_json, engagement_rate,
                      click_through_rate, lead_rate
                    FROM analytics_snapshots
                    WHERE id = 'demo-analytics-driveway-export'
                    """
                ).fetchone()
                self.assertEqual(snapshot[0], "mock")
                self.assertTrue(json.loads(snapshot[1])["demo"])
                self.assertGreater(snapshot[2], 0)
                self.assertGreater(snapshot[3], 0)
                self.assertGreater(snapshot[4], 0)

                performance = connection.execute(
                    """
                    SELECT trend, performance_score, media_asset_ids_json
                    FROM post_performance_metrics
                    WHERE id = 'demo-performance-driveway-export'
                    """
                ).fetchone()
                self.assertEqual(performance[0], "improving")
                self.assertGreater(performance[1], 0)
                self.assertIn("demo-media-driveway-after", json.loads(performance[2]))

                analytics_import = connection.execute(
                    """
                    SELECT source, import_type, status
                    FROM analytics_imports
                    WHERE id = 'demo-analytics-import-mock-sync'
                    """
                ).fetchone()
                self.assertEqual(analytics_import, ("mock", "mock_sync", "completed"))

                insight = connection.execute(
                    """
                    SELECT insight_type, confidence, evidence_json
                    FROM content_insights
                    WHERE id = 'demo-insight-before-after'
                    """
                ).fetchone()
                self.assertEqual(insight[:2], ("best_content_type", "low"))
                self.assertTrue(json.loads(insight[2])["demo"])

                memory = connection.execute(
                    """
                    SELECT memory_type, title, content, source, evidence_json
                    FROM ai_memory
                    WHERE id = 'demo-memory-before-after'
                    """
                ).fetchone()
                self.assertEqual(memory[:4], (
                    "performance_learning",
                    "Before-and-after posts may be useful",
                    "Demo-only early signal: transformation posts may be worth testing again.",
                    "mock",
                ))
                self.assertTrue(json.loads(memory[4])["demo"])

                weekly_report = connection.execute(
                    """
                    SELECT generated_by, metric_totals_json
                    FROM weekly_reports
                    WHERE id = 'demo-weekly-report-2026-06-08'
                    """
                ).fetchone()
                self.assertEqual(weekly_report[0], "ai_mock")
                self.assertTrue(json.loads(weekly_report[1])["demo"])

    def test_batch7_migration_preserves_existing_snapshot_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"

            with closing(sqlite3.connect(db_path)) as connection:
                for migration_path in sorted(MIGRATIONS_DIR.glob("*.sql")):
                    if migration_path.name.startswith("007_"):
                        break
                    connection.executescript(migration_path.read_text(encoding="utf-8"))
                    connection.execute(
                        "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)",
                        (migration_path.stem,),
                    )

                connection.execute(
                    """
                    INSERT INTO analytics_snapshots (
                      id, platform, source, captured_at, impressions, reach,
                      likes, comments, shares, saves, clicks, leads, metrics_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "legacy-mock-snapshot",
                        "facebook",
                        "mock",
                        "2026-05-30T12:00:00Z",
                        100,
                        80,
                        4,
                        1,
                        1,
                        2,
                        3,
                        1,
                        json.dumps({"demo": True}),
                    ),
                )
                connection.commit()

            initialize_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                snapshot = connection.execute(
                    """
                    SELECT source, snapshot_date, impressions, reach,
                      engagement_rate, click_through_rate, lead_rate,
                      raw_metrics_json
                    FROM analytics_snapshots
                    WHERE id = 'legacy-mock-snapshot'
                    """
                ).fetchone()
                self.assertEqual(snapshot[:4], ("mock", "2026-05-30T12:00:00Z", 100, 80))
                self.assertGreater(snapshot[4], 0)
                self.assertGreater(snapshot[5], 0)
                self.assertGreater(snapshot[6], 0)
                self.assertTrue(json.loads(snapshot[7])["demo"])

    @staticmethod
    def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


if __name__ == "__main__":
    unittest.main()
