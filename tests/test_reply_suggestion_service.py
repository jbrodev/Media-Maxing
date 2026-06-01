import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.ai.providers.mock import MockProvider
from scripts.ai.schemas import (
    AIStructuredGenerationResponse,
    ReplySafetyFlag,
    ReplySuggestionOutput,
    SchemaValidationError,
)
from scripts.db.seed_demo import DEMO_BRAND_ID, seed_demo_database
from scripts.services.engagement import EngagementService
from scripts.services.reply_suggestions import (
    ReplySuggestionService,
    ReplySuggestionServiceError,
)


class ReplySuggestionSchemaTest(unittest.TestCase):
    def test_valid_reply_output(self):
        output = ReplySuggestionOutput(
            suggested_reply="Thanks for the kind words.",
            tone="friendly",
            confidence="high",
            safety_flags=[],
            blocking_flags=[],
            recommended_action="reply",
            needs_human_review=True,
            reason_summary="Friendly thank-you draft for owner review.",
        )

        self.assertEqual(output.recommended_action, "reply")
        self.assertTrue(output.needs_human_review)

    def test_invalid_action_rejected(self):
        with self.assertRaises(SchemaValidationError):
            ReplySuggestionOutput(
                suggested_reply="A reply.",
                tone="friendly",
                confidence="high",
                recommended_action="send_now",
                reason_summary="Invalid action fixture.",
            )

    def test_invalid_severity_rejected(self):
        with self.assertRaises(SchemaValidationError):
            ReplySafetyFlag(
                code="unsupported_guarantee",
                severity="severe",
                message="Invalid severity fixture.",
            )

    def test_blocking_flag_must_be_visible(self):
        with self.assertRaises(SchemaValidationError):
            ReplySuggestionOutput(
                suggested_reply="A reply.",
                tone="friendly",
                confidence="high",
                safety_flags=[],
                blocking_flags=["unsupported_guarantee"],
                recommended_action="reply",
                reason_summary="Invalid blocking fixture.",
            )

    def test_empty_reply_allowed_for_spam(self):
        output = ReplySuggestionOutput(
            suggested_reply="",
            tone="neutral",
            confidence="high",
            recommended_action="mark_spam",
            reason_summary="Spam should not receive an outward reply.",
        )

        self.assertEqual(output.suggested_reply, "")


class MalformedReplyProvider(MockProvider):
    def generate_structured(self, request):
        return AIStructuredGenerationResponse(
            data={"fields": {"suggestedReply": "Incomplete provider output."}},
            schema_name=request.schema_name,
            provider="mock",
            is_mock=True,
        )


class ReplySuggestionServiceTest(unittest.TestCase):
    def _database(self) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        seed_demo_database(db_path)
        EngagementService(db_path).ingest_mock_engagement(brand_profile_id=DEMO_BRAND_ID)
        return db_path

    def test_praise_comment_gets_friendly_local_draft(self):
        suggestion = ReplySuggestionService(self._database()).generate(
            engagement_item_id="mock-engagement-praise-comment"
        )

        self.assertEqual(suggestion.recommendedAction, "reply")
        self.assertIn("Thank you", suggestion.suggestedReply)
        self.assertTrue(suggestion.needsHumanReview)
        self.assertEqual(suggestion.status, "generated")

    def test_pricing_question_invites_estimate_without_inventing_price(self):
        suggestion = ReplySuggestionService(self._database()).generate(
            engagement_item_id="mock-engagement-pricing-question"
        )

        self.assertEqual(suggestion.recommendedAction, "invite_to_message")
        self.assertIn("estimate", suggestion.suggestedReply.lower())
        self.assertNotRegex(suggestion.suggestedReply, r"\$\d+")

    def test_booking_request_does_not_invent_availability(self):
        suggestion = ReplySuggestionService(self._database()).generate(
            engagement_item_id="mock-engagement-booking-request"
        )

        self.assertEqual(suggestion.recommendedAction, "ask_for_more_info")
        self.assertNotIn("available tomorrow", suggestion.suggestedReply.lower())

    def test_complaint_is_empathetic_and_escalated(self):
        suggestion = ReplySuggestionService(self._database()).generate(
            engagement_item_id="mock-engagement-complaint"
        )

        self.assertEqual(suggestion.recommendedAction, "escalate")
        self.assertIn("sorry", suggestion.suggestedReply.lower())

    def test_spam_recommends_no_outward_reply(self):
        suggestion = ReplySuggestionService(self._database()).generate(
            engagement_item_id="mock-engagement-spam"
        )

        self.assertEqual(suggestion.recommendedAction, "mark_spam")
        self.assertEqual(suggestion.suggestedReply, "")

    def test_urgent_lead_keeps_person_in_loop(self):
        suggestion = ReplySuggestionService(self._database()).generate(
            engagement_item_id="mock-engagement-urgent-lead-message"
        )

        self.assertEqual(suggestion.recommendedAction, "escalate")
        self.assertIn("person", suggestion.suggestedReply.lower())

    def test_generation_updates_inbox_status_and_writes_audit(self):
        db_path = self._database()
        suggestion = ReplySuggestionService(db_path).generate(
            engagement_item_id="mock-engagement-general-comment"
        )

        with closing(sqlite3.connect(db_path)) as connection:
            item_status = connection.execute(
                "SELECT status FROM engagement_items WHERE id = ?",
                ("mock-engagement-general-comment",),
            ).fetchone()[0]
            audit = connection.execute(
                """
                SELECT action, previous_status, new_status, actor_type
                FROM reply_approvals
                WHERE reply_suggestion_id = ?
                """,
                (suggestion.id,),
            ).fetchone()
        self.assertEqual(item_status, "reply_suggested")
        self.assertEqual(audit, ("suggest", "needs_reply", "reply_suggested", "ai"))

    def test_regeneration_preserves_history(self):
        db_path = self._database()
        service = ReplySuggestionService(db_path)
        first = service.generate(engagement_item_id="mock-engagement-general-comment")
        second = service.generate(engagement_item_id="mock-engagement-general-comment")

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(len(service.list_for_engagement("mock-engagement-general-comment")), 2)

    def test_unsupported_guarantee_request_is_visible_and_blocking(self):
        db_path = self._database()
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute(
                """
                INSERT INTO engagement_items (
                  id, brand_profile_id, platform, item_type, direction,
                  content, content_redacted, received_at, sentiment, intent,
                  priority, status, requires_response, source
                ) VALUES (?, ?, 'facebook', 'comment', 'inbound', ?, ?,
                  '2026-06-01T12:00:00Z', 'neutral', 'question', 'normal',
                  'needs_reply', 1, 'manual')
                """,
                (
                    "manual-guarantee-question",
                    DEMO_BRAND_ID,
                    "Can you guarantee the cleaning result?",
                    "Can you guarantee the cleaning result?",
                ),
            )
            connection.commit()

        suggestion = ReplySuggestionService(db_path).generate(
            engagement_item_id="manual-guarantee-question"
        )

        self.assertIn("unsupported_guarantee", suggestion.blockingFlags)
        self.assertTrue(
            any(
                flag["code"] == "unsupported_guarantee"
                and flag["severity"] == "critical"
                for flag in suggestion.safetyReview
            )
        )

    def test_malformed_provider_output_rolls_back_all_writes(self):
        db_path = self._database()
        service = ReplySuggestionService(db_path, provider=MalformedReplyProvider())

        with self.assertRaises(ReplySuggestionServiceError):
            service.generate(engagement_item_id="mock-engagement-general-comment")

        with closing(sqlite3.connect(db_path)) as connection:
            suggestion_count = connection.execute(
                "SELECT COUNT(*) FROM reply_suggestions"
            ).fetchone()[0]
            audit_count = connection.execute(
                "SELECT COUNT(*) FROM reply_approvals"
            ).fetchone()[0]
            item_status = connection.execute(
                "SELECT status FROM engagement_items WHERE id = ?",
                ("mock-engagement-general-comment",),
            ).fetchone()[0]
        self.assertEqual(suggestion_count, 0)
        self.assertEqual(audit_count, 0)
        self.assertEqual(item_status, "needs_reply")

    def test_cli_prints_safe_metadata_only(self):
        db_path = self._database()

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.services.reply_suggestions",
                "--database",
                str(db_path),
                "--engagement-item-id",
                "mock-engagement-praise-comment",
            ],
            capture_output=True,
            check=False,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("reply_suggestion_created=", result.stdout)
        self.assertIn("recommended_action=reply", result.stdout)
        self.assertIn("provider=mock", result.stdout)
        self.assertIn("real_reply_send=false", result.stdout)
        self.assertNotIn("Thank you", result.stdout)


if __name__ == "__main__":
    unittest.main()
