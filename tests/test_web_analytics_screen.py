from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SCRIPT = REPO_ROOT / "apps" / "web" / "analytics.js"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "settings.js"
WEB_STYLES = REPO_ROOT / "apps" / "web" / "styles.css"


class WebAnalyticsScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_SCRIPT.read_text(encoding="utf-8") if WEB_SCRIPT.exists() else ""
        self.settings_script = WEB_SETTINGS.read_text(encoding="utf-8")
        self.styles = WEB_STYLES.read_text(encoding="utf-8")

    def test_analytics_route_has_required_screen_elements(self):
        required_ids = [
            "analytics-view",
            "analytics-range-filter",
            "analytics-platform-filter",
            "analytics-source-filter",
            "analytics-loading-state",
            "analytics-error-state",
            "analytics-empty-state",
            "analytics-summary-grid",
            "analytics-summary-posts",
            "analytics-summary-impressions",
            "analytics-summary-views",
            "analytics-summary-engagements",
            "analytics-summary-engagement-rate",
            "analytics-summary-clicks",
            "analytics-summary-leads",
            "analytics-summary-lead-rate",
            "analytics-summary-best-platform",
            "analytics-summary-best-angle",
            "analytics-platform-breakdown",
            "analytics-goal-breakdown",
            "analytics-angle-breakdown",
            "analytics-top-posts",
            "analytics-underperforming-posts",
            "analytics-insights",
            "analytics-manual-form",
            "analytics-manual-post",
            "analytics-manual-platform",
            "analytics-manual-date",
            "analytics-manual-impressions",
            "analytics-manual-reach",
            "analytics-manual-views",
            "analytics-manual-likes",
            "analytics-manual-comments",
            "analytics-manual-shares",
            "analytics-manual-saves",
            "analytics-manual-clicks",
            "analytics-manual-leads",
            "analytics-manual-messages",
            "analytics-manual-calls",
            "analytics-manual-website-clicks",
            "analytics-manual-notes",
            "analytics-manual-success",
            "analytics-manual-error",
            "analytics-generate-mock",
            "analytics-mock-message",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_analytics_route_and_demo_safety_copy_are_present(self):
        self.assertIn('"analytics"', self.settings_script)
        self.assertIn('href="#analytics"', self.html)
        self.assertIn("Mock analytics are demo data", self.html)
        self.assertIn("No real analytics APIs", self.html)
        self.assertIn("Manual analytics entry", self.html)
        self.assertIn('<script src="./analytics.js"></script>', self.html)

    def test_analytics_script_contains_local_adapter_and_handlers(self):
        for function_name in (
            "loadAnalyticsSnapshots",
            "saveAnalyticsSnapshots",
            "createManualAnalyticsSnapshot",
            "generateMockAnalytics",
            "calculateAnalyticsRates",
            "computeAnalyticsSummary",
            "computePlatformBreakdown",
            "computeContentBreakdown",
            "identifyTopPosts",
            "identifyUnderperformingPosts",
            "renderAnalytics",
            "renderAnalyticsInsights",
            "handleAnalyticsInsightAction",
            "setupAnalytics",
        ):
            with self.subTest(function_name=function_name):
                self.assertIn(f"function {function_name}", self.script)

        self.assertIn("Temporary browser Analytics adapter", self.script)
        self.assertIn("local-social-ai-manager.analyticsSnapshots", self.script)
        self.assertIn('source: "mock"', self.script)
        self.assertIn('source: "manual"', self.script)
        self.assertNotIn("fetch(", self.script)

    def test_analytics_css_classes_present(self):
        for class_name in (
            ".analytics-toolbar",
            ".analytics-summary-grid",
            ".analytics-summary-card",
            ".analytics-breakdown-grid",
            ".analytics-table-wrap",
            ".analytics-post-list",
            ".analytics-post-card",
            ".analytics-insight-list",
            ".analytics-insight-card",
            ".analytics-manual-form",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.styles)


if __name__ == "__main__":
    unittest.main()
