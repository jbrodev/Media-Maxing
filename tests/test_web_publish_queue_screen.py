from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "settings.js"
WEB_STYLES = REPO_ROOT / "apps" / "web" / "styles.css"


class WebPublishQueueScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_SETTINGS.read_text(encoding="utf-8")
        self.styles = WEB_STYLES.read_text(encoding="utf-8")

    def test_publish_queue_route_has_required_screen_elements(self):
        required_ids = [
            "queue-view",
            "queue-summary-waiting",
            "queue-summary-ready",
            "queue-summary-blocked",
            "queue-summary-mock-published",
            "queue-summary-failed",
            "queue-summary-needs-attention",
            "queue-platform-filter",
            "queue-status-filter",
            "queue-preflight-filter",
            "queue-date-filter",
            "queue-brand-filter",
            "queue-search",
            "queue-loading-state",
            "queue-error-state",
            "queue-empty-state",
            "queue-list",
            "queue-detail-panel",
            "queue-detail-empty",
            "queue-detail-content",
            "queue-detail-platform",
            "queue-detail-due",
            "queue-detail-timezone",
            "queue-detail-status",
            "queue-detail-preflight",
            "queue-detail-account-status",
            "queue-detail-account-name",
            "queue-detail-account-scopes",
            "queue-detail-manual-export",
            "queue-detail-real-publishing",
            "queue-detail-mock-publish",
            "queue-detail-caption",
            "queue-detail-hashtags",
            "queue-detail-cta",
            "queue-detail-media",
            "queue-detail-errors",
            "queue-detail-warnings",
            "queue-detail-scheduled",
            "queue-detail-draft",
            "queue-attempt-history",
            "queue-run-preflight",
            "queue-manual-export",
            "queue-mock-publish",
            "queue-cancel",
            "queue-open-calendar",
            "queue-open-draft",
            "queue-copy-caption",
            "queue-export-package",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_publish_queue_route_and_safety_copy_are_present(self):
        self.assertIn('"calendar", "queue"', self.script)
        self.assertIn("Publish Queue", self.html)
        self.assertIn("Local queue only", self.html)
        self.assertIn("Real publishing disabled", self.html)
        self.assertIn("Mock publish is demo-only", self.html)
        self.assertIn("manual export", self.html.lower())
        self.assertIn("account connection status", self.html.lower())
        self.assertIn("real publishing disabled", self.html.lower())

    def test_publish_queue_script_contains_required_workflow_handlers(self):
        for function_name in (
            "renderPublishQueue",
            "selectQueueItem",
            "runSelectedQueuePreflight",
            "markSelectedQueueManualExported",
            "mockPublishSelectedQueueItem",
            "cancelSelectedQueueItem",
            "copySelectedQueueCaption",
            "exportSelectedQueuePackage",
            "appendPublishAttempt",
            "runQueuePreflight",
            "queueAccountReadiness",
            "connectedAccountForPlatform",
            "loadPublishAttempts",
            "savePublishAttempts",
        ):
            with self.subTest(function_name=function_name):
                self.assertIn(f"function {function_name}", self.script)

    def test_publish_queue_mock_and_manual_actions_are_local_only(self):
        self.assertIn("Mock publish recorded locally. No external API was called.", self.script)
        self.assertIn("Manual export recorded locally. No external API was called.", self.script)
        self.assertIn("preflightStatus !== \"passed\"", self.script)
        self.assertIn("queueStatus !== \"ready\"", self.script)
        self.assertIn("mockPublishEnabled", self.script)
        self.assertIn("future real publishing remains disabled", self.script.lower())
        self.assertIn("manualExportEligible", self.script)
        self.assertIn("realPublishingEligible", self.script)
        self.assertIn("mockPublishEligible", self.script)

    def test_publish_queue_css_classes_present(self):
        for class_name in (
            ".queue-summary-grid",
            ".queue-toolbar",
            ".queue-layout",
            ".queue-list",
            ".queue-card",
            ".queue-detail-panel",
            ".queue-detail-grid",
            ".queue-action-panel",
            ".attempt-history-list",
            ".preflight-list",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.styles)


if __name__ == "__main__":
    unittest.main()
