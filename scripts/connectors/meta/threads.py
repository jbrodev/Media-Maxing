from __future__ import annotations

from scripts.connectors.meta.base import MetaConnector
from scripts.connectors.types import (
    ConnectorCapabilities,
    PlatformFeatureStatus,
    PlatformPermissionScope,
)


class ThreadsConnector(MetaConnector):
    def __init__(self) -> None:
        super().__init__(
            platform="threads",
            label="Threads",
            capabilities=ConnectorCapabilities(
                canConnect=True,
                canReadProfile=True,
                canPublishText=False,
                canPublishImage=False,
                canPublishVideo=False,
                canPublishCarousel=False,
                canReadComments=False,
                canReplyToComments=False,
                canReadAnalytics=False,
                requiresBusinessAccount=False,
                requiresAppReview=True,
                supportsOAuth=True,
                supportsManualExportFallback=True,
            ),
            required_scopes=(
                PlatformPermissionScope(
                    id="threads_basic",
                    label="Threads basic profile",
                    description="Placeholder scope for future Threads profile checks.",
                    status=PlatformFeatureStatus.SCAFFOLDED,
                ),
            ),
            setup_instructions=(
                "Create or use a Meta developer app with Threads integration readiness when available for the app.",
                "Set META_CLIENT_ID, META_CLIENT_SECRET, META_REDIRECT_URI, and optionally META_GRAPH_API_VERSION in the local environment.",
                "Required redirect URI should match the server callback, for example http://localhost:8000/api/connect/threads/callback.",
                "Required scopes are placeholders: threads_basic. Verify exact scopes against current Meta docs before real OAuth.",
                "Required account type: Threads profile with supported business setup when required by Meta.",
                "App review warning: Meta may require app review before live Threads permissions work.",
                "Local development note: mock OAuth works without credentials; real network calls are disabled by default.",
                "Safety note: Publishing is disabled in this batch, even if META_ENABLE_REAL_PUBLISHING=true.",
            ),
        )
