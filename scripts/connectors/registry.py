from __future__ import annotations

from scripts.connectors.base import SocialConnector
from scripts.connectors.linkedin import LinkedInConnector
from scripts.connectors.meta import FacebookConnector, InstagramConnector, ThreadsConnector
from scripts.connectors.tiktok import TikTokConnector
from scripts.connectors.youtube import YouTubeConnector
from scripts.connectors.x import XConnector
from scripts.connectors.types import (
    ConnectorCapabilities,
    PlatformConnectorMetadata,
    PlatformFeatureStatus,
    PlatformPermissionScope,
    SocialPlatform,
)


SUPPORTED_SOCIAL_PLATFORMS = tuple(platform.value for platform in SocialPlatform)


class ConnectorRegistryError(ValueError):
    pass


def get_connector(platform: str) -> SocialConnector:
    normalized = _normalize_platform(platform)
    try:
        return _CONNECTORS[normalized]
    except KeyError as error:
        raise ConnectorRegistryError(
            f"Unsupported social platform {platform!r}. Supported platforms: "
            + ", ".join(SUPPORTED_SOCIAL_PLATFORMS)
        ) from error


def list_connectors() -> tuple[SocialConnector, ...]:
    return tuple(_CONNECTORS[platform] for platform in SUPPORTED_SOCIAL_PLATFORMS)


def list_connector_metadata() -> tuple[PlatformConnectorMetadata, ...]:
    return tuple(_metadata_for_connector(connector) for connector in list_connectors())


def list_platform_capabilities() -> dict[str, dict[str, bool]]:
    return {
        connector.getPlatform(): connector.getCapabilities().to_dict()
        for connector in list_connectors()
    }


def list_platform_setup_status() -> dict[str, str]:
    return {
        connector.getPlatform(): connector.featureStatus.value
        for connector in list_connectors()
    }


def list_mock_only_platforms() -> tuple[str, ...]:
    return tuple(
        connector.getPlatform()
        for connector in list_connectors()
        if connector.featureStatus == PlatformFeatureStatus.MOCK_ONLY
    )


def list_not_configured_platforms() -> tuple[str, ...]:
    return tuple(
        metadata.platform for metadata in list_connector_metadata() if not metadata.configured
    )


def _metadata_for_connector(connector: SocialConnector) -> PlatformConnectorMetadata:
    setup = connector.getSetupInstructions()
    return PlatformConnectorMetadata(
        platform=connector.getPlatform(),
        label=connector.label,
        featureStatus=connector.featureStatus,
        capabilities=connector.getCapabilities(),
        setupSummary=setup[0] if setup else "Setup instructions are not available yet.",
        configured=connector.featureStatus
        in {
            PlatformFeatureStatus.MOCK_ONLY,
            PlatformFeatureStatus.READY_FOR_TESTING,
            PlatformFeatureStatus.ENABLED,
        },
    )


def _normalize_platform(platform: str) -> str:
    return platform.strip().lower()


def _scaffolded_connector(platform: str, label: str) -> SocialConnector:
    return SocialConnector(
        platform=platform,
        label=label,
        featureStatus=PlatformFeatureStatus.SCAFFOLDED,
        capabilities=ConnectorCapabilities(
            canConnect=False,
            supportsOAuth=True,
            supportsManualExportFallback=True,
            requiresAppReview=True,
        ),
        requiredScopes=(),
        setupInstructions=(
            f"{label} connector metadata is scaffolded. Credentials, OAuth, "
            "profile reads, analytics, replies, and publishing are not implemented.",
            "Use manual export while this platform remains scaffolded.",
        ),
    )


_CONNECTORS: dict[str, SocialConnector] = {
    "facebook": FacebookConnector(),
    "instagram": InstagramConnector(),
    "threads": ThreadsConnector(),
    "youtube": YouTubeConnector(),
    "tiktok": TikTokConnector(),
    "linkedin": LinkedInConnector(),
    "x": XConnector(),
}
