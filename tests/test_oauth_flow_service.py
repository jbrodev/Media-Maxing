from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from scripts.db.init_db import initialize_database
from scripts.services.oauth_flow import (
    DEFAULT_OAUTH_STATE_TTL_SECONDS,
    OAuthFlowService,
    connect_accounts_handler,
    connect_callback_handler,
    connect_platforms_handler,
    connect_start_handler,
)


class OAuthFlowServiceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        return db_path

    def _state_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params["state"][0]

    def test_start_mock_oauth_for_instagram_stores_state_hash_only(self):
        db_path = self._database()

        result = OAuthFlowService(db_path).start_oauth(
            platform="instagram",
            redirect_uri="http://localhost:8000/api/connect/instagram/callback",
            requested_scopes=["basic_profile"],
            now="2026-05-28T12:00:00Z",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.platform, "instagram")
        self.assertEqual(result.status, "redirect_ready")
        self.assertEqual(result.expiresAt, "2026-05-28T12:10:00Z")
        self.assertIn("state=", result.authorizationUrl)
        self.assertEqual(DEFAULT_OAUTH_STATE_TTL_SECONDS, 600)
        state = self._state_from_url(result.authorizationUrl)

        with closing(sqlite3.connect(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT platform, state_hash, status, requested_scopes_json FROM oauth_states"
            ).fetchone()
            oauth_columns = {column[1] for column in connection.execute("PRAGMA table_info(oauth_states)")}
            audit_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM connector_audit_logs
                WHERE platform = 'instagram' AND action = 'oauth_start'
                """
            ).fetchone()[0]

        self.assertEqual(row["platform"], "instagram")
        self.assertEqual(row["status"], "created")
        self.assertNotEqual(row["state_hash"], state)
        self.assertTrue(row["state_hash"].startswith("sha256:"))
        self.assertNotIn("state", oauth_columns)
        self.assertNotIn("raw_state", oauth_columns)
        self.assertEqual(audit_count, 1)

    def test_callback_with_valid_state_succeeds_in_mock_mode(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="instagram",
            redirect_uri="http://localhost:8000/api/connect/instagram/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = self._state_from_url(start.authorizationUrl)

        result = service.handle_callback(
            platform="instagram",
            state=state,
            code="mock-code",
            now="2026-05-28T12:01:00Z",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.status, "mock_connected")
        self.assertEqual(result.account["platform"], "instagram")
        self.assertEqual(result.account["connectionStatus"], "connected")

        with closing(sqlite3.connect(db_path)) as connection:
            state_status = connection.execute(
                "SELECT status FROM oauth_states WHERE id = ?",
                (start.stateId,),
            ).fetchone()[0]
            account_count = connection.execute(
                "SELECT COUNT(*) FROM social_accounts WHERE platform = 'instagram'"
            ).fetchone()[0]
            token_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM platform_tokens
                WHERE platform = 'instagram'
                  AND encryption_status = 'placeholder_not_stored'
                  AND encrypted_access_token IS NULL
                  AND encrypted_refresh_token IS NULL
                """
            ).fetchone()[0]
            callback_audit_count = connection.execute(
                """
                SELECT COUNT(*)
                FROM connector_audit_logs
                WHERE platform = 'instagram' AND action = 'oauth_callback'
                """
            ).fetchone()[0]

        self.assertEqual(state_status, "consumed")
        self.assertEqual(account_count, 1)
        self.assertEqual(token_count, 1)
        self.assertEqual(callback_audit_count, 1)

    def test_callback_with_missing_state_fails(self):
        result = OAuthFlowService(self._database()).handle_callback(
            platform="instagram",
            state=None,
            code="mock-code",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "missing_state")

    def test_callback_with_wrong_state_fails(self):
        db_path = self._database()
        OAuthFlowService(db_path).start_oauth(
            platform="instagram",
            redirect_uri="http://localhost:8000/api/connect/instagram/callback",
        )

        result = OAuthFlowService(db_path).handle_callback(
            platform="instagram",
            state="wrong-state",
            code="mock-code",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "invalid_state")

    def test_callback_with_expired_state_fails(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="instagram",
            redirect_uri="http://localhost:8000/api/connect/instagram/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = self._state_from_url(start.authorizationUrl)

        result = service.handle_callback(
            platform="instagram",
            state=state,
            code="mock-code",
            now="2026-05-28T12:11:00Z",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "expired_state")
        with closing(sqlite3.connect(db_path)) as connection:
            status = connection.execute(
                "SELECT status FROM oauth_states WHERE id = ?",
                (start.stateId,),
            ).fetchone()[0]
        self.assertEqual(status, "expired")

    def test_callback_with_reused_state_fails(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="instagram",
            redirect_uri="http://localhost:8000/api/connect/instagram/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = self._state_from_url(start.authorizationUrl)
        first = service.handle_callback(
            platform="instagram",
            state=state,
            code="mock-code",
            now="2026-05-28T12:01:00Z",
        )

        second = service.handle_callback(
            platform="instagram",
            state=state,
            code="mock-code",
            now="2026-05-28T12:02:00Z",
        )

        self.assertTrue(first.success)
        self.assertFalse(second.success)
        self.assertEqual(second.status, "reused_state")

    def test_unsupported_platform_fails_safely(self):
        result = OAuthFlowService(self._database()).start_oauth(
            platform="myspace",
            redirect_uri="http://localhost/callback",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "unsupported_platform")

    def test_callback_missing_code_fails_without_consuming_state(self):
        db_path = self._database()
        service = OAuthFlowService(db_path)
        start = service.start_oauth(
            platform="instagram",
            redirect_uri="http://localhost:8000/api/connect/instagram/callback",
            now="2026-05-28T12:00:00Z",
        )
        state = self._state_from_url(start.authorizationUrl)

        result = service.handle_callback(
            platform="instagram",
            state=state,
            code=None,
            now="2026-05-28T12:01:00Z",
        )

        self.assertFalse(result.success)
        self.assertEqual(result.status, "missing_code")
        with closing(sqlite3.connect(db_path)) as connection:
            state_status = connection.execute(
                "SELECT status FROM oauth_states WHERE id = ?",
                (start.stateId,),
            ).fetchone()[0]
        self.assertEqual(state_status, "created")

    def test_route_handler_scaffolding_exposes_safe_shapes(self):
        db_path = self._database()

        start = connect_start_handler(
            "instagram",
            {"redirectUri": "http://localhost:8000/api/connect/instagram/callback"},
            database_path=db_path,
            now="2026-05-28T12:00:00Z",
        )
        state = self._state_from_url(start["authorizationUrl"])
        callback = connect_callback_handler(
            "instagram",
            {"state": state, "code": "mock-code"},
            database_path=db_path,
            now="2026-05-28T12:01:00Z",
        )
        accounts = connect_accounts_handler(database_path=db_path)
        platforms = connect_platforms_handler(database_path=db_path)

        self.assertTrue(start["success"])
        self.assertNotIn("stateHash", start)
        self.assertTrue(callback["success"])
        self.assertEqual(len(accounts["accounts"]), 1)
        self.assertIn("instagram", [item["platform"] for item in platforms["platforms"]])


if __name__ == "__main__":
    unittest.main()
