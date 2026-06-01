from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ai.schemas import (
    APPROVAL_STATUSES,
    GeneratedContentBundle,
    PlatformPostDraft,
    SUPPORTED_PLATFORMS,
)
from scripts.db.init_db import initialize_database, resolve_database_path


DEFAULT_DRAFT_STATUS = "needs_review"
APPROVAL_LOG_ACTION = "generated_saved_to_drafts"
SECRET_KEY_PARTS = (
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "bearer",
    "client_secret",
    "refresh",
    "access",
)


class DraftPersistenceError(ValueError):
    pass


class DuplicateDraftSaveError(DraftPersistenceError):
    pass


@dataclass(frozen=True)
class SavedGeneratedDraft:
    id: str
    brandProfileId: str
    platform: str
    headline: str | None
    hook: str | None
    caption: str
    shortCaption: str | None
    longCaption: str | None
    callToAction: str | None
    hashtags: list[str]
    mediaAssetIds: list[str]
    contentGoal: str | None
    contentAngle: str | None
    altText: str | None
    notes: str | None
    score: dict[str, Any]
    safetyFlags: list[str]
    approvalStatus: str
    generationProvider: str
    promptTemplateId: str | None
    promptVersion: str | None
    generationTimestamp: str | None
    createdAt: str
    updatedAt: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "brandProfileId": self.brandProfileId,
            "platform": self.platform,
            "headline": self.headline,
            "hook": self.hook,
            "caption": self.caption,
            "shortCaption": self.shortCaption,
            "longCaption": self.longCaption,
            "callToAction": self.callToAction,
            "hashtags": self.hashtags,
            "mediaAssetIds": self.mediaAssetIds,
            "contentGoal": self.contentGoal,
            "contentAngle": self.contentAngle,
            "altText": self.altText,
            "notes": self.notes,
            "score": self.score,
            "safetyFlags": self.safetyFlags,
            "approvalStatus": self.approvalStatus,
            "generationProvider": self.generationProvider,
            "promptTemplateId": self.promptTemplateId,
            "promptVersion": self.promptVersion,
            "generationTimestamp": self.generationTimestamp,
            "createdAt": self.createdAt,
            "updatedAt": self.updatedAt,
        }


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _safe_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    cleaned = value.strip()
    return cleaned or None


def _metadata_value(metadata: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = metadata.get(key)
        cleaned = _safe_optional_string(value)
        if cleaned:
            return cleaned
    return None


def _redact_secrets(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            key_lower = key_text.lower()
            if any(part in key_lower for part in SECRET_KEY_PARTS):
                redacted[key_text] = "[redacted]"
            else:
                redacted[key_text] = _redact_secrets(item)
        return redacted
    if isinstance(value, list):
        return [_redact_secrets(item) for item in value]
    return value


def _score_dict(post: PlatformPostDraft) -> dict[str, Any]:
    return post.score.to_dict() if post.score is not None else {}


def _generation_timestamp(bundle: GeneratedContentBundle, now: str) -> str:
    return bundle.created_at or now


def _prompt_template_id(bundle: GeneratedContentBundle) -> str:
    return (
        _metadata_value(
            bundle.prompt_metadata,
            "rendered_prompt_template_id",
            "promptTemplateId",
            "prompt_template_id",
            "promptId",
            "prompt_id",
        )
        or bundle.prompt_id
    )


def _prompt_version(bundle: GeneratedContentBundle) -> str:
    return (
        _metadata_value(
            bundle.prompt_metadata,
            "rendered_prompt_version",
            "promptVersion",
            "prompt_version",
        )
        or bundle.prompt_version
    )


def _compute_save_request_id(bundle: GeneratedContentBundle) -> str:
    payload = {
        "brandProfileId": bundle.brand_profile_id,
        "contentIdeaId": bundle.content_idea_id,
        "promptId": bundle.prompt_id,
        "promptVersion": bundle.prompt_version,
        "generationProvider": bundle.generation_provider,
        "createdAt": bundle.created_at,
        "posts": [
            {
                "platform": post.platform,
                "caption": post.caption,
                "mediaAssetIds": post.media_asset_ids,
                "hashtags": post.hashtags,
            }
            for post in bundle.posts
        ],
    }
    digest = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"generated-save-{digest}"


def _selected_posts(
    bundle: GeneratedContentBundle,
    selected_platforms: Iterable[str] | None,
) -> list[PlatformPostDraft]:
    if selected_platforms is None:
        return list(bundle.posts)

    requested = list(selected_platforms)
    if not requested:
        raise DraftPersistenceError("Select at least one generated draft to save.")

    unsupported = sorted(set(requested) - set(SUPPORTED_PLATFORMS))
    if unsupported:
        raise DraftPersistenceError(
            "Unsupported platform ID(s): " + ", ".join(unsupported) + "."
        )

    requested_set = set(requested)
    posts = [post for post in bundle.posts if post.platform in requested_set]
    if not posts:
        raise DraftPersistenceError(
            "No generated drafts matched the selected platform(s). Generate again or select a saved preview."
        )
    return posts


def _validate_bundle(
    bundle: GeneratedContentBundle,
    selected_platforms: Iterable[str] | None,
) -> list[PlatformPostDraft]:
    if not isinstance(bundle, GeneratedContentBundle):
        raise DraftPersistenceError(
            "Save to Drafts requires a validated GeneratedContentBundle."
        )
    if not bundle.posts:
        raise DraftPersistenceError("GeneratedContentBundle contains no posts to save.")
    if bundle.generation_provider not in {"mock", "openai", "anthropic", "local"}:
        raise DraftPersistenceError("Unsupported generation provider.")
    if DEFAULT_DRAFT_STATUS not in APPROVAL_STATUSES:
        raise DraftPersistenceError("Default draft status is not configured.")
    return _selected_posts(bundle, selected_platforms)


def _existing_save_request_ids(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT prompt_metadata_json FROM generated_posts"
    ).fetchall()
    request_ids: set[str] = set()
    for row in rows:
        metadata = _decode_json(row[0], {})
        request_id = metadata.get("saveRequestId")
        if isinstance(request_id, str) and request_id:
            request_ids.add(request_id)
    return request_ids


def _ensure_brand_exists(connection: sqlite3.Connection, brand_profile_id: str) -> None:
    row = connection.execute(
        "SELECT 1 FROM brand_profiles WHERE id = ?",
        (brand_profile_id,),
    ).fetchone()
    if row is None:
        raise DraftPersistenceError(
            f"Brand profile {brand_profile_id!r} does not exist."
        )


def _draft_prompt_metadata(
    *,
    bundle: GeneratedContentBundle,
    post: PlatformPostDraft,
    save_request_id: str,
    generation_timestamp: str,
    prompt_template_id: str,
    prompt_version: str,
) -> dict[str, Any]:
    return _redact_secrets(
        {
            "saveRequestId": save_request_id,
            "promptTemplateId": prompt_template_id,
            "promptVersion": prompt_version,
            "promptId": bundle.prompt_id,
            "generationTimestamp": generation_timestamp,
            "generationProvider": bundle.generation_provider,
            "bundlePromptMetadata": bundle.prompt_metadata,
            "providerMetadata": bundle.provider_metadata,
            "safetyReview": bundle.safety_review.to_dict(),
            "draft": {
                "platform": post.platform,
                "statusBeforeSave": post.status,
                "approvalStatus": DEFAULT_DRAFT_STATUS,
                "headline": post.headline,
                "hook": post.hook,
                "shortCaption": post.short_caption,
                "longCaption": post.long_caption,
                "callToAction": post.call_to_action,
                "contentGoal": post.content_goal,
                "contentAngle": post.content_angle,
                "targetAudience": post.target_audience,
                "suggestedPostTime": post.suggested_post_time,
                "altText": post.alt_text,
                "notes": post.notes,
                "score": _score_dict(post),
            },
        }
    )


def _row_to_saved_draft(row: sqlite3.Row) -> SavedGeneratedDraft:
    return SavedGeneratedDraft(
        id=row["id"],
        brandProfileId=row["brand_profile_id"],
        platform=row["platform"],
        headline=row["headline"],
        hook=row["hook"],
        caption=row["caption"],
        shortCaption=row["short_caption"],
        longCaption=row["long_caption"],
        callToAction=row["call_to_action"],
        hashtags=_decode_json(row["hashtags_json"], []),
        mediaAssetIds=_decode_json(row["media_asset_ids_json"], []),
        contentGoal=row["content_goal"],
        contentAngle=row["content_angle"],
        altText=row["alt_text"],
        notes=row["notes"],
        score=_decode_json(row["score_json"], {}),
        safetyFlags=_decode_json(row["safety_flags_json"], []),
        approvalStatus=row["approval_status"],
        generationProvider=row["generation_provider"],
        promptTemplateId=row["prompt_template_id"],
        promptVersion=row["prompt_version"],
        generationTimestamp=row["generation_timestamp"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def save_generated_bundle_to_drafts(
    database_path: str | Path | None,
    bundle: GeneratedContentBundle,
    *,
    selected_platforms: Iterable[str] | None = None,
    save_request_id: str | None = None,
    actor_label: str = "local_user",
) -> list[SavedGeneratedDraft]:
    posts = _validate_bundle(bundle, selected_platforms)
    request_id = _safe_optional_string(save_request_id) or _compute_save_request_id(bundle)
    now = _now_utc()
    generation_timestamp = _generation_timestamp(bundle, now)
    prompt_template_id = _prompt_template_id(bundle)
    prompt_version = _prompt_version(bundle)
    campaign_name = _metadata_value(bundle.prompt_metadata, "campaignName", "campaign_name")
    offer_context = _metadata_value(bundle.prompt_metadata, "offerContext", "offer_context")
    user_instructions = _metadata_value(
        bundle.prompt_metadata,
        "userInstructions",
        "user_instructions",
    )

    db_path = initialize_database(resolve_database_path(database_path))
    saved_ids: list[str] = []

    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN")
            _ensure_brand_exists(connection, bundle.brand_profile_id)

            if request_id in _existing_save_request_ids(connection):
                raise DuplicateDraftSaveError(
                    f"Drafts were already saved for saveRequestId {request_id!r}."
                )

            for post in posts:
                draft_id = str(uuid.uuid4())
                prompt_metadata = _draft_prompt_metadata(
                    bundle=bundle,
                    post=post,
                    save_request_id=request_id,
                    generation_timestamp=generation_timestamp,
                    prompt_template_id=prompt_template_id,
                    prompt_version=prompt_version,
                )
                provider_metadata = _redact_secrets(
                    {
                        **bundle.provider_metadata,
                        "generationProvider": bundle.generation_provider,
                        "generationTimestamp": generation_timestamp,
                    }
                )

                connection.execute(
                    """
                    INSERT INTO generated_posts (
                      id,
                      content_idea_id,
                      brand_profile_id,
                      platform,
                      caption,
                      hashtags_json,
                      media_asset_ids_json,
                      approval_status,
                      safety_flags_json,
                      generation_provider,
                      prompt_metadata_json,
                      provider_metadata_json,
                      headline,
                      hook,
                      short_caption,
                      long_caption,
                      call_to_action,
                      content_goal,
                      content_angle,
                      target_audience,
                      campaign_name,
                      offer_context,
                      user_instructions,
                      suggested_post_time,
                      alt_text,
                      notes,
                      score_json,
                      prompt_template_id,
                      prompt_version,
                      generation_timestamp,
                      created_at,
                      updated_at
                    ) VALUES (
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (
                        draft_id,
                        bundle.content_idea_id,
                        bundle.brand_profile_id,
                        post.platform,
                        post.caption,
                        _json(post.hashtags),
                        _json(post.media_asset_ids),
                        DEFAULT_DRAFT_STATUS,
                        _json(post.safety_flags),
                        bundle.generation_provider,
                        _json(prompt_metadata),
                        _json(provider_metadata),
                        post.headline,
                        post.hook,
                        post.short_caption,
                        post.long_caption,
                        post.call_to_action,
                        post.content_goal,
                        post.content_angle,
                        post.target_audience,
                        campaign_name,
                        offer_context,
                        user_instructions,
                        post.suggested_post_time,
                        post.alt_text,
                        post.notes,
                        _json(_score_dict(post)),
                        prompt_template_id,
                        prompt_version,
                        generation_timestamp,
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO approval_logs (
                      id,
                      entity_type,
                      entity_id,
                      action,
                      actor_label,
                      notes,
                      changed_fields_json,
                      created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        "generated_post",
                        draft_id,
                        APPROVAL_LOG_ACTION,
                        actor_label,
                        (
                            "Generated draft saved locally for human review. "
                            "No publishing or scheduling was performed."
                        ),
                        _json(
                            {
                                "approvalStatus": DEFAULT_DRAFT_STATUS,
                                "generationProvider": bundle.generation_provider,
                                "platform": post.platform,
                                "promptTemplateId": prompt_template_id,
                                "promptVersion": prompt_version,
                                "saveRequestId": request_id,
                            }
                        ),
                        now,
                    ),
                )
                saved_ids.append(draft_id)

            connection.commit()
        except DraftPersistenceError:
            connection.rollback()
            raise
        except sqlite3.Error as error:
            connection.rollback()
            raise DraftPersistenceError(f"Could not save generated drafts: {error}") from error

        placeholders = ", ".join("?" for _ in saved_ids)
        rows = connection.execute(
            f"SELECT * FROM generated_posts WHERE id IN ({placeholders}) ORDER BY created_at, id",
            tuple(saved_ids),
        ).fetchall()

    by_id = {row["id"]: _row_to_saved_draft(row) for row in rows}
    return [by_id[draft_id] for draft_id in saved_ids]


def list_generated_drafts(
    database_path: str | Path | None = None,
    *,
    approval_status: str | None = None,
    platform: str | None = None,
    search: str | None = None,
) -> list[SavedGeneratedDraft]:
    db_path = initialize_database(resolve_database_path(database_path))
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        clauses: list[str] = []
        params: list[Any] = []

        if approval_status is not None:
            if approval_status not in APPROVAL_STATUSES:
                raise DraftPersistenceError(
                    f"Unsupported approval status {approval_status!r}."
                )
            clauses.append("approval_status = ?")
            params.append(approval_status)

        if platform is not None:
            if platform not in SUPPORTED_PLATFORMS:
                raise DraftPersistenceError(f"Unsupported platform {platform!r}.")
            clauses.append("platform = ?")
            params.append(platform)

        cleaned_search = _safe_optional_string(search)
        if cleaned_search:
            clauses.append(
                "(LOWER(caption) LIKE ? OR LOWER(COALESCE(headline, '')) LIKE ? OR LOWER(COALESCE(hook, '')) LIKE ?)"
            )
            like_value = f"%{cleaned_search.lower()}%"
            params.extend([like_value, like_value, like_value])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = connection.execute(
            f"""
            SELECT * FROM generated_posts
            {where}
            ORDER BY created_at DESC, id DESC
            """,
            tuple(params),
        ).fetchall()
    return [_row_to_saved_draft(row) for row in rows]


def get_generated_draft(
    database_path: str | Path | None,
    draft_id: str,
) -> SavedGeneratedDraft | None:
    if not _safe_optional_string(draft_id):
        raise DraftPersistenceError("draft_id is required.")

    db_path = initialize_database(resolve_database_path(database_path))
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM generated_posts WHERE id = ?",
            (draft_id,),
        ).fetchone()

    return _row_to_saved_draft(row) if row else None


def _get_required_draft(
    connection: sqlite3.Connection,
    draft_id: str,
) -> sqlite3.Row:
    cleaned_id = _safe_optional_string(draft_id)
    if not cleaned_id:
        raise DraftPersistenceError("draft_id is required.")

    row = connection.execute(
        "SELECT * FROM generated_posts WHERE id = ?",
        (cleaned_id,),
    ).fetchone()
    if row is None:
        raise DraftPersistenceError(f"Draft {cleaned_id!r} does not exist.")
    return row


def _append_approval_log(
    connection: sqlite3.Connection,
    *,
    draft_id: str,
    action: str,
    actor_label: str,
    notes: str | None,
    changed_fields: dict[str, Any],
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO approval_logs (
          id,
          entity_type,
          entity_id,
          action,
          actor_label,
          notes,
          changed_fields_json,
          created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            "generated_post",
            draft_id,
            action,
            actor_label,
            notes,
            _json(_redact_secrets(changed_fields)),
            created_at,
        ),
    )


def _update_status(
    database_path: str | Path | None,
    draft_id: str,
    status: str,
    *,
    action: str,
    reason: str | None = None,
    actor_label: str = "local_user",
) -> SavedGeneratedDraft:
    if status not in APPROVAL_STATUSES:
        raise DraftPersistenceError(f"Unsupported approval status {status!r}.")

    db_path = initialize_database(resolve_database_path(database_path))
    now = _now_utc()
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN")
            row = _get_required_draft(connection, draft_id)
            previous_status = row["approval_status"]
            connection.execute(
                """
                UPDATE generated_posts
                SET approval_status = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (status, now, row["id"]),
            )
            _append_approval_log(
                connection,
                draft_id=row["id"],
                action=action,
                actor_label=actor_label,
                notes=reason,
                changed_fields={
                    "approvalStatus": status,
                    "previousApprovalStatus": previous_status,
                    "reason": reason,
                },
                created_at=now,
            )
            connection.commit()
            updated = _get_required_draft(connection, row["id"])
        except DraftPersistenceError:
            connection.rollback()
            raise
        except sqlite3.Error as error:
            connection.rollback()
            raise DraftPersistenceError(f"Could not update draft status: {error}") from error
    return _row_to_saved_draft(updated)


def approve_generated_draft(
    database_path: str | Path | None,
    draft_id: str,
    *,
    actor_label: str = "local_user",
) -> SavedGeneratedDraft:
    return _update_status(
        database_path,
        draft_id,
        "approved",
        action="approved",
        actor_label=actor_label,
    )


def reject_generated_draft(
    database_path: str | Path | None,
    draft_id: str,
    *,
    reason: str | None = None,
    actor_label: str = "local_user",
) -> SavedGeneratedDraft:
    return _update_status(
        database_path,
        draft_id,
        "rejected",
        action="rejected",
        reason=reason,
        actor_label=actor_label,
    )


def request_generated_draft_revision(
    database_path: str | Path | None,
    draft_id: str,
    *,
    instructions: str | None = None,
    actor_label: str = "local_user",
) -> SavedGeneratedDraft:
    return _update_status(
        database_path,
        draft_id,
        "revision_requested",
        action="revision_requested",
        reason=instructions,
        actor_label=actor_label,
    )


def archive_generated_draft(
    database_path: str | Path | None,
    draft_id: str,
    *,
    reason: str | None = None,
    actor_label: str = "local_user",
) -> SavedGeneratedDraft:
    return _update_status(
        database_path,
        draft_id,
        "archived",
        action="archived",
        reason=reason,
        actor_label=actor_label,
    )


EDITABLE_DRAFT_FIELDS = {
    "headline": "headline",
    "hook": "hook",
    "caption": "caption",
    "shortCaption": "short_caption",
    "longCaption": "long_caption",
    "callToAction": "call_to_action",
    "hashtags": "hashtags_json",
    "altText": "alt_text",
    "notes": "notes",
}


def _clean_hashtags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise DraftPersistenceError("hashtags must be a list of text values.")
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise DraftPersistenceError("hashtags must contain only text values.")
        tag = item.strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = f"#{tag}"
        cleaned.append(tag)
    return cleaned


def update_generated_draft(
    database_path: str | Path | None,
    draft_id: str,
    updates: dict[str, Any],
    *,
    actor_label: str = "local_user",
) -> SavedGeneratedDraft:
    if not isinstance(updates, dict) or not updates:
        raise DraftPersistenceError("updates must include at least one editable field.")

    unknown = sorted(set(updates) - set(EDITABLE_DRAFT_FIELDS))
    if unknown:
        raise DraftPersistenceError(
            "Unknown editable draft field(s): " + ", ".join(unknown) + "."
        )

    db_path = initialize_database(resolve_database_path(database_path))
    now = _now_utc()
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("BEGIN")
            row = _get_required_draft(connection, draft_id)
            set_parts: list[str] = []
            params: list[Any] = []
            edited_fields: list[str] = []

            for field_name, column_name in EDITABLE_DRAFT_FIELDS.items():
                if field_name not in updates:
                    continue
                edited_fields.append(field_name)
                if field_name == "hashtags":
                    value = _json(_clean_hashtags(updates[field_name]))
                elif field_name == "caption":
                    value = _safe_optional_string(updates[field_name])
                    if not value:
                        raise DraftPersistenceError("caption is required.")
                else:
                    value = _safe_optional_string(updates[field_name])
                set_parts.append(f"{column_name} = ?")
                params.append(value)

            previous_status = row["approval_status"]
            next_status = "needs_review" if previous_status == "approved" else previous_status
            set_parts.append("approval_status = ?")
            params.append(next_status)
            set_parts.append("updated_at = ?")
            params.append(now)
            params.append(row["id"])

            connection.execute(
                f"""
                UPDATE generated_posts
                SET {', '.join(set_parts)}
                WHERE id = ?
                """,
                tuple(params),
            )
            action = (
                "edited_requires_reapproval"
                if previous_status == "approved"
                else "edited"
            )
            _append_approval_log(
                connection,
                draft_id=row["id"],
                action=action,
                actor_label=actor_label,
                notes=(
                    "Approved drafts return to needs_review after edits."
                    if previous_status == "approved"
                    else "Draft edited locally."
                ),
                changed_fields={
                    "editedFields": edited_fields,
                    "approvalStatus": next_status,
                    "previousApprovalStatus": previous_status,
                },
                created_at=now,
            )
            connection.commit()
            updated = _get_required_draft(connection, row["id"])
        except DraftPersistenceError:
            connection.rollback()
            raise
        except sqlite3.Error as error:
            connection.rollback()
            raise DraftPersistenceError(f"Could not update draft: {error}") from error
    return _row_to_saved_draft(updated)


def get_approval_history(
    database_path: str | Path | None,
    draft_id: str,
) -> list[dict[str, Any]]:
    db_path = initialize_database(resolve_database_path(database_path))
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        _get_required_draft(connection, draft_id)
        rows = connection.execute(
            """
            SELECT *
            FROM approval_logs
            WHERE entity_type = 'generated_post'
              AND entity_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (draft_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "entity_type": row["entity_type"],
            "entity_id": row["entity_id"],
            "action": row["action"],
            "actor_label": row["actor_label"],
            "notes": row["notes"],
            "changed_fields": _decode_json(row["changed_fields_json"], {}),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
