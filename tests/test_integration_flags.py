import json
import tempfile
import unittest

from scripts.services.integration_flags import (
    IntegrationMode,
    IntegrationStatus,
    NetworkSafetyMode,
    validate_integration_feature_flags,
)


class IntegrationFeatureFlagsTest(unittest.TestCase):
    def test_no_env_vars_returns_safe_mock_state(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_integration_feature_flags(
                {
                    "APP_ENV": "development",
                    "LOCAL_DATA_DIR": temp_dir,
                }
            )

        self.assertEqual(result.integrationsMode, IntegrationMode.MOCK.value)
        self.assertEqual(result.networkSafetyMode, NetworkSafetyMode.MOCK.value)
        self.assertFalse(result.realPublishingAvailable)
        self.assertEqual(result.platforms["facebook"].status, IntegrationStatus.MOCK_READY.value)
        self.assertEqual(result.platforms["youtube"].status, IntegrationStatus.MOCK_READY.value)

    def test_real_oauth_without_client_secret_reports_missing_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_integration_feature_flags(
                {
                    "APP_ENV": "development",
                    "LOCAL_DATA_DIR": temp_dir,
                    "INTEGRATIONS_MODE": "real_oauth",
                    "ENABLE_REAL_OAUTH": "true",
                    "ENABLE_REAL_NETWORK_CALLS": "true",
                    "META_ENABLE_REAL_OAUTH": "true",
                    "META_CLIENT_ID": "fake-client-id",
                    "META_REDIRECT_URI": "http://localhost:8000/api/connect/facebook/callback",
                }
            )

        facebook = result.platforms["facebook"]
        self.assertEqual(facebook.status, IntegrationStatus.MISSING_CONFIG.value)
        self.assertIn("META_CLIENT_SECRET", facebook.missingRequiredEnvVars)
        self.assertFalse(facebook.realOAuthAvailable)

    def test_real_oauth_with_fake_credentials_is_ready_without_exposing_secrets(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_integration_feature_flags(
                {
                    "APP_ENV": "development",
                    "LOCAL_DATA_DIR": temp_dir,
                    "INTEGRATIONS_MODE": "real_oauth",
                    "ENABLE_REAL_OAUTH": "true",
                    "ENABLE_REAL_NETWORK_CALLS": "true",
                    "TOKEN_STORAGE_MODE": "placeholder_not_stored",
                    "META_ENABLE_REAL_OAUTH": "true",
                    "META_CLIENT_ID": "fake-client-id",
                    "META_CLIENT_SECRET": "fake-client-secret-must-not-leak",
                    "META_REDIRECT_URI": "http://localhost:8000/api/connect/facebook/callback",
                }
            )

        facebook = result.platforms["facebook"]
        self.assertEqual(facebook.status, IntegrationStatus.REAL_OAUTH_READY.value)
        self.assertTrue(facebook.realOAuthAvailable)
        self.assertFalse(facebook.realPublishingAvailable)

        serialized = json.dumps(result.to_frontend_safe_dict())
        self.assertNotIn("fake-client-secret-must-not-leak", serialized)
        self.assertIn("Configured, hidden", serialized)

    def test_real_oauth_ready_but_network_disabled_is_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = validate_integration_feature_flags(
                {
                    "APP_ENV": "development",
                    "LOCAL_DATA_DIR": temp_dir,
                    "INTEGRATIONS_MODE": "real_oauth",
                    "ENABLE_REAL_OAUTH": "true",
                    "ENABLE_REAL_NETWORK_CALLS": "false",
                    "META_ENABLE_REAL_OAUTH": "true",
                    "META_CLIENT_ID": "fake-client-id",
                    "META_CLIENT_SECRET": "fake-client-secret",
                    "META_REDIRECT_URI": "http://localhost:8000/api/connect/facebook/callback",
                }
            )

        self.assertEqual(
            result.platforms["facebook"].status,
            IntegrationStatus.REAL_NETWORK_DISABLED.value,
        )
        self.assertFalse(result.platforms["facebook"].realOAuthAvailable)

    def test_real_publishing_flag_is_warned_and_blocked(self):
        result = validate_integration_feature_flags(
            {
                "APP_ENV": "development",
                "INTEGRATIONS_MODE": "mock",
                "ENABLE_REAL_PUBLISHING": "true",
                "META_ENABLE_REAL_PUBLISHING": "true",
            }
        )

        self.assertFalse(result.realPublishingAvailable)
        self.assertIn("real_publishing_disabled_by_policy", result.warningCodes)
        self.assertIn(
            "real_publishing_disabled_by_policy",
            result.platforms["facebook"].warningCodes,
        )

    def test_invalid_values_are_machine_readable_errors(self):
        result = validate_integration_feature_flags(
            {
                "APP_ENV": "development",
                "INTEGRATIONS_MODE": "real",
                "ENABLE_REAL_OAUTH": "sometimes",
                "TOKEN_STORAGE_MODE": "plain_text",
            }
        )

        self.assertIn("invalid_integrations_mode", result.errorCodes)
        self.assertIn("invalid_boolean_ENABLE_REAL_OAUTH", result.errorCodes)
        self.assertIn("invalid_token_storage_mode", result.errorCodes)


if __name__ == "__main__":
    unittest.main()
