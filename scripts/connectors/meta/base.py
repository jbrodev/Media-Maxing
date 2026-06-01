from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from typing import Any
from pathlib import Path

from scripts.connectors.base import DISABLED_PUBLISHING_MESSAGE, SocialConnector
from scripts.connectors.meta.config import load_meta_config
from scripts.connectors.meta.errors import missing_meta_config_error
from scripts.connectors.meta.oauth import (
    build_mock_meta_authorization_url,
    build_meta_profile_request,
    build_real_meta_authorization_url,
)
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
    PlatformHttpResponse,
    normalize_provider_error,
    redact_http_value,
    redact_raw_text,
)
from scripts.services.token_security import is_token_expired


class MetaConnector(SocialConnector):
    required_account_type = "business"

    def __init__(
        self,
        *,
        platform: str,
        label: str,
        capabilities: ConnectorCapabilities,
        required_scopes: tuple[PlatformPermissionScope, ...],
        setup_instructions: tuple[str, ...],
    ) -> None:
        super().__init__(
            platform=platform,
            label=label,
            featureStatus=PlatformFeatureStatus.MOCK_ONLY,
            capabilities=capabilities,
            requiredScopes=required_scopes,
            setupInstructions=setup_instructions,
        )

    def getOAuthConfig(self) -> OAuthConfig:
        config = load_meta_config()
        status = (
            PlatformFeatureStatus.READY_FOR_TESTING
            if config.realOAuthReady
            else PlatformFeatureStatus.REQUIRES_CREDENTIALS
        )
        return OAuthConfig(
            platform=self.platform,
            authorizationUrl=f"https://www.facebook.com/{config.graphApiVersion}/dialog/oauth",
            tokenUrl=f"https://graph.facebook.com/{config.graphApiVersion}/oauth/access_token",
            redirectUri=config.redirectUri,
            clientIdConfigured=config.clientIdConfigured,
            scopes=self.requiredScopes,
            status=status,
            notes=(
                "Meta OAuth is scaffolded. Real token exchange is not active in "
                "this batch, and publishing remains disabled."
            ),
        )

    def buildAuthorizationUrl(self, request: OAuthStartRequest) -> OAuthStartResult:
        config = load_meta_config()
        redirect_uri = request.redirectUri or config.redirectUri
        scopes = request.requestedScopes or tuple(scope.id for scope in self.requiredScopes)
        mode = str(request.metadata.get("mode") or config.integrationsMode or "mock").lower()
        state = str(request.metadata.get("state") or "mock-state-local-only")

        if mode == "mock":
            if not redirect_uri:
                redirect_uri = f"http://localhost:8000/api/connect/{self.platform}/callback"
            return OAuthStartResult(
                success=True,
                authorizationUrl=build_mock_meta_authorization_url(
                    platform=self.platform,
                    redirect_uri=redirect_uri,
                    state=state,
                    scopes=tuple(scopes),
                ),
                status="mock_redirect_ready",
                message=(
                    f"Mock {self.label} authorization URL created. "
                    "No real Meta API was called."
                ),
            )

        if config.missingConfigKeys or not redirect_uri:
            error = missing_meta_config_error(self.platform, config.missingConfigKeys)
            return OAuthStartResult(
                success=False,
                status="setup_required",
                message=error.message,
            )

        if not config.realOAuthEnabled:
            return OAuthStartResult(
                success=False,
                status="setup_required",
                message=(
                    "Real Meta OAuth is disabled. Set META_ENABLE_REAL_OAUTH=true "
                    "only after reviewing safety gates and configuring server-side OAuth."
                ),
            )

        return OAuthStartResult(
            success=True,
            authorizationUrl=build_real_meta_authorization_url(
                config=config,
                redirect_uri=redirect_uri,
                state=state,
                scopes=tuple(scopes),
            ),
            status="redirect_ready",
            message=(
                "Real Meta authorization URL built locally. Token exchange remains "
                "disabled until a future explicit task implements it safely."
            ),
        )

    def handleOAuthCallback(self, request: OAuthCallbackRequest) -> OAuthCallbackResult:
        if request.error:
            return OAuthCallbackResult(
                success=False,
                status="provider_error",
                message="Meta OAuth returned an error. No token exchange was attempted.",
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
                message="OAuth callback code is required. The code is not logged or exchanged in this batch.",
            )
        return OAuthCallbackResult(
            success=False,
            status="token_exchange_disabled",
            message=(
                "Meta callback scaffold received safe fields, but real token "
                "exchange is disabled. Validate state through OAuthFlowService "
                "before future token exchange work."
            ),
        )

    def exchangeAuthorizationCode(
        self,
        *,
        database_path: str | Path | None = None,
        state: str | None,
        code: str | None,
        http_client_config: PlatformHttpClientConfig | None = None,
        now: str | None = None,
    ):
        """Exchange a Meta OAuth code through the server-side state service.

        The connector exposes this convenience entry point, but the actual
        safety gates, state validation, token storage, and audit logging live
        in OAuthFlowService so all OAuth callbacks use the same boundary.
        """
        from scripts.services.oauth_flow import OAuthFlowService

        return OAuthFlowService(
            database_path,
            integrations_mode="real_oauth",
            http_client_config=http_client_config,
        ).handle_callback(
            platform=self.platform,
            state=state,
            code=code,
            now=now,
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
            metadata={
                "healthStatus": result.status,
                "connectionStatus": result.connectionStatus,
                "mockOrScaffolded": True,
            },
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
        account = _load_social_account(db_path, account_id)
        if account is None:
            return self._record_health(
                db_path,
                ConnectorHealthResult(
                    platform=self.platform,
                    status="error",
                    featureStatus=self.featureStatus,
                    socialAccountId=account_id,
                    checkedAt=checked_at,
                    connectionStatus="not_connected",
                    message="Connected account was not found locally.",
                    errors=["account_not_found: Connected account was not found locally."],
                ),
            )

        if account["platform"] != self.platform:
            return self._record_health(
                db_path,
                ConnectorHealthResult(
                    platform=self.platform,
                    status="error",
                    featureStatus=self.featureStatus,
                    socialAccountId=account_id,
                    checkedAt=checked_at,
                    connectionStatus=account["connection_status"],
                    message="Connected account platform does not match this connector.",
                    errors=["platform_mismatch: Connected account belongs to another platform."],
                ),
            )

        token = _load_latest_token(db_path, account_id)
        if _connection_requires_reauth(account, token, now=now):
            return self._record_health(
                db_path,
                ConnectorHealthResult(
                    platform=self.platform,
                    status="expired",
                    featureStatus=self.featureStatus,
                    socialAccountId=account_id,
                    checkedAt=checked_at,
                    connectionStatus="requires_reauth",
                    requiresReauth=True,
                    accountType=account["account_type"],
                    displayName=account["display_name"],
                    username=account["username"],
                    platformAccountId=account["platform_account_id"],
                    message="The local connection needs reauthorization before real checks can run.",
                    errors=["requires_reauth: Token metadata is expired or the connection was revoked."],
                ),
            )

        missing_scopes = _missing_required_scopes(account, self.requiredScopes)
        if missing_scopes:
            warnings = [
                "missing_scopes: This connection is missing permissions needed for future real platform checks."
            ]
            if self.platform == "instagram":
                warnings.append(
                    "instagram_business_required: Instagram discovery requires a Business or Creator account setup."
                )
            return self._record_health(
                db_path,
                ConnectorHealthResult(
                    platform=self.platform,
                    status="missing_permissions",
                    featureStatus=self.featureStatus,
                    socialAccountId=account_id,
                    checkedAt=checked_at,
                    connectionStatus="limited",
                    missingScopes=missing_scopes,
                    missingPermissions=missing_scopes,
                    accountType=account["account_type"],
                    displayName=account["display_name"],
                    username=account["username"],
                    platformAccountId=account["platform_account_id"],
                    warnings=warnings,
                    message="The connection is present but missing permissions for complete discovery.",
                ),
            )

        config = load_meta_config()
        request = build_meta_profile_request(config=config, platform=self.platform)
        response = PlatformHttpClient(
            http_client_config
            or PlatformHttpClientConfig(
                provider="meta",
                platform=self.platform,
                allowNetwork=False,
            )
        ).request(request)

        if not response.ok:
            result = self._health_from_failed_response(
                account,
                token,
                response,
                checked_at=checked_at,
                debug=debug,
            )
            return self._record_health(db_path, result)

        payload = response.json if isinstance(response.json, dict) else {}
        platform_account_id = _first_text(payload, "id") or account["platform_account_id"]
        display_name = (
            _first_text(payload, "name", "display_name")
            or account["display_name"]
        )
        username = _first_text(payload, "username", "handle") or account["username"]
        account_type = (
            _first_text(payload, "account_type", "accountType")
            or account["account_type"]
            or "unknown"
        )
        if account_type not in {"personal", "business", "creator", "page", "channel", "organization", "unknown"}:
            account_type = account["account_type"] or "unknown"

        warnings: list[str] = []
        health_status = "healthy"
        connection_status = "connected"
        if not platform_account_id or not display_name:
            health_status = "limited"
            connection_status = "limited"
            warnings.append(
                "discovery_incomplete: Provider response did not include enough account profile data."
            )
        if self.platform == "instagram" and account_type not in {"business", "creator"}:
            health_status = "limited"
            connection_status = "limited"
            warnings.append(
                "instagram_business_required: Confirm this is an Instagram Business or Creator account."
            )

        return self._record_health(
            db_path,
            ConnectorHealthResult(
                platform=self.platform,
                status=health_status,
                featureStatus=self.featureStatus,
                socialAccountId=account_id,
                canUseRealNetwork=bool(http_client_config and http_client_config.allowNetwork),
                checkedAt=checked_at,
                connectionStatus=connection_status,
                requiresReauth=False,
                accountType=account_type,
                displayName=display_name,
                username=username,
                platformAccountId=platform_account_id,
                warnings=warnings,
                message=(
                    "Meta profile discovery completed through the connector health scaffold."
                    if health_status == "healthy"
                    else "Meta profile discovery is incomplete and remains limited."
                ),
                rawProviderResponseRedacted=_redacted_response_text(response) if debug else None,
            ),
        )

    def publishText(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _meta_publishing_disabled(self.platform)

    def publishImage(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _meta_publishing_disabled(self.platform)

    def publishVideo(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _meta_publishing_disabled(self.platform)

    def publishCarousel(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _meta_publishing_disabled(self.platform)

    def _health_from_failed_response(
        self,
        account: sqlite3.Row,
        token: sqlite3.Row | None,
        response: PlatformHttpResponse,
        *,
        checked_at: str,
        debug: bool,
    ) -> ConnectorHealthResult:
        status = response.error.status if response.error else "provider_error"
        errors = [f"{status}: {response.error.message}"] if response.error else []
        provider_error = response.error.providerError if response.error else None
        if provider_error is None and response.status is not None:
            provider_error = normalize_provider_error(
                provider="meta",
                platform=self.platform,
                status=response.status,
                payload=response.json,
                raw_text=response.text,
            )
            errors.append(f"provider_error: {provider_error.userSafeMessage}")

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
            connection_status = "error" if response.status and response.status >= 500 else account["connection_status"]
            requires_reauth = False

        return ConnectorHealthResult(
            platform=self.platform,
            status=health_status,
            featureStatus=self.featureStatus,
            socialAccountId=account["id"],
            checkedAt=checked_at,
            connectionStatus=connection_status,
            requiresReauth=requires_reauth,
            accountType=account["account_type"],
            displayName=account["display_name"],
            username=account["username"],
            platformAccountId=account["platform_account_id"],
            errors=errors or ["provider_error: Provider profile check failed."],
            retryable=bool(provider_error and provider_error.retryable),
            message=(
                provider_error.userSafeMessage
                if provider_error
                else "The provider profile check failed safely."
            ),
            rawProviderResponseRedacted=_redacted_response_text(response) if debug else None,
        )

    def _record_health(
        self,
        db_path: Path,
        result: ConnectorHealthResult,
    ) -> ConnectorHealthResult:
        if result.socialAccountId:
            _update_social_account_health(db_path, result)
            _insert_connector_health_check(db_path, result)
            create_connector_audit_log(
                db_path,
                platform=self.platform,
                social_account_id=result.socialAccountId,
                action="connection_validate",
                status=result.status,
                message=result.message or "Connector health check completed locally.",
                safe_metadata=_health_safe_metadata(result),
                now=result.checkedAt,
            )
        return result


def _meta_publishing_disabled(platform: str) -> ConnectorActionResult:
    return ConnectorActionResult(
        success=False,
        status="disabled_by_policy",
        message=(
            f"{DISABLED_PUBLISHING_MESSAGE} META_ENABLE_REAL_PUBLISHING is ignored "
            "by this scaffold."
        ),
        metadata={
            "platform": platform,
            "realPublishingEnabled": False,
            "policy": "future_real_publishing_requires_explicit_platform_task",
        },
    )


def _load_social_account(db_path: Path, account_id: str | None) -> sqlite3.Row | None:
    if not account_id:
        return None
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            """
            SELECT *
            FROM social_accounts
            WHERE id = ?
            """,
            (account_id,),
        ).fetchone()


def _load_latest_token(db_path: Path, account_id: str | None) -> sqlite3.Row | None:
    if not account_id:
        return None
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            """
            SELECT *
            FROM platform_tokens
            WHERE social_account_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (account_id,),
        ).fetchone()


def _connection_requires_reauth(
    account: sqlite3.Row,
    token: sqlite3.Row | None,
    *,
    now: str | datetime | None,
) -> bool:
    if account["requires_reauth"]:
        return True
    if account["connection_status"] in {"expired", "revoked", "requires_reauth"}:
        return True
    if token is None:
        return True
    if token["revoked_at"]:
        return True
    return is_token_expired(token["access_token_expires_at"], now=now)


def _missing_required_scopes(
    account: sqlite3.Row,
    required_scopes: tuple[PlatformPermissionScope, ...],
) -> list[str]:
    granted = set(_decode_json(account["granted_scopes_json"], []))
    explicit_missing = set(_decode_json(account["missing_scopes_json"], []))
    required = {scope.id for scope in required_scopes if scope.required}
    return sorted(explicit_missing | (required - granted))


def _update_social_account_health(
    db_path: Path,
    result: ConnectorHealthResult,
) -> None:
    timestamp = result.checkedAt or _utc_timestamp(None)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            UPDATE social_accounts
            SET
              platform_account_id = COALESCE(?, platform_account_id),
              display_name = COALESCE(?, display_name),
              username = COALESCE(?, username),
              account_type = COALESCE(?, account_type),
              connection_status = ?,
              missing_scopes_json = ?,
              requires_reauth = ?,
              last_validated_at = ?,
              updated_at = ?
            WHERE id = ?
            """,
            (
                result.platformAccountId,
                result.displayName,
                result.username,
                result.accountType or "unknown",
                result.connectionStatus,
                json.dumps(result.missingScopes, sort_keys=True),
                1 if result.requiresReauth else 0,
                timestamp,
                timestamp,
                result.socialAccountId,
            ),
        )
        connection.commit()


def _insert_connector_health_check(
    db_path: Path,
    result: ConnectorHealthResult,
) -> None:
    timestamp = result.checkedAt or _utc_timestamp(None)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO connector_health_checks (
              id, platform, social_account_id, health_status, feature_status,
              message, safe_metadata_json, checked_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"health-{result.platform}-{uuid.uuid4().hex[:12]}",
                result.platform,
                result.socialAccountId,
                result.status,
                result.featureStatus.value,
                result.message,
                json.dumps(_health_safe_metadata(result), sort_keys=True),
                timestamp,
                timestamp,
            ),
        )
        connection.commit()


def _health_safe_metadata(result: ConnectorHealthResult) -> dict[str, Any]:
    return {
        "connectionStatus": result.connectionStatus,
        "requiresReauth": result.requiresReauth,
        "missingScopes": result.missingScopes,
        "missingPermissions": result.missingPermissions,
        "accountType": result.accountType,
        "displayName": result.displayName,
        "username": result.username,
        "platformAccountId": result.platformAccountId,
        "warnings": result.warnings,
        "errors": result.errors,
        "retryable": result.retryable,
        "rawProviderResponseRedacted": result.rawProviderResponseRedacted,
    }


def _redacted_response_text(response: PlatformHttpResponse) -> str:
    payload = response.json if response.json is not None else response.text
    if isinstance(payload, str):
        return redact_raw_text(payload)
    return json.dumps(redact_http_value(payload).value, sort_keys=True)


def _first_text(source: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _utc_timestamp(value: str | datetime | None) -> str:
    if value is None:
        parsed = datetime.now(timezone.utc)
    elif isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00",
        "Z",
    )
