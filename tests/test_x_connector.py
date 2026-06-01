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


EMPTY_X_ENV = {
    "X_CLIENT_ID": "",
    "X_CLIENT_SECRET": "",
    "X_REDIRECT_URI": "",
    "X_ENABLE_REAL_OAUTH": "",
    "X_ENABLE_REAL_PUBLISHING": "",
    "INTEGRATIONS_MODE": "",
}


class XConnectorScaffoldTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        return db_path

    def test_x_connector_exposes_safe_capabilities_and_setup(self):
        connector = get_connector("x")
        capabilities = connector.getCapabilities()
        instructions = "\n".join(connector.getSetupInstructions())
        scope_ids = [scope.id for scope in connector.getRequiredScopes()]

        self.assertEqual(connector.getPlatform(), "x")
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
        self.assertIn("users.read", scope_ids)
        self.assertIn("tweet.write", scope_ids)
        self.assertIn("X developer app", instructions)
        self.assertIn("API access/pricing", instructions)
        self.assertIn("Publishing is disabled", instructions)

    def test_missing_x_config_returns_setup_required_for_real_oauth(self):
        with patch.dict(os.environ, EMPTY_X_ENV, clear=False):
            connector = get_connector("x")

            result = connector.buildAuthorizationUrl(
                OAuthStartRequest(
                    platform="x",
                    redirectUri="http://localhost:8000/api/connect/x/callback",
                    metadata={"mode": "real"},
                )
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "setup_required")
        self.assertIn("X_CLIENT_ID", result.message)
        self.assertIn("X_CLIENT_SECRET", result.message)
        self.assertNotIn("demo-secret", result.message)

    def test_mock_mode_builds_x_authorization_url_without_credentials(self):
        with patch.dict(os.environ, EMPTY_X_ENV | {"INTEGRATIONS_MODE": "mock"}, clear=False):
            connector = get_connector("x")

            result = connector.buildAuthorizationUrl(
                OAuthStartRequest(
                    platform="x",
                    redirectUri="http://localhost:8000/api/connect/x/callback",
                    requestedScopes=("users.read",),
                    metadata={"state": "x-state-for-test", "mode": "mock"},
                )
            )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "mock_redirect_ready")
        self.assertIn("mock-oauth", result.authorizationUrl or "")
        self.assertIn("x-state-for-test", result.authorizationUrl or "")

    def test_publishing_stays_disabled_by_policy(self):
        connector = get_connector("x")

        text_result = connector.publishText({"caption": "Do not publish"})
        image_result = connector.publishImage({"caption": "Do not publish"})
        video_result = connector.publishVideo({"caption": "Do not publish"})

        for result in (text_result, image_result, video_result):
            with self.subTest(result=result):
                self.assertFalse(result.success)
                self.assertEqual(result.status, "disabled_by_policy")
                self.assertFalse(result.metadata["realPublishingEnabled"])
                self.assertIn("publishing", result.message.lower())

    def test_mock_oauth_creates_safe_x_account(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="x",
            redirect_uri="http://localhost:8000/api/connect/x/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = parse_qs(urlparse(start.authorizationUrl or "").query)["state"][0]

        callback = service.handle_callback(
            platform="x",
            state=state,
            code="mock-x-code",
            now="2026-05-28T12:01:00Z",
        )

        self.assertTrue(callback.success)
        self.assertEqual(callback.status, "mock_connected")
        self.assertEqual(callback.account["platform"], "x")
        self.assertEqual(callback.account["accountType"], "unknown")
        self.assertNotIn("accessToken", callback.account)
        self.assertNotIn("refreshToken", callback.account)

    def test_x_validate_connection_returns_mock_health(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="x",
            redirect_uri="http://localhost:8000/api/connect/x/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = parse_qs(urlparse(start.authorizationUrl or "").query)["state"][0]
        callback = service.handle_callback(
            platform="x",
            state=state,
            code="mock-x-code",
            now="2026-05-28T12:01:00Z",
        )
        account_id = callback.account["id"]

        result = get_connector("x").validateConnection(
            account_id,
            database_path=db_path,
            http_client_config=PlatformHttpClientConfig(
                provider="x",
                platform="x",
                safetyMode=NetworkSafetyMode.MOCK,
            ),
            now="2026-05-28T12:30:00Z",
        )

        self.assertIn(result.status, {"healthy", "limited"})
        self.assertEqual(result.socialAccountId, account_id)
        self.assertEqual(result.accountType, "unknown")
        self.assertEqual(result.connectionStatus, "connected")
        with closing(sqlite3.connect(db_path)) as connection:
            last_validated = connection.execute(
                "SELECT last_validated_at FROM social_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()[0]
        self.assertEqual(last_validated, "2026-05-28T12:30:00Z")

    def test_registry_treats_x_as_mock_only_connector(self):
        setup_status = list_platform_setup_status()

        self.assertEqual(setup_status["x"], PlatformFeatureStatus.MOCK_ONLY.value)
        self.assertIn("x", list_mock_only_platforms())


if __name__ == "__main__":
    unittest.main()
