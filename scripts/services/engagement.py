from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.db.engagement_models import ENGAGEMENT_SOURCES, ENGAGEMENT_STATUSES
from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.settings import PLATFORM_IDS


class EngagementServiceError(ValueError):
    def __init__(self, message: str, error_codes: list[str] | None = None):
        super().__init__(message)
        self.error_codes = error_codes or []


@dataclass(frozen=True)
class EngagementItem:
    id: str
    brandProfileId: str | None
    platform: str
    socialAccountId: str | None
    generatedPostId: str | None
    scheduledPostId: str | None
    publishedPostId: str | None
    externalItemId: str | None
    threadId: str | None
    itemType: str
    direction: str
    authorName: str | None
    authorHandle: str | None
    authorProfileUrl: str | None
    content: str
    contentRedacted: str
    receivedAt: str
    sentiment: str
    intent: str
    priority: str
    status: str
    requiresResponse: bool
    assignedTo: str | None
    source: str
    safetyFlags: list[str] = field(default_factory=list)
    rawData: dict[str, Any] = field(default_factory=dict)
    createdAt: str = ""
    updatedAt: str = ""


@dataclass(frozen=True)
class MockEngagementIngestionResult:
    createdCount: int
    skippedCount: int
    importId: str
    items: list[EngagementItem] = field(default_factory=list)


MOCK_SCENARIOS = (
    {
        "slug": "praise-comment",
        "platform": "instagram",
        "item_type": "comment",
        "author_name": "Demo Visitor A",
        "author_handle": "demo_visitor_a",
        "content": "Demo comment: The driveway cleanup looks great. Nice work.",
        "sentiment": "positive",
        "intent": "praise",
        "priority": "normal",
        "status": "new",
        "requires_response": 0,
    },
    {
        "slug": "pricing-question",
        "platform": "facebook",
        "item_type": "comment",
        "author_name": "Demo Visitor B",
        "author_handle": "demo_visitor_b",
        "content": "Demo question: How do you price a typical exterior cleaning visit?",
        "sentiment": "neutral",
        "intent": "price_request",
        "priority": "normal",
        "status": "needs_reply",
        "requires_response": 1,
    },
    {
        "slug": "booking-request",
        "platform": "facebook",
        "item_type": "lead_message",
        "author_name": "Demo Visitor C",
        "author_handle": "demo_visitor_c",
        "content": "Demo lead: I would like to ask about booking a future exterior cleaning estimate.",
        "sentiment": "neutral",
        "intent": "booking_request",
        "priority": "high",
        "status": "needs_reply",
        "requires_response": 1,
    },
    {
        "slug": "complaint",
        "platform": "instagram",
        "item_type": "comment",
        "author_name": "Demo Visitor D",
        "author_handle": "demo_visitor_d",
        "content": "Demo complaint: I had trouble getting a clear answer and would like a person to follow up.",
        "sentiment": "negative",
        "intent": "complaint",
        "priority": "high",
        "status": "escalated",
        "requires_response": 1,
    },
    {
        "slug": "spam",
        "platform": "threads",
        "item_type": "comment",
        "author_name": "Demo Visitor E",
        "author_handle": "demo_visitor_e",
        "content": "Demo spam: Visit an unrelated promotion link for instant growth.",
        "sentiment": "unknown",
        "intent": "spam",
        "priority": "low",
        "status": "spam",
        "requires_response": 0,
    },
    {
        "slug": "review-like-comment",
        "platform": "facebook",
        "item_type": "review",
        "author_name": "Demo Visitor F",
        "author_handle": "demo_visitor_f",
        "content": "Demo review-like comment: The team explanation was helpful and easy to understand.",
        "sentiment": "positive",
        "intent": "praise",
        "priority": "normal",
        "status": "new",
        "requires_response": 0,
    },
    {
        "slug": "urgent-lead-message",
        "platform": "facebook",
        "item_type": "direct_message",
        "author_name": "Demo Visitor G",
        "author_handle": "demo_visitor_g",
        "content": "Demo urgent lead: Please have a person review this time-sensitive service question.",
        "sentiment": "neutral",
        "intent": "urgent",
        "priority": "urgent",
        "status": "escalated",
        "requires_response": 1,
    },
    {
        "slug": "general-comment",
        "platform": "instagram",
        "item_type": "comment",
        "author_name": "Demo Visitor H",
        "author_handle": "demo_visitor_h",
        "content": "Demo comment: Do you share more seasonal exterior care reminders?",
        "sentiment": "neutral",
        "intent": "general",
        "priority": "normal",
        "status": "needs_reply",
        "requires_response": 1,
    },
)


class EngagementService:
    """Local-only engagement storage and deterministic mock ingestion.

    This service never fetches platform comments and never sends replies.
    """

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))

    def ingest_mock_engagement(
        self,
        *,
        brand_profile_id: str,
    ) -> MockEngagementIngestionResult:
        self._require_brand(brand_profile_id)
        now = _now_utc()
        created: list[EngagementItem] = []
        skipped = 0
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            for scenario in MOCK_SCENARIOS:
                linked = self._demo_links(brand_profile_id, scenario["platform"])
                item_id = f"mock-engagement-{scenario['slug']}"
                if connection.execute(
                    "SELECT 1 FROM engagement_items WHERE id = ?",
                    (item_id,),
                ).fetchone():
                    skipped += 1
                    continue
                thread_id = f"mock-thread-{scenario['slug']}"
                thread_status = (
                    "spam"
                    if scenario["status"] == "spam"
                    else "needs_attention"
                    if scenario["status"] == "escalated"
                    else "open"
                )
                connection.execute(
                    """
                    INSERT INTO engagement_threads (
                      id, brand_profile_id, platform, external_thread_id,
                      related_post_id, subject, status, last_message_at,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      status = excluded.status,
                      last_message_at = excluded.last_message_at,
                      updated_at = excluded.updated_at
                    """,
                    (
                        thread_id,
                        brand_profile_id,
                        scenario["platform"],
                        f"mock-external-thread-{scenario['slug']}",
                        linked["published_post_id"],
                        f"Demo {scenario['slug'].replace('-', ' ')}",
                        thread_status,
                        now,
                        now,
                        now,
                    ),
                )
                raw_data = {
                    "demo": True,
                    "fixture": scenario["slug"],
                    "realPlatformFetch": False,
                    "realReplySend": False,
                }
                safety_flags = (
                    ["human_review_required"]
                    if scenario["status"] == "escalated"
                    else ["spam_review"]
                    if scenario["status"] == "spam"
                    else []
                )
                connection.execute(
                    """
                    INSERT INTO engagement_items (
                      id, brand_profile_id, platform, social_account_id,
                      generated_post_id, scheduled_post_id, published_post_id,
                      external_item_id, thread_id, item_type, direction,
                      author_name, author_handle, content, content_redacted,
                      received_at, sentiment, intent, priority, status,
                      requires_response, source, safety_flags_json, raw_data_json,
                      created_at, updated_at
                    ) VALUES (
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'inbound',
                      ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'mock', ?, ?, ?, ?
                    )
                    """,
                    (
                        item_id,
                        brand_profile_id,
                        scenario["platform"],
                        linked["social_account_id"],
                        linked["generated_post_id"],
                        linked["scheduled_post_id"],
                        linked["published_post_id"],
                        f"mock-external-item-{scenario['slug']}",
                        thread_id,
                        scenario["item_type"],
                        scenario["author_name"],
                        scenario["author_handle"],
                        scenario["content"],
                        scenario["content"],
                        now,
                        scenario["sentiment"],
                        scenario["intent"],
                        scenario["priority"],
                        scenario["status"],
                        scenario["requires_response"],
                        _json(safety_flags),
                        _json(raw_data),
                        now,
                        now,
                    ),
                )
                created.append(self._get_item(connection, item_id))
            import_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO engagement_imports (
                  id, source, platform, import_type, status,
                  records_imported, records_skipped, imported_at
                ) VALUES (?, 'mock', NULL, 'mock_ingestion', 'completed', ?, ?, ?)
                """,
                (import_id, len(created), skipped, now),
            )
            connection.commit()
        return MockEngagementIngestionResult(
            createdCount=len(created),
            skippedCount=skipped,
            importId=import_id,
            items=created,
        )

    def list_items(
        self,
        *,
        brand_profile_id: str | None = None,
        platform: str | None = None,
        status: str | None = None,
        source: str | None = None,
    ) -> list[EngagementItem]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if brand_profile_id:
            clauses.append("brand_profile_id = ?")
            parameters.append(brand_profile_id)
        if platform:
            _require_choice("platform", platform, PLATFORM_IDS)
            clauses.append("platform = ?")
            parameters.append(platform)
        if status:
            _require_choice("status", status, ENGAGEMENT_STATUSES)
            clauses.append("status = ?")
            parameters.append(status)
        if source:
            _require_choice("source", source, ENGAGEMENT_SOURCES)
            clauses.append("source = ?")
            parameters.append(source)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                f"""
                SELECT *
                FROM engagement_items
                {"WHERE " + " AND ".join(clauses) if clauses else ""}
                ORDER BY received_at DESC, created_at DESC
                """,
                parameters,
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def _require_brand(self, brand_profile_id: str) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            exists = connection.execute(
                "SELECT 1 FROM brand_profiles WHERE id = ?",
                (brand_profile_id,),
            ).fetchone()
        if not exists:
            raise EngagementServiceError(
                f"Brand profile {brand_profile_id!r} does not exist.",
                ["brand_profile_not_found"],
            )

    def _demo_links(self, brand_profile_id: str, platform: str) -> dict[str, str | None]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT published_posts.id, published_posts.scheduled_post_id,
                  published_posts.generated_post_id
                FROM published_posts
                JOIN generated_posts
                  ON generated_posts.id = published_posts.generated_post_id
                WHERE generated_posts.brand_profile_id = ?
                ORDER BY published_posts.created_at
                LIMIT 1
                """,
                (brand_profile_id,),
            ).fetchone()
            account = connection.execute(
                """
                SELECT id
                FROM social_accounts
                WHERE brand_profile_id = ?
                  AND platform = ?
                  AND connection_status IN ('connected', 'limited')
                ORDER BY created_at
                LIMIT 1
                """,
                (brand_profile_id, platform),
            ).fetchone()
        return {
            "published_post_id": row[0] if row else None,
            "scheduled_post_id": row[1] if row else None,
            "generated_post_id": row[2] if row else None,
            "social_account_id": account[0] if account else None,
        }

    @staticmethod
    def _get_item(connection: sqlite3.Connection, item_id: str) -> EngagementItem:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT * FROM engagement_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        return _row_to_item(row)


def _row_to_item(row: sqlite3.Row) -> EngagementItem:
    return EngagementItem(
        id=row["id"],
        brandProfileId=row["brand_profile_id"],
        platform=row["platform"],
        socialAccountId=row["social_account_id"],
        generatedPostId=row["generated_post_id"],
        scheduledPostId=row["scheduled_post_id"],
        publishedPostId=row["published_post_id"],
        externalItemId=row["external_item_id"],
        threadId=row["thread_id"],
        itemType=row["item_type"],
        direction=row["direction"],
        authorName=row["author_name"],
        authorHandle=row["author_handle"],
        authorProfileUrl=row["author_profile_url"],
        content=row["content"],
        contentRedacted=row["content_redacted"],
        receivedAt=row["received_at"],
        sentiment=row["sentiment"],
        intent=row["intent"],
        priority=row["priority"],
        status=row["status"],
        requiresResponse=bool(row["requires_response"]),
        assignedTo=row["assigned_to"],
        source=row["source"],
        safetyFlags=_decode_json(row["safety_flags_json"], []),
        rawData=_decode_json(row["raw_data_json"], {}),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _require_choice(field_name: str, value: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        raise EngagementServiceError(
            f"{field_name} must be one of: {', '.join(choices)}.",
            [f"invalid_{field_name}"],
        )


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
        description="Manage local-only mock engagement inbox records. No platform APIs are called."
    )
    parser.add_argument("--database", help="Path to the local SQLite database.")
    parser.add_argument("--brand-profile-id", required=True, help="Brand Brain to use.")
    parser.add_argument(
        "--ingest-mock",
        action="store_true",
        help="Insert safe fake demo engagement records.",
    )
    args = parser.parse_args()

    service = EngagementService(args.database)
    if args.ingest_mock:
        result = service.ingest_mock_engagement(
            brand_profile_id=args.brand_profile_id,
        )
        print(f"mock_engagement_created={result.createdCount}")
        print(f"mock_engagement_skipped={result.skippedCount}")
    print(f"engagement_items={len(service.list_items(brand_profile_id=args.brand_profile_id))}")
    print("real_platform_fetch=false")
    print("real_reply_send=false")


if __name__ == "__main__":
    main()
