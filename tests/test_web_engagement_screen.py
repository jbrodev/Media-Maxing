from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SCRIPT = REPO_ROOT / "apps" / "web" / "engagement.js"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "settings.js"
WEB_STYLES = REPO_ROOT / "apps" / "web" / "styles.css"


class WebEngagementScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_SCRIPT.read_text(encoding="utf-8") if WEB_SCRIPT.exists() else ""
        self.settings_script = WEB_SETTINGS.read_text(encoding="utf-8")
        self.styles = WEB_STYLES.read_text(encoding="utf-8")

    def test_engagement_route_has_required_screen_elements(self):
        required_ids = [
            "engagement-view",
            "engagement-generate-mock",
            "engagement-mock-message",
            "engagement-summary-new",
            "engagement-summary-needs-reply",
            "engagement-summary-reply-suggested",
            "engagement-summary-approved",
            "engagement-summary-urgent",
            "engagement-summary-complaints",
            "engagement-summary-leads",
            "engagement-summary-spam",
            "engagement-platform-filter",
            "engagement-status-filter",
            "engagement-sentiment-filter",
            "engagement-intent-filter",
            "engagement-priority-filter",
            "engagement-source-filter",
            "engagement-date-filter",
            "engagement-search",
            "engagement-loading-state",
            "engagement-error-state",
            "engagement-empty-state",
            "engagement-list",
            "engagement-detail-panel",
            "engagement-detail-empty",
            "engagement-detail-content",
            "engagement-detail-full-content",
            "engagement-detail-platform",
            "engagement-detail-author",
            "engagement-detail-received",
            "engagement-detail-sentiment",
            "engagement-detail-intent",
            "engagement-detail-priority",
            "engagement-detail-status",
            "engagement-detail-related-post",
            "engagement-detail-thread",
            "engagement-detail-notes",
            "engagement-mark-needs-reply",
            "engagement-ignore",
            "engagement-archive",
            "engagement-mark-spam",
            "engagement-escalate",
            "engagement-mark-replied-manually",
            "engagement-generate-suggestion",
            "engagement-suggestion-area",
            "engagement-suggestion-message",
            "engagement-action-message",
            "engagement-action-error",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_engagement_route_and_safety_copy_are_present(self):
        self.assertIn('"engagement"', self.settings_script)
        self.assertIn('href="#engagement"', self.html)
        self.assertIn("Replies are not sent automatically.", self.html)
        self.assertIn("AI suggestions require approval.", self.html)
        self.assertIn("Manual reply tracking is local only.", self.html)
        self.assertIn('<script src="./engagement.js"></script>', self.html)

    def test_engagement_script_contains_local_adapter_and_handlers(self):
        for function_name in (
            "loadEngagementItems",
            "saveEngagementItems",
            "generateMockEngagement",
            "updateEngagementStatus",
            "filteredEngagementItems",
            "renderEngagementSummary",
            "renderEngagementList",
            "renderEngagementDetail",
            "renderEngagement",
            "setupEngagement",
        ):
            with self.subTest(function_name=function_name):
                self.assertIn(f"function {function_name}", self.script)

        self.assertIn("Temporary browser Engagement adapter", self.script)
        self.assertIn("local-social-ai-manager.engagementItems", self.script)
        self.assertIn('source: "mock"', self.script)
        self.assertIn("Replies are not sent automatically.", self.script)
        self.assertIn("approved locally only", self.script)
        self.assertNotIn("fetch(", self.script)

    def test_engagement_css_classes_present(self):
        for class_name in (
            ".engagement-summary-grid",
            ".engagement-summary-card",
            ".engagement-toolbar",
            ".engagement-layout",
            ".engagement-list",
            ".engagement-card",
            ".engagement-detail-panel",
            ".engagement-detail-grid",
            ".engagement-actions",
            ".engagement-suggestion-area",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.styles)


if __name__ == "__main__":
    unittest.main()
