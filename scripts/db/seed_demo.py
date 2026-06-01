from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.db.init_db import initialize_database, resolve_database_path


DEMO_USER_ID = "demo-user-local-owner"
DEMO_BRAND_ID = "demo-brand-brightside-exterior-care"
DEMO_NOW = "2026-05-26T12:00:00Z"


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _upsert(
    connection: sqlite3.Connection,
    table: str,
    values: dict[str, Any],
    update_columns: list[str] | None = None,
) -> None:
    columns = list(values)
    placeholders = ", ".join("?" for _ in columns)
    column_list = ", ".join(columns)
    update_targets = update_columns or [column for column in columns if column != "id"]
    update_clause = ", ".join(f"{column} = excluded.{column}" for column in update_targets)

    connection.execute(
        f"""
        INSERT INTO {table} ({column_list})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET {update_clause}
        """,
        tuple(values[column] for column in columns),
    )


def seed_demo_database(database_path: str | Path | None = None) -> Path:
    db_path = initialize_database(resolve_database_path(database_path))

    media_assets = [
        {
            "id": "demo-media-driveway-before",
            "media_type": "image",
            "original_path": "data/media/originals/demo-driveway-before.jpg",
            "processed_path": "data/media/processed/demo-driveway-before.webp",
            "thumbnail_path": "data/media/thumbnails/demo-driveway-before.webp",
            "file_name": "demo-driveway-before.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 248000,
            "tags_json": _json(["demo", "driveway", "before"]),
            "job_context_json": _json({
                "service": "pressure washing",
                "serviceType": "pressure washing",
                "stage": "before",
                "locationName": "Demo customer driveway",
                "city": "Demo City",
                "state": "NY",
                "projectDate": "2026-05-01",
                "contentAngle": "before_after",
            }),
            "metadata_json": _json({
                "demo": True,
                "actual_file_required": False,
                "title": "Driveway before cleaning",
                "description": "Before photo of a driveway surface for a transformation post.",
                "qualityRating": 4,
                "usageStatus": "reviewed",
                "notes": "Pair with the after photo. Do not imply guaranteed results.",
            }),
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-media-driveway-after",
            "media_type": "image",
            "original_path": "data/media/originals/demo-driveway-after.jpg",
            "processed_path": "data/media/processed/demo-driveway-after.webp",
            "thumbnail_path": "data/media/thumbnails/demo-driveway-after.webp",
            "file_name": "demo-driveway-after.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 263000,
            "tags_json": _json(["demo", "driveway", "after"]),
            "job_context_json": _json({
                "service": "pressure washing",
                "serviceType": "pressure washing",
                "stage": "after",
                "locationName": "Demo customer driveway",
                "city": "Demo City",
                "state": "NY",
                "projectDate": "2026-05-01",
                "contentAngle": "before_after",
            }),
            "metadata_json": _json({
                "demo": True,
                "actual_file_required": False,
                "title": "Driveway after cleaning",
                "description": "After photo showing a cleaner driveway surface for a before/after draft.",
                "qualityRating": 5,
                "usageStatus": "ready_for_generation",
                "notes": "Use with the before image and avoid unsupported claims.",
            }),
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-media-gutter-cleaning",
            "media_type": "image",
            "original_path": "data/media/originals/demo-gutter-cleaning.jpg",
            "processed_path": "data/media/processed/demo-gutter-cleaning.webp",
            "thumbnail_path": "data/media/thumbnails/demo-gutter-cleaning.webp",
            "file_name": "demo-gutter-cleaning.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 196000,
            "tags_json": _json(["demo", "gutters", "maintenance"]),
            "job_context_json": _json({
                "service": "gutter cleaning",
                "serviceType": "gutter cleaning",
                "season": "spring",
                "locationName": "Demo residential exterior",
                "city": "Demo City",
                "state": "NY",
                "projectDate": "2026-05-04",
                "contentAngle": "educational",
            }),
            "metadata_json": _json({
                "demo": True,
                "actual_file_required": False,
                "title": "Gutter cleaning detail",
                "description": "Close-up maintenance photo for an educational seasonal reminder.",
                "qualityRating": 4,
                "usageStatus": "reviewed",
                "notes": "Good for explaining why seasonal maintenance matters.",
            }),
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-media-soft-wash-siding",
            "media_type": "image",
            "original_path": "data/media/originals/demo-soft-wash-siding.jpg",
            "processed_path": "data/media/processed/demo-soft-wash-siding.webp",
            "thumbnail_path": "data/media/thumbnails/demo-soft-wash-siding.webp",
            "file_name": "demo-soft-wash-siding.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 221000,
            "tags_json": _json(["demo", "siding", "soft wash"]),
            "job_context_json": _json({
                "service": "soft washing",
                "serviceType": "soft washing",
                "surface": "vinyl siding",
                "locationName": "Demo siding project",
                "city": "Demo City",
                "state": "NY",
                "projectDate": "2026-05-08",
                "contentAngle": "trust_builder",
            }),
            "metadata_json": _json({
                "demo": True,
                "actual_file_required": False,
                "title": "Soft wash siding detail",
                "description": "Surface-safe exterior cleaning example for a trust-building post.",
                "qualityRating": 4,
                "usageStatus": "new",
                "notes": "Mention careful surface selection, not guaranteed outcomes.",
            }),
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-media-crew-setup",
            "media_type": "image",
            "original_path": "data/media/originals/demo-crew-setup.jpg",
            "processed_path": "data/media/processed/demo-crew-setup.webp",
            "thumbnail_path": "data/media/thumbnails/demo-crew-setup.webp",
            "file_name": "demo-crew-setup.jpg",
            "mime_type": "image/jpeg",
            "file_size_bytes": 188000,
            "tags_json": _json(["demo", "behind the scenes", "equipment"]),
            "job_context_json": _json({
                "service": "exterior cleaning",
                "serviceType": "exterior cleaning",
                "stage": "setup",
                "locationName": "Demo job setup",
                "city": "Demo City",
                "state": "NY",
                "projectDate": "2026-05-10",
                "contentAngle": "behind_the_scenes",
            }),
            "metadata_json": _json({
                "demo": True,
                "actual_file_required": False,
                "title": "Crew setup before service",
                "description": "Behind-the-scenes setup photo for showing process and care.",
                "qualityRating": 3,
                "usageStatus": "new",
                "notes": "Useful for showing process without naming customers.",
            }),
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
    ]

    content_ideas = [
        {
            "id": "demo-idea-before-after-driveway",
            "brand_profile_id": DEMO_BRAND_ID,
            "goal": "show_transformation",
            "angle": "before_after",
            "target_platforms_json": _json(["facebook", "instagram"]),
            "media_asset_ids_json": _json(["demo-media-driveway-before", "demo-media-driveway-after"]),
            "notes": "Demo idea: show a clear exterior cleaning transformation without making unsupported claims.",
            "status": "used",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-idea-gutter-seasonal",
            "brand_profile_id": DEMO_BRAND_ID,
            "goal": "seasonal_reminder",
            "angle": "educational",
            "target_platforms_json": _json(["facebook", "linkedin"]),
            "media_asset_ids_json": _json(["demo-media-gutter-cleaning"]),
            "notes": "Demo idea: remind homeowners to check gutters before heavy rain season.",
            "status": "used",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-idea-behind-scenes",
            "brand_profile_id": DEMO_BRAND_ID,
            "goal": "build_trust",
            "angle": "behind_the_scenes",
            "target_platforms_json": _json(["instagram", "threads"]),
            "media_asset_ids_json": _json(["demo-media-crew-setup"]),
            "notes": "Demo idea: show preparation and care before a job starts.",
            "status": "open",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
    ]

    generated_posts = [
        {
            "id": "demo-post-driveway-transformation",
            "content_idea_id": "demo-idea-before-after-driveway",
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "instagram",
            "caption": (
                "Demo draft: A clean driveway can make the whole entrance feel brighter. "
                "Here is a sample before/after concept for an exterior cleaning post."
            ),
            "hashtags_json": _json(["#DemoPost", "#ExteriorCleaning", "#DrivewayCleaning"]),
            "media_asset_ids_json": _json(["demo-media-driveway-before", "demo-media-driveway-after"]),
            "approval_status": "approved",
            "safety_flags_json": _json([]),
            "generation_provider": "mock",
            "prompt_metadata_json": _json({"prompt_id": "platform_post_generator_v1", "demo": True}),
            "provider_metadata_json": _json({"provider": "mock", "demo": True}),
            "last_scheduled_at": "2026-06-02T14:00:00Z",
            "publish_readiness_status": "manually_exported",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-post-gutter-reminder",
            "content_idea_id": "demo-idea-gutter-seasonal",
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "facebook",
            "caption": (
                "Demo draft: Spring rain is easier to handle when gutters are clear. "
                "This sample post reminds local homeowners to look for clogs, overflow, and downspout issues."
            ),
            "hashtags_json": _json(["#DemoPost", "#GutterCleaning", "#HomeMaintenance"]),
            "media_asset_ids_json": _json(["demo-media-gutter-cleaning"]),
            "approval_status": "approved",
            "safety_flags_json": _json([]),
            "generation_provider": "mock",
            "prompt_metadata_json": _json({"prompt_id": "platform_post_generator_v1", "demo": True}),
            "provider_metadata_json": _json({"provider": "mock", "demo": True}),
            "last_scheduled_at": "2026-06-05T13:30:00Z",
            "publish_readiness_status": "waiting",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-post-crew-prep",
            "content_idea_id": "demo-idea-behind-scenes",
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "threads",
            "caption": (
                "Demo draft: The careful setup before a job matters. This sample post shows equipment prep, "
                "surface checks, and a simple local-service workflow."
            ),
            "hashtags_json": _json(["#DemoPost", "#BehindTheScenes", "#LocalServiceBusiness"]),
            "media_asset_ids_json": _json(["demo-media-crew-setup"]),
            "approval_status": "needs_review",
            "safety_flags_json": _json([]),
            "generation_provider": "mock",
            "prompt_metadata_json": _json({"prompt_id": "platform_post_generator_v1", "demo": True}),
            "provider_metadata_json": _json({"provider": "mock", "demo": True}),
            "last_scheduled_at": None,
            "publish_readiness_status": "not_scheduled",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
    ]

    scheduled_posts = [
        {
            "id": "demo-scheduled-driveway-transformation",
            "generated_post_id": "demo-post-driveway-transformation",
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "instagram",
            "scheduled_for": "2026-06-02T14:00:00Z",
            "timezone": "America/New_York",
            "status": "completed",
            "caption_snapshot": generated_posts[0]["caption"],
            "media_asset_ids_json": _json(["demo-media-driveway-before", "demo-media-driveway-after"]),
            "media_snapshot_json": _json(["demo-media-driveway-before", "demo-media-driveway-after"]),
            "platform_account_id": None,
            "publish_queue_item_id": "demo-queue-driveway-transformation",
            "recurrence_rule": None,
            "is_recurring_template": 0,
            "user_notes": "Demo scheduled item that was manually exported locally.",
            "preflight_snapshot_json": _json({"demo": True, "errors": [], "warnings": ["manual export only"], "real_platform_publish": False}),
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
            "canceled_at": None,
        },
        {
            "id": "demo-scheduled-gutter-reminder",
            "generated_post_id": "demo-post-gutter-reminder",
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "facebook",
            "scheduled_for": "2026-06-05T13:30:00Z",
            "timezone": "America/New_York",
            "status": "scheduled",
            "caption_snapshot": generated_posts[1]["caption"],
            "media_asset_ids_json": _json(["demo-media-gutter-cleaning"]),
            "media_snapshot_json": _json(["demo-media-gutter-cleaning"]),
            "platform_account_id": None,
            "publish_queue_item_id": "demo-queue-gutter-reminder",
            "recurrence_rule": None,
            "is_recurring_template": 0,
            "user_notes": "Demo scheduled item waiting for future local queue processing.",
            "preflight_snapshot_json": _json({"demo": True, "errors": [], "warnings": ["manual export only"], "real_platform_publish": False}),
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
            "canceled_at": None,
        },
    ]

    publish_queue_items = [
        {
            "id": "demo-queue-driveway-transformation",
            "scheduled_post_id": "demo-scheduled-driveway-transformation",
            "generated_post_id": "demo-post-driveway-transformation",
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "instagram",
            "queue_status": "manually_exported",
            "due_at": "2026-06-02T14:00:00Z",
            "timezone": "America/New_York",
            "priority": 100,
            "preflight_status": "passed",
            "preflight_errors_json": _json([]),
            "preflight_warnings_json": _json(["Manual export only. No real platform API publishing."]),
            "mock_publish_enabled": 0,
            "manual_export_required": 1,
            "last_checked_at": "2026-06-02T13:55:00Z",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
        {
            "id": "demo-queue-gutter-reminder",
            "scheduled_post_id": "demo-scheduled-gutter-reminder",
            "generated_post_id": "demo-post-gutter-reminder",
            "brand_profile_id": DEMO_BRAND_ID,
            "platform": "facebook",
            "queue_status": "waiting",
            "due_at": "2026-06-05T13:30:00Z",
            "timezone": "America/New_York",
            "priority": 100,
            "preflight_status": "passed",
            "preflight_errors_json": _json([]),
            "preflight_warnings_json": _json(["Manual export only. No real platform API publishing."]),
            "mock_publish_enabled": 0,
            "manual_export_required": 1,
            "last_checked_at": "2026-05-26T12:05:00Z",
            "created_at": DEMO_NOW,
            "updated_at": DEMO_NOW,
        },
    ]

    publish_attempts = [
        {
            "id": "demo-attempt-driveway-manual-export",
            "publish_queue_item_id": "demo-queue-driveway-transformation",
            "scheduled_post_id": "demo-scheduled-driveway-transformation",
            "platform": "instagram",
            "attempt_type": "manual_export",
            "attempt_status": "succeeded",
            "started_at": "2026-06-02T14:05:00Z",
            "finished_at": "2026-06-02T14:10:00Z",
            "error_code": None,
            "error_message": None,
            "provider_response_json": _json({
                "demo": True,
                "real_platform_publish": False,
                "note": "Manual export package recorded locally. No API call was made.",
            }),
            "created_at": DEMO_NOW,
        },
        {
            "id": "demo-attempt-gutter-preflight",
            "publish_queue_item_id": "demo-queue-gutter-reminder",
            "scheduled_post_id": "demo-scheduled-gutter-reminder",
            "platform": "facebook",
            "attempt_type": "preflight",
            "attempt_status": "started",
            "started_at": "2026-05-26T12:05:00Z",
            "finished_at": None,
            "error_code": None,
            "error_message": None,
            "provider_response_json": _json({
                "demo": True,
                "real_platform_publish": False,
                "note": "Preflight placeholder for local queue readiness.",
            }),
            "created_at": DEMO_NOW,
        },
    ]

    approval_logs = [
        {
            "id": "demo-approval-generated-driveway",
            "entity_type": "generated_post",
            "entity_id": "demo-post-driveway-transformation",
            "action": "approved",
            "actor_label": "demo_local_user",
            "notes": "Demo approval record. No real post was sent.",
            "changed_fields_json": _json({"approval_status": "approved"}),
            "created_at": DEMO_NOW,
        },
        {
            "id": "demo-approval-generated-gutter",
            "entity_type": "generated_post",
            "entity_id": "demo-post-gutter-reminder",
            "action": "approved",
            "actor_label": "demo_local_user",
            "notes": "Demo approval record. No real post was sent.",
            "changed_fields_json": _json({"approval_status": "approved"}),
            "created_at": DEMO_NOW,
        },
        {
            "id": "demo-approval-generated-crew-prep",
            "entity_type": "generated_post",
            "entity_id": "demo-post-crew-prep",
            "action": "created_needs_review",
            "actor_label": "mock_ai_provider",
            "notes": "Demo draft awaits local human review.",
            "changed_fields_json": _json({"approval_status": "needs_review"}),
            "created_at": DEMO_NOW,
        },
        {
            "id": "demo-approval-scheduled-driveway",
            "entity_type": "scheduled_post",
            "entity_id": "demo-scheduled-driveway-transformation",
            "action": "scheduled_after_approval",
            "actor_label": "demo_local_user",
            "notes": "Demo schedule record for dashboard placeholders.",
            "changed_fields_json": _json({"status": "completed"}),
            "created_at": DEMO_NOW,
        },
        {
            "id": "demo-approval-scheduled-gutter",
            "entity_type": "scheduled_post",
            "entity_id": "demo-scheduled-gutter-reminder",
            "action": "scheduled_after_approval",
            "actor_label": "demo_local_user",
            "notes": "Demo schedule record for dashboard placeholders.",
            "changed_fields_json": _json({"status": "scheduled"}),
            "created_at": DEMO_NOW,
        },
    ]

    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        _upsert(
            connection,
            "users",
            {
                "id": DEMO_USER_ID,
                "display_name": "Demo Local Owner",
                "email": "demo-owner@example.local",
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "brand_profiles",
            {
                "id": DEMO_BRAND_ID,
                "user_id": DEMO_USER_ID,
                "business_name": "Brightside Exterior Care Demo",
                "description": (
                    "Fake demo profile for a local exterior cleaning service. "
                    "Used only for development and UI placeholders."
                ),
                "voice": "Helpful, neighborly, practical, and safety-conscious.",
                "services_json": _json(["pressure washing", "soft washing", "gutter cleaning"]),
                "locations_json": _json(["Demo City", "Nearby service areas"]),
                "target_audience": "Local homeowners and small property managers.",
                "supported_claims_json": _json(
                    [
                        "Uses careful surface checks before cleaning",
                        "Offers exterior cleaning and maintenance reminders",
                    ]
                ),
                "blocked_phrases_json": _json(
                    [
                        "guaranteed results",
                        "best in the city",
                        "real customer said",
                    ]
                ),
                "preferences_json": _json(
                    {
                        "demo": True,
                        "avoid_fake_social_proof": True,
                        "tagline": "Cleaner curb appeal, handled with care.",
                        "industry": "Exterior cleaning",
                        "targetCustomers": [
                            "local homeowners",
                            "small property managers",
                            "real estate listing teams",
                        ],
                        "toneRules": [
                            "Use practical local-service language.",
                            "Avoid hype, pressure, and unsupported superlatives.",
                            "Explain safety limits clearly.",
                        ],
                        "preferredWords": ["careful", "local", "clean", "seasonal"],
                        "commonCTAs": [
                            "Request a demo estimate",
                            "Ask about exterior cleaning options",
                        ],
                        "hashtags": [
                            "#DemoBusiness",
                            "#ExteriorCleaning",
                            "#LocalServiceBusiness",
                        ],
                        "website": "https://example.local/brightside-demo",
                        "phone": "555-0100",
                        "email": "hello@brightside-demo.example",
                        "approvalRules": [
                            "Owner approves every generated draft before scheduling.",
                            "Edited approved drafts require review before publishing.",
                        ],
                        "safetyRules": [
                            "Never invent testimonials.",
                            "Never invent prices, certifications, guarantees, or availability.",
                            "Do not imply a post was sent when it is only a draft.",
                        ],
                        "examplePosts": [
                            "Demo post: Spring is a good time to check siding, gutters, and walkways before heavy rain.",
                            "Demo post: A careful exterior cleaning plan starts with looking at the surface before choosing pressure.",
                        ],
                    }
                ),
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "app_settings",
            {
                "id": "default",
                "user_id": DEMO_USER_ID,
                "automation_level": "approval_queue",
                "require_approval_before_publishing": 1,
                "require_approval_before_replying": 1,
                "emergency_pause_enabled": 0,
                "kill_switch_enabled": 0,
                "integrations_mode": "mock",
                "enable_real_network_calls": 0,
                "enable_real_oauth": 0,
                "enable_real_publishing": 0,
                "token_storage_mode": "placeholder_not_stored",
                "settings_json": _json({"demo_seeded": True}),
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "social_accounts",
            {
                "id": "demo-social-facebook-page",
                "brand_profile_id": DEMO_BRAND_ID,
                "platform": "facebook",
                "platform_account_id": "mock-facebook-page-brightside-demo",
                "display_name": "Brightside Demo Facebook Page",
                "username": "brightside-demo",
                "profile_url": "https://example.local/mock-facebook-page",
                "profile_image_url": None,
                "account_type": "page",
                "connection_status": "connected",
                "capabilities_json": _json(
                    {
                        "canConnect": True,
                        "canReadProfile": True,
                        "canPublishText": False,
                        "canPublishImage": False,
                        "canPublishVideo": False,
                        "supportsManualExportFallback": True,
                        "realPublishingEnabled": False,
                    }
                ),
                "granted_scopes_json": _json(["pages_show_list"]),
                "missing_scopes_json": _json(["pages_manage_posts"]),
                "requires_reauth": 0,
                "last_connected_at": DEMO_NOW,
                "last_validated_at": DEMO_NOW,
                "disconnected_at": None,
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "platform_tokens",
            {
                "id": "demo-token-facebook-page-placeholder",
                "social_account_id": "demo-social-facebook-page",
                "platform": "facebook",
                "token_type": "page_access",
                "encrypted_access_token": None,
                "encrypted_refresh_token": None,
                "access_token_expires_at": None,
                "refresh_token_expires_at": None,
                "scope": "pages_show_list",
                "token_version": 1,
                "encryption_status": "placeholder_not_stored",
                "last_refresh_at": None,
                "revoked_at": None,
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        for connector_audit_log in [
            {
                "id": "demo-connector-audit-facebook-oauth-start",
                "platform": "facebook",
                "social_account_id": "demo-social-facebook-page",
                "action": "oauth_start",
                "status": "succeeded",
                "message": "Mock Facebook connection started locally. No real OAuth request was sent.",
                "safe_metadata_json": _json(
                    {"demo": True, "real_oauth": False, "token_storage": "placeholder_not_stored"}
                ),
                "created_at": DEMO_NOW,
            },
            {
                "id": "demo-connector-audit-facebook-validate",
                "platform": "facebook",
                "social_account_id": "demo-social-facebook-page",
                "action": "connection_validate",
                "status": "succeeded",
                "message": "Mock Facebook connection validated locally. No platform API was called.",
                "safe_metadata_json": _json(
                    {"demo": True, "real_network_call": False, "real_publishing": False}
                ),
                "created_at": DEMO_NOW,
            },
        ]:
            _upsert(connection, "connector_audit_logs", connector_audit_log)

        _upsert(
            connection,
            "connector_health_checks",
            {
                "id": "demo-connector-health-facebook-page",
                "platform": "facebook",
                "social_account_id": "demo-social-facebook-page",
                "health_status": "mock_connected",
                "feature_status": "mock_only",
                "message": "Mock account is available for UI demos. Real publishing remains disabled.",
                "safe_metadata_json": _json({"demo": True, "real_network_call": False}),
                "checked_at": DEMO_NOW,
                "created_at": DEMO_NOW,
            },
        )

        for media_asset in media_assets:
            _upsert(connection, "media_assets", media_asset)

        for content_idea in content_ideas:
            _upsert(connection, "content_ideas", content_idea)

        for generated_post in generated_posts:
            _upsert(connection, "generated_posts", generated_post)

        for scheduled_post in scheduled_posts:
            _upsert(connection, "scheduled_posts", scheduled_post)

        for publish_queue_item in publish_queue_items:
            _upsert(connection, "publish_queue_items", publish_queue_item)

        for publish_attempt in publish_attempts:
            _upsert(connection, "publish_attempts", publish_attempt)

        _upsert(
            connection,
            "published_posts",
            {
                "id": "demo-published-driveway-export",
                "scheduled_post_id": "demo-scheduled-driveway-transformation",
                "generated_post_id": "demo-post-driveway-transformation",
                "platform": "instagram",
                "publish_mode": "manual_export",
                "external_post_id": None,
                "permalink": None,
                "published_at": "2026-06-02T14:10:00Z",
                "metadata_json": _json(
                    {
                        "demo": True,
                        "real_platform_publish": False,
                        "note": "Represents a manually exported demo post, not an API publish.",
                    }
                ),
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "analytics_snapshots",
            {
                "id": "demo-analytics-driveway-export",
                "published_post_id": "demo-published-driveway-export",
                "scheduled_post_id": "demo-scheduled-driveway-transformation",
                "generated_post_id": "demo-post-driveway-transformation",
                "brand_profile_id": DEMO_BRAND_ID,
                "platform": "instagram",
                "source": "mock",
                "snapshot_date": "2026-06-09T12:00:00Z",
                "impressions": 1240,
                "reach": 980,
                "views": 0,
                "likes": 42,
                "comments": 5,
                "shares": 7,
                "saves": 9,
                "clicks": 13,
                "profile_visits": 18,
                "follows": 3,
                "leads": 2,
                "messages": 1,
                "calls": 1,
                "website_clicks": 8,
                "engagement_rate": 0.0643,
                "click_through_rate": 0.0105,
                "lead_rate": 0.1538,
                "raw_metrics_json": _json(
                    {
                        "demo": True,
                        "engagement_rate": 0.0643,
                        "note": "Mock analytics for development only.",
                    }
                ),
                "notes": "Clearly fake mock metrics for local dashboard development.",
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "post_performance_metrics",
            {
                "id": "demo-performance-driveway-export",
                "generated_post_id": "demo-post-driveway-transformation",
                "scheduled_post_id": "demo-scheduled-driveway-transformation",
                "published_post_id": "demo-published-driveway-export",
                "brand_profile_id": DEMO_BRAND_ID,
                "platform": "instagram",
                "content_goal": "show_transformation",
                "content_angle": "before_after",
                "media_asset_ids_json": _json(
                    ["demo-media-driveway-before", "demo-media-driveway-after"]
                ),
                "posted_at": "2026-06-02T14:10:00Z",
                "first_snapshot_at": "2026-06-09T12:00:00Z",
                "latest_snapshot_at": "2026-06-09T12:00:00Z",
                "total_impressions": 1240,
                "total_reach": 980,
                "total_views": 0,
                "total_likes": 42,
                "total_comments": 5,
                "total_shares": 7,
                "total_saves": 9,
                "total_clicks": 13,
                "total_leads": 2,
                "engagement_rate": 0.0643,
                "lead_rate": 0.1538,
                "performance_score": 72.5,
                "trend": "improving",
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "analytics_imports",
            {
                "id": "demo-analytics-import-mock-sync",
                "source": "mock",
                "platform": "instagram",
                "import_type": "mock_sync",
                "status": "completed",
                "records_imported": 1,
                "records_skipped": 0,
                "error_message": None,
                "imported_at": "2026-06-09T12:00:00Z",
                "created_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "content_insights",
            {
                "id": "demo-insight-before-after",
                "brand_profile_id": DEMO_BRAND_ID,
                "insight_type": "best_content_type",
                "title": "Before-and-after content may be worth testing",
                "summary": (
                    "Demo-only early signal from one mock post. Collect more real manual "
                    "results before treating this as a reliable pattern."
                ),
                "evidence_json": _json(
                    {
                        "demo": True,
                        "data_points": 1,
                        "analytics_snapshot_ids": ["demo-analytics-driveway-export"],
                    }
                ),
                "confidence": "low",
                "related_post_ids_json": _json(["demo-published-driveway-export"]),
                "related_media_asset_ids_json": _json(
                    ["demo-media-driveway-before", "demo-media-driveway-after"]
                ),
                "recommended_action": (
                    "Try another reviewed before-and-after draft and compare manual results."
                ),
                "status": "active",
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "ai_memory",
            {
                "id": "demo-memory-before-after",
                "brand_profile_id": DEMO_BRAND_ID,
                "memory_type": "performance_learning",
                "summary": (
                    "Demo-only early signal: transformation posts may be worth testing again."
                ),
                "title": "Before-and-after posts may be useful",
                "content": (
                    "Demo-only early signal: transformation posts may be worth testing again."
                ),
                "confidence": "low",
                "evidence_json": _json(
                    {
                        "demo": True,
                        "data_points": 1,
                        "content_insight_ids": ["demo-insight-before-after"],
                    }
                ),
                "source": "mock",
                "status": "active",
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        _upsert(
            connection,
            "weekly_reports",
            {
                "id": "demo-weekly-report-2026-06-08",
                "brand_profile_id": DEMO_BRAND_ID,
                "week_start_date": "2026-06-08",
                "week_end_date": "2026-06-14",
                "summary": (
                    "Demo weekly report based on fake local metrics for dashboard development."
                ),
                "wins_json": _json(
                    ["Demo transformation post created a useful baseline for comparison."]
                ),
                "concerns_json": _json(
                    ["Only one mock data point exists, so confidence remains low."]
                ),
                "recommendations_json": _json(
                    ["Collect manual metrics for the next approved transformation post."]
                ),
                "top_posts_json": _json(["demo-published-driveway-export"]),
                "platform_breakdown_json": _json(
                    {"demo": True, "instagram": {"posts": 1, "leads": 2}}
                ),
                "metric_totals_json": _json(
                    {
                        "demo": True,
                        "impressions": 1240,
                        "engagements": 63,
                        "leads": 2,
                    }
                ),
                "generated_by": "ai_mock",
                "created_at": DEMO_NOW,
                "updated_at": DEMO_NOW,
            },
        )

        for approval_log in approval_logs:
            _upsert(connection, "approval_logs", approval_log)

        connection.commit()

    return db_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the local SQLite database with safe fake demo data."
    )
    parser.add_argument(
        "--database",
        help="Path to the SQLite database. Defaults to DATABASE_URL or data/app.sqlite.",
    )
    args = parser.parse_args()

    db_path = seed_demo_database(args.database)
    print(f"Seeded safe demo data in {db_path}")


if __name__ == "__main__":
    main()
