"""Tests for ContentGenerationService.

Required scenarios:
1. Happy path with one media asset and Instagram/Facebook.
2. Multi-platform generation.
3. Missing brand profile (incomplete + no loader).
4. Unsupported platform.
5. Safety flag example (uses a stub provider that emits risky text).
6. Emergency pause example.
"""

from __future__ import annotations

import unittest

from scripts.ai.providers.base import AIProvider
from scripts.ai.schemas import (
    AIStructuredGenerationRequest,
    AIStructuredGenerationResponse,
    AITextGenerationRequest,
    AITextGenerationResponse,
    ContentGenerationInput,
    ContentGenerationOptions,
    GeneratedContentBundle,
    PlatformPostDraft,
    SchemaValidationError,
)
from scripts.services.content_generation import (
    ContentGenerationError,
    ContentGenerationService,
    SettingsSnapshot,
    generate_content,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _brand(**overrides):
    base = {
        "id": "brand-test",
        "businessName": "Brightside Exterior Care Demo",
        "voice": "Helpful, neighborly, practical.",
        "services": ["pressure washing", "soft washing"],
        "supportedClaims": ["Uses careful surface checks before cleaning."],
        "blockedPhrases": ["guaranteed results"],
        "targetAudience": "local homeowners",
        "locations": ["Demo City"],
    }
    base.update(overrides)
    return base


def _input(**overrides) -> ContentGenerationInput:
    base = dict(
        brand_profile=_brand(),
        content_goal="show_transformation",
        content_angle="before_after",
        selected_platforms=["instagram"],
        selected_media_assets=[{"id": "media-driveway-before", "tags": ["before"]}],
        user_instructions="Keep claims supportable.",
    )
    base.update(overrides)
    return ContentGenerationInput(**base)


class _StubProvider(AIProvider):
    """Provider that returns whatever bundle the test supplies."""

    name = "mock"
    label = "Stub for tests"
    requires_network = False

    def __init__(self, bundle_factory):
        self._bundle_factory = bundle_factory

    def generate_text(self, request: AITextGenerationRequest) -> AITextGenerationResponse:
        raise NotImplementedError

    def generate_structured(
        self, request: AIStructuredGenerationRequest
    ) -> AIStructuredGenerationResponse:
        raise NotImplementedError

    def generate_bundle(self, input, options):
        return self._bundle_factory(input, options)


def _risky_bundle(input, options):
    return GeneratedContentBundle(
        brand_profile_id=input.brand_profile_id(),
        posts=[
            PlatformPostDraft(
                platform="facebook",
                caption=(
                    "Act now! We guarantee a spotless driveway. "
                    "Auto-approved by the system."
                ),
                hashtags=["#Mock"],
                media_asset_ids=["media-1"],
            ),
        ],
        prompt_id="platform_post_generator_v1",
        prompt_version="v1",
        generation_provider="mock",
    )


# ---------------------------------------------------------------------------
# Scenario 1: Happy path with one media asset on Instagram + Facebook.
# ---------------------------------------------------------------------------


class HappyPathTest(unittest.TestCase):
    def test_happy_path_single_platform(self):
        service = ContentGenerationService()
        bundle = service.generate(_input(selected_platforms=["instagram"]))
        self.assertEqual(len(bundle.posts), 1)
        self.assertEqual(bundle.posts[0].platform, "instagram")
        self.assertEqual(bundle.posts[0].status, "needs_review")
        self.assertEqual(bundle.generation_provider, "mock")
        self.assertEqual(bundle.safety_review.flags, [])
        self.assertEqual(bundle.safety_review.blocking_flags, [])

    def test_happy_path_instagram_and_facebook(self):
        bundle = ContentGenerationService().generate(
            _input(selected_platforms=["instagram", "facebook"])
        )
        platforms = [post.platform for post in bundle.posts]
        self.assertEqual(platforms, ["instagram", "facebook"])
        for post in bundle.posts:
            self.assertIn(_brand()["businessName"], post.caption)
            self.assertEqual(post.media_asset_ids, ["media-driveway-before"])
            self.assertIn("local homeowners", post.caption)

    def test_bundle_prompt_metadata_includes_render_info(self):
        bundle = ContentGenerationService().generate(_input())
        self.assertEqual(
            bundle.prompt_metadata.get("rendered_prompt_template_id"),
            "platform_post_generator_v1",
        )
        self.assertEqual(bundle.prompt_metadata.get("rendered_prompt_version"), "v1")
        self.assertGreater(bundle.prompt_metadata.get("rendered_prompt_chars", 0), 0)


# ---------------------------------------------------------------------------
# Scenario 2: Multi-platform generation.
# ---------------------------------------------------------------------------


class MultiPlatformTest(unittest.TestCase):
    def test_one_draft_per_requested_platform(self):
        bundle = ContentGenerationService().generate(
            _input(selected_platforms=["instagram", "facebook", "threads", "linkedin", "x"])
        )
        platforms = [post.platform for post in bundle.posts]
        self.assertEqual(platforms, ["instagram", "facebook", "threads", "linkedin", "x"])
        for post in bundle.posts:
            self.assertEqual(post.status, "needs_review")
            self.assertTrue(post.caption)

    def test_all_seven_platforms(self):
        bundle = ContentGenerationService().generate(
            _input(
                selected_platforms=[
                    "instagram",
                    "facebook",
                    "threads",
                    "tiktok",
                    "youtube",
                    "linkedin",
                    "x",
                ]
            )
        )
        self.assertEqual(len(bundle.posts), 7)


# ---------------------------------------------------------------------------
# Scenario 3: Missing brand profile.
# ---------------------------------------------------------------------------


class MissingBrandProfileTest(unittest.TestCase):
    def test_incomplete_brand_profile_without_loader_raises(self):
        bare_input = ContentGenerationInput(
            brand_profile={"id": "brand-missing"},
            content_goal="build_trust",
            content_angle="trust_builder",
            selected_platforms=["facebook"],
        )
        service = ContentGenerationService()
        with self.assertRaises(ContentGenerationError) as raised:
            service.generate(bare_input)
        self.assertIn("brand-missing", str(raised.exception))
        self.assertIn("brand_loader", str(raised.exception))

    def test_incomplete_brand_profile_loaded_via_brand_loader(self):
        def loader(brand_id):
            self.assertEqual(brand_id, "brand-missing")
            return _brand(id="brand-missing", businessName="Loaded Demo Business")

        service = ContentGenerationService(brand_loader=loader)
        bundle = service.generate(
            ContentGenerationInput(
                brand_profile={"id": "brand-missing"},
                content_goal="build_trust",
                content_angle="trust_builder",
                selected_platforms=["facebook"],
            )
        )
        self.assertEqual(bundle.brand_profile_id, "brand-missing")
        self.assertIn("Loaded Demo Business", bundle.posts[0].caption)

    def test_brand_loader_returns_nothing_raises(self):
        service = ContentGenerationService(brand_loader=lambda _id: None)
        with self.assertRaises(ContentGenerationError):
            service.generate(
                ContentGenerationInput(
                    brand_profile={"id": "brand-missing"},
                    content_goal="build_trust",
                    content_angle="trust_builder",
                    selected_platforms=["facebook"],
                )
            )


# ---------------------------------------------------------------------------
# Scenario 4: Unsupported platform.
# ---------------------------------------------------------------------------


class UnsupportedPlatformTest(unittest.TestCase):
    def test_unsupported_platform_rejected_at_input_validation(self):
        with self.assertRaises(SchemaValidationError) as raised:
            ContentGenerationService().generate(_input(selected_platforms=["myspace"]))
        self.assertIn("selected_platforms", str(raised.exception))

    def test_empty_platforms_rejected(self):
        with self.assertRaises(SchemaValidationError):
            ContentGenerationService().generate(_input(selected_platforms=[]))


# ---------------------------------------------------------------------------
# Scenario 5: Safety flag example (stub provider emits risky caption).
# ---------------------------------------------------------------------------


class SafetyFlagTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ContentGenerationService(provider=_StubProvider(_risky_bundle))

    def test_risky_caption_is_flagged_and_blocking(self):
        bundle = self.service.generate(_input(selected_platforms=["facebook"]))
        review = bundle.safety_review
        self.assertIn("unsupported_guarantee", review.flags)
        self.assertIn("missing_approval", review.flags)
        self.assertIn("aggressive_language", review.flags)
        # Aggressive language is informational; the others are blocking.
        self.assertIn("unsupported_guarantee", review.blocking_flags)
        self.assertIn("missing_approval", review.blocking_flags)
        self.assertNotIn("aggressive_language", review.blocking_flags)
        # blocking ⊆ flags invariant holds.
        self.assertTrue(set(review.blocking_flags).issubset(set(review.flags)))

    def test_per_post_safety_flags_match_review(self):
        bundle = self.service.generate(_input(selected_platforms=["facebook"]))
        post_flags = set(bundle.posts[0].safety_flags)
        self.assertEqual(post_flags, set(bundle.safety_review.flags))

    def test_blocked_brand_phrase_is_caught_end_to_end(self):
        def risky_with_blocked_phrase(input, options):
            return GeneratedContentBundle(
                brand_profile_id=input.brand_profile_id(),
                posts=[
                    PlatformPostDraft(
                        platform="facebook",
                        caption="We have guaranteed results for every job.",
                    )
                ],
                prompt_id="platform_post_generator_v1",
                prompt_version="v1",
                generation_provider="mock",
            )

        service = ContentGenerationService(
            provider=_StubProvider(risky_with_blocked_phrase),
        )
        bundle = service.generate(_input(selected_platforms=["facebook"]))
        # The brand fixture blocks "guaranteed results", which should flag
        # both brand_mismatch and unsupported_guarantee.
        self.assertIn("brand_mismatch", bundle.safety_review.blocking_flags)
        self.assertIn("unsupported_guarantee", bundle.safety_review.blocking_flags)


# ---------------------------------------------------------------------------
# Scenario 6: Emergency pause.
# ---------------------------------------------------------------------------


class EmergencyPauseTest(unittest.TestCase):
    def test_pause_adds_informational_flag(self):
        service = ContentGenerationService(
            settings_loader=lambda: SettingsSnapshot(emergency_pause_enabled=True),
        )
        bundle = service.generate(_input())
        self.assertIn("emergency_pause_conflict", bundle.safety_review.flags)
        # Non-blocking: generation still completes under pause.
        self.assertNotIn("emergency_pause_conflict", bundle.safety_review.blocking_flags)
        self.assertEqual(len(bundle.posts), 1)
        self.assertIn("Emergency pause", bundle.safety_review.notes)

    def test_no_pause_no_flag(self):
        service = ContentGenerationService(
            settings_loader=lambda: SettingsSnapshot(emergency_pause_enabled=False),
        )
        bundle = service.generate(_input())
        self.assertNotIn("emergency_pause_conflict", bundle.safety_review.flags)

    def test_duck_typed_settings_object_accepted(self):
        class CamelSettings:
            emergencyPauseEnabled = True
            aiProviderPreference = "mock"

        service = ContentGenerationService(settings_loader=lambda: CamelSettings())
        bundle = service.generate(_input())
        self.assertIn("emergency_pause_conflict", bundle.safety_review.flags)


# ---------------------------------------------------------------------------
# Convenience function.
# ---------------------------------------------------------------------------


class ConvenienceFunctionTest(unittest.TestCase):
    def test_generate_content_one_shot(self):
        bundle = generate_content(_input())
        self.assertEqual(len(bundle.posts), 1)
        self.assertEqual(bundle.generation_provider, "mock")


# ---------------------------------------------------------------------------
# Media loader behavior.
# ---------------------------------------------------------------------------


class MediaLoaderTest(unittest.TestCase):
    def test_id_only_assets_call_loader(self):
        loaded_calls: list[list[str]] = []

        def loader(ids):
            loaded_calls.append(list(ids))
            return [{"id": "m-1", "stage": "before"}, {"id": "m-2", "stage": "after"}]

        service = ContentGenerationService(media_loader=loader)
        bundle = service.generate(
            _input(selected_media_assets=[{"id": "m-1"}, {"id": "m-2"}])
        )
        self.assertEqual(loaded_calls, [["m-1", "m-2"]])
        self.assertEqual(bundle.posts[0].media_asset_ids, ["m-1", "m-2"])

    def test_complete_assets_skip_loader(self):
        loader_calls: list[list[str]] = []

        def loader(ids):
            loader_calls.append(list(ids))
            return []

        service = ContentGenerationService(media_loader=loader)
        service.generate(
            _input(selected_media_assets=[{"id": "m-1", "tags": ["before"]}])
        )
        self.assertEqual(loader_calls, [])


if __name__ == "__main__":
    unittest.main()
