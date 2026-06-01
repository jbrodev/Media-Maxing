from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen

from apps.api.local_server import (
    LocalApiApplication,
    LocalApiError,
    LocalApiHttpServer,
)
from scripts.db.seed_demo import DEMO_BRAND_ID, seed_demo_database


class LocalApiServerTest(unittest.TestCase):
    def _application(self) -> LocalApiApplication:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        db_path = Path(temp_dir.name) / "app.sqlite"
        seed_demo_database(db_path)
        return LocalApiApplication(db_path)

    def test_health_and_bootstrap_are_local_only_and_token_safe(self):
        app = self._application()

        health = app.dispatch("GET", "/api/health").body
        bootstrap = app.dispatch("GET", "/api/bootstrap").body
        serialized = json.dumps(bootstrap).lower()

        self.assertTrue(health["ok"])
        self.assertFalse(health["realPublishing"])
        self.assertFalse(health["realReplySending"])
        self.assertTrue(bootstrap["localOnly"])
        self.assertNotIn("encrypted_access_token", serialized)
        self.assertNotIn("encrypted_refresh_token", serialized)
        self.assertNotIn("authorization_code", serialized)
        self.assertIn("integrationSetup", bootstrap)

    def test_integration_setup_route_masks_server_side_secret_values(self):
        app = self._application()

        with patch.dict(
            "os.environ",
            {
                "META_CLIENT_ID": "local-client-id",
                "META_CLIENT_SECRET": "local-secret-must-not-leak",
                "META_REDIRECT_URI": "http://127.0.0.1:8000/api/connect/facebook/callback",
            },
            clear=False,
        ):
            setup = app.dispatch("GET", "/api/integration-setup").body

        serialized = json.dumps(setup)
        facebook_vars = setup["platforms"]["facebook"]["envVars"]
        self.assertNotIn("local-secret-must-not-leak", serialized)
        self.assertEqual(
            facebook_vars["META_CLIENT_SECRET"]["displayValue"],
            "Configured, hidden",
        )

    def test_settings_brand_analytics_memory_and_weekly_report_persist(self):
        app = self._application()

        settings = app.dispatch(
            "PATCH",
            "/api/settings",
            body={"appName": "Owner Local Manager"},
        ).body
        brand = app.dispatch(
            "PATCH",
            f"/api/brand-profiles/{DEMO_BRAND_ID}",
            body={"tagline": "Careful local exterior service"},
        ).body
        snapshot = app.dispatch(
            "POST",
            "/api/analytics/snapshots",
            body={
                "brand_profile_id": DEMO_BRAND_ID,
                "platform": "facebook",
                "snapshot_date": "2026-06-11",
                "generated_post_id": "demo-post-gutter-reminder",
                "metrics": {"impressions": 100, "likes": 4, "leads": 1},
            },
        ).body
        memory = app.dispatch(
            "POST",
            "/api/ai-memory/refresh",
            body={"brand_profile_id": DEMO_BRAND_ID},
        ).body
        archived_memory = app.dispatch(
            "POST",
            f"/api/ai-memory/{memory['memories'][0]['id']}/archive",
            body={},
        ).body
        report = app.dispatch(
            "POST",
            "/api/weekly-reports",
            body={
                "brand_profile_id": DEMO_BRAND_ID,
                "week_start_date": "2026-06-08",
            },
        ).body
        reloaded = app.dispatch("GET", "/api/bootstrap").body

        self.assertEqual(settings["appName"], "Owner Local Manager")
        self.assertEqual(brand["tagline"], "Careful local exterior service")
        self.assertEqual(snapshot["source"], "manual")
        self.assertGreaterEqual(memory["createdCount"], 1)
        self.assertEqual(archived_memory["status"], "archived")
        self.assertEqual(report["weekStartDate"], "2026-06-08")
        self.assertEqual(reloaded["settings"]["appName"], "Owner Local Manager")
        self.assertEqual(
            reloaded["brandProfile"]["tagline"],
            "Careful local exterior service",
        )
        self.assertTrue(any(item["id"] == snapshot["id"] for item in reloaded["analyticsSnapshots"]))

    def test_engagement_reply_workflow_persists_in_sqlite(self):
        app = self._application()

        ingested = app.dispatch(
            "POST",
            "/api/engagement/mock",
            body={"brand_profile_id": DEMO_BRAND_ID},
        ).body
        suggestion = app.dispatch(
            "POST",
            "/api/engagement/mock-engagement-praise-comment/suggestions",
            body={},
        ).body
        approved = app.dispatch(
            "POST",
            f"/api/reply-suggestions/{suggestion['id']}/approve",
            body={},
        ).body
        app.dispatch(
            "POST",
            "/api/engagement/mock-engagement-complaint/status",
            body={"status": "escalated"},
        )
        reloaded = app.dispatch("GET", "/api/bootstrap").body

        self.assertEqual(ingested["createdCount"], 8)
        self.assertEqual(approved["status"], "approved")
        inbox = {item["id"]: item for item in reloaded["engagementItems"]}
        self.assertEqual(inbox["mock-engagement-praise-comment"]["status"], "reply_approved")
        self.assertEqual(inbox["mock-engagement-complaint"]["status"], "escalated")
        self.assertTrue(
            any(entry["action"] == "approve" for entry in reloaded["replyApprovals"])
        )

    def test_generated_bundle_save_persists_once_and_rejects_duplicate(self):
        app = self._application()
        bundle = {
            "brandProfileId": DEMO_BRAND_ID,
            "posts": [
                {
                    "platform": "facebook",
                    "headline": "Local SQLite preview",
                    "hook": "A careful local update.",
                    "caption": "A validated browser preview saved through the localhost SQLite bridge.",
                    "hashtags": ["#LocalBusiness"],
                    "mediaAssetIds": [],
                    "contentGoal": "build_trust",
                    "contentAngle": "trust_builder",
                    "safetyFlags": [],
                    "status": "needs_review",
                }
            ],
            "promptId": "platform_post_generator_v1",
            "promptVersion": "v1",
            "generationProvider": "mock",
            "promptMetadata": {"renderFormat": "structured-mock-browser"},
            "providerMetadata": {"mock": True},
            "safetyReview": {
                "flags": [],
                "blockingFlags": [],
                "reviewer": "local_rules",
                "notes": "Local validation test.",
                "suggestedFixes": [],
            },
            "createdAt": "2026-06-01T12:00:00Z",
        }

        saved = app.dispatch(
            "POST",
            "/api/drafts/save-generated",
            body={"bundle": bundle, "save_request_id": "local-api-save-once"},
        ).body
        reloaded = app.dispatch("GET", "/api/bootstrap").body

        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0]["approvalStatus"], "needs_review")
        self.assertTrue(any(item["id"] == saved[0]["id"] for item in reloaded["drafts"]))
        self.assertTrue(
            any(
                entry["action"] == "generated_saved_to_drafts"
                for entry in reloaded["approvalLogs"][saved[0]["id"]]
            )
        )
        with self.assertRaises(LocalApiError):
            app.dispatch(
                "POST",
                "/api/drafts/save-generated",
                body={"bundle": bundle, "save_request_id": "local-api-save-once"},
            )

    def test_content_generation_uses_sqlite_brand_media_and_active_memory(self):
        app = self._application()

        bundle = app.dispatch(
            "POST",
            "/api/content-generation",
            body={
                "input": {
                    "brandProfileId": DEMO_BRAND_ID,
                    "contentGoal": "show_transformation",
                    "contentAngle": "before_after",
                    "selectedPlatforms": ["instagram", "facebook"],
                    "selectedMediaIds": ["demo-media-driveway-before"],
                    "userInstructions": "Keep the message practical.",
                }
            },
        ).body

        self.assertEqual(bundle["generationProvider"], "mock")
        self.assertEqual(
            [post["platform"] for post in bundle["posts"]],
            ["instagram", "facebook"],
        )
        self.assertTrue(bundle["saveRequestId"].startswith("generation-"))
        self.assertGreaterEqual(bundle["promptMetadata"]["activeAiMemoryCount"], 1)
        self.assertEqual(
            bundle["promptMetadata"]["renderedPromptTemplateId"],
            "platform_post_generator_v1",
        )
        self.assertEqual(
            bundle["posts"][0]["mediaAssetIds"],
            ["demo-media-driveway-before"],
        )

    def test_draft_calendar_queue_and_media_actions_persist(self):
        app = self._application()

        edited = app.dispatch(
            "PATCH",
            "/api/drafts/demo-post-gutter-reminder",
            body={"caption": "Reviewed local caption for scheduling."},
        ).body
        approved = app.dispatch(
            "POST",
            "/api/drafts/demo-post-gutter-reminder/approval",
            body={"action": "approve"},
        ).body
        scheduled = app.dispatch(
            "POST",
            "/api/drafts/demo-post-gutter-reminder/schedule",
            body={
                "scheduled_for": "2027-06-10T14:00:00Z",
                "timezone": "America/New_York",
                "user_notes": "Local bridge scheduling test.",
            },
        ).body
        bootstrap = app.dispatch("GET", "/api/bootstrap").body
        queue = next(
            item
            for item in bootstrap["publishQueueItems"]
            if item["scheduledPostId"] == scheduled["id"]
        )
        preflight = app.dispatch(
            "POST",
            f"/api/publish-queue/{queue['id']}/preflight",
            body={},
        ).body
        completion = app.dispatch(
            "POST",
            f"/api/publish-queue/{queue['id']}/mark-manually-exported",
            body={},
        ).body
        media = app.dispatch(
            "PATCH",
            "/api/media/demo-media-driveway-before",
            body={"title": "SQLite bridge title", "usageStatus": "reviewed"},
        ).body
        reloaded = app.dispatch("GET", "/api/bootstrap").body

        self.assertEqual(edited["approvalStatus"], "needs_review")
        self.assertEqual(approved["approvalStatus"], "approved")
        self.assertEqual(preflight["eligible"], True)
        self.assertEqual(completion["queueStatus"], "manually_exported")
        self.assertEqual(media["title"], "SQLite bridge title")
        queue_reloaded = next(
            item for item in reloaded["publishQueueItems"] if item["id"] == queue["id"]
        )
        scheduled_reloaded = next(
            item for item in reloaded["scheduledPosts"] if item["id"] == scheduled["id"]
        )
        self.assertEqual(queue_reloaded["queueStatus"], "manually_exported")
        self.assertEqual(scheduled_reloaded["status"], "completed")
        self.assertTrue(
            any(
                item["title"] == "SQLite bridge title"
                for item in reloaded["mediaAssets"]
            )
        )

    def test_calendar_attention_insight_and_mock_connector_actions_persist(self):
        app = self._application()

        app.dispatch(
            "POST",
            "/api/drafts/demo-post-gutter-reminder/approval",
            body={"action": "approve"},
        )
        scheduled = app.dispatch(
            "POST",
            "/api/drafts/demo-post-gutter-reminder/schedule",
            body={
                "scheduled_for": "2027-06-10T14:00:00Z",
                "timezone": "America/New_York",
            },
        ).body
        attention = app.dispatch(
            "POST",
            f"/api/calendar/{scheduled['id']}/needs-attention",
            body={},
        ).body
        insight = app.dispatch(
            "PATCH",
            "/api/analytics/insights/demo-insight-before-after",
            body={"status": "applied"},
        ).body
        connected = app.dispatch(
            "POST",
            "/api/connect/youtube/mock-connect",
            body={},
        ).body
        account_id = connected["account"]["id"]
        checked = app.dispatch(
            "POST",
            "/api/connect/youtube/validate",
            body={"socialAccountId": account_id},
        ).body
        disconnected = app.dispatch(
            "POST",
            "/api/connect/youtube/disconnect",
            body={"socialAccountId": account_id},
        ).body
        reloaded = app.dispatch("GET", "/api/bootstrap").body

        self.assertEqual(attention["status"], "needs_attention")
        self.assertEqual(insight["status"], "applied")
        self.assertTrue(connected["success"])
        self.assertEqual(checked["socialAccountId"], account_id)
        self.assertTrue(disconnected["success"])
        account = next(item for item in reloaded["connectedAccounts"] if item["id"] == account_id)
        self.assertEqual(account["connectionStatus"], "disconnected")
        queue = next(
            item
            for item in reloaded["publishQueueItems"]
            if item["scheduledPostId"] == scheduled["id"]
        )
        self.assertEqual(queue["queueStatus"], "blocked")
        self.assertIn("needs_attention", queue["preflightErrors"])

    def test_unknown_route_returns_safe_error(self):
        app = self._application()

        with self.assertRaises(LocalApiError) as context:
            app.dispatch("GET", "/api/not-a-route")

        self.assertEqual(context.exception.status, 404)
        self.assertIn("route_not_found", context.exception.error_codes)

    def test_http_server_serves_static_app_and_health_on_loopback(self):
        app = self._application()
        server = LocalApiHttpServer(("127.0.0.1", 0), app)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        with urlopen(f"{base_url}/api/health", timeout=5) as response:
            health = json.loads(response.read().decode("utf-8"))
        with urlopen(f"{base_url}/", timeout=5) as response:
            html = response.read().decode("utf-8")

        self.assertTrue(health["ok"])
        self.assertIn('<script src="./api-client.js"></script>', html)
        self.assertIn("Local Social AI Manager", html)

    def test_http_server_serializes_connector_health_safely(self):
        app = self._application()
        server = LocalApiHttpServer(("127.0.0.1", 0), app)
        self.addCleanup(server.server_close)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        connect_request = Request(
            f"{base_url}/api/connect/youtube/mock-connect",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(connect_request, timeout=5) as response:
            connected = json.loads(response.read().decode("utf-8"))
        validate_request = Request(
            f"{base_url}/api/connect/youtube/validate",
            data=json.dumps({"socialAccountId": connected["account"]["id"]}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(validate_request, timeout=5) as response:
            health = json.loads(response.read().decode("utf-8"))

        self.assertEqual(health["socialAccountId"], connected["account"]["id"])
        self.assertIsInstance(health["featureStatus"], str)
        self.assertNotIn("encryptedAccessToken", json.dumps(health))

    def test_http_server_refuses_non_loopback_binding(self):
        app = self._application()

        with self.assertRaises(ValueError):
            LocalApiHttpServer(("0.0.0.0", 0), app)


if __name__ == "__main__":
    unittest.main()
