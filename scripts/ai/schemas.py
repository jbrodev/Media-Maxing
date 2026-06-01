"""Structured input and output schemas for AI content generation.

These dataclasses are the canonical Python shape for content generation.
They mirror the TypeScript shapes in ``packages/types/index.ts`` where
they overlap and validate enums and required fields locally without
depending on external packages.

Runtime validation lives in each dataclass's ``__post_init__`` or
``validate()`` method. The validator raises
:class:`SchemaValidationError` with a useful message so callers and
tests can assert on specific failure modes without parsing exception
text.

These schemas are also designed to round-trip through SQLite JSON
columns: every nested value is a primitive, list, or dict, and
``to_dict()`` returns a JSON-serialisable shape.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

# ---------------------------------------------------------------------------
# Enums and shared constants.
# ---------------------------------------------------------------------------

AIProviderName = Literal["mock", "openai", "anthropic", "local"]

SUPPORTED_PLATFORMS = (
    "facebook",
    "instagram",
    "threads",
    "youtube",
    "tiktok",
    "linkedin",
    "x",
)

SUPPORTED_GOALS = (
    "get_leads",
    "show_transformation",
    "educate_customer",
    "promote_offer",
    "build_trust",
    "announce_availability",
    "repurpose_old_content",
    "behind_the_scenes",
    "seasonal_reminder",
)

SUPPORTED_ANGLES = (
    "before_after",
    "educational",
    "behind_the_scenes",
    "testimonial",
    "promotion",
    "faq",
    "trust_builder",
    "transformation",
    "seasonal",
    "other",
)

SUPPORTED_PROVIDERS = ("mock", "openai", "anthropic", "local")

APPROVAL_STATUSES = (
    "draft",
    "needs_review",
    "approved",
    "rejected",
    "revision_requested",
    "archived",
)

CREATIVITY_LEVELS = ("low", "medium", "high")

SUGGESTION_SEVERITIES = ("minor", "moderate", "critical")

SAFETY_REVIEWERS = ("local_rules", "ai", "manual")

# The standard safety flag vocabulary documented for the safety review
# module. Extra snake_case flag names are allowed at runtime; the
# vocabulary is exported for the Settings UI, safety review module, and
# the prompt registry.
SAFETY_FLAG_VOCABULARY = (
    "invented_fact",
    "unsupported_claim",
    "fake_testimonial",
    "unsupported_guarantee",
    "aggressive_language",
    "sensitive_or_private_info",
    "platform_policy_risk",
    "brand_mismatch",
    "missing_approval",
    "emergency_pause_conflict",
)


# ---------------------------------------------------------------------------
# Error type and small validators.
# ---------------------------------------------------------------------------


class SchemaValidationError(ValueError):
    """Raised when a content generation input or output fails validation."""


def _require_string(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{field_name} is required and must be a non-empty string.")
    return value.strip()


def _require_enum(field_name: str, value: Any, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise SchemaValidationError(
            f"{field_name} must be one of {list(allowed)}, got {value!r}."
        )
    return value


def _require_string_list(field_name: str, values: Any) -> list[str]:
    if not isinstance(values, list):
        raise SchemaValidationError(f"{field_name} must be a list.")
    cleaned: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise SchemaValidationError(f"{field_name} must contain only strings.")
        stripped = item.strip()
        if stripped:
            cleaned.append(stripped)
    return cleaned


def _require_optional_string(field_name: str, value: Any) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SchemaValidationError(f"{field_name} must be a string or None.")
    return value


def _require_dict(field_name: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SchemaValidationError(f"{field_name} must be a dict.")
    return value


def _require_dict_list(field_name: str, values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        raise SchemaValidationError(f"{field_name} must be a list of dicts.")
    for item in values:
        if not isinstance(item, dict):
            raise SchemaValidationError(f"{field_name} entries must be dicts.")
    return values


# ---------------------------------------------------------------------------
# Small leaf types: caption variants, hashtag sets, scores, suggestions.
# ---------------------------------------------------------------------------


@dataclass
class CaptionVariant:
    text: str
    style: str

    def __post_init__(self) -> None:
        self.text = _require_string("CaptionVariant.text", self.text)
        self.style = _require_string("CaptionVariant.style", self.style)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HashtagSet:
    platform: str
    hashtags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.platform = _require_enum("HashtagSet.platform", self.platform, SUPPORTED_PLATFORMS)
        cleaned = _require_string_list("HashtagSet.hashtags", self.hashtags)
        for tag in cleaned:
            if not tag.startswith("#"):
                raise SchemaValidationError(
                    f"HashtagSet.hashtags entries must start with '#': {tag!r}"
                )
        self.hashtags = cleaned

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedPostScore:
    """Quality score for a generated draft. Scores are on a 0..100 scale."""

    overall: float
    breakdown: dict[str, float] = field(default_factory=dict)
    rationale: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.overall, (int, float)):
            raise SchemaValidationError("GeneratedPostScore.overall must be a number.")
        if not 0 <= self.overall <= 100:
            raise SchemaValidationError(
                "GeneratedPostScore.overall must be between 0 and 100 inclusive."
            )
        if not isinstance(self.breakdown, dict):
            raise SchemaValidationError("GeneratedPostScore.breakdown must be a dict.")
        for key, value in self.breakdown.items():
            if not isinstance(key, str) or not key.strip():
                raise SchemaValidationError(
                    "GeneratedPostScore.breakdown keys must be non-empty strings."
                )
            if not isinstance(value, (int, float)) or not 0 <= value <= 100:
                raise SchemaValidationError(
                    f"GeneratedPostScore.breakdown[{key!r}] must be a number between 0 and 100."
                )
        self.rationale = _require_optional_string("GeneratedPostScore.rationale", self.rationale)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DraftImprovementSuggestion:
    """One owner-facing suggestion for improving a draft."""

    suggestion_text: str
    target_field: Optional[str] = None
    severity: str = "minor"
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        self.suggestion_text = _require_string(
            "DraftImprovementSuggestion.suggestion_text", self.suggestion_text
        )
        self.target_field = _require_optional_string(
            "DraftImprovementSuggestion.target_field", self.target_field
        )
        self.severity = _require_enum(
            "DraftImprovementSuggestion.severity", self.severity, SUGGESTION_SEVERITIES
        )
        self.notes = _require_optional_string("DraftImprovementSuggestion.notes", self.notes)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategyIdea:
    title: str
    content_goal: str
    content_angle: str
    media_asset_ids: list[str] = field(default_factory=list)
    rationale: Optional[str] = None
    needs_owner_confirmation: bool = False

    def __post_init__(self) -> None:
        self.title = _require_string("StrategyIdea.title", self.title)
        self.content_goal = _require_enum(
            "StrategyIdea.content_goal", self.content_goal, SUPPORTED_GOALS
        )
        self.content_angle = _require_enum(
            "StrategyIdea.content_angle", self.content_angle, SUPPORTED_ANGLES
        )
        self.media_asset_ids = _require_string_list(
            "StrategyIdea.media_asset_ids", self.media_asset_ids
        )
        self.rationale = _require_optional_string("StrategyIdea.rationale", self.rationale)
        if not isinstance(self.needs_owner_confirmation, bool):
            raise SchemaValidationError(
                "StrategyIdea.needs_owner_confirmation must be a boolean."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContentStrategyBrief:
    summary: str
    ideas: list[StrategyIdea] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    planning_window: Optional[str] = None

    def __post_init__(self) -> None:
        self.summary = _require_string("ContentStrategyBrief.summary", self.summary)
        if not isinstance(self.ideas, list):
            raise SchemaValidationError("ContentStrategyBrief.ideas must be a list.")
        for idea in self.ideas:
            if not isinstance(idea, StrategyIdea):
                raise SchemaValidationError(
                    "ContentStrategyBrief.ideas entries must be StrategyIdea instances."
                )
        if not 1 <= len(self.ideas) <= 8:
            raise SchemaValidationError(
                "ContentStrategyBrief.ideas must contain between 1 and 8 ideas."
            )
        self.open_questions = _require_string_list(
            "ContentStrategyBrief.open_questions", self.open_questions
        )
        self.planning_window = _require_optional_string(
            "ContentStrategyBrief.planning_window", self.planning_window
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedPostSafetyReview:
    flags: list[str] = field(default_factory=list)
    blocking_flags: list[str] = field(default_factory=list)
    reviewer: str = "local_rules"
    notes: Optional[str] = None
    suggested_fixes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.flags = _require_string_list("GeneratedPostSafetyReview.flags", self.flags)
        self.blocking_flags = _require_string_list(
            "GeneratedPostSafetyReview.blocking_flags", self.blocking_flags
        )
        invalid_blocking = set(self.blocking_flags) - set(self.flags)
        if invalid_blocking:
            raise SchemaValidationError(
                "GeneratedPostSafetyReview.blocking_flags must be a subset of flags. "
                f"Unknown blocking flags: {sorted(invalid_blocking)}."
            )
        self.reviewer = _require_enum(
            "GeneratedPostSafetyReview.reviewer", self.reviewer, SAFETY_REVIEWERS
        )
        self.notes = _require_optional_string("GeneratedPostSafetyReview.notes", self.notes)
        self.suggested_fixes = _require_string_list(
            "GeneratedPostSafetyReview.suggested_fixes", self.suggested_fixes
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Platform-specific draft + bundle.
# ---------------------------------------------------------------------------


@dataclass
class PlatformPostDraft:
    """A draft for one platform. Default status is 'needs_review'."""

    platform: str
    caption: str
    headline: Optional[str] = None
    short_caption: Optional[str] = None
    long_caption: Optional[str] = None
    hook: Optional[str] = None
    call_to_action: Optional[str] = None
    hashtags: list[str] = field(default_factory=list)
    media_asset_ids: list[str] = field(default_factory=list)
    content_angle: Optional[str] = None
    content_goal: Optional[str] = None
    target_audience: Optional[str] = None
    suggested_post_time: Optional[str] = None
    alt_text: Optional[str] = None
    notes: Optional[str] = None
    caption_variants: list[CaptionVariant] = field(default_factory=list)
    safety_flags: list[str] = field(default_factory=list)
    score: Optional[GeneratedPostScore] = None
    status: str = "needs_review"

    def __post_init__(self) -> None:
        self.platform = _require_enum(
            "PlatformPostDraft.platform", self.platform, SUPPORTED_PLATFORMS
        )
        self.caption = _require_string("PlatformPostDraft.caption", self.caption)
        for optional_name in (
            "headline",
            "short_caption",
            "long_caption",
            "hook",
            "call_to_action",
            "target_audience",
            "suggested_post_time",
            "alt_text",
            "notes",
        ):
            setattr(
                self,
                optional_name,
                _require_optional_string(
                    f"PlatformPostDraft.{optional_name}", getattr(self, optional_name)
                ),
            )
        cleaned_tags = _require_string_list("PlatformPostDraft.hashtags", self.hashtags)
        for tag in cleaned_tags:
            if not tag.startswith("#"):
                raise SchemaValidationError(
                    f"PlatformPostDraft.hashtags entries must start with '#': {tag!r}"
                )
        self.hashtags = cleaned_tags
        self.media_asset_ids = _require_string_list(
            "PlatformPostDraft.media_asset_ids", self.media_asset_ids
        )
        if self.content_angle is not None:
            self.content_angle = _require_enum(
                "PlatformPostDraft.content_angle", self.content_angle, SUPPORTED_ANGLES
            )
        if self.content_goal is not None:
            self.content_goal = _require_enum(
                "PlatformPostDraft.content_goal", self.content_goal, SUPPORTED_GOALS
            )
        for variant in self.caption_variants:
            if not isinstance(variant, CaptionVariant):
                raise SchemaValidationError(
                    "PlatformPostDraft.caption_variants entries must be CaptionVariant instances."
                )
        self.safety_flags = _require_string_list(
            "PlatformPostDraft.safety_flags", self.safety_flags
        )
        if self.score is not None and not isinstance(self.score, GeneratedPostScore):
            raise SchemaValidationError(
                "PlatformPostDraft.score must be a GeneratedPostScore or None."
            )
        self.status = _require_enum("PlatformPostDraft.status", self.status, APPROVAL_STATUSES)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedContentBundle:
    """The full output of a content generation run.

    ``prompt_metadata`` carries the prompt id, version, and any context
    the prompt registry rendered with. ``provider_metadata`` carries the
    provider id, model id, fingerprint, and any vendor-safe metadata.
    """

    brand_profile_id: str
    posts: list[PlatformPostDraft]
    prompt_id: str
    prompt_version: str
    generation_provider: str
    prompt_metadata: dict[str, Any] = field(default_factory=dict)
    provider_metadata: dict[str, Any] = field(default_factory=dict)
    safety_review: GeneratedPostSafetyReview = field(default_factory=GeneratedPostSafetyReview)
    strategy_brief: Optional[ContentStrategyBrief] = None
    caption_variants: list[CaptionVariant] = field(default_factory=list)
    hashtag_sets: list[HashtagSet] = field(default_factory=list)
    improvement_suggestions: list[DraftImprovementSuggestion] = field(default_factory=list)
    content_idea_id: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        self.brand_profile_id = _require_string(
            "GeneratedContentBundle.brand_profile_id", self.brand_profile_id
        )
        if not isinstance(self.posts, list) or not self.posts:
            raise SchemaValidationError(
                "GeneratedContentBundle.posts must be a non-empty list of PlatformPostDraft."
            )
        for draft in self.posts:
            if not isinstance(draft, PlatformPostDraft):
                raise SchemaValidationError(
                    "GeneratedContentBundle.posts entries must be PlatformPostDraft instances."
                )
        self.prompt_id = _require_string("GeneratedContentBundle.prompt_id", self.prompt_id)
        self.prompt_version = _require_string(
            "GeneratedContentBundle.prompt_version", self.prompt_version
        )
        self.generation_provider = _require_enum(
            "GeneratedContentBundle.generation_provider",
            self.generation_provider,
            SUPPORTED_PROVIDERS,
        )
        _require_dict("GeneratedContentBundle.prompt_metadata", self.prompt_metadata)
        _require_dict("GeneratedContentBundle.provider_metadata", self.provider_metadata)
        if not isinstance(self.safety_review, GeneratedPostSafetyReview):
            raise SchemaValidationError(
                "GeneratedContentBundle.safety_review must be a GeneratedPostSafetyReview."
            )
        if self.strategy_brief is not None and not isinstance(
            self.strategy_brief, ContentStrategyBrief
        ):
            raise SchemaValidationError(
                "GeneratedContentBundle.strategy_brief must be a ContentStrategyBrief or None."
            )
        for caption_variant in self.caption_variants:
            if not isinstance(caption_variant, CaptionVariant):
                raise SchemaValidationError(
                    "GeneratedContentBundle.caption_variants entries must be CaptionVariant instances."
                )
        for hashtag_set in self.hashtag_sets:
            if not isinstance(hashtag_set, HashtagSet):
                raise SchemaValidationError(
                    "GeneratedContentBundle.hashtag_sets entries must be HashtagSet instances."
                )
        for suggestion in self.improvement_suggestions:
            if not isinstance(suggestion, DraftImprovementSuggestion):
                raise SchemaValidationError(
                    "GeneratedContentBundle.improvement_suggestions entries must be "
                    "DraftImprovementSuggestion instances."
                )
        self.content_idea_id = _require_optional_string(
            "GeneratedContentBundle.content_idea_id", self.content_idea_id
        )
        self.created_at = _require_optional_string(
            "GeneratedContentBundle.created_at", self.created_at
        )

    @property
    def drafts(self) -> list[PlatformPostDraft]:
        """Back-compat alias for ``posts``. Some prompt templates and prior
        code refer to drafts; the bundle stores them as ``posts``."""
        return self.posts

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Generation request inputs.
# ---------------------------------------------------------------------------


@dataclass
class ContentGenerationInput:
    brand_profile: dict[str, Any]
    content_goal: str
    content_angle: str
    selected_platforms: list[str]
    selected_media_assets: list[dict[str, Any]] = field(default_factory=list)
    campaign_name: Optional[str] = None
    target_audience: Optional[str] = None
    location_context: Optional[str] = None
    offer_context: Optional[str] = None
    user_instructions: Optional[str] = None
    approval_required: bool = True
    content_idea_id: Optional[str] = None

    def validate(self) -> None:
        _require_dict("ContentGenerationInput.brand_profile", self.brand_profile)
        if not self.brand_profile:
            raise SchemaValidationError("ContentGenerationInput.brand_profile is required.")
        brand_id = self.brand_profile.get("id") or self.brand_profile.get("brandProfileId")
        if not isinstance(brand_id, str) or not brand_id.strip():
            raise SchemaValidationError(
                "ContentGenerationInput.brand_profile must include a non-empty 'id'."
            )
        _require_enum(
            "ContentGenerationInput.content_goal", self.content_goal, SUPPORTED_GOALS
        )
        _require_enum(
            "ContentGenerationInput.content_angle", self.content_angle, SUPPORTED_ANGLES
        )
        if not isinstance(self.selected_platforms, list) or not self.selected_platforms:
            raise SchemaValidationError(
                "ContentGenerationInput.selected_platforms must be a non-empty list "
                "of supported platforms."
            )
        for platform in self.selected_platforms:
            _require_enum(
                "ContentGenerationInput.selected_platforms", platform, SUPPORTED_PLATFORMS
            )
        _require_dict_list(
            "ContentGenerationInput.selected_media_assets", self.selected_media_assets
        )
        _require_optional_string(
            "ContentGenerationInput.campaign_name", self.campaign_name
        )
        _require_optional_string(
            "ContentGenerationInput.target_audience", self.target_audience
        )
        _require_optional_string(
            "ContentGenerationInput.location_context", self.location_context
        )
        _require_optional_string(
            "ContentGenerationInput.offer_context", self.offer_context
        )
        _require_optional_string(
            "ContentGenerationInput.user_instructions", self.user_instructions
        )
        if not isinstance(self.approval_required, bool):
            raise SchemaValidationError(
                "ContentGenerationInput.approval_required must be a boolean."
            )
        _require_optional_string(
            "ContentGenerationInput.content_idea_id", self.content_idea_id
        )

    def brand_profile_id(self) -> str:
        return str(self.brand_profile.get("id") or self.brand_profile.get("brandProfileId") or "")


@dataclass
class ContentGenerationOptions:
    provider_name: str = "mock"
    prompt_id: str = "platform_post_generator_v1"
    number_of_variants: int = 0
    include_hashtags: bool = True
    include_emojis: bool = False
    include_cta: bool = True
    tone: Optional[str] = None
    creativity_level: str = "medium"
    max_caption_length: Optional[int] = None
    require_safety_review: bool = True
    generate_platform_specific_versions: bool = True
    hashtag_count: int = 5

    def validate(self) -> None:
        _require_enum(
            "ContentGenerationOptions.provider_name", self.provider_name, SUPPORTED_PROVIDERS
        )
        _require_string("ContentGenerationOptions.prompt_id", self.prompt_id)
        for bool_name in (
            "include_hashtags",
            "include_emojis",
            "include_cta",
            "require_safety_review",
            "generate_platform_specific_versions",
        ):
            if not isinstance(getattr(self, bool_name), bool):
                raise SchemaValidationError(
                    f"ContentGenerationOptions.{bool_name} must be a boolean."
                )
        if not isinstance(self.number_of_variants, int) or self.number_of_variants < 0:
            raise SchemaValidationError(
                "ContentGenerationOptions.number_of_variants must be a non-negative integer."
            )
        _require_optional_string("ContentGenerationOptions.tone", self.tone)
        _require_enum(
            "ContentGenerationOptions.creativity_level",
            self.creativity_level,
            CREATIVITY_LEVELS,
        )
        if self.max_caption_length is not None and (
            not isinstance(self.max_caption_length, int) or self.max_caption_length <= 0
        ):
            raise SchemaValidationError(
                "ContentGenerationOptions.max_caption_length must be a positive integer or None."
            )
        if not isinstance(self.hashtag_count, int) or self.hashtag_count < 0:
            raise SchemaValidationError(
                "ContentGenerationOptions.hashtag_count must be a non-negative integer."
            )


# ---------------------------------------------------------------------------
# Generic text and structured generation request/response shapes.
# These are lower-level primitives that every provider must implement.
# ---------------------------------------------------------------------------


@dataclass
class AITextGenerationRequest:
    prompt: str
    system: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stop_sequences: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise SchemaValidationError("AITextGenerationRequest.prompt is required.")
        if self.system is not None and not isinstance(self.system, str):
            raise SchemaValidationError(
                "AITextGenerationRequest.system must be a string or None."
            )
        if self.max_tokens is not None and (
            not isinstance(self.max_tokens, int) or self.max_tokens <= 0
        ):
            raise SchemaValidationError(
                "AITextGenerationRequest.max_tokens must be a positive integer or None."
            )
        if self.temperature is not None and not isinstance(self.temperature, (int, float)):
            raise SchemaValidationError(
                "AITextGenerationRequest.temperature must be a number or None."
            )
        if not isinstance(self.stop_sequences, list) or any(
            not isinstance(item, str) for item in self.stop_sequences
        ):
            raise SchemaValidationError(
                "AITextGenerationRequest.stop_sequences must be a list of strings."
            )
        if not isinstance(self.metadata, dict):
            raise SchemaValidationError("AITextGenerationRequest.metadata must be a dict.")


@dataclass
class AITextGenerationResponse:
    text: str
    provider: str
    model: Optional[str] = None
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_mock: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise SchemaValidationError("AITextGenerationResponse.text must be a string.")
        if self.provider not in SUPPORTED_PROVIDERS:
            raise SchemaValidationError(
                f"AITextGenerationResponse.provider must be one of {list(SUPPORTED_PROVIDERS)}."
            )
        if not isinstance(self.usage, dict):
            raise SchemaValidationError("AITextGenerationResponse.usage must be a dict.")
        if not isinstance(self.metadata, dict):
            raise SchemaValidationError("AITextGenerationResponse.metadata must be a dict.")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AIStructuredGenerationRequest:
    prompt: str
    schema_name: str
    schema_hint: Optional[dict[str, Any]] = None
    system: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise SchemaValidationError("AIStructuredGenerationRequest.prompt is required.")
        if not isinstance(self.schema_name, str) or not self.schema_name.strip():
            raise SchemaValidationError(
                "AIStructuredGenerationRequest.schema_name is required."
            )
        if self.schema_hint is not None and not isinstance(self.schema_hint, dict):
            raise SchemaValidationError(
                "AIStructuredGenerationRequest.schema_hint must be a dict or None."
            )
        if self.system is not None and not isinstance(self.system, str):
            raise SchemaValidationError(
                "AIStructuredGenerationRequest.system must be a string or None."
            )
        if not isinstance(self.metadata, dict):
            raise SchemaValidationError(
                "AIStructuredGenerationRequest.metadata must be a dict."
            )


@dataclass
class AIStructuredGenerationResponse:
    data: dict[str, Any]
    schema_name: str
    provider: str
    model: Optional[str] = None
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    is_mock: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.data, dict):
            raise SchemaValidationError(
                "AIStructuredGenerationResponse.data must be a dict."
            )
        if not isinstance(self.schema_name, str) or not self.schema_name.strip():
            raise SchemaValidationError(
                "AIStructuredGenerationResponse.schema_name is required."
            )
        if self.provider not in SUPPORTED_PROVIDERS:
            raise SchemaValidationError(
                f"AIStructuredGenerationResponse.provider must be one of {list(SUPPORTED_PROVIDERS)}."
            )
        if not isinstance(self.usage, dict):
            raise SchemaValidationError(
                "AIStructuredGenerationResponse.usage must be a dict."
            )
        if not isinstance(self.metadata, dict):
            raise SchemaValidationError(
                "AIStructuredGenerationResponse.metadata must be a dict."
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
