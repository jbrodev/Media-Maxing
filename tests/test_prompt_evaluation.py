from __future__ import annotations

import unittest
from pathlib import Path

from scripts.evaluations.prompt_evaluation import (
    FIXTURES_DIR,
    load_fixtures,
    run_evaluations,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


class PromptEvaluationFixtureTest(unittest.TestCase):
    def test_docs_and_required_fixture_cases_exist(self):
        docs_path = REPO_ROOT / "docs" / "prompt-evaluation.md"
        self.assertTrue(docs_path.exists())

        fixtures = load_fixtures(FIXTURES_DIR)
        fixture_names = {fixture["name"] for fixture in fixtures}

        expected_names = {
            "local_service_before_after_transformation",
            "educational_faq_post",
            "promotional_offer_post",
            "behind_the_scenes_post",
            "trust_building_post",
            "seasonal_reminder_post",
            "missing_brand_profile_fields",
            "media_with_weak_metadata",
            "unsupported_guarantee_request",
            "fake_testimonial_request",
            "emergency_pause_enabled",
            "multi_platform_generation",
        }
        self.assertTrue(expected_names.issubset(fixture_names))
        self.assertGreaterEqual(len(fixtures), 12)

        for fixture in fixtures:
            with self.subTest(fixture=fixture["name"]):
                self.assertIn("brandProfile", fixture)
                self.assertIn("selectedMedia", fixture)
                self.assertIn("selectedPlatforms", fixture)
                self.assertIn("contentGoal", fixture)
                self.assertIn("contentAngle", fixture)
                self.assertIn("expected", fixture)


class PromptEvaluationRunnerTest(unittest.TestCase):
    def test_all_mock_prompt_evaluations_pass(self):
        results = run_evaluations(FIXTURES_DIR)
        failures = [result for result in results if not result.passed]

        self.assertEqual(
            failures,
            [],
            "\n".join(
                f"{result.name}: {', '.join(result.failures)}" for result in failures
            ),
        )

        by_name = {result.name: result for result in results}
        self.assertIn("unsupported_guarantee", by_name["unsupported_guarantee_request"].flags)
        self.assertIn("fake_testimonial", by_name["fake_testimonial_request"].flags)
        self.assertIn(
            "emergency_pause_conflict",
            by_name["emergency_pause_enabled"].flags,
        )
        self.assertIn(
            "emergency_pause_enabled",
            by_name["emergency_pause_enabled"].scheduling_error_codes,
        )
        self.assertEqual(
            by_name["multi_platform_generation"].platforms,
            ["facebook", "instagram", "linkedin", "x"],
        )


if __name__ == "__main__":
    unittest.main()
