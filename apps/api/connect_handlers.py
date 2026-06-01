"""Route handler scaffolding for future local API wiring.

No web framework is configured yet. These functions mirror the planned
routes and delegate to the server-side OAuth flow service:

- POST /api/connect/:platform/start
- GET /api/connect/:platform/callback
- POST /api/connect/:platform/disconnect
- GET /api/connect/accounts
- GET /api/connect/platforms
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.services.oauth_flow import (
    connect_accounts_handler,
    connect_callback_handler,
    connect_disconnect_handler,
    connect_platforms_handler,
    connect_start_handler,
)


def start(platform: str, payload: dict[str, Any] | None = None, *, database_path: str | Path | None = None) -> dict[str, Any]:
    return connect_start_handler(platform, payload, database_path=database_path)


def callback(platform: str, query: dict[str, Any] | None = None, *, database_path: str | Path | None = None) -> dict[str, Any]:
    return connect_callback_handler(platform, query, database_path=database_path)


def disconnect(platform: str, payload: dict[str, Any] | None = None, *, database_path: str | Path | None = None) -> dict[str, Any]:
    return connect_disconnect_handler(platform, payload, database_path=database_path)


def accounts(*, database_path: str | Path | None = None) -> dict[str, Any]:
    return connect_accounts_handler(database_path=database_path)


def platforms(*, database_path: str | Path | None = None) -> dict[str, Any]:
    return connect_platforms_handler(database_path=database_path)
