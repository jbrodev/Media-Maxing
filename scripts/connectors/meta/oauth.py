from __future__ import annotations

from urllib.parse import urlencode

from scripts.connectors.meta.config import MetaConfig
from scripts.services.platform_http_client import PlatformHttpMethod, PlatformHttpRequest


MOCK_META_AUTH_BASE_URL = "http://localhost/mock-oauth/meta"
SUPPORTED_META_OAUTH_PLATFORMS = ("facebook", "instagram", "threads")


def build_mock_meta_authorization_url(
    *,
    platform: str,
    redirect_uri: str,
    state: str,
    scopes: tuple[str, ...],
) -> str:
    query = urlencode(
        {
            "platform": platform,
            "response_type": "code",
            "client_id": f"mock-meta-{platform}-client",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "state": state,
            "mock": "true",
        }
    )
    return f"{MOCK_META_AUTH_BASE_URL}/{platform}/authorize?{query}"


def build_real_meta_authorization_url(
    *,
    config: MetaConfig,
    redirect_uri: str,
    state: str,
    scopes: tuple[str, ...],
) -> str:
    # TODO: Verify exact Meta OAuth endpoint and scope behavior against current
    # official docs before enabling real OAuth. This builder is inert unless
    # real OAuth is explicitly configured and requested.
    query = urlencode(
        {
            "client_id": config.clientId or "",
            "redirect_uri": redirect_uri,
            "state": state,
            "response_type": "code",
            "scope": ",".join(scopes),
        }
    )
    return f"https://www.facebook.com/{config.graphApiVersion}/dialog/oauth?{query}"


def build_meta_token_exchange_request(
    *,
    config: MetaConfig,
    code: str,
    redirect_uri: str,
) -> PlatformHttpRequest:
    # TODO: Verify Meta's current token exchange endpoint, parameters, and
    # short-lived/long-lived token behavior against official docs before
    # allowing real operator use. This request is only sent by guarded
    # server-side code when all real OAuth safety flags are enabled.
    return PlatformHttpRequest(
        method=PlatformHttpMethod.POST,
        url=f"https://graph.facebook.com/{config.graphApiVersion}/oauth/access_token",
        formBody={
            "client_id": config.clientId or "",
            "client_secret": config.clientSecret or "",
            "redirect_uri": redirect_uri,
            "code": code,
            "grant_type": "authorization_code",
        },
    )


def build_meta_profile_request(*, config: MetaConfig, platform: str) -> PlatformHttpRequest:
    # TODO: Verify exact profile/account discovery endpoints per Meta product
    # before real discovery is enabled for operators. Tests use mocked
    # responses and no real API call is made by default.
    fields_by_platform = {
        "facebook": "id,name,username",
        "instagram": "id,name,username,account_type",
        "threads": "id,name,username",
    }
    return PlatformHttpRequest(
        method=PlatformHttpMethod.GET,
        url=f"https://graph.facebook.com/{config.graphApiVersion}/me",
        query={"fields": fields_by_platform.get(platform, "id,name")},
    )
