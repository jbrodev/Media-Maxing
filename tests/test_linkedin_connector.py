from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from scripts.connectors.registry import get_connector, list_mock_only_platforms, list_platform_setup_status
from scripts.connectors.types import OAuthStartRequest, PlatformFeatureStatus
from scripts.db.init_db import initialize_database
from scripts.services.oauth_flow import OAuthFlowService
from scripts.services.platform_http_client import NetworkSafetyMode, PlatformHttpClientConfig


EMPTY_LINKEDIN_ENV = {
    "LINKEDIN_CLIENT_ID": "",
    "LINKEDIN_CLIENT_SECRET": "",
    "LINKEDIN_REDIRECT_URI": "",
    "LINKEDIN_ENABLE_REAL_OAUTH": "",
    "LINKEDIN_ENABLE_REAL_PUBLISHING": "",
    "INTEGRATIONS_MODE": "",
}


class LinkedInConnectorScaffoldTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        return db_path

    def test_linkedin_connector_exposes_safe_capabilities_and_setup(self):
        connector = get_connector("linkedin")
        capabilities = connector.getCapabilities()
        instructions = "\n".join(connector.getSetupInstructions())
        scope_ids = [scope.id for scope in connector.getRequiredScopes()]

        self.assertEqual(connector.getPlatform(), "linkedin")
        self.assertEqual(connector.featureStatus, PlatformFeatureStatus.MOCK_ONLY)
        self.assertTrue(capabilities.canConnect)
        self.assertTrue(capabilities.supportsOAuth)
        self.assertTrue(capabilities.canReadProfile)
        self.assertTrue(capabilities.supportsManualExportFallback)
        self.assertTrue(capabilities.requiresAppReview)
        self.assertFalse(capabilities.canPublishText)
        self.assertFalse(capabilities.canPublishImage)
        self.assertFalse(capabilities.canPublishVideo)
        self.assertFalse(capabilities.canScheduleNatively)
        self.assertIn("openid", scope_ids)
        self.assertIn("w_member_social", scope_ids)
        self.assertIn("LinkedIn Developer app", instructions)
        self.assertIn("Product access", instructions)
        self.assertIn("Organization/page access", instructions)
        self.assertIn("Publishing is disabled", instructions)

    def test_missing_linkedin_config_returns_setup_required_for_real_oauth(self):
        with patch.dict(os.environ, EMPTY_LINKEDIN_ENV, clear=False):
            connector = get_connector("linkedin")

            result = connector.buildAuthorizationUrl(
                OAuthStartRequest(
                    platform="linkedin",
                    redirectUri="http://localhost:8000/api/connect/linkedin/callback",
                    metadata={"mode": "real"},
                )
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "setup_required")
        self.assertIn("LINKEDIN_CLIENT_ID", result.message)
        self.assertIn("LINKEDIN_CLIENT_SECRET", result.message)
        self.assertNotIn("demo-secret", result.message)

    def test_mock_mode_builds_linkedin_authorization_url_without_credentials(self):
        with patch.dict(os.environ, EMPTY_LINKEDIN_ENV | {"INTEGRATIONS_MODE": "mock"}, clear=False):
            connector = get_connector("linkedin")

            result = connector.buildAuthorizationUrl(
                OAuthStartRequest(
                    platform="linkedin",
                    redirectUri="http://localhost:8000/api/connect/linkedin/callback",
                    requestedScopes=("openid", "profile"),
                    metadata={"state": "linkedin-state-for-test", "mode": "mock"},
                )
            )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "mock_redirect_ready")
        self.assertIn("mock-oauth", result.authorizationUrl or "")
        self.assertIn("linkedin", result.authorizationUrl or "")
        self.assertIn("linkedin-state-for-test", result.authorizationUrl or "")

    def test_publishing_stays_disabled_by_policy(self):
        connector = get_connector("linkedin")

        text_result = connector.publishText({"caption": "Do not publish"})
        image_result = connector.publishImage({"caption": "Do not publish"})
        video_result = connector.publishVideo({"caption": "Do not publish"})

        for result in (text_result, image_result, video_result):
            with self.subTest(result=result):
                self.assertFalse(result.success)
                self.assertEqual(result.status, "disabled_by_policy")
                self.assertFalse(result.metadata["realPublishingEnabled"])
                self.assertIn("publishing", result.message.lower())

    def test_mock_oauth_creates_safe_linkedin_account(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="linkedin",
            redirect_uri="http://localhost:8000/api/connect/linkedin/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = parse_qs(urlparse(start.authorizationUrl or "").query)["state"][0]

        callback = service.handle_callback(
            platform="linkedin",
            state=state,
            code="mock-linkedin-code",
            now="2026-05-28T12:01:00Z",
        )

        self.assertTrue(callback.success)
        self.assertEqual(callback.status, "mock_connected")
        self.assertEqual(callback.account["platform"], "linkedin")
        self.assertEqual(callback.account["accountType"], "organization")
        self.assertNotIn("accessToken", callback.account)
        self.assertNotIn("refreshToken", callback.account)

    def test_linkedin_validate_connection_returns_mock_health(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="linkedin",
            redirect_uri="http://localhost:8000/api/connect/linkedin/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = parse_qs(urlparse(start.authorizationUrl or "").query)["state"][0]
        callback = service.handle_callback(
            platform="linkedin",
            state=state,
            code="mock-linkedin-code",
            now="2026-05-28T12:01:00Z",
        )
        account_id = callback.account["id"]

        result = get_connector("linkedin").validateConnection(
            account_id,
            database_path=db_path,
            http_client_config=PlatformHttpClientConfig(
                provider="linkedin",
                platform="linkedin",
                safetyMode=NetworkSafetyMode.MOCK,
            ),
            now="2026-05-28T12:30:00Z",
        )

        self.assertIn(result.status, {"healthy", "limited"})
        self.assertEqual(result.socialAccountId, account_id)
        self.assertEqual(result.accountType, "organization")
        self.assertEqual(result.connectionStatus, "connected")
        with closing(sqlite3.connect(db_path)) as connection:
            last_validated = connection.execute(
                "SELECT last_validated_at FROM social_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()[0]
        self.assertEqual(last_validated, "2026-05-28T12:30:00Z")

    def test_registry_treats_linkedin_as_mock_only_connector(self):
        setup_status = list_platform_setup_status()

        self.assertEqual(setup_status["linkedin"], PlatformFeatureStatus.MOCK_ONLY.value)
        self.assertIn("linkedin", list_mock_only_platforms())


if __name__ == "__main__":
    unittest.main()
