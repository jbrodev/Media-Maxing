from __future__ import annotations

import os
import re
from pathlib import Path

from scripts.db.init_db import REPO_ROOT


ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class LocalEnvError(ValueError):
    """Raised when a local environment file cannot be parsed safely."""


def load_local_env_file(
    path: str | Path | None = None,
    *,
    override: bool = False,
) -> list[str]:
    """Load a simple local .env file without printing or returning secret values."""

    env_path = Path(path) if path is not None else REPO_ROOT / ".env"
    if not env_path.exists():
        return []

    loaded_keys: list[str] = []
    for line_number, raw_line in enumerate(
        env_path.read_text(encoding="utf-8").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        if "=" not in line:
            raise LocalEnvError(
                f"Invalid local environment entry at {env_path}:{line_number}."
            )
        key, value = line.split("=", 1)
        key = key.strip()
        if not ENV_KEY_PATTERN.fullmatch(key):
            raise LocalEnvError(
                f"Invalid local environment key at {env_path}:{line_number}."
            )
        value = _strip_matching_quotes(value.strip())
        if override or key not in os.environ:
            os.environ[key] = value
        loaded_keys.append(key)
    return loaded_keys


def _strip_matching_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value
