from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from scripts.db.analytics_models import (
    ANALYTICS_IMPORT_STATUSES,
    ANALYTICS_IMPORT_TYPES,
    ANALYTICS_SOURCES,
)
from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.settings import PLATFORM_IDS, load_app_settings


METRIC_FIELDS = (
    "impressions",
    "reach",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "clicks",
    "profile_visits",
    "follows",
    "leads",
    "messages",
    "calls",
    "website_clicks",
)

UPDATE_ALIASES = {
    "snapshotDate": "snapshot_date",
    "profileVisits": "profile_visits",
    "websiteClicks": "website_clicks",
}


class AnalyticsServiceError(ValueError):
    def __init__(self, message: str, error_codes: list[str] | None = None):
        super().__init__(message)
        self.error_codes = error_codes or []


@dataclass(frozen=True)
class AnalyticsSnapshot:
    id: str
    publishedPostId: str | None
    scheduledPostId: str | None
    generatedPostId: str | None
    brandProfileId: str | None
    platform: str
    source: str
    snapshotDate: str
    impressions: int
    reach: int
    views: int
    likes: int
    comments: int
    shares: int
    saves: int
    clicks: int
    profileVisits: int
    follows: int
    leads: int
    messages: int
    calls: int
    websiteClicks: int
    engagementRate: float
    clickThroughRate: float
    leadRate: float
    rawMetrics: dict[str, Any] = field(default_factory=dict)
    notes: str | None = None
    createdAt: str = ""
    updatedAt: str = ""


@dataclass(frozen=True)
class PostPerformanceMetrics:
    id: str
    generatedPostId: str | None
    scheduledPostId: str | None
    publishedPostId: str | None
    brandProfileId: str
    platform: str
    contentGoal: str | None
    contentAngle: str | None
    mediaAssetIds: list[str]
    postedAt: str | None
    firstSnapshotAt: str | None
    latestSnapshotAt: str | None
    totalImpressions: int
    totalReach: int
    totalViews: int
    totalLikes: int
    totalComments: int
    totalShares: int
    totalSaves: int
    totalClicks: int
    totalLeads: int
    engagementRate: float
    leadRate: float
    performanceScore: float
    trend: str
    createdAt: str
    updatedAt: str


@dataclass(frozen=True)
class AnalyticsImportRecord:
    id: str
    source: str
    platform: str | None
    importType: str
    status: str
    recordsImported: int
    recordsSkipped: int
    errorMessage: str | None
    importedAt: str
    createdAt: str


@dataclass(frozen=True)
class MockAnalyticsGenerationResult:
    createdCount: int
    skippedCount: int
    importId: str
    snapshots: list[AnalyticsSnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class ContentInsight:
    id: str
    brandProfileId: str
    insightType: str
    title: str
    summary: str
    evidence: dict[str, Any]
    confidence: str
    relatedPostIds: list[str]
    relatedMediaAssetIds: list[str]
    recommendedAction: str | None
    status: str
    createdAt: str
    updatedAt: str


def calculate_analytics_rates(metrics: dict[str, Any]) -> dict[str, float]:
    values = {field_name: _metric_value(metrics, field_name) for field_name in METRIC_FIELDS}
    engagements = values["likes"] + values["comments"] + values["shares"] + values["saves"]
    engagement_denominator = max(values["reach"], values["impressions"], values["views"], 1)
    click_denominator = max(values["impressions"], values["views"], values["reach"], 1)
    lead_denominator = max(values["clicks"], values["impressions"], values["views"], 1)
    return {
        "engagementRate": round(engagements / engagement_denominator, 6),
        "clickThroughRate": round(values["clicks"] / click_denominator, 6),
        "leadRate": round(values["leads"] / lead_denominator, 6),
    }


def calculate_performance_score(metrics: dict[str, Any]) -> float:
    rates = calculate_analytics_rates(metrics)
    saves = _metric_value(metrics, "saves")
    score = (
        rates["engagementRate"] * 100 * 0.4
        + rates["clickThroughRate"] * 100 * 0.2
        + rates["leadRate"] * 100 * 0.3
        + min(saves, 10)
    )
    return round(min(score, 100.0), 4)


class AnalyticsService:
    """Local analytics storage, summaries, mock fixtures, and rule-based insights.

    The service never calls platform APIs. Snapshot metrics keep their source so
    manual, mock, imported, estimated, and future API data remain distinguishable.
    """

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))

    def create_manual_snapshot(
        self,
        *,
        brand_profile_id: str,
        platform: str,
        snapshot_date: str,
        published_post_id: str | None = None,
        scheduled_post_id: str | None = None,
        generated_post_id: str | None = None,
        notes: str | None = None,
        **metrics: Any,
    ) -> AnalyticsSnapshot:
        return self._create_snapshot(
            brand_profile_id=brand_profile_id,
            platform=platform,
            source="manual",
            snapshot_date=snapshot_date,
            published_post_id=published_post_id,
            scheduled_post_id=scheduled_post_id,
            generated_post_id=generated_post_id,
            notes=notes,
            raw_metrics={"entryMode": "manual", "localOnly": True},
            metrics=metrics,
        )

    def update_snapshot(
        self,
        snapshot_id: str,
        updates: dict[str, Any],
    ) -> AnalyticsSnapshot:
        current = self._require_snapshot_row(snapshot_id)
        normalized_updates = {
            UPDATE_ALIASES.get(field_name, field_name): value
            for field_name, value in updates.items()
        }
        allowed_fields = {*METRIC_FIELDS, "snapshot_date", "notes"}
        unknown_fields = sorted(set(normalized_updates) - allowed_fields)
        if unknown_fields:
            raise AnalyticsServiceError(
                f"Unsupported analytics snapshot field(s): {', '.join(unknown_fields)}.",
                ["invalid_snapshot_field"],
            )

        values = {field_name: current[field_name] for field_name in METRIC_FIELDS}
        for field_name in METRIC_FIELDS:
            if field_name in normalized_updates:
                values[field_name] = _require_non_negative_int(
                    field_name, normalized_updates[field_name]
                )
        snapshot_date = (
            _normalize_datetime(normalized_updates["snapshot_date"])
            if "snapshot_date" in normalized_updates
            else current["snapshot_date"]
        )
        notes = (
            _clean_optional_text(normalized_updates["notes"])
            if "notes" in normalized_updates
            else current["notes"]
        )
        self._ensure_unique_snapshot(
            source=current["source"],
            snapshot_date=snapshot_date,
            published_post_id=current["published_post_id"],
            scheduled_post_id=current["scheduled_post_id"],
            generated_post_id=current["generated_post_id"],
            exclude_snapshot_id=current["id"],
        )
        rates = calculate_analytics_rates(values)
        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                f"""
                UPDATE analytics_snapshots
                SET {", ".join(f"{field_name} = ?" for field_name in METRIC_FIELDS)},
                    snapshot_date = ?,
                    notes = ?,
                    engagement_rate = ?,
                    click_through_rate = ?,
                    lead_rate = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    *(values[field_name] for field_name in METRIC_FIELDS),
                    snapshot_date,
                    notes,
                    rates["engagementRate"],
                    rates["clickThroughRate"],
                    rates["leadRate"],
                    now,
                    current["id"],
                ),
            )
            connection.commit()
        return self.get_snapshot(current["id"])

    def get_snapshot(self, snapshot_id: str) -> AnalyticsSnapshot:
        return _row_to_snapshot(self._require_snapshot_row(snapshot_id))

    def list_snapshots(
        self,
        *,
        brand_profile_id: str | None = None,
        platform: str | None = None,
        start: str | None = None,
        end: str | None = None,
        source: str | None = None,
    ) -> list[AnalyticsSnapshot]:
        clauses, parameters = self._snapshot_filters(
            brand_profile_id=brand_profile_id,
            platform=platform,
            start=start,
            end=end,
            source=source,
        )
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                f"""
                SELECT *
                FROM analytics_snapshots
                {"WHERE " + " AND ".join(clauses) if clauses else ""}
                ORDER BY snapshot_date ASC, created_at ASC
                """,
                parameters,
            ).fetchall()
        return [_row_to_snapshot(row) for row in rows]

    def generate_mock_snapshots(
        self,
        *,
        brand_profile_id: str | None = None,
        snapshot_date: str | None = None,
        explicitly_requested: bool = False,
    ) -> MockAnalyticsGenerationResult:
        settings = load_app_settings(self.database_path)
        if settings.appEnvironment not in {"development", "demo", "test"} and not explicitly_requested:
            raise AnalyticsServiceError(
                "Mock analytics generation is available only in development/demo mode or by explicit request.",
                ["mock_generation_not_allowed"],
            )

        normalized_date = _normalize_datetime(snapshot_date or date.today().isoformat())
        targets = self._mock_targets(brand_profile_id)
        created: list[AnalyticsSnapshot] = []
        skipped = 0
        for target in targets:
            if self._snapshot_exists(
                source="mock",
                snapshot_date=normalized_date,
                published_post_id=target["published_post_id"],
                scheduled_post_id=target["scheduled_post_id"],
                generated_post_id=target["generated_post_id"],
            ):
                skipped += 1
                continue
            metrics = _deterministic_mock_metrics(
                f"{target['platform']}:{target['published_post_id']}:{target['scheduled_post_id']}:{normalized_date}"
            )
            created.append(
                self._create_snapshot(
                    brand_profile_id=target["brand_profile_id"],
                    platform=target["platform"],
                    source="mock",
                    snapshot_date=normalized_date,
                    published_post_id=target["published_post_id"],
                    scheduled_post_id=target["scheduled_post_id"],
                    generated_post_id=target["generated_post_id"],
                    notes="Fake demo metrics generated locally. Not platform analytics.",
                    raw_metrics={
                        "demo": True,
                        "generatedBy": "AnalyticsService.generate_mock_snapshots",
                        "realPlatformAnalytics": False,
                    },
                    metrics=metrics,
                )
            )
        audit = self.record_analytics_import(
            source="mock",
            import_type="mock_sync",
            status="completed",
            records_imported=len(created),
            records_skipped=skipped,
            imported_at=normalized_date,
        )
        return MockAnalyticsGenerationResult(
            createdCount=len(created),
            skippedCount=skipped,
            importId=audit.id,
            snapshots=created,
        )

    def compute_post_performance_metrics(
        self,
        *,
        brand_profile_id: str | None = None,
        platform: str | None = None,
        start: str | None = None,
        end: str | None = None,
        source: str | None = None,
    ) -> list[PostPerformanceMetrics]:
        rows = self._snapshot_rows_with_context(
            brand_profile_id=brand_profile_id,
            platform=platform,
            start=start,
            end=end,
            source=source,
        )
        grouped: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault(_snapshot_post_key(row), []).append(row)

        computed: list[PostPerformanceMetrics] = []
        for group_rows in grouped.values():
            ordered = sorted(group_rows, key=lambda row: (row["snapshot_date"], row["created_at"]))
            earliest = ordered[0]
            latest = ordered[-1]
            latest_values = {field_name: latest[field_name] for field_name in METRIC_FIELDS}
            earliest_values = {field_name: earliest[field_name] for field_name in METRIC_FIELDS}
            latest_score = calculate_performance_score(latest_values)
            earliest_score = calculate_performance_score(earliest_values)
            trend = _trend(earliest_score, latest_score, len(ordered))
            metric = self._persist_performance_metric(
                latest=latest,
                first_snapshot_at=earliest["snapshot_date"],
                latest_snapshot_at=latest["snapshot_date"],
                score=latest_score,
                trend=trend,
            )
            computed.append(metric)
        return sorted(computed, key=lambda metric: metric.performanceScore, reverse=True)

    def compute_dashboard_summary(self, **filters: Any) -> dict[str, Any]:
        metrics = self.compute_post_performance_metrics(**filters)
        platform = self._breakdown(metrics, "platform")
        angles = self._breakdown(metrics, "contentAngle")
        goals = self._breakdown(metrics, "contentGoal")
        total_engagements = sum(
            metric.totalLikes + metric.totalComments + metric.totalShares + metric.totalSaves
            for metric in metrics
        )
        top = metrics[0] if metrics else None
        return {
            "totalPosts": len(metrics),
            "totalImpressions": sum(metric.totalImpressions for metric in metrics),
            "totalViews": sum(metric.totalViews for metric in metrics),
            "totalEngagements": total_engagements,
            "totalClicks": sum(metric.totalClicks for metric in metrics),
            "totalLeads": sum(metric.totalLeads for metric in metrics),
            "averageEngagementRate": _average(metric.engagementRate for metric in metrics),
            "averageLeadRate": _average(metric.leadRate for metric in metrics),
            "bestPlatform": platform[0]["platform"] if platform else None,
            "bestContentAngle": angles[0]["contentAngle"] if angles else None,
            "bestContentGoal": goals[0]["contentGoal"] if goals else None,
            "topPost": top,
            "dateRange": {"start": filters.get("start"), "end": filters.get("end")},
        }

    def compute_platform_breakdown(self, **filters: Any) -> list[dict[str, Any]]:
        return self._breakdown(self.compute_post_performance_metrics(**filters), "platform")

    def compute_content_angle_breakdown(self, **filters: Any) -> list[dict[str, Any]]:
        return self._breakdown(self.compute_post_performance_metrics(**filters), "contentAngle")

    def compute_content_goal_breakdown(self, **filters: Any) -> list[dict[str, Any]]:
        return self._breakdown(self.compute_post_performance_metrics(**filters), "contentGoal")

    def identify_top_posts(self, *, limit: int = 5, **filters: Any) -> list[PostPerformanceMetrics]:
        return self.compute_post_performance_metrics(**filters)[: max(limit, 0)]

    def identify_underperforming_posts(
        self, *, limit: int = 5, **filters: Any
    ) -> list[PostPerformanceMetrics]:
        metrics = self.compute_post_performance_metrics(**filters)
        return sorted(metrics, key=lambda metric: metric.performanceScore)[: max(limit, 0)]

    def create_content_insights(
        self,
        *,
        brand_profile_id: str,
        start: str | None = None,
        end: str | None = None,
        source: str | None = None,
    ) -> list[ContentInsight]:
        metrics = self.compute_post_performance_metrics(
            brand_profile_id=brand_profile_id,
            start=start,
            end=end,
            source=source,
        )
        if not metrics:
            return []
        candidates: list[dict[str, Any]] = []
        angle_breakdown = self._breakdown(metrics, "contentAngle")
        if angle_breakdown and angle_breakdown[0]["contentAngle"] != "unknown":
            best = angle_breakdown[0]
            candidates.append(
                {
                    "key": f"best-angle:{best['contentAngle']}",
                    "insight_type": "best_content_type",
                    "title": f"{_label(best['contentAngle'])} content is worth testing",
                    "summary": (
                        f"{_label(best['contentAngle'])} posts currently have the strongest "
                        "local performance score. Treat this as a pattern to test, not a guarantee."
                    ),
                    "evidence": {"breakdown": best, "dataPoints": best["postCount"]},
                    "recommended_action": "Create another reviewed post with this angle and compare results.",
                }
            )
        platform_breakdown = self._breakdown(metrics, "platform")
        if platform_breakdown:
            best = platform_breakdown[0]
            candidates.append(
                {
                    "key": f"best-platform:{best['platform']}",
                    "insight_type": "best_platform",
                    "title": f"{_label(best['platform'])} is the current leading platform",
                    "summary": (
                        f"{_label(best['platform'])} has the strongest local comparison score "
                        "for the selected data range."
                    ),
                    "evidence": {"breakdown": best, "dataPoints": best["postCount"]},
                    "recommended_action": "Keep collecting comparable metrics before shifting strategy.",
                }
            )
        educational = [metric for metric in metrics if metric.contentAngle == "educational"]
        if educational and sum(metric.totalSaves for metric in educational) > 0:
            candidates.append(
                {
                    "key": "educational-saves",
                    "insight_type": "audience_signal",
                    "title": "Educational posts are earning saves",
                    "summary": "Educational posts have local save signals that may justify another useful FAQ or reminder.",
                    "evidence": {
                        "dataPoints": len(educational),
                        "totalSaves": sum(metric.totalSaves for metric in educational),
                    },
                    "recommended_action": "Test another practical educational post.",
                }
            )

        return [
            self._upsert_content_insight(brand_profile_id, candidate, metrics)
            for candidate in candidates
        ]

    def record_analytics_import(
        self,
        *,
        source: str,
        import_type: str,
        platform: str | None = None,
        status: str = "completed",
        records_imported: int = 0,
        records_skipped: int = 0,
        error_message: str | None = None,
        imported_at: str | None = None,
    ) -> AnalyticsImportRecord:
        _require_choice("source", source, ANALYTICS_SOURCES)
        _require_choice("import_type", import_type, ANALYTICS_IMPORT_TYPES)
        _require_choice("status", status, ANALYTICS_IMPORT_STATUSES)
        if platform is not None:
            _require_platform(platform)
        imported = _normalize_datetime(imported_at or _now_utc())
        record_id = str(uuid.uuid4())
        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO analytics_imports (
                  id, source, platform, import_type, status, records_imported,
                  records_skipped, error_message, imported_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    source,
                    platform,
                    import_type,
                    status,
                    _require_non_negative_int("records_imported", records_imported),
                    _require_non_negative_int("records_skipped", records_skipped),
                    _clean_optional_text(error_message),
                    imported,
                    now,
                ),
            )
            connection.commit()
        return self._get_import(record_id)

    def _create_snapshot(
        self,
        *,
        brand_profile_id: str,
        platform: str,
        source: str,
        snapshot_date: str,
        published_post_id: str | None,
        scheduled_post_id: str | None,
        generated_post_id: str | None,
        notes: str | None,
        raw_metrics: dict[str, Any],
        metrics: dict[str, Any],
    ) -> AnalyticsSnapshot:
        _require_platform(platform)
        _require_choice("source", source, ANALYTICS_SOURCES)
        self._require_brand(brand_profile_id)
        normalized_date = _normalize_datetime(snapshot_date)
        values = {
            field_name: _require_non_negative_int(field_name, _metric_value(metrics, field_name))
            for field_name in METRIC_FIELDS
        }
        self._ensure_unique_snapshot(
            source=source,
            snapshot_date=normalized_date,
            published_post_id=published_post_id,
            scheduled_post_id=scheduled_post_id,
            generated_post_id=generated_post_id,
        )
        rates = calculate_analytics_rates(values)
        snapshot_id = str(uuid.uuid4())
        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                f"""
                INSERT INTO analytics_snapshots (
                  id, published_post_id, scheduled_post_id, generated_post_id,
                  brand_profile_id, platform, source, snapshot_date,
                  {", ".join(METRIC_FIELDS)},
                  engagement_rate, click_through_rate, lead_rate,
                  raw_metrics_json, notes, created_at, updated_at
                ) VALUES (
                  ?, ?, ?, ?, ?, ?, ?, ?,
                  {", ".join("?" for _ in METRIC_FIELDS)},
                  ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    snapshot_id,
                    published_post_id,
                    scheduled_post_id,
                    generated_post_id,
                    brand_profile_id,
                    platform,
                    source,
                    normalized_date,
                    *(values[field_name] for field_name in METRIC_FIELDS),
                    rates["engagementRate"],
                    rates["clickThroughRate"],
                    rates["leadRate"],
                    _json(raw_metrics),
                    _clean_optional_text(notes),
                    now,
                    now,
                ),
            )
            connection.commit()
        return self.get_snapshot(snapshot_id)

    def _snapshot_filters(
        self,
        *,
        brand_profile_id: str | None,
        platform: str | None,
        start: str | None,
        end: str | None,
        source: str | None,
    ) -> tuple[list[str], list[Any]]:
        clauses: list[str] = []
        parameters: list[Any] = []
        if brand_profile_id:
            clauses.append("brand_profile_id = ?")
            parameters.append(brand_profile_id)
        if platform:
            _require_platform(platform)
            clauses.append("platform = ?")
            parameters.append(platform)
        if start:
            clauses.append("snapshot_date >= ?")
            parameters.append(_normalize_datetime(start))
        if end:
            clauses.append("snapshot_date < ?")
            parameters.append(_normalize_datetime(end))
        if source:
            _require_choice("source", source, ANALYTICS_SOURCES)
            clauses.append("source = ?")
            parameters.append(source)
        return clauses, parameters

    def _snapshot_rows_with_context(self, **filters: Any) -> list[sqlite3.Row]:
        clauses, parameters = self._snapshot_filters(**filters)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                f"""
                SELECT analytics_snapshots.*,
                  generated_posts.content_goal,
                  generated_posts.content_angle,
                  generated_posts.media_asset_ids_json,
                  generated_posts.call_to_action,
                  published_posts.published_at
                FROM analytics_snapshots
                LEFT JOIN published_posts
                  ON published_posts.id = analytics_snapshots.published_post_id
                LEFT JOIN generated_posts
                  ON generated_posts.id = analytics_snapshots.generated_post_id
                  OR generated_posts.id = published_posts.generated_post_id
                {"WHERE " + " AND ".join("analytics_snapshots." + clause for clause in clauses) if clauses else ""}
                ORDER BY analytics_snapshots.snapshot_date ASC,
                  analytics_snapshots.created_at ASC
                """,
                parameters,
            ).fetchall()

    def _persist_performance_metric(
        self,
        *,
        latest: sqlite3.Row,
        first_snapshot_at: str,
        latest_snapshot_at: str,
        score: float,
        trend: str,
    ) -> PostPerformanceMetrics:
        existing_id = self._find_performance_metric_id(latest)
        metric_id = existing_id or str(
            uuid.uuid5(uuid.NAMESPACE_URL, f"local-social-ai-manager:{_snapshot_post_key(latest)}")
        )
        now = _now_utc()
        created_at = now
        if existing_id:
            with closing(sqlite3.connect(self.database_path)) as connection:
                created_at = connection.execute(
                    "SELECT created_at FROM post_performance_metrics WHERE id = ?",
                    (existing_id,),
                ).fetchone()[0]
        values = {
            "id": metric_id,
            "generated_post_id": latest["generated_post_id"],
            "scheduled_post_id": latest["scheduled_post_id"],
            "published_post_id": latest["published_post_id"],
            "brand_profile_id": latest["brand_profile_id"],
            "platform": latest["platform"],
            "content_goal": latest["content_goal"],
            "content_angle": latest["content_angle"],
            "media_asset_ids_json": latest["media_asset_ids_json"] or "[]",
            "posted_at": latest["published_at"],
            "first_snapshot_at": first_snapshot_at,
            "latest_snapshot_at": latest_snapshot_at,
            "total_impressions": latest["impressions"],
            "total_reach": latest["reach"],
            "total_views": latest["views"],
            "total_likes": latest["likes"],
            "total_comments": latest["comments"],
            "total_shares": latest["shares"],
            "total_saves": latest["saves"],
            "total_clicks": latest["clicks"],
            "total_leads": latest["leads"],
            "engagement_rate": latest["engagement_rate"],
            "lead_rate": latest["lead_rate"],
            "performance_score": score,
            "trend": trend,
            "created_at": created_at,
            "updated_at": now,
        }
        with closing(sqlite3.connect(self.database_path)) as connection:
            columns = list(values)
            connection.execute(
                f"""
                INSERT INTO post_performance_metrics ({", ".join(columns)})
                VALUES ({", ".join("?" for _ in columns)})
                ON CONFLICT(id) DO UPDATE SET
                  {", ".join(f"{column} = excluded.{column}" for column in columns if column not in {"id", "created_at"})}
                """,
                tuple(values[column] for column in columns),
            )
            connection.commit()
        return self._get_performance_metric(metric_id)

    def _find_performance_metric_id(self, row: sqlite3.Row) -> str | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            found = connection.execute(
                """
                SELECT id
                FROM post_performance_metrics
                WHERE (published_post_id IS NOT NULL AND published_post_id = ?)
                   OR (published_post_id IS NULL AND scheduled_post_id IS NOT NULL AND scheduled_post_id = ?)
                   OR (published_post_id IS NULL AND scheduled_post_id IS NULL
                       AND generated_post_id IS NOT NULL AND generated_post_id = ?)
                LIMIT 1
                """,
                (row["published_post_id"], row["scheduled_post_id"], row["generated_post_id"]),
            ).fetchone()
        return found[0] if found else None

    def _get_performance_metric(self, metric_id: str) -> PostPerformanceMetrics:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM post_performance_metrics WHERE id = ?",
                (metric_id,),
            ).fetchone()
        return _row_to_performance_metric(row)

    def _breakdown(
        self, metrics: list[PostPerformanceMetrics], field_name: str
    ) -> list[dict[str, Any]]:
        groups: dict[str, list[PostPerformanceMetrics]] = {}
        for metric in metrics:
            value = getattr(metric, field_name) or "unknown"
            groups.setdefault(value, []).append(metric)
        rows: list[dict[str, Any]] = []
        output_name = field_name
        for value, group in groups.items():
            rows.append(
                {
                    output_name: value,
                    "postCount": len(group),
                    "totalImpressions": sum(item.totalImpressions for item in group),
                    "totalViews": sum(item.totalViews for item in group),
                    "totalEngagements": sum(
                        item.totalLikes + item.totalComments + item.totalShares + item.totalSaves
                        for item in group
                    ),
                    "totalComments": sum(item.totalComments for item in group),
                    "totalSaves": sum(item.totalSaves for item in group),
                    "totalClicks": sum(item.totalClicks for item in group),
                    "totalLeads": sum(item.totalLeads for item in group),
                    "averageEngagementRate": _average(item.engagementRate for item in group),
                    "averageLeadRate": _average(item.leadRate for item in group),
                    "averagePerformanceScore": _average(item.performanceScore for item in group),
                }
            )
        return sorted(rows, key=lambda row: row["averagePerformanceScore"], reverse=True)

    def _upsert_content_insight(
        self,
        brand_profile_id: str,
        candidate: dict[str, Any],
        metrics: list[PostPerformanceMetrics],
    ) -> ContentInsight:
        insight_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"local-social-ai-manager:insight:{brand_profile_id}:{candidate['key']}",
            )
        )
        data_points = int(candidate["evidence"].get("dataPoints", len(metrics)))
        confidence = _confidence(data_points)
        post_ids = [
            metric.publishedPostId or metric.generatedPostId or metric.id for metric in metrics
        ]
        media_ids = sorted({media_id for metric in metrics for media_id in metric.mediaAssetIds})
        now = _now_utc()
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                """
                INSERT INTO content_insights (
                  id, brand_profile_id, insight_type, title, summary,
                  evidence_json, confidence, related_post_ids_json,
                  related_media_asset_ids_json, recommended_action,
                  status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  summary = excluded.summary,
                  evidence_json = excluded.evidence_json,
                  confidence = excluded.confidence,
                  related_post_ids_json = excluded.related_post_ids_json,
                  related_media_asset_ids_json = excluded.related_media_asset_ids_json,
                  recommended_action = excluded.recommended_action,
                  updated_at = excluded.updated_at
                """,
                (
                    insight_id,
                    brand_profile_id,
                    candidate["insight_type"],
                    candidate["title"],
                    candidate["summary"],
                    _json(candidate["evidence"]),
                    confidence,
                    _json(post_ids),
                    _json(media_ids),
                    candidate["recommended_action"],
                    now,
                    now,
                ),
            )
            connection.commit()
        return self._get_content_insight(insight_id)

    def _get_content_insight(self, insight_id: str) -> ContentInsight:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM content_insights WHERE id = ?",
                (insight_id,),
            ).fetchone()
        return _row_to_content_insight(row)

    def _get_import(self, import_id: str) -> AnalyticsImportRecord:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM analytics_imports WHERE id = ?",
                (import_id,),
            ).fetchone()
        return _row_to_import(row)

    def _mock_targets(self, brand_profile_id: str | None) -> list[sqlite3.Row]:
        parameters: list[Any] = []
        brand_clause = ""
        if brand_profile_id:
            brand_clause = " AND generated_posts.brand_profile_id = ?"
            parameters.append(brand_profile_id)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                f"""
                SELECT published_posts.id AS published_post_id,
                  published_posts.scheduled_post_id,
                  published_posts.generated_post_id,
                  generated_posts.brand_profile_id,
                  published_posts.platform
                FROM published_posts
                JOIN generated_posts
                  ON generated_posts.id = published_posts.generated_post_id
                WHERE published_posts.publish_mode IN ('mock', 'manual_export')
                  {brand_clause}
                UNION ALL
                SELECT NULL AS published_post_id,
                  publish_queue_items.scheduled_post_id,
                  publish_queue_items.generated_post_id,
                  generated_posts.brand_profile_id,
                  publish_queue_items.platform
                FROM publish_queue_items
                JOIN generated_posts
                  ON generated_posts.id = publish_queue_items.generated_post_id
                WHERE publish_queue_items.queue_status IN ('mock_published', 'manually_exported')
                  AND NOT EXISTS (
                    SELECT 1
                    FROM published_posts
                    WHERE published_posts.scheduled_post_id = publish_queue_items.scheduled_post_id
                  )
                  {brand_clause}
                ORDER BY scheduled_post_id
                """,
                (*parameters, *parameters),
            ).fetchall()

    def _require_brand(self, brand_profile_id: str) -> None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                "SELECT 1 FROM brand_profiles WHERE id = ?",
                (brand_profile_id,),
            ).fetchone()
        if row is None:
            raise AnalyticsServiceError(
                f"Brand profile {brand_profile_id!r} does not exist.",
                ["brand_profile_not_found"],
            )

    def _snapshot_exists(self, **values: Any) -> bool:
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM analytics_snapshots
                WHERE source = ?
                  AND snapshot_date = ?
                  AND published_post_id IS ?
                  AND scheduled_post_id IS ?
                  AND generated_post_id IS ?
                LIMIT 1
                """,
                (
                    values["source"],
                    values["snapshot_date"],
                    values["published_post_id"],
                    values["scheduled_post_id"],
                    values["generated_post_id"],
                ),
            ).fetchone()
        return row is not None

    def _ensure_unique_snapshot(
        self,
        *,
        exclude_snapshot_id: str | None = None,
        **values: Any,
    ) -> None:
        if not any(
            values[field_name]
            for field_name in ("published_post_id", "scheduled_post_id", "generated_post_id")
        ):
            return
        parameters = [
            values["source"],
            values["snapshot_date"],
            values["published_post_id"],
            values["scheduled_post_id"],
            values["generated_post_id"],
        ]
        exclusion = ""
        if exclude_snapshot_id:
            exclusion = " AND id != ?"
            parameters.append(exclude_snapshot_id)
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                f"""
                SELECT 1
                FROM analytics_snapshots
                WHERE source = ?
                  AND snapshot_date = ?
                  AND published_post_id IS ?
                  AND scheduled_post_id IS ?
                  AND generated_post_id IS ?
                  {exclusion}
                LIMIT 1
                """,
                parameters,
            ).fetchone()
        if row:
            raise AnalyticsServiceError(
                "An analytics snapshot with this source, post, and date already exists.",
                ["duplicate_snapshot"],
            )

    def _require_snapshot_row(self, snapshot_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM analytics_snapshots WHERE id = ?",
                (snapshot_id,),
            ).fetchone()
        if row is None:
            raise AnalyticsServiceError(
                f"Analytics snapshot {snapshot_id!r} does not exist.",
                ["snapshot_not_found"],
            )
        return row


def _row_to_snapshot(row: sqlite3.Row) -> AnalyticsSnapshot:
    return AnalyticsSnapshot(
        id=row["id"],
        publishedPostId=row["published_post_id"],
        scheduledPostId=row["scheduled_post_id"],
        generatedPostId=row["generated_post_id"],
        brandProfileId=row["brand_profile_id"],
        platform=row["platform"],
        source=row["source"],
        snapshotDate=row["snapshot_date"],
        impressions=row["impressions"],
        reach=row["reach"],
        views=row["views"],
        likes=row["likes"],
        comments=row["comments"],
        shares=row["shares"],
        saves=row["saves"],
        clicks=row["clicks"],
        profileVisits=row["profile_visits"],
        follows=row["follows"],
        leads=row["leads"],
        messages=row["messages"],
        calls=row["calls"],
        websiteClicks=row["website_clicks"],
        engagementRate=row["engagement_rate"],
        clickThroughRate=row["click_through_rate"],
        leadRate=row["lead_rate"],
        rawMetrics=_decode_json(row["raw_metrics_json"], {}),
        notes=row["notes"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _row_to_performance_metric(row: sqlite3.Row) -> PostPerformanceMetrics:
    return PostPerformanceMetrics(
        id=row["id"],
        generatedPostId=row["generated_post_id"],
        scheduledPostId=row["scheduled_post_id"],
        publishedPostId=row["published_post_id"],
        brandProfileId=row["brand_profile_id"],
        platform=row["platform"],
        contentGoal=row["content_goal"],
        contentAngle=row["content_angle"],
        mediaAssetIds=_decode_json(row["media_asset_ids_json"], []),
        postedAt=row["posted_at"],
        firstSnapshotAt=row["first_snapshot_at"],
        latestSnapshotAt=row["latest_snapshot_at"],
        totalImpressions=row["total_impressions"],
        totalReach=row["total_reach"],
        totalViews=row["total_views"],
        totalLikes=row["total_likes"],
        totalComments=row["total_comments"],
        totalShares=row["total_shares"],
        totalSaves=row["total_saves"],
        totalClicks=row["total_clicks"],
        totalLeads=row["total_leads"],
        engagementRate=row["engagement_rate"],
        leadRate=row["lead_rate"],
        performanceScore=row["performance_score"],
        trend=row["trend"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _row_to_import(row: sqlite3.Row) -> AnalyticsImportRecord:
    return AnalyticsImportRecord(
        id=row["id"],
        source=row["source"],
        platform=row["platform"],
        importType=row["import_type"],
        status=row["status"],
        recordsImported=row["records_imported"],
        recordsSkipped=row["records_skipped"],
        errorMessage=row["error_message"],
        importedAt=row["imported_at"],
        createdAt=row["created_at"],
    )


def _row_to_content_insight(row: sqlite3.Row) -> ContentInsight:
    return ContentInsight(
        id=row["id"],
        brandProfileId=row["brand_profile_id"],
        insightType=row["insight_type"],
        title=row["title"],
        summary=row["summary"],
        evidence=_decode_json(row["evidence_json"], {}),
        confidence=row["confidence"],
        relatedPostIds=_decode_json(row["related_post_ids_json"], []),
        relatedMediaAssetIds=_decode_json(row["related_media_asset_ids_json"], []),
        recommendedAction=row["recommended_action"],
        status=row["status"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _snapshot_post_key(row: sqlite3.Row) -> str:
    return (
        f"published:{row['published_post_id']}"
        if row["published_post_id"]
        else f"scheduled:{row['scheduled_post_id']}"
        if row["scheduled_post_id"]
        else f"generated:{row['generated_post_id']}"
        if row["generated_post_id"]
        else f"snapshot:{row['id']}"
    )


def _deterministic_mock_metrics(seed_text: str) -> dict[str, int]:
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:12], 16)
    impressions = 350 + seed % 1800
    reach = max(1, int(impressions * (0.68 + (seed % 17) / 100)))
    views = seed % 500
    likes = 8 + seed % 70
    comments = 1 + seed % 11
    shares = seed % 9
    saves = 2 + seed % 16
    clicks = 3 + seed % 28
    leads = seed % 5
    return {
        "impressions": impressions,
        "reach": reach,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "clicks": clicks,
        "profile_visits": 4 + seed % 35,
        "follows": seed % 8,
        "leads": leads,
        "messages": seed % 4,
        "calls": seed % 3,
        "website_clicks": min(clicks, 2 + seed % 18),
    }


def _trend(first_score: float, latest_score: float, count: int) -> str:
    if count < 2:
        return "unknown"
    if latest_score > first_score + 1:
        return "improving"
    if latest_score < first_score - 1:
        return "declining"
    return "flat"


def _confidence(data_points: int) -> str:
    if data_points < 5:
        return "low"
    if data_points <= 20:
        return "medium"
    return "high"


def _metric_value(metrics: dict[str, Any], field_name: str) -> int:
    alias = {
        "profile_visits": "profileVisits",
        "website_clicks": "websiteClicks",
    }.get(field_name)
    value = metrics.get(field_name, metrics.get(alias, 0) if alias else 0)
    return _require_non_negative_int(field_name, value)


def _require_non_negative_int(field_name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise AnalyticsServiceError(
            f"{field_name} must be a non-negative integer.",
            ["invalid_metric"],
        )
    return value


def _require_platform(platform: str) -> None:
    if platform not in PLATFORM_IDS:
        raise AnalyticsServiceError(
            f"Unsupported platform {platform!r}.",
            ["unsupported_platform"],
        )


def _require_choice(field_name: str, value: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        raise AnalyticsServiceError(
            f"{field_name} must be one of: {', '.join(choices)}.",
            [f"invalid_{field_name}"],
        )


def _normalize_datetime(raw_value: str) -> str:
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise AnalyticsServiceError("A snapshot date is required.", ["invalid_date"])
    normalized = raw_value.strip()
    try:
        if len(normalized) == 10:
            parsed = datetime.fromisoformat(normalized).replace(tzinfo=timezone.utc)
        else:
            parsed = datetime.fromisoformat(
                normalized.removesuffix("Z") + "+00:00"
                if normalized.endswith("Z")
                else normalized
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise AnalyticsServiceError(
            "Date must be an ISO date or datetime.",
            ["invalid_date"],
        ) from error
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _json(value: Any) -> str:
    return json.dumps(
        value,
        default=_json_default,
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {value.__class__.__name__} is not JSON serializable")


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _average(values: Any) -> float:
    collected = list(values)
    return round(sum(collected) / len(collected), 6) if collected else 0


def _label(value: str) -> str:
    return str(value).replace("_", " ").title()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compute local-only analytics summaries. No platform APIs are called."
    )
    parser.add_argument("--database", help="Path to the local SQLite database.")
    parser.add_argument("--brand-profile-id", help="Optional Brand Brain filter.")
    parser.add_argument(
        "--generate-mock",
        action="store_true",
        help="Generate clearly fake local demo analytics before summarizing.",
    )
    parser.add_argument(
        "--explicit-mock",
        action="store_true",
        help="Explicitly allow mock generation outside development/demo mode.",
    )
    args = parser.parse_args()

    service = AnalyticsService(args.database)
    if args.generate_mock:
        mock_result = service.generate_mock_snapshots(
            brand_profile_id=args.brand_profile_id,
            explicitly_requested=args.explicit_mock,
        )
        print(f"mock_snapshots_created={mock_result.createdCount}")
        print(f"mock_snapshots_skipped={mock_result.skippedCount}")
    summary = service.compute_dashboard_summary(brand_profile_id=args.brand_profile_id)
    print(_json(summary))
    print("real_platform_analytics=false")


if __name__ == "__main__":
    main()
