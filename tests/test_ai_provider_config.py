import os
import unittest
from unittest import mock

from scripts.ai.config import (
    DEFAULT_PROVIDER_NAME,
    AIProviderConfig,
)


class AIProviderConfigDefaultsTest(unittest.TestCase):
    def test_default_is_mock(self):
        self.assertEqual(DEFAULT_PROVIDER_NAME, "mock")

    def test_empty_environment_resolves_to_safe_defaults(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            config = AIProviderConfig.from_environment()

        self.assertEqual(config.provider_name, "mock")
        self.assertEqual(config.integrations_mode, "mock")
        self.assertFalse(config.enable_real_network_calls)
        self.assertFalse(config.has_api_key("openai"))
        self.assertFalse(config.has_api_key("anthropic"))
        self.assertEqual(config.base_url_for("local"), "")


class AIProviderConfigPreferenceTest(unittest.TestCase):
    def test_explicit_preference_overrides_env(self):
        env = {"AI_PROVIDER_PREFERENCE": "openai"}
        with mock.patch.dict(os.environ, env, clear=True):
            config = AIProviderConfig.from_environment(provider_preference="anthropic")
        self.assertEqual(config.provider_name, "anthropic")

    def test_env_preference_used_when_no_argument(self):
        env = {"AI_PROVIDER_PREFERENCE": "openai"}
        with mock.patch.dict(os.environ, env, clear=True):
            config = AIProviderConfig.from_environment()
        self.assertEqual(config.provider_name, "openai")

    def test_unknown_preference_falls_back_to_mock(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            config = AIProviderConfig.from_environment(provider_preference="not-real")
        self.assertEqual(config.provider_name, "mock")

    def test_case_and_whitespace_insensitive(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            config = AIProviderConfig.from_environment(provider_preference="  ANTHROPIC ")
        self.assertEqual(config.provider_name, "anthropic")


class AIProviderConfigEnvParsingTest(unittest.TestCase):
    def test_env_truthy_parsing(self):
        for truthy in ("true", "TRUE", "1", "yes", "On"):
            with self.subTest(value=truthy):
                with mock.patch.dict(
                    os.environ, {"ENABLE_REAL_NETWORK_CALLS": truthy}, clear=True
                ):
                    config = AIProviderConfig.from_environment()
                self.assertTrue(config.enable_real_network_calls)

        for falsy in ("false", "0", "no", "off", ""):
            with self.subTest(value=falsy):
                with mock.patch.dict(
                    os.environ, {"ENABLE_REAL_NETWORK_CALLS": falsy}, clear=True
                ):
                    config = AIProviderConfig.from_environment()
                self.assertFalse(config.enable_real_network_calls)

    def test_api_keys_loaded_from_env(self):
        env = {
            "OPENAI_API_KEY": "test-openai-key-placeholder",
            "ANTHROPIC_API_KEY": "  test-anthropic-key-placeholder  ",
            "LOCAL_AI_BASE_URL": "http://localhost:11434",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            config = AIProviderConfig.from_environment()

        self.assertTrue(config.has_api_key("openai"))
        self.assertTrue(config.has_api_key("anthropic"))
        self.assertEqual(config.api_key_for("openai"), "test-openai-key-placeholder")
        # Whitespace is stripped.
        self.assertEqual(config.api_key_for("anthropic"), "test-anthropic-key-placeholder")
        self.assertEqual(config.base_url_for("local"), "http://localhost:11434")


class AIProviderConfigRedactionTest(unittest.TestCase):
    """API keys must never appear in repr or safe_dict."""

    def setUp(self) -> None:
        self.env = {
            "OPENAI_API_KEY": "test-openai-redaction-placeholder",
            "ANTHROPIC_API_KEY": "test-anthropic-redaction-placeholder",
        }

    def test_repr_does_not_contain_keys(self):
        with mock.patch.dict(os.environ, self.env, clear=True):
            config = AIProviderConfig.from_environment()
        text = repr(config)
        self.assertNotIn("test-openai-redaction-placeholder", text)
        self.assertNotIn("test-anthropic-redaction-placeholder", text)
        self.assertIn("redacted", text.lower())

    def test_str_does_not_contain_keys(self):
        with mock.patch.dict(os.environ, self.env, clear=True):
            config = AIProviderConfig.from_environment()
        self.assertNotIn("test-openai-redaction-placeholder", str(config))
        self.assertNotIn("test-anthropic-redaction-placeholder", str(config))

    def test_safe_dict_reports_presence_without_values(self):
        with mock.patch.dict(os.environ, self.env, clear=True):
            config = AIProviderConfig.from_environment()
        snapshot = config.safe_dict()
        self.assertEqual(
            snapshot["api_keys_present"], {"openai": True, "anthropic": True}
        )
        # Make sure no raw key leaks through any value of the dict.
        for value in snapshot.values():
            self.assertNotIn("test-openai-redaction-placeholder", repr(value))
            self.assertNotIn("test-anthropic-redaction-placeholder", repr(value))


class AIProviderConfigInjectedEnvTest(unittest.TestCase):
    """The factory accepts an explicit env dict for deterministic tests."""

    def test_env_dict_takes_precedence_over_os_environ(self):
        with mock.patch.dict(os.environ, {"AI_PROVIDER_PREFERENCE": "anthropic"}, clear=True):
            config = AIProviderConfig.from_environment(
                env={"AI_PROVIDER_PREFERENCE": "openai"}
            )
        self.assertEqual(config.provider_name, "openai")


if __name__ == "__main__":
    unittest.main()
