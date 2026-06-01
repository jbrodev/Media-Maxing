from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "settings.js"
WEB_STYLES = REPO_ROOT / "apps" / "web" / "styles.css"


class WebCalendarScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_SETTINGS.read_text(encoding="utf-8")
        self.styles = WEB_STYLES.read_text(encoding="utf-8")

    def test_calendar_route_has_required_screen_elements(self):
        required_ids = [
            "calendar-view",
            "calendar-range-label",
            "calendar-view-week",
            "calendar-view-month",
            "calendar-view-list",
            "calendar-prev",
            "calendar-today",
            "calendar-next",
            "calendar-platform-filter",
            "calendar-status-filter",
            "calendar-loading-state",
            "calendar-error-state",
            "calendar-empty-state",
            "calendar-grid",
            "calendar-list",
            "calendar-detail-panel",
            "calendar-detail-empty",
            "calendar-detail-content",
            "calendar-reschedule-form",
            "calendar-reschedule-datetime",
            "calendar-reschedule-timezone",
            "calendar-notes",
            "calendar-reschedule-button",
            "calendar-cancel-button",
            "calendar-open-draft",
            "calendar-view-queue-item",
            "calendar-copy-caption",
            "calendar-mark-needs-attention",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_calendar_script_contains_local_adapter_and_actions(self):
        for function_name in (
            "loadScheduledPosts",
            "saveScheduledPosts",
            "loadPublishQueueItems",
            "savePublishQueueItems",
            "renderCalendar",
            "selectCalendarPost",
            "rescheduleSelectedPost",
            "cancelSelectedPost",
            "copySelectedCaption",
            "markSelectedNeedsAttention",
        ):
            with self.subTest(function_name=function_name):
                self.assertIn(f"function {function_name}", self.script)

        self.assertIn("Temporary browser Calendar adapter", self.script)
        self.assertIn("no real publishing", self.script.lower())
        self.assertIn("local-social-ai-manager.scheduledPosts", self.script)
        self.assertIn("local-social-ai-manager.publishQueueItems", self.script)

    def test_calendar_route_and_safety_copy_are_present(self):
        self.assertIn('"home", "media", "generate", "drafts", "calendar"', self.script)
        self.assertIn("Local-only calendar", self.html)
        self.assertIn("Real publishing disabled", self.html)
        self.assertIn("approved drafts", self.html)

    def test_calendar_css_classes_present(self):
        for class_name in (
            ".calendar-toolbar",
            ".calendar-layout",
            ".calendar-grid",
            ".calendar-day",
            ".calendar-post-card",
            ".calendar-detail-panel",
            ".calendar-detail-grid",
            ".calendar-view-toggle",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.styles)


if __name__ == "__main__":
    unittest.main()
