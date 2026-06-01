import json
import unittest

from scripts.ai.prompts import (
    PromptDefinitionError,
    PromptInputSpec,
    PromptRegistryError,
    PromptRenderError,
    PromptTemplate,
    REQUIRED_SECTIONS,
    get_prompt,
    list_prompt_ids,
    list_prompts,
    list_versions_for_family,
)


REQUIRED_TEMPLATE_IDS = (
    "content_strategy_brief_v1",
    "platform_post_generator_v1",
    "caption_variants_generator_v1",
    "hashtag_generator_v1",
    "safety_review_v1",
    "draft_improvement_v1",
    "comment_reply_suggestion_v1",
)


def _platform_post_inputs(**overrides):
    base = {
        "business_name": "Brightside Exterior Care Demo",
        "brand_voice": "Helpful, neighborly, practical.",
        "services": ["pressure washing", "gutter cleaning"],
        "supported_claims": ["uses careful surface checks before cleaning"],
        "blocked_phrases": ["guaranteed results", "best in town"],
        "target_audience": "Local homeowners",
        "locations": ["Demo City"],
        "content_goal": "show_transformation",
        "content_angle": "before_after",
        "media_notes": ["id: media-driveway-before; stage: before"],
        "user_instructions": "Keep it honest. Mention seasonal timing.",
        "requested_platforms": ["instagram", "facebook"],
    }
    base.update(overrides)
    return base


class RegistryContentsTest(unittest.TestCase):
    def test_all_required_templates_are_registered(self):
        ids = list_prompt_ids()
        for prompt_id in REQUIRED_TEMPLATE_IDS:
            with self.subTest(prompt_id=prompt_id):
                self.assertIn(prompt_id, ids)

    def test_get_prompt_returns_matching_template(self):
        for prompt_id in REQUIRED_TEMPLATE_IDS:
            with self.subTest(prompt_id=prompt_id):
                template = get_prompt(prompt_id)
                self.assertIsInstance(template, PromptTemplate)
                self.assertEqual(template.id, prompt_id)

    def test_list_prompts_returns_all(self):
        all_templates = list_prompts()
        self.assertEqual(len(all_templates), len(REQUIRED_TEMPLATE_IDS))
        ids = {template.id for template in all_templates}
        self.assertEqual(ids, set(REQUIRED_TEMPLATE_IDS))

    def test_list_versions_for_family(self):
        versions = list_versions_for_family("platform_post_generator")
        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0].id, "platform_post_generator_v1")
        self.assertEqual(versions[0].version, "v1")
        self.assertEqual(versions[0].family, "platform_post_generator")

    def test_unknown_prompt_raises(self):
        with self.assertRaises(PromptRegistryError):
            get_prompt("does_not_exist_v9")


class TemplateShapeTest(unittest.TestCase):
    """Every required template must have all section headers, safety rules,
    declared inputs, and metadata."""

    def test_each_template_has_required_sections(self):
        for prompt_id in REQUIRED_TEMPLATE_IDS:
            template = get_prompt(prompt_id)
            for section in REQUIRED_SECTIONS:
                with self.subTest(prompt_id=prompt_id, section=section):
                    self.assertIn(section, template.template)

    def test_each_template_has_safety_rules_and_metadata(self):
        for prompt_id in REQUIRED_TEMPLATE_IDS:
            template = get_prompt(prompt_id)
            with self.subTest(prompt_id=prompt_id):
                self.assertGreater(len(template.safety_rules), 0)
                self.assertTrue(template.description)
                self.assertTrue(template.output_contract)
                self.assertTrue(template.created_at)
                self.assertTrue(template.expected_inputs)

    def test_metadata_snapshot_does_not_include_full_body(self):
        template = get_prompt("platform_post_generator_v1")
        metadata = template.to_metadata()
        for value in metadata.values():
            self.assertNotIn(template.template, repr(value))


class PlatformPostGeneratorContentTest(unittest.TestCase):
    """The platform_post_generator_v1 template must encode every required behavior."""

    def setUp(self) -> None:
        self.template = get_prompt("platform_post_generator_v1")
        self.body = self.template.template

    def test_lists_every_supported_platform(self):
        for platform in (
            "facebook",
            "instagram",
            "threads",
            "tiktok",
            "youtube",
            "linkedin",
            "x",
        ):
            with self.subTest(platform=platform):
                self.assertIn(platform, self.body)

    def test_uses_requested_platforms_input(self):
        self.assertIn("Requested platforms", self.body)
        self.assertIn("requested_platforms", {spec.name for spec in self.template.expected_inputs})

    def test_constraint_phrases_present(self):
        required_phrases = [
            "Do not invent",
            "Do not invent testimonials",
            "Do not promise guaranteed results",
            "licenses",
            "Do not publish",
            "brand profile and media metadata",
            "[unknown]",
            "call-to-action",
            "platform-specific tone and length",
        ]
        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.body)
        # "draft only" must appear at least once (case-insensitive).
        self.assertIn("draft only", self.body.lower())


class RenderingTest(unittest.TestCase):
    def test_render_succeeds_with_all_inputs(self):
        rendered = get_prompt("platform_post_generator_v1").render(
            _platform_post_inputs()
        )
        self.assertIn("Brightside Exterior Care Demo", rendered)
        self.assertIn("pressure washing", rendered)
        self.assertIn("instagram", rendered)

    def test_render_with_missing_required_raises(self):
        inputs = _platform_post_inputs()
        del inputs["business_name"]
        with self.assertRaises(PromptRenderError) as raised:
            get_prompt("platform_post_generator_v1").render(inputs)
        self.assertIn("business_name", str(raised.exception))

    def test_render_with_unknown_variable_raises(self):
        inputs = _platform_post_inputs()
        inputs["totally_unknown"] = "boom"
        with self.assertRaises(PromptRenderError) as raised:
            get_prompt("platform_post_generator_v1").render(inputs)
        self.assertIn("totally_unknown", str(raised.exception))

    def test_optional_inputs_render_as_placeholder(self):
        inputs = _platform_post_inputs()
        del inputs["brand_voice"]
        del inputs["user_instructions"]
        rendered = get_prompt("platform_post_generator_v1").render(inputs)
        self.assertIn("[not provided]", rendered)

    def test_list_inputs_render_as_bullets(self):
        rendered = get_prompt("platform_post_generator_v1").render(
            _platform_post_inputs(services=["pressure washing", "gutter cleaning"])
        )
        self.assertIn("- pressure washing", rendered)
        self.assertIn("- gutter cleaning", rendered)

    def test_empty_list_renders_as_none_listed(self):
        rendered = get_prompt("platform_post_generator_v1").render(
            _platform_post_inputs(supported_claims=[])
        )
        self.assertIn("[none listed]", rendered)

    def test_render_with_no_args_raises_for_required(self):
        with self.assertRaises(PromptRenderError):
            get_prompt("platform_post_generator_v1").render({})

    def test_render_is_deterministic(self):
        first = get_prompt("platform_post_generator_v1").render(_platform_post_inputs())
        second = get_prompt("platform_post_generator_v1").render(_platform_post_inputs())
        self.assertEqual(first, second)


class CrossTemplateRenderTest(unittest.TestCase):
    """Every required template should be renderable with realistic inputs."""

    def _required_only(self, template: PromptTemplate):
        sample = {
            "business_name": "Sample Local Service Demo",
            "services": ["service one"],
            "content_goal": "build_trust",
            "content_angle": "trust_builder",
            "requested_platforms": ["facebook"],
            "platform": "facebook",
            "original_caption": "Sample caption text for tests.",
            "owner_feedback": "Make it shorter.",
            "variant_count": 2,
            "hashtag_count": 3,
            "draft_caption": "Sample draft caption.",
            "engagement_type": "comment",
            "engagement_body": "Hello, do you serve my area?",
            "planning_window": "next 7 days",
        }
        return {
            spec.name: sample[spec.name]
            for spec in template.expected_inputs
            if spec.required and spec.name in sample
        }

    def test_every_required_template_renders_with_required_only(self):
        for prompt_id in REQUIRED_TEMPLATE_IDS:
            template = get_prompt(prompt_id)
            inputs = self._required_only(template)
            missing = [name for name in template.required_input_names() if name not in inputs]
            with self.subTest(prompt_id=prompt_id):
                self.assertEqual(
                    missing,
                    [],
                    f"Test fixture is missing required input(s) for {prompt_id}: {missing}",
                )
                rendered = template.render(inputs)
                self.assertGreater(len(rendered), 0)
                for section in REQUIRED_SECTIONS:
                    self.assertIn(section, rendered)


class TemplateDefinitionTest(unittest.TestCase):
    """Construction-time validation should catch malformed templates."""

    _BASE_BODY = """\
ROLE
Test.

GOAL
Test.

CONTEXT
Business: {{ business_name }}

INPUTS
None.

CONSTRAINTS
None.

SAFETY RULES
None.

OUTPUT FORMAT
None.

ACCEPTANCE CRITERIA
None.
"""

    def test_template_with_undeclared_placeholder_fails(self):
        with self.assertRaises(PromptDefinitionError):
            PromptTemplate(
                id="x_v1",
                name="X",
                version="v1",
                description="d",
                expected_inputs=(),  # business_name not declared
                output_contract="o",
                safety_rules=("rule",),
                template=self._BASE_BODY,
            )

    def test_template_missing_required_input_in_body_fails(self):
        body = self._BASE_BODY.replace("{{ business_name }}", "static")
        with self.assertRaises(PromptDefinitionError):
            PromptTemplate(
                id="x_v1",
                name="X",
                version="v1",
                description="d",
                expected_inputs=(
                    PromptInputSpec(name="business_name", description="d"),
                ),
                output_contract="o",
                safety_rules=("rule",),
                template=body,
            )

    def test_template_missing_section_header_fails(self):
        body = self._BASE_BODY.replace("ACCEPTANCE CRITERIA", "DONE")
        with self.assertRaises(PromptDefinitionError):
            PromptTemplate(
                id="x_v1",
                name="X",
                version="v1",
                description="d",
                expected_inputs=(
                    PromptInputSpec(name="business_name", description="d"),
                ),
                output_contract="o",
                safety_rules=("rule",),
                template=body,
            )

    def test_template_id_must_end_with_version(self):
        with self.assertRaises(PromptDefinitionError):
            PromptTemplate(
                id="something_else",
                name="X",
                version="v1",
                description="d",
                expected_inputs=(
                    PromptInputSpec(name="business_name", description="d"),
                ),
                output_contract="o",
                safety_rules=("rule",),
                template=self._BASE_BODY,
            )

    def test_template_must_have_at_least_one_safety_rule(self):
        with self.assertRaises(PromptDefinitionError):
            PromptTemplate(
                id="x_v1",
                name="X",
                version="v1",
                description="d",
                expected_inputs=(
                    PromptInputSpec(name="business_name", description="d"),
                ),
                output_contract="o",
                safety_rules=(),
                template=self._BASE_BODY,
            )


class JsonSerializableMetadataTest(unittest.TestCase):
    def test_every_template_metadata_is_json_serializable(self):
        for prompt_id in REQUIRED_TEMPLATE_IDS:
            template = get_prompt(prompt_id)
            with self.subTest(prompt_id=prompt_id):
                payload = json.dumps(template.to_metadata())
                self.assertIn(prompt_id, payload)


if __name__ == "__main__":
    unittest.main()
