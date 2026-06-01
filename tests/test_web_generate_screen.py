from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_GENERATE = REPO_ROOT / "apps" / "web" / "generate.js"
WEB_SETTINGS_SCRIPT = REPO_ROOT / "apps" / "web" / "settings.js"


class WebGenerateScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_GENERATE.read_text(encoding="utf-8")
        self.settings_script = WEB_SETTINGS_SCRIPT.read_text(encoding="utf-8")

    def test_route_view_and_required_ids_present(self):
        required_ids = [
            "generate-view",
            "generate-form",
            "generate-brand-summary",
            "generate-brand-empty",
            "generate-brand-fields",
            "generate-media-grid",
            "generate-media-empty",
            "generate-platforms",
            "generate-goal",
            "generate-angle",
            "generate-campaign",
            "generate-offer",
            "generate-instructions",
            "generate-variants",
            "generate-tone",
            "generate-creativity",
            "generate-include-hashtags",
            "generate-include-emojis",
            "generate-include-cta",
            "generate-require-safety",
            "generate-submit",
            "generate-results",
            "generate-results-empty",
            "generate-loading",
            "generate-error",
            "generate-save-drafts",
            "generate-clear-results",
            "generate-reset",
            "drafts-view",
            "drafts-list",
        ]
        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_content_goal_options_present(self):
        for option_value in (
            "get_leads",
            "show_transformation",
            "educate_customer",
            "promote_offer",
            "build_trust",
            "announce_availability",
            "repurpose_old_content",
            "behind_the_scenes",
            "seasonal_reminder",
        ):
            with self.subTest(goal=option_value):
                self.assertIn(f'value="{option_value}"', self.html)

    def test_content_angle_options_present(self):
        for option_value in (
            "before_after",
            "educational",
            "behind_the_scenes",
            "testimonial",
            "promotion",
            "faq",
            "trust_builder",
            "transformation",
            "seasonal",
            "other",
        ):
            with self.subTest(angle=option_value):
                self.assertIn(f'value="{option_value}"', self.html)

    def test_temporary_adapter_callout_and_todo_present(self):
        self.assertIn("Temporary browser generation adapter", self.html)
        self.assertIn("TODO", self.script)
        self.assertIn("localStorage", self.script)
        self.assertIn("local-social-ai-manager.drafts", self.script)

    def test_routing_includes_new_routes(self):
        # settings.js owns hash routing for the static demo.
        self.assertIn('"generate"', self.settings_script)
        self.assertIn('"drafts"', self.settings_script)

    def test_safety_review_logic_mirrors_python_module(self):
        # The browser mirror must use the same flag vocabulary as
        # scripts/ai/safety.py so backend wiring later does not surprise users.
        for flag in (
            "brand_mismatch",
            "unsupported_guarantee",
            "fake_testimonial",
            "unsupported_claim",
            "aggressive_language",
            "platform_policy_risk",
            "missing_approval",
            "emergency_pause_conflict",
        ):
            with self.subTest(flag=flag):
                self.assertIn(flag, self.script)

    def test_save_to_drafts_does_not_persist_until_clicked(self):
        # Persistence happens inside handleSaveToDrafts (button handler), not
        # inside handleGenerate. Verify the structure rather than triggering JS.
        self.assertIn("handleSaveToDrafts", self.script)
        self.assertIn("persistDrafts", self.script)
        # generate handler must never persist on its own.
        generate_handler_idx = self.script.find("function handleGenerate")
        save_handler_idx = self.script.find("function handleSaveToDrafts")
        self.assertGreaterEqual(generate_handler_idx, 0)
        self.assertGreaterEqual(save_handler_idx, 0)
        between = self.script[generate_handler_idx:save_handler_idx]
        self.assertNotIn("persistDrafts(", between)
        self.assertNotIn(f"setItem({chr(39)}{chr(39)}", between)

    def test_required_platforms_present(self):
        for platform in (
            "instagram",
            "facebook",
            "threads",
            "tiktok",
            "youtube",
            "linkedin",
            "x",
        ):
            with self.subTest(platform=platform):
                self.assertIn(f'"{platform}"', self.script)

    def test_empty_loading_error_states_present(self):
        self.assertIn('id="generate-loading"', self.html)
        self.assertIn('id="generate-error"', self.html)
        self.assertIn('id="generate-results-empty"', self.html)
        self.assertIn('id="generate-brand-empty"', self.html)


if __name__ == "__main__":
    unittest.main()
