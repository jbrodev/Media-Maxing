from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.init_db import initialize_database
from scripts.db.social_connections import (
    CONNECTOR_AUDIT_ACTIONS,
    OAUTH_STATE_STATUSES,
    PLATFORM_TOKEN_TYPES,
    SOCIAL_ACCOUNT_TYPES,
    SOCIAL_CONNECTION_STATUSES,
    TOKEN_ENCRYPTION_STATUSES,
    create_connector_audit_log,
    create_mock_social_account,
    create_oauth_state_record,
    create_placeholder_platform_token,
    list_safe_social_accounts,
)


EXPECTED_SOCIAL_ACCOUNT_COLUMNS = {
    "id",
    "brand_profile_id",
    "platform",
    "platform_account_id",
    "display_name",
    "username",
    "profile_url",
    "profile_image_url",
    "account_type",
    "connection_status",
    "capabilities_json",
    "granted_scopes_json",
    "missing_scopes_json",
    "requires_reauth",
    "last_connected_at",
    "last_validated_at",
    "disconnected_at",
    "created_at",
    "updated_at",
}

EXPECTED_PLATFORM_TOKEN_COLUMNS = {
    "id",
    "social_account_id",
    "platform",
    "token_type",
    "encrypted_access_token",
    "encrypted_refresh_token",
    "access_token_expires_at",
    "refresh_token_expires_at",
    "scope",
    "token_version",
    "encryption_status",
    "last_refresh_at",
    "revoked_at",
    "created_at",
    "updated_at",
}

EXPECTED_OAUTH_STATE_COLUMNS = {
    "id",
    "platform",
    "state_hash",
    "redirect_uri",
    "code_verifier_hash",
    "requested_scopes_json",
    "status",
    "created_at",
    "expires_at",
    "consumed_at",
    "error_message",
}


class SocialConnectionModelTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        return db_path

    def test_social_connection_tables_and_constants_exist(self):
        db_path = self._database()

        self.assertIn("business", SOCIAL_ACCOUNT_TYPES)
        self.assertIn("requires_reauth", SOCIAL_CONNECTION_STATUSES)
        self.assertIn("page_access", PLATFORM_TOKEN_TYPES)
        self.assertIn("placeholder_not_stored", TOKEN_ENCRYPTION_STATUSES)
        self.assertIn("consumed", OAUTH_STATE_STATUSES)
        self.assertIn("oauth_callback", CONNECTOR_AUDIT_ACTIONS)

        with closing(sqlite3.connect(db_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

            self.assertIn("social_accounts", tables)
            self.assertIn("platform_tokens", tables)
            self.assertIn("oauth_states", tables)
            self.assertIn("connector_audit_logs", tables)
            self.assertIn("connector_health_checks", tables)
            self.assertTrue(
                EXPECTED_SOCIAL_ACCOUNT_COLUMNS.issubset(
                    self._columns(connection, "social_accounts")
                )
            )
            self.assertTrue(
                EXPECTED_PLATFORM_TOKEN_COLUMNS.issubset(
                    self._columns(connection, "platform_tokens")
                )
            )
            self.assertTrue(
                EXPECTED_OAUTH_STATE_COLUMNS.issubset(
                    self._columns(connection, "oauth_states")
                )
            )

    def test_mock_account_and_placeholder_token_are_safe_to_insert(self):
        db_path = self._database()

        account_id = create_mock_social_account(
            db_path,
            platform="facebook",
            display_name="Demo Facebook Page",
            username="demo-page",
            platform_account_id="mock-facebook-page-1",
            account_type="page",
            granted_scopes=["pages_show_list"],
            capabilities={"canReadProfile": True, "canPublishText": False},
        )
        token_id = create_placeholder_platform_token(
            db_path,
            social_account_id=account_id,
            platform="facebook",
            token_type="page_access",
            scope="pages_show_list",
        )

        with closing(sqlite3.connect(db_path)) as connection:
            token_row = connection.execute(
                """
                SELECT encrypted_access_token, encrypted_refresh_token, encryption_status
                FROM platform_tokens
                WHERE id = ?
                """,
                (token_id,),
            ).fetchone()

        self.assertEqual(token_row, (None, None, "placeholder_not_stored"))

    def test_placeholder_tokens_reject_token_blobs_at_database_level(self):
        db_path = self._database()
        account_id = create_mock_social_account(
            db_path,
            platform="instagram",
            display_name="Demo Instagram",
        )

        with closing(sqlite3.connect(db_path)) as connection:
            with self.assertRaises(sqlite3.IntegrityError):
                connection.execute(
                    """
                    INSERT INTO platform_tokens (
                      id, social_account_id, platform, token_type,
                      encrypted_access_token, encryption_status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        "unsafe-token-test",
                        account_id,
                        "instagram",
                        "oauth_access",
                        "raw-or-placeholder-token-value",
                        "placeholder_not_stored",
                    ),
                )

    def test_oauth_state_stores_hash_and_not_raw_state(self):
        db_path = self._database()

        state_id = create_oauth_state_record(
            db_path,
            platform="threads",
            state_hash="sha256:demo-state-hash",
            redirect_uri="http://localhost:8000/oauth/threads/callback",
            requested_scopes=["basic_profile"],
            expires_at="2026-05-27T13:10:00Z",
        )

        with closing(sqlite3.connect(db_path)) as connection:
            state_row = connection.execute(
                "SELECT state_hash, status FROM oauth_states WHERE id = ?",
                (state_id,),
            ).fetchone()
            oauth_columns = self._columns(connection, "oauth_states")

        self.assertEqual(state_row, ("sha256:demo-state-hash", "created"))
        self.assertNotIn("state", oauth_columns)
        self.assertNotIn("raw_state", oauth_columns)

    def test_safe_account_dto_excludes_token_and_oauth_secret_fields(self):
        db_path = self._database()
        account_id = create_mock_social_account(
            db_path,
            platform="facebook",
            display_name="Demo Facebook Page",
            username="demo-page",
            platform_account_id="mock-facebook-page-1",
            account_type="page",
        )
        create_placeholder_platform_token(
            db_path,
            social_account_id=account_id,
            platform="facebook",
            token_type="page_access",
            scope="pages_show_list",
        )
        create_connector_audit_log(
            db_path,
            platform="facebook",
            action="oauth_start",
            status="succeeded",
            message="Mock OAuth started locally.",
            social_account_id=account_id,
            safe_metadata={"demo": True},
        )

        accounts = list_safe_social_accounts(db_path)

        self.assertEqual(len(accounts), 1)
        safe_account = accounts[0]
        self.assertEqual(safe_account["id"], account_id)
        self.assertEqual(safe_account["platform"], "facebook")
        self.assertEqual(safe_account["connectionStatus"], "connected")
        self.assertEqual(safe_account["tokenStorageStatus"], "placeholder_not_stored")

        forbidden_keys = {
            "encryptedAccessToken",
            "encryptedRefreshToken",
            "accessToken",
            "refreshToken",
            "authorizationCode",
            "state",
            "stateHash",
            "clientSecret",
        }
        self.assertTrue(forbidden_keys.isdisjoint(safe_account))

    @staticmethod
    def _columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})")}


if __name__ == "__main__":
    unittest.main()
