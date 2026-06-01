from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.init_db import initialize_database
from scripts.db.settings import update_app_settings
from scripts.db.social_connections import create_mock_social_account
from scripts.services.preflight import (
    PLATFORM_REQUIREMENT_MATRIX,
    REQUIREMENT_VERSION,
    PreflightValidationService,
)


def _json(value):
    return json.dumps(value, sort_keys=True)


class PreflightValidationServiceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO brand_profiles (
                  id, business_name, services_json, locations_json,
                  supported_claims_json, blocked_phrases_json, preferences_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "brand-preflight-test",
                    "Preflight Test Exterior Care",
                    _json(["pressure washing"]),
                    _json(["Demo City"]),
                    _json(["Uses careful surface checks."]),
                    _json([]),
                    _json({"demo": True}),
                ),
            )
            self._insert_media(connection, "media-image", "image", "image/jpeg")
            self._insert_media(connection, "media-video", "video", "video/mp4")
            connection.commit()
        return db_path

    def _insert_media(
        self,
        connection: sqlite3.Connection,
        media_id: str,
        media_type: str,
        mime_type: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO media_assets (
              id, media_type, original_path, file_name, mime_type,
              file_size_bytes, tags_json, job_context_json, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                media_id,
                media_type,
                f"data/media/originals/{media_id}",
                f"{media_id}",
                mime_type,
                1200,
                _json(["demo"]),
                _json({}),
                _json({"demo": True}),
            ),
        )

    def _create_scheduled_queue(
        self,
        db_path: Path,
        *,
        platform: str,
        caption: str = "Safe approved local preflight draft.",
        approval_status: str = "approved",
        media_ids: list[str] | None = None,
        safety_flags: list[str] | None = None,
        headline: str = "Useful local title",
        scheduled_for: str = "2026-06-10T13:00:00Z",
        queue_status: str = "waiting",
    ) -> tuple[str, str, str]:
        post_id = f"post-{platform}-{abs(hash((caption, approval_status, headline))) % 1000000}"
        scheduled_id = f"scheduled-{post_id}"
        queue_id = f"queue-{post_id}"
        media_ids = media_ids or []
        safety_flags = safety_flags or []
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO generated_posts (
                  id, brand_profile_id, platform, caption, approval_status,
                  safety_flags_json, generation_provider, headline, media_asset_ids_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    "brand-preflight-test",
                    platform,
                    caption,
                    approval_status,
                    _json(safety_flags),
                    "mock",
                    headline,
                    _json(media_ids),
                ),
            )
            connection.execute(
                """
                INSERT INTO scheduled_posts (
                  id, generated_post_id, brand_profile_id, platform,
                  scheduled_for, timezone, status, caption_snapshot,
                  media_asset_ids_json, schedule_metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scheduled_id,
                    post_id,
                    "brand-preflight-test",
                    platform,
                    scheduled_for,
                    "America/New_York",
                    "scheduled",
                    caption,
                    _json(media_ids),
                    _json(
                        {
                            "headline": headline,
                            "hashtags": ["#Demo"],
                            "callToAction": "Ask about options.",
                            "safetyFlags": safety_flags,
                        }
                    ),
                ),
            )
            connection.execute(
                """
                INSERT INTO publish_queue_items (
                  id, scheduled_post_id, generated_post_id, brand_profile_id,
                  platform, queue_status, due_at, timezone, preflight_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    queue_id,
                    scheduled_id,
                    post_id,
                    "brand-preflight-test",
                    platform,
                    queue_status,
                    scheduled_for,
                    "America/New_York",
                    "not_checked",
                ),
            )
            connection.commit()
        return post_id, scheduled_id, queue_id

    def test_platform_requirement_matrix_contains_all_supported_platforms(self):
        self.assertEqual(
            set(PLATFORM_REQUIREMENT_MATRIX),
            {"instagram", "facebook", "threads", "tiktok", "youtube", "linkedin", "x"},
        )
        self.assertEqual(PLATFORM_REQUIREMENT_MATRIX["instagram"].mediaRequired, True)
        self.assertEqual(PLATFORM_REQUIREMENT_MATRIX["facebook"].mediaRequired, False)
        self.assertEqual(PLATFORM_REQUIREMENT_MATRIX["tiktok"].videoRequired, True)
        self.assertEqual(PLATFORM_REQUIREMENT_MATRIX["youtube"].titleRequired, True)
        self.assertEqual(PLATFORM_REQUIREMENT_MATRIX["x"].maxCaptionLength, 280)

    def test_instagram_without_media_fails(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(db_path, platform="instagram")

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("missing_required_media", result.error_codes)
        self.assertEqual(result.platform, "instagram")
        self.assertEqual(result.requirementVersion, REQUIREMENT_VERSION)

    def test_facebook_text_only_passes_with_missing_account_warning(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(db_path, platform="facebook")

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.errors, [])
        self.assertIn("missing_connected_account", result.warning_codes)
        self.assertEqual(result.accountCheckStatus, "missing_account")
        self.assertIsNone(result.matchedSocialAccountId)
        self.assertEqual(result.connectionStatus, "not_connected")
        self.assertTrue(result.manualExportEligible)
        self.assertFalse(result.realPublishingEligible)

    def test_tiktok_without_video_fails(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="tiktok",
            media_ids=["media-image"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("missing_required_video", result.error_codes)

    def test_youtube_shorts_without_video_fails(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="youtube",
            media_ids=["media-image"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("missing_required_video", result.error_codes)

    def test_x_text_too_long_fails(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="x",
            caption="x" * 281,
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("caption_too_long", result.error_codes)

    def test_linkedin_professional_text_with_optional_media_passes(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="linkedin",
            caption="A practical local service note for property managers.",
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.errors, [])
        self.assertIn("professional_tone_recommended", result.info_codes)

    def test_emergency_pause_fails(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(db_path, platform="facebook")
        update_app_settings(db_path, {"emergencyPauseEnabled": True})

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("emergency_pause_enabled", result.error_codes)

    def test_critical_safety_flag_fails(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="facebook",
            safety_flags=["unsupported_guarantee"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("critical_safety_flags", result.error_codes)

    def test_missing_local_media_record_fails_when_media_required(self):
        db_path = self._database()
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="instagram",
            media_ids=["missing-media-id"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "failed")
        self.assertIn("missing_linked_media", result.error_codes)

    def test_mock_connected_account_satisfies_account_check_but_real_publish_stays_disabled(self):
        db_path = self._database()
        account_id = create_mock_social_account(
            db_path,
            platform="instagram",
            display_name="Mock Instagram Business",
            account_type="business",
            connection_status="connected",
            granted_scopes=["instagram_basic", "pages_show_list"],
        )
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="instagram",
            media_ids=["media-image"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.status, "warning")
        self.assertEqual(result.accountCheckStatus, "connected")
        self.assertEqual(result.matchedSocialAccountId, account_id)
        self.assertEqual(result.connectionStatus, "connected")
        self.assertEqual(result.missingScopes, [])
        self.assertFalse(result.requiresReauth)
        self.assertTrue(result.manualExportEligible)
        self.assertTrue(result.mockPublishEligible)
        self.assertFalse(result.realPublishingEligible)
        self.assertNotIn("missing_connected_account", result.warning_codes)
        self.assertIn("real_publishing_disabled_by_policy", result.warning_codes)

    def test_expired_account_requires_reauth_and_blocks_future_real_publish(self):
        db_path = self._database()
        create_mock_social_account(
            db_path,
            platform="instagram",
            display_name="Expired Instagram Business",
            account_type="business",
            connection_status="expired",
            granted_scopes=["instagram_basic"],
            requires_reauth=True,
        )
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="instagram",
            media_ids=["media-image"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.accountCheckStatus, "requires_reauth")
        self.assertEqual(result.connectionStatus, "expired")
        self.assertTrue(result.requiresReauth)
        self.assertIn("account_requires_reauth", result.warning_codes)
        self.assertIn("account_requires_reauth", result.accountWarnings[0])
        self.assertEqual(result.accountErrors, ["future_real_publish_blocked: Account requires reauth."])
        self.assertTrue(result.manualExportEligible)
        self.assertFalse(result.realPublishingEligible)

    def test_limited_account_missing_scopes_warns_without_blocking_manual_export(self):
        db_path = self._database()
        account_id = create_mock_social_account(
            db_path,
            platform="instagram",
            display_name="Limited Instagram Business",
            account_type="business",
            connection_status="limited",
            granted_scopes=["instagram_basic"],
            missing_scopes=["pages_show_list"],
        )
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="instagram",
            media_ids=["media-image"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.accountCheckStatus, "limited")
        self.assertEqual(result.matchedSocialAccountId, account_id)
        self.assertEqual(result.missingScopes, ["pages_show_list"])
        self.assertIn("missing_account_scopes", result.warning_codes)
        self.assertTrue(result.manualExportEligible)
        self.assertFalse(result.realPublishingEligible)

    def test_disconnected_account_does_not_satisfy_future_real_publish_readiness(self):
        db_path = self._database()
        create_mock_social_account(
            db_path,
            platform="instagram",
            display_name="Disconnected Instagram Business",
            account_type="business",
            connection_status="disconnected",
            granted_scopes=["instagram_basic", "pages_show_list"],
        )
        _, _, queue_id = self._create_scheduled_queue(
            db_path,
            platform="instagram",
            media_ids=["media-image"],
        )

        result = PreflightValidationService(db_path).validate_queue_item(queue_id)

        self.assertEqual(result.accountCheckStatus, "missing_account")
        self.assertEqual(result.connectionStatus, "not_connected")
        self.assertIn("missing_connected_account", result.warning_codes)
        self.assertTrue(result.manualExportEligible)
        self.assertFalse(result.realPublishingEligible)


if __name__ == "__main__":
    unittest.main()
