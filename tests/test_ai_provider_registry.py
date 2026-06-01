import os
import unittest
from unittest import mock

from scripts.ai.config import AIProviderConfig
from scripts.ai.providers.base import (
    AIProviderError,
    ProviderConfigurationError,
    ProviderDisabledError,
)
from scripts.ai.providers.mock import MockProvider
from scripts.ai.providers.registry import (
    DEFAULT_PROVIDER_NAME,
    get_provider,
    list_available_providers,
    provider_from_config,
)
from scripts.ai.schemas import (
    AIStructuredGenerationRequest,
    AITextGenerationRequest,
    ContentGenerationInput,
    ContentGenerationOptions,
)


def _minimal_input() -> ContentGenerationInput:
    return ContentGenerationInput(
        brand_profile={
            "id": "brand-test",
            "businessName": "Provider Gate Demo",
            "voice": "Plain and honest.",
            "services": ["sample service"],
            "supportedClaims": ["Sample supported claim."],
            "targetAudience": "demo customers",
        },
        content_goal="build_trust",
        content_angle="trust_builder",
        selected_platforms=["facebook"],
    )


class DefaultProviderTest(unittest.TestCase):
    def test_default_provider_name_is_mock(self):
        self.assertEqual(DEFAULT_PROVIDER_NAME, "mock")

    def test_get_provider_with_no_argument_returns_mock(self):
        provider = get_provider()
        self.assertIsInstance(provider, MockProvider)
        self.assertEqual(provider.name, "mock")

    def test_get_provider_is_case_and_whitespace_tolerant(self):
        provider = get_provider("  MOCK  ")
        self.assertEqual(provider.name, "mock")

    def test_get_provider_rejects_unknown_name(self):
        with self.assertRaises(ProviderConfigurationError):
            get_provider("not-a-real-provider")


class RealProviderGatingTest(unittest.TestCase):
    """Real provider stubs must refuse to generate unless safety gates pass."""

    real_provider_names = ("openai", "anthropic", "local")

    def test_real_providers_disabled_when_environment_is_empty(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            for name in self.real_provider_names:
                with self.subTest(provider=name):
                    provider = get_provider(name)
                    with self.assertRaises(ProviderDisabledError) as raised:
                        provider.generate_bundle(_minimal_input(), ContentGenerationOptions())
                    # The disabled reason should mention INTEGRATIONS_MODE because
                    # that is the first gate checked.
                    self.assertIn("INTEGRATIONS_MODE", str(raised.exception))

    def test_real_provider_blocked_when_network_gate_off(self):
        env = {
            "INTEGRATIONS_MODE": "testing",
            "ENABLE_REAL_NETWORK_CALLS": "false",
            "OPENAI_API_KEY": "test-openai-key-placeholder",
            "ANTHROPIC_API_KEY": "test-anthropic-key-placeholder",
            "LOCAL_AI_BASE_URL": "http://localhost:11434",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            for name in self.real_provider_names:
                with self.subTest(provider=name):
                    with self.assertRaises(ProviderDisabledError) as raised:
                        get_provider(name).generate_bundle(
                            _minimal_input(), ContentGenerationOptions()
                        )
                    self.assertIn("ENABLE_REAL_NETWORK_CALLS", str(raised.exception))

    def test_real_provider_blocked_when_key_missing(self):
        env = {
            "INTEGRATIONS_MODE": "testing",
            "ENABLE_REAL_NETWORK_CALLS": "true",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            for name in self.real_provider_names:
                with self.subTest(provider=name):
                    with self.assertRaises(ProviderDisabledError) as raised:
                        get_provider(name).generate_bundle(
                            _minimal_input(), ContentGenerationOptions()
                        )
                    self.assertIn("empty", str(raised.exception).lower())

    def test_real_provider_remains_disabled_even_when_all_gates_pass(self):
        """Batch 3 keeps real provider calls off even when gates allow them.

        The stub adapter raises ProviderDisabledError with the
        "not yet implemented" message to make this policy explicit.
        """
        env = {
            "INTEGRATIONS_MODE": "testing",
            "ENABLE_REAL_NETWORK_CALLS": "true",
            "OPENAI_API_KEY": "test-openai-key-placeholder",
            "ANTHROPIC_API_KEY": "test-anthropic-key-placeholder",
            "LOCAL_AI_BASE_URL": "http://localhost:11434",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            for name in ("openai", "anthropic", "local"):
                with self.subTest(provider=name):
                    with self.assertRaises(ProviderDisabledError) as raised:
                        get_provider(name).generate_bundle(
                            _minimal_input(), ContentGenerationOptions()
                        )
                    self.assertIn("not yet implemented", str(raised.exception))


class RealProviderRaisesOnAllPrimitivesTest(unittest.TestCase):
    """Every generate_* method must refuse to run without safety gates."""

    def test_each_primitive_raises_provider_disabled_error(self):
        text_request = AITextGenerationRequest(prompt="hello")
        structured_request = AIStructuredGenerationRequest(
            prompt="hello", schema_name="platform_post_draft"
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            for name in ("openai", "anthropic", "local"):
                provider = get_provider(name)
                with self.subTest(provider=name, method="generate_text"):
                    with self.assertRaises(ProviderDisabledError):
                        provider.generate_text(text_request)
                with self.subTest(provider=name, method="generate_structured"):
                    with self.assertRaises(ProviderDisabledError):
                        provider.generate_structured(structured_request)
                with self.subTest(provider=name, method="generate_bundle"):
                    with self.assertRaises(ProviderDisabledError):
                        provider.generate_bundle(_minimal_input(), ContentGenerationOptions())

    def test_provider_disabled_error_is_an_ai_provider_error(self):
        # Catch-all callers should be able to use the base class.
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(AIProviderError):
                get_provider("openai").generate_text(AITextGenerationRequest(prompt="x"))


class ProviderFromConfigTest(unittest.TestCase):
    def test_default_config_resolves_to_mock(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            config = AIProviderConfig.from_environment()
        provider = provider_from_config(config)
        self.assertIsInstance(provider, MockProvider)

    def test_explicit_preference_resolves_to_real_stub(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            config = AIProviderConfig.from_environment(provider_preference="openai")
        provider = provider_from_config(config)
        self.assertEqual(provider.name, "openai")
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ProviderDisabledError):
                provider.generate_text(AITextGenerationRequest(prompt="x"))


class ListAvailableProvidersTest(unittest.TestCase):
    def test_mock_listed_and_available(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            entries = list_available_providers()

        by_id = {entry["id"]: entry for entry in entries}
        self.assertIn("mock", by_id)
        self.assertTrue(by_id["mock"]["available"])
        self.assertFalse(by_id["mock"]["requiresNetwork"])
        self.assertIsNone(by_id["mock"]["reason"])

    def test_real_providers_listed_and_unavailable_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            entries = list_available_providers()

        by_id = {entry["id"]: entry for entry in entries}
        for name in ("openai", "anthropic", "local"):
            with self.subTest(provider=name):
                entry = by_id[name]
                self.assertFalse(entry["available"])
                self.assertTrue(entry["requiresNetwork"])
                self.assertTrue(entry["reason"])

    def test_entries_have_expected_keys(self):
        entries = list_available_providers()
        expected_keys = {"id", "label", "requiresNetwork", "available", "reason"}
        for entry in entries:
            self.assertEqual(set(entry.keys()), expected_keys)


if __name__ == "__main__":
    unittest.main()
