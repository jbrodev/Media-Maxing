from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.services.local_env import LocalEnvError, load_local_env_file


class LocalEnvTest(unittest.TestCase):
    def test_missing_file_is_optional(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / ".env"

            self.assertEqual(load_local_env_file(missing), [])

    def test_loader_returns_names_only_and_does_not_override_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "APP_ENV=development\nMETA_CLIENT_SECRET='local-only-secret'\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"APP_ENV": "test"}, clear=False):
                loaded_keys = load_local_env_file(env_path)

                self.assertEqual(loaded_keys, ["APP_ENV", "META_CLIENT_SECRET"])
                self.assertEqual(os.environ["APP_ENV"], "test")
                self.assertEqual(os.environ["META_CLIENT_SECRET"], "local-only-secret")
                self.assertNotIn("local-only-secret", repr(loaded_keys))

    def test_override_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("APP_ENV=development\n", encoding="utf-8")
            with patch.dict(os.environ, {"APP_ENV": "test"}, clear=False):
                load_local_env_file(env_path, override=True)

                self.assertEqual(os.environ["APP_ENV"], "development")

    def test_invalid_entry_fails_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text("META_CLIENT_SECRET\n", encoding="utf-8")

            with self.assertRaises(LocalEnvError):
                load_local_env_file(env_path)


if __name__ == "__main__":
    unittest.main()
