import json
import os
import unittest
from unittest.mock import patch

from scripts.services.platform_http_client import (
    NetworkSafetyMode,
    PlatformHttpClient,
    PlatformHttpClientConfig,
    PlatformHttpMethod,
    PlatformHttpRequest,
    PlatformHttpResponse,
    normalize_provider_error,
    redact_http_value,
)


class PlatformHttpClientTest(unittest.TestCase):
    def test_authorization_header_is_redacted_when_network_is_blocked(self):
        client = PlatformHttpClient(
            PlatformHttpClientConfig(
                provider="meta",
                platform="instagram",
                safetyMode=NetworkSafetyMode.DISABLED,
            )
        )

        response = client.request(
            PlatformHttpRequest(
                method=PlatformHttpMethod.GET,
                url="https://graph.example.local/me",
                headers={"Authorization": "Bearer secret-token-value"},
            )
        )

        self.assertFalse(response.ok)
        self.assertEqual(response.error.status, "network_disabled")
        serialized = json.dumps(response.to_safe_dict())
        self.assertNotIn("secret-token-value", serialized)
        self.assertIn("[REDACTED]", serialized)

    def test_oauth_form_body_client_secret_is_redacted(self):
        safe = redact_http_value(
            {
                "client_id": "fake-client",
                "client_secret": "fake-secret-value",
                "code": "long-oauth-code-value-123456789",
                "grant_type": "authorization_code",
            }
        )

        serialized = json.dumps(safe.value)
        self.assertNotIn("fake-secret-value", serialized)
        self.assertNotIn("long-oauth-code-value-123456789", serialized)
        self.assertIn("grant_type", serialized)

    def test_test_environment_blocks_network_by_default(self):
        with patch.dict(
            os.environ,
            {
                "APP_ENV": "test",
                "ALLOW_NETWORK_IN_TESTS": "false",
                "ENABLE_REAL_NETWORK_CALLS": "true",
            },
            clear=False,
        ):
            client = PlatformHttpClient(
                PlatformHttpClientConfig(provider="meta", platform="facebook")
            )

        response = client.request(
            PlatformHttpRequest(
                method=PlatformHttpMethod.GET,
                url="https://example.com/should-not-run",
            )
        )

        self.assertFalse(response.ok)
        self.assertEqual(response.error.status, "network_disabled")

    def test_mock_mode_returns_configured_mock_response(self):
        client = PlatformHttpClient(
            PlatformHttpClientConfig(
                provider="meta",
                platform="threads",
                safetyMode=NetworkSafetyMode.MOCK,
                mockResponses={
                    "GET https://graph.example.local/me": PlatformHttpResponse(
                        ok=True,
                        status=200,
                        json={"id": "mock-profile", "name": "Mock Profile"},
                    )
                },
            )
        )

        response = client.request(
            PlatformHttpRequest(
                method=PlatformHttpMethod.GET,
                url="https://graph.example.local/me",
            )
        )

        self.assertTrue(response.ok)
        self.assertEqual(response.json["id"], "mock-profile")
        self.assertTrue(response.mocked)

    def test_invalid_url_returns_safe_error(self):
        client = PlatformHttpClient(
            PlatformHttpClientConfig(
                provider="google",
                platform="youtube",
                safetyMode=NetworkSafetyMode.ENABLED,
                allowNetwork=True,
                transport=lambda request, timeout: PlatformHttpResponse(ok=True, status=200),
            )
        )

        response = client.request(
            PlatformHttpRequest(
                method=PlatformHttpMethod.GET,
                url="not-a-valid-url",
            )
        )

        self.assertFalse(response.ok)
        self.assertEqual(response.error.status, "invalid_url")

    def test_provider_401_and_429_are_normalized(self):
        unauthorized = normalize_provider_error(
            provider="meta",
            platform="facebook",
            status=401,
            payload={"error": {"code": "190", "message": "OAuth access_token bad"}},
            raw_text='{"error":{"message":"OAuth access_token bad"}}',
        )
        limited = normalize_provider_error(
            provider="x",
            platform="x",
            status=429,
            payload={"detail": "Too many requests"},
            raw_text="Bearer abcdefghijklmnopqrstuvwxyz123456",
        )

        self.assertTrue(unauthorized.requiresReauth)
        self.assertFalse(unauthorized.rateLimited)
        self.assertNotIn("access_token", unauthorized.rawRedacted)
        self.assertTrue(limited.rateLimited)
        self.assertNotIn("abcdefghijklmnopqrstuvwxyz123456", limited.rawRedacted)


if __name__ == "__main__":
    unittest.main()
