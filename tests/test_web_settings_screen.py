from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SCRIPT = REPO_ROOT / "apps" / "web" / "settings.js"


class WebSettingsScreenTest(unittest.TestCase):
    def test_settings_screen_contains_required_fields_and_adapter(self):
        html = WEB_INDEX.read_text(encoding="utf-8")
        script = WEB_SCRIPT.read_text(encoding="utf-8")

        required_ids = [
            "settings-view",
            "settings-form",
            "appName",
            "localDataDirectory",
            "defaultTimezone",
            "defaultPlatformTargets",
            "automationLevel",
            "requireApprovalBeforePublishing",
            "requireApprovalBeforeReplying",
            "emergencyPauseEnabled",
            "aiProviderPreference",
            "settings-error",
            "settings-success",
        ]

        for element_id in required_ids:
            self.assertIn(f'id="{element_id}"', html)

        self.assertIn("Emergency pause", html)
        self.assertIn("Local settings adapter", html)
        self.assertIn("activeApiBridge", script)
        self.assertIn("persistThroughApi", script)
        self.assertIn("localStorage", script)
        self.assertIn("autonomous_content_engine", script)
        self.assertIn("approval before publishing", script)


if __name__ == "__main__":
    unittest.main()
