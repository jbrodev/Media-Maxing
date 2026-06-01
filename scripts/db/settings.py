from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.db.init_db import initialize_database, resolve_database_path


SETTINGS_ID = "default"
AUTOMATION_LEVELS = {
    "manual_assist",
    "approval_queue",
    "semi_auto_scheduling",
    "safe_auto_posting",
    "autonomous_content_engine",
}
PLATFORM_IDS = {"facebook", "instagram", "threads", "youtube", "tiktok", "linkedin", "x"}
AI_PROVIDER_PREFERENCES = {"mock", "openai", "anthropic", "local"}
UPDATABLE_FIELDS = {
    "appName",
    "appEnvironment",
    "localDataDirectory",
    "defaultTimezone",
    "defaultPlatformTargets",
    "automationLevel",
    "requireApprovalBeforePublishing",
    "requireApprovalBeforeReplying",
    "emergencyPauseEnabled",
    "aiProviderPreference",
}


class SettingsValidationError(ValueError):
    pass


@dataclass(frozen=True)
class AppSettings:
    appName: str
    appEnvironment: str
    localDataDirectory: str
    defaultTimezone: str
    defaultPlatformTargets: list[str]
    automationLevel: str
    requireApprovalBeforePublishing: bool
    requireApprovalBeforeReplying: bool
    emergencyPauseEnabled: bool
    aiProviderPreference: str
    createdAt: str
    updatedAt: str


def _default_settings_json() -> dict[str, Any]:
    return {
        "appName": "Local Social AI Manager",
        "appEnvironment": os.environ.get("APP_ENV") or "development",
        "localDataDirectory": os.environ.get("LOCAL_DATA_DIR") or "./data",
        "defaultTimezone": "America/New_York",
        "defaultPlatformTargets": ["facebook", "instagram"],
        "aiProviderPreference": "mock",
    }


def _ensure_default_settings_row(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT OR IGNORE INTO app_settings (
          id,
          automation_level,
          require_approval_before_publishing,
          require_approval_before_replying,
          emergency_pause_enabled,
          kill_switch_enabled,
          integrations_mode,
          enable_real_network_calls,
          enable_real_oauth,
          enable_real_publishing,
          token_storage_mode,
          settings_json
        ) VALUES (
          ?,
          'approval_queue',
          1,
          1,
          0,
          0,
          'mock',
          0,
          0,
          0,
          'placeholder_not_stored',
          ?
        )
        """,
        (SETTINGS_ID, json.dumps(_default_settings_json(), sort_keys=True)),
    )


def _decode_settings_json(raw_value: str | None) -> dict[str, Any]:
    defaults = _default_settings_json()
    if not raw_value:
        return defaults

    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return defaults

    if not isinstance(decoded, dict):
        return defaults

    return {**defaults, **decoded}


def _require_non_empty_string(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SettingsValidationError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _require_bool(field_name: str, value: Any) -> bool:
    if not isinstance(value, bool):
        raise SettingsValidationError(f"{field_name} must be true or false.")
    return value


def _validate_settings(updates: dict[str, Any], merged_json: dict[str, Any]) -> None:
    unknown_fields = sorted(set(updates) - UPDATABLE_FIELDS)
    if unknown_fields:
        raise SettingsValidationError(
            f"Unknown setting field(s): {', '.join(unknown_fields)}."
        )

    for field_name in (
        "appName",
        "appEnvironment",
        "localDataDirectory",
        "defaultTimezone",
        "aiProviderPreference",
    ):
        merged_json[field_name] = _require_non_empty_string(
            field_name,
            merged_json[field_name],
        )

    if merged_json["aiProviderPreference"] not in AI_PROVIDER_PREFERENCES:
        raise SettingsValidationError(
            "aiProviderPreference must be one of: "
            f"{', '.join(sorted(AI_PROVIDER_PREFERENCES))}."
        )

    platform_targets = merged_json["defaultPlatformTargets"]
    if not isinstance(platform_targets, list) or not platform_targets:
        raise SettingsValidationError(
            "defaultPlatformTargets must be a non-empty list of platform IDs."
        )

    invalid_platforms = [
        platform for platform in platform_targets if platform not in PLATFORM_IDS
    ]
    if invalid_platforms:
        raise SettingsValidationError(
            "defaultPlatformTargets contains unsupported platform ID(s): "
            f"{', '.join(invalid_platforms)}."
        )

    automation_level = updates.get("automationLevel")
    if automation_level is not None and automation_level not in AUTOMATION_LEVELS:
        raise SettingsValidationError(
            "automationLevel must be one of "
            f"{', '.join(sorted(AUTOMATION_LEVELS))}; got {automation_level!r}."
        )

    for field_name in (
        "requireApprovalBeforePublishing",
        "requireApprovalBeforeReplying",
        "emergencyPauseEnabled",
    ):
        if field_name in updates:
            _require_bool(field_name, updates[field_name])


def _row_to_settings(row: sqlite3.Row) -> AppSettings:
    extra_settings = _decode_settings_json(row["settings_json"])
    return AppSettings(
        appName=str(extra_settings["appName"]),
        appEnvironment=str(extra_settings["appEnvironment"]),
        localDataDirectory=str(extra_settings["localDataDirectory"]),
        defaultTimezone=str(extra_settings["defaultTimezone"]),
        defaultPlatformTargets=list(extra_settings["defaultPlatformTargets"]),
        automationLevel=row["automation_level"],
        requireApprovalBeforePublishing=bool(row["require_approval_before_publishing"]),
        requireApprovalBeforeReplying=bool(row["require_approval_before_replying"]),
        emergencyPauseEnabled=bool(row["emergency_pause_enabled"]),
        aiProviderPreference=str(extra_settings["aiProviderPreference"]),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def load_app_settings(database_path: str | Path | None = None) -> AppSettings:
    db_path = initialize_database(resolve_database_path(database_path))

    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_default_settings_row(connection)
        connection.commit()

        row = connection.execute(
            "SELECT * FROM app_settings WHERE id = ?",
            (SETTINGS_ID,),
        ).fetchone()

    return _row_to_settings(row)


def update_app_settings(
    database_path: str | Path | None,
    updates: dict[str, Any],
) -> AppSettings:
    db_path = initialize_database(resolve_database_path(database_path))
    current = load_app_settings(db_path)
    merged_json = {
        "appName": current.appName,
        "appEnvironment": current.appEnvironment,
        "localDataDirectory": current.localDataDirectory,
        "defaultTimezone": current.defaultTimezone,
        "defaultPlatformTargets": current.defaultPlatformTargets,
        "aiProviderPreference": current.aiProviderPreference,
    }

    for key in list(merged_json):
        if key in updates:
            merged_json[key] = updates[key]

    _validate_settings(updates, merged_json)

    automation_level = updates.get("automationLevel", current.automationLevel)
    require_publishing = updates.get(
        "requireApprovalBeforePublishing",
        current.requireApprovalBeforePublishing,
    )
    require_replying = updates.get(
        "requireApprovalBeforeReplying",
        current.requireApprovalBeforeReplying,
    )
    emergency_pause = updates.get(
        "emergencyPauseEnabled",
        current.emergencyPauseEnabled,
    )

    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        _ensure_default_settings_row(connection)
        connection.execute(
            """
            UPDATE app_settings
            SET automation_level = ?,
              require_approval_before_publishing = ?,
              require_approval_before_replying = ?,
              emergency_pause_enabled = ?,
              settings_json = ?,
              updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                automation_level,
                int(bool(require_publishing)),
                int(bool(require_replying)),
                int(bool(emergency_pause)),
                json.dumps(merged_json, sort_keys=True),
                SETTINGS_ID,
            ),
        )
        connection.commit()

    return load_app_settings(db_path)
