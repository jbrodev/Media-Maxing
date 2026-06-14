from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.ai.platform_limits import caption_limit_for
from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.settings import load_app_settings
from scripts.connectors.registry import get_connector
from scripts.connectors.registry import ConnectorRegistryError
from scripts.services.approval_queue import CRITICAL_SAFETY_FLAGS


REQUIREMENT_VERSION = "mvp-platform-requirements-v1"
PREFLIGHTABLE_QUEUE_STATUSES = {"waiting", "ready", "blocked"}


@dataclass(frozen=True)
class PlatformRequirement:
    platform: str
    label: str
    mediaRequired: bool
    supportedMediaTypes: tuple[str, ...]
    maxCaptionLength: int
    hashtagRecommendation: str
    altTextRecommendation: str
    videoRequired: bool
    titleRequired: bool
    descriptionRequired: bool
    accountConnectionRequiredForFuturePublishing: bool
    notes: str


# TODO: Verify exact platform API limits, supported media combinations, aspect
# ratios, carousel support, and account requirements when real connectors are
# implemented. These are practical MVP placeholders only.
PLATFORM_REQUIREMENT_MATRIX: dict[str, PlatformRequirement] = {
    "instagram": PlatformRequirement(
        platform="instagram",
        label="Instagram",
        mediaRequired=True,
        supportedMediaTypes=("image", "video"),
        maxCaptionLength=caption_limit_for("instagram"),
        hashtagRecommendation="Allowed; a small relevant set is recommended.",
        altTextRecommendation="Recommended when media is present.",
        videoRequired=False,
        titleRequired=False,
        descriptionRequired=False,
        accountConnectionRequiredForFuturePublishing=True,
        notes="Carousel and exact media rules are future API work.",
    ),
    "facebook": PlatformRequirement(
        platform="facebook",
        label="Facebook",
        mediaRequired=False,
        supportedMediaTypes=("image", "video"),
        maxCaptionLength=caption_limit_for("facebook"),
        hashtagRecommendation="Optional; keep them light.",
        altTextRecommendation="Recommended when media is present.",
        videoRequired=False,
        titleRequired=False,
        descriptionRequired=False,
        accountConnectionRequiredForFuturePublishing=True,
        notes="Text-only posts are acceptable for MVP preflight.",
    ),
    "threads": PlatformRequirement(
        platform="threads",
        label="Threads",
        mediaRequired=False,
        supportedMediaTypes=("image", "video"),
        maxCaptionLength=caption_limit_for("threads"),
        hashtagRecommendation="Optional; concise text is preferred.",
        altTextRecommendation="Recommended when media is present.",
        videoRequired=False,
        titleRequired=False,
        descriptionRequired=False,
        accountConnectionRequiredForFuturePublishing=True,
        notes="Short conversational text is preferred.",
    ),
    "tiktok": PlatformRequirement(
        platform="tiktok",
        label="TikTok",
        mediaRequired=True,
        supportedMediaTypes=("video",),
        maxCaptionLength=caption_limit_for("tiktok"),
        hashtagRecommendation="Allowed; keep relevant.",
        altTextRecommendation="Not primary for MVP; captions and accessibility metadata are future work.",
        videoRequired=True,
        titleRequired=False,
        descriptionRequired=False,
        accountConnectionRequiredForFuturePublishing=True,
        notes="Vertical video is preferred but not enforced until video metadata exists.",
    ),
    "youtube": PlatformRequirement(
        platform="youtube",
        label="YouTube Shorts",
        mediaRequired=True,
        supportedMediaTypes=("video",),
        maxCaptionLength=caption_limit_for("youtube"),
        hashtagRecommendation="Allowed in description; keep relevant.",
        altTextRecommendation="Not primary for Shorts MVP.",
        videoRequired=True,
        titleRequired=True,
        descriptionRequired=False,
        accountConnectionRequiredForFuturePublishing=True,
        notes="Vertical video is preferred but not enforced until video metadata exists.",
    ),
    "linkedin": PlatformRequirement(
        platform="linkedin",
        label="LinkedIn",
        mediaRequired=False,
        supportedMediaTypes=("image", "video"),
        maxCaptionLength=caption_limit_for("linkedin"),
        hashtagRecommendation="Recommended but limited; use a small professional set.",
        altTextRecommendation="Recommended when media is present.",
        videoRequired=False,
        titleRequired=False,
        descriptionRequired=False,
        accountConnectionRequiredForFuturePublishing=True,
        notes="Professional tone is recommended.",
    ),
    "x": PlatformRequirement(
        platform="x",
        label="X",
        mediaRequired=False,
        supportedMediaTypes=("image", "video"),
        maxCaptionLength=caption_limit_for("x"),
        hashtagRecommendation="Optional; short text budget.",
        altTextRecommendation="Recommended when media is present.",
        videoRequired=False,
        titleRequired=False,
        descriptionRequired=False,
        accountConnectionRequiredForFuturePublishing=True,
        notes="Strict short-text placeholder limit for MVP.",
    ),
}


@dataclass(frozen=True)
class PreflightValidationResult:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    checkedAt: str = ""
    platform: str = ""
    requirementVersion: str = REQUIREMENT_VERSION
    accountCheckStatus: str = "not_checked"
    matchedSocialAccountId: str | None = None
    accountWarnings: list[str] = field(default_factory=list)
    accountErrors: list[str] = field(default_factory=list)
    missingScopes: list[str] = field(default_factory=list)
    requiresReauth: bool = False
    connectionStatus: str = "not_connected"
    realPublishingEligible: bool = False
    manualExportEligible: bool = False
    mockPublishEligible: bool = False

    @property
    def passed(self) -> bool:
        return not self.errors

    @property
    def error_codes(self) -> list[str]:
        return [_message_code(message) for message in self.errors]

    @property
    def warning_codes(self) -> list[str]:
        return [_message_code(message) for message in self.warnings]

    @property
    def info_codes(self) -> list[str]:
        return [_message_code(message) for message in self.info]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
            "checkedAt": self.checkedAt,
            "platform": self.platform,
            "requirementVersion": self.requirementVersion,
            "accountCheckStatus": self.accountCheckStatus,
            "matchedSocialAccountId": self.matchedSocialAccountId,
            "accountWarnings": self.accountWarnings,
            "accountErrors": self.accountErrors,
            "missingScopes": self.missingScopes,
            "requiresReauth": self.requiresReauth,
            "connectionStatus": self.connectionStatus,
            "realPublishingEligible": self.realPublishingEligible,
            "manualExportEligible": self.manualExportEligible,
            "mockPublishEligible": self.mockPublishEligible,
        }


@dataclass(frozen=True)
class AccountReadiness:
    accountCheckStatus: str
    matchedSocialAccountId: str | None = None
    accountWarnings: list[str] = field(default_factory=list)
    accountErrors: list[str] = field(default_factory=list)
    missingScopes: list[str] = field(default_factory=list)
    requiresReauth: bool = False
    connectionStatus: str = "not_connected"


class PreflightValidationError(ValueError):
    pass


class PreflightValidationService:
    """Local-only preflight checks for scheduled posts and queue items.

    This service validates local SQLite records against an MVP platform
    requirement matrix. It never calls social APIs, checks live platform docs,
    publishes content, or requires credentials.
    """

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))

    def validate_queue_item(
        self,
        queue_item_id: str,
        *,
        checked_at: str | datetime | None = None,
    ) -> PreflightValidationResult:
        queue_row = self._require_queue_row(queue_item_id)
        scheduled_row = self._scheduled_row(queue_row["scheduled_post_id"])
        if scheduled_row is None:
            return self._result(
                platform=queue_row["platform"],
                checked_at=checked_at,
                errors=["missing_scheduled_post: Queue item has no scheduled post."],
                warnings=[],
                info=[],
                account_readiness=AccountReadiness("not_checked"),
            )
        return self._validate(queue_row, scheduled_row, checked_at=checked_at)

    def validate_scheduled_post(
        self,
        scheduled_post_id: str,
        *,
        checked_at: str | datetime | None = None,
    ) -> PreflightValidationResult:
        scheduled_row = self._require_scheduled_row(scheduled_post_id)
        queue_row = self._queue_row_for_scheduled(scheduled_post_id)
        if queue_row is None:
            return self._result(
                platform=scheduled_row["platform"],
                checked_at=checked_at,
                errors=["missing_publish_queue_item: Scheduled post has no queue item."],
                warnings=[],
                info=[],
                account_readiness=AccountReadiness("not_checked"),
            )
        return self._validate(queue_row, scheduled_row, checked_at=checked_at)

    def _validate(
        self,
        queue_row: sqlite3.Row,
        scheduled_row: sqlite3.Row,
        *,
        checked_at: str | datetime | None,
    ) -> PreflightValidationResult:
        errors: list[str] = []
        warnings: list[str] = [
            "manual_export_only: Manual export is the safe path; real publishing remains disabled."
        ]
        info: list[str] = []

        platform = scheduled_row["platform"]
        requirement = PLATFORM_REQUIREMENT_MATRIX.get(platform)
        if requirement is None:
            return self._result(
                platform=platform,
                checked_at=checked_at,
                errors=["unsupported_platform: Platform is not supported by the MVP matrix."],
                warnings=warnings,
                info=info,
                account_readiness=AccountReadiness("unsupported_platform"),
            )

        settings = load_app_settings(self.database_path)
        if settings.emergencyPauseEnabled:
            errors.append("emergency_pause_enabled: Emergency pause blocks readiness.")

        queue_status = queue_row["queue_status"]
        if queue_status not in PREFLIGHTABLE_QUEUE_STATUSES:
            errors.append(
                f"queue_status_not_preflightable: Queue status {queue_status} cannot be preflighted."
            )

        if scheduled_row["status"] in {"canceled", "completed", "missed"}:
            errors.append(
                f"scheduled_post_{scheduled_row['status']}: Scheduled post is not active."
            )

        scheduled_for = scheduled_row["scheduled_for"]
        if not scheduled_for or not str(scheduled_for).strip():
            errors.append("missing_scheduled_time: Scheduled time is required.")

        draft_row = self._generated_post_row(scheduled_row["generated_post_id"])
        if draft_row is None:
            errors.append("missing_generated_post: Source draft does not exist.")
        else:
            self._validate_draft_status(draft_row, errors)

        if not self._brand_exists(scheduled_row["brand_profile_id"]):
            errors.append("missing_brand_profile: Scheduled brand profile does not exist.")

        caption = scheduled_row["caption_snapshot"] or ""
        if not caption.strip():
            errors.append("missing_caption: Caption/text is required.")
        elif len(caption) > requirement.maxCaptionLength:
            errors.append(
                f"caption_too_long: Caption is {len(caption)} characters; "
                f"{requirement.label} allows up to {requirement.maxCaptionLength}."
            )

        schedule_metadata = _decode_json(scheduled_row["schedule_metadata_json"], {})
        title = _clean_text(schedule_metadata.get("headline"))
        if requirement.titleRequired and not title:
            errors.append("missing_required_title: Title/headline is required.")

        if requirement.descriptionRequired and not caption.strip():
            errors.append("missing_required_description: Description is required.")

        media_ids = _decode_json(
            scheduled_row["media_asset_ids_json"] or scheduled_row["media_snapshot_json"],
            [],
        )
        media_rows = self._media_rows(media_ids)
        existing_media_ids = {row["id"] for row in media_rows}
        missing_media = [media_id for media_id in media_ids if media_id not in existing_media_ids]

        if requirement.mediaRequired and not media_ids:
            errors.append("missing_required_media: Platform requires linked media.")
        if missing_media:
            errors.append(
                "missing_linked_media: Linked media does not exist: "
                + ", ".join(missing_media)
            )

        media_types = [row["media_type"] for row in media_rows]
        unsupported_types = sorted(
            {media_type for media_type in media_types if media_type not in requirement.supportedMediaTypes}
        )
        if unsupported_types:
            errors.append(
                "unsupported_media_type: Platform does not support media type(s): "
                + ", ".join(unsupported_types)
            )

        if requirement.videoRequired and "video" not in media_types:
            errors.append("missing_required_video: Platform requires a video asset.")

        draft_flags = _decode_json(draft_row["safety_flags_json"], []) if draft_row else []
        schedule_flags = schedule_metadata.get("safetyFlags", [])
        if not isinstance(schedule_flags, list):
            schedule_flags = []
        critical_flags = sorted(set(draft_flags + schedule_flags) & CRITICAL_SAFETY_FLAGS)
        if critical_flags:
            errors.append(
                "critical_safety_flags: Critical flags must be resolved: "
                + ", ".join(critical_flags)
            )

        account_readiness = self._account_readiness(
            platform=platform,
            brand_profile_id=scheduled_row["brand_profile_id"],
        )
        warnings.extend(account_readiness.accountWarnings)
        warnings.append(
            "real_publishing_disabled_by_policy: Future real publishing remains disabled in this build."
        )

        if media_ids and requirement.altTextRecommendation:
            info.append("alt_text_recommended: " + requirement.altTextRecommendation)
        if requirement.hashtagRecommendation:
            info.append("hashtag_guidance: " + requirement.hashtagRecommendation)
        if platform == "linkedin":
            info.append("professional_tone_recommended: LinkedIn posts should stay professional and useful.")
        if requirement.notes:
            info.append("platform_notes: " + requirement.notes)

        return self._result(
            platform=platform,
            checked_at=checked_at,
            errors=errors,
            warnings=warnings,
            info=info,
            account_readiness=account_readiness,
        )

    def _account_readiness(
        self,
        *,
        platform: str,
        brand_profile_id: str,
    ) -> AccountReadiness:
        accounts = self._candidate_social_accounts(platform, brand_profile_id)
        required_scopes = self._required_scopes_for_platform(platform)
        active_accounts = [
            account
            for account in accounts
            if account["connection_status"] not in {"disconnected", "not_connected"}
        ]
        if not active_accounts:
            return AccountReadiness(
                accountCheckStatus="missing_account",
                accountWarnings=[
                    "missing_connected_account: Future real publishing will require a connected account; manual export is still allowed."
                ],
                accountErrors=[
                    "future_real_publish_blocked: Missing connected account."
                ],
            )

        account = active_accounts[0]
        connection_status = account["connection_status"]
        granted_scopes = set(_decode_json(account["granted_scopes_json"], []))
        recorded_missing_scopes = set(_decode_json(account["missing_scopes_json"], []))
        missing_scopes = sorted((set(required_scopes) - granted_scopes) | recorded_missing_scopes)
        warnings: list[str] = []
        account_errors: list[str] = []
        requires_reauth = bool(account["requires_reauth"]) or connection_status in {
            "expired",
            "revoked",
            "requires_reauth",
            "error",
        }

        if len(active_accounts) > 1:
            warnings.append(
                "account_selection_needed: Multiple accounts exist for this platform; using a safe local default for now."
            )

        if requires_reauth:
            warnings.append(
                "account_requires_reauth: Connected account needs reconnect before future real publishing."
            )
            account_errors.append("future_real_publish_blocked: Account requires reauth.")
            check_status = "requires_reauth"
        elif connection_status == "limited":
            check_status = "limited"
        elif connection_status == "connected":
            check_status = "connected"
        else:
            warnings.append(
                f"account_status_warning: Account status {connection_status} needs review before future real publishing."
            )
            account_errors.append(
                f"future_real_publish_blocked: Account status {connection_status} is not ready."
            )
            check_status = connection_status

        if missing_scopes:
            warnings.append(
                "missing_account_scopes: Future real publishing may need scopes: "
                + ", ".join(missing_scopes)
            )
            if not requires_reauth:
                account_errors.append("future_real_publish_blocked: Missing required account scopes.")

        return AccountReadiness(
            accountCheckStatus=check_status,
            matchedSocialAccountId=account["id"],
            accountWarnings=warnings,
            accountErrors=_dedupe_messages(account_errors),
            missingScopes=missing_scopes,
            requiresReauth=requires_reauth,
            connectionStatus=connection_status,
        )

    def _validate_draft_status(
        self,
        draft_row: sqlite3.Row,
        errors: list[str],
    ) -> None:
        status = draft_row["approval_status"]
        if status == "rejected":
            errors.append("draft_rejected: Rejected drafts cannot pass preflight.")
        elif status == "archived":
            errors.append("draft_archived: Archived drafts cannot pass preflight.")
        elif status == "revision_requested":
            errors.append(
                "unresolved_revision_request: Draft needs revision before preflight."
            )
        elif status != "approved":
            errors.append("draft_not_approved: Draft must be approved before preflight.")

    def _result(
        self,
        *,
        platform: str,
        checked_at: str | datetime | None,
        errors: list[str],
        warnings: list[str],
        info: list[str],
        account_readiness: AccountReadiness,
    ) -> PreflightValidationResult:
        deduped_errors = _dedupe_messages(errors)
        deduped_warnings = _dedupe_messages(warnings)
        deduped_info = _dedupe_messages(info)
        status = "failed" if deduped_errors else "warning" if deduped_warnings else "passed"
        manual_export_eligible = not deduped_errors
        mock_publish_eligible = manual_export_eligible and (
            os.environ.get("INTEGRATIONS_MODE", "mock").strip().lower() == "mock"
        )
        return PreflightValidationResult(
            status=status,
            errors=deduped_errors,
            warnings=deduped_warnings,
            info=deduped_info,
            checkedAt=_checked_at_iso(checked_at),
            platform=platform,
            requirementVersion=REQUIREMENT_VERSION,
            accountCheckStatus=account_readiness.accountCheckStatus,
            matchedSocialAccountId=account_readiness.matchedSocialAccountId,
            accountWarnings=account_readiness.accountWarnings,
            accountErrors=account_readiness.accountErrors,
            missingScopes=account_readiness.missingScopes,
            requiresReauth=account_readiness.requiresReauth,
            connectionStatus=account_readiness.connectionStatus,
            realPublishingEligible=False,
            manualExportEligible=manual_export_eligible,
            mockPublishEligible=mock_publish_eligible,
        )

    def _required_scopes_for_platform(self, platform: str) -> list[str]:
        try:
            connector = get_connector(platform)
        except ConnectorRegistryError:
            return []
        return [scope.id for scope in connector.getRequiredScopes()]

    def _candidate_social_accounts(
        self,
        platform: str,
        brand_profile_id: str,
    ) -> list[sqlite3.Row]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            table = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'social_accounts'"
            ).fetchone()
            if table is None:
                return []
            return connection.execute(
                """
                SELECT *
                FROM social_accounts
                WHERE platform = ?
                  AND (brand_profile_id IS NULL OR brand_profile_id = ?)
                ORDER BY
                  CASE connection_status
                    WHEN 'connected' THEN 0
                    WHEN 'limited' THEN 1
                    WHEN 'requires_reauth' THEN 2
                    WHEN 'expired' THEN 3
                    WHEN 'revoked' THEN 4
                    ELSE 5
                  END,
                  last_validated_at DESC,
                  created_at DESC
                """,
                (platform, brand_profile_id),
            ).fetchall()

    def _require_queue_row(self, queue_item_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM publish_queue_items WHERE id = ?",
                (queue_item_id,),
            ).fetchone()
        if row is None:
            raise PreflightValidationError(
                f"Publish queue item {queue_item_id!r} does not exist."
            )
        return row

    def _require_scheduled_row(self, scheduled_post_id: str) -> sqlite3.Row:
        row = self._scheduled_row(scheduled_post_id)
        if row is None:
            raise PreflightValidationError(
                f"Scheduled post {scheduled_post_id!r} does not exist."
            )
        return row

    def _scheduled_row(self, scheduled_post_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT * FROM scheduled_posts WHERE id = ?",
                (scheduled_post_id,),
            ).fetchone()

    def _queue_row_for_scheduled(self, scheduled_post_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                """
                SELECT *
                FROM publish_queue_items
                WHERE scheduled_post_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (scheduled_post_id,),
            ).fetchone()

    def _generated_post_row(self, generated_post_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT * FROM generated_posts WHERE id = ?",
                (generated_post_id,),
            ).fetchone()

    def _brand_exists(self, brand_profile_id: str) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT 1 FROM brand_profiles WHERE id = ?",
                (brand_profile_id,),
            ).fetchone()
        return row is not None

    def _media_rows(self, media_ids: list[str]) -> list[sqlite3.Row]:
        if not media_ids:
            return []
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                f"""
                SELECT id, media_type, mime_type, original_path
                FROM media_assets
                WHERE id IN ({', '.join('?' for _ in media_ids)})
                """,
                tuple(media_ids),
            ).fetchall()


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _dedupe_messages(messages: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for message in messages:
        if message in seen:
            continue
        seen.add(message)
        deduped.append(message)
    return deduped


def _message_code(message: str) -> str:
    return message.split(":", 1)[0]


def _clean_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _checked_at_iso(value: str | datetime | None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    else:
        raw = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )
