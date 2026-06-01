from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import tempfile
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.ai.schemas import (
    ContentGenerationInput,
    ContentGenerationOptions,
    GeneratedContentBundle,
)
from scripts.db.drafts import save_generated_bundle_to_drafts
from scripts.db.init_db import initialize_database
from scripts.db.settings import update_app_settings
from scripts.services.approval_queue import Actor, ApprovalQueueService
from scripts.services.content_generation import (
    ContentGenerationService,
    SettingsSnapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

GUARANTEE_MARKERS = (
    "guarantee",
    "guaranteed",
    "100% satisfaction",
    "we promise",
)
TESTIMONIAL_MARKERS = (
    "one customer said",
    "a client told",
    "real customer review",
    "verified customer",
    "a happy customer",
)


@dataclass(frozen=True)
class EvaluationResult:
    name: str
    passed: bool
    failures: list[str] = field(default_factory=list)
    platforms: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    blocking_flags: list[str] = field(default_factory=list)
    scheduling_error_codes: list[str] = field(default_factory=list)


def load_fixtures(fixtures_dir: str | Path = FIXTURES_DIR) -> list[dict[str, Any]]:
    root = Path(fixtures_dir)
    fixtures: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            decoded = json.load(handle)
        if isinstance(decoded, list):
            fixtures.extend(decoded)
        elif isinstance(decoded, dict):
            fixtures.append(decoded)
        else:
            raise ValueError(f"Fixture file {path} must contain an object or list.")
    return fixtures


def run_evaluations(fixtures_dir: str | Path = FIXTURES_DIR) -> list[EvaluationResult]:
    return [evaluate_fixture(fixture) for fixture in load_fixtures(fixtures_dir)]


def evaluate_fixture(fixture: dict[str, Any]) -> EvaluationResult:
    name = str(fixture.get("name") or "unnamed_fixture")
    expected = fixture.get("expected") or {}
    failures: list[str] = []

    try:
        bundle = _generate_bundle(fixture)
    except Exception as error:
        return EvaluationResult(
            name=name,
            passed=False,
            failures=[f"generation_failed: {error}"],
        )

    _check_bundle_structure(bundle, fixture, expected, failures)
    scheduling_error_codes = _maybe_check_scheduling(name, bundle, fixture, expected, failures)

    return EvaluationResult(
        name=name,
        passed=not failures,
        failures=failures,
        platforms=[post.platform for post in bundle.posts],
        flags=list(bundle.safety_review.flags),
        blocking_flags=list(bundle.safety_review.blocking_flags),
        scheduling_error_codes=scheduling_error_codes,
    )


def _generate_bundle(fixture: dict[str, Any]) -> GeneratedContentBundle:
    settings = fixture.get("settings") or {}
    service = ContentGenerationService(
        settings_loader=lambda: SettingsSnapshot(
            emergency_pause_enabled=bool(settings.get("emergencyPauseEnabled", False)),
            ai_provider_preference="mock",
        )
    )
    options_data = fixture.get("options") or {}
    options = ContentGenerationOptions(
        provider_name="mock",
        prompt_id=options_data.get("promptId", "platform_post_generator_v1"),
        number_of_variants=int(options_data.get("numberOfVariants", 0)),
        include_hashtags=bool(options_data.get("includeHashtags", True)),
        include_cta=bool(options_data.get("includeCta", True)),
        hashtag_count=int(options_data.get("hashtagCount", 5)),
    )
    input_data = ContentGenerationInput(
        brand_profile=fixture["brandProfile"],
        selected_media_assets=list(fixture.get("selectedMedia") or []),
        selected_platforms=list(fixture["selectedPlatforms"]),
        content_goal=fixture["contentGoal"],
        content_angle=fixture["contentAngle"],
        user_instructions=fixture.get("userInstructions"),
        campaign_name=fixture.get("campaignName"),
        offer_context=fixture.get("offerContext"),
        target_audience=fixture.get("targetAudience"),
    )
    return service.generate(input_data, options)


def _check_bundle_structure(
    bundle: GeneratedContentBundle,
    fixture: dict[str, Any],
    expected: dict[str, Any],
    failures: list[str],
) -> None:
    try:
        bundle.to_dict()
    except Exception as error:
        failures.append(f"schema_roundtrip_failed: {error}")

    requested_platforms = list(fixture["selectedPlatforms"])
    expected_outputs = list(expected.get("expectedPlatformOutputs") or requested_platforms)
    actual_platforms = [post.platform for post in bundle.posts]
    if actual_platforms != requested_platforms:
        failures.append(
            f"platforms_mismatch: expected {requested_platforms}, got {actual_platforms}"
        )
    if actual_platforms != expected_outputs:
        failures.append(
            f"expected_platform_outputs_mismatch: expected {expected_outputs}, got {actual_platforms}"
        )

    for post in bundle.posts:
        if not post.caption.strip():
            failures.append(f"{post.platform}: empty_caption")
        if expected.get("requireHooks") and not (post.hook and post.hook.strip()):
            failures.append(f"{post.platform}: missing_hook")
        if expected.get("expectHashtags") is True and not post.hashtags:
            failures.append(f"{post.platform}: missing_hashtags")
        if expected.get("expectHashtags") is False and post.hashtags:
            failures.append(f"{post.platform}: unexpected_hashtags")
        if expected.get("expectCta") is True and not post.call_to_action:
            failures.append(f"{post.platform}: missing_cta")
        if expected.get("expectCta") is False and post.call_to_action:
            failures.append(f"{post.platform}: unexpected_cta")
        if post.status != "needs_review":
            failures.append(f"{post.platform}: draft_status_not_needs_review")

    expected_flags = set(expected.get("safetyFlags") or [])
    actual_flags = set(bundle.safety_review.flags)
    missing_flags = sorted(expected_flags - actual_flags)
    if missing_flags:
        failures.append(f"missing_safety_flags: {missing_flags}")

    expected_blocking = set(expected.get("blockingFlags") or [])
    actual_blocking = set(bundle.safety_review.blocking_flags)
    missing_blocking = sorted(expected_blocking - actual_blocking)
    if missing_blocking:
        failures.append(f"missing_blocking_flags: {missing_blocking}")

    if expected.get("forbidUnflaggedGuarantees", True):
        _check_unflagged_markers(
            bundle,
            markers=GUARANTEE_MARKERS,
            expected_flag="unsupported_guarantee",
            failures=failures,
        )
    if expected.get("forbidUnflaggedTestimonials", True):
        _check_unflagged_markers(
            bundle,
            markers=TESTIMONIAL_MARKERS,
            expected_flag="fake_testimonial",
            failures=failures,
        )

    if not bundle.prompt_metadata.get("rendered_prompt_template_id"):
        failures.append("missing_prompt_template_metadata")
    if not bundle.prompt_metadata.get("rendered_prompt_version"):
        failures.append("missing_prompt_version_metadata")
    if bundle.generation_provider != "mock":
        failures.append("non_mock_provider_used")

    if len(bundle.posts) > 1:
        captions = {post.caption for post in bundle.posts}
        if len(captions) == 1:
            failures.append("platform_tone_difference_missing")
        for post in bundle.posts:
            label = _platform_label_fragment(post.platform)
            if label and label not in post.caption:
                failures.append(f"{post.platform}: platform_label_missing")


def _check_unflagged_markers(
    bundle: GeneratedContentBundle,
    *,
    markers: tuple[str, ...],
    expected_flag: str,
    failures: list[str],
) -> None:
    has_marker = any(
        marker in post.caption.lower()
        for marker in markers
        for post in bundle.posts
    )
    if has_marker and expected_flag not in bundle.safety_review.flags:
        failures.append(f"unflagged_marker: {expected_flag}")


def _platform_label_fragment(platform: str) -> str:
    return {
        "facebook": "Facebook draft",
        "instagram": "Instagram draft",
        "threads": "Threads draft",
        "youtube": "YouTube Shorts draft",
        "tiktok": "TikTok draft",
        "linkedin": "LinkedIn draft",
        "x": "X draft",
    }.get(platform, "")


def _maybe_check_scheduling(
    name: str,
    bundle: GeneratedContentBundle,
    fixture: dict[str, Any],
    expected: dict[str, Any],
    failures: list[str],
) -> list[str]:
    if "expectSchedulingEligible" not in expected:
        return []

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / f"{name}.sqlite"
        initialize_database(db_path)
        _seed_evaluation_database(db_path, fixture)
        if (fixture.get("settings") or {}).get("emergencyPauseEnabled"):
            update_app_settings(db_path, {"emergencyPauseEnabled": True})
        saved = save_generated_bundle_to_drafts(
            db_path,
            bundle,
            save_request_id=f"evaluation-{name}",
        )
        service = ApprovalQueueService(db_path)
        for draft in saved:
            service.approve(draft.id, actor=Actor(actorType="test", actorName="Prompt Eval"))
        all_codes: list[str] = []
        for draft in saved:
            result = service.check_scheduling_eligibility(draft.id)
            all_codes.extend(result.error_codes)
            if result.eligible != bool(expected["expectSchedulingEligible"]):
                failures.append(
                    f"{draft.platform}: scheduling_eligibility_expected_"
                    f"{expected['expectSchedulingEligible']}_got_{result.eligible}"
                )
        missing_codes = sorted(set(expected.get("schedulingErrorCodes") or []) - set(all_codes))
        if missing_codes:
            failures.append(f"missing_scheduling_error_codes: {missing_codes}")
        blocked_conditions = set(expected.get("blockedConditions") or [])
        missing_blocked_conditions = sorted(
            blocked_conditions
            - set(all_codes)
            - set(bundle.safety_review.flags)
            - set(bundle.safety_review.blocking_flags)
        )
        if missing_blocked_conditions:
            failures.append(
                f"missing_expected_blocked_conditions: {missing_blocked_conditions}"
            )
        return sorted(set(all_codes))


def _seed_evaluation_database(db_path: Path, fixture: dict[str, Any]) -> None:
    brand = fixture["brandProfile"]
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO brand_profiles (
              id,
              business_name,
              description,
              voice,
              services_json,
              locations_json,
              target_audience,
              supported_claims_json,
              blocked_phrases_json,
              preferences_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                brand["id"],
                brand.get("businessName") or "Evaluation Business",
                brand.get("description"),
                brand.get("voice") or brand.get("brandVoice"),
                json.dumps(brand.get("services") or []),
                json.dumps(brand.get("locations") or brand.get("serviceAreas") or []),
                brand.get("targetAudience"),
                json.dumps(brand.get("supportedClaims") or []),
                json.dumps(brand.get("blockedPhrases") or brand.get("bannedWords") or []),
                json.dumps({"evaluation": True}),
            ),
        )
        for asset in fixture.get("selectedMedia") or []:
            media_id = asset.get("id")
            if not media_id:
                continue
            connection.execute(
                """
                INSERT OR REPLACE INTO media_assets (
                  id,
                  media_type,
                  original_path,
                  file_name,
                  mime_type,
                  file_size_bytes,
                  tags_json,
                  job_context_json,
                  metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    asset.get("mediaType") or asset.get("media_type") or "image",
                    f"data/media/originals/{media_id}.jpg",
                    asset.get("fileName") or f"{media_id}.jpg",
                    asset.get("mimeType") or "image/jpeg",
                    int(asset.get("fileSizeBytes") or 1000),
                    json.dumps(asset.get("tags") or []),
                    json.dumps(asset.get("jobContext") or {}),
                    json.dumps(asset.get("metadata") or {}),
                ),
            )
        connection.commit()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deterministic mock prompt/content evaluations."
    )
    parser.add_argument(
        "--fixtures",
        default=str(FIXTURES_DIR),
        help="Directory containing prompt evaluation JSON fixture files.",
    )
    args = parser.parse_args()

    results = run_evaluations(args.fixtures)
    passed = 0
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.name}")
        if result.failures:
            for failure in result.failures:
                print(f"  - {failure}")
        if result.passed:
            passed += 1

    print(f"\n{passed}/{len(results)} prompt evaluation fixture(s) passed.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
