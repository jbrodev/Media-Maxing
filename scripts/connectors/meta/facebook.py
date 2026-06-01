from __future__ import annotations

from scripts.connectors.meta.base import MetaConnector
from scripts.connectors.types import (
    ConnectorCapabilities,
    PlatformFeatureStatus,
    PlatformPermissionScope,
)


class FacebookConnector(MetaConnector):
    def __init__(self) -> None:
        super().__init__(
            platform="facebook",
            label="Facebook",
            capabilities=ConnectorCapabilities(
                canConnect=True,
                canReadProfile=True,
                canPublishText=False,
                canPublishImage=False,
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
                    id="pages_show_list",
                    label="Pages list",
                    description="Placeholder scope for listing Facebook Pages the user can manage.",
                    status=PlatformFeatureStatus.SCAFFOLDED,
                ),
                PlatformPermissionScope(
                    id="pages_read_engagement",
                    label="Page engagement read",
                    description="Placeholder scope for future safe page profile and engagement checks.",
                    status=PlatformFeatureStatus.PLANNED,
                ),
            ),
            setup_instructions=(
                "Create or use a Meta developer app and configure Facebook Login for a local callback URL.",
                "Set META_CLIENT_ID, META_CLIENT_SECRET, META_REDIRECT_URI, and optionally META_GRAPH_API_VERSION in the local environment.",
                "Required redirect URI should match the server callback, for example http://localhost:8000/api/connect/facebook/callback.",
                "Required scopes are placeholders: pages_show_list and pages_read_engagement. Verify exact scopes against current Meta docs before real OAuth.",
                "Required account type: Facebook Page access for the business.",
                "App review warning: Meta may require app review before live Page permissions work.",
                "Local development note: mock OAuth works without credentials; real network calls are disabled by default.",
                "Safety note: Publishing is disabled in this batch, even if META_ENABLE_REAL_PUBLISHING=true.",
            ),
        )
