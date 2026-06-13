"""Deterministic mock provider.

MockProvider produces content from the brand profile, content goal,
content angle, and the requested platforms. The output is fully
deterministic: no randomness, no network, no clock reads. Tests can rely
on byte-for-byte stable output across runs.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from scripts.ai.providers.base import AIProvider
from scripts.ai.schemas import (
    AIStructuredGenerationRequest,
    AIStructuredGenerationResponse,
    AITextGenerationRequest,
    AITextGenerationResponse,
    CaptionVariant,
    ContentGenerationInput,
    ContentGenerationOptions,
    GeneratedContentBundle,
    GeneratedPostSafetyReview,
    PlatformPostDraft,
)

MOCK_MODEL_ID = "mock-deterministic-v1"


MOCK_PROMPT_ID_DEFAULT = "platform_post_generator_v1"
MOCK_PROMPT_VERSION = "v1"


_PLATFORM_OPENER = {
    "facebook": "Facebook draft from {business}",
    "instagram": "Instagram draft from {business}",
    "threads": "Threads draft from {business}",
    "youtube": "YouTube Shorts draft from {business}",
    "tiktok": "TikTok draft from {business}",
    "linkedin": "LinkedIn draft from {business}",
    "x": "X draft from {business}",
}

_ANGLE_NOTE = {
    "before_after": "Shows a clear before and after change without inventing customer results.",
    "educational": "Shares one practical tip that the business can support.",
    "behind_the_scenes": "Shows real preparation or process without naming any customer.",
    "testimonial": "Placeholder reference to a real quote. Do not invent testimonials.",
    "promotion": "Mentions an offer only if it is supported by the brand profile.",
    "faq": "Answers one common question in plain language.",
    "trust_builder": "Highlights one careful, supportable practice from the brand profile.",
    "transformation": "Shows a clear change while staying honest about scope.",
    "seasonal": "Connects the message to the current season without urgency hype.",
    "other": "A general draft aligned to brand voice.",
}

_GOAL_CTA = {
    "get_leads": "Ask the customer to message for an estimate.",
    "show_transformation": "Invite the customer to see more recent projects.",
    "educate_customer": "Invite the customer to ask a follow-up question.",
    "promote_offer": "Invite the customer to ask about current availability.",
    "build_trust": "Invite the customer to learn more about the team.",
    "announce_availability": "Invite the customer to ask about open dates.",
    "repurpose_old_content": "Invite the customer to revisit recent project notes.",
    "behind_the_scenes": "Invite the customer to see more process posts.",
    "seasonal_reminder": "Invite the customer to plan ahead for the season.",
}

_HOOK_PREFIX = {
    "facebook": "A practical local update",
    "instagram": "A quick visual story",
    "threads": "A short behind-the-scenes note",
    "youtube": "A Shorts-ready opener",
    "tiktok": "A fast visual hook",
    "linkedin": "A trust-building business note",
    "x": "A concise local-service thought",
}


def _slug(text: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text)
    parts = [part for part in cleaned.split() if part]
    return "".join(part[:1].upper() + part[1:].lower() for part in parts)


def _unique(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _build_hashtags(
    business_name: str,
    services: list[str],
    angle: str,
    count: int,
) -> list[str]:
    if count <= 0:
        return []
    candidates: list[str] = []
    business_tag = _slug(business_name)
    if business_tag:
        candidates.append(f"#{business_tag}")
    angle_tag = _slug(angle.replace("_", " "))
    if angle_tag:
        candidates.append(f"#{angle_tag}")
    candidates.append("#LocalBusiness")
    candidates.append("#LocalServiceBusiness")
    for service in services:
        service_tag = _slug(service)
        if service_tag:
            candidates.append(f"#{service_tag}")
    return _unique(candidates)[:count]


def _claim_line(supported_claims: list[str]) -> str:
    cleaned = [claim.strip() for claim in supported_claims if isinstance(claim, str) and claim.strip()]
    if not cleaned:
        return "No additional claims listed in the brand profile."
    return "Supported brand claim: " + cleaned[0]


def _voice_line(voice: str) -> str:
    voice = (voice or "").strip()
    if not voice:
        return "Voice: helpful, practical, and honest."
    return f"Voice: {voice}"


def _maybe_truncate(text: str, max_length: int | None) -> str:
    if max_length is None or max_length <= 0:
        return text
    if len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]
    return text[: max_length - 3].rstrip() + "..."


def _build_caption(
    platform: str,
    business_name: str,
    voice: str,
    services: list[str],
    supported_claims: list[str],
    audience: str,
    goal: str,
    angle: str,
    instructions: str | None,
    max_caption_length: int | None,
) -> str:
    opener_template = _PLATFORM_OPENER.get(platform, "Draft from {business}")
    service_phrase = ", ".join(services[:2]) if services else "the listed services"
    parts = [
        opener_template.format(business=business_name) + ".",
        f"Audience: {audience}.",
        f"Focus service(s): {service_phrase}.",
        _ANGLE_NOTE.get(angle, _ANGLE_NOTE["other"]),
        _claim_line(supported_claims),
        _voice_line(voice),
        _GOAL_CTA.get(goal, "Invite the customer to reply with a question."),
    ]
    if instructions and instructions.strip():
        parts.append(f"User note: {instructions.strip()}")
    parts.append("Mock draft. Not a real published post.")
    caption = " ".join(parts)
    return _maybe_truncate(caption, max_caption_length)


def _build_hook(platform: str, business_name: str, angle: str) -> str:
    prefix = _HOOK_PREFIX.get(platform, "A local-service post")
    readable_angle = angle.replace("_", " ")
    return f"{prefix} from {business_name}: {readable_angle}."


def _build_variant(label: str, caption: str, suffix: str, max_caption_length: int | None) -> CaptionVariant:
    text = _maybe_truncate(caption + " " + suffix, max_caption_length)
    return CaptionVariant(text=text, style=label)


def _build_short_caption(caption: str) -> str:
    if len(caption) > 110:
        return caption[:107].rstrip() + "..."
    return caption


def _build_long_caption(caption: str, angle: str) -> str:
    note = _ANGLE_NOTE.get(angle, _ANGLE_NOTE["other"])
    return f"{caption}\n\nMore detail: {note}"


def _build_alt_text(angle: str, media_ids: list[str]) -> str | None:
    if not media_ids:
        return None
    readable_angle = angle.replace("_", " ")
    return f"Image describing a recent {readable_angle} moment."


# Deterministic per-platform scheduling hints. No clock reads: an anchor
# date keeps preview output stable across runs and mirrors the browser
# fallback in apps/web/generate.js.
_SUGGESTED_DAY_OFFSET = {
    "instagram": 1,
    "facebook": 2,
    "threads": 1,
    "tiktok": 3,
    "youtube": 4,
    "linkedin": 5,
    "x": 1,
}
_SUGGESTED_HOUR = {
    "instagram": 16,
    "facebook": 13,
    "threads": 18,
    "tiktok": 19,
    "youtube": 11,
    "linkedin": 9,
    "x": 8,
}
_SUGGESTED_ANCHOR = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _suggested_post_time(platform: str, index: int) -> str:
    offset_days = _SUGGESTED_DAY_OFFSET.get(platform, 1) + index // 7
    hour = _SUGGESTED_HOUR.get(platform, 12)
    scheduled = (_SUGGESTED_ANCHOR + timedelta(days=offset_days)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return scheduled.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _collect_media_ids(media_assets: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for asset in media_assets:
        if not isinstance(asset, dict):
            continue
        media_id = asset.get("id")
        if isinstance(media_id, str) and media_id.strip():
            ids.append(media_id.strip())
    return ids


def _fingerprint(
    input: ContentGenerationInput,
    options: ContentGenerationOptions,
) -> str:
    payload = {
        "brand_profile_id": input.brand_profile_id(),
        "content_goal": input.content_goal,
        "content_angle": input.content_angle,
        "selected_platforms": list(input.selected_platforms),
        "media_asset_ids": _collect_media_ids(input.selected_media_assets),
        "user_instructions": input.user_instructions or "",
        "campaign_name": input.campaign_name or "",
        "target_audience": input.target_audience or "",
        "location_context": input.location_context or "",
        "offer_context": input.offer_context or "",
        "approval_required": input.approval_required,
        "prompt_id": options.prompt_id,
        "hashtag_count": options.hashtag_count if options.include_hashtags else 0,
        "include_emojis": options.include_emojis,
        "include_cta": options.include_cta,
        "tone": options.tone or "",
        "creativity_level": options.creativity_level,
        "number_of_variants": options.number_of_variants,
        "max_caption_length": options.max_caption_length,
        "require_safety_review": options.require_safety_review,
        "generate_platform_specific_versions": options.generate_platform_specific_versions,
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


class MockProvider(AIProvider):
    name = "mock"
    label = "Mock provider (deterministic, offline)"
    requires_network = False

    def generate_bundle(
        self,
        input: ContentGenerationInput,
        options: ContentGenerationOptions,
    ) -> GeneratedContentBundle:
        input.validate()
        options.validate()

        brand = input.brand_profile
        business_name = (brand.get("businessName") or "the business").strip() or "the business"
        voice = (brand.get("voice") or brand.get("brandVoice") or "").strip()
        services = [
            service.strip()
            for service in (brand.get("services") or [])
            if isinstance(service, str) and service.strip()
        ]
        supported_claims = [
            claim.strip()
            for claim in (brand.get("supportedClaims") or [])
            if isinstance(claim, str) and claim.strip()
        ]
        audience = (
            input.target_audience
            or brand.get("targetAudience")
            or "local customers"
        ).strip() or "local customers"
        media_ids = _collect_media_ids(input.selected_media_assets)

        drafts: list[PlatformPostDraft] = []
        for index, platform in enumerate(input.selected_platforms):
            caption = _build_caption(
                platform=platform,
                business_name=business_name,
                voice=voice,
                services=services,
                supported_claims=supported_claims,
                audience=audience,
                goal=input.content_goal,
                angle=input.content_angle,
                instructions=input.user_instructions,
                max_caption_length=options.max_caption_length,
            )
            variants: list[CaptionVariant] = []
            if options.number_of_variants > 0:
                variant_styles = ("short", "warm", "direct")
                for index in range(options.number_of_variants):
                    style = variant_styles[index % len(variant_styles)]
                    suffix = f"({style} variation #{index + 1})"
                    variants.append(
                        _build_variant(style, caption, suffix, options.max_caption_length)
                    )
            hashtags = (
                _build_hashtags(
                    business_name=business_name,
                    services=services,
                    angle=input.content_angle,
                    count=options.hashtag_count,
                )
                if options.include_hashtags
                else []
            )
            cta = (
                "Reply or send a message to ask about availability."
                if options.include_cta
                else None
            )
            drafts.append(
                PlatformPostDraft(
                    platform=platform,
                    hook=_build_hook(platform, business_name, input.content_angle),
                    headline=f"{business_name}: {input.content_angle.replace('_', ' ').title()}",
                    caption=caption,
                    short_caption=_build_short_caption(caption),
                    long_caption=_build_long_caption(caption, input.content_angle),
                    hashtags=hashtags,
                    media_asset_ids=list(media_ids),
                    caption_variants=variants,
                    call_to_action=cta,
                    content_goal=input.content_goal,
                    content_angle=input.content_angle,
                    target_audience=audience,
                    suggested_post_time=_suggested_post_time(platform, index),
                    alt_text=_build_alt_text(input.content_angle, list(media_ids)),
                    notes="Generated by MockProvider. Deterministic. Not a real post.",
                    status="needs_review",
                )
            )

        prompt_id = options.prompt_id or MOCK_PROMPT_ID_DEFAULT
        return GeneratedContentBundle(
            brand_profile_id=input.brand_profile_id(),
            posts=drafts,
            prompt_id=prompt_id,
            prompt_version=MOCK_PROMPT_VERSION,
            generation_provider="mock",
            prompt_metadata={
                "prompt_id": prompt_id,
                "prompt_version": MOCK_PROMPT_VERSION,
                "render_format": "structured-mock",
                "content_goal": input.content_goal,
                "content_angle": input.content_angle,
                "selected_platforms": list(input.selected_platforms),
            },
            provider_metadata={
                "deterministic": True,
                "mock": True,
                "input_fingerprint": _fingerprint(input, options),
                "provider_label": self.label,
                "model": MOCK_MODEL_ID,
            },
            safety_review=GeneratedPostSafetyReview(
                flags=[],
                blocking_flags=[],
                reviewer="local_rules",
                notes="Mock provider does not perform a safety review. Run safety checks separately.",
            ),
            content_idea_id=input.content_idea_id,
        )

    # ------------------------------------------------------------------
    # Generic primitives. These implement the same provider interface as
    # any future real adapter so callers can switch providers without
    # changing their request/response handling.
    # ------------------------------------------------------------------

    def generate_text(self, request: AITextGenerationRequest) -> AITextGenerationResponse:
        request.validate()
        first_line = next(
            (line.strip() for line in request.prompt.splitlines() if line.strip()),
            "",
        )
        excerpt = first_line[:120]
        system_line = f"System: {request.system.strip()}\n" if request.system else ""
        body = (
            f"[MOCK DRAFT]\n"
            f"{system_line}"
            f"Prompt excerpt: {excerpt}\n\n"
            "This is a deterministic mock response generated locally without any "
            "network call. It is intended for development and UI testing only. "
            "Replace this text by selecting a real provider in Settings once API "
            "keys are configured."
        )
        if request.max_tokens:
            body = _maybe_truncate(body, request.max_tokens * 4)
        return AITextGenerationResponse(
            text=body,
            provider="mock",
            model=MOCK_MODEL_ID,
            finish_reason="stop",
            usage={
                "prompt_chars": len(request.prompt),
                "completion_chars": len(body),
            },
            metadata={
                "deterministic": True,
                "mock": True,
                "fingerprint": _text_fingerprint(request),
                "provider_label": self.label,
            },
            is_mock=True,
        )

    def generate_structured(
        self,
        request: AIStructuredGenerationRequest,
    ) -> AIStructuredGenerationResponse:
        request.validate()
        data = _mock_structured_payload(request.schema_name, request.prompt, request.metadata)
        return AIStructuredGenerationResponse(
            data=data,
            schema_name=request.schema_name,
            provider="mock",
            model=MOCK_MODEL_ID,
            finish_reason="stop",
            usage={"prompt_chars": len(request.prompt)},
            metadata={
                "deterministic": True,
                "mock": True,
                "fingerprint": _structured_fingerprint(request),
                "provider_label": self.label,
            },
            is_mock=True,
        )


def _text_fingerprint(request: AITextGenerationRequest) -> str:
    payload = {
        "prompt": request.prompt,
        "system": request.system or "",
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "stop_sequences": list(request.stop_sequences),
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _structured_fingerprint(request: AIStructuredGenerationRequest) -> str:
    payload = {
        "prompt": request.prompt,
        "schema_name": request.schema_name,
        "schema_hint": request.schema_hint or {},
        "system": request.system or "",
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _mock_structured_payload(
    schema_name: str,
    prompt: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    excerpt = (prompt.strip().splitlines() or [""])[0][:120]
    metadata = metadata or {}
    base: dict[str, Any] = {
        "schema_name": schema_name,
        "summary": f"Mock structured response for schema {schema_name!r}.",
        "prompt_excerpt": excerpt,
        "is_demo": True,
    }
    if schema_name == "platform_post_draft":
        base["fields"] = {
            "platform": "instagram",
            "caption": "Mock caption for a local-service post. Not real content.",
            "hashtags": ["#Mock", "#Demo", "#LocalServiceBusiness"],
            "media_asset_ids": [],
        }
    elif schema_name == "hashtag_set":
        base["fields"] = {
            "platform": "instagram",
            "hashtags": ["#Mock", "#Demo", "#LocalServiceBusiness"],
        }
    elif schema_name == "safety_review":
        base["fields"] = {
            "flags": [],
            "blocking_flags": [],
            "reviewer": "local_rules",
            "notes": "Mock safety review. No real evaluation performed.",
        }
    elif schema_name == "reply_suggestion":
        base["fields"] = _mock_reply_suggestion_fields(metadata)
    else:
        base["fields"] = {
            "headline": "Mock headline",
            "body": "Mock body. Not real content.",
            "tags": ["mock", "demo"],
        }
    return base


def _mock_reply_suggestion_fields(metadata: dict[str, Any]) -> dict[str, Any]:
    intent = str(metadata.get("intent") or "general").strip().lower()
    tone = str(metadata.get("tone") or "helpful").strip() or "helpful"
    if intent == "spam":
        return {
            "suggestedReply": "",
            "tone": tone,
            "confidence": "high",
            "safetyFlags": [],
            "blockingFlags": [],
            "recommendedAction": "mark_spam",
            "needsHumanReview": True,
            "reasonSummary": "Spam should not receive an outward reply.",
        }
    if intent == "praise":
        reply = "Thank you for the kind words. We appreciate you taking the time to share them."
        action = "reply"
        reason = "Friendly thank-you draft for owner review."
    elif intent == "price_request":
        reply = (
            "Thanks for asking. Pricing depends on the project details. "
            "Please send us a message and we can help with an estimate."
        )
        action = "invite_to_message"
        reason = "Invites an estimate request without inventing a price."
    elif intent == "booking_request":
        reply = (
            "Thanks for reaching out. Please send us the project details and the best way "
            "to contact you so the team can follow up about next steps."
        )
        action = "ask_for_more_info"
        reason = "Requests next-step details without inventing availability."
    elif intent == "complaint":
        reply = (
            "Thank you for letting us know. We are sorry this was frustrating. "
            "Please send us a message so a person can review the details and follow up."
        )
        action = "escalate"
        reason = "Uses an empathetic acknowledgment and routes the complaint to a person."
    elif intent == "urgent":
        reply = (
            "Thanks for reaching out. Please send the key details and the best contact "
            "method so a person can review this promptly."
        )
        action = "escalate"
        reason = "Provides a concise next step while keeping a person in the loop."
    else:
        reply = "Thanks for reaching out. Please send us a message and we will be glad to help."
        action = "reply"
        reason = "Helpful general response for owner review."
    return {
        "suggestedReply": reply,
        "tone": tone,
        "confidence": "high",
        "safetyFlags": [],
        "blockingFlags": [],
        "recommendedAction": action,
        "needsHumanReview": True,
        "reasonSummary": reason,
    }
