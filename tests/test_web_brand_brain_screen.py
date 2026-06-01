from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_INDEX = REPO_ROOT / "apps" / "web" / "index.html"
WEB_SCRIPT = REPO_ROOT / "apps" / "web" / "settings.js"


class WebBrandBrainScreenTest(unittest.TestCase):
    def test_brand_brain_screen_contains_required_fields_and_adapter(self):
        html = WEB_INDEX.read_text(encoding="utf-8")
        script = WEB_SCRIPT.read_text(encoding="utf-8")

        required_ids = [
            "brand-view",
            "brand-brain-form",
            "brand-businessName",
            "brand-tagline",
            "brand-industry",
            "brand-description",
            "brand-services",
            "brand-serviceAreas",
            "brand-targetCustomers",
            "brand-brandVoice",
            "brand-toneRules",
            "brand-bannedWords",
            "brand-preferredWords",
            "brand-commonCTAs",
            "brand-hashtags",
            "brand-website",
            "brand-phone",
            "brand-email",
            "brand-approvalRules",
            "brand-safetyRules",
            "brand-examplePosts",
            "brand-error",
            "brand-success",
        ]

        for element_id in required_ids:
            self.assertIn(f'id="{element_id}"', html)

        self.assertIn("Business memory", html)
        self.assertIn("Temporary browser Brand Brain adapter", html)
        self.assertIn("Add item", html)
        self.assertIn("BRAND_STORAGE_KEY", script)
        self.assertIn("setupBrandBrainForm", script)
        self.assertIn("localStorage", script)
        self.assertIn("businessName is required", script)


if __name__ == "__main__":
    unittest.main()
