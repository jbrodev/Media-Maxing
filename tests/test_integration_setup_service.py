import json
import tempfile
from pathlib import Path
import unittest

from scripts.services.integration_setup import (
    mask_config_value,
    validate_social_integration_setup,
)


class IntegrationSetupServiceTest(unittest.TestCase):
    def test_no_platform_env_vars_returns_mock_only_and_missing_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_social_integration_setup(
                {
                    "APP_ENV": "development",
                    "LOCAL_DATA_DIR": temp_dir,
                    "INTEGRATIONS_MODE": "mock",
                    "ENABLE_REAL_OAUTH": "false",
                    "ENABLE_REAL_PUBLISHING": "false",
                    "TOKEN_STORAGE_MODE": "placeholder_not_stored",
                }
            )

        self.assertEqual(result.appEnvironment, "development")
        self.assertEqual(result.integrationsMode, "mock")
        self.assertTrue(result.localDataDirectoryExists)
        self.assertFalse(result.realPublishingEnabled)
        self.assertFalse(result.realPublishingAvailable)
        self.assertEqual(len(result.platforms), 7)
        self.assertEqual(result.platforms["facebook"].status, "mock_ready")
        self.assertIn("META_CLIENT_ID", result.platforms["facebook"].missingRequiredEnvVars)
        self.assertEqual(result.platforms["youtube"].status, "mock_ready")
        self.assertTrue(result.platforms["facebook"].mockConnectAvailable)
        self.assertFalse(result.platforms["facebook"].realPublishingAvailable)

    def test_fake_meta_env_marks_configured_but_real_publishing_stays_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_social_integration_setup(
                {
                    "APP_ENV": "development",
                    "LOCAL_DATA_DIR": temp_dir,
                    "INTEGRATIONS_MODE": "mock",
                    "ENABLE_REAL_OAUTH": "false",
                    "ENABLE_REAL_PUBLISHING": "false",
                    "TOKEN_STORAGE_MODE": "placeholder_not_stored",
                    "META_CLIENT_ID": "1234567890",
                    "META_CLIENT_SECRET": "placeholder-value-that-must-not-leak",
                    "META_REDIRECT_URI": "http://localhost:8000/api/connect/meta/callback",
                    "META_ENABLE_REAL_OAUTH": "false",
                    "META_ENABLE_REAL_PUBLISHING": "true",
                }
            )

        facebook = result.platforms["facebook"]
        self.assertEqual(facebook.status, "mock_ready")
        self.assertEqual(facebook.redirectUri, "http://localhost:8000/api/connect/meta/callback")
        self.assertEqual(facebook.envVars["META_CLIENT_SECRET"].displayValue, "Configured, hidden")
        self.assertFalse(facebook.realPublishingAvailable)
        self.assertFalse(result.realPublishingAvailable)

        serialized = json.dumps(result.to_dict())
        self.assertNotIn("placeholder-value-that-must-not-leak", serialized)

    def test_unknown_app_env_and_token_storage_are_reported_as_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_social_integration_setup(
                {
                    "APP_ENV": "banana",
                    "LOCAL_DATA_DIR": str(Path(temp_dir) / "missing"),
                    "INTEGRATIONS_MODE": "mock",
                    "TOKEN_STORAGE_MODE": "plain_text",
                    "ENABLE_REAL_PUBLISHING": "false",
                }
            )

        self.assertIn("unknown_app_environment", result.errorCodes)
        self.assertIn("invalid_token_storage_mode", result.errorCodes)
        self.assertIn("missing_local_data_directory", result.warningCodes)

    def test_real_oauth_ready_status_is_exposed_to_setup_wizard(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_social_integration_setup(
                {
                    "APP_ENV": "development",
                    "LOCAL_DATA_DIR": temp_dir,
                    "INTEGRATIONS_MODE": "real_oauth",
                    "ENABLE_REAL_OAUTH": "true",
                    "ENABLE_REAL_NETWORK_CALLS": "true",
                    "TOKEN_STORAGE_MODE": "placeholder_not_stored",
                    "META_ENABLE_REAL_OAUTH": "true",
                    "META_CLIENT_ID": "fake-client",
                    "META_CLIENT_SECRET": "fake-secret",
                    "META_REDIRECT_URI": "http://localhost:8000/api/connect/facebook/callback",
                }
            )

        self.assertEqual(result.platforms["facebook"].status, "real_oauth_ready")
        self.assertTrue(result.platforms["facebook"].realOAuthAvailable)

    def test_mask_config_value_never_returns_secret_value(self):
        self.assertEqual(mask_config_value("CLIENT_SECRET", "super-sensitive"), "Configured, hidden")
        self.assertEqual(mask_config_value("CLIENT_ID", "abcdef123456"), "ab...56")
        self.assertEqual(mask_config_value("REDIRECT_URI", "http://localhost/callback"), "http://localhost/callback")
        self.assertEqual(mask_config_value("CLIENT_ID", ""), "Not configured")


if __name__ == "__main__":
    unittest.main()
