from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from scripts.connectors.registry import get_connector
from scripts.connectors.meta.config import load_meta_config
from scripts.connectors.meta.errors import normalize_meta_error
from scripts.connectors.types import OAuthStartRequest


EMPTY_META_ENV = {
    "META_CLIENT_ID": "",
    "META_CLIENT_SECRET": "",
    "META_REDIRECT_URI": "",
    "META_GRAPH_API_VERSION": "",
    "META_ENABLE_REAL_OAUTH": "",
    "META_ENABLE_REAL_PUBLISHING": "",
    "INTEGRATIONS_MODE": "",
}


class MetaConnectorScaffoldTest(unittest.TestCase):
    def test_missing_config_returns_setup_required_for_real_oauth_start(self):
        with patch.dict(os.environ, EMPTY_META_ENV, clear=False):
            connector = get_connector("facebook")

            result = connector.buildAuthorizationUrl(
                OAuthStartRequest(
                    platform="facebook",
                    redirectUri="http://localhost:8000/api/connect/facebook/callback",
                    metadata={"mode": "real"},
                )
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "setup_required")
        self.assertIn("META_CLIENT_ID", result.message)
        self.assertNotIn("META_CLIENT_SECRET=", result.message)

    def test_mock_mode_builds_safe_mock_authorization_url_without_credentials(self):
        with patch.dict(os.environ, EMPTY_META_ENV | {"INTEGRATIONS_MODE": "mock"}, clear=False):
            connector = get_connector("instagram")

            result = connector.buildAuthorizationUrl(
                OAuthStartRequest(
                    platform="instagram",
                    redirectUri="http://localhost:8000/api/connect/instagram/callback",
                    requestedScopes=("instagram_basic", "pages_show_list"),
                    metadata={"state": "state-for-test", "mode": "mock"},
                )
            )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "mock_redirect_ready")
        self.assertIn("mock-oauth", result.authorizationUrl or "")
        self.assertIn("instagram", result.authorizationUrl or "")
        self.assertIn("state-for-test", result.authorizationUrl or "")

    def test_meta_config_loader_uses_safe_defaults(self):
        with patch.dict(os.environ, EMPTY_META_ENV, clear=False):
            config = load_meta_config()

        self.assertFalse(config.clientIdConfigured)
        self.assertFalse(config.clientSecretConfigured)
        self.assertFalse(config.redirectUriConfigured)
        self.assertFalse(config.realOAuthEnabled)
        self.assertFalse(config.realPublishingEnabled)
        self.assertIn("META_CLIENT_ID", config.missingConfigKeys)

    def test_meta_connectors_expose_setup_instructions_and_capabilities(self):
        for platform in ("facebook", "instagram", "threads"):
            with self.subTest(platform=platform):
                connector = get_connector(platform)
                capabilities = connector.getCapabilities()
                instructions = "\n".join(connector.getSetupInstructions())

                self.assertTrue(capabilities.canConnect)
                self.assertTrue(capabilities.supportsOAuth)
                self.assertTrue(capabilities.supportsManualExportFallback)
                self.assertFalse(capabilities.canPublishText)
                self.assertFalse(capabilities.canPublishImage)
                self.assertIn("App review", instructions)
                self.assertIn("Publishing is disabled", instructions)

    def test_publishing_stays_disabled_even_when_meta_flag_is_true(self):
        with patch.dict(os.environ, EMPTY_META_ENV | {"META_ENABLE_REAL_PUBLISHING": "true"}, clear=False):
            connector = get_connector("threads")

            result = connector.publishText({"caption": "Do not publish this."})

        self.assertFalse(result.success)
        self.assertEqual(result.status, "disabled_by_policy")
        self.assertFalse(result.metadata["realPublishingEnabled"])

    def test_meta_error_normalization_redacts_raw_details(self):
        error = normalize_meta_error(
            "facebook",
            {
                "error": {
                    "code": 190,
                    "message": "Invalid OAuth access token: secret-token-value",
                    "type": "OAuthException",
                }
            },
        )

        self.assertEqual(error.code, "meta_190")
        self.assertTrue(error.requiresReauth)
        self.assertIn("[redacted]", error.rawErrorRedacted)
        self.assertNotIn("secret-token-value", error.rawErrorRedacted)


if __name__ == "__main__":
    unittest.main()
