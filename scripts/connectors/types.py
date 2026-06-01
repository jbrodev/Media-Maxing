from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class SocialPlatform(StrEnum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"
    X = "x"


class PlatformFeatureStatus(StrEnum):
    UNAVAILABLE = "unavailable"
    PLANNED = "planned"
    SCAFFOLDED = "scaffolded"
    MOCK_ONLY = "mock_only"
    REQUIRES_CREDENTIALS = "requires_credentials"
    REQUIRES_APP_REVIEW = "requires_app_review"
    READY_FOR_TESTING = "ready_for_testing"
    ENABLED = "enabled"


@dataclass(frozen=True)
class PlatformPermissionScope:
    id: str
    label: str
    description: str
    required: bool = True
    status: PlatformFeatureStatus = PlatformFeatureStatus.SCAFFOLDED


@dataclass(frozen=True)
class ConnectorCapabilities:
    canConnect: bool = False
    canRefreshToken: bool = False
    canPublishText: bool = False
    canPublishImage: bool = False
    canPublishVideo: bool = False
    canPublishCarousel: bool = False
    canReadComments: bool = False
    canReplyToComments: bool = False
    canReadAnalytics: bool = False
    canReadProfile: bool = False
    canScheduleNatively: bool = False
    requiresBusinessAccount: bool = False
    requiresAppReview: bool = False
    supportsOAuth: bool = False
    supportsManualExportFallback: bool = True

    def to_dict(self) -> dict[str, bool]:
        return {
            "canConnect": self.canConnect,
            "canRefreshToken": self.canRefreshToken,
            "canPublishText": self.canPublishText,
            "canPublishImage": self.canPublishImage,
            "canPublishVideo": self.canPublishVideo,
            "canPublishCarousel": self.canPublishCarousel,
            "canReadComments": self.canReadComments,
            "canReplyToComments": self.canReplyToComments,
            "canReadAnalytics": self.canReadAnalytics,
            "canReadProfile": self.canReadProfile,
            "canScheduleNatively": self.canScheduleNatively,
            "requiresBusinessAccount": self.requiresBusinessAccount,
            "requiresAppReview": self.requiresAppReview,
            "supportsOAuth": self.supportsOAuth,
            "supportsManualExportFallback": self.supportsManualExportFallback,
        }


@dataclass(frozen=True)
class OAuthConfig:
    platform: str
    authorizationUrl: str | None = None
    tokenUrl: str | None = None
    redirectUri: str | None = None
    clientIdConfigured: bool = False
    scopes: tuple[PlatformPermissionScope, ...] = ()
    status: PlatformFeatureStatus = PlatformFeatureStatus.SCAFFOLDED
    notes: str = ""


@dataclass(frozen=True)
class OAuthStartRequest:
    platform: str
    redirectUri: str | None = None
    requestedScopes: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OAuthStartResult:
    success: bool
    authorizationUrl: str | None = None
    stateId: str | None = None
    status: str = "not_started"
    message: str = ""


@dataclass(frozen=True)
class OAuthCallbackRequest:
    platform: str
    code: str | None = None
    state: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OAuthCallbackResult:
    success: bool
    accountProfile: "ConnectedAccountProfile | None" = None
    status: str = "not_completed"
    message: str = ""


@dataclass(frozen=True)
class ConnectedAccountProfile:
    platform: str
    providerAccountId: str
    displayName: str
    handle: str | None = None
    accountType: str | None = None
    profileUrl: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TokenSet:
    platform: str
    accessToken: str | None = None
    refreshToken: str | None = None
    expiresAt: str | None = None
    scopes: tuple[str, ...] = ()
    tokenType: str | None = None


@dataclass(frozen=True)
class TokenRefreshResult:
    success: bool
    tokenSet: TokenSet | None = None
    status: str = "not_refreshed"
    message: str = ""


@dataclass(frozen=True)
class ConnectorHealthResult:
    platform: str
    status: str
    featureStatus: PlatformFeatureStatus = PlatformFeatureStatus.SCAFFOLDED
    socialAccountId: str | None = None
    canUseRealNetwork: bool = False
    message: str = ""
    checkedAt: str | None = None
    connectionStatus: str = "not_connected"
    requiresReauth: bool = False
    missingScopes: list[str] = field(default_factory=list)
    missingPermissions: list[str] = field(default_factory=list)
    accountType: str = "unknown"
    displayName: str | None = None
    username: str | None = None
    platformAccountId: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    retryable: bool = False
    rawProviderResponseRedacted: str | None = None


@dataclass(frozen=True)
class ConnectorActionResult:
    success: bool
    status: str
    message: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConnectorError:
    code: str
    message: str
    platform: str | None = None
    retryable: bool = False
    safeMetadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlatformConnectorMetadata:
    platform: str
    label: str
    featureStatus: PlatformFeatureStatus
    capabilities: ConnectorCapabilities
    setupSummary: str
    configured: bool = False
