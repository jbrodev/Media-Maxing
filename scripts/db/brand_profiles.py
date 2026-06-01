from __future__ import annotations

import json
import re
import sqlite3
import sys
import uuid
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.db.init_db import initialize_database, resolve_database_path


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

LIST_FIELDS = {
    "services",
    "serviceAreas",
    "targetCustomers",
    "toneRules",
    "bannedWords",
    "preferredWords",
    "commonCTAs",
    "hashtags",
    "approvalRules",
    "safetyRules",
    "examplePosts",
}

EXTRA_FIELDS = {
    "tagline",
    "industry",
    "targetCustomers",
    "toneRules",
    "preferredWords",
    "commonCTAs",
    "hashtags",
    "website",
    "phone",
    "email",
    "approvalRules",
    "safetyRules",
    "examplePosts",
}

UPDATABLE_FIELDS = {
    "businessName",
    "tagline",
    "industry",
    "description",
    "services",
    "serviceAreas",
    "targetCustomers",
    "brandVoice",
    "toneRules",
    "bannedWords",
    "preferredWords",
    "commonCTAs",
    "hashtags",
    "website",
    "phone",
    "email",
    "approvalRules",
    "safetyRules",
    "examplePosts",
}


class BrandProfileValidationError(ValueError):
    pass


@dataclass(frozen=True)
class BrandProfile:
    id: str
    businessName: str
    tagline: str | None
    industry: str | None
    description: str | None
    services: list[str]
    serviceAreas: list[str]
    targetCustomers: list[str]
    brandVoice: str | None
    toneRules: list[str]
    bannedWords: list[str]
    preferredWords: list[str]
    commonCTAs: list[str]
    hashtags: list[str]
    website: str | None
    phone: str | None
    email: str | None
    approvalRules: list[str]
    safetyRules: list[str]
    examplePosts: list[str]
    createdAt: str
    updatedAt: str


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True)


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise BrandProfileValidationError("String fields must be text values.")
    cleaned = value.strip()
    return cleaned or None


def _clean_required_string(field_name: str, value: Any) -> str:
    cleaned = _clean_optional_string(value)
    if not cleaned:
        raise BrandProfileValidationError(f"{field_name} is required.")
    return cleaned


def _clean_string_list(field_name: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise BrandProfileValidationError(f"{field_name} must be a list of text values.")

    cleaned_values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise BrandProfileValidationError(
                f"{field_name} must contain only text values."
            )
        cleaned = item.strip()
        if cleaned:
            cleaned_values.append(cleaned)
    return cleaned_values


def _validate_profile_data(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    unknown_fields = sorted(set(data) - (UPDATABLE_FIELDS | {"id"}))
    if unknown_fields:
        raise BrandProfileValidationError(
            f"Unknown brand profile field(s): {', '.join(unknown_fields)}."
        )

    cleaned: dict[str, Any] = {}
    if not partial or "businessName" in data:
        cleaned["businessName"] = _clean_required_string(
            "businessName",
            data.get("businessName"),
        )

    for field_name in UPDATABLE_FIELDS - {"businessName"}:
        if field_name not in data:
            continue
        if field_name in LIST_FIELDS:
            cleaned[field_name] = _clean_string_list(field_name, data[field_name])
        else:
            cleaned[field_name] = _clean_optional_string(data[field_name])

    email = cleaned.get("email")
    if email and not EMAIL_PATTERN.match(email):
        raise BrandProfileValidationError("email must be a valid email address.")

    return cleaned


def _profile_from_row(row: sqlite3.Row) -> BrandProfile:
    preferences = _decode_json(row["preferences_json"], {})
    return BrandProfile(
        id=row["id"],
        businessName=row["business_name"],
        tagline=preferences.get("tagline"),
        industry=preferences.get("industry"),
        description=row["description"],
        services=_decode_json(row["services_json"], []),
        serviceAreas=_decode_json(row["locations_json"], []),
        targetCustomers=preferences.get(
            "targetCustomers",
            [row["target_audience"]] if row["target_audience"] else [],
        ),
        brandVoice=row["voice"],
        toneRules=preferences.get("toneRules", []),
        bannedWords=_decode_json(row["blocked_phrases_json"], []),
        preferredWords=preferences.get("preferredWords", []),
        commonCTAs=preferences.get("commonCTAs", []),
        hashtags=preferences.get("hashtags", []),
        website=preferences.get("website"),
        phone=preferences.get("phone"),
        email=preferences.get("email"),
        approvalRules=preferences.get("approvalRules", []),
        safetyRules=preferences.get("safetyRules", []),
        examplePosts=preferences.get("examplePosts", []),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _connect(database_path: str | Path | None) -> tuple[Path, sqlite3.Connection]:
    db_path = initialize_database(resolve_database_path(database_path))
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return db_path, connection


def _preferences_from_data(data: dict[str, Any]) -> dict[str, Any]:
    return {field: data[field] for field in EXTRA_FIELDS if field in data}


def create_brand_profile(
    database_path: str | Path | None,
    data: dict[str, Any],
) -> BrandProfile:
    cleaned = _validate_profile_data(data)
    profile_id = str(data.get("id") or uuid.uuid4())
    preferences = _preferences_from_data(cleaned)

    _, connection = _connect(database_path)
    with closing(connection):
        connection.execute(
            """
            INSERT INTO brand_profiles (
              id,
              business_name,
              description,
              voice,
              services_json,
              locations_json,
              target_audience,
              blocked_phrases_json,
              preferences_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                cleaned["businessName"],
                cleaned.get("description"),
                cleaned.get("brandVoice"),
                _json(cleaned.get("services", [])),
                _json(cleaned.get("serviceAreas", [])),
                ", ".join(cleaned.get("targetCustomers", [])) or None,
                _json(cleaned.get("bannedWords", [])),
                _json(preferences),
            ),
        )
        connection.commit()

    profile = get_brand_profile(database_path, profile_id)
    if profile is None:
        raise RuntimeError("Brand profile was created but could not be loaded.")
    return profile


def get_brand_profile(
    database_path: str | Path | None,
    profile_id: str,
) -> BrandProfile | None:
    _, connection = _connect(database_path)
    with closing(connection):
        row = connection.execute(
            "SELECT * FROM brand_profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
    return _profile_from_row(row) if row else None


def list_brand_profiles(database_path: str | Path | None) -> list[BrandProfile]:
    _, connection = _connect(database_path)
    with closing(connection):
        rows = connection.execute(
            "SELECT * FROM brand_profiles ORDER BY created_at ASC, business_name ASC"
        ).fetchall()
    return [_profile_from_row(row) for row in rows]


def update_brand_profile(
    database_path: str | Path | None,
    profile_id: str,
    updates: dict[str, Any],
) -> BrandProfile:
    current = get_brand_profile(database_path, profile_id)
    if current is None:
        raise BrandProfileValidationError(f"Brand profile not found: {profile_id}.")

    cleaned_updates = _validate_profile_data(updates, partial=True)
    existing_preferences = {
        "tagline": current.tagline,
        "industry": current.industry,
        "targetCustomers": current.targetCustomers,
        "toneRules": current.toneRules,
        "preferredWords": current.preferredWords,
        "commonCTAs": current.commonCTAs,
        "hashtags": current.hashtags,
        "website": current.website,
        "phone": current.phone,
        "email": current.email,
        "approvalRules": current.approvalRules,
        "safetyRules": current.safetyRules,
        "examplePosts": current.examplePosts,
    }
    existing_preferences.update(_preferences_from_data(cleaned_updates))
    preferences = {
        key: value
        for key, value in existing_preferences.items()
        if value not in (None, [], "")
    }

    merged = {
        "businessName": current.businessName,
        "description": current.description,
        "brandVoice": current.brandVoice,
        "services": current.services,
        "serviceAreas": current.serviceAreas,
        "targetCustomers": current.targetCustomers,
        "bannedWords": current.bannedWords,
        **cleaned_updates,
    }

    _, connection = _connect(database_path)
    with closing(connection):
        connection.execute(
            """
            UPDATE brand_profiles
            SET business_name = ?,
              description = ?,
              voice = ?,
              services_json = ?,
              locations_json = ?,
              target_audience = ?,
              blocked_phrases_json = ?,
              preferences_json = ?,
              updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                merged["businessName"],
                merged.get("description"),
                merged.get("brandVoice"),
                _json(merged.get("services", [])),
                _json(merged.get("serviceAreas", [])),
                ", ".join(merged.get("targetCustomers", [])) or None,
                _json(merged.get("bannedWords", [])),
                _json(preferences),
                profile_id,
            ),
        )
        connection.commit()

    updated = get_brand_profile(database_path, profile_id)
    if updated is None:
        raise RuntimeError("Brand profile was updated but could not be loaded.")
    return updated
