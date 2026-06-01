from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any

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
    TokenRefreshResult,
)


DISABLED_PUBLISHING_MESSAGE = (
    "Real publishing is disabled by policy. Use local manual export or mock "
    "publishing until a future explicit platform implementation enables this."
)


@dataclass(frozen=True)
class SocialConnector(ABC):
    platform: str
    label: str
    featureStatus: PlatformFeatureStatus
    capabilities: ConnectorCapabilities
    requiredScopes: tuple[PlatformPermissionScope, ...] = ()
    setupInstructions: tuple[str, ...] = ()

    def getPlatform(self) -> str:
        return self.platform

    def getCapabilities(self) -> ConnectorCapabilities:
        return self.capabilities

    def getOAuthConfig(self) -> OAuthConfig:
        return OAuthConfig(
            platform=self.platform,
            scopes=self.requiredScopes,
            status=self.featureStatus,
            notes="OAuth is scaffolded only. Real OAuth remains disabled by default.",
        )

    def buildAuthorizationUrl(self, request: OAuthStartRequest) -> OAuthStartResult:
        return OAuthStartResult(
            success=False,
            status="scaffolded",
            message=(
                f"{self.label} OAuth is scaffolded only and does not call real APIs."
            ),
        )

    def handleOAuthCallback(self, request: OAuthCallbackRequest) -> OAuthCallbackResult:
        return OAuthCallbackResult(
            success=False,
            status="scaffolded",
            message=(
                f"{self.label} OAuth callbacks are scaffolded only and do not exchange tokens."
            ),
        )

    def refreshToken(self, token_reference: str | None = None) -> TokenRefreshResult:
        return TokenRefreshResult(
            success=False,
            status="disabled_by_policy",
            message="Token refresh is disabled until secure token storage is implemented.",
        )

    def validateConnection(self, account_id: str | None = None, **kwargs: Any) -> ConnectorHealthResult:
        return ConnectorHealthResult(
            platform=self.platform,
            status="scaffolded",
            featureStatus=self.featureStatus,
            canUseRealNetwork=False,
            message="No real platform network check is performed in mock/demo mode.",
        )

    def disconnect(self, account_id: str | None = None) -> ConnectorActionResult:
        return ConnectorActionResult(
            success=True,
            status="local_only",
            message="Local disconnect scaffold completed; no external revoke call was made.",
        )

    def getAccountProfile(self, account_id: str | None = None, **kwargs: Any) -> ConnectedAccountProfile | None:
        return None

    def getRequiredScopes(self) -> tuple[PlatformPermissionScope, ...]:
        return self.requiredScopes

    def getSetupInstructions(self) -> tuple[str, ...]:
        return self.setupInstructions

    def publishText(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _disabled_publishing_result(self.platform)

    def publishImage(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _disabled_publishing_result(self.platform)

    def publishVideo(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _disabled_publishing_result(self.platform)

    def publishCarousel(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return _disabled_publishing_result(self.platform)

    def replyToComment(self, payload: dict[str, Any] | None = None) -> ConnectorActionResult:
        return ConnectorActionResult(
            success=False,
            status="disabled_by_policy",
            message="Real comment replies are disabled by policy and require human approval.",
            metadata={"platform": self.platform},
        )


def _disabled_publishing_result(platform: str) -> ConnectorActionResult:
    return ConnectorActionResult(
        success=False,
        status="disabled_by_policy",
        message=DISABLED_PUBLISHING_MESSAGE,
        metadata={"platform": platform, "realPublishingEnabled": False},
    )
