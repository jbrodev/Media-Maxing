"""Local deterministic safety review for generated content.

This module runs without any AI provider. It uses simple
string and regex checks against the caption to surface common
issues that owners should fix before approving a draft:

- Blocked phrases from the brand profile.
- Unsupported guarantees.
- Invented testimonials.
- Credentials (licensed/insured/certified/...) not in
  ``supportedClaims``.
- Aggressive or pressuring language.
- Phrases that claim the draft is already published.
- Phrases that attempt to bypass approval.
- Emergency pause state (informational, not blocking).

Returns a tuple of ``(flags, blocking_flags, suggested_fixes)`` so the
caller can attach them to a ``GeneratedPostSafetyReview`` or per-post
``safety_flags`` field. Flag names use the
:data:`scripts.ai.schemas.SAFETY_FLAG_VOCABULARY` constants.

These checks are intentionally conservative: false positives are
preferred to false negatives. Owners can review and dismiss flags in
the UI.
"""

from __future__ import annotations

import re
from typing import Any

_GUARANTEE_PATTERNS = (
    r"\bguarantee[sd]?\b",
    r"\b100\s*%\s*(?:satisfaction|guarantee|results)\b",
    r"\bwe (?:will|always) (?:deliver|fix|solve)\b",
    r"\bpromise(?:d)?\b",
)

_CREDENTIAL_KEYWORDS = (
    "licensed",
    "insured",
    "certified",
    "accredited",
    "bonded",
    "epa-certified",
    "iso-certified",
    "award-winning",
    "voted best",
)

_TESTIMONIAL_PHRASES = (
    "one customer said",
    "a client told",
    "as our customer said",
    "real customer review",
    "verified customer",
    "review:",
    "said,",
    "told us,",
    "as one happy",
    "a happy customer",
)

_AGGRESSIVE_PATTERNS = (
    r"\bact now\b",
    r"\bdon'?t (?:miss|wait)\b",
    r"\blast chance\b",
    r"\bhurry\b",
    r"\blimited time only\b",
    r"\bbefore it'?s too late\b",
    r"\byou must\b",
    r"!!!+",
)

_PUBLISHED_CLAIM_PHRASES = (
    "we posted",
    "we just shared",
    "now live on our",
    "as seen on our page",
    "we have already published",
    "we already posted",
)

_APPROVAL_BYPASS_PHRASES = (
    "auto-approved",
    "auto approved",
    "skip review",
    "no review needed",
    "approved automatically",
    "no approval required",
)


def _add_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _brand_blocked_phrases(brand_profile: dict[str, Any]) -> list[str]:
    raw = (
        brand_profile.get("blockedPhrases")
        or brand_profile.get("bannedWords")
        or brand_profile.get("blocked_phrases")
        or []
    )
    return [phrase for phrase in raw if isinstance(phrase, str) and phrase.strip()]


def _supported_claims_text(brand_profile: dict[str, Any]) -> str:
    claims = brand_profile.get("supportedClaims") or brand_profile.get("supported_claims") or []
    return " ".join(claim.lower() for claim in claims if isinstance(claim, str))


def run_safety_checks(
    caption: str,
    brand_profile: dict[str, Any],
    *,
    emergency_pause_enabled: bool = False,
) -> tuple[list[str], list[str], list[str]]:
    """Run deterministic safety checks on a caption.

    Returns ``(flags, blocking_flags, suggested_fixes)``. ``blocking_flags``
    is always a subset of ``flags``.
    """
    if not isinstance(caption, str):
        raise TypeError("caption must be a string.")
    if not isinstance(brand_profile, dict):
        raise TypeError("brand_profile must be a dict.")

    flags: list[str] = []
    blocking: list[str] = []
    fixes: list[str] = []

    lower = caption.lower()

    # 1. Brand profile blocked phrases.
    for phrase in _brand_blocked_phrases(brand_profile):
        if phrase.lower() in lower:
            _add_unique(flags, "brand_mismatch")
            _add_unique(blocking, "brand_mismatch")
            fixes.append(f"Remove blocked phrase: {phrase!r}")

    # 2. Guarantees.
    for pattern in _GUARANTEE_PATTERNS:
        if re.search(pattern, lower):
            _add_unique(flags, "unsupported_guarantee")
            _add_unique(blocking, "unsupported_guarantee")
            fixes.append("Remove the guarantee or soften it to what the brand can actually support.")
            break

    # 3. Invented testimonials.
    for phrase in _TESTIMONIAL_PHRASES:
        if phrase in lower:
            _add_unique(flags, "fake_testimonial")
            _add_unique(blocking, "fake_testimonial")
            fixes.append(
                "Remove the testimonial. Only use customer quotes the owner has explicitly confirmed."
            )
            break

    # 4. Credentials not in supported claims.
    supported_text = _supported_claims_text(brand_profile)
    for word in _CREDENTIAL_KEYWORDS:
        if word in lower and word not in supported_text:
            _add_unique(flags, "unsupported_claim")
            _add_unique(blocking, "unsupported_claim")
            fixes.append(
                f"Remove '{word}' or add it to supportedClaims in the brand profile first."
            )
            break

    # 5. Aggressive or pressuring language.
    for pattern in _AGGRESSIVE_PATTERNS:
        if re.search(pattern, lower):
            _add_unique(flags, "aggressive_language")
            fixes.append("Soften the call-to-action. Avoid pressure language.")
            break

    # 6. "Already posted" / "live on our page" type claims.
    for phrase in _PUBLISHED_CLAIM_PHRASES:
        if phrase in lower:
            _add_unique(flags, "platform_policy_risk")
            _add_unique(blocking, "platform_policy_risk")
            fixes.append(
                "This is a draft, not a published post. Remove published-claim language."
            )
            break

    # 7. Explicit approval bypass attempts.
    for phrase in _APPROVAL_BYPASS_PHRASES:
        if phrase in lower:
            _add_unique(flags, "missing_approval")
            _add_unique(blocking, "missing_approval")
            fixes.append("Approval bypass attempted. Drafts must go through owner approval.")
            break

    # 8. Emergency pause status — informational, not blocking.
    # AGENTS.md says emergency pause must block scheduling/publishing,
    # not draft generation, but the bundle should record the conflict so
    # downstream UI can surface it.
    if emergency_pause_enabled:
        _add_unique(flags, "emergency_pause_conflict")
        fixes.append(
            "Emergency pause is enabled. Scheduling and publishing remain blocked downstream."
        )

    return flags, blocking, fixes
