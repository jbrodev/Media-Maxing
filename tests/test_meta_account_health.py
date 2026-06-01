from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.connectors.registry import get_connector
from scripts.db.init_db import initialize_database
from scripts.db.social_connections import (
    create_mock_social_account,
    create_placeholder_platform_token,
)
from scripts.services.platform_http_client import (
    NetworkSafetyMode,
    PlatformHttpClientConfig,
    PlatformHttpResponse,
)


class MetaAccountHealthTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        return db_path

    def _account(
        self,
        db_path: Path,
        *,
        platform: str = "facebook",
        granted_scopes: list[str] | None = None,
        missing_scopes: list[str] | None = None,
        connection_status: str = "connected",
        expires_at: str | None = "2099-05-28T13:00:00Z",
    ) -> str:
        account_id = create_mock_social_account(
            db_path,
            platform=platform,
            display_name="Demo Meta Account",
            platform_account_id=f"demo-{platform}-account",
            account_type="page" if platform == "facebook" else "business",
            connection_status=connection_status,
            granted_scopes=granted_scopes or [],
            missing_scopes=missing_scopes or [],
            account_id=f"acct-{platform}-health",
            now="2026-05-28T12:00:00Z",
        )
        token_id = create_placeholder_platform_token(
            db_path,
            social_account_id=account_id,
            platform=platform,
            token_type="oauth_access",
            scope=" ".join(granted_scopes or []),
            now="2026-05-28T12:00:00Z",
        )
        if expires_at:
            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute(
                    "UPDATE platform_tokens SET access_token_expires_at = ? WHERE id = ?",
                    (expires_at, token_id),
                )
                connection.commit()
        return account_id

    def test_mock_facebook_account_health_updates_last_validated(self):
        db_path = self._database()
        account_id = self._account(
            db_path,
            platform="facebook",
            granted_scopes=["pages_show_list", "pages_read_engagement"],
        )

        def fake_profile(request, timeout):
            return PlatformHttpResponse(
                ok=True,
                status=200,
                json={
                    "id": "fb-page-123",
                    "name": "Demo Facebook Page",
                    "username": "demo-page",
                    "account_type": "page",
                },
            )

        result = get_connector("facebook").validateConnection(
            account_id,
            database_path=db_path,
            http_client_config=PlatformHttpClientConfig(
                provider="meta",
                platform="facebook",
                safetyMode=NetworkSafetyMode.ENABLED,
                allowNetwork=True,
                transport=fake_profile,
            ),
            now="2026-05-28T12:30:00Z",
            debug=True,
        )

        self.assertEqual(result.status, "healthy")
        self.assertEqual(result.socialAccountId, account_id)
        self.assertEqual(result.connectionStatus, "connected")
        self.assertEqual(result.displayName, "Demo Facebook Page")
        self.assertEqual(result.platformAccountId, "fb-page-123")
        self.assertIn("name", result.rawProviderResponseRedacted)

        with closing(sqlite3.connect(db_path)) as connection:
            row = connection.execute(
                "SELECT last_validated_at, display_name, platform_account_id FROM social_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
            audit_count = connection.execute(
                "SELECT COUNT(*) FROM connector_audit_logs WHERE action = 'connection_validate'"
            ).fetchone()[0]
            health_count = connection.execute(
                "SELECT COUNT(*) FROM connector_health_checks WHERE social_account_id = ?",
                (account_id,),
            ).fetchone()[0]

        self.assertEqual(row[0], "2026-05-28T12:30:00Z")
        self.assertEqual(row[1], "Demo Facebook Page")
        self.assertEqual(row[2], "fb-page-123")
        self.assertEqual(audit_count, 1)
        self.assertEqual(health_count, 1)

    def test_instagram_missing_business_scope_returns_missing_permissions(self):
        db_path = self._database()
        account_id = self._account(
            db_path,
            platform="instagram",
            granted_scopes=["instagram_basic"],
            missing_scopes=["pages_show_list"],
        )

        result = get_connector("instagram").validateConnection(
            account_id,
            database_path=db_path,
            http_client_config=PlatformHttpClientConfig(
                provider="meta",
                platform="instagram",
                safetyMode=NetworkSafetyMode.MOCK,
            ),
            now="2026-05-28T12:30:00Z",
        )

        self.assertEqual(result.status, "missing_permissions")
        self.assertEqual(result.connectionStatus, "limited")
        self.assertIn("pages_show_list", result.missingScopes)
        self.assertIn("business", " ".join(result.warnings).lower())

    def test_expired_token_marks_account_requires_reauth(self):
        db_path = self._database()
        account_id = self._account(
            db_path,
            platform="threads",
            granted_scopes=["threads_basic"],
            expires_at="2026-05-28T11:59:00Z",
        )

        result = get_connector("threads").validateConnection(
            account_id,
            database_path=db_path,
            now="2026-05-28T12:30:00Z",
        )

        self.assertEqual(result.status, "expired")
        self.assertTrue(result.requiresReauth)
        self.assertEqual(result.connectionStatus, "requires_reauth")

        with closing(sqlite3.connect(db_path)) as connection:
            status, requires_reauth = connection.execute(
                "SELECT connection_status, requires_reauth FROM social_accounts WHERE id = ?",
                (account_id,),
            ).fetchone()
        self.assertEqual(status, "requires_reauth")
        self.assertEqual(requires_reauth, 1)

    def test_network_disabled_returns_health_without_crashing(self):
        db_path = self._database()
        account_id = self._account(
            db_path,
            platform="facebook",
            granted_scopes=["pages_show_list", "pages_read_engagement"],
        )

        result = get_connector("facebook").validateConnection(
            account_id,
            database_path=db_path,
            http_client_config=PlatformHttpClientConfig(
                provider="meta",
                platform="facebook",
                safetyMode=NetworkSafetyMode.DISABLED,
            ),
            now="2026-05-28T12:30:00Z",
        )

        self.assertEqual(result.status, "network_disabled")
        self.assertFalse(result.requiresReauth)
        self.assertIn("disabled", " ".join(result.errors).lower())

    def test_provider_401_marks_requires_reauth(self):
        db_path = self._database()
        account_id = self._account(
            db_path,
            platform="facebook",
            granted_scopes=["pages_show_list", "pages_read_engagement"],
        )

        def auth_error(request, timeout):
            return PlatformHttpResponse(
                ok=False,
                status=401,
                json={"error": {"code": "190", "message": "OAuth access_token invalid"}},
                text='{"error":{"message":"OAuth access_token invalid"}}',
            )

        result = get_connector("facebook").validateConnection(
            account_id,
            database_path=db_path,
            http_client_config=PlatformHttpClientConfig(
                provider="meta",
                platform="facebook",
                safetyMode=NetworkSafetyMode.ENABLED,
                allowNetwork=True,
                transport=auth_error,
            ),
            now="2026-05-28T12:30:00Z",
            debug=True,
        )

        self.assertEqual(result.status, "expired")
        self.assertTrue(result.requiresReauth)
        self.assertNotIn("access_token", result.rawProviderResponseRedacted)

    def test_get_account_profile_returns_safe_profile_from_mock_response(self):
        db_path = self._database()
        account_id = self._account(
            db_path,
            platform="threads",
            granted_scopes=["threads_basic"],
        )

        def fake_profile(request, timeout):
            return PlatformHttpResponse(
                ok=True,
                status=200,
                json={
                    "id": "threads-profile-1",
                    "username": "demo_threads",
                    "name": "Demo Threads",
                },
            )

        profile = get_connector("threads").getAccountProfile(
            account_id,
            database_path=db_path,
            http_client_config=PlatformHttpClientConfig(
                provider="meta",
                platform="threads",
                safetyMode=NetworkSafetyMode.ENABLED,
                allowNetwork=True,
                transport=fake_profile,
            ),
        )

        self.assertEqual(profile.providerAccountId, "threads-profile-1")
        self.assertEqual(profile.displayName, "Demo Threads")
        self.assertEqual(profile.handle, "demo_threads")
        serialized = json.dumps(profile.__dict__)
        self.assertNotIn("access_token", serialized)


if __name__ == "__main__":
    unittest.main()
