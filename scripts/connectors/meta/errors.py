from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


TOKENISH_PATTERNS = [
    re.compile(r"(?i)(access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|authorization[_ -]?code)[:= ]+[^,\s\"'}]+"),
    re.compile(r"(?i)secret-token-value"),
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]+"),
]


@dataclass(frozen=True)
class MetaConnectorError:
    code: str
    message: str
    userSafeMessage: str
    retryable: bool = False
    requiresReauth: bool = False
    missingConfig: bool = False
    rawErrorRedacted: str = ""


def normalize_meta_error(platform: str, raw_error: Any) -> MetaConnectorError:
    raw_text = _safe_json(raw_error)
    redacted = redact_meta_error(raw_text)
    error_payload = raw_error.get("error", raw_error) if isinstance(raw_error, dict) else {}
    meta_code = str(error_payload.get("code") or error_payload.get("error_subcode") or "unknown")
    message = str(error_payload.get("message") or "Meta connector action failed.")
    requires_reauth = meta_code in {"190", "102"} or "oauth" in message.lower()

    return MetaConnectorError(
        code=f"meta_{meta_code}",
        message=redact_meta_error(message),
        userSafeMessage=(
            f"{platform.title()} connection needs attention. "
            "No secret values were stored or displayed."
        ),
        retryable=meta_code in {"1", "2", "4", "17", "613"},
        requiresReauth=requires_reauth,
        missingConfig=False,
        rawErrorRedacted=redacted,
    )


def missing_meta_config_error(platform: str, missing_keys: tuple[str, ...]) -> MetaConnectorError:
    return MetaConnectorError(
        code="meta_setup_required",
        message=f"Missing required Meta configuration: {', '.join(missing_keys)}.",
        userSafeMessage=(
            f"{platform.title()} needs Meta app configuration before real OAuth can start."
        ),
        retryable=False,
        requiresReauth=False,
        missingConfig=True,
        rawErrorRedacted=json.dumps({"missingConfigKeys": list(missing_keys)}),
    )


def redact_meta_error(value: str) -> str:
    redacted = value
    for pattern in TOKENISH_PATTERNS:
        redacted = pattern.sub(lambda match: _redacted_value(match.group(0)), redacted)
    return redacted


def _redacted_value(match: str) -> str:
    if ":" in match:
        return match.split(":", 1)[0] + ": [redacted]"
    if "=" in match:
        return match.split("=", 1)[0] + "=[redacted]"
    return "[redacted]"


def _safe_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True)
    except TypeError:
        return str(value)
