"""Tests for the content generation structured schemas.

These tests exercise:
- Each new schema (GeneratedPostScore, DraftImprovementSuggestion,
  StrategyIdea, ContentStrategyBrief, expanded PlatformPostDraft,
  expanded GeneratedContentBundle, expanded ContentGenerationInput,
  expanded ContentGenerationOptions, and the safety review).
- A valid GeneratedContentBundle fixture round-trips through
  ``to_dict`` cleanly.
- An invalid GeneratedContentBundle fixture raises
  ``SchemaValidationError`` with a useful message.
- Platform, goal, angle, status, provider, severity, creativity, and
  safety reviewer enums match the rest of the app.
"""

from __future__ import annotations

import json
import unittest

from scripts.ai.schemas import (
    APPROVAL_STATUSES,
    CREATIVITY_LEVELS,
    SAFETY_FLAG_VOCABULARY,
    SAFETY_REVIEWERS,
    SUGGESTION_SEVERITIES,
    SUPPORTED_ANGLES,
    SUPPORTED_GOALS,
    SUPPORTED_PLATFORMS,
    SUPPORTED_PROVIDERS,
    CaptionVariant,
    ContentGenerationInput,
    ContentGenerationOptions,
    ContentStrategyBrief,
    DraftImprovementSuggestion,
    GeneratedContentBundle,
    GeneratedPostSafetyReview,
    GeneratedPostScore,
    HashtagSet,
    PlatformPostDraft,
    SchemaValidationError,
    StrategyIdea,
)


# ---------------------------------------------------------------------------
# Reusable fixtures.
# ---------------------------------------------------------------------------


def _valid_brand_profile() -> dict:
    return {
        "id": "brand-fixture",
        "businessName": "Fixture Local Service",
        "voice": "Helpful, honest, neighborly.",
        "services": ["pressure washing"],
        "supportedClaims": ["uses careful surface checks"],
        "targetAudience": "local homeowners",
    }


def _valid_score() -> GeneratedPostScore:
    return GeneratedPostScore(
        overall=82.0,
        breakdown={"clarity": 90.0, "brand_voice": 80.0, "safety_match": 76.0},
        rationale="Strong clarity. Voice mostly on brand. No safety blockers detected.",
    )


def _valid_post() -> PlatformPostDraft:
    return PlatformPostDraft(
        platform="instagram",
        caption="Fixture caption for testing the structured schema layer.",
        headline="Sample headline",
        short_caption="Short fixture caption.",
        long_caption="Longer fixture caption with more detail about the project.",
        hook="A small change that makes a big difference.",
        call_to_action="Reply or send a message to ask about availability.",
        hashtags=["#FixtureLocal", "#PressureWashing"],
        media_asset_ids=["media-fixture-before", "media-fixture-after"],
        content_angle="before_after",
        content_goal="show_transformation",
        target_audience="local homeowners",
        suggested_post_time="2026-06-04T16:00:00Z",
        alt_text="Before and after photos of a cleaned driveway.",
        notes="Fixture only.",
        caption_variants=[
            CaptionVariant(text="Short alt variant.", style="short"),
        ],
        safety_flags=[],
        score=_valid_score(),
        status="needs_review",
    )


def _valid_strategy_brief() -> ContentStrategyBrief:
    return ContentStrategyBrief(
        summary="Plan a transformation post and a seasonal reminder.",
        ideas=[
            StrategyIdea(
                title="Driveway transformation",
                content_goal="show_transformation",
                content_angle="before_after",
                media_asset_ids=["media-fixture-before", "media-fixture-after"],
                rationale="Strong visual difference and supportable claims.",
            ),
            StrategyIdea(
                title="Seasonal gutter check reminder",
                content_goal="seasonal_reminder",
                content_angle="educational",
                rationale="Owner asked for seasonal content.",
                needs_owner_confirmation=True,
            ),
        ],
        open_questions=["Do we have a recent gutter-cleaning photo?"],
        planning_window="next 7 days",
    )


def _valid_safety_review() -> GeneratedPostSafetyReview:
    return GeneratedPostSafetyReview(
        flags=[],
        blocking_flags=[],
        reviewer="local_rules",
        notes="Fixture: no flags raised.",
        suggested_fixes=[],
    )


def _valid_bundle() -> GeneratedContentBundle:
    return GeneratedContentBundle(
        brand_profile_id="brand-fixture",
        posts=[_valid_post()],
        prompt_id="platform_post_generator_v1",
        prompt_version="v1",
        generation_provider="mock",
        prompt_metadata={
            "prompt_id": "platform_post_generator_v1",
            "prompt_version": "v1",
            "render_format": "structured-mock",
            "content_goal": "show_transformation",
            "content_angle": "before_after",
            "selected_platforms": ["instagram"],
        },
        provider_metadata={
            "deterministic": True,
            "mock": True,
            "model": "mock-deterministic-v1",
        },
        safety_review=_valid_safety_review(),
        strategy_brief=_valid_strategy_brief(),
        caption_variants=[CaptionVariant(text="Bundle-level variant.", style="warm")],
        hashtag_sets=[
            HashtagSet(platform="instagram", hashtags=["#FixtureLocal", "#LocalBusiness"]),
        ],
        improvement_suggestions=[
            DraftImprovementSuggestion(
                suggestion_text="Add one sentence about safety checks.",
                target_field="caption",
                severity="minor",
            ),
        ],
        content_idea_id="idea-fixture",
        created_at="2026-05-26T12:00:00Z",
    )


# ---------------------------------------------------------------------------
# Enum cross-checks. These keep the schema and the rest of the app in sync.
# ---------------------------------------------------------------------------


class EnumConsistencyTest(unittest.TestCase):
    def test_platform_enum_matches_app(self):
        self.assertEqual(
            set(SUPPORTED_PLATFORMS),
            {"facebook", "instagram", "threads", "youtube", "tiktok", "linkedin", "x"},
        )

    def test_goal_enum_has_required_values(self):
        for value in (
            "get_leads",
            "show_transformation",
            "build_trust",
            "seasonal_reminder",
        ):
            self.assertIn(value, SUPPORTED_GOALS)

    def test_angle_enum_has_required_values(self):
        for value in ("before_after", "educational", "trust_builder"):
            self.assertIn(value, SUPPORTED_ANGLES)

    def test_provider_enum(self):
        self.assertEqual(
            set(SUPPORTED_PROVIDERS), {"mock", "openai", "anthropic", "local"}
        )

    def test_approval_statuses(self):
        self.assertEqual(
            set(APPROVAL_STATUSES),
            {
                "draft",
                "needs_review",
                "approved",
                "rejected",
                "revision_requested",
                "archived",
            },
        )

    def test_creativity_and_severity_and_reviewer_enums(self):
        self.assertEqual(set(CREATIVITY_LEVELS), {"low", "medium", "high"})
        self.assertEqual(set(SUGGESTION_SEVERITIES), {"minor", "moderate", "critical"})
        self.assertEqual(set(SAFETY_REVIEWERS), {"local_rules", "ai", "manual"})

    def test_safety_flag_vocabulary_covers_required_categories(self):
        for flag in (
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
        ):
            self.assertIn(flag, SAFETY_FLAG_VOCABULARY)


# ---------------------------------------------------------------------------
# Valid bundle round-trips.
# ---------------------------------------------------------------------------


class ValidBundleFixtureTest(unittest.TestCase):
    def test_valid_bundle_constructs_without_error(self):
        bundle = _valid_bundle()
        self.assertIsInstance(bundle, GeneratedContentBundle)
        self.assertEqual(bundle.brand_profile_id, "brand-fixture")
        self.assertEqual(len(bundle.posts), 1)
        self.assertEqual(bundle.posts[0].status, "needs_review")
        self.assertEqual(bundle.posts[0].score.overall, 82.0)

    def test_valid_bundle_to_dict_is_json_serialisable(self):
        # GeneratedContentBundle is intended to round-trip through a
        # SQLite JSON column, so its dict form must be JSON serialisable.
        payload = json.dumps(_valid_bundle().to_dict())
        self.assertIn("brand-fixture", payload)
        self.assertIn("platform_post_generator_v1", payload)

    def test_drafts_alias_returns_posts(self):
        bundle = _valid_bundle()
        self.assertIs(bundle.drafts, bundle.posts)


# ---------------------------------------------------------------------------
# Invalid bundle fixtures and field-level validation errors.
# ---------------------------------------------------------------------------


class InvalidBundleFixtureTest(unittest.TestCase):
    def test_unknown_platform_in_draft_rejected(self):
        with self.assertRaises(SchemaValidationError) as raised:
            PlatformPostDraft(platform="myspace", caption="text")
        self.assertIn("platform", str(raised.exception).lower())

    def test_unknown_status_in_draft_rejected(self):
        with self.assertRaises(SchemaValidationError):
            PlatformPostDraft(
                platform="instagram",
                caption="text",
                status="auto_published",
            )

    def test_hashtag_without_hash_rejected(self):
        with self.assertRaises(SchemaValidationError):
            PlatformPostDraft(
                platform="instagram",
                caption="text",
                hashtags=["LocalBusiness"],  # missing leading "#"
            )

    def test_blocking_flags_must_be_subset_of_flags(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedPostSafetyReview(
                flags=["aggressive_language"],
                blocking_flags=["fake_testimonial"],
            )

    def test_invalid_safety_reviewer_rejected(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedPostSafetyReview(reviewer="some_robot")

    def test_score_out_of_range_rejected(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedPostScore(overall=120.0)
        with self.assertRaises(SchemaValidationError):
            GeneratedPostScore(overall=-5.0)

    def test_score_breakdown_out_of_range_rejected(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedPostScore(overall=70.0, breakdown={"clarity": 150.0})

    def test_improvement_suggestion_severity_rejected(self):
        with self.assertRaises(SchemaValidationError):
            DraftImprovementSuggestion(
                suggestion_text="Tighten the hook.",
                severity="catastrophic",
            )

    def test_strategy_brief_must_have_at_least_one_idea(self):
        with self.assertRaises(SchemaValidationError):
            ContentStrategyBrief(summary="ok", ideas=[])

    def test_strategy_idea_unknown_goal_rejected(self):
        with self.assertRaises(SchemaValidationError):
            StrategyIdea(
                title="Bad goal",
                content_goal="dominate_earth",
                content_angle="before_after",
            )

    def test_bundle_with_empty_posts_rejected(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedContentBundle(
                brand_profile_id="brand-fixture",
                posts=[],
                prompt_id="x_v1",
                prompt_version="v1",
                generation_provider="mock",
            )

    def test_bundle_with_unknown_provider_rejected(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedContentBundle(
                brand_profile_id="brand-fixture",
                posts=[_valid_post()],
                prompt_id="x_v1",
                prompt_version="v1",
                generation_provider="random_llm_co",
            )

    def test_bundle_with_non_dict_metadata_rejected(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedContentBundle(
                brand_profile_id="brand-fixture",
                posts=[_valid_post()],
                prompt_id="x_v1",
                prompt_version="v1",
                generation_provider="mock",
                prompt_metadata="not a dict",  # type: ignore[arg-type]
            )

    def test_bundle_with_wrong_strategy_brief_type_rejected(self):
        with self.assertRaises(SchemaValidationError):
            GeneratedContentBundle(
                brand_profile_id="brand-fixture",
                posts=[_valid_post()],
                prompt_id="x_v1",
                prompt_version="v1",
                generation_provider="mock",
                strategy_brief={"summary": "raw dict, not a ContentStrategyBrief"},  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# ContentGenerationInput / Options validation.
# ---------------------------------------------------------------------------


class GenerationInputTest(unittest.TestCase):
    def _input(self, **overrides) -> ContentGenerationInput:
        base = dict(
            brand_profile=_valid_brand_profile(),
            content_goal="build_trust",
            content_angle="trust_builder",
            selected_platforms=["instagram"],
            selected_media_assets=[{"id": "media-fixture"}],
            campaign_name="Spring tune-up",
            target_audience="homeowners",
            location_context="Demo City",
            offer_context="Free quote within 5 miles",
            user_instructions="Keep claims supportable.",
            approval_required=True,
            content_idea_id="idea-fixture",
        )
        base.update(overrides)
        return ContentGenerationInput(**base)

    def test_valid_input_passes(self):
        inp = self._input()
        inp.validate()
        self.assertEqual(inp.brand_profile_id(), "brand-fixture")

    def test_missing_brand_id_rejected(self):
        inp = self._input(brand_profile={"businessName": "no id"})
        with self.assertRaises(SchemaValidationError):
            inp.validate()

    def test_unknown_content_goal_rejected(self):
        inp = self._input(content_goal="dominate_earth")
        with self.assertRaises(SchemaValidationError):
            inp.validate()

    def test_empty_selected_platforms_rejected(self):
        inp = self._input(selected_platforms=[])
        with self.assertRaises(SchemaValidationError):
            inp.validate()

    def test_unknown_platform_rejected(self):
        inp = self._input(selected_platforms=["myspace"])
        with self.assertRaises(SchemaValidationError):
            inp.validate()

    def test_approval_required_must_be_bool(self):
        inp = self._input(approval_required="yes please")  # type: ignore[arg-type]
        with self.assertRaises(SchemaValidationError):
            inp.validate()

    def test_selected_media_assets_must_be_list_of_dicts(self):
        inp = self._input(selected_media_assets=[{"id": "ok"}, "not a dict"])  # type: ignore[list-item]
        with self.assertRaises(SchemaValidationError):
            inp.validate()


class GenerationOptionsTest(unittest.TestCase):
    def test_defaults_validate(self):
        ContentGenerationOptions().validate()

    def test_unknown_creativity_level_rejected(self):
        opts = ContentGenerationOptions(creativity_level="extreme")
        with self.assertRaises(SchemaValidationError):
            opts.validate()

    def test_negative_number_of_variants_rejected(self):
        opts = ContentGenerationOptions(number_of_variants=-1)
        with self.assertRaises(SchemaValidationError):
            opts.validate()

    def test_non_bool_include_flag_rejected(self):
        opts = ContentGenerationOptions(include_hashtags="yes")  # type: ignore[arg-type]
        with self.assertRaises(SchemaValidationError):
            opts.validate()

    def test_max_caption_length_must_be_positive(self):
        opts = ContentGenerationOptions(max_caption_length=0)
        with self.assertRaises(SchemaValidationError):
            opts.validate()


if __name__ == "__main__":
    unittest.main()
