from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SCRIPT = REPO_ROOT / "apps" / "web" / "settings.js"


class WebMediaLibraryScreenTest(unittest.TestCase):
    def test_media_library_screen_contains_required_controls_and_states(self):
        html = WEB_INDEX.read_text(encoding="utf-8")
        script = WEB_SCRIPT.read_text(encoding="utf-8")

        required_ids = [
            "media-view",
            "media-import-input",
            "media-import-button",
            "media-search",
            "media-type-filter",
            "media-status-filter",
            "media-grid",
            "media-detail-panel",
            "media-metadata-form",
            "media-title",
            "media-description",
            "media-tags",
            "media-serviceType",
            "media-locationName",
            "media-city",
            "media-state",
            "media-projectDate",
            "media-contentAngle",
            "media-qualityRating",
            "media-usageStatus",
            "media-notes",
            "media-metadata-error",
            "media-metadata-success",
            "media-loading-state",
            "media-error-state",
            "media-empty-state",
            "media-count",
        ]

        for element_id in required_ids:
            self.assertIn(f'id="{element_id}"', html)

        self.assertIn("Grid view", html)
        self.assertIn("ready_for_generation", html)
        self.assertIn("reviewed", html)
        self.assertIn("Local-only import", html)
        self.assertIn("MEDIA_STORAGE_KEY", script)
        self.assertIn("defaultMediaAssets", script)
        self.assertIn("setupMediaLibrary", script)
        self.assertIn("renderMediaLibrary", script)
        self.assertIn("filterMediaAssets", script)
        self.assertIn("openMediaDetailPanel", script)
        self.assertIn("saveMediaMetadata", script)
        self.assertIn("qualityRating", script)
        self.assertIn("before_after", script)
        self.assertIn("used_in_draft", script)

    def test_media_library_demo_adapter_has_seed_like_media_and_safety_limits(self):
        script = WEB_SCRIPT.read_text(encoding="utf-8")

        expected_demo_filenames = [
            "demo-driveway-before.jpg",
            "demo-driveway-after.jpg",
            "demo-gutter-cleaning.jpg",
            "demo-team-setup.mp4",
            "demo-seasonal-reminder.jpg",
        ]

        for filename in expected_demo_filenames:
            self.assertIn(filename, script)

        self.assertIn("image", script)
        self.assertIn("video", script)
        self.assertIn("Unsupported file type", script)
        self.assertIn("Files are stored only in this browser demo", script)
        self.assertIn("accept=\"image/*,video/*\"", WEB_INDEX.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
