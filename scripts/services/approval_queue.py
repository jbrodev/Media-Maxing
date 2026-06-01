from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.ai.schemas import SUPPORTED_PLATFORMS
from scripts.db.drafts import (
    DraftPersistenceError,
    SavedGeneratedDraft,
    approve_generated_draft,
    archive_generated_draft,
    get_generated_draft,
    list_generated_drafts,
    reject_generated_draft,
    request_generated_draft_revision,
)
from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.settings import load_app_settings


CRITICAL_SAFETY_FLAGS = {
    "invented_testimonial",
    "fake_testimonial",
    "unsupported_guarantee",
    "approval_bypass_attempt",
    "missing_approval",
    "emergency_pause_enabled",
    "emergency_pause_conflict",
    "missing_required_brand_claim_support",
    "unsupported_claim",
    "private_customer_info_risk",
}

SAFETY_FLAG_SEVERITY = {
    "aggressive_language": "warning",
    "brand_mismatch": "critical",
    "platform_policy_risk": "critical",
    **{flag: "critical" for flag in CRITICAL_SAFETY_FLAGS},
}

ACTOR_TYPES = {"user", "system", "ai", "test"}
MEDIA_REQUIRED_PLATFORMS = {"instagram", "youtube", "tiktok"}


class ApprovalQueueError(ValueError):
    pass


@dataclass(frozen=True)
class Actor:
    actorType: str
    actorName: str | None = None
    actorId: str | None = None

    def __post_init__(self) -> None:
        if self.actorType not in ACTOR_TYPES:
            raise ApprovalQueueError(
                "actorType must be one of: " + ", ".join(sorted(ACTOR_TYPES)) + "."
            )

    @property
    def label(self) -> str:
        if self.actorName:
            return f"{self.actorType}:{self.actorName}"
        if self.actorId:
            return f"{self.actorType}:{self.actorId}"
        return self.actorType


@dataclass(frozen=True)
class ApprovalLogEntry:
    draftId: str
    action: str
    previousStatus: str | None
    newStatus: str | None
    reason: str | None
    actorType: str
    actorName: str | None
    actorId: str | None
    createdAt: str


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def error_codes(self) -> list[str]:
        return [item.split(":", 1)[0] for item in self.errors]

    @property
    def warning_codes(self) -> list[str]:
        return [item.split(":", 1)[0] for item in self.warnings]


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


class ApprovalQueueService:
    """Reusable local approval queue and preflight safety gate.

    This service does not publish, schedule, or connect accounts. Calendar
    and Publish Queue features should call its eligibility methods before
    doing any future local scheduling or real-platform work.
    """

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))

    def list_drafts_needing_review(self) -> list[SavedGeneratedDraft]:
        return list_generated_drafts(self.database_path, approval_status="needs_review")

    def list_approved_drafts(self) -> list[SavedGeneratedDraft]:
        return list_generated_drafts(self.database_path, approval_status="approved")

    def get_approval_status(self, draft_id: str) -> str:
        return self._require_draft(draft_id).approvalStatus

    def approve(
        self,
        draft_id: str,
        *,
        actor: Actor | None = None,
        reason: str | None = None,
    ) -> SavedGeneratedDraft:
        actor = actor or Actor(actorType="user")
        previous = self.get_approval_status(draft_id)
        draft = approve_generated_draft(
            self.database_path,
            draft_id,
            actor_label=actor.label,
        )
        self._augment_latest_log(draft.id, previous, draft.approvalStatus, reason, actor)
        return draft

    def reject(
        self,
        draft_id: str,
        *,
        reason: str | None = None,
        actor: Actor | None = None,
    ) -> SavedGeneratedDraft:
        actor = actor or Actor(actorType="user")
        previous = self.get_approval_status(draft_id)
        draft = reject_generated_draft(
            self.database_path,
            draft_id,
            reason=reason,
            actor_label=actor.label,
        )
        self._augment_latest_log(draft.id, previous, draft.approvalStatus, reason, actor)
        return draft

    def request_revision(
        self,
        draft_id: str,
        *,
        reason: str | None = None,
        actor: Actor | None = None,
    ) -> SavedGeneratedDraft:
        actor = actor or Actor(actorType="user")
        previous = self.get_approval_status(draft_id)
        draft = request_generated_draft_revision(
            self.database_path,
            draft_id,
            instructions=reason,
            actor_label=actor.label,
        )
        self._augment_latest_log(draft.id, previous, draft.approvalStatus, reason, actor)
        return draft

    def archive(
        self,
        draft_id: str,
        *,
        reason: str | None = None,
        actor: Actor | None = None,
    ) -> SavedGeneratedDraft:
        actor = actor or Actor(actorType="user")
        previous = self.get_approval_status(draft_id)
        draft = archive_generated_draft(
            self.database_path,
            draft_id,
            reason=reason,
            actor_label=actor.label,
        )
        self._augment_latest_log(draft.id, previous, draft.approvalStatus, reason, actor)
        return draft

    def get_approval_history(self, draft_id: str) -> list[ApprovalLogEntry]:
        self._require_draft(draft_id)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM approval_logs
                WHERE entity_type = 'generated_post'
                  AND entity_id = ?
                ORDER BY rowid ASC
                """,
                (draft_id,),
            ).fetchall()

        entries: list[ApprovalLogEntry] = []
        for row in rows:
            changed = _decode_json(row["changed_fields_json"], {})
            entries.append(
                ApprovalLogEntry(
                    draftId=row["entity_id"],
                    action=row["action"],
                    previousStatus=changed.get("previousStatus")
                    or changed.get("previousApprovalStatus"),
                    newStatus=changed.get("newStatus") or changed.get("approvalStatus"),
                    reason=changed.get("reason") or row["notes"],
                    actorType=changed.get("actorType") or _actor_type_from_label(row["actor_label"]),
                    actorName=changed.get("actorName"),
                    actorId=changed.get("actorId"),
                    createdAt=row["created_at"],
                )
            )
        return entries

    def check_scheduling_eligibility(self, draft_id: str) -> EligibilityResult:
        draft = self._require_draft(draft_id)
        errors: list[str] = []
        warnings: list[str] = []
        self._add_common_eligibility_errors(draft, errors)
        return EligibilityResult(eligible=not errors, errors=errors, warnings=warnings)

    def check_publishing_eligibility(self, draft_id: str) -> EligibilityResult:
        draft = self._require_draft(draft_id)
        errors: list[str] = []
        warnings: list[str] = ["real_publishing_disabled_by_policy: Real publishing is not implemented."]
        self._add_common_eligibility_errors(draft, errors)
        self._add_publishing_only_errors(draft, errors, warnings)
        return EligibilityResult(eligible=not errors, errors=errors, warnings=warnings)

    def _require_draft(self, draft_id: str) -> SavedGeneratedDraft:
        draft = get_generated_draft(self.database_path, draft_id)
        if draft is None:
            raise ApprovalQueueError(f"Draft {draft_id!r} does not exist.")
        return draft

    def _augment_latest_log(
        self,
        draft_id: str,
        previous_status: str,
        new_status: str,
        reason: str | None,
        actor: Actor,
    ) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                """
                SELECT id, changed_fields_json
                FROM approval_logs
                WHERE entity_type = 'generated_post'
                  AND entity_id = ?
                ORDER BY rowid DESC
                LIMIT 1
                """,
                (draft_id,),
            ).fetchone()
            if row is None:
                raise ApprovalQueueError("Approval action did not create an approval log.")

            changed = _decode_json(row["changed_fields_json"], {})
            changed.update(
                {
                    "draftId": draft_id,
                    "previousStatus": previous_status,
                    "newStatus": new_status,
                    "reason": reason,
                    "actorType": actor.actorType,
                    "actorName": actor.actorName,
                    "actorId": actor.actorId,
                }
            )
            connection.execute(
                """
                UPDATE approval_logs
                SET changed_fields_json = ?,
                    notes = ?
                WHERE id = ?
                """,
                (json.dumps(changed, sort_keys=True), reason, row["id"]),
            )
            connection.commit()

    def _add_common_eligibility_errors(
        self,
        draft: SavedGeneratedDraft,
        errors: list[str],
    ) -> None:
        settings = load_app_settings(self.database_path)

        if draft.approvalStatus == "rejected":
            errors.append("draft_rejected: Rejected drafts are not eligible.")
        elif draft.approvalStatus == "archived":
            errors.append("draft_archived: Archived drafts are not eligible.")
        elif draft.approvalStatus == "revision_requested":
            errors.append(
                "unresolved_revision_request: Draft needs revision before eligibility."
            )
        elif draft.approvalStatus != "approved":
            errors.append("draft_not_approved: Draft must be approved first.")

        if settings.emergencyPauseEnabled:
            errors.append("emergency_pause_enabled: Emergency pause blocks eligibility.")

        if draft.platform not in SUPPORTED_PLATFORMS:
            errors.append("invalid_platform: Draft platform is not supported.")

        if not draft.caption or not draft.caption.strip():
            errors.append("missing_caption: Draft caption/content is required.")

        critical_flags = sorted(set(draft.safetyFlags) & CRITICAL_SAFETY_FLAGS)
        if critical_flags:
            errors.append(
                "critical_safety_flags: Critical flags must be resolved: "
                + ", ".join(critical_flags)
            )

        if not self._brand_exists(draft.brandProfileId):
            errors.append("missing_brand_profile: Draft brand profile does not exist.")

        missing_media = self._missing_media_ids(draft.mediaAssetIds)
        if missing_media:
            errors.append(
                "missing_linked_media: Linked media does not exist: "
                + ", ".join(missing_media)
            )

        if draft.platform in MEDIA_REQUIRED_PLATFORMS and not draft.mediaAssetIds:
            errors.append("missing_required_media: Platform requires linked media.")

    def _add_publishing_only_errors(
        self,
        draft: SavedGeneratedDraft,
        errors: list[str],
        warnings: list[str],
    ) -> None:
        if draft.platform in {"youtube", "tiktok"} and not draft.headline:
            errors.append("missing_required_metadata: Title/headline is required.")

        if self._table_exists("social_accounts"):
            if not self._connected_account_exists(draft.platform):
                errors.append(
                    "missing_connected_account: No connected account for platform."
                )
        else:
            warnings.append(
                "social_account_model_not_implemented: Connected accounts are future work."
            )

    def _brand_exists(self, brand_profile_id: str) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT 1 FROM brand_profiles WHERE id = ?",
                (brand_profile_id,),
            ).fetchone()
        return row is not None

    def _missing_media_ids(self, media_ids: list[str]) -> list[str]:
        if not media_ids:
            return []
        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute(
                f"""
                SELECT id
                FROM media_assets
                WHERE id IN ({', '.join('?' for _ in media_ids)})
                """,
                tuple(media_ids),
            ).fetchall()
        existing = {row[0] for row in rows}
        return [media_id for media_id in media_ids if media_id not in existing]

    def _table_exists(self, table_name: str) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
                (table_name,),
            ).fetchone()
        return row is not None

    def _connected_account_exists(self, platform: str) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM social_accounts
                WHERE platform = ?
                  AND connection_status IN ('connected', 'limited')
                  AND requires_reauth = 0
                LIMIT 1
                """,
                (platform,),
            ).fetchone()
        return row is not None


def _actor_type_from_label(actor_label: str | None) -> str:
    if not actor_label:
        return "user"
    maybe_type = actor_label.split(":", 1)[0]
    return maybe_type if maybe_type in ACTOR_TYPES else "user"
