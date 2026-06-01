from __future__ import annotations

import argparse
import json
import mimetypes
import shutil
import sqlite3
import sys
import uuid
from contextlib import closing
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.db.init_db import REPO_ROOT, initialize_database, resolve_database_path
from scripts.db.settings import load_app_settings


MAX_MEDIA_FILE_SIZE_BYTES = 100 * 1024 * 1024

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".m4v"}

MIME_TYPE_OVERRIDES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".m4v": "video/mp4",
}

CONTENT_ANGLES = {
    "before_after",
    "educational",
    "behind_the_scenes",
    "testimonial",
    "promotion",
    "faq",
    "trust_builder",
    "transformation",
    "seasonal",
    "other",
}

USAGE_STATUSES = {
    "new",
    "reviewed",
    "ready_for_generation",
    "used_in_draft",
    "published",
    "archived",
}

METADATA_FIELDS = {
    "title",
    "description",
    "qualityRating",
    "usageStatus",
    "notes",
}

JOB_CONTEXT_FIELDS = {
    "serviceType",
    "locationName",
    "city",
    "state",
    "projectDate",
    "contentAngle",
}


class MediaStorageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class MediaDirectories:
    localDataDirectory: Path
    mediaDirectory: Path
    originalsDirectory: Path
    processedDirectory: Path
    thumbnailsDirectory: Path


@dataclass(frozen=True)
class ImportedMediaAsset:
    id: str
    mediaType: str
    originalFilename: str
    internalFilename: str
    internalPath: str
    mimeType: str
    fileSizeBytes: int
    createdAt: str
    updatedAt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MediaAsset:
    id: str
    mediaType: str
    originalFilename: str
    originalPath: str
    processedPath: str | None
    thumbnailPath: str | None
    mimeType: str | None
    fileSizeBytes: int | None
    title: str
    description: str
    tags: list[str]
    serviceType: str
    locationName: str
    city: str
    state: str
    projectDate: str
    contentAngle: str
    qualityRating: int | None
    usageStatus: str
    notes: str
    createdAt: str
    updatedAt: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def resolve_local_data_dir(
    local_data_dir: str | Path | None = None,
    database_path: str | Path | None = None,
) -> Path:
    if local_data_dir:
        return Path(local_data_dir).expanduser().resolve()

    try:
        settings = load_app_settings(database_path)
        if settings.localDataDirectory:
            configured_path = Path(settings.localDataDirectory).expanduser()
            if configured_path.is_absolute():
                return configured_path.resolve()
            return (REPO_ROOT / configured_path).resolve()
    except Exception:
        pass

    return (REPO_ROOT / "data").resolve()


def ensure_media_directories(
    local_data_dir: str | Path | None = None,
    database_path: str | Path | None = None,
) -> MediaDirectories:
    data_dir = resolve_local_data_dir(local_data_dir, database_path)
    media_dir = data_dir / "media"
    originals_dir = media_dir / "originals"
    processed_dir = media_dir / "processed"
    thumbnails_dir = media_dir / "thumbnails"

    for directory in (originals_dir, processed_dir, thumbnails_dir):
        directory.mkdir(parents=True, exist_ok=True)

    return MediaDirectories(
        localDataDirectory=data_dir,
        mediaDirectory=media_dir,
        originalsDirectory=originals_dir,
        processedDirectory=processed_dir,
        thumbnailsDirectory=thumbnails_dir,
    )


def _media_type_from_extension(extension: str) -> str | None:
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    return None


def _detect_mime_type(source_path: Path) -> str:
    extension = source_path.suffix.lower()
    if extension in MIME_TYPE_OVERRIDES:
        return MIME_TYPE_OVERRIDES[extension]

    guessed_type, _ = mimetypes.guess_type(source_path.name)
    return guessed_type or "application/octet-stream"


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _clean_optional_string(field_name: str, value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        raise MediaStorageValidationError(f"{field_name} must be a text value.")
    return value.strip()


def _clean_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        raw_tags = value.split(",")
    elif isinstance(value, list):
        raw_tags = value
    else:
        raise MediaStorageValidationError("tags must be a list or comma-separated text.")

    cleaned: list[str] = []
    for tag in raw_tags:
        if not isinstance(tag, str):
            raise MediaStorageValidationError("tags must contain only text values.")
        normalized = tag.strip()
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    return cleaned


def _clean_quality_rating(value: Any) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        raise MediaStorageValidationError("qualityRating must be a number from 1 to 5.")
    try:
        rating = int(value)
    except (TypeError, ValueError):
        raise MediaStorageValidationError("qualityRating must be a number from 1 to 5.")
    if rating < 1 or rating > 5:
        raise MediaStorageValidationError("qualityRating must be a number from 1 to 5.")
    return rating


def _validate_metadata_updates(updates: dict[str, Any]) -> dict[str, Any]:
    allowed_fields = METADATA_FIELDS | JOB_CONTEXT_FIELDS | {"tags"}
    unknown_fields = sorted(set(updates) - allowed_fields)
    if unknown_fields:
        raise MediaStorageValidationError(
            f"Unknown media metadata field(s): {', '.join(unknown_fields)}."
        )

    cleaned: dict[str, Any] = {}
    for field_name in METADATA_FIELDS - {"qualityRating"}:
        if field_name in updates:
            cleaned[field_name] = _clean_optional_string(field_name, updates[field_name])

    for field_name in JOB_CONTEXT_FIELDS:
        if field_name in updates:
            cleaned[field_name] = _clean_optional_string(field_name, updates[field_name])

    if "tags" in updates:
        cleaned["tags"] = _clean_tags(updates["tags"])

    if "qualityRating" in updates:
        cleaned["qualityRating"] = _clean_quality_rating(updates["qualityRating"])

    if "contentAngle" in cleaned and cleaned["contentAngle"]:
        if cleaned["contentAngle"] not in CONTENT_ANGLES:
            raise MediaStorageValidationError(
                "contentAngle must be one of: "
                f"{', '.join(sorted(CONTENT_ANGLES))}."
            )

    if "usageStatus" in cleaned and cleaned["usageStatus"]:
        if cleaned["usageStatus"] not in USAGE_STATUSES:
            raise MediaStorageValidationError(
                "usageStatus must be one of: "
                f"{', '.join(sorted(USAGE_STATUSES))}."
            )

    return cleaned


def _row_to_media_asset(row: sqlite3.Row) -> MediaAsset:
    tags = _decode_json(row["tags_json"], [])
    job_context = _decode_json(row["job_context_json"], {})
    metadata = _decode_json(row["metadata_json"], {})
    title = metadata.get("title") or row["file_name"]
    service_type = job_context.get("serviceType") or job_context.get("service") or ""
    content_angle = job_context.get("contentAngle") or "other"
    usage_status = metadata.get("usageStatus") or metadata.get("status") or "new"
    quality_rating = metadata.get("qualityRating")
    try:
        quality_rating = int(quality_rating) if quality_rating not in (None, "") else None
    except (TypeError, ValueError):
        quality_rating = None

    return MediaAsset(
        id=row["id"],
        mediaType=row["media_type"],
        originalFilename=row["file_name"],
        originalPath=row["original_path"],
        processedPath=row["processed_path"],
        thumbnailPath=row["thumbnail_path"],
        mimeType=row["mime_type"],
        fileSizeBytes=row["file_size_bytes"],
        title=str(title),
        description=str(metadata.get("description") or ""),
        tags=tags if isinstance(tags, list) else [],
        serviceType=str(service_type),
        locationName=str(job_context.get("locationName") or ""),
        city=str(job_context.get("city") or ""),
        state=str(job_context.get("state") or ""),
        projectDate=str(job_context.get("projectDate") or ""),
        contentAngle=content_angle if content_angle in CONTENT_ANGLES else "other",
        qualityRating=quality_rating,
        usageStatus=usage_status if usage_status in USAGE_STATUSES else "new",
        notes=str(metadata.get("notes") or ""),
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def _connect(database_path: str | Path | None) -> tuple[Path, sqlite3.Connection]:
    db_path = initialize_database(resolve_database_path(database_path))
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return db_path, connection


def _validate_source_file(
    source_path: str | Path,
    max_file_size_bytes: int,
) -> tuple[Path, str, str, int]:
    resolved_source = Path(source_path).expanduser().resolve()
    if not resolved_source.exists():
        raise MediaStorageValidationError(f"Media file does not exist: {resolved_source}")
    if not resolved_source.is_file():
        raise MediaStorageValidationError(f"Media path is not a file: {resolved_source}")

    file_size = resolved_source.stat().st_size
    if file_size <= 0:
        raise MediaStorageValidationError("Media file is empty.")
    if file_size > max_file_size_bytes:
        raise MediaStorageValidationError(
            "Media file is larger than the allowed limit "
            f"of {max_file_size_bytes} bytes."
        )

    extension = resolved_source.suffix.lower()
    media_type = _media_type_from_extension(extension)
    mime_type = _detect_mime_type(resolved_source)
    if media_type is None or not mime_type.startswith(f"{media_type}/"):
        raise MediaStorageValidationError(
            "Unsupported media type. Only image and video files are supported."
        )

    return resolved_source, media_type, mime_type, file_size


def _safe_internal_filename(source_path: Path) -> str:
    extension = source_path.suffix.lower()
    if extension == ".jpeg":
        extension = ".jpg"
    return f"{uuid.uuid4().hex}{extension}"


def _insert_media_asset(
    database_path: Path,
    *,
    asset_id: str,
    media_type: str,
    original_filename: str,
    internal_filename: str,
    internal_path: Path,
    mime_type: str,
    file_size_bytes: int,
) -> ImportedMediaAsset:
    metadata = {
        "originalFilename": original_filename,
        "internalFilename": internal_filename,
        "storage": "local",
        "title": original_filename,
        "description": "",
        "qualityRating": None,
        "usageStatus": "new",
        "notes": "",
    }

    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO media_assets (
              id,
              media_type,
              original_path,
              file_name,
              mime_type,
              file_size_bytes,
              tags_json,
              job_context_json,
              metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, '[]', '{}', ?)
            """,
            (
                asset_id,
                media_type,
                str(internal_path),
                original_filename,
                mime_type,
                file_size_bytes,
                json.dumps(metadata, sort_keys=True),
            ),
        )
        row = connection.execute(
            "SELECT * FROM media_assets WHERE id = ?",
            (asset_id,),
        ).fetchone()
        connection.commit()

    return ImportedMediaAsset(
        id=row["id"],
        mediaType=row["media_type"],
        originalFilename=row["file_name"],
        internalFilename=internal_filename,
        internalPath=row["original_path"],
        mimeType=row["mime_type"],
        fileSizeBytes=row["file_size_bytes"],
        createdAt=row["created_at"],
        updatedAt=row["updated_at"],
    )


def import_media_file(
    database_path: str | Path | None,
    source_path: str | Path,
    *,
    local_data_dir: str | Path | None = None,
    max_file_size_bytes: int = MAX_MEDIA_FILE_SIZE_BYTES,
) -> ImportedMediaAsset:
    db_path = initialize_database(resolve_database_path(database_path))
    resolved_source, media_type, mime_type, file_size = _validate_source_file(
        source_path,
        max_file_size_bytes,
    )

    directories = ensure_media_directories(local_data_dir, db_path)
    internal_filename = _safe_internal_filename(resolved_source)
    destination = (directories.originalsDirectory / internal_filename).resolve()
    originals_dir = directories.originalsDirectory.resolve()

    if destination.parent != originals_dir:
        raise MediaStorageValidationError("Resolved media destination is unsafe.")
    if destination.exists():
        raise MediaStorageValidationError("Generated media filename already exists.")

    shutil.copy2(resolved_source, destination)

    try:
        return _insert_media_asset(
            db_path,
            asset_id=str(uuid.uuid4()),
            media_type=media_type,
            original_filename=resolved_source.name,
            internal_filename=internal_filename,
            internal_path=destination,
            mime_type=mime_type,
            file_size_bytes=file_size,
        )
    except Exception:
        if destination.exists():
            destination.unlink()
        raise


def get_media_asset(
    database_path: str | Path | None,
    media_asset_id: str,
) -> MediaAsset | None:
    _, connection = _connect(database_path)
    with closing(connection):
        row = connection.execute(
            "SELECT * FROM media_assets WHERE id = ?",
            (media_asset_id,),
        ).fetchone()
    return _row_to_media_asset(row) if row else None


def list_media_assets(database_path: str | Path | None = None) -> list[MediaAsset]:
    _, connection = _connect(database_path)
    with closing(connection):
        rows = connection.execute(
            "SELECT * FROM media_assets ORDER BY created_at ASC, file_name ASC"
        ).fetchall()
    return [_row_to_media_asset(row) for row in rows]


def update_media_asset_metadata(
    database_path: str | Path | None,
    media_asset_id: str,
    updates: dict[str, Any],
) -> MediaAsset:
    cleaned = _validate_metadata_updates(updates)
    _, connection = _connect(database_path)
    with closing(connection):
        row = connection.execute(
            "SELECT * FROM media_assets WHERE id = ?",
            (media_asset_id,),
        ).fetchone()
        if row is None:
            raise MediaStorageValidationError(f"Media asset not found: {media_asset_id}.")

        tags = _decode_json(row["tags_json"], [])
        job_context = _decode_json(row["job_context_json"], {})
        metadata = _decode_json(row["metadata_json"], {})

        if "tags" in cleaned:
            tags = cleaned["tags"]

        for field_name in JOB_CONTEXT_FIELDS:
            if field_name in cleaned:
                if cleaned[field_name]:
                    job_context[field_name] = cleaned[field_name]
                else:
                    job_context.pop(field_name, None)

        for field_name in METADATA_FIELDS:
            if field_name in cleaned:
                if cleaned[field_name] not in ("", None):
                    metadata[field_name] = cleaned[field_name]
                else:
                    metadata.pop(field_name, None)

        connection.execute(
            """
            UPDATE media_assets
            SET tags_json = ?,
              job_context_json = ?,
              metadata_json = ?,
              updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                json.dumps(tags, sort_keys=True),
                json.dumps(job_context, sort_keys=True),
                json.dumps(metadata, sort_keys=True),
                media_asset_id,
            ),
        )
        connection.commit()

    updated = get_media_asset(database_path, media_asset_id)
    if updated is None:
        raise RuntimeError("Media asset was updated but could not be loaded.")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import an image or video into local media storage."
    )
    parser.add_argument("source", help="Path to an image or video file to import.")
    parser.add_argument(
        "--database",
        help="Path to the SQLite database. Defaults to DATABASE_URL or data/app.sqlite.",
    )
    parser.add_argument(
        "--local-data-dir",
        help="Local app data directory. Defaults to app settings or ./data.",
    )
    args = parser.parse_args()

    result = import_media_file(
        args.database,
        args.source,
        local_data_dir=args.local_data_dir,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
