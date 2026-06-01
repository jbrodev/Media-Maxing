import socket
import unittest
from unittest import mock

from scripts.ai.providers.mock import MOCK_MODEL_ID, MOCK_PROMPT_VERSION, MockProvider
from scripts.ai.schemas import (
    AIStructuredGenerationRequest,
    AIStructuredGenerationResponse,
    AITextGenerationRequest,
    AITextGenerationResponse,
    ContentGenerationInput,
    ContentGenerationOptions,
    GeneratedContentBundle,
    GeneratedPostSafetyReview,
    PlatformPostDraft,
    SchemaValidationError,
)


def _input(**overrides) -> ContentGenerationInput:
    base = {
        "brand_profile": {
            "id": "brand-north-star",
            "businessName": "North Star Exterior Demo",
            "voice": "Helpful, neighborly, practical.",
            "services": ["pressure washing", "soft washing"],
            "supportedClaims": ["Uses careful surface checks before cleaning."],
            "targetAudience": "local homeowners",
        },
        "content_goal": "show_transformation",
        "content_angle": "before_after",
        "selected_platforms": ["instagram", "facebook"],
        "selected_media_assets": [
            {"id": "media-driveway-before", "tags": ["before"]},
            {"id": "media-driveway-after", "tags": ["after"]},
        ],
        "user_instructions": "Keep claims supportable. Mention the seasonal angle.",
        "content_idea_id": "idea-driveway-transformation",
    }
    base.update(overrides)
    return ContentGenerationInput(**base)


class MockProviderDeterminismTest(unittest.TestCase):
    def test_two_runs_produce_identical_output(self):
        provider = MockProvider()
        first = provider.generate_bundle(_input(), ContentGenerationOptions())
        second = provider.generate_bundle(_input(), ContentGenerationOptions())

        self.assertEqual(first.to_dict(), second.to_dict())

    def test_changing_input_changes_fingerprint(self):
        provider = MockProvider()
        baseline = provider.generate_bundle(_input(), ContentGenerationOptions())
        different_angle = provider.generate_bundle(
            _input(content_angle="educational"), ContentGenerationOptions()
        )

        self.assertNotEqual(
            baseline.provider_metadata["input_fingerprint"],
            different_angle.provider_metadata["input_fingerprint"],
        )


class MockProviderOutputShapeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = MockProvider().generate_bundle(
            _input(), ContentGenerationOptions()
        )

    def test_returns_generated_content_bundle(self):
        self.assertIsInstance(self.bundle, GeneratedContentBundle)

    def test_one_draft_per_requested_platform(self):
        self.assertEqual(len(self.bundle.drafts), 2)
        platforms = [draft.platform for draft in self.bundle.drafts]
        self.assertEqual(platforms, ["instagram", "facebook"])
        for draft in self.bundle.drafts:
            self.assertIsInstance(draft, PlatformPostDraft)

    def test_drafts_use_brand_fields(self):
        for draft in self.bundle.drafts:
            self.assertIn("North Star Exterior Demo", draft.caption)
            self.assertIn("Audience: local homeowners", draft.caption)

    def test_media_asset_ids_attached_to_each_draft(self):
        for draft in self.bundle.drafts:
            self.assertEqual(
                draft.media_asset_ids,
                ["media-driveway-before", "media-driveway-after"],
            )

    def test_hashtags_are_deterministic_and_well_formed(self):
        first_draft = self.bundle.drafts[0]
        second_draft = self.bundle.drafts[1]
        # Hashtags depend on brand + angle, not on the platform string, so they
        # should be identical across the two drafts for the same brand/angle.
        self.assertEqual(first_draft.hashtags, second_draft.hashtags)
        for tag in first_draft.hashtags:
            self.assertTrue(tag.startswith("#"))

    def test_prompt_metadata_populated(self):
        self.assertEqual(self.bundle.prompt_id, "platform_post_generator_v1")
        self.assertEqual(self.bundle.prompt_version, MOCK_PROMPT_VERSION)

    def test_generation_provider_is_mock(self):
        self.assertEqual(self.bundle.generation_provider, "mock")

    def test_provider_metadata_marks_deterministic(self):
        self.assertIs(self.bundle.provider_metadata.get("deterministic"), True)
        self.assertIs(self.bundle.provider_metadata.get("mock"), True)
        self.assertIn("input_fingerprint", self.bundle.provider_metadata)

    def test_safety_review_present_with_list_flags(self):
        review = self.bundle.safety_review
        self.assertIsInstance(review, GeneratedPostSafetyReview)
        self.assertIsInstance(review.flags, list)
        self.assertEqual(review.flags, [])
        self.assertEqual(review.blocking_flags, [])

    def test_content_idea_id_propagated(self):
        self.assertEqual(self.bundle.content_idea_id, "idea-driveway-transformation")


class MockProviderCaptionVariantsTest(unittest.TestCase):
    def test_variants_are_generated_when_requested(self):
        options = ContentGenerationOptions(
            number_of_variants=2,
        )
        bundle = MockProvider().generate_bundle(_input(), options)
        for draft in bundle.drafts:
            self.assertEqual(len(draft.caption_variants), 2)
            for variant in draft.caption_variants:
                self.assertTrue(variant.text)
                self.assertTrue(variant.style)

    def test_no_variants_by_default(self):
        bundle = MockProvider().generate_bundle(_input(), ContentGenerationOptions())
        for draft in bundle.drafts:
            self.assertEqual(draft.caption_variants, [])

    def test_max_caption_length_truncates(self):
        options = ContentGenerationOptions(max_caption_length=40)
        bundle = MockProvider().generate_bundle(_input(), options)
        for draft in bundle.drafts:
            self.assertLessEqual(len(draft.caption), 40)


class MockProviderValidationTest(unittest.TestCase):
    def test_unknown_platform_rejected(self):
        bogus = _input(selected_platforms=["myspace"])
        with self.assertRaises(SchemaValidationError):
            MockProvider().generate_bundle(bogus, ContentGenerationOptions())

    def test_unknown_goal_rejected(self):
        bogus = _input(content_goal="world_domination")
        with self.assertRaises(SchemaValidationError):
            MockProvider().generate_bundle(bogus, ContentGenerationOptions())

    def test_missing_brand_id_rejected(self):
        bogus = ContentGenerationInput(
            brand_profile={"businessName": "No-ID Demo"},
            content_goal="build_trust",
            content_angle="trust_builder",
            selected_platforms=["facebook"],
        )
        with self.assertRaises(SchemaValidationError):
            MockProvider().generate_bundle(bogus, ContentGenerationOptions())


class MockProviderTextGenerationTest(unittest.TestCase):
    def _request(self, **overrides) -> AITextGenerationRequest:
        base = {
            "prompt": "Write a one-paragraph reminder about seasonal gutter cleaning.",
            "system": "You are a helpful local-service marketing assistant.",
        }
        base.update(overrides)
        return AITextGenerationRequest(**base)

    def test_returns_text_generation_response(self):
        response = MockProvider().generate_text(self._request())
        self.assertIsInstance(response, AITextGenerationResponse)
        self.assertEqual(response.provider, "mock")
        self.assertEqual(response.model, MOCK_MODEL_ID)
        self.assertTrue(response.is_mock)
        self.assertEqual(response.finish_reason, "stop")

    def test_text_is_labeled_as_mock(self):
        response = MockProvider().generate_text(self._request())
        self.assertIn("[MOCK DRAFT]", response.text)
        self.assertIn("deterministic mock response", response.text)

    def test_text_includes_prompt_excerpt(self):
        response = MockProvider().generate_text(self._request())
        self.assertIn("seasonal gutter cleaning", response.text)

    def test_text_is_deterministic(self):
        first = MockProvider().generate_text(self._request())
        second = MockProvider().generate_text(self._request())
        self.assertEqual(first.text, second.text)
        self.assertEqual(
            first.metadata["fingerprint"], second.metadata["fingerprint"]
        )

    def test_changing_prompt_changes_fingerprint(self):
        first = MockProvider().generate_text(self._request())
        second = MockProvider().generate_text(self._request(prompt="Different prompt entirely."))
        self.assertNotEqual(
            first.metadata["fingerprint"], second.metadata["fingerprint"]
        )

    def test_max_tokens_truncates_response(self):
        response = MockProvider().generate_text(self._request(max_tokens=10))
        # max_tokens=10 -> ~40 chars heuristic; allow either the truncated
        # version or the full body shorter than the cap.
        self.assertLessEqual(len(response.text), 40)

    def test_empty_prompt_rejected(self):
        with self.assertRaises(SchemaValidationError):
            MockProvider().generate_text(AITextGenerationRequest(prompt="   "))


class MockProviderStructuredGenerationTest(unittest.TestCase):
    def _request(self, **overrides) -> AIStructuredGenerationRequest:
        base = {
            "prompt": "Draft a single Instagram post about an exterior cleaning service.",
            "schema_name": "platform_post_draft",
        }
        base.update(overrides)
        return AIStructuredGenerationRequest(**base)

    def test_returns_structured_response(self):
        response = MockProvider().generate_structured(self._request())
        self.assertIsInstance(response, AIStructuredGenerationResponse)
        self.assertEqual(response.provider, "mock")
        self.assertTrue(response.is_mock)
        self.assertEqual(response.schema_name, "platform_post_draft")

    def test_known_schemas_return_specific_fields(self):
        provider = MockProvider()

        post = provider.generate_structured(self._request())
        self.assertIn("caption", post.data["fields"])
        self.assertIn("hashtags", post.data["fields"])

        hashtags = provider.generate_structured(
            self._request(schema_name="hashtag_set")
        )
        self.assertIn("hashtags", hashtags.data["fields"])

        safety = provider.generate_structured(
            self._request(schema_name="safety_review")
        )
        self.assertEqual(safety.data["fields"]["flags"], [])
        self.assertEqual(safety.data["fields"]["blocking_flags"], [])
        self.assertEqual(safety.data["fields"]["reviewer"], "local_rules")

    def test_reply_suggestion_schema_returns_safe_intent_specific_fields(self):
        response = MockProvider().generate_structured(
            self._request(
                schema_name="reply_suggestion",
                metadata={"intent": "price_request", "tone": "friendly"},
            )
        )
        fields = response.data["fields"]
        self.assertEqual(fields["recommendedAction"], "invite_to_message")
        self.assertNotRegex(fields["suggestedReply"], r"\$\d+")
        self.assertTrue(fields["needsHumanReview"])
        self.assertEqual(fields["tone"], "friendly")

    def test_unknown_schema_returns_generic_demo_fields(self):
        response = MockProvider().generate_structured(
            self._request(schema_name="something_brand_new")
        )
        self.assertEqual(response.data["schema_name"], "something_brand_new")
        self.assertIn("headline", response.data["fields"])
        self.assertTrue(response.data["is_demo"])

    def test_structured_is_deterministic(self):
        first = MockProvider().generate_structured(self._request())
        second = MockProvider().generate_structured(self._request())
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_missing_schema_name_rejected(self):
        with self.assertRaises(SchemaValidationError):
            MockProvider().generate_structured(
                AIStructuredGenerationRequest(prompt="x", schema_name=" ")
            )


class MockProviderNoNetworkTest(unittest.TestCase):
    """The mock provider must not open any sockets."""

    def test_no_socket_open_during_generation(self):
        original_socket = socket.socket
        original_create_connection = socket.create_connection

        def _explode(*args, **kwargs):
            raise AssertionError("MockProvider must not perform network I/O.")

        with mock.patch.object(socket, "socket", _explode), mock.patch.object(
            socket, "create_connection", _explode
        ):
            provider = MockProvider()
            bundle = provider.generate_bundle(_input(), ContentGenerationOptions())
            text = provider.generate_text(
                AITextGenerationRequest(prompt="A small prompt.")
            )
            structured = provider.generate_structured(
                AIStructuredGenerationRequest(
                    prompt="A small prompt.",
                    schema_name="platform_post_draft",
                )
            )

        # Sanity: make sure we restored the originals (the with-block does this).
        self.assertIs(socket.socket, original_socket)
        self.assertIs(socket.create_connection, original_create_connection)
        self.assertEqual(bundle.generation_provider, "mock")
        self.assertTrue(text.is_mock)
        self.assertTrue(structured.is_mock)


if __name__ == "__main__":
    unittest.main()
