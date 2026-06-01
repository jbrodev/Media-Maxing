from __future__ import annotations

import argparse
import json
import re
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.ai.prompts import PromptRegistryError, PromptRenderError, get_prompt
from scripts.ai.providers.base import AIProvider, AIProviderError
from scripts.ai.providers.registry import get_provider
from scripts.ai.schemas import (
    AIStructuredGenerationRequest,
    ReplySafetyFlag,
    ReplySafetyReview,
    ReplySuggestionOutput,
    SchemaValidationError,
)
from scripts.db.init_db import initialize_database, resolve_database_path


PROMPT_ID = "comment_reply_suggestion_v1"


class ReplySuggestionServiceError(RuntimeError):
    def __init__(self, message: str, error_codes: list[str] | None = None):
        super().__init__(message)
        self.error_codes = error_codes or []


@dataclass(frozen=True)
class ReplySuggestion:
    id: str
    engagementItemId: str
    brandProfileId: str
    suggestedReply: str
    tone: str
    confidence: str
    safetyFlags: list[str] = field(default_factory=list)
    blockingFlags: list[str] = field(default_factory=list)
    safetyReview: list[dict[str, str]] = field(default_factory=list)
    recommendedAction: str = "reply"
    needsHumanReview: bool = True
    reasonSummary: str = ""
    provider: str = "mock"
    promptTemplateId: str = PROMPT_ID
    promptVersion: str = "v1"
    status: str = "generated"
    createdAt: str = ""
    updatedAt: str = ""


class ReplySuggestionService:
    """Create local-only, review-required reply suggestions.

    This service has no external-send capability. It renders a versioned
    prompt, asks an AI provider for structured draft text, runs deterministic
    local safety checks, and persists the draft with its audit row.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        provider: AIProvider | None = None,
    ):
        self.database_path = initialize_database(resolve_database_path(database_path))
        self.provider = provider

    def generate(
        self,
        *,
        engagement_item_id: str,
        tone: str | None = None,
        provider_name: str = "mock",
        owner_notes: str | None = None,
    ) -> ReplySuggestion:
        if not isinstance(engagement_item_id, str) or not engagement_item_id.strip():
            raise ReplySuggestionServiceError(
                "engagement_item_id is required.",
                ["engagement_item_id_required"],
            )
        selected_tone = (tone or "helpful").strip() or "helpful"

        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            item = self._require_engagement_item(connection, engagement_item_id.strip())
            brand = self._require_brand_profile(connection, item["brand_profile_id"])
            prompt = self._load_prompt()
            rendered_prompt = self._render_prompt(
                prompt,
                connection=connection,
                item=item,
                brand=brand,
                selected_tone=selected_tone,
                owner_notes=owner_notes,
            )
            provider = self._resolve_provider(provider_name)
            provider_output = self._generate_provider_output(
                provider,
                rendered_prompt=rendered_prompt,
                item=item,
                selected_tone=selected_tone,
            )
            local_review = run_reply_safety_review(
                engagement_content=item["content"],
                intent=item["intent"],
                suggested_reply=provider_output.suggested_reply,
            )
            output = _merge_provider_output_and_local_review(provider_output, local_review)
            now = _now_utc()
            suggestion_id = str(uuid.uuid4())

            try:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO reply_suggestions (
                          id, engagement_item_id, brand_profile_id,
                          suggested_reply, tone, confidence, safety_flags_json,
                          reasoning_summary, provider, prompt_template_id,
                          prompt_version, recommended_action, needs_human_review,
                          blocking_flags_json, safety_review_json, status,
                          created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'generated', ?, ?)
                        """,
                        (
                            suggestion_id,
                            item["id"],
                            brand["id"],
                            output.suggested_reply,
                            output.tone,
                            output.confidence,
                            _json([flag.code for flag in output.safety_flags]),
                            output.reason_summary,
                            provider.name,
                            prompt.id,
                            prompt.version,
                            output.recommended_action,
                            int(output.needs_human_review),
                            _json(output.blocking_flags),
                            _json([flag.to_dict() for flag in output.safety_flags]),
                            now,
                            now,
                        ),
                    )
                    connection.execute(
                        """
                        UPDATE engagement_items
                        SET status = 'reply_suggested',
                          updated_at = ?
                        WHERE id = ?
                        """,
                        (now, item["id"]),
                    )
                    connection.execute(
                        """
                        INSERT INTO reply_approvals (
                          id, reply_suggestion_id, engagement_item_id,
                          action, previous_status, new_status, reason,
                          actor_type, created_at
                        ) VALUES (?, ?, ?, 'suggest', ?, 'reply_suggested', ?, 'ai', ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            suggestion_id,
                            item["id"],
                            item["status"],
                            "Local AI reply suggestion generated for owner review only.",
                            now,
                        ),
                    )
            except sqlite3.DatabaseError as error:
                raise ReplySuggestionServiceError(
                    f"Could not store reply suggestion: {error}",
                    ["reply_suggestion_persistence_failed"],
                ) from error
            return self._get_suggestion(connection, suggestion_id)

    def list_for_engagement(self, engagement_item_id: str) -> list[ReplySuggestion]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            self._require_engagement_item(connection, engagement_item_id)
            rows = connection.execute(
                """
                SELECT *
                FROM reply_suggestions
                WHERE engagement_item_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (engagement_item_id,),
            ).fetchall()
        return [_row_to_suggestion(row) for row in rows]

    @staticmethod
    def _require_engagement_item(
        connection: sqlite3.Connection,
        engagement_item_id: str,
    ) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM engagement_items WHERE id = ?",
            (engagement_item_id,),
        ).fetchone()
        if not row:
            raise ReplySuggestionServiceError(
                f"Engagement item {engagement_item_id!r} does not exist.",
                ["engagement_item_not_found"],
            )
        return row

    @staticmethod
    def _require_brand_profile(
        connection: sqlite3.Connection,
        brand_profile_id: str | None,
    ) -> sqlite3.Row:
        if not brand_profile_id:
            raise ReplySuggestionServiceError(
                "Engagement item is missing a Brand Brain link.",
                ["brand_profile_required"],
            )
        row = connection.execute(
            "SELECT * FROM brand_profiles WHERE id = ?",
            (brand_profile_id,),
        ).fetchone()
        if not row:
            raise ReplySuggestionServiceError(
                f"Brand profile {brand_profile_id!r} does not exist.",
                ["brand_profile_not_found"],
            )
        return row

    @staticmethod
    def _load_prompt():
        try:
            return get_prompt(PROMPT_ID)
        except PromptRegistryError as error:
            raise ReplySuggestionServiceError(
                str(error),
                ["reply_prompt_not_found"],
            ) from error

    @staticmethod
    def _render_prompt(
        prompt,
        *,
        connection: sqlite3.Connection,
        item: sqlite3.Row,
        brand: sqlite3.Row,
        selected_tone: str,
        owner_notes: str | None,
    ) -> str:
        related_post = None
        if item["generated_post_id"]:
            related_post = connection.execute(
                """
                SELECT id, headline, hook, caption
                FROM generated_posts
                WHERE id = ?
                """,
                (item["generated_post_id"],),
            ).fetchone()
        thread = None
        if item["thread_id"]:
            thread = connection.execute(
                "SELECT subject, status FROM engagement_threads WHERE id = ?",
                (item["thread_id"],),
            ).fetchone()
        variables = {
            "business_name": brand["business_name"],
            "brand_voice": brand["voice"],
            "supported_claims": _decode_json(brand["supported_claims_json"], []),
            "blocked_phrases": _decode_json(brand["blocked_phrases_json"], []),
            "platform": item["platform"],
            "engagement_type": item["item_type"],
            "engagement_body": item["content_redacted"],
            "engagement_author": item["author_handle"] or "local inbox visitor",
            "engagement_sentiment": item["sentiment"],
            "engagement_intent": item["intent"],
            "engagement_priority": item["priority"],
            "engagement_history": (
                f"Thread subject: {thread['subject']}; status: {thread['status']}"
                if thread
                else None
            ),
            "owner_notes": owner_notes,
            "related_post_context": (
                _related_post_context(related_post) if related_post else None
            ),
            "selected_tone": selected_tone,
        }
        try:
            return prompt.render(variables)
        except PromptRenderError as error:
            raise ReplySuggestionServiceError(
                str(error),
                ["reply_prompt_render_failed"],
            ) from error

    def _resolve_provider(self, provider_name: str) -> AIProvider:
        if self.provider is not None:
            return self.provider
        try:
            return get_provider(provider_name)
        except Exception as error:
            raise ReplySuggestionServiceError(
                str(error),
                ["reply_provider_unavailable"],
            ) from error

    @staticmethod
    def _generate_provider_output(
        provider: AIProvider,
        *,
        rendered_prompt: str,
        item: sqlite3.Row,
        selected_tone: str,
    ) -> ReplySuggestionOutput:
        try:
            response = provider.generate_structured(
                AIStructuredGenerationRequest(
                    prompt=rendered_prompt,
                    schema_name="reply_suggestion",
                    metadata={
                        "intent": item["intent"],
                        "sentiment": item["sentiment"],
                        "priority": item["priority"],
                        "tone": selected_tone,
                    },
                )
            )
            fields = response.data.get("fields")
            if not isinstance(fields, dict):
                raise SchemaValidationError(
                    "Reply suggestion provider output must contain a fields object."
                )
            return _reply_output_from_provider_fields(fields)
        except (AIProviderError, SchemaValidationError) as error:
            raise ReplySuggestionServiceError(
                f"Reply suggestion provider output was rejected: {error}",
                ["reply_provider_output_invalid"],
            ) from error

    @staticmethod
    def _get_suggestion(
        connection: sqlite3.Connection,
        suggestion_id: str,
    ) -> ReplySuggestion:
        row = connection.execute(
            "SELECT * FROM reply_suggestions WHERE id = ?",
            (suggestion_id,),
        ).fetchone()
        if not row:
            raise ReplySuggestionServiceError(
                f"Reply suggestion {suggestion_id!r} does not exist.",
                ["reply_suggestion_not_found"],
            )
        return _row_to_suggestion(row)


def run_reply_safety_review(
    *,
    engagement_content: str,
    intent: str,
    suggested_reply: str,
) -> ReplySafetyReview:
    """Run deterministic local checks. No AI or network calls occur here."""

    inbound = engagement_content or ""
    reply = suggested_reply or ""
    flags: list[ReplySafetyFlag] = []

    def add_flag(code: str, severity: str, message: str) -> None:
        if not any(existing.code == code for existing in flags):
            flags.append(ReplySafetyFlag(code=code, severity=severity, message=message))

    if re.search(r"\$\s*\d|(?:price|cost|charge)\s+(?:is|will be)\s+\d", reply, re.IGNORECASE):
        add_flag("invented_price", "critical", "Remove any invented price before approval.")
    if re.search(
        r"\b(?:available|appointment|scheduled|booked)\s+(?:today|tomorrow|on|for|at)\b",
        reply,
        re.IGNORECASE,
    ):
        add_flag(
            "invented_availability",
            "critical",
            "Remove any invented scheduling availability before approval.",
        )
    if re.search(r"\bguarantee(?:d|s)?\b", inbound + "\n" + reply, re.IGNORECASE):
        add_flag(
            "unsupported_guarantee",
            "critical",
            "A guarantee was requested or suggested. Keep the reply supportable.",
        )
    if re.search(r"\b(?:idiot|stupid|shut up|go away|your fault)\b", reply, re.IGNORECASE):
        add_flag("aggressive_language", "critical", "Use calm, respectful language.")
    if re.search(
        r"\b(?:social security|ssn|credit card|card number|password)\b|\b\d{3}-\d{2}-\d{4}\b",
        reply,
        re.IGNORECASE,
    ):
        add_flag("privacy_risk", "critical", "Remove private or sensitive information.")
    if intent == "complaint" and reply and not re.search(
        r"\b(?:sorry|apolog|understand|thank you for letting us know)\b",
        reply,
        re.IGNORECASE,
    ):
        add_flag(
            "complaint_mishandled",
            "critical",
            "Complaints need an empathetic acknowledgment and human escalation.",
        )
    if re.search(
        r"\b(?:reply has been sent|sent your reply|automatically sent|posted this reply|booked you)\b",
        reply,
        re.IGNORECASE,
    ):
        add_flag(
            "approval_bypass_attempt",
            "critical",
            "The draft must not claim it was sent or bypass owner approval.",
        )
    if intent == "spam":
        add_flag("spam_no_reply_recommended", "info", "Spam should not receive an outward reply.")
    if re.search(r"\b(?:threat|lawsuit|lawyer|hate|abusive)\b", inbound, re.IGNORECASE):
        add_flag(
            "sensitive_escalation_recommended",
            "warning",
            "Keep a person in the loop and avoid argumentative replies.",
        )

    blocking = [flag.code for flag in flags if flag.severity == "critical"]
    return ReplySafetyReview(
        flags=flags,
        blocking_flags=blocking,
        needs_human_review=True,
    )


def _reply_output_from_provider_fields(fields: dict[str, Any]) -> ReplySuggestionOutput:
    return ReplySuggestionOutput(
        suggested_reply=fields.get("suggestedReply"),
        tone=fields.get("tone"),
        confidence=fields.get("confidence"),
        safety_flags=_provider_safety_flags(fields.get("safetyFlags", [])),
        blocking_flags=fields.get("blockingFlags", []),
        recommended_action=fields.get("recommendedAction"),
        needs_human_review=fields.get("needsHumanReview"),
        reason_summary=fields.get("reasonSummary"),
    )


def _provider_safety_flags(values: Any) -> list[ReplySafetyFlag]:
    if not isinstance(values, list):
        raise SchemaValidationError("Reply suggestion safetyFlags must be a list.")
    flags: list[ReplySafetyFlag] = []
    for value in values:
        if isinstance(value, str):
            flags.append(
                ReplySafetyFlag(
                    code=value,
                    severity="warning",
                    message="Provider surfaced this flag for owner review.",
                )
            )
        elif isinstance(value, dict):
            flags.append(
                ReplySafetyFlag(
                    code=value.get("code"),
                    severity=value.get("severity", "warning"),
                    message=value.get("message", "Provider surfaced this flag for owner review."),
                )
            )
        else:
            raise SchemaValidationError(
                "Reply suggestion safetyFlags entries must be strings or objects."
            )
    return flags


def _merge_provider_output_and_local_review(
    output: ReplySuggestionOutput,
    local_review: ReplySafetyReview,
) -> ReplySuggestionOutput:
    flags_by_code = {flag.code: flag for flag in output.safety_flags}
    for flag in local_review.flags:
        flags_by_code[flag.code] = flag
    blocking_flags = sorted(set(output.blocking_flags) | set(local_review.blocking_flags))
    return ReplySuggestionOutput(
        suggested_reply=output.suggested_reply,
        tone=output.tone,
        confidence=output.confidence,
        safety_flags=list(flags_by_code.values()),
        blocking_flags=blocking_flags,
        recommended_action=output.recommended_action,
        needs_human_review=True,
        reason_summary=output.reason_summary,
    )


def _row_to_suggestion(row: sqlite3.Row) -> ReplySuggestion:
    return ReplySuggestion(
        id=row["id"],
        engagementItemId=row["engagement_item_id"],
        brandProfileId=row["brand_profile_id"],
        suggestedReply=row["suggested_reply"],
        tone=row["tone"] or "helpful",
        confidence=row["confidence"],
        safetyFlags=_decode_json(row["safety_flags_json"], []),
        blockingFlags=_decode_json(row["blocking_flags_json"], []),
        safetyReview=_decode_json(row["safety_review_json"], []),
        recommendedAction=row["recommended_action"],
        needsHumanReview=bool(row["needs_human_review"]),
        reasonSummary=row["reasoning_summary"] or "",
        provider=row["provider"],
        promptTemplateId=row["prompt_template_id"],
        promptVersion=row["prompt_version"],
        status=row["status"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _related_post_context(row: sqlite3.Row) -> str:
    parts = [
        f"Draft ID: {row['id']}",
        f"Headline: {row['headline'] or '[not provided]'}",
        f"Hook: {row['hook'] or '[not provided]'}",
        f"Caption: {(row['caption'] or '')[:500]}",
    ]
    return "\n".join(parts)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate one local-only AI reply suggestion. No reply is sent externally."
    )
    parser.add_argument("--database", help="Path to the local SQLite database.")
    parser.add_argument("--engagement-item-id", required=True, help="Local engagement item ID.")
    parser.add_argument("--tone", help="Optional owner-selected tone.")
    args = parser.parse_args()

    suggestion = ReplySuggestionService(args.database).generate(
        engagement_item_id=args.engagement_item_id,
        tone=args.tone,
    )
    print(f"reply_suggestion_created={suggestion.id}")
    print(f"recommended_action={suggestion.recommendedAction}")
    print(f"provider={suggestion.provider}")
    print(f"safety_flag_count={len(suggestion.safetyFlags)}")
    print(f"blocking_flag_count={len(suggestion.blockingFlags)}")
    print("needs_human_review=true")
    print("real_reply_send=false")


if __name__ == "__main__":
    main()
