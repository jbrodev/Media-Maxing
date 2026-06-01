from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.db.init_db import initialize_database
from scripts.db.social_connections import create_mock_social_account
from scripts.services.token_security import (
    TokenAccessPolicy,
    TokenSecurityService,
    TokenStorageMode,
    is_token_expired,
    redact_token_data,
    requires_reauth,
)


class TokenSecurityServiceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        return db_path

    def test_redacts_access_refresh_and_client_secret_values(self):
        raw = {
            "access_token": "fixture",
            "refresh_token": "fixture",
            "client_secret": "fixture",
            "nested": {
                "Authorization": "fixture",
                "safe": "keep me",
            },
        }

        result = redact_token_data(raw)

        self.assertTrue(result.redacted)
        self.assertIn("access_token", result.redactedFields)
        self.assertIn("refresh_token", result.redactedFields)
        self.assertIn("client_secret", result.redactedFields)
        self.assertEqual(result.value["access_token"], "[REDACTED]")
        self.assertEqual(result.value["refresh_token"], "[REDACTED]")
        self.assertEqual(result.value["client_secret"], "[REDACTED]")
        self.assertEqual(result.value["nested"]["Authorization"], "[REDACTED]")
        self.assertEqual(result.value["nested"]["safe"], "keep me")

    def test_safe_account_dto_excludes_token_fields(self):
        db_path = self._database()
        create_mock_social_account(
            db_path,
            platform="facebook",
            display_name="Demo Page",
            account_id="safe-dto-account",
            account_type="page",
        )

        dto = TokenSecurityService(db_path).list_safe_social_account_dtos()[0]

        self.assertEqual(dto["id"], "safe-dto-account")
        self.assertEqual(dto["platform"], "facebook")
        self.assertEqual(dto["displayName"], "Demo Page")
        forbidden = {
            "accessToken",
            "refreshToken",
            "encryptedAccessToken",
            "encryptedRefreshToken",
            "authorizationCode",
            "clientSecret",
            "state",
            "stateHash",
        }
        self.assertTrue(forbidden.isdisjoint(dto))

    def test_placeholder_mode_refuses_to_store_raw_tokens(self):
        db_path = self._database()
        account_id = create_mock_social_account(
            db_path,
            platform="instagram",
            display_name="Demo Instagram",
        )

        result = TokenSecurityService(
            db_path,
            storage_mode=TokenStorageMode.PLACEHOLDER_NOT_STORED,
        ).store_token_set(
            social_account_id=account_id,
            platform="instagram",
            token_set={
                "access_token": "fixture",
                "refresh_token": "fixture",
                "expires_at": "2026-05-27T12:30:00Z",
            },
        )

        self.assertFalse(result.success)
        self.assertEqual(result.storageMode, TokenStorageMode.PLACEHOLDER_NOT_STORED.value)
        self.assertEqual(result.encryptionStatus, "placeholder_not_stored")
        self.assertIn("secure_storage_unavailable", result.error_codes)

    def test_insecure_dev_mode_is_blocked_outside_development(self):
        db_path = self._database()
        account_id = create_mock_social_account(
            db_path,
            platform="threads",
            display_name="Demo Threads",
        )

        with patch.dict(
            os.environ,
            {
                "APP_ENV": "production",
                "ALLOW_INSECURE_TOKEN_STORAGE": "true",
            },
            clear=False,
        ):
            result = TokenSecurityService(
                db_path,
                storage_mode=TokenStorageMode.INSECURE_DEV_ONLY,
            ).store_token_set(
                social_account_id=account_id,
                platform="threads",
                token_set={"access_token": "fixture"},
            )

        self.assertFalse(result.success)
        self.assertIn("insecure_dev_mode_blocked", result.error_codes)

    def test_expired_token_requires_reauth(self):
        self.assertTrue(
            is_token_expired(
                "2026-05-27T11:59:00Z",
                now="2026-05-27T12:00:00Z",
            )
        )
        self.assertTrue(
            requires_reauth(
                access_token_expires_at="2026-05-27T11:59:00Z",
                refresh_token_expires_at=None,
                connection_status="connected",
                requires_reauth_flag=False,
            )
        )
        self.assertFalse(
            requires_reauth(
                access_token_expires_at="2026-05-27T13:00:00Z",
                refresh_token_expires_at=None,
                connection_status="connected",
                requires_reauth_flag=False,
                now="2026-05-27T12:00:00Z",
            )
        )

    def test_server_side_retrieve_policy_refuses_frontend_context(self):
        service = TokenSecurityService(self._database())
        result = service.retrieve_token_metadata(
            social_account_id="missing",
            access_policy=TokenAccessPolicy.FRONTEND_SAFE_DTO,
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["status"], "forbidden")


if __name__ == "__main__":
    unittest.main()
