from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from scripts.connectors.base import DISABLED_PUBLISHING_MESSAGE, SocialConnector
from scripts.connectors.types import (
    ConnectedAccountProfile,
    ConnectorActionResult,
    ConnectorCapabilities,
    ConnectorHealthResult,
    OAuthCallbackRequest,
    OAuthCallbackResult,
    OAuthConfig,
    OAuthStartRequest,
    OAuthStartResult,
    PlatformFeatureStatus,
    PlatformPermissionScope,
)
from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.social_connections import create_connector_audit_log
from scripts.services.platform_http_client import (
    PlatformHttpClient,
    PlatformHttpClientConfig,
    PlatformHttpMethod,
    PlatformHttpRequest,
    PlatformHttpResponse,
    normalize_provider_error,
    redact_http_value,
    redact_raw_text,
)


TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_PROFILE_URL = "https://open.tiktokapis.com/v2/user/info/"
MOCK_TIKTOK_AUTH_BASE_URL = "http://localhost/mock-oauth/tiktok"


@dataclass(frozen=True)
class TikTokConfig:
    clientKey: str | None
    clientSecret: str | None
    redirectUri: str | None
    realOAuthEnabled: bool
    realPublishingEnabled: bool

    @property
    def missingConfigKeys(self) -> tuple[str, ...]:
        missing = []
        if not self.clientKey:
            missing.append("TIKTOK_CLIENT_KEY")
        if not self.clientSecret:
            missing.append("TIKTOK_CLIENT_SECRET")
        if not self.redirectUri:
            missing.append("TIKTOK_REDIRECT_URI")
        return tuple(missing)


def load_tiktok_config(env: dict[str, str] | None = None) -> TikTokConfig:
    values = env if env is not None else dict(os.environ)
    return TikTokConfig(
        clientKey=_env_value(values, "TIKTOK_CLIENT_KEY"),
        clientSecret=_env_value(values, "TIKTOK_CLIENT_SECRET"),
        redirectUri=_env_value(values, "TIKTOK_REDIRECT_URI"),
        realOAuthEnabled=_env_truthy(values.get("TIKTOK_ENABLE_REAL_OAUTH")),
        realPublishingEnabled=_env_truthy(values.get("TIKTOK_ENABLE_REAL_PUBLISHING")),
    )


class TikTokConnector(SocialConnector):
    def __init__(self) -> None:
        super().__init__(
            platform="tiktok",
            label="TikTok",
            featureStatus=PlatformFeatureStatus.MOCK_ONLY,
            capabilities=ConnectorCapabilities(
                canConnect=True,
                canRefreshToken=False,
                canPublishVideo=False,
                canReadAnalytics=False,
                canReadProfile=True,
                canScheduleNatively=False,
                requiresBusinessAccount=False,
                requiresAppReview=True,
                supportsOAuth=True,
                supportsManualExportFallback=True,
            ),
            requiredScopes=(
                PlatformPermissionScope(
                    id="user.info.basic",
                    label="Basic profile",
                    description="Placeholder scope for future TikTok profile discovery. TODO: verify before production.",
                    status=PlatformFeatureStatus.SCAFFOLDED,
                ),
                PlatformPermissionScope(
                    id="video.upload",
                    label="Video upload",
                    description="Placeholder scope for future TikTok video posting. Posting is disabled in this build.",
                    required=False,
                    status=PlatformFeatureStatus.PLANNED,
                ),
            ),
            setupInstructions=(
                "Create or use a TikTok developer app before future real OAuth testing.",
                "Add the local redirect URI, for example http://localhost:8000/api/connect/tiktok/callback.",
                "Set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, and TIKTOK_REDIRECT_URI in local .env only.",
                "Required scopes are placeholders: user.info.basic for profile checks and video.upload for future posting. TODO: verify exact scopes before production.",
                "App review warning: TikTok may require review before live permissions work.",
                "Content posting review warning: TikTok video posting access may require separate approval and policy review.",
                "Publishing is disabled in this build. Use manual export as the safe fallback.",
            ),
        )

    def getOAuthConfig(self) -> OAuthConfig:
        config = load_tiktok_config()
        status = (
            PlatformFeatureStatus.READY_FOR_TESTING
            if not config.missingConfigKeys and config.realOAuthEnabled
            else PlatformFeatureStatus.REQUIRES_CREDENTIALS
        )
        return OAuthConfig(
            platform=self.platform,
            authorizationUrl=TIKTOK_AUTH_URL,
            tokenUrl=TIKTOK_TOKEN_URL,
            redirectUri=config.redirectUri,
            clientIdConfigured=bool(config.clientKey),
            scopes=self.requiredScopes,
            status=status,
            notes="TikTok OAuth is scaffolded. Mock mode is default and video posting remains disabled.",
        )

    def buildAuthorizationUrl(self, request: OAuthStartRequest) -> OAuthStartResult:
        config = load_tiktok_config()
        redirect_uri = request.redirectUri or config.redirectUri
        scopes = request.requestedScopes or tuple(scope.id for scope in self.requiredScopes if scope.required)
        mode = str(request.metadata.get("mode") or os.environ.get("INTEGRATIONS_MODE") or "mock").lower()
        state = str(request.metadata.get("state") or "mock-state-local-only")

        if mode == "mock":
            return OAuthStartResult(
                success=True,
                authorizationUrl=_mock_authorization_url(
                    redirect_uri=redirect_uri or "http://localhost:8000/api/connect/tiktok/callback",
                    state=state,
                    scopes=tuple(scopes),
                ),
                status="mock_redirect_ready",
                message="Mock TikTok authorization URL created. No real TikTok API was called.",
            )

        if config.missingConfigKeys or not redirect_uri:
            return OAuthStartResult(
                success=False,
                status="setup_required",
                message=(
                    "TikTok OAuth setup is missing required local environment variables: "
                    + ", ".join(config.missingConfigKeys)
                    + ". Do not commit secrets."
                ),
            )
        if not config.realOAuthEnabled:
            return OAuthStartResult(
                success=False,
                status="setup_required",
                message="Real TikTok OAuth is disabled. Keep mock mode unless a future task enables guarded OAuth.",
            )

        return OAuthStartResult(
            success=True,
            authorizationUrl=_real_authorization_url(
                client_key=config.clientKey or "",
                redirect_uri=redirect_uri,
                state=state,
                scopes=tuple(scopes),
            ),
            status="redirect_ready",
            message="Guarded TikTok authorization URL built locally. Token exchange and posting remain disabled.",
        )

    def handleOAuthCallback(self, request: OAuthCallbackRequest) -> OAuthCallbackResult:
        if request.error:
            return OAuthCallbackResult(
                success=False,
                status="provider_error",
                message="TikTok OAuth returned an error. No token exchange was attempted.",
            )
        if not request.state:
            return OAuthCallbackResult(
                success=False,
                status="missing_state",
                message="OAuth callback state is required and must be validated server-side.",
            )
        if not request.code:
            return OAuthCallbackResult(
                success=False,
                status="missing_code",
                message="OAuth callback code is required. The code is not logged or exchanged in this scaffold.",
            )
        return OAuthCallbackResult(
            success=False,
            status="token_exchange_not_implemented",
            message="TikTok token exchange is scaffolded only. Mock OAuth remains the default path.",
        )

    def getAccountProfile(
        self,
        account_id: str | None = None,
        **kwargs: Any,
    ) -> ConnectedAccountProfile | None:
        result = self.validateConnection(account_id, debug=True, **kwargs)
        if not result.platformAccountId or not result.displayName:
            return None
        return ConnectedAccountProfile(
            platform=self.platform,
            providerAccountId=result.platformAccountId,
            displayName=result.displayName,
            handle=result.username,
            accountType=result.accountType,
            metadata={"healthStatus": result.status, "connectionStatus": result.connectionStatus},
        )

    def validateConnection(
        self,
        account_id: str | None = None,
        *,
        database_path: str | Path | None = None,
        http_client_config: PlatformHttpClientConfig | None = None,
        now: str | datetime | None = None,
        debug: bool = False,
        **kwargs: Any,
    ) -> ConnectorHealthResult:
        checked_at = _utc_timestamp(now)
        db_path = initialize_database(resolve_database_path(database_path))
        account = _load_account(db_path, account_id)
        if account is None:
            return ConnectorHealthResult(
                platform=self.platform,
                status="error",
                featureStatus=self.featureStatus,
                socialAccountId=account_id,
                checkedAt=checked_at,
                errors=["account_not_found: Connected account was not found locally."],
                message="Connected account was not found locally.",
            )
        if account["platform"] != self.platform:
            return ConnectorHealthResult(
                platform=self.platform,
                status="error",
                featureStatus=self.featureStatus,
                socialAccountId=account_id,
                checkedAt=checked_at,
                connectionStatus=account["connection_status"],
                errors=["platform_mismatch: Connected account belongs to another platform."],
                message="Connected account platform does not match this connector.",
            )

        response = PlatformHttpClient(
            http_client_config
            or PlatformHttpClientConfig(provider="tiktok", platform=self.platform, allowNetwork=False)
        ).request(_profile_request())
        if not response.ok:
            result = _health_from_failed_response(account, response, checked_at=checked_at, debug=debug)
            _record_tiktok_health(db_path, result)
            return result

        payload = response.json if isinstance(response.json, dict) else {}
        profile = _extract_profile(payload)
        platform_account_id = profile.get("id") or account["platform_account_id"] or f"mock-tiktok-{account['id']}"
        display_name = profile.get("displayName") or account["display_name"] or "Mock TikTok Account"
        username = profile.get("username") or account["username"]
        status = "healthy"
        warnings: list[str] = []
        if response.mocked and not profile:
            warnings.append("mock_discovery: Mock TikTok profile was synthesized locally.")
        elif not profile:
            status = "limited"
            warnings.append("discovery_incomplete: Provider response did not include profile data.")

        result = ConnectorHealthResult(
            platform=self.platform,
            status=status,
            featureStatus=self.featureStatus,
            socialAccountId=account_id,
            checkedAt=checked_at,
            connectionStatus="connected",
            accountType="business",
            displayName=display_name,
            username=username,
            platformAccountId=platform_account_id,
            warnings=warnings,
            message="TikTok profile health checked through mock/scaffold discovery.",
            rawProviderResponseRedacted=_redacted_response_text(response) if debug else None,
        )
        _record_tiktok_health(db_path, result)
        return result

    def publishVideo(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return ConnectorActionResult(
            success=False,
            status="disabled_by_policy",
            message=(
                "TikTok video posting is disabled by policy. "
                f"{DISABLED_PUBLISHING_MESSAGE}"
            ),
            metadata={
                "platform": self.platform,
                "realPublishingEnabled": False,
                "postingEnabled": False,
                "uploadEnabled": False,
            },
        )


def _mock_authorization_url(*, redirect_uri: str, state: str, scopes: tuple[str, ...]) -> str:
    query = urlencode(
        {
            "platform": "tiktok",
            "response_type": "code",
            "client_key": "mock-tiktok-client",
            "redirect_uri": redirect_uri,
            "scope": ",".join(scopes),
            "state": state,
            "mock": "true",
        }
    )
    return f"{MOCK_TIKTOK_AUTH_BASE_URL}/authorize?{query}"


def _real_authorization_url(
    *,
    client_key: str,
    redirect_uri: str,
    state: str,
    scopes: tuple[str, ...],
) -> str:
    query = urlencode(
        {
            "client_key": client_key,
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(scopes),
        }
    )
    return f"{TIKTOK_AUTH_URL}?{query}"


def _profile_request() -> PlatformHttpRequest:
    return PlatformHttpRequest(
        method=PlatformHttpMethod.GET,
        url=TIKTOK_PROFILE_URL,
        query={"fields": "open_id,union_id,avatar_url,display_name"},
    )


def _extract_profile(payload: dict[str, Any]) -> dict[str, str]:
    user = payload.get("data")
    if isinstance(user, dict) and isinstance(user.get("user"), dict):
        user = user["user"]
    if not isinstance(user, dict):
        return {}
    return {
        "id": str(user.get("open_id") or user.get("id") or ""),
        "displayName": str(user.get("display_name") or user.get("displayName") or ""),
        "username": str(user.get("username") or user.get("unique_id") or ""),
    }


def _health_from_failed_response(
    account: sqlite3.Row,
    response: PlatformHttpResponse,
    *,
    checked_at: str,
    debug: bool,
) -> ConnectorHealthResult:
    status = response.error.status if response.error else "provider_error"
    provider_error = response.error.providerError if response.error else None
    if provider_error is None and response.status is not None:
        provider_error = normalize_provider_error(
            provider="tiktok",
            platform="tiktok",
            status=response.status,
            payload=response.json,
            raw_text=response.text,
        )
    if status == "network_disabled":
        health_status = "network_disabled"
        connection_status = account["connection_status"]
        requires_reauth = False
    elif provider_error and provider_error.requiresReauth:
        health_status = "expired"
        connection_status = "requires_reauth"
        requires_reauth = True
    elif provider_error and provider_error.missingPermission:
        health_status = "missing_permissions"
        connection_status = "limited"
        requires_reauth = False
    else:
        health_status = "error"
        connection_status = account["connection_status"]
        requires_reauth = False
    return ConnectorHealthResult(
        platform="tiktok",
        status=health_status,
        featureStatus=PlatformFeatureStatus.MOCK_ONLY,
        socialAccountId=account["id"],
        checkedAt=checked_at,
        connectionStatus=connection_status,
        requiresReauth=requires_reauth,
        accountType=account["account_type"],
        displayName=account["display_name"],
        username=account["username"],
        platformAccountId=account["platform_account_id"],
        errors=[provider_error.userSafeMessage if provider_error else "TikTok health check failed safely."],
        retryable=bool(provider_error and provider_error.retryable),
        message=provider_error.userSafeMessage if provider_error else "TikTok health check failed safely.",
        rawProviderResponseRedacted=_redacted_response_text(response) if debug else None,
    )


def _record_tiktok_health(db_path: Path, result: ConnectorHealthResult) -> None:
    timestamp = result.checkedAt or _utc_timestamp(None)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            UPDATE social_accounts
            SET platform_account_id = COALESCE(?, platform_account_id),
                display_name = COALESCE(?, display_name),
                username = COALESCE(?, username),
                account_type = ?,
                connection_status = ?,
                requires_reauth = ?,
                last_validated_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                result.platformAccountId,
                result.displayName,
                result.username,
                result.accountType or "business",
                result.connectionStatus,
                1 if result.requiresReauth else 0,
                timestamp,
                timestamp,
                result.socialAccountId,
            ),
        )
        connection.execute(
            """
            INSERT INTO connector_health_checks (
              id, platform, social_account_id, health_status, feature_status,
              message, safe_metadata_json, checked_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"health-tiktok-{uuid.uuid4().hex[:12]}",
                result.platform,
                result.socialAccountId,
                result.status,
                result.featureStatus.value,
                result.message,
                json.dumps(
                    {
                        "connectionStatus": result.connectionStatus,
                        "requiresReauth": result.requiresReauth,
                        "warnings": result.warnings,
                        "errors": result.errors,
                        "accountType": result.accountType,
                        "displayName": result.displayName,
                        "username": result.username,
                        "platformAccountId": result.platformAccountId,
                    },
                    sort_keys=True,
                ),
                timestamp,
                timestamp,
            ),
        )
        connection.commit()
    create_connector_audit_log(
        db_path,
        platform="tiktok",
        social_account_id=result.socialAccountId,
        action="connection_validate",
        status=result.status,
        message=result.message or "TikTok connector health check completed locally.",
        safe_metadata={
            "connectionStatus": result.connectionStatus,
            "requiresReauth": result.requiresReauth,
            "warnings": result.warnings,
            "errors": result.errors,
        },
        now=timestamp,
    )


def _load_account(db_path: Path, account_id: str | None) -> sqlite3.Row | None:
    if not account_id:
        return None
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute("SELECT * FROM social_accounts WHERE id = ?", (account_id,)).fetchone()


def _redacted_response_text(response: PlatformHttpResponse) -> str:
    payload = response.json if response.json is not None else response.text
    if isinstance(payload, str):
        return redact_raw_text(payload)
    return json.dumps(redact_http_value(payload).value, sort_keys=True)


def _env_value(env: dict[str, str], key: str) -> str | None:
    value = env.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _env_truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"1", "true", "yes", "on"})


def _utc_timestamp(value: str | datetime | None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
