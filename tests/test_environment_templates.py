from __future__ import annotations

from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class EnvironmentTemplatesTest(unittest.TestCase):
    def test_root_template_has_safe_integration_defaults(self):
        template = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

        self.assertIn("INTEGRATIONS_MODE=mock", template)
        self.assertIn("ENABLE_REAL_NETWORK_CALLS=false", template)
        self.assertIn("ENABLE_REAL_OAUTH=false", template)
        self.assertIn("ENABLE_REAL_PUBLISHING=false", template)
        self.assertIn("TOKEN_STORAGE_MODE=placeholder_not_stored", template)

    def test_web_template_excludes_server_side_secrets_and_database_paths(self):
        template = (REPO_ROOT / "apps" / "web" / ".env.example").read_text(
            encoding="utf-8"
        )

        self.assertIn("LOCAL_API_ORIGIN=", template)
        for forbidden in (
            "DATABASE_URL",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "CLIENT_SECRET",
            "TOKEN_STORAGE_MODE",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, template)


if __name__ == "__main__":
    unittest.main()
