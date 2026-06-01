"""Content generation orchestration.

The :class:`ContentGenerationService` wires:

1. :class:`scripts.ai.schemas.ContentGenerationInput` validation.
2. Optional brand-profile / media-asset / settings loaders.
3. Prompt rendering via :mod:`scripts.ai.prompts`.
4. Provider lookup via :mod:`scripts.ai.providers.registry` (mock by default).
5. Bundle schema validation (handled by the dataclasses).
6. Local deterministic safety review via :mod:`scripts.ai.safety`.

The service does not persist drafts. It does not call any network. It
does not depend on UI components. It is safe to call repeatedly from
tests or a future API route.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from scripts.ai.prompts import PromptRegistryError, get_prompt
from scripts.ai.providers.base import AIProvider, AIProviderError
from scripts.ai.providers.registry import get_provider
from scripts.ai.safety import run_safety_checks
from scripts.ai.schemas import (
    ContentGenerationInput,
    ContentGenerationOptions,
    GeneratedContentBundle,
    GeneratedPostSafetyReview,
    SchemaValidationError,
)


class ContentGenerationError(RuntimeError):
    """Raised when the service cannot produce a bundle (loader miss, etc.)."""


@dataclass
class SettingsSnapshot:
    """Minimal app-settings-shaped object the service consumes.

    Real callers can build this from
    :class:`scripts.db.settings.AppSettings` without forcing the service
    to import settings.
    """

    emergency_pause_enabled: bool = False
    ai_provider_preference: str = "mock"


BrandProfileLoader = Callable[[str], Optional[dict[str, Any]]]
MediaAssetLoader = Callable[[list[str]], list[dict[str, Any]]]
SettingsLoader = Callable[[], Optional[SettingsSnapshot]]


@dataclass
class ContentGenerationService:
    provider: Optional[AIProvider] = None
    brand_loader: Optional[BrandProfileLoader] = None
    media_loader: Optional[MediaAssetLoader] = None
    settings_loader: Optional[SettingsLoader] = None
    safety_check_runner: Callable[..., tuple[list[str], list[str], list[str]]] = field(
        default=run_safety_checks
    )

    def generate(
        self,
        input: ContentGenerationInput,
        options: Optional[ContentGenerationOptions] = None,
    ) -> GeneratedContentBundle:
        options = options or ContentGenerationOptions()
        input.validate()
        options.validate()

        resolved_brand = self._resolve_brand_profile(input)
        resolved_media = self._resolve_media_assets(input)
        settings = self._load_settings()
        emergency_pause = bool(getattr(settings, "emergency_pause_enabled", False))

        resolved_input = ContentGenerationInput(
            brand_profile=resolved_brand,
            content_goal=input.content_goal,
            content_angle=input.content_angle,
            selected_platforms=list(input.selected_platforms),
            selected_media_assets=list(resolved_media),
            campaign_name=input.campaign_name,
            target_audience=input.target_audience,
            location_context=input.location_context,
            offer_context=input.offer_context,
            user_instructions=self._compose_instructions(input),
            approval_required=input.approval_required,
            content_idea_id=input.content_idea_id,
        )
        resolved_input.validate()

        prompt_template = self._load_prompt(options.prompt_id)
        rendered_prompt = prompt_template.render(
            self._build_prompt_variables(resolved_input, options)
        )

        provider = self._resolve_provider(options)

        try:
            bundle = provider.generate_bundle(resolved_input, options)
        except AIProviderError as error:
            raise ContentGenerationError(str(error)) from error

        self._apply_safety_review(
            bundle,
            brand_profile=resolved_brand,
            emergency_pause=emergency_pause,
            rendered_prompt=rendered_prompt,
            prompt_template_id=prompt_template.id,
            prompt_template_version=prompt_template.version,
        )

        return bundle

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    def _resolve_brand_profile(self, input: ContentGenerationInput) -> dict[str, Any]:
        if not isinstance(input.brand_profile, dict):
            raise ContentGenerationError("brand_profile must be a dict.")
        if input.brand_profile.get("businessName"):
            return dict(input.brand_profile)

        brand_id = input.brand_profile_id()
        if not self.brand_loader:
            raise ContentGenerationError(
                f"Brand profile {brand_id!r} is incomplete (missing 'businessName') "
                "and no brand_loader was configured. Either pass a complete brand_profile "
                "or configure the service with a brand_loader."
            )

        loaded = self.brand_loader(brand_id)
        if not loaded:
            raise ContentGenerationError(
                f"brand_loader returned no profile for {brand_id!r}."
            )
        merged: dict[str, Any] = dict(loaded)
        for key, value in input.brand_profile.items():
            if value is not None:
                merged[key] = value
        if not merged.get("businessName"):
            raise ContentGenerationError(
                f"Loaded brand profile for {brand_id!r} is missing 'businessName'."
            )
        return merged

    def _resolve_media_assets(self, input: ContentGenerationInput) -> list[dict[str, Any]]:
        if not input.selected_media_assets:
            return []
        if self.media_loader is None:
            return list(input.selected_media_assets)
        ids = []
        all_id_only = True
        for asset in input.selected_media_assets:
            if not isinstance(asset, dict):
                all_id_only = False
                break
            asset_id = asset.get("id")
            if not isinstance(asset_id, str) or not asset_id.strip():
                all_id_only = False
                break
            extra_keys = set(asset.keys()) - {"id"}
            if extra_keys:
                all_id_only = False
            ids.append(asset_id.strip())
        if not all_id_only:
            return list(input.selected_media_assets)
        loaded = self.media_loader(ids)
        if not isinstance(loaded, list):
            raise ContentGenerationError("media_loader must return a list of dicts.")
        for asset in loaded:
            if not isinstance(asset, dict):
                raise ContentGenerationError("media_loader entries must be dicts.")
        return loaded

    def _load_settings(self) -> Optional[SettingsSnapshot]:
        if self.settings_loader is None:
            return None
        snapshot = self.settings_loader()
        if snapshot is None:
            return None
        if not isinstance(snapshot, SettingsSnapshot):
            # Accept any object with the same duck-typed attributes.
            return SettingsSnapshot(
                emergency_pause_enabled=bool(
                    getattr(snapshot, "emergency_pause_enabled", False)
                    or getattr(snapshot, "emergencyPauseEnabled", False)
                ),
                ai_provider_preference=str(
                    getattr(snapshot, "ai_provider_preference", None)
                    or getattr(snapshot, "aiProviderPreference", None)
                    or "mock"
                ),
            )
        return snapshot

    def _load_prompt(self, prompt_id: str):
        try:
            return get_prompt(prompt_id)
        except PromptRegistryError as error:
            raise ContentGenerationError(str(error)) from error

    def _resolve_provider(self, options: ContentGenerationOptions) -> AIProvider:
        if self.provider is not None:
            return self.provider
        try:
            return get_provider(options.provider_name)
        except Exception as error:  # ProviderConfigurationError -> friendly wrap
            raise ContentGenerationError(str(error)) from error

    def _compose_instructions(self, input: ContentGenerationInput) -> Optional[str]:
        parts: list[str] = []
        if input.user_instructions:
            parts.append(input.user_instructions)
        if input.campaign_name:
            parts.append(f"Campaign: {input.campaign_name}.")
        if input.location_context:
            parts.append(f"Location context: {input.location_context}.")
        if input.offer_context:
            parts.append(f"Offer context: {input.offer_context}.")
        return " ".join(parts) if parts else None

    def _build_prompt_variables(
        self,
        input: ContentGenerationInput,
        options: ContentGenerationOptions,
    ) -> dict[str, Any]:
        brand = input.brand_profile
        media_notes = []
        for asset in input.selected_media_assets:
            if not isinstance(asset, dict):
                continue
            media_notes.append(
                "id: "
                + str(asset.get("id", "unknown"))
                + "; angle: "
                + str(asset.get("contentAngle") or asset.get("content_angle") or "unspecified")
                + "; stage: "
                + str(asset.get("stage") or asset.get("usageStatus") or "unspecified")
            )
        return {
            "business_name": brand.get("businessName") or "the business",
            "brand_voice": brand.get("voice") or brand.get("brandVoice"),
            "services": brand.get("services") or [],
            "supported_claims": brand.get("supportedClaims") or [],
            "blocked_phrases": brand.get("blockedPhrases") or brand.get("bannedWords") or [],
            "target_audience": input.target_audience or brand.get("targetAudience"),
            "locations": brand.get("locations") or brand.get("serviceAreas") or [],
            "content_goal": input.content_goal,
            "content_angle": input.content_angle,
            "media_notes": media_notes,
            "user_instructions": input.user_instructions,
            "requested_platforms": list(input.selected_platforms),
        }

    # ------------------------------------------------------------------
    # Safety review
    # ------------------------------------------------------------------

    def _apply_safety_review(
        self,
        bundle: GeneratedContentBundle,
        *,
        brand_profile: dict[str, Any],
        emergency_pause: bool,
        rendered_prompt: str,
        prompt_template_id: str,
        prompt_template_version: str,
    ) -> None:
        all_flags: list[str] = []
        all_blocking: list[str] = []
        all_fixes: list[str] = []

        for post in bundle.posts:
            flags, blocking, fixes = self.safety_check_runner(
                post.caption,
                brand_profile,
                emergency_pause_enabled=emergency_pause,
            )
            # Defensive: ensure blocking ⊆ flags before assigning to the post.
            post.safety_flags = list(flags)
            for value in flags:
                if value not in all_flags:
                    all_flags.append(value)
            for value in blocking:
                if value not in all_blocking:
                    all_blocking.append(value)
            for fix in fixes:
                if fix not in all_fixes:
                    all_fixes.append(fix)

        bundle.safety_review = GeneratedPostSafetyReview(
            flags=sorted(all_flags),
            blocking_flags=sorted(all_blocking),
            reviewer="local_rules",
            notes=self._safety_notes(all_flags, all_blocking, emergency_pause),
            suggested_fixes=all_fixes,
        )
        bundle.prompt_metadata = dict(bundle.prompt_metadata or {})
        bundle.prompt_metadata.update(
            {
                "rendered_prompt_chars": len(rendered_prompt),
                "rendered_prompt_template_id": prompt_template_id,
                "rendered_prompt_version": prompt_template_version,
            }
        )

    def _safety_notes(
        self,
        flags: list[str],
        blocking_flags: list[str],
        emergency_pause: bool,
    ) -> str:
        parts = ["Local rule-based safety check completed."]
        if emergency_pause:
            parts.append(
                "Emergency pause is enabled — scheduling and publishing remain blocked elsewhere."
            )
        parts.append(f"{len(flags)} flag(s); {len(blocking_flags)} blocking.")
        return " ".join(parts)


# ---------------------------------------------------------------------------
# Module-level convenience function for one-shot use.
# ---------------------------------------------------------------------------


def generate_content(
    input: ContentGenerationInput,
    options: Optional[ContentGenerationOptions] = None,
    **service_kwargs: Any,
) -> GeneratedContentBundle:
    """Build a default-configured service and run one generation call."""
    return ContentGenerationService(**service_kwargs).generate(input, options)


__all__ = [
    "ContentGenerationError",
    "ContentGenerationService",
    "SettingsSnapshot",
    "generate_content",
]
