import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.init_db import initialize_database
from scripts.db.settings import (
    SettingsValidationError,
    load_app_settings,
    update_app_settings,
)


class AppSettingsTest(unittest.TestCase):
    def test_load_app_settings_creates_safe_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"
            initialize_database(db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute("DELETE FROM app_settings")
                connection.commit()

            settings = load_app_settings(db_path)

            self.assertEqual(settings.appName, "Local Social AI Manager")
            self.assertEqual(settings.appEnvironment, "development")
            self.assertEqual(settings.localDataDirectory, "./data")
            self.assertEqual(settings.defaultTimezone, "America/New_York")
            self.assertEqual(settings.defaultPlatformTargets, ["facebook", "instagram"])
            self.assertEqual(settings.automationLevel, "approval_queue")
            self.assertTrue(settings.requireApprovalBeforePublishing)
            self.assertTrue(settings.requireApprovalBeforeReplying)
            self.assertFalse(settings.emergencyPauseEnabled)
            self.assertEqual(settings.aiProviderPreference, "mock")
            self.assertIsNotNone(settings.createdAt)
            self.assertIsNotNone(settings.updatedAt)

    def test_update_app_settings_persists_valid_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"
            initialize_database(db_path)

            updated = update_app_settings(
                db_path,
                {
                    "appName": "Demo Manager",
                    "appEnvironment": "test",
                    "localDataDirectory": "./demo-data",
                    "defaultTimezone": "America/Chicago",
                    "defaultPlatformTargets": ["facebook", "linkedin"],
                    "automationLevel": "manual_assist",
                    "requireApprovalBeforePublishing": True,
                    "requireApprovalBeforeReplying": False,
                    "emergencyPauseEnabled": True,
                    "aiProviderPreference": "local",
                },
            )
            loaded = load_app_settings(db_path)

            self.assertEqual(updated, loaded)
            self.assertEqual(loaded.appName, "Demo Manager")
            self.assertEqual(loaded.defaultPlatformTargets, ["facebook", "linkedin"])
            self.assertEqual(loaded.automationLevel, "manual_assist")
            self.assertTrue(loaded.requireApprovalBeforePublishing)
            self.assertFalse(loaded.requireApprovalBeforeReplying)
            self.assertTrue(loaded.emergencyPauseEnabled)
            self.assertEqual(loaded.aiProviderPreference, "local")

    def test_update_app_settings_rejects_invalid_automation_level(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "app.sqlite"
            initialize_database(db_path)
            before = load_app_settings(db_path)

            with self.assertRaises(SettingsValidationError) as error:
                update_app_settings(db_path, {"automationLevel": "auto_everything"})

            self.assertIn("automationLevel", str(error.exception))
            self.assertIn("auto_everything", str(error.exception))
            after = load_app_settings(db_path)
            self.assertEqual(after, before)


if __name__ == "__main__":
    unittest.main()
