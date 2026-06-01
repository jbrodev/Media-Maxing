from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "settings.js"
WEB_STYLES = REPO_ROOT / "apps" / "web" / "styles.css"


class WebSocialSetupScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_SETTINGS.read_text(encoding="utf-8")
        self.styles = WEB_STYLES.read_text(encoding="utf-8")

    def test_social_setup_route_has_required_screen_elements(self):
        required_ids = [
            "social-setup-view",
            "social-setup-summary",
            "social-setup-platform-list",
            "social-setup-detail-panel",
            "social-setup-env-list",
            "social-setup-checklist",
            "social-setup-docs-links",
            "social-setup-mock-test",
            "social-setup-copy-redirect",
            "social-setup-later",
            "social-setup-action-message",
            "social-setup-action-error",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_social_setup_nav_and_safety_copy_are_present(self):
        self.assertIn('href="#setup"', self.html)
        self.assertIn("Social Integration Setup", self.html)
        self.assertIn("Mock mode vs real mode", self.html)
        self.assertIn("Publishing disabled", self.html)
        self.assertIn("I will add API keys later", self.html)

        for label in ("Facebook", "Instagram", "Threads", "YouTube", "TikTok", "LinkedIn", "X"):
            with self.subTest(label=label):
                self.assertIn(label, self.html + self.script)

    def test_social_setup_script_contains_validation_and_mock_handlers(self):
        for name in (
            "renderSocialSetup",
            "validateIntegrationSetupConfig",
            "normalizeServerIntegrationSetup",
            "setupPlatformStatus",
            "maskSetupValue",
            "runSetupMockConnectionTest",
            "copySetupRedirectUri",
            "selectSetupPlatform",
        ):
            with self.subTest(name=name):
                self.assertIn(f"function {name}", self.script)

        self.assertIn('"setup"', self.script)
        self.assertIn("META_CLIENT_SECRET", self.script)
        self.assertIn("GOOGLE_CLIENT_SECRET", self.script)
        self.assertIn("YouTube Data API", self.script)
        self.assertIn("TIKTOK_CLIENT_SECRET", self.script)
        self.assertIn("TikTok developer app", self.script)
        self.assertIn("Content posting review", self.script)
        self.assertIn("LINKEDIN_CLIENT_SECRET", self.script)
        self.assertIn("LinkedIn Developer app", self.script)
        self.assertIn("Product access", self.script)
        self.assertIn("Organization/page access", self.script)
        self.assertIn("X_CLIENT_SECRET", self.script)
        self.assertIn("X developer app", self.script)
        self.assertIn("API access/pricing", self.script)
        self.assertIn("Configured, hidden", self.script)
        self.assertIn("realPublishingAvailable: false", self.script)
        self.assertIn("snapshot?.integrationSetup", self.script)

    def test_social_setup_surface_does_not_show_secret_values_or_token_fields(self):
        browser_surface = self.html + self.script
        forbidden = (
            "accessToken",
            "refreshToken",
            "authorizationCode",
            "clientSecret",
            "encryptedAccessToken",
            "encryptedRefreshToken",
            "demo-secret",
            "fake-secret",
        )

        for token_field in forbidden:
            with self.subTest(token_field=token_field):
                self.assertNotIn(token_field, browser_surface)

    def test_social_setup_css_classes_present(self):
        for class_name in (
            ".social-setup-layout",
            ".social-setup-summary-grid",
            ".social-setup-platform-list",
            ".social-setup-card",
            ".social-setup-detail-panel",
            ".setup-env-list",
            ".setup-checklist",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.styles)


if __name__ == "__main__":
    unittest.main()
