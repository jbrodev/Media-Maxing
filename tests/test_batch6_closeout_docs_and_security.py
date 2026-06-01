from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.qa.integration_security_scan import scan_paths


ROOT = Path(__file__).resolve().parents[1]


class Batch6CloseoutDocsAndSecurityTest(unittest.TestCase):
    def _doc_text(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_batch6_required_docs_exist_with_safety_language(self):
        required_docs = {
            "docs/integration-feature-flags.md": [
                "INTEGRATIONS_MODE",
                "ENABLE_REAL_PUBLISHING",
                "mock mode",
                "publishing remains disabled",
            ],
            "docs/platform-http-client.md": [
                "server-only",
                "network safety modes",
                "redaction",
                "provider error",
                "timeout",
                "mock mode",
            ],
            "docs/meta-oauth-real-mode.md": [
                "META_CLIENT_ID",
                "OAuth start",
                "callback",
                "token exchange",
                "placeholder_not_stored",
                "publishing disabled",
            ],
            "docs/connector-health-checks.md": [
                "healthy",
                "limited",
                "expired",
                "missing_permissions",
                "network_disabled",
                "Check connection",
            ],
            "docs/youtube-integration.md": ["mock OAuth", "publishing disabled", "manual export"],
            "docs/tiktok-integration.md": ["mock OAuth", "publishing disabled", "manual export"],
            "docs/linkedin-integration.md": ["mock OAuth", "publishing disabled", "manual export"],
            "docs/x-integration.md": ["mock OAuth", "publishing disabled", "manual export"],
            "docs/integration-security-review.md": [
                "secrets",
                "redacted",
                "token storage",
                "before real OAuth",
                "before real publishing",
            ],
        }

        for relative_path, expected_phrases in required_docs.items():
            with self.subTest(relative_path=relative_path):
                text = self._doc_text(relative_path)
                lowered = text.lower()
                for phrase in expected_phrases:
                    self.assertIn(phrase.lower(), lowered)

    def test_security_scan_reports_without_exposing_secret_values(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            secret_value = "sk-live-secret-value-that-must-not-print-123456"
            sample = root / "sample.py"
            sample.write_text(
                "TOKEN = {'access_token': '" + secret_value + "', 'client_secret': 'hidden'}\n",
                encoding="utf-8",
            )

            result = scan_paths([root])
            report = result.to_report()

        self.assertEqual(result.files_with_risky_patterns, 1)
        self.assertEqual(result.actual_secret_like_values, 1)
        self.assertNotIn(secret_value, report)
        self.assertIn("actual_secret_like_values=1", report)
        self.assertIn("No secret values printed.", report)


if __name__ == "__main__":
    unittest.main()
