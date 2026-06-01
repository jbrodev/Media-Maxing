from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any, Callable

from scripts.services.integration_flags import NetworkSafetyMode, resolve_network_safety_mode


class PlatformHttpMethod(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


@dataclass(frozen=True)
class ProviderErrorNormalized:
    provider: str
    platform: str
    status: int | None
    code: str
    message: str
    userSafeMessage: str
    retryable: bool = False
    requiresReauth: bool = False
    rateLimited: bool = False
    missingPermission: bool = False
    rawRedacted: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "platform": self.platform,
            "status": self.status,
            "code": self.code,
            "message": self.message,
            "userSafeMessage": self.userSafeMessage,
            "retryable": self.retryable,
            "requiresReauth": self.requiresReauth,
            "rateLimited": self.rateLimited,
            "missingPermission": self.missingPermission,
            "rawRedacted": self.rawRedacted,
        }


@dataclass(frozen=True)
class PlatformHttpError:
    provider: str
    platform: str
    status: str
    message: str
    request: dict[str, Any] = field(default_factory=dict)
    providerError: ProviderErrorNormalized | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "platform": self.platform,
            "status": self.status,
            "message": self.message,
            "request": self.request,
            "providerError": self.providerError.to_dict() if self.providerError else None,
        }


@dataclass(frozen=True)
class PlatformHttpResponse:
    ok: bool
    status: int | None = None
    headers: dict[str, str] = field(default_factory=dict)
    text: str = ""
    json: Any = None
    error: PlatformHttpError | None = None
    mocked: bool = False

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "headers": redact_http_value(self.headers).value,
            "text": redact_raw_text(self.text),
            "json": redact_http_value(self.json).value,
            "error": self.error.to_dict() if self.error else None,
            "mocked": self.mocked,
        }


@dataclass(frozen=True)
class PlatformHttpRequest:
    method: PlatformHttpMethod | str
    url: str
    query: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    jsonBody: Any = None
    formBody: dict[str, Any] | None = None
    timeoutSeconds: float | None = None
    mockResponse: PlatformHttpResponse | None = None


PlatformHttpTransport = Callable[[PlatformHttpRequest, float], PlatformHttpResponse]


@dataclass(frozen=True)
class PlatformHttpClientConfig:
    provider: str
    platform: str
    safetyMode: NetworkSafetyMode | str | None = None
    timeoutSeconds: float = 15.0
    allowNetwork: bool = False
    mockResponses: dict[str, PlatformHttpResponse] = field(default_factory=dict)
    transport: PlatformHttpTransport | None = None


@dataclass(frozen=True)
class HttpRedactionResult:
    value: Any
    redacted: bool
    redactedFields: tuple[str, ...] = ()


SENSITIVE_FIELD_MARKERS = (
    "access_token",
    "refresh_token",
    "client_secret",
    "authorization",
    "bearer",
    "code",
    "id_token",
    "appsecret_proof",
    "signed_request",
    "set-cookie",
)
LONG_PROVIDER_TOKEN = re.compile(r"^[A-Za-z0-9._~+/=-]{24,}$")
BEARER_TEXT = re.compile(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]{12,}")
KEY_VALUE_SECRET = re.compile(
    r"(?i)(access_token|refresh_token|client_secret|authorization|code|id_token|appsecret_proof|signed_request)"
    r"([\"'\s:=]+)([^,\"'\s&}]+)"
)


class PlatformHttpClient:
    """Server-side HTTP boundary for future provider API calls.

    The client is intentionally conservative. Tests and local development do
    not make external calls unless flags and connector code explicitly opt in.
    """

    def __init__(self, config: PlatformHttpClientConfig):
        safety_mode = _safety_mode_from_value(config.safetyMode)
        if safety_mode is None:
            safety_mode = resolve_network_safety_mode(
                env=dict(os.environ),
                connector_allows_network=config.allowNetwork,
            )
        if os.environ.get("APP_ENV") == "test" and os.environ.get("ALLOW_NETWORK_IN_TESTS", "").lower() not in {"1", "true", "yes", "on"}:
            safety_mode = NetworkSafetyMode.DISABLED
        self.config = replace(config, safetyMode=safety_mode)

    def get(self, url: str, **kwargs: Any) -> PlatformHttpResponse:
        return self.request(PlatformHttpRequest(method=PlatformHttpMethod.GET, url=url, **kwargs))

    def post(self, url: str, **kwargs: Any) -> PlatformHttpResponse:
        return self.request(PlatformHttpRequest(method=PlatformHttpMethod.POST, url=url, **kwargs))

    def put(self, url: str, **kwargs: Any) -> PlatformHttpResponse:
        return self.request(PlatformHttpRequest(method=PlatformHttpMethod.PUT, url=url, **kwargs))

    def patch(self, url: str, **kwargs: Any) -> PlatformHttpResponse:
        return self.request(PlatformHttpRequest(method=PlatformHttpMethod.PATCH, url=url, **kwargs))

    def delete(self, url: str, **kwargs: Any) -> PlatformHttpResponse:
        return self.request(PlatformHttpRequest(method=PlatformHttpMethod.DELETE, url=url, **kwargs))

    def request(self, request: PlatformHttpRequest) -> PlatformHttpResponse:
        invalid = _validate_url(request.url)
        if invalid:
            return self._safe_error("invalid_url", invalid, request)

        safety_mode = _safety_mode_from_value(self.config.safetyMode) or NetworkSafetyMode.MOCK
        if safety_mode == NetworkSafetyMode.DISABLED:
            return self._safe_error(
                "network_disabled",
                "External platform network calls are disabled by safety policy.",
                request,
            )
        if safety_mode == NetworkSafetyMode.MOCK:
            mock = request.mockResponse or self.config.mockResponses.get(_mock_key(request))
            if mock is None:
                mock = PlatformHttpResponse(
                    ok=True,
                    status=200,
                    json={
                        "mock": True,
                        "provider": self.config.provider,
                        "platform": self.config.platform,
                    },
                )
            return replace(mock, mocked=True)
        if not self.config.allowNetwork and self.config.transport is None:
            return self._safe_error(
                "network_not_allowed",
                "Network mode was enabled without connector-level allowNetwork approval.",
                request,
            )

        timeout = request.timeoutSeconds or self.config.timeoutSeconds
        try:
            if self.config.transport is not None:
                return self.config.transport(request, timeout)
            return self._urllib_request(request, timeout)
        except urllib.error.HTTPError as error:
            text = _decode_bytes(error.read())
            payload = safe_json_parse(text)
            provider_error = normalize_provider_error(
                provider=self.config.provider,
                platform=self.config.platform,
                status=error.code,
                payload=payload,
                raw_text=text,
            )
            return PlatformHttpResponse(
                ok=False,
                status=error.code,
                text=redact_raw_text(text),
                json=redact_http_value(payload).value,
                error=PlatformHttpError(
                    provider=self.config.provider,
                    platform=self.config.platform,
                    status="provider_error",
                    message=provider_error.userSafeMessage,
                    request=_safe_request_summary(request),
                    providerError=provider_error,
                ),
            )
        except Exception as error:
            return self._safe_error("network_error", str(error), request)

    def _urllib_request(
        self,
        request: PlatformHttpRequest,
        timeout: float,
    ) -> PlatformHttpResponse:
        url = _url_with_query(request.url, request.query)
        headers = dict(request.headers)
        data: bytes | None = None
        if request.formBody is not None:
            data = urllib.parse.urlencode(request.formBody).encode("utf-8")
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        elif request.jsonBody is not None:
            data = json.dumps(request.jsonBody).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        raw_request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=str(request.method).upper(),
        )
        with urllib.request.urlopen(raw_request, timeout=timeout) as response:
            text = _decode_bytes(response.read())
            payload = safe_json_parse(text)
            return PlatformHttpResponse(
                ok=200 <= int(response.status) < 300,
                status=int(response.status),
                headers=dict(response.headers.items()),
                text=text,
                json=payload,
            )

    def _safe_error(
        self,
        status: str,
        message: str,
        request: PlatformHttpRequest,
    ) -> PlatformHttpResponse:
        return PlatformHttpResponse(
            ok=False,
            status=None,
            error=PlatformHttpError(
                provider=self.config.provider,
                platform=self.config.platform,
                status=status,
                message=redact_raw_text(message),
                request=_safe_request_summary(request),
            ),
        )


def normalize_provider_error(
    *,
    provider: str,
    platform: str,
    status: int | None,
    payload: Any,
    raw_text: str,
) -> ProviderErrorNormalized:
    payload_dict = payload if isinstance(payload, dict) else {}
    error_payload = payload_dict.get("error", payload_dict)
    if not isinstance(error_payload, dict):
        error_payload = {}
    code = str(
        error_payload.get("code")
        or error_payload.get("error")
        or error_payload.get("type")
        or status
        or "unknown"
    )
    message = str(
        error_payload.get("message")
        or error_payload.get("detail")
        or payload_dict.get("message")
        or "Provider request failed."
    )
    lowered = message.lower()
    requires_reauth = status in {401, 403} and (
        "oauth" in lowered or "token" in lowered or "auth" in lowered or code in {"190", "401"}
    )
    missing_permission = status == 403 or "permission" in lowered or "scope" in lowered
    rate_limited = status == 429 or "rate" in lowered and "limit" in lowered
    retryable = rate_limited or (status is not None and 500 <= status <= 599)
    return ProviderErrorNormalized(
        provider=provider,
        platform=platform,
        status=status,
        code=redact_raw_text(code),
        message=redact_raw_text(message),
        userSafeMessage=_user_safe_message(status, requires_reauth, rate_limited, missing_permission),
        retryable=retryable,
        requiresReauth=requires_reauth,
        rateLimited=rate_limited,
        missingPermission=missing_permission,
        rawRedacted=redact_raw_text(raw_text),
    )


def safe_json_parse(text: str) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def redact_http_value(value: Any) -> HttpRedactionResult:
    redacted_fields: list[str] = []
    redacted = _redact_value(value, redacted_fields, path="")
    return HttpRedactionResult(
        value=redacted,
        redacted=bool(redacted_fields),
        redactedFields=tuple(redacted_fields),
    )


def redact_raw_text(value: str) -> str:
    redacted = BEARER_TEXT.sub("Bearer [REDACTED]", str(value))
    redacted = KEY_VALUE_SECRET.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", redacted)
    for marker in (
        "access_token",
        "refresh_token",
        "client_secret",
        "id_token",
        "appsecret_proof",
        "signed_request",
    ):
        redacted = re.sub(re.escape(marker), "[REDACTED_FIELD]", redacted, flags=re.IGNORECASE)
    return redacted


def _redact_value(value: Any, redacted_fields: list[str], *, path: str) -> Any:
    if isinstance(value, dict):
        result: dict[Any, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if _is_sensitive_field(key_text, child):
                result[key] = "[REDACTED]"
                redacted_fields.append(child_path)
            else:
                result[key] = _redact_value(child, redacted_fields, path=child_path)
        return result
    if isinstance(value, list):
        return [
            _redact_value(child, redacted_fields, path=f"{path}[{index}]")
            for index, child in enumerate(value)
        ]
    if isinstance(value, str):
        redacted_text = redact_raw_text(value)
        if redacted_text != value:
            redacted_fields.append(path or "<value>")
        return redacted_text
    return value


def _is_sensitive_field(key: str, value: Any) -> bool:
    normalized = key.replace("-", "_").lower()
    if any(marker in normalized for marker in SENSITIVE_FIELD_MARKERS):
        return True
    return isinstance(value, str) and normalized in {"token", "secret"} and LONG_PROVIDER_TOKEN.match(value)


def _safe_request_summary(request: PlatformHttpRequest) -> dict[str, Any]:
    return {
        "method": str(request.method).upper(),
        "url": _redact_url(request.url),
        "query": redact_http_value(request.query).value,
        "headers": redact_http_value(request.headers).value,
        "formBody": redact_http_value(request.formBody).value,
        "jsonBody": redact_http_value(request.jsonBody).value,
    }


def _url_with_query(url: str, query: dict[str, Any]) -> str:
    if not query:
        return url
    parsed = urllib.parse.urlparse(url)
    existing = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
    existing.update({key: str(value) for key, value in query.items()})
    return urllib.parse.urlunparse(
        parsed._replace(query=urllib.parse.urlencode(existing))
    )


def _redact_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    redacted_query = urllib.parse.urlencode(
        [
            (key, "[REDACTED]" if _is_sensitive_field(key, value) else value)
            for key, value in query_pairs
        ]
    )
    return urllib.parse.urlunparse(parsed._replace(query=redacted_query))


def _validate_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "Provider URL must be an absolute http or https URL."
    return None


def _mock_key(request: PlatformHttpRequest) -> str:
    return f"{str(request.method).upper()} {_url_with_query(request.url, request.query)}"


def _safety_mode_from_value(value: NetworkSafetyMode | str | None) -> NetworkSafetyMode | None:
    if value is None:
        return None
    return value if isinstance(value, NetworkSafetyMode) else NetworkSafetyMode(str(value))


def _decode_bytes(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _user_safe_message(
    status: int | None,
    requires_reauth: bool,
    rate_limited: bool,
    missing_permission: bool,
) -> str:
    if requires_reauth:
        return "The platform connection needs reauthorization. No secret values were shown."
    if rate_limited:
        return "The platform rate limited the request. Try again later."
    if missing_permission:
        return "The platform connection is missing a required permission or scope."
    if status:
        return f"The platform returned HTTP {status}. Details were redacted for safety."
    return "The platform request failed. Details were redacted for safety."
