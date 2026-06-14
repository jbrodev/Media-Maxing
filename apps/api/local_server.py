from __future__ import annotations

import argparse
import json
import mimetypes
import sqlite3
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from apps.api import connect_handlers
from scripts.ai.schemas import (
    CaptionVariant,
    ContentGenerationInput,
    ContentGenerationOptions,
    GeneratedContentBundle,
    GeneratedPostSafetyReview,
    GeneratedPostScore,
    PlatformPostDraft,
)
from scripts.connectors.registry import get_connector
from scripts.db.brand_profiles import (
    get_brand_profile,
    list_brand_profiles,
    update_brand_profile,
)
from scripts.db.drafts import (
    list_generated_drafts,
    save_generated_bundle_to_drafts,
    update_generated_draft,
)
from scripts.db.init_db import REPO_ROOT, initialize_database, resolve_database_path
from scripts.db.media_storage import (
    MAX_MEDIA_FILE_SIZE_BYTES,
    get_media_asset,
    import_media_bytes,
    list_media_assets,
    update_media_asset_metadata,
)
from scripts.db.settings import load_app_settings, update_app_settings
from scripts.services.ai_learning import AILearningService
from scripts.services.ai_memory import AIMemoryService
from scripts.services.analytics import AnalyticsService
from scripts.services.approval_queue import ApprovalQueueService
from scripts.services.backup import BackupService, BackupServiceError
from scripts.services.content_generation import ContentGenerationService
from scripts.services.diagnostics import DiagnosticsService, redact_diagnostic_text
from scripts.services.engagement import EngagementService
from scripts.services.integration_setup import validate_social_integration_setup
from scripts.services.local_env import load_local_env_file
from scripts.services.manual_export import ManualExportService
from scripts.services.oauth_flow import OAuthFlowService
from scripts.services.onboarding import OnboardingService
from scripts.services.publish_queue import PublishQueueService
from scripts.services.reply_approvals import ReplyApprovalService
from scripts.services.reply_suggestions import ReplySuggestionService
from scripts.services.safety_center import SafetyCenterService
from scripts.services.scheduling import (
    CalendarSchedulingService,
    _row_to_queue_item,
)
from scripts.services.token_security import TokenSecurityService
from scripts.services.weekly_reports import WeeklyReportService
from scripts.jobs.local_runner import LocalJobRunner


WEB_ROOT = REPO_ROOT / "apps" / "web"
MAX_JSON_BODY_BYTES = 256 * 1024
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class LocalApiError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: int = HTTPStatus.BAD_REQUEST,
        error_codes: list[str] | None = None,
    ):
        super().__init__(message)
        self.status = int(status)
        self.error_codes = error_codes or []


@dataclass(frozen=True)
class LocalApiResponse:
    status: int
    body: dict[str, Any] | list[Any]


class LocalApiApplication:
    """Small localhost bridge that delegates to the SQLite service layer."""

    def __init__(self, database_path: str | Path | None = None):
        self.database_path = initialize_database(resolve_database_path(database_path))

    def dispatch(
        self,
        method: str,
        raw_path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> LocalApiResponse:
        parsed = urlparse(raw_path)
        path = parsed.path.rstrip("/") or "/"
        query = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        payload = body or {}
        try:
            response = self._dispatch(method.upper(), path, query=query, body=payload)
            return LocalApiResponse(status=HTTPStatus.OK, body=_json_safe(response))
        except LocalApiError:
            raise
        except Exception as error:
            codes = list(getattr(error, "error_codes", []) or [])
            raise LocalApiError(
                str(error) or "The local API request could not be completed.",
                error_codes=codes or ["local_api_request_failed"],
            ) from error

    def _dispatch(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, str],
        body: dict[str, Any],
    ) -> Any:
        segments = [unquote(part) for part in path.split("/") if part]
        if segments == ["api", "health"] and method == "GET":
            return {
                "ok": True,
                "mode": "localhost_sqlite_bridge",
                "database": self.database_path.name,
                "realPublishing": False,
                "realReplySending": False,
            }
        if segments == ["api", "bootstrap"] and method == "GET":
            return self._bootstrap()
        if segments == ["api", "integration-setup"] and method == "GET":
            return validate_social_integration_setup().to_dict()
        if segments == ["api", "diagnostics"]:
            diagnostics = DiagnosticsService(self.database_path)
            if method == "GET":
                return diagnostics.run_checks()
        if segments == ["api", "diagnostics", "export"] and method == "POST":
            recent_errors = body.get("recentErrors") or body.get("recent_errors") or []
            if not isinstance(recent_errors, list):
                recent_errors = []
            return DiagnosticsService(self.database_path).export_report(
                recent_errors=[str(error) for error in recent_errors[:25]],
            )
        if segments == ["api", "onboarding"]:
            onboarding = OnboardingService(self.database_path)
            if method == "GET":
                return onboarding.get_state().to_dict()
            if method == "PATCH":
                return onboarding.update_progress(
                    current_step=body.get("current_step") or body.get("currentStep"),
                    completed_steps=body.get("completed_steps")
                    or body.get("completedSteps"),
                    skipped_steps=body.get("skipped_steps") or body.get("skippedSteps"),
                    status=body.get("status"),
                ).to_dict()
        if len(segments) == 3 and segments[:2] == ["api", "onboarding"] and method == "POST":
            onboarding = OnboardingService(self.database_path)
            action = segments[2]
            if action == "complete":
                return onboarding.complete(body).to_dict()
            if action == "skip":
                return onboarding.skip(reason=body.get("reason")).to_dict()
            if action == "restart":
                return onboarding.restart().to_dict()
        if segments == ["api", "safety-center"]:
            safety = SafetyCenterService(self.database_path)
            if method == "GET":
                return safety.get_state()
        if segments == ["api", "safety-center", "audit-logs"] and method == "GET":
            return SafetyCenterService(self.database_path).list_audit_logs()
        if segments == ["api", "backups"]:
            backups = BackupService(self.database_path)
            if method == "GET":
                return backups.list_backups()
            if method == "POST":
                try:
                    return backups.create_backup(
                        backup_type=body.get("backup_type")
                        or body.get("backupType")
                        or "full_local_backup",
                        backup_name=body.get("backup_name") or body.get("backupName"),
                        include_media=bool(
                            body.get("include_media") or body.get("includeMedia")
                        ),
                        include_token_metadata=bool(
                            body.get("include_token_metadata")
                            or body.get("includeTokenMetadata")
                        ),
                        include_sensitive_tokens=bool(
                            body.get("include_sensitive_tokens")
                            or body.get("includeSensitiveTokens")
                        ),
                    )
                except BackupServiceError as error:
                    raise LocalApiError(str(error), error_codes=error.error_codes) from error
        if segments == ["api", "backups", "restore-preview"] and method == "POST":
            try:
                return BackupService(self.database_path).preview_restore(
                    _required(body, "backupPath")
                    if "backupPath" in body
                    else _required(body, "backup_path")
                )
            except BackupServiceError as error:
                raise LocalApiError(str(error), error_codes=error.error_codes) from error
        if segments == ["api", "safety-center", "emergency-pause"] and method == "POST":
            if "enabled" not in body:
                raise LocalApiError(
                    "enabled is required.",
                    error_codes=["enabled_required"],
                )
            return SafetyCenterService(self.database_path).set_emergency_pause(
                bool(body.get("enabled")),
                actor_type=body.get("actor_type") or body.get("actorType") or "user",
                reason=body.get("reason"),
            )
        if segments == ["api", "safety-center", "automation-level"] and method == "POST":
            return SafetyCenterService(self.database_path).set_automation_level(
                _required(body, "automation_level")
                if "automation_level" in body
                else _required(body, "automationLevel"),
                actor_type=body.get("actor_type") or body.get("actorType") or "user",
                reason=body.get("reason"),
            )
        if (
            len(segments) == 4
            and segments[:3] == ["api", "safety-center", "kill-switch"]
            and method == "POST"
        ):
            return SafetyCenterService(self.database_path).run_kill_switch_action(
                segments[3],
                actor_type=body.get("actor_type") or body.get("actorType") or "user",
                confirmation_phrase=body.get("confirmation_phrase")
                or body.get("confirmationPhrase"),
            )
        if segments == ["api", "settings"]:
            if method == "GET":
                return asdict(load_app_settings(self.database_path))
            if method == "PATCH":
                return asdict(update_app_settings(self.database_path, body))
        if segments == ["api", "brand-profiles"] and method == "GET":
            return [asdict(profile) for profile in list_brand_profiles(self.database_path)]
        if len(segments) == 3 and segments[:2] == ["api", "brand-profiles"]:
            profile_id = segments[2]
            if method == "GET":
                profile = get_brand_profile(self.database_path, profile_id)
                if profile is None:
                    raise LocalApiError(
                        "Brand profile was not found.",
                        status=HTTPStatus.NOT_FOUND,
                        error_codes=["brand_profile_not_found"],
                    )
                return asdict(profile)
            if method == "PATCH":
                return asdict(update_brand_profile(self.database_path, profile_id, body))
        if segments == ["api", "media"] and method == "GET":
            return [asset.to_dict() for asset in list_media_assets(self.database_path)]
        if len(segments) == 3 and segments[:2] == ["api", "media"] and method == "PATCH":
            return update_media_asset_metadata(
                self.database_path,
                segments[2],
                body,
            ).to_dict()
        if segments == ["api", "content-generation"] and method == "POST":
            return self._generate_content(body)
        if segments == ["api", "drafts"] and method == "GET":
            return [draft.to_dict() for draft in list_generated_drafts(self.database_path)]
        if segments == ["api", "drafts", "save-generated"] and method == "POST":
            bundle = _generated_bundle_from_payload(_required(body, "bundle"))
            return [
                draft.to_dict()
                for draft in save_generated_bundle_to_drafts(
                    self.database_path,
                    bundle,
                    selected_platforms=body.get("selected_platforms"),
                    save_request_id=body.get("save_request_id"),
                    actor_label="local_browser_user",
                )
            ]
        if len(segments) >= 3 and segments[:2] == ["api", "drafts"]:
            draft_id = segments[2]
            if len(segments) == 3 and method == "PATCH":
                return update_generated_draft(self.database_path, draft_id, body).to_dict()
            if len(segments) == 4 and segments[3] == "approval" and method == "POST":
                return self._update_draft_approval(draft_id, body).to_dict()
            if len(segments) == 4 and segments[3] == "schedule" and method == "POST":
                return asdict(
                    CalendarSchedulingService(self.database_path).schedule_approved_draft(
                        draft_id,
                        scheduled_for=_required(body, "scheduled_for"),
                        timezone=body.get("timezone"),
                        user_notes=body.get("user_notes"),
                        allow_past_test_item=bool(body.get("allow_past_test_item", False)),
                    )
                )
        if len(segments) == 4 and segments[:2] == ["api", "calendar"] and method == "POST":
            scheduled_post_id, action = segments[2], segments[3]
            calendar = CalendarSchedulingService(self.database_path)
            if action == "reschedule":
                return calendar.update_scheduled_time(
                    scheduled_post_id,
                    scheduled_for=_required(body, "scheduled_for"),
                    timezone=body.get("timezone"),
                    allow_past_test_item=bool(body.get("allow_past_test_item", False)),
                )
            if action == "notes":
                return calendar.update_scheduled_notes(
                    scheduled_post_id,
                    body.get("user_notes"),
                )
            if action == "cancel":
                return calendar.cancel_scheduled_post(
                    scheduled_post_id,
                    reason=body.get("reason"),
                )
            if action == "needs-attention":
                return calendar.mark_needs_attention(scheduled_post_id)
            if action == "fix-caption":
                return calendar.trim_caption_to_limit(scheduled_post_id)
        if len(segments) == 4 and segments[:2] == ["api", "publish-queue"] and method == "POST":
            queue_item_id, action = segments[2], segments[3]
            if action == "preflight":
                return LocalJobRunner(self.database_path).preflight_queue_item(queue_item_id)
            if action == "mock-publish":
                return PublishQueueService(self.database_path).mock_publish(queue_item_id)
            if action == "mark-manually-exported":
                return PublishQueueService(self.database_path).mark_manually_exported(
                    queue_item_id,
                    notes=body.get("notes"),
                )
            if action == "cancel":
                return PublishQueueService(self.database_path).cancel(
                    queue_item_id,
                    reason=body.get("reason"),
                )
            if action == "skip":
                return PublishQueueService(self.database_path).skip(
                    queue_item_id,
                    reason=body.get("reason"),
                )
            if action == "export-package":
                return ManualExportService(self.database_path).export_queue_item(
                    queue_item_id,
                    copy_media=bool(body.get("copy_media", False)),
                )
        if segments == ["api", "analytics", "snapshots"]:
            analytics = AnalyticsService(self.database_path)
            if method == "GET":
                return analytics.list_snapshots(**_analytics_filters(query))
            if method == "POST":
                values = dict(body)
                metrics = values.pop("metrics", {})
                return analytics.create_manual_snapshot(**values, **metrics)
        if segments == ["api", "analytics", "mock"] and method == "POST":
            return AnalyticsService(self.database_path).generate_mock_snapshots(
                brand_profile_id=body.get("brand_profile_id"),
                snapshot_date=body.get("snapshot_date"),
                explicitly_requested=bool(body.get("explicitly_requested", False)),
            )
        if (
            len(segments) == 4
            and segments[:3] == ["api", "analytics", "insights"]
            and method == "PATCH"
        ):
            return AnalyticsService(self.database_path).update_content_insight_status(
                segments[3],
                status=_required(body, "status"),
            )
        if segments == ["api", "engagement", "items"] and method == "GET":
            return EngagementService(self.database_path).list_items(
                brand_profile_id=query.get("brand_profile_id"),
                platform=query.get("platform"),
                status=query.get("status"),
                source=query.get("source"),
            )
        if segments == ["api", "engagement", "mock"] and method == "POST":
            return EngagementService(self.database_path).ingest_mock_engagement(
                brand_profile_id=_required(body, "brand_profile_id"),
            )
        if (
            len(segments) == 4
            and segments[:2] == ["api", "engagement"]
            and segments[3] == "suggestions"
        ):
            engagement_item_id = segments[2]
            suggestions = ReplySuggestionService(self.database_path)
            if method == "GET":
                return suggestions.list_for_engagement(engagement_item_id)
            if method == "POST":
                return suggestions.generate(
                    engagement_item_id=engagement_item_id,
                    tone=body.get("tone"),
                    owner_notes=body.get("owner_notes"),
                )
        if (
            len(segments) == 4
            and segments[:2] == ["api", "engagement"]
            and segments[3] == "status"
            and method == "POST"
        ):
            return self._update_engagement_status(segments[2], body)
        if len(segments) >= 3 and segments[:2] == ["api", "reply-suggestions"]:
            suggestion_id = segments[2]
            approvals = ReplyApprovalService(self.database_path)
            if len(segments) == 3 and method == "PATCH":
                return approvals.edit_suggestion(
                    suggestion_id=suggestion_id,
                    suggested_reply=_required(body, "suggested_reply"),
                    tone=body.get("tone"),
                    reason=body.get("reason"),
                )
            if len(segments) == 4 and method == "POST":
                if segments[3] == "approve":
                    return approvals.approve(
                        suggestion_id=suggestion_id,
                        reason=body.get("reason"),
                    )
                if segments[3] == "reject":
                    return approvals.reject(
                        suggestion_id=suggestion_id,
                        reason=body.get("reason"),
                    )
        if segments == ["api", "ai-memory"] and method == "GET":
            return AIMemoryService(self.database_path).list_memories(
                brand_profile_id=query.get("brand_profile_id"),
                status=query.get("status", "active"),
            )
        if segments == ["api", "ai-memory", "refresh"] and method == "POST":
            return AILearningService(self.database_path).updateLearningMemory(
                brandProfileId=_required(body, "brand_profile_id"),
            )
        if (
            len(segments) == 4
            and segments[:2] == ["api", "ai-memory"]
            and segments[3] == "archive"
            and method == "POST"
        ):
            return AILearningService(self.database_path).archiveMemory(segments[2])
        if (
            len(segments) == 4
            and segments[:2] == ["api", "ai-memory"]
            and segments[3] == "dismiss"
            and method == "POST"
        ):
            return AILearningService(self.database_path).dismissMemory(segments[2])
        if segments == ["api", "weekly-reports"]:
            reports = WeeklyReportService(self.database_path)
            if method == "GET":
                return reports.list_reports(brand_profile_id=query.get("brand_profile_id"))
            if method == "POST":
                return AILearningService(self.database_path).generateWeeklyReport(
                    brandProfileId=_required(body, "brand_profile_id"),
                    weekStartDate=_required(body, "week_start_date"),
                    source=body.get("source"),
                )
        if len(segments) >= 3 and segments[:2] == ["api", "connect"]:
            return self._dispatch_connector(method, segments, query, body)
        raise LocalApiError(
            "Local API route was not found.",
            status=HTTPStatus.NOT_FOUND,
            error_codes=["route_not_found"],
        )

    def _generate_content(self, body: dict[str, Any]) -> dict[str, Any]:
        request = _object(body.get("input"))
        options = _object(body.get("options"))

        def load_brand(profile_id: str) -> dict[str, Any] | None:
            profile = get_brand_profile(self.database_path, profile_id)
            return asdict(profile) if profile else None

        def load_media(media_ids: list[str]) -> list[dict[str, Any]]:
            assets: list[dict[str, Any]] = []
            for media_id in media_ids:
                asset = get_media_asset(self.database_path, media_id)
                if asset is None:
                    raise LocalApiError(
                        f"Media asset {media_id!r} was not found.",
                        error_codes=["media_asset_not_found"],
                    )
                assets.append(asset.to_dict())
            return assets

        def load_memory(profile_id: str) -> list[dict[str, Any]]:
            return AILearningService(
                self.database_path
            ).applyLearningToGenerationContext(brandProfileId=profile_id)[
                "activeAIMemory"
            ]

        bundle = ContentGenerationService(
            brand_loader=load_brand,
            media_loader=load_media,
            settings_loader=lambda: load_app_settings(self.database_path),
            memory_loader=load_memory,
        ).generate(
            _content_generation_input_from_payload(request),
            _content_generation_options_from_payload(options or request),
        )
        bundle.created_at = _now_utc()
        response = _camelize_keys(bundle.to_dict())
        response["saveRequestId"] = f"generation-{uuid.uuid4()}"
        return response

    def _dispatch_connector(
        self,
        method: str,
        segments: list[str],
        query: dict[str, str],
        body: dict[str, Any],
    ) -> Any:
        if segments == ["api", "connect", "accounts"] and method == "GET":
            return connect_handlers.accounts(database_path=self.database_path)
        if segments == ["api", "connect", "platforms"] and method == "GET":
            return connect_handlers.platforms(database_path=self.database_path)
        if len(segments) != 4:
            raise LocalApiError(
                "Connector route was not found.",
                status=HTTPStatus.NOT_FOUND,
                error_codes=["route_not_found"],
            )
        platform, action = segments[2], segments[3]
        if action == "start" and method == "POST":
            return connect_handlers.start(platform, body, database_path=self.database_path)
        if action == "callback" and method == "GET":
            return connect_handlers.callback(platform, query, database_path=self.database_path)
        if action == "disconnect" and method == "POST":
            return connect_handlers.disconnect(platform, body, database_path=self.database_path)
        if action == "mock-connect" and method == "POST":
            return self._mock_connect(platform)
        if action == "validate" and method == "POST":
            connector = get_connector(platform)
            return connector.validateConnection(
                _required(body, "socialAccountId"),
                database_path=self.database_path,
            )
        raise LocalApiError(
            "Connector route was not found.",
            status=HTTPStatus.NOT_FOUND,
            error_codes=["route_not_found"],
        )

    def _mock_connect(self, platform: str) -> Any:
        service = OAuthFlowService(self.database_path, integrations_mode="mock")
        start = service.start_oauth(
            platform=platform,
            redirect_uri=f"http://localhost:8000/api/connect/{platform}/callback",
        )
        if not start.success or not start.authorizationUrl:
            return start.to_safe_dict()
        state_values = parse_qs(urlparse(start.authorizationUrl).query).get("state", [])
        if not state_values:
            raise LocalApiError(
                "Mock OAuth state could not be created.",
                error_codes=["mock_oauth_state_missing"],
            )
        return service.handle_callback(
            platform=platform,
            state=state_values[-1],
            code="local-mock-oauth-code",
        ).to_safe_dict()

    def _update_draft_approval(self, draft_id: str, body: dict[str, Any]) -> Any:
        action = _required(body, "action")
        reason = body.get("reason")
        approvals = ApprovalQueueService(self.database_path)
        if action == "approve":
            return approvals.approve(draft_id, reason=reason)
        if action == "reject":
            return approvals.reject(draft_id, reason=reason)
        if action == "request_revision":
            return approvals.request_revision(draft_id, reason=reason)
        if action == "archive":
            return approvals.archive(draft_id, reason=reason)
        raise LocalApiError(
            "Unsupported draft approval action.",
            error_codes=["invalid_draft_approval_action"],
        )

    def _update_engagement_status(self, engagement_item_id: str, body: dict[str, Any]) -> Any:
        status = _required(body, "status")
        suggestion_id = body.get("suggestion_id")
        approvals = ReplyApprovalService(self.database_path)
        if status == "replied_manually":
            approvals.mark_replied_manually(
                engagement_item_id=engagement_item_id,
                suggestion_id=suggestion_id,
            )
        elif status == "escalated":
            approvals.escalate(
                engagement_item_id=engagement_item_id,
                suggestion_id=suggestion_id,
            )
        elif status == "spam":
            approvals.mark_spam(
                engagement_item_id=engagement_item_id,
                suggestion_id=suggestion_id,
            )
        elif status == "archived":
            approvals.archive(
                engagement_item_id=engagement_item_id,
                suggestion_id=suggestion_id,
            )
        else:
            EngagementService(self.database_path).update_status(
                engagement_item_id,
                status=status,
            )
        return {"id": engagement_item_id, "status": status, "localOnly": True}

    def _bootstrap(self) -> dict[str, Any]:
        brands = list_brand_profiles(self.database_path)
        onboarding = OnboardingService(self.database_path).get_state()
        safety_center = SafetyCenterService(self.database_path).get_state()
        engagement = EngagementService(self.database_path)
        engagement_items = engagement.list_items()
        suggestions = ReplySuggestionService(self.database_path)
        approvals = ReplyApprovalService(self.database_path)
        analytics = AnalyticsService(self.database_path)
        return {
            "settings": asdict(load_app_settings(self.database_path)),
            "onboarding": onboarding.to_dict(),
            "setupChecklist": onboarding.checklist,
            "safetyCenter": safety_center,
            "brandProfile": asdict(brands[0]) if brands else None,
            "mediaAssets": [asset.to_dict() for asset in list_media_assets(self.database_path)],
            "drafts": [draft.to_dict() for draft in list_generated_drafts(self.database_path)],
            "scheduledPosts": CalendarSchedulingService(
                self.database_path
            ).list_scheduled_posts(
                start="1970-01-01T00:00:00Z",
                end="2100-01-01T00:00:00Z",
            ),
            "publishQueueItems": self._list_publish_queue_items(),
            "publishAttempts": self._list_publish_attempts(),
            "approvalLogs": self._approval_logs_by_entity(),
            "connectedAccounts": TokenSecurityService(
                self.database_path
            ).list_safe_social_account_dtos(),
            "connectorAudit": self._list_connector_audit_logs(),
            "analyticsSnapshots": analytics.list_snapshots(),
            "analyticsInsights": self._list_content_insights(),
            "engagementItems": engagement_items,
            "replySuggestions": [
                suggestion
                for item in engagement_items
                for suggestion in suggestions.list_for_engagement(item.id)
            ],
            "replyApprovals": [
                entry
                for item in engagement_items
                for entry in approvals.list_history(item.id)
            ],
            "aiMemory": AIMemoryService(self.database_path).list_memories(status=None),
            "weeklyReports": WeeklyReportService(self.database_path).list_reports(),
            "backupHistory": BackupService(self.database_path).list_backups(),
            "integrationSetup": validate_social_integration_setup().to_dict(),
            "diagnostics": DiagnosticsService(self.database_path).run_checks(),
            "localOnly": True,
            "realPublishing": False,
            "realReplySending": False,
        }

    def _list_publish_queue_items(self) -> list[Any]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM publish_queue_items
                ORDER BY due_at ASC, created_at ASC
                """
            ).fetchall()
        return [_row_to_queue_item(row) for row in rows]

    def _list_publish_attempts(self) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM publish_attempts
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "publishQueueItemId": row["publish_queue_item_id"],
                "scheduledPostId": row["scheduled_post_id"],
                "platform": row["platform"],
                "attemptType": row["attempt_type"],
                "attemptStatus": row["attempt_status"],
                "startedAt": row["started_at"],
                "finishedAt": row["finished_at"],
                "errorCode": row["error_code"],
                "errorMessage": row["error_message"],
                "providerResponse": _decode_json(row["provider_response_json"], {}),
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def _approval_logs_by_entity(self) -> dict[str, list[dict[str, Any]]]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM approval_logs
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["entity_id"], []).append(
                {
                    "id": row["id"],
                    "entityType": row["entity_type"],
                    "entityId": row["entity_id"],
                    "action": row["action"],
                    "actorLabel": row["actor_label"],
                    "notes": row["notes"],
                    "changedFields": _decode_json(row["changed_fields_json"], {}),
                    "createdAt": row["created_at"],
                }
            )
        return grouped

    def _list_connector_audit_logs(self) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM connector_audit_logs
                ORDER BY created_at DESC, id DESC
                LIMIT 100
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "platform": row["platform"],
                "socialAccountId": row["social_account_id"],
                "action": row["action"],
                "status": row["status"],
                "message": row["message"],
                "safeMetadata": _decode_json(row["safe_metadata_json"], {}),
                "createdAt": row["created_at"],
            }
            for row in rows
        ]

    def _list_content_insights(self) -> list[dict[str, Any]]:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM content_insights
                ORDER BY updated_at DESC, created_at DESC
                """
            ).fetchall()
        return [
            {
                "id": row["id"],
                "brandProfileId": row["brand_profile_id"],
                "insightType": row["insight_type"],
                "title": row["title"],
                "summary": row["summary"],
                "evidence": _decode_json(row["evidence_json"], {}),
                "confidence": row["confidence"],
                "relatedPostIds": _decode_json(row["related_post_ids_json"], []),
                "relatedMediaAssetIds": _decode_json(
                    row["related_media_asset_ids_json"], []
                ),
                "recommendedAction": row["recommended_action"],
                "status": row["status"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in rows
        ]


class LocalApiRequestHandler(BaseHTTPRequestHandler):
    server_version = "LocalSocialAIManager/0.1"

    def do_GET(self) -> None:
        if self.path.startswith("/api/"):
            self._handle_api("GET")
        else:
            self._serve_static()

    def do_POST(self) -> None:
        self._handle_api("POST")

    def do_PATCH(self) -> None:
        self._handle_api("PATCH")

    def log_message(self, format_string: str, *args: Any) -> None:
        print(f"local-api: {self.address_string()} {format_string % args}")

    def _handle_api(self, method: str) -> None:
        try:
            if method == "POST" and urlparse(self.path).path == "/api/media/import":
                self._handle_media_upload()
                return
            body = self._read_json_body() if method in {"POST", "PATCH"} else {}
            response = self.server.application.dispatch(method, self.path, body=body)
            self._send_json(response.status, response.body)
        except LocalApiError as error:
            self._send_json(
                error.status,
                {
                    "ok": False,
                    "error": redact_diagnostic_text(str(error)),
                    "errorCodes": error.error_codes,
                },
            )

    def _handle_media_upload(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise LocalApiError(
                "Media upload size is invalid.",
                error_codes=["invalid_media_upload_size"],
            ) from error
        if length <= 0:
            raise LocalApiError(
                "Media upload is empty.",
                error_codes=["empty_media_upload"],
            )
        if length > MAX_MEDIA_FILE_SIZE_BYTES:
            raise LocalApiError(
                "Media upload is larger than the allowed local limit.",
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                error_codes=["media_upload_too_large"],
            )
        filename = unquote(self.headers.get("X-Local-Filename", ""))
        try:
            asset = import_media_bytes(
                self.server.application.database_path,
                filename,
                self.rfile.read(length),
            )
        except Exception as error:
            raise LocalApiError(
                str(error) or "Media upload could not be imported.",
                error_codes=list(getattr(error, "error_codes", []) or [])
                or ["media_upload_failed"],
            ) from error
        self._send_json(HTTPStatus.OK, asset.to_dict())

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > MAX_JSON_BODY_BYTES:
            raise LocalApiError(
                "JSON request body is too large.",
                status=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                error_codes=["request_body_too_large"],
            )
        if length == 0:
            return {}
        try:
            decoded = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LocalApiError(
                "Request body must be valid JSON.",
                error_codes=["invalid_json"],
            ) from error
        if not isinstance(decoded, dict):
            raise LocalApiError(
                "Request body must be a JSON object.",
                error_codes=["invalid_json_shape"],
            )
        return decoded

    def _serve_static(self) -> None:
        raw_path = urlparse(self.path).path
        requested = "index.html" if raw_path in {"", "/"} else unquote(raw_path).lstrip("/")
        candidate = (WEB_ROOT / requested).resolve()
        if WEB_ROOT.resolve() not in candidate.parents and candidate != WEB_ROOT.resolve():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        if not candidate.exists() or not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        payload = candidate.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(_json_safe(payload), sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)


class LocalApiHttpServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], application: LocalApiApplication):
        if address[0] not in LOOPBACK_HOSTS:
            raise ValueError("The local API bridge must bind to a loopback host.")
        super().__init__(address, LocalApiRequestHandler)
        self.application = application


def _analytics_filters(query: dict[str, str]) -> dict[str, Any]:
    return {
        key: query[key]
        for key in ("brand_profile_id", "platform", "start", "end", "source")
        if query.get(key)
    }


def _content_generation_input_from_payload(payload: dict[str, Any]) -> ContentGenerationInput:
    media_assets = _value_alias(payload, "selectedMediaAssets", "selected_media_assets")
    if media_assets is None:
        media_assets = [
            {"id": media_id}
            for media_id in _string_list(
                _value_alias(payload, "selectedMediaIds", "selected_media_ids")
            )
        ]
    return ContentGenerationInput(
        brand_profile={
            "id": _required_alias(payload, "brandProfileId", "brand_profile_id"),
        },
        content_goal=_required_alias(payload, "contentGoal", "content_goal"),
        content_angle=_required_alias(payload, "contentAngle", "content_angle"),
        selected_platforms=_value_alias(
            payload,
            "selectedPlatforms",
            "selected_platforms",
            default=[],
        ),
        selected_media_assets=media_assets,
        campaign_name=_value_alias(payload, "campaignName", "campaign_name"),
        target_audience=_value_alias(payload, "targetAudience", "target_audience"),
        location_context=_value_alias(payload, "locationContext", "location_context"),
        offer_context=_value_alias(payload, "offerContext", "offer_context"),
        user_instructions=_value_alias(payload, "userInstructions", "user_instructions"),
        content_idea_id=_value_alias(payload, "contentIdeaId", "content_idea_id"),
    )


def _content_generation_options_from_payload(payload: dict[str, Any]) -> ContentGenerationOptions:
    return ContentGenerationOptions(
        provider_name=_value_alias(payload, "providerName", "provider_name", default="mock"),
        prompt_id=_value_alias(
            payload,
            "promptId",
            "prompt_id",
            default="platform_post_generator_v1",
        ),
        number_of_variants=_value_alias(
            payload,
            "numberOfVariants",
            "number_of_variants",
            default=0,
        ),
        include_hashtags=_value_alias(
            payload,
            "includeHashtags",
            "include_hashtags",
            default=True,
        ),
        include_emojis=_value_alias(
            payload,
            "includeEmojis",
            "include_emojis",
            default=False,
        ),
        include_cta=_value_alias(payload, "includeCTA", "include_cta", default=True),
        tone=_value_alias(payload, "tone"),
        creativity_level=_value_alias(
            payload,
            "creativityLevel",
            "creativity_level",
            default="medium",
        ),
        require_safety_review=_value_alias(
            payload,
            "requireSafetyReview",
            "require_safety_review",
            default=True,
        ),
    )


def _generated_bundle_from_payload(payload: Any) -> GeneratedContentBundle:
    if not isinstance(payload, dict):
        raise LocalApiError(
            "bundle must be a JSON object.",
            error_codes=["invalid_generated_bundle"],
        )
    safety_payload = _object(payload.get("safetyReview") or payload.get("safety_review"))
    posts_payload = payload.get("posts")
    if not isinstance(posts_payload, list):
        raise LocalApiError(
            "bundle.posts must be a list.",
            error_codes=["invalid_generated_bundle"],
        )
    return GeneratedContentBundle(
        brand_profile_id=_required_alias(payload, "brandProfileId", "brand_profile_id"),
        posts=[_platform_post_from_payload(post) for post in posts_payload],
        prompt_id=_required_alias(payload, "promptId", "prompt_id"),
        prompt_version=_required_alias(payload, "promptVersion", "prompt_version"),
        generation_provider=_required_alias(
            payload,
            "generationProvider",
            "generation_provider",
        ),
        prompt_metadata=_object(payload.get("promptMetadata") or payload.get("prompt_metadata")),
        provider_metadata=_object(
            payload.get("providerMetadata") or payload.get("provider_metadata")
        ),
        safety_review=GeneratedPostSafetyReview(
            flags=_string_list(safety_payload.get("flags")),
            blocking_flags=_string_list(
                safety_payload.get("blockingFlags")
                or safety_payload.get("blocking_flags")
            ),
            reviewer=safety_payload.get("reviewer") or "local_rules",
            notes=safety_payload.get("notes"),
            suggested_fixes=_string_list(
                safety_payload.get("suggestedFixes")
                or safety_payload.get("suggested_fixes")
            ),
        ),
        content_idea_id=payload.get("contentIdeaId") or payload.get("content_idea_id"),
        created_at=payload.get("createdAt") or payload.get("created_at"),
    )


def _platform_post_from_payload(payload: Any) -> PlatformPostDraft:
    if not isinstance(payload, dict):
        raise LocalApiError(
            "bundle.posts entries must be JSON objects.",
            error_codes=["invalid_generated_bundle"],
        )
    score_payload = payload.get("score")
    score = None
    if isinstance(score_payload, dict):
        score = GeneratedPostScore(
            overall=score_payload.get("overall"),
            breakdown=_object(score_payload.get("breakdown")),
            rationale=score_payload.get("rationale"),
        )
    variants = payload.get("captionVariants") or payload.get("caption_variants") or []
    if not isinstance(variants, list):
        raise LocalApiError(
            "captionVariants must be a list.",
            error_codes=["invalid_generated_bundle"],
        )
    return PlatformPostDraft(
        platform=_required(payload, "platform"),
        caption=_required(payload, "caption"),
        headline=payload.get("headline"),
        short_caption=payload.get("shortCaption") or payload.get("short_caption"),
        long_caption=payload.get("longCaption") or payload.get("long_caption"),
        hook=payload.get("hook"),
        call_to_action=payload.get("callToAction") or payload.get("call_to_action"),
        hashtags=_string_list(payload.get("hashtags")),
        media_asset_ids=_string_list(
            payload.get("mediaAssetIds") or payload.get("media_asset_ids")
        ),
        content_angle=payload.get("contentAngle") or payload.get("content_angle"),
        content_goal=payload.get("contentGoal") or payload.get("content_goal"),
        target_audience=payload.get("targetAudience") or payload.get("target_audience"),
        suggested_post_time=payload.get("suggestedPostTime")
        or payload.get("suggested_post_time"),
        alt_text=payload.get("altText") or payload.get("alt_text"),
        notes=payload.get("notes"),
        caption_variants=[
            CaptionVariant(
                text=_required(variant, "text"),
                style=_required(variant, "style"),
            )
            for variant in variants
            if isinstance(variant, dict)
        ],
        safety_flags=_string_list(
            payload.get("safetyFlags") or payload.get("safety_flags")
        ),
        score=score,
        status=payload.get("status") or "needs_review",
    )


def _required_alias(values: dict[str, Any], *field_names: str) -> Any:
    for field_name in field_names:
        value = values.get(field_name)
        if value is not None and not (isinstance(value, str) and not value.strip()):
            return value
    raise LocalApiError(
        f"{field_names[0]} is required.",
        error_codes=[f"{field_names[0]}_required"],
    )


def _value_alias(values: dict[str, Any], *field_names: str, default: Any = None) -> Any:
    for field_name in field_names:
        if field_name in values:
            return values[field_name]
    return default


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _string_list(value: Any) -> list[str]:
    return value if isinstance(value, list) else []


def _required(values: dict[str, Any], field_name: str) -> Any:
    value = values.get(field_name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise LocalApiError(
            f"{field_name} is required.",
            error_codes=[f"{field_name}_required"],
        )
    return value


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _json_safe(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _json_safe(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value


def _camelize_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            _camelize_key(str(key)): _camelize_keys(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_camelize_keys(item) for item in value]
    return value


def _camelize_key(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serve the localhost-only SQLite bridge and static web app."
    )
    parser.add_argument("--database", help="Path to the local SQLite database.")
    parser.add_argument(
        "--env-file",
        help="Optional local .env path. Defaults to the repo-root .env when present.",
    )
    parser.add_argument("--host", default="127.0.0.1", choices=sorted(LOOPBACK_HOSTS))
    parser.add_argument("--port", default=8000, type=int)
    args = parser.parse_args()

    load_local_env_file(args.env_file)
    application = LocalApiApplication(args.database)
    server = LocalApiHttpServer((args.host, args.port), application)
    print(f"Local Social AI Manager running at http://{args.host}:{args.port}")
    print(f"SQLite database: {application.database_path}")
    print("real_publishing=false")
    print("real_reply_sending=false")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
