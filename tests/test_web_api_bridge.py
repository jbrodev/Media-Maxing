from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_CLIENT = REPO_ROOT / "apps" / "web" / "api-client.js"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "settings.js"
WEB_GENERATE = REPO_ROOT / "apps" / "web" / "generate.js"
WEB_ANALYTICS = REPO_ROOT / "apps" / "web" / "analytics.js"
WEB_ENGAGEMENT = REPO_ROOT / "apps" / "web" / "engagement.js"


class WebApiBridgeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.client = WEB_CLIENT.read_text(encoding="utf-8")
        self.settings = WEB_SETTINGS.read_text(encoding="utf-8")
        self.generate = WEB_GENERATE.read_text(encoding="utf-8")
        self.analytics = WEB_ANALYTICS.read_text(encoding="utf-8")
        self.engagement = WEB_ENGAGEMENT.read_text(encoding="utf-8")

    def test_bridge_client_is_loaded_before_feature_scripts(self):
        bridge_index = self.html.index('<script src="./api-client.js"></script>')
        settings_index = self.html.index('<script src="./settings.js"></script>')

        self.assertLess(bridge_index, settings_index)
        self.assertIn("/api/bootstrap", self.client)
        self.assertIn("local-api-ready", self.client)
        self.assertIn("SQLite bridge unavailable; using static local demo adapter.", self.client)

    def test_phase7_screens_use_bridge_routes_when_available(self):
        for route in (
            "/api/analytics/snapshots",
            "/api/analytics/mock",
            "/api/weekly-reports",
            "/api/ai-memory/refresh",
            "/api/ai-memory/",
        ):
            with self.subTest(route=route):
                self.assertIn(route, self.analytics)
        for route in (
            "/api/engagement/mock",
            "/api/reply-suggestions/",
        ):
            with self.subTest(route=route):
                self.assertIn(route, self.engagement)

    def test_legacy_workflows_have_sqlite_mutation_routes(self):
        self.assertIn("/api/settings", self.settings)
        self.assertIn("/api/brand-profiles/", self.settings)
        self.assertIn("/api/media/", self.settings)
        self.assertIn("/api/calendar/", self.settings)
        self.assertIn("/api/publish-queue/", self.settings)
        self.assertIn("/api/drafts/", self.generate)
        self.assertIn("/api/drafts/save-generated", self.generate)
        self.assertIn("/needs-attention", self.settings)
        self.assertIn("/mock-connect", self.settings)
        self.assertIn("/validate", self.settings)
        self.assertIn("/api/analytics/insights/", self.analytics)


if __name__ == "__main__":
    unittest.main()
