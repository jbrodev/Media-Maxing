from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SETTINGS = REPO_ROOT / "apps" / "web" / "settings.js"
WEB_STYLES = REPO_ROOT / "apps" / "web" / "styles.css"


class WebConnectedAccountsScreenTest(unittest.TestCase):
    def setUp(self) -> None:
        self.html = WEB_INDEX.read_text(encoding="utf-8")
        self.script = WEB_SETTINGS.read_text(encoding="utf-8")
        self.styles = WEB_STYLES.read_text(encoding="utf-8")

    def test_connected_accounts_route_has_required_screen_elements(self):
        required_ids = [
            "connected-view",
            "connected-platform-grid",
            "connected-account-list",
            "connected-loading-state",
            "connected-error-state",
            "connected-empty-state",
            "connected-action-message",
            "connected-action-error",
            "connected-setup-panel",
            "connected-audit-list",
        ]

        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.html)

    def test_platform_cards_and_safety_copy_are_present(self):
        self.assertIn('href="#connected"', self.html)
        self.assertIn("Connected Accounts", self.html)
        self.assertIn("real publishing is not enabled", self.html.lower())
        self.assertIn("mock/demo", self.html.lower())

        for label in ("Facebook", "Instagram", "Threads", "YouTube", "TikTok", "LinkedIn", "X"):
            with self.subTest(label=label):
                self.assertIn(label, self.html + self.script)

    def test_connected_accounts_script_contains_mock_flow_handlers(self):
        self.assertIn('"connected"', self.script)
        for name in (
            "renderConnectedAccounts",
            "mockConnectPlatform",
            "disconnectConnectedAccount",
            "showConnectedSetupInstructions",
            "loadConnectedAccounts",
            "saveConnectedAccounts",
            "appendConnectorAuditLog",
            "safeConnectedAccount",
            "validateConnectedAccount",
        ):
            with self.subTest(name=name):
                self.assertIn(f"function {name}", self.script)

        self.assertIn("placeholder_not_stored", self.script)
        self.assertIn("Publishing disabled in this build", self.script)
        self.assertIn("No real API was called", self.script)
        self.assertIn("Check connection", self.script)
        self.assertIn("healthStatus", self.script)
        self.assertIn("lastValidatedAt", self.script)
        self.assertIn('["facebook", "instagram", "youtube", "tiktok", "linkedin", "x"]', self.script)
        self.assertNotIn("enabled first for Facebook, Instagram, and YouTube", self.script)

    def test_browser_ui_does_not_reference_token_fields(self):
        browser_surface = self.html + self.script
        forbidden = (
            "accessToken",
            "refreshToken",
            "authorizationCode",
            "clientSecret",
            "encryptedAccessToken",
            "encryptedRefreshToken",
        )

        for token_field in forbidden:
            with self.subTest(token_field=token_field):
                self.assertNotIn(token_field, browser_surface)

    def test_connected_accounts_css_classes_present(self):
        for class_name in (
            ".connected-platform-grid",
            ".connected-platform-card",
            ".connected-account-list",
            ".connected-account-card",
            ".connected-setup-panel",
            ".connector-audit-list",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, self.styles)


if __name__ == "__main__":
    unittest.main()
