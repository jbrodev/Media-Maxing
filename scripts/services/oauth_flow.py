from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from scripts.connectors.meta.config import load_meta_config
from scripts.connectors.meta.oauth import (
    SUPPORTED_META_OAUTH_PLATFORMS,
    build_meta_token_exchange_request,
)
from scripts.connectors.registry import (
    ConnectorRegistryError,
    get_connector,
    list_connector_metadata,
)
from scripts.db.init_db import initialize_database, resolve_database_path
from scripts.db.social_connections import (
    create_connector_audit_log,
    create_mock_social_account,
    create_oauth_state_record,
    create_placeholder_platform_token,
    list_safe_social_accounts,
)
from scripts.services.platform_http_client import (
    NetworkSafetyMode,
    PlatformHttpClient,
    PlatformHttpClientConfig,
    normalize_provider_error,
)
from scripts.services.token_security import TokenSecurityService


DEFAULT_OAUTH_STATE_TTL_SECONDS = 600
DEFAULT_MOCK_AUTHORIZE_BASE_URL = "http://localhost/mock-oauth"


@dataclass(frozen=True)
class OAuthStartServiceResult:
    success: bool
    platform: str
    status: str
    message: str
    authorizationUrl: str | None = None
    stateId: str | None = None
    expiresAt: str | None = None
    warnings: list[str] = field(default_factory=list)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "status": self.status,
            "message": self.message,
            "authorizationUrl": self.authorizationUrl,
            "stateId": self.stateId,
            "expiresAt": self.expiresAt,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class OAuthCallbackServiceResult:
    success: bool
    platform: str
    status: str
    message: str
    account: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "platform": self.platform,
            "status": self.status,
            "message": self.message,
            "account": self.account,
            "warnings": self.warnings,
        }


class OAuthFlowService:
    """Safe local OAuth scaffolding.

    This service supports mock OAuth only by default. It never exchanges real
    authorization codes, never stores raw state values, never logs codes or
    tokens, and never publishes content.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        state_ttl_seconds: int = DEFAULT_OAUTH_STATE_TTL_SECONDS,
        integrations_mode: str | None = None,
        http_client_config: PlatformHttpClientConfig | None = None,
    ):
        self.database_path = initialize_database(resolve_database_path(database_path))
        self.state_ttl_seconds = state_ttl_seconds
        self.integrations_mode = integrations_mode or os.environ.get("INTEGRATIONS_MODE") or "mock"
        self.http_client_config = http_client_config

    def start_oauth(
        self,
        *,
        platform: str,
        redirect_uri: str,
        requested_scopes: list[str] | None = None,
        now: str | datetime | None = None,
    ) -> OAuthStartServiceResult:
        normalized_platform = platform.strip().lower()
        try:
            connector = get_connector(normalized_platform)
        except ConnectorRegistryError as error:
            return OAuthStartServiceResult(
                success=False,
                platform=normalized_platform,
                status="unsupported_platform",
                message=str(error),
            )

        capabilities = connector.getCapabilities()
        if not capabilities.supportsOAuth:
            self._audit(
                normalized_platform,
                action="oauth_start",
                status="failed",
                message="Connector does not support OAuth.",
            )
            return OAuthStartServiceResult(
                success=False,
                platform=normalized_platform,
                status="oauth_not_supported",
                message="Connector does not support OAuth.",
            )

        parsed_now = _parse_datetime(now)
        expires_at = parsed_now + timedelta(seconds=self.state_ttl_seconds)
        state = secrets.token_urlsafe(32)
        state_hash = _hash_state(state)
        scopes = requested_scopes or [scope.id for scope in connector.getRequiredScopes()]
        state_id = create_oauth_state_record(
            self.database_path,
            platform=normalized_platform,
            state_hash=state_hash,
            redirect_uri=redirect_uri,
            requested_scopes=scopes,
            expires_at=_to_iso(expires_at),
            now=_to_iso(parsed_now),
        )
        authorization_url = self._build_authorization_url(
            platform=normalized_platform,
            redirect_uri=redirect_uri,
            state=state,
            scopes=scopes,
        )
        self._audit(
            normalized_platform,
            action="oauth_start",
            status="succeeded",
            message="Mock OAuth start created local state.",
            safe_metadata={
                "stateId": state_id,
                "requestedScopes": scopes,
                "expiresAt": _to_iso(expires_at),
                "mode": "mock",
            },
        )
        return OAuthStartServiceResult(
            success=True,
            platform=normalized_platform,
            status="redirect_ready",
            message="Mock OAuth authorization URL created.",
            authorizationUrl=authorization_url,
            stateId=state_id,
            expiresAt=_to_iso(expires_at),
            warnings=[
                "mock_oauth_only: No real platform OAuth request is made by default."
            ],
        )

    def handle_callback(
        self,
        *,
        platform: str,
        state: str | None,
        code: str | None,
        error: str | None = None,
        now: str | datetime | None = None,
    ) -> OAuthCallbackServiceResult:
        normalized_platform = platform.strip().lower()
        try:
            get_connector(normalized_platform)
        except ConnectorRegistryError as connector_error:
            return OAuthCallbackServiceResult(
                success=False,
                platform=normalized_platform,
                status="unsupported_platform",
                message=str(connector_error),
            )

        if not state:
            self._audit(
                normalized_platform,
                action="oauth_callback",
                status="failed",
                message="OAuth callback was missing state.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=normalized_platform,
                status="missing_state",
                message="OAuth callback is missing state.",
            )

        state_row = self._find_state(normalized_platform, _hash_state(state))
        if state_row is None:
            self._audit(
                normalized_platform,
                action="oauth_callback",
                status="failed",
                message="OAuth callback state was invalid.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=normalized_platform,
                status="invalid_state",
                message="OAuth callback state is invalid.",
            )

        if state_row["status"] == "consumed":
            self._audit(
                normalized_platform,
                action="oauth_callback",
                status="failed",
                message="OAuth callback state was reused.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=normalized_platform,
                status="reused_state",
                message="OAuth callback state has already been used.",
            )

        parsed_now = _parse_datetime(now)
        expires_at = _parse_datetime(state_row["expires_at"])
        if expires_at <= parsed_now or state_row["status"] == "expired":
            self._mark_state(state_row["id"], "expired", now=parsed_now)
            self._audit(
                normalized_platform,
                action="oauth_callback",
                status="failed",
                message="OAuth callback state expired.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=normalized_platform,
                status="expired_state",
                message="OAuth callback state has expired.",
            )

        if error:
            self._mark_state(state_row["id"], "failed", now=parsed_now, error_message="Provider returned an OAuth error.")
            self._audit(
                normalized_platform,
                action="oauth_callback",
                status="failed",
                message="OAuth provider returned an error.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=normalized_platform,
                status="provider_error",
                message="OAuth provider returned an error.",
            )

        if not code:
            self._audit(
                normalized_platform,
                action="oauth_callback",
                status="failed",
                message="OAuth callback was missing code.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=normalized_platform,
                status="missing_code",
                message="OAuth callback is missing code.",
            )

        if self.integrations_mode != "mock":
            return self._handle_real_oauth_callback(
                platform=normalized_platform,
                state_row=state_row,
                code=code,
                now=parsed_now,
            )

        account_id = self._create_mock_account(normalized_platform, state_row, now=parsed_now)
        self._mark_state(state_row["id"], "consumed", now=parsed_now)
        self._audit(
            normalized_platform,
            action="oauth_callback",
            status="succeeded",
            message="Mock OAuth callback connected a local demo account.",
            social_account_id=account_id,
            safe_metadata={
                "mode": "mock",
                "stateId": state_row["id"],
                "tokenStorage": "placeholder_not_stored",
            },
        )
        account = next(
            (
                item
                for item in TokenSecurityService(self.database_path).list_safe_social_account_dtos()
                if item["id"] == account_id
            ),
            None,
        )
        return OAuthCallbackServiceResult(
            success=True,
            platform=normalized_platform,
            status="mock_connected",
            message="Mock OAuth connection completed locally. No real token exchange occurred.",
            account=account,
            warnings=[
                "mock_connection_only: No real platform account was connected and no token was stored."
            ],
        )

    def _handle_real_oauth_callback(
        self,
        *,
        platform: str,
        state_row: sqlite3.Row,
        code: str,
        now: datetime,
    ) -> OAuthCallbackServiceResult:
        if platform not in SUPPORTED_META_OAUTH_PLATFORMS:
            self._audit(
                platform,
                action="oauth_callback",
                status="blocked",
                message="Real OAuth token exchange is implemented only for Meta scaffolds.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=platform,
                status="real_oauth_not_implemented",
                message="Real OAuth token exchange is implemented only for Meta scaffolds in this batch.",
            )

        env = dict(os.environ)
        mode = (self.integrations_mode or env.get("INTEGRATIONS_MODE") or "mock").strip().lower()
        global_oauth_enabled = _env_truthy(env.get("ENABLE_REAL_OAUTH")) or mode == "real_oauth"
        platform_oauth_enabled = _env_truthy(env.get("META_ENABLE_REAL_OAUTH"))
        real_network_enabled = _env_truthy(env.get("ENABLE_REAL_NETWORK_CALLS"))
        if not global_oauth_enabled or not platform_oauth_enabled:
            self._audit(
                platform,
                action="oauth_callback",
                status="blocked",
                message="Real Meta OAuth is disabled by feature flags.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=platform,
                status="real_oauth_disabled",
                message="Real Meta OAuth is disabled. No token exchange was attempted.",
            )
        if not real_network_enabled:
            self._audit(
                platform,
                action="oauth_callback",
                status="blocked",
                message="Real network calls are disabled by feature flags.",
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=platform,
                status="real_network_disabled",
                message="Real network calls are disabled. No token exchange was attempted.",
            )

        config = load_meta_config(env)
        if config.missingConfigKeys:
            self._audit(
                platform,
                action="oauth_callback",
                status="blocked",
                message="Meta OAuth configuration is incomplete.",
                safe_metadata={"missingConfigKeys": list(config.missingConfigKeys)},
            )
            return OAuthCallbackServiceResult(
                success=False,
                platform=platform,
                status="setup_required",
                message="Meta OAuth configuration is incomplete. No token exchange was attempted.",
                warnings=[
                    "missing_config: " + ", ".join(config.missingConfigKeys)
                ],
            )

        redirect_uri = state_row["redirect_uri"] or config.redirectUri
        token_request = build_meta_token_exchange_request(
            config=config,
            code=code,
            redirect_uri=redirect_uri,
        )
        http_config = self.http_client_config or PlatformHttpClientConfig(
            provider="meta",
            platform=platform,
            safetyMode=NetworkSafetyMode.ENABLED,
            allowNetwork=True,
        )
        response = PlatformHttpClient(http_config).request(token_request)
        if not response.ok:
            provider_error = (
                response.error.providerError
                if response.error and response.error.providerError
                else normalize_provider_error(
                    provider="meta",
                    platform=platform,
                    status=response.status,
                    payload=response.json,
                    raw_text=response.text,
                )
            )
            self._mark_state(
                state_row["id"],
                "failed",
                now=now,
                error_message=provider_error.userSafeMessage,
            )
            self._audit(
                platform,
                action="token_exchange",
                status="failed",
                message=provider_error.userSafeMessage,
                safe_metadata={
                    "providerStatus": provider_error.status,
                    "errorCode": provider_error.code,
                    "requiresReauth": provider_error.requiresReauth,
                    "rateLimited": provider_error.rateLimited,
                },
            )
            if provider_error.requiresReauth:
                status = "provider_requires_reauth"
            elif provider_error.rateLimited:
                status = "provider_rate_limited"
            else:
                status = "provider_error"
            return OAuthCallbackServiceResult(
                success=False,
                platform=platform,
                status=status,
                message=provider_error.userSafeMessage,
            )

        token_payload = response.json if isinstance(response.json, dict) else {}
        account_id = self._create_limited_real_meta_account(
            platform,
            state_row,
            token_payload=token_payload,
            now=now,
        )
        token_storage = TokenSecurityService(self.database_path).store_token_set(
            social_account_id=account_id,
            platform=platform,
            token_set=_token_payload_for_storage(token_payload, now=now),
            token_type="oauth_access",
        )
        scopes = _scopes_from_token_payload(token_payload)
        if not token_storage.success and token_storage.encryptionStatus == "placeholder_not_stored":
            create_placeholder_platform_token(
                self.database_path,
                social_account_id=account_id,
                platform=platform,
                token_type="oauth_access",
                scope=" ".join(scopes),
                now=_to_iso(now),
            )

        self._mark_state(state_row["id"], "consumed", now=now)
        self._audit(
            platform,
            action="token_exchange",
            status="succeeded_limited",
            message="Meta OAuth token exchange completed through guarded server-side path.",
            social_account_id=account_id,
            safe_metadata={
                "tokenStorageMode": token_storage.storageMode,
                "encryptionStatus": token_storage.encryptionStatus,
                "tokenStored": token_storage.success,
                "accountDiscovery": "not_implemented",
                "longLivedExchange": "not_implemented",
            },
        )
        self._audit(
            platform,
            action="oauth_callback",
            status="succeeded",
            message="Real Meta OAuth callback completed with limited local account metadata.",
            social_account_id=account_id,
            safe_metadata={
                "mode": "real_oauth",
                "stateId": state_row["id"],
                "realPublishingEnabled": False,
            },
        )
        account = next(
            (
                item
                for item in TokenSecurityService(self.database_path).list_safe_social_account_dtos()
                if item["id"] == account_id
            ),
            None,
        )
        return OAuthCallbackServiceResult(
            success=True,
            platform=platform,
            status="real_oauth_limited_connected",
            message=(
                "Meta OAuth token exchange completed locally. Account discovery "
                "is not implemented yet, so the account is limited and publishing remains disabled."
            ),
            account=account,
            warnings=[
                "account_discovery_not_implemented: Created a limited account with unknown provider account ID.",
                "long_lived_token_exchange_not_implemented: Only the short-lived token exchange path is scaffolded.",
                "real_publishing_disabled_by_policy: No publishing methods were enabled.",
            ],
        )

    def disconnect(
        self,
        *,
        platform: str,
        social_account_id: str,
        now: str | datetime | None = None,
    ) -> dict[str, Any]:
        normalized_platform = platform.strip().lower()
        parsed_now = _parse_datetime(now)
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                """
                UPDATE social_accounts
                SET connection_status = 'disconnected',
                    disconnected_at = ?,
                    updated_at = ?
                WHERE id = ? AND platform = ?
                """,
                (_to_iso(parsed_now), _to_iso(parsed_now), social_account_id, normalized_platform),
            )
            updated = connection.total_changes
            connection.commit()
        self._audit(
            normalized_platform,
            action="disconnect",
            status="succeeded" if updated else "not_found",
            message="Local disconnect completed. No external revoke call was made.",
            social_account_id=social_account_id if updated else None,
        )
        return {
            "success": bool(updated),
            "platform": normalized_platform,
            "status": "local_disconnected" if updated else "not_found",
            "message": "Local disconnect completed. No external revoke call was made."
            if updated
            else "No matching local account was found.",
        }

    def _build_authorization_url(
        self,
        *,
        platform: str,
        redirect_uri: str,
        state: str,
        scopes: list[str],
    ) -> str:
        query = urlencode(
            {
                "platform": platform,
                "response_type": "code",
                "client_id": f"mock-{platform}-client",
                "redirect_uri": redirect_uri,
                "scope": " ".join(scopes),
                "state": state,
                "mock": "true",
            }
        )
        return f"{DEFAULT_MOCK_AUTHORIZE_BASE_URL}/{platform}/authorize?{query}"

    def _create_mock_account(
        self,
        platform: str,
        state_row: sqlite3.Row,
        *,
        now: datetime,
    ) -> str:
        scopes = _decode_json(state_row["requested_scopes_json"], [])
        account_id = create_mock_social_account(
            self.database_path,
            platform=platform,
            display_name=f"Mock {platform.title()} Account",
            username=f"mock-{platform}",
            platform_account_id=f"mock-{platform}-account",
            account_type=_account_type_for_platform(platform),
            connection_status="connected",
            capabilities={
                "canConnect": True,
                "canReadProfile": True,
                "canPublishText": False,
                "canPublishImage": False,
                "canPublishVideo": False,
                "supportsManualExportFallback": True,
                "mockOAuth": True,
                "realPublishingEnabled": False,
            },
            granted_scopes=scopes,
            missing_scopes=[],
            now=_to_iso(now),
        )
        create_placeholder_platform_token(
            self.database_path,
            social_account_id=account_id,
            platform=platform,
            token_type="app_token_placeholder",
            scope=" ".join(scopes),
            now=_to_iso(now),
        )
        return account_id

    def _create_limited_real_meta_account(
        self,
        platform: str,
        state_row: sqlite3.Row,
        *,
        token_payload: dict[str, Any],
        now: datetime,
    ) -> str:
        scopes = _scopes_from_token_payload(token_payload)
        account_id = f"acct-meta-{platform}-{state_row['id'][-12:]}"
        return create_mock_social_account(
            self.database_path,
            platform=platform,
            display_name=f"Limited {platform.title()} Account",
            username=None,
            platform_account_id=f"unknown-{platform}-{state_row['id'][-12:]}",
            account_type=_account_type_for_platform(platform),
            connection_status="limited",
            capabilities={
                "canConnect": True,
                "canReadProfile": False,
                "canPublishText": False,
                "canPublishImage": False,
                "canPublishVideo": False,
                "supportsManualExportFallback": True,
                "realOAuth": True,
                "accountDiscoveryImplemented": False,
                "realPublishingEnabled": False,
            },
            granted_scopes=scopes,
            missing_scopes=[],
            requires_reauth=True,
            account_id=account_id,
            now=_to_iso(now),
        )

    def _find_state(self, platform: str, state_hash: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                """
                SELECT *
                FROM oauth_states
                WHERE platform = ?
                  AND state_hash = ?
                LIMIT 1
                """,
                (platform, state_hash),
            ).fetchone()

    def _mark_state(
        self,
        state_id: str,
        status: str,
        *,
        now: datetime,
        error_message: str | None = None,
    ) -> None:
        consumed_at = _to_iso(now) if status == "consumed" else None
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute(
                """
                UPDATE oauth_states
                SET status = ?,
                    consumed_at = COALESCE(?, consumed_at),
                    error_message = COALESCE(?, error_message)
                WHERE id = ?
                """,
                (status, consumed_at, error_message, state_id),
            )
            connection.commit()

    def _audit(
        self,
        platform: str,
        *,
        action: str,
        status: str,
        message: str,
        social_account_id: str | None = None,
        safe_metadata: dict[str, Any] | None = None,
    ) -> None:
        create_connector_audit_log(
            self.database_path,
            platform=platform,
            action=action,
            status=status,
            message=message,
            social_account_id=social_account_id,
            safe_metadata=safe_metadata or {},
        )


def connect_start_handler(
    platform: str,
    payload: dict[str, Any] | None = None,
    *,
    database_path: str | Path | None = None,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    redirect_uri = payload.get("redirectUri") or payload.get("redirect_uri")
    if not isinstance(redirect_uri, str) or not redirect_uri.strip():
        redirect_uri = f"http://localhost:8000/api/connect/{platform}/callback"
    scopes = payload.get("requestedScopes") or payload.get("requested_scopes") or []
    if not isinstance(scopes, list):
        scopes = []
    return OAuthFlowService(database_path).start_oauth(
        platform=platform,
        redirect_uri=redirect_uri,
        requested_scopes=[str(scope) for scope in scopes],
        now=now,
    ).to_safe_dict()


def connect_callback_handler(
    platform: str,
    query: dict[str, Any] | None = None,
    *,
    database_path: str | Path | None = None,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    query = query or {}
    return OAuthFlowService(database_path).handle_callback(
        platform=platform,
        state=_optional_string(query.get("state")),
        code=_optional_string(query.get("code")),
        error=_optional_string(query.get("error")),
        now=now,
    ).to_safe_dict()


def connect_disconnect_handler(
    platform: str,
    payload: dict[str, Any] | None = None,
    *,
    database_path: str | Path | None = None,
    now: str | datetime | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    account_id = _optional_string(payload.get("socialAccountId") or payload.get("social_account_id"))
    if not account_id:
        return {
            "success": False,
            "platform": platform,
            "status": "missing_account_id",
            "message": "A social account ID is required for disconnect.",
        }
    return OAuthFlowService(database_path).disconnect(
        platform=platform,
        social_account_id=account_id,
        now=now,
    )


def connect_accounts_handler(
    *,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "accounts": TokenSecurityService(database_path).list_safe_social_account_dtos(),
    }


def connect_platforms_handler(
    *,
    database_path: str | Path | None = None,
) -> dict[str, Any]:
    return {
        "success": True,
        "platforms": [
            {
                "platform": metadata.platform,
                "label": metadata.label,
                "featureStatus": metadata.featureStatus.value,
                "capabilities": metadata.capabilities.to_dict(),
                "setupSummary": metadata.setupSummary,
                "configured": metadata.configured,
            }
            for metadata in list_connector_metadata()
        ],
    }


def _hash_state(state: str) -> str:
    return "sha256:" + hashlib.sha256(state.encode("utf-8")).hexdigest()


def _parse_datetime(value: str | datetime | None) -> datetime:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value
    else:
        raw = value[:-1] + "+00:00" if value.endswith("Z") else value
        parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _account_type_for_platform(platform: str) -> str:
    if platform == "youtube":
        return "channel"
    if platform == "linkedin":
        return "organization"
    if platform == "facebook":
        return "page"
    if platform in {"instagram", "threads", "tiktok", "x"}:
        return "business" if platform in {"instagram", "tiktok"} else "unknown"
    return "unknown"


def _env_truthy(value: str | None) -> bool:
    return bool(value and value.strip().lower() in {"1", "true", "yes", "on"})


def _scopes_from_token_payload(token_payload: dict[str, Any]) -> list[str]:
    raw_scope = token_payload.get("scope") or token_payload.get("scopes") or []
    if isinstance(raw_scope, str):
        separator = "," if "," in raw_scope else " "
        return [scope.strip() for scope in raw_scope.split(separator) if scope.strip()]
    if isinstance(raw_scope, list):
        return [str(scope).strip() for scope in raw_scope if str(scope).strip()]
    return []


def _token_payload_for_storage(
    token_payload: dict[str, Any],
    *,
    now: datetime,
) -> dict[str, Any]:
    result = dict(token_payload)
    expires_in = token_payload.get("expires_in")
    if isinstance(expires_in, int) and expires_in > 0:
        from datetime import timedelta

        result["access_token_expires_at"] = _to_iso(now + timedelta(seconds=expires_in))
    return result
