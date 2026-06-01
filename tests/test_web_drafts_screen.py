from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_GENERATE = REPO_ROOT / "apps" / "web" / "generate.js"
WEB_STYLES = REPO_ROOT / "apps" / "web" / "styles.css"


class WebDraftsScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_GENERATE.read_text(encoding="utf-8")
        self.styles = WEB_STYLES.read_text(encoding="utf-8")

    def test_drafts_route_has_filter_and_detail_elements(self):
        required_ids = [
            "drafts-status-filter",
            "drafts-platform-filter",
            "drafts-search",
            "drafts-list",
            "drafts-detail",
            "drafts-detail-empty",
            "drafts-form",
            "draft-edit-headline",
            "draft-edit-hook",
            "draft-edit-caption",
            "draft-edit-short-caption",
            "draft-edit-long-caption",
            "draft-edit-cta",
            "draft-edit-hashtags",
            "draft-edit-alt-text",
            "draft-edit-notes",
            "draft-save-edits",
            "draft-approve",
            "draft-reject",
            "draft-request-revision",
            "draft-archive",
            "draft-schedule",
            "draft-schedule-panel",
            "draft-schedule-form",
            "draft-schedule-date",
            "draft-schedule-time",
            "draft-schedule-timezone",
            "draft-schedule-notes",
            "draft-schedule-confirm",
            "draft-schedule-cancel",
            "draft-schedule-platform",
            "draft-schedule-caption-preview",
            "draft-schedule-media-count",
            "draft-schedule-approval-status",
            "draft-schedule-safety-status",
            "draft-schedule-calendar-link",
            "draft-action-reason",
            "draft-safety-flags",
            "draft-linked-media",
            "draft-prompt-metadata",
            "draft-approval-history",
        ]
        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_approval_status_filter_options_present(self):
        for status in (
            "all",
            "draft",
            "needs_review",
            "approved",
            "rejected",
            "revision_requested",
            "archived",
        ):
            with self.subTest(status=status):
                self.assertIn(f'value="{status}"', self.html)

    def test_drafts_script_contains_required_workflow_handlers(self):
        for handler in (
            "renderDraftsList",
            "selectDraft",
            "saveDraftEdits",
            "approveSelectedDraft",
            "rejectSelectedDraft",
            "requestRevisionForSelectedDraft",
            "archiveSelectedDraft",
            "openSchedulePanel",
            "confirmDraftSchedule",
            "checkDraftSchedulingEligibility",
            "createScheduledPostFromDraft",
            "createPublishQueueItemFromDraft",
            "appendApprovalLog",
            "loadApprovalLogs",
        ):
            with self.subTest(handler=handler):
                self.assertIn(f"function {handler}", self.script)

    def test_edit_after_approval_safest_rule_present(self):
        self.assertIn("edited_requires_reapproval", self.script)
        self.assertIn("needs_review", self.script)
        self.assertIn("Approved drafts return to needs review after edits", self.html)

    def test_drafts_schedule_action_is_local_only(self):
        drafts_section = self.html[
            self.html.find('id="drafts-view"') : self.html.find("</section>", self.html.find('id="drafts-view"')) + 10
        ]
        self.assertNotIn("Publish", drafts_section)
        self.assertIn("Schedule", self.html)
        self.assertIn("Temporary browser scheduling adapter", self.script)
        self.assertIn("local-social-ai-manager.scheduledPosts", self.script)
        self.assertIn("local-social-ai-manager.publishQueueItems", self.script)
        self.assertIn("No publishing was performed", self.script)

    def test_drafts_schedule_blocked_messages_present(self):
        for message in (
            "This draft needs approval before scheduling.",
            "Rejected drafts cannot be scheduled.",
            "This draft needs revision before scheduling.",
            "Resolve critical safety flags before scheduling.",
            "Scheduling is paused because emergency pause is enabled.",
        ):
            with self.subTest(message=message):
                self.assertIn(message, self.script)

    def test_drafts_css_classes_present(self):
        for class_name in (
            ".drafts-toolbar",
            ".draft-card",
            ".draft-detail-grid",
            ".draft-readonly-grid",
            ".approval-history-list",
            ".draft-schedule-panel",
            ".draft-schedule-summary",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.styles)


if __name__ == "__main__":
    unittest.main()
