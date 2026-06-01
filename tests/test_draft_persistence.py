from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.ai.schemas import (
    GeneratedContentBundle,
    GeneratedPostSafetyReview,
    GeneratedPostScore,
    PlatformPostDraft,
)
from scripts.db.drafts import (
    DraftPersistenceError,
    DuplicateDraftSaveError,
    archive_generated_draft,
    approve_generated_draft,
    get_approval_history,
    get_generated_draft,
    list_generated_drafts,
    reject_generated_draft,
    request_generated_draft_revision,
    save_generated_bundle_to_drafts,
    update_generated_draft,
)
from scripts.db.init_db import initialize_database


def _insert_brand(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO brand_profiles (
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
            "brand-draft-test",
            "Draft Test Exterior Care",
            "Fake local service business for draft persistence tests.",
            "Helpful and practical.",
            json.dumps(["pressure washing"]),
            json.dumps(["Demo City"]),
            "local homeowners",
            json.dumps(["Uses careful surface checks before cleaning."]),
            json.dumps(["guaranteed results"]),
            json.dumps({"demo": True}),
        ),
    )


def _bundle() -> GeneratedContentBundle:
    return GeneratedContentBundle(
        brand_profile_id="brand-draft-test",
        content_idea_id="idea-driveway",
        prompt_id="platform_post_generator_v1",
        prompt_version="v1",
        generation_provider="mock",
        created_at="2026-05-26T15:00:00Z",
        prompt_metadata={
            "rendered_prompt_template_id": "platform_post_generator_v1",
            "rendered_prompt_version": "v1",
            "campaignName": "Spring curb appeal",
            "offerContext": "Ask about a demo estimate.",
            "userInstructions": "Keep it neighborly.",
        },
        provider_metadata={"provider": "mock", "model": "deterministic-local"},
        safety_review=GeneratedPostSafetyReview(
            flags=["aggressive_language"],
            blocking_flags=[],
            reviewer="local_rules",
            notes="Mock local safety review.",
            suggested_fixes=["Soften pressure language."],
        ),
        posts=[
            PlatformPostDraft(
                platform="instagram",
                headline="Fresh driveway moment",
                hook="A quick before and after for the feed.",
                caption="Demo draft caption for Instagram.",
                short_caption="Demo short caption.",
                long_caption="Demo long caption with more detail.",
                call_to_action="Ask about exterior cleaning options",
                hashtags=["#DemoPost", "#ExteriorCleaning"],
                media_asset_ids=["media-before", "media-after"],
                content_goal="show_transformation",
                content_angle="before_after",
                target_audience="local homeowners",
                suggested_post_time="2026-06-01T16:00:00Z",
                alt_text="Before and after driveway cleaning demo image.",
                notes="Generated locally with mock provider.",
                safety_flags=["aggressive_language"],
                score=GeneratedPostScore(
                    overall=82,
                    breakdown={"clarity": 85, "safety_match": 80},
                    rationale="Clear but CTA should stay gentle.",
                ),
                status="approved",
            ),
            PlatformPostDraft(
                platform="facebook",
                caption="Demo draft caption for Facebook.",
                hashtags=["#DemoPost"],
                media_asset_ids=["media-before"],
                content_goal="educate_customer",
                content_angle="educational",
                target_audience="homeowners",
                safety_flags=[],
                score=GeneratedPostScore(overall=75),
            ),
        ],
    )


class DraftPersistenceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        initialize_database(db_path)
        with closing(sqlite3.connect(db_path)) as connection:
            _insert_brand(connection)
            connection.execute(
                """
                INSERT INTO content_ideas (
                  id, brand_profile_id, goal, angle, target_platforms_json,
                  media_asset_ids_json, notes, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "idea-driveway",
                    "brand-draft-test",
                    "show_transformation",
                    "before_after",
                    json.dumps(["instagram", "facebook"]),
                    json.dumps(["media-before", "media-after"]),
                    "Demo idea.",
                    "open",
                ),
            )
            connection.commit()
        return db_path

    def test_save_generated_bundle_creates_needs_review_drafts_and_logs(self):
        db_path = self._database()

        saved = save_generated_bundle_to_drafts(
            db_path,
            _bundle(),
            selected_platforms=["instagram", "facebook"],
            save_request_id="save-drafts-test-1",
        )

        self.assertEqual(len(saved), 2)
        self.assertEqual([draft.platform for draft in saved], ["instagram", "facebook"])
        self.assertTrue(all(draft.approvalStatus == "needs_review" for draft in saved))

        with closing(sqlite3.connect(db_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT * FROM generated_posts ORDER BY platform DESC"
            ).fetchall()
            self.assertEqual(len(rows), 2)

            instagram = [row for row in rows if row["platform"] == "instagram"][0]
            self.assertEqual(instagram["approval_status"], "needs_review")
            self.assertEqual(instagram["headline"], "Fresh driveway moment")
            self.assertEqual(instagram["hook"], "A quick before and after for the feed.")
            self.assertEqual(
                instagram["call_to_action"], "Ask about exterior cleaning options"
            )
            self.assertEqual(instagram["content_goal"], "show_transformation")
            self.assertEqual(instagram["content_angle"], "before_after")
            self.assertEqual(instagram["campaign_name"], "Spring curb appeal")
            self.assertEqual(instagram["prompt_template_id"], "platform_post_generator_v1")
            self.assertEqual(instagram["prompt_version"], "v1")
            self.assertEqual(instagram["generation_timestamp"], "2026-05-26T15:00:00Z")
            self.assertEqual(
                json.loads(instagram["media_asset_ids_json"]),
                ["media-before", "media-after"],
            )
            self.assertEqual(
                json.loads(instagram["hashtags_json"]),
                ["#DemoPost", "#ExteriorCleaning"],
            )
            self.assertEqual(json.loads(instagram["safety_flags_json"]), ["aggressive_language"])
            self.assertEqual(json.loads(instagram["score_json"])["overall"], 82)

            prompt_metadata = json.loads(instagram["prompt_metadata_json"])
            self.assertEqual(prompt_metadata["saveRequestId"], "save-drafts-test-1")
            self.assertEqual(prompt_metadata["promptTemplateId"], "platform_post_generator_v1")
            self.assertEqual(prompt_metadata["promptVersion"], "v1")
            self.assertEqual(prompt_metadata["safetyReview"]["flags"], ["aggressive_language"])
            self.assertEqual(prompt_metadata["draft"]["statusBeforeSave"], "approved")
            self.assertEqual(prompt_metadata["draft"]["approvalStatus"], "needs_review")

            approval_logs = connection.execute(
                "SELECT * FROM approval_logs ORDER BY entity_id"
            ).fetchall()
            self.assertEqual(len(approval_logs), 2)
            self.assertTrue(
                all(log["action"] == "generated_saved_to_drafts" for log in approval_logs)
            )
            changed = json.loads(approval_logs[0]["changed_fields_json"])
            self.assertEqual(changed["approvalStatus"], "needs_review")
            self.assertEqual(changed["generationProvider"], "mock")
            self.assertEqual(changed["saveRequestId"], "save-drafts-test-1")

    def test_saved_drafts_can_be_listed_and_fetched(self):
        db_path = self._database()
        saved = save_generated_bundle_to_drafts(db_path, _bundle(), save_request_id="save-list")

        drafts = list_generated_drafts(db_path, approval_status="needs_review")
        self.assertEqual(len(drafts), 2)
        self.assertEqual(drafts[0].approvalStatus, "needs_review")

        fetched = get_generated_draft(db_path, saved[0].id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, saved[0].id)
        self.assertEqual(fetched.mediaAssetIds, saved[0].mediaAssetIds)
        self.assertEqual(fetched.promptTemplateId, "platform_post_generator_v1")

    def test_duplicate_save_request_is_rejected_without_extra_rows(self):
        db_path = self._database()
        save_generated_bundle_to_drafts(db_path, _bundle(), save_request_id="duplicate-token")

        with self.assertRaises(DuplicateDraftSaveError):
            save_generated_bundle_to_drafts(
                db_path,
                _bundle(),
                save_request_id="duplicate-token",
            )

        with closing(sqlite3.connect(db_path)) as connection:
            draft_count = connection.execute(
                "SELECT COUNT(*) FROM generated_posts"
            ).fetchone()[0]
            approval_count = connection.execute(
                "SELECT COUNT(*) FROM approval_logs"
            ).fetchone()[0]
        self.assertEqual(draft_count, 2)
        self.assertEqual(approval_count, 2)

    def test_invalid_bundle_fails_safely(self):
        db_path = self._database()

        with self.assertRaises(DraftPersistenceError):
            save_generated_bundle_to_drafts(db_path, object())

        with self.assertRaises(DraftPersistenceError):
            save_generated_bundle_to_drafts(
                db_path,
                _bundle(),
                selected_platforms=["x"],
                save_request_id="no-matching-platform",
            )

        with closing(sqlite3.connect(db_path)) as connection:
            draft_count = connection.execute(
                "SELECT COUNT(*) FROM generated_posts"
            ).fetchone()[0]
            approval_count = connection.execute(
                "SELECT COUNT(*) FROM approval_logs"
            ).fetchone()[0]
        self.assertEqual(draft_count, 0)
        self.assertEqual(approval_count, 0)

    def test_status_actions_update_draft_and_create_approval_logs(self):
        db_path = self._database()
        saved = save_generated_bundle_to_drafts(db_path, _bundle(), save_request_id="status-actions")
        first, second = saved

        approved = approve_generated_draft(db_path, first.id, actor_label="owner")
        self.assertEqual(approved.approvalStatus, "approved")

        rejected = reject_generated_draft(
            db_path,
            second.id,
            reason="Photo does not match the current offer.",
            actor_label="owner",
        )
        self.assertEqual(rejected.approvalStatus, "rejected")

        revision = request_generated_draft_revision(
            db_path,
            first.id,
            instructions="Make the CTA softer.",
            actor_label="owner",
        )
        self.assertEqual(revision.approvalStatus, "revision_requested")

        archived = archive_generated_draft(
            db_path,
            second.id,
            reason="Keep for history, but do not use.",
            actor_label="owner",
        )
        self.assertEqual(archived.approvalStatus, "archived")

        first_history = get_approval_history(db_path, first.id)
        actions = [entry["action"] for entry in first_history]
        self.assertIn("approved", actions)
        self.assertIn("revision_requested", actions)
        self.assertTrue(all(entry["entity_type"] == "generated_post" for entry in first_history))

        second_history = get_approval_history(db_path, second.id)
        second_actions = [entry["action"] for entry in second_history]
        self.assertIn("rejected", second_actions)
        self.assertIn("archived", second_actions)

    def test_editing_approved_draft_returns_it_to_needs_review(self):
        db_path = self._database()
        saved = save_generated_bundle_to_drafts(db_path, _bundle(), save_request_id="edit-approved")
        draft = approve_generated_draft(db_path, saved[0].id, actor_label="owner")
        self.assertEqual(draft.approvalStatus, "approved")

        edited = update_generated_draft(
            db_path,
            draft.id,
            {
                "caption": "Updated caption after owner review.",
                "headline": "Updated headline",
                "hashtags": ["#Updated", "#Demo"],
                "notes": "Owner changed approved copy.",
            },
            actor_label="owner",
        )

        self.assertEqual(edited.approvalStatus, "needs_review")
        self.assertEqual(edited.caption, "Updated caption after owner review.")
        self.assertEqual(edited.hashtags, ["#Updated", "#Demo"])

        history = get_approval_history(db_path, draft.id)
        actions = [entry["action"] for entry in history]
        self.assertIn("edited_requires_reapproval", actions)
        changed = [
            entry for entry in history if entry["action"] == "edited_requires_reapproval"
        ][0]["changed_fields"]
        self.assertEqual(changed["approvalStatus"], "needs_review")
        self.assertIn("caption", changed["editedFields"])

    def test_list_generated_drafts_filters_platform_status_and_search(self):
        db_path = self._database()
        save_generated_bundle_to_drafts(db_path, _bundle(), save_request_id="filters")

        instagram = list_generated_drafts(db_path, platform="instagram")
        self.assertEqual(len(instagram), 1)
        self.assertEqual(instagram[0].platform, "instagram")

        caption_results = list_generated_drafts(db_path, search="facebook")
        self.assertEqual(len(caption_results), 1)
        self.assertEqual(caption_results[0].platform, "facebook")

        hook_results = list_generated_drafts(db_path, search="quick before")
        self.assertEqual(len(hook_results), 1)
        self.assertEqual(hook_results[0].platform, "instagram")


if __name__ == "__main__":
    unittest.main()
