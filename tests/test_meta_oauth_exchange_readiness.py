from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from scripts.db.init_db import initialize_database
from scripts.connectors.registry import get_connector
from scripts.services.oauth_flow import OAuthFlowService
from scripts.services.platform_http_client import (
    NetworkSafetyMode,
    PlatformHttpClientConfig,
    PlatformHttpResponse,
    normalize_provider_error,
)


class MetaOAuthExchangeReadinessTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        return db_path

    def _state_from_url(self, url: str) -> str:
        return parse_qs(urlparse(url).query)["state"][0]

    def _real_oauth_env(self, **overrides: str) -> dict[str, str]:
        values = {
            "APP_ENV": "development",
            "INTEGRATIONS_MODE": "real_oauth",
            "ENABLE_REAL_OAUTH": "true",
            "ENABLE_REAL_NETWORK_CALLS": "true",
            "ENABLE_REAL_PUBLISHING": "false",
            "TOKEN_STORAGE_MODE": "placeholder_not_stored",
            "META_ENABLE_REAL_OAUTH": "true",
            "META_ENABLE_REAL_PUBLISHING": "false",
            "META_CLIENT_ID": "fake-meta-client-id",
            "META_CLIENT_SECRET": "fake-meta-client-secret",
            "META_REDIRECT_URI": "http://localhost:8000/api/connect/instagram/callback",
            "META_GRAPH_API_VERSION": "v20.0",
        }
        values.update(overrides)
        return values

    def _service_with_state(
        self,
        db_path: Path,
        *,
        platform: str = "instagram",
        integrations_mode: str = "real_oauth",
        transport=None,
    ) -> tuple[OAuthFlowService, str]:
        service = OAuthFlowService(
            db_path,
            integrations_mode=integrations_mode,
            http_client_config=PlatformHttpClientConfig(
                provider="meta",
                platform=platform,
                safetyMode=NetworkSafetyMode.ENABLED,
                allowNetwork=True,
                transport=transport,
            ),
        )
        start = service.start_oauth(
            platform=platform,
            redirect_uri=f"http://localhost:8000/api/connect/{platform}/callback",
            now="2026-05-28T12:00:00Z",
        )
        return service, self._state_from_url(start.authorizationUrl)

    def test_real_oauth_disabled_does_not_call_network(self):
        db_path = self._database()
        called = {"count": 0}

        def fail_if_called(request, timeout):
            called["count"] += 1
            raise AssertionError("network should not be called")

        with patch.dict(
            os.environ,
            self._real_oauth_env(
                INTEGRATIONS_MODE="disabled",
                ENABLE_REAL_OAUTH="false",
            ),
            clear=True,
        ):
            service, state = self._service_with_state(
                db_path,
                integrations_mode="disabled",
                transport=fail_if_called,
            )
            result = service.handle_callback(
                platform="instagram",
                state=state,
                code="real-code",
                now="2026-05-28T12:01:00Z",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "real_oauth_disabled")
        self.assertEqual(called["count"], 0)

    def test_network_disabled_does_not_call_network(self):
        db_path = self._database()
        called = {"count": 0}

        def fail_if_called(request, timeout):
            called["count"] += 1
            raise AssertionError("network should not be called")

        with patch.dict(
            os.environ,
            self._real_oauth_env(ENABLE_REAL_NETWORK_CALLS="false"),
            clear=True,
        ):
            service, state = self._service_with_state(db_path, transport=fail_if_called)
            result = service.handle_callback(
                platform="instagram",
                state=state,
                code="real-code",
                now="2026-05-28T12:01:00Z",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "real_network_disabled")
        self.assertEqual(called["count"], 0)

    def test_missing_meta_client_secret_does_not_call_network(self):
        db_path = self._database()
        called = {"count": 0}

        def fail_if_called(request, timeout):
            called["count"] += 1
            raise AssertionError("network should not be called")

        with patch.dict(os.environ, self._real_oauth_env(META_CLIENT_SECRET=""), clear=True):
            service, state = self._service_with_state(db_path, transport=fail_if_called)
            result = service.handle_callback(
                platform="instagram",
                state=state,
                code="real-code",
                now="2026-05-28T12:01:00Z",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "setup_required")
        self.assertIn("META_CLIENT_SECRET", result.warnings[0])
        self.assertEqual(called["count"], 0)

    def test_invalid_state_does_not_call_network(self):
        db_path = self._database()
        called = {"count": 0}

        def fail_if_called(request, timeout):
            called["count"] += 1
            raise AssertionError("network should not be called")

        with patch.dict(os.environ, self._real_oauth_env(), clear=True):
            service, _state = self._service_with_state(db_path, transport=fail_if_called)
            result = service.handle_callback(
                platform="instagram",
                state="wrong-state",
                code="real-code",
                now="2026-05-28T12:01:00Z",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "invalid_state")
        self.assertEqual(called["count"], 0)

    def test_mock_http_token_response_creates_limited_safe_account(self):
        db_path = self._database()
        requests = []

        def fake_token_transport(request, timeout):
            requests.append(request)
            return PlatformHttpResponse(
                ok=True,
                status=200,
                json={
                    "access_token": "meta-access-token-must-not-leak",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "scope": "instagram_basic,pages_show_list",
                },
                text=json.dumps(
                    {
                        "access_token": "meta-access-token-must-not-leak",
                        "token_type": "bearer",
                    }
                ),
            )

        with patch.dict(os.environ, self._real_oauth_env(), clear=True):
            service, state = self._service_with_state(db_path, transport=fake_token_transport)
            result = service.handle_callback(
                platform="instagram",
                state=state,
                code="real-code-must-not-leak",
                now="2026-05-28T12:01:00Z",
            )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "real_oauth_limited_connected")
        self.assertEqual(result.account["platform"], "instagram")
        self.assertEqual(result.account["connectionStatus"], "limited")
        self.assertTrue(result.account["requiresReauth"])
        self.assertNotIn("accessToken", result.account)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].formBody["grant_type"], "authorization_code")

        with closing(sqlite3.connect(db_path)) as connection:
            token_row = connection.execute(
                """
                SELECT encrypted_access_token, encrypted_refresh_token, encryption_status
                FROM platform_tokens
                WHERE platform = 'instagram'
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()
            audit_rows = connection.execute(
                """
                SELECT action, status, message, safe_metadata_json
                FROM connector_audit_logs
                WHERE platform = 'instagram'
                ORDER BY created_at
                """
            ).fetchall()

        self.assertIsNone(token_row[0])
        self.assertIsNone(token_row[1])
        self.assertEqual(token_row[2], "placeholder_not_stored")
        audit_text = json.dumps([tuple(row) for row in audit_rows])
        self.assertIn("token_exchange", audit_text)
        self.assertNotIn("meta-access-token-must-not-leak", audit_text)
        self.assertNotIn("real-code-must-not-leak", audit_text)

    def test_http_401_returns_safe_requires_reauth_error(self):
        db_path = self._database()

        def unauthorized_transport(request, timeout):
            return PlatformHttpResponse(
                ok=False,
                status=401,
                json={"error": {"code": "190", "message": "OAuth access_token invalid"}},
                text='{"error":{"message":"OAuth access_token invalid"}}',
                error=None,
            )

        with patch.dict(os.environ, self._real_oauth_env(), clear=True):
            service, state = self._service_with_state(db_path, transport=unauthorized_transport)
            result = service.handle_callback(
                platform="instagram",
                state=state,
                code="real-code-must-not-leak",
                now="2026-05-28T12:01:00Z",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "provider_requires_reauth")
        serialized = json.dumps(result.to_safe_dict())
        self.assertNotIn("access_token", serialized)
        self.assertNotIn("real-code-must-not-leak", serialized)

    def test_http_429_returns_rate_limited_error(self):
        db_path = self._database()

        def rate_limited_transport(request, timeout):
            return PlatformHttpResponse(
                ok=False,
                status=429,
                json={"error": {"code": "4", "message": "Rate limit reached"}},
                text='{"error":{"message":"Rate limit reached"}}',
                error=None,
            )

        with patch.dict(os.environ, self._real_oauth_env(), clear=True):
            service, state = self._service_with_state(db_path, transport=rate_limited_transport)
            result = service.handle_callback(
                platform="instagram",
                state=state,
                code="real-code",
                now="2026-05-28T12:01:00Z",
            )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "provider_rate_limited")

    def test_batch5_mock_oauth_flow_still_works(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="instagram",
            redirect_uri="http://localhost:8000/api/connect/instagram/callback",
            now="2026-05-28T12:00:00Z",
        )
        result = service.handle_callback(
            platform="instagram",
            state=self._state_from_url(start.authorizationUrl),
            code="mock-code",
            now="2026-05-28T12:01:00Z",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "mock_connected")
        self.assertEqual(result.account["connectionStatus"], "connected")

    def test_meta_connector_delegates_exchange_through_oauth_state_service(self):
        db_path = self._database()

        def fake_token_transport(request, timeout):
            return PlatformHttpResponse(
                ok=True,
                status=200,
                json={
                    "access_token": "meta-access-token-must-not-leak",
                    "token_type": "bearer",
                    "expires_in": 3600,
                    "scope": "instagram_basic",
                },
            )

        with patch.dict(os.environ, self._real_oauth_env(), clear=True):
            service, state = self._service_with_state(db_path, transport=fake_token_transport)
            connector = get_connector("instagram")
            result = connector.exchangeAuthorizationCode(
                database_path=db_path,
                state=state,
                code="real-code",
                http_client_config=service.http_client_config,
                now="2026-05-28T12:01:00Z",
            )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "real_oauth_limited_connected")


if __name__ == "__main__":
    unittest.main()
