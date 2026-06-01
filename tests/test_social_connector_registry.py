from __future__ import annotations

import unittest

from scripts.connectors.registry import (
    SUPPORTED_SOCIAL_PLATFORMS,
    ConnectorRegistryError,
    get_connector,
    list_connector_metadata,
    list_mock_only_platforms,
    list_platform_capabilities,
    list_platform_setup_status,
)
from scripts.connectors.types import PlatformFeatureStatus


class SocialConnectorRegistryTest(unittest.TestCase):
    def test_all_supported_platform_ids_are_registered(self):
        self.assertEqual(
            SUPPORTED_SOCIAL_PLATFORMS,
            ("facebook", "instagram", "threads", "youtube", "tiktok", "linkedin", "x"),
        )
        self.assertEqual(
            {metadata.platform for metadata in list_connector_metadata()},
            set(SUPPORTED_SOCIAL_PLATFORMS),
        )

    def test_each_connector_returns_safe_capabilities(self):
        for platform in SUPPORTED_SOCIAL_PLATFORMS:
            connector = get_connector(platform)
            capabilities = connector.getCapabilities()

            self.assertEqual(connector.getPlatform(), platform)
            self.assertTrue(capabilities.supportsManualExportFallback)
            self.assertFalse(capabilities.canPublishText)
            self.assertFalse(capabilities.canPublishImage)
            self.assertFalse(capabilities.canPublishVideo)
            self.assertFalse(capabilities.canPublishCarousel)
            self.assertFalse(capabilities.canReplyToComments)

    def test_unknown_platform_returns_useful_error(self):
        with self.assertRaisesRegex(ConnectorRegistryError, "Unsupported social platform"):
            get_connector("myspace")

    def test_registry_lists_capabilities_and_setup_status(self):
        capabilities = list_platform_capabilities()
        setup_status = list_platform_setup_status()

        self.assertEqual(set(capabilities), set(SUPPORTED_SOCIAL_PLATFORMS))
        self.assertEqual(set(setup_status), set(SUPPORTED_SOCIAL_PLATFORMS))
        self.assertEqual(setup_status["facebook"], PlatformFeatureStatus.MOCK_ONLY.value)
        self.assertEqual(setup_status["instagram"], PlatformFeatureStatus.MOCK_ONLY.value)
        self.assertEqual(setup_status["threads"], PlatformFeatureStatus.MOCK_ONLY.value)
        self.assertEqual(setup_status["youtube"], PlatformFeatureStatus.MOCK_ONLY.value)

    def test_registry_identifies_mock_only_platforms(self):
        self.assertEqual(
            set(list_mock_only_platforms()),
            {"facebook", "instagram", "threads", "youtube", "tiktok", "linkedin", "x"},
        )

    def test_default_publish_action_is_disabled_by_policy(self):
        connector = get_connector("facebook")

        result = connector.publishText({"caption": "This must not publish."})

        self.assertFalse(result.success)
        self.assertEqual(result.status, "disabled_by_policy")
        self.assertIn("disabled", result.message.lower())


if __name__ == "__main__":
    unittest.main()
