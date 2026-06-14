"""Single source of truth for per-platform caption character limits.

These values are referenced by content generation (so over-limit captions are
never produced), by preflight validation (so any caption that slips through is
flagged), and by the queue auto-fix action (so a too-long caption can be
trimmed to fit). Keep this module dependency-free so any layer can import it.

TODO: Confirm exact platform API limits when real connectors are implemented.
These are practical MVP placeholders only.
"""

from __future__ import annotations

PLATFORM_CAPTION_LIMITS: dict[str, int] = {
    "instagram": 2200,
    "facebook": 63206,
    "threads": 500,
    "tiktok": 2200,
    "youtube": 5000,
    "linkedin": 3000,
    "x": 280,
}

DEFAULT_CAPTION_LIMIT = 2200


def caption_limit_for(platform: str) -> int:
    """Return the max caption length for a platform (safe default if unknown)."""
    return PLATFORM_CAPTION_LIMITS.get(platform, DEFAULT_CAPTION_LIMIT)


def trim_to_limit(text: str, limit: int) -> str:
    """Trim ``text`` so it fits within ``limit`` characters.

    Cuts on a word boundary when one is close to the limit and appends a
    single-character ellipsis. The returned string is always ``<= limit``.
    """
    if limit <= 0 or len(text) <= limit:
        return text
    ellipsis = "…"  # single-character ellipsis
    budget = max(0, limit - len(ellipsis))
    truncated = text[:budget]
    boundary = truncated.rfind(" ")
    if boundary > 0 and boundary >= budget - 30:
        truncated = truncated[:boundary]
    return (truncated.rstrip() + ellipsis)[:limit]
