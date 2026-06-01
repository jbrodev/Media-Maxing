from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.init_db import initialize_database
from scripts.db.settings import update_app_settings
from scripts.services.manual_export import ManualExportError, ManualExportService


def _json(value):
    return json.dumps(value, sort_keys=True)


class ManualExportServiceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        update_app_settings(
            db_path,
            {
                "localDataDirectory": str(Path(temp_dir.name) / "data"),
                "appEnvironment": "development",
            },
        )
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO brand_profiles (
                  id, business_name, services_json, locations_json,
                  supported_claims_json, blocked_phrases_json, preferences_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "brand-export-test",
                    "Export Test Exterior Care",
                    _json(["driveway cleaning"]),
                    _json(["Demo City"]),
                    _json(["Uses local-first demo data."]),
                    _json([]),
                    _json({"demo": True}),
                ),
            )
            connection.execute(
                """
                INSERT INTO media_assets (
                  id, media_type, original_path, file_name, mime_type,
                  file_size_bytes, tags_json, job_context_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "media-export-1",
                    "image",
                    "data/media/originals/demo-driveway.jpg",
                    "demo-driveway.jpg",
                    "image/jpeg",
                    2400,
                    _json(["demo", "before-after"]),
                    _json({}),
                    _json({"demo": True}),
                ),
            )
            connection.commit()
        return db_path

    def _create_ready_queue_item(
        self,
        db_path: Path,
        *,
        queue_status: str = "ready",
        preflight_status: str = "passed",
        preflight_errors: list[str] | None = None,
        preflight_warnings: list[str] | None = None,
    ) -> tuple[str, str, str]:
        post_id = "post-export-ready"
        scheduled_id = "scheduled-export-ready"
        queue_id = "queue-export-ready"
        preflight_errors = preflight_errors or []
        preflight_warnings = preflight_warnings or [
            "missing_connected_account: Future real publishing needs an account."
        ]
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO generated_posts (
                  id, brand_profile_id, platform, headline, hook, caption,
                  call_to_action, hashtags_json, approval_status,
                  safety_flags_json, generation_provider, media_asset_ids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    "brand-export-test",
                    "facebook",
                    "Driveway project recap",
                    "A safe before-and-after driveway moment.",
                    "A clean driveway can make the whole property feel fresher.",
                    "Ask about exterior cleaning options.",
                    _json(["#DemoBusiness", "#ExteriorCleaning"]),
                    "approved",
                    _json([]),
                    "mock",
                    _json(["media-export-1"]),
                ),
            )
            connection.execute(
                """
                INSERT INTO scheduled_posts (
                  id, generated_post_id, brand_profile_id, platform,
                  scheduled_for, timezone, status, caption_snapshot,
                  media_asset_ids_json, schedule_metadata_json, user_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scheduled_id,
                    post_id,
                    "brand-export-test",
                    "facebook",
                    "2026-06-10T13:00:00Z",
                    "America/New_York",
                    "queued",
                    "A clean driveway can make the whole property feel fresher.",
                    _json(["media-export-1"]),
                    _json(
                        {
                            "headline": "Driveway project recap",
                            "hook": "A safe before-and-after driveway moment.",
                            "hashtags": ["#DemoBusiness", "#ExteriorCleaning"],
                            "callToAction": "Ask about exterior cleaning options.",
                            "safetyFlags": [],
                        }
                    ),
                    "Demo export note.",
                ),
            )
            connection.execute(
                """
                INSERT INTO publish_queue_items (
                  id, scheduled_post_id, generated_post_id, brand_profile_id,
                  platform, queue_status, due_at, timezone, preflight_status,
                  preflight_errors_json, preflight_warnings_json,
                  mock_publish_enabled, manual_export_required
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    queue_id,
                    scheduled_id,
                    post_id,
                    "brand-export-test",
                    "facebook",
                    queue_status,
                    "2026-06-10T13:00:00Z",
                    "America/New_York",
                    preflight_status,
                    _json(preflight_errors),
                    _json(preflight_warnings),
                    1,
                    1,
                ),
            )
            connection.commit()
        return post_id, scheduled_id, queue_id

    def test_ready_queue_item_exports_manual_package_files_without_marking_exported(self):
        db_path = self._database()
        post_id, scheduled_id, queue_id = self._create_ready_queue_item(db_path)
        export_dir = tempfile.TemporaryDirectory()
        self.addCleanup(export_dir.cleanup)
        export_root = Path(export_dir.name)

        result = ManualExportService(db_path, export_root=export_root).export_queue_item(
            queue_id,
            exported_at="2026-06-10T14:00:00Z",
        )

        self.assertTrue(result.exportPath.exists())
        self.assertEqual(result.filesCreated, [
            "caption.txt",
            "hashtags.txt",
            "post.md",
            "metadata.json",
            "media-manifest.json",
            "posting-instructions.md",
        ])
        self.assertEqual(
            (result.exportPath / "caption.txt").read_text(encoding="utf-8"),
            "A clean driveway can make the whole property feel fresher.\n",
        )
        self.assertIn("#DemoBusiness", (result.exportPath / "hashtags.txt").read_text(encoding="utf-8"))

        metadata = json.loads((result.exportPath / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["queueItemId"], queue_id)
        self.assertEqual(metadata["scheduledPostId"], scheduled_id)
        self.assertEqual(metadata["generatedPostId"], post_id)
        self.assertEqual(metadata["preflightStatus"], "warnings")
        self.assertEqual(metadata["queueStatus"], "ready")

        media_manifest = json.loads(
            (result.exportPath / "media-manifest.json").read_text(encoding="utf-8")
        )
        self.assertFalse(media_manifest["mediaCopied"])
        self.assertEqual(media_manifest["media"][0]["id"], "media-export-1")
        self.assertIn(
            "not an automatic publish",
            (result.exportPath / "posting-instructions.md").read_text(encoding="utf-8").lower(),
        )
        self.assertIn(
            "mark as manually exported",
            (result.exportPath / "posting-instructions.md").read_text(encoding="utf-8").lower(),
        )

        with closing(sqlite3.connect(db_path)) as connection:
            queue_status = connection.execute(
                "SELECT queue_status FROM publish_queue_items WHERE id = ?",
                (queue_id,),
            ).fetchone()[0]
        self.assertEqual(queue_status, "ready")

    def test_failed_preflight_blocks_manual_export(self):
        db_path = self._database()
        _, _, queue_id = self._create_ready_queue_item(
            db_path,
            queue_status="blocked",
            preflight_status="errors",
            preflight_errors=["missing_required_media: Platform requires linked media."],
        )

        with self.assertRaises(ManualExportError) as error:
            ManualExportService(db_path).export_queue_item(queue_id)

        self.assertIn("preflight_failed", error.exception.error_codes)

    def test_emergency_pause_blocks_manual_export(self):
        db_path = self._database()
        _, _, queue_id = self._create_ready_queue_item(db_path)
        update_app_settings(db_path, {"emergencyPauseEnabled": True})

        with self.assertRaises(ManualExportError) as error:
            ManualExportService(db_path).export_queue_item(queue_id)

        self.assertIn("emergency_pause_enabled", error.exception.error_codes)

    def test_repeated_exports_use_unique_folders(self):
        db_path = self._database()
        _, _, queue_id = self._create_ready_queue_item(db_path)
        export_dir = tempfile.TemporaryDirectory()
        self.addCleanup(export_dir.cleanup)
        export_root = Path(export_dir.name)
        service = ManualExportService(db_path, export_root=export_root)

        first = service.export_queue_item(queue_id, exported_at="2026-06-10T14:00:00Z")
        second = service.export_queue_item(queue_id, exported_at="2026-06-10T14:00:00Z")

        self.assertNotEqual(first.exportPath, second.exportPath)
        self.assertTrue(first.exportPath.exists())
        self.assertTrue(second.exportPath.exists())


if __name__ == "__main__":
    unittest.main()
