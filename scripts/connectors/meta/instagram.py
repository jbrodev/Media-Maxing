from __future__ import annotations

from scripts.connectors.meta.base import MetaConnector
from scripts.connectors.types import (
    ConnectorCapabilities,
    PlatformFeatureStatus,
    PlatformPermissionScope,
)


class InstagramConnector(MetaConnector):
    def __init__(self) -> None:
        super().__init__(
            platform="instagram",
            label="Instagram",
            capabilities=ConnectorCapabilities(
                canConnect=True,
                canReadProfile=True,
                canPublishImage=False,
                canPublishVideo=False,
                canPublishCarousel=False,
                canReadComments=False,
                canReplyToComments=False,
                canReadAnalytics=False,
                requiresBusinessAccount=True,
                requiresAppReview=True,
                supportsOAuth=True,
                supportsManualExportFallback=True,
            ),
            required_scopes=(
                PlatformPermissionScope(
                    id="instagram_basic",
                    label="Instagram basic profile",
                    description="Placeholder scope for future Instagram Business/Creator profile checks.",
                    status=PlatformFeatureStatus.SCAFFOLDED,
                ),
                PlatformPermissionScope(
                    id="pages_show_list",
                    label="Linked Page list",
                    description="Placeholder scope for discovering linked Facebook Page context.",
                    status=PlatformFeatureStatus.PLANNED,
                ),
            ),
            setup_instructions=(
                "Create or use a Meta developer app with Instagram Business/Creator integration readiness.",
                "Set META_CLIENT_ID, META_CLIENT_SECRET, META_REDIRECT_URI, and optionally META_GRAPH_API_VERSION in the local environment.",
                "Required redirect URI should match the server callback, for example http://localhost:8000/api/connect/instagram/callback.",
                "Required scopes are placeholders: instagram_basic and pages_show_list. Verify exact scopes against current Meta docs before real OAuth.",
                "Required account type: Instagram Business or Creator account connected through Meta.",
                "App review warning: Meta may require app review before live Instagram permissions work.",
                "Local development note: mock OAuth works without credentials; real network calls are disabled by default.",
                "Safety note: Publishing is disabled in this batch, even if META_ENABLE_REAL_PUBLISHING=true.",
            ),
        )
