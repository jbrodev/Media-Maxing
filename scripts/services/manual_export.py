from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
import uuid
from contextlib import closing
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.db.init_db import REPO_ROOT, initialize_database, resolve_database_path
from scripts.db.settings import load_app_settings
from scripts.services.preflight import PreflightValidationService


EXPORT_FILE_ORDER = [
    "caption.txt",
    "hashtags.txt",
    "post.md",
    "metadata.json",
    "media-manifest.json",
    "posting-instructions.md",
]

BLOCKED_QUEUE_STATUSES = {"canceled", "processing", "skipped"}
FAILED_PREFLIGHT_STATUSES = {"errors", "blocked", "failed"}
PASSING_PREFLIGHT_STATUSES = {"passed", "warnings", "warning"}
SECRET_MARKERS = {
    "access_token",
    "refresh_token",
    "client_secret",
    "authorization",
    "bearer",
    "id_token",
    "appsecret_proof",
    "signed_request",
    "openai_api_key",
    "anthropic_api_key",
    "meta_client_secret",
    "google_client_secret",
    "tiktok_client_secret",
    "linkedin_client_secret",
    "x_client_secret",
}


@dataclass(frozen=True)
class ManualExportResult:
    queueItemId: str
    exportPath: Path
    filesCreated: list[str] = field(default_factory=list)
    mediaCopied: bool = False
    preflightStatus: str = ""


class ManualExportError(ValueError):
    def __init__(self, message: str, error_codes: list[str] | None = None):
        super().__init__(message)
        self.error_codes = error_codes or []


class ManualExportService:
    """Create local manual posting packages for publish queue items.

    This service writes files under the local export directory only. It does
    not publish, call platform APIs, upload files, or mark the item as posted.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        export_root: str | Path | None = None,
    ):
        self.database_path = initialize_database(resolve_database_path(database_path))
        self.export_root = Path(export_root).expanduser().resolve() if export_root else None
        self.preflight = PreflightValidationService(self.database_path)

    def export_queue_item(
        self,
        queue_item_id: str,
        *,
        exported_at: str | datetime | None = None,
        copy_media: bool = False,
        allow_failed_preflight_in_development: bool = False,
    ) -> ManualExportResult:
        settings = load_app_settings(self.database_path)
        if settings.emergencyPauseEnabled:
            raise ManualExportError(
                "Emergency pause blocks manual export packages in the MVP.",
                ["emergency_pause_enabled"],
            )

        queue_row = self._require_queue_row(queue_item_id)
        scheduled_row = self._require_scheduled_row(queue_row["scheduled_post_id"])
        generated_row = self._generated_post_row(queue_row["generated_post_id"])
        brand_row = self._brand_row(queue_row["brand_profile_id"])

        self._validate_queue_status(queue_row)
        preflight_status = self._validate_preflight(
            queue_row,
            settings_app_environment=settings.appEnvironment,
            allow_failed_preflight_in_development=allow_failed_preflight_in_development,
        )

        exported_dt = _coerce_datetime(exported_at)
        package_dir = self._create_package_dir(
            platform=queue_row["platform"],
            queue_item_id=queue_row["id"],
            label=self._package_label(scheduled_row, generated_row),
            exported_dt=exported_dt,
        )

        schedule_metadata = _decode_json(scheduled_row["schedule_metadata_json"], {})
        media_ids = _decode_json(
            scheduled_row["media_asset_ids_json"] or scheduled_row["media_snapshot_json"],
            [],
        )
        media_rows = self._media_rows(media_ids)
        media_manifest = self._build_media_manifest(
            package_dir,
            media_rows,
            copy_media=copy_media,
        )
        hashtags = _clean_string_list(schedule_metadata.get("hashtags"))
        safety_flags = _clean_string_list(schedule_metadata.get("safetyFlags"))

        files_created: list[str] = []
        files_created.append(
            self._write_text(
                package_dir / "caption.txt",
                f"{scheduled_row['caption_snapshot'].strip()}\n",
            )
        )
        if hashtags:
            files_created.append(
                self._write_text(package_dir / "hashtags.txt", " ".join(hashtags) + "\n")
            )

        post_markdown = self._post_markdown(
            queue_row=queue_row,
            scheduled_row=scheduled_row,
            generated_row=generated_row,
            brand_row=brand_row,
            schedule_metadata=schedule_metadata,
            hashtags=hashtags,
            media_manifest=media_manifest,
        )
        files_created.append(self._write_text(package_dir / "post.md", post_markdown))

        metadata = {
            "queueItemId": queue_row["id"],
            "scheduledPostId": scheduled_row["id"],
            "generatedPostId": queue_row["generated_post_id"],
            "brandProfileId": queue_row["brand_profile_id"],
            "platform": queue_row["platform"],
            "dueAt": queue_row["due_at"],
            "exportedAt": _utc_iso(exported_dt),
            "preflightStatus": preflight_status,
            "queueStatus": queue_row["queue_status"],
            "mediaAssetIds": media_ids,
            "safetyFlags": safety_flags,
            "appVersion": None,
            "realPublishing": False,
            "manualExportOnly": True,
        }
        files_created.append(self._write_json(package_dir / "metadata.json", metadata))
        files_created.append(
            self._write_json(package_dir / "media-manifest.json", media_manifest)
        )
        files_created.append(
            self._write_text(
                package_dir / "posting-instructions.md",
                self._posting_instructions(queue_row, scheduled_row, media_manifest),
            )
        )

        ordered_files = [name for name in EXPORT_FILE_ORDER if name in files_created]
        return ManualExportResult(
            queueItemId=queue_row["id"],
            exportPath=package_dir,
            filesCreated=ordered_files,
            mediaCopied=bool(media_manifest["mediaCopied"]),
            preflightStatus=preflight_status,
        )

    def _validate_queue_status(self, queue_row: sqlite3.Row) -> None:
        status = queue_row["queue_status"]
        if status in BLOCKED_QUEUE_STATUSES:
            raise ManualExportError(
                f"Queue item status {status!r} cannot be exported.",
                ["queue_status_not_exportable"],
            )

    def _validate_preflight(
        self,
        queue_row: sqlite3.Row,
        *,
        settings_app_environment: str,
        allow_failed_preflight_in_development: bool,
    ) -> str:
        stored_status = (queue_row["preflight_status"] or "not_checked").strip()
        if stored_status in FAILED_PREFLIGHT_STATUSES:
            if allow_failed_preflight_in_development and settings_app_environment == "development":
                return stored_status
            raise ManualExportError(
                "Queue item has failed preflight and cannot be exported safely.",
                ["preflight_failed"],
            )

        result = self.preflight.validate_queue_item(queue_row["id"])
        if result.errors:
            if allow_failed_preflight_in_development and settings_app_environment == "development":
                return "errors"
            raise ManualExportError(
                "Queue item failed current preflight and cannot be exported safely.",
                result.error_codes or ["preflight_failed"],
            )

        if stored_status in PASSING_PREFLIGHT_STATUSES:
            return "warnings" if result.warnings or stored_status in {"warnings", "warning"} else "passed"
        return "warnings" if result.warnings else "passed"

    def _create_package_dir(
        self,
        *,
        platform: str,
        queue_item_id: str,
        label: str,
        exported_dt: datetime,
    ) -> Path:
        date_dir = self._manual_posts_root() / exported_dt.strftime("%Y-%m-%d")
        date_dir.mkdir(parents=True, exist_ok=True)
        base_name = f"{_slug(platform)}-{_slug(label)}-{_slug(queue_item_id)}"
        candidate = date_dir / base_name
        suffix = 2
        while candidate.exists():
            candidate = date_dir / f"{base_name}-{suffix}"
            suffix += 1
        candidate.mkdir(parents=False)
        return candidate

    def _manual_posts_root(self) -> Path:
        if self.export_root is not None:
            return self.export_root
        settings = load_app_settings(self.database_path)
        data_dir = Path(settings.localDataDirectory).expanduser()
        if not data_dir.is_absolute():
            data_dir = (REPO_ROOT / data_dir).resolve()
        return data_dir / "exports" / "manual-posts"

    def _package_label(
        self,
        scheduled_row: sqlite3.Row,
        generated_row: sqlite3.Row | None,
    ) -> str:
        schedule_metadata = _decode_json(scheduled_row["schedule_metadata_json"], {})
        for value in (
            schedule_metadata.get("headline"),
            schedule_metadata.get("hook"),
            generated_row["headline"] if generated_row and "headline" in generated_row.keys() else None,
            scheduled_row["caption_snapshot"],
        ):
            if isinstance(value, str) and value.strip():
                return value[:48]
        return "post"

    def _build_media_manifest(
        self,
        package_dir: Path,
        media_rows: list[sqlite3.Row],
        *,
        copy_media: bool,
    ) -> dict[str, Any]:
        media_entries: list[dict[str, Any]] = []
        media_dir = package_dir / "media"
        copied_any = False
        for row in media_rows:
            original_path = row["original_path"] or ""
            source_path = _resolve_local_path(original_path)
            copied_path = None
            copied = False
            if copy_media and source_path and source_path.exists() and source_path.is_file():
                media_dir.mkdir(parents=True, exist_ok=True)
                safe_name = f"{_slug(row['id'])}-{_safe_filename(row['file_name'] or source_path.name)}"
                destination = _unique_path(media_dir / safe_name)
                shutil.copy2(source_path, destination)
                copied = True
                copied_any = True
                copied_path = str(destination)
            media_entries.append(
                {
                    "id": row["id"],
                    "fileName": row["file_name"],
                    "mediaType": row["media_type"],
                    "mimeType": row["mime_type"],
                    "fileSizeBytes": row["file_size_bytes"],
                    "originalPath": original_path,
                    "copied": copied,
                    "copiedPath": copied_path,
                }
            )
        return {
            "mediaCopied": copied_any,
            "mediaCopyMode": "copied" if copied_any else "referenced_local_paths",
            "note": (
                "Media files remain in the local media library unless copied into this package."
            ),
            "media": media_entries,
        }

    def _post_markdown(
        self,
        *,
        queue_row: sqlite3.Row,
        scheduled_row: sqlite3.Row,
        generated_row: sqlite3.Row | None,
        brand_row: sqlite3.Row | None,
        schedule_metadata: dict[str, Any],
        hashtags: list[str],
        media_manifest: dict[str, Any],
    ) -> str:
        media_lines = [
            f"- {item['fileName'] or item['id']}: {item['originalPath']}"
            for item in media_manifest["media"]
        ] or ["- No linked media."]
        headline = _first_text(schedule_metadata.get("headline"), generated_row["headline"] if generated_row else None)
        hook = _first_text(schedule_metadata.get("hook"), generated_row["hook"] if generated_row else None)
        cta = _first_text(schedule_metadata.get("callToAction"), generated_row["call_to_action"] if generated_row else None)
        business_name = brand_row["business_name"] if brand_row else "Unknown brand"
        return "\n".join(
            [
                "# Manual Posting Package",
                "",
                "This package is local-only. It is not an automatic publish.",
                "",
                f"- Platform: {queue_row['platform']}",
                f"- Business: {business_name}",
                f"- Scheduled time: {scheduled_row['scheduled_for']} ({scheduled_row['timezone']})",
                f"- Queue item: {queue_row['id']}",
                "",
                "## Hook / Headline",
                "",
                hook or headline or "No hook/headline provided.",
                "",
                "## Caption",
                "",
                scheduled_row["caption_snapshot"].strip(),
                "",
                "## CTA",
                "",
                cta or "No CTA provided.",
                "",
                "## Hashtags",
                "",
                " ".join(hashtags) if hashtags else "No hashtags provided.",
                "",
                "## Media",
                "",
                *media_lines,
                "",
                "## Notes",
                "",
                scheduled_row["user_notes"] or "No notes.",
                "",
            ]
        )

    def _posting_instructions(
        self,
        queue_row: sqlite3.Row,
        scheduled_row: sqlite3.Row,
        media_manifest: dict[str, Any],
    ) -> str:
        media_step = (
            "Attach the copied media files from the `media/` folder."
            if media_manifest["mediaCopied"]
            else "Open the local media library paths listed in `media-manifest.json`."
        )
        return "\n".join(
            [
                "# Posting Instructions",
                "",
                "This is not an automatic publish. No social platform API was called.",
                "",
                f"Platform: {queue_row['platform']}",
                f"Scheduled time: {scheduled_row['scheduled_for']} ({scheduled_row['timezone']})",
                "",
                "1. Open the correct social account manually.",
                "2. Double-check that the account, media, caption, and scheduled context are correct.",
                f"3. {media_step}",
                "4. Paste the caption from `caption.txt`.",
                "5. Add hashtags from `hashtags.txt` if that file exists.",
                "6. Review the post one final time before posting manually.",
                "7. After you manually post or finish exporting, return to the app and mark as manually exported.",
                "",
                "Real publishing remains disabled by policy.",
                "",
            ]
        )

    def _write_text(self, path: Path, body: str) -> str:
        _ensure_no_secret_markers(body)
        path.write_text(body, encoding="utf-8")
        return path.name

    def _write_json(self, path: Path, value: dict[str, Any]) -> str:
        body = json.dumps(value, indent=2, sort_keys=True) + "\n"
        _ensure_no_secret_markers(body)
        path.write_text(body, encoding="utf-8")
        return path.name

    def _require_queue_row(self, queue_item_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM publish_queue_items WHERE id = ?",
                (queue_item_id,),
            ).fetchone()
        if row is None:
            raise ManualExportError(
                f"Publish queue item {queue_item_id!r} does not exist.",
                ["queue_item_not_found"],
            )
        return row

    def _require_scheduled_row(self, scheduled_post_id: str) -> sqlite3.Row:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM scheduled_posts WHERE id = ?",
                (scheduled_post_id,),
            ).fetchone()
        if row is None:
            raise ManualExportError(
                f"Scheduled post {scheduled_post_id!r} does not exist.",
                ["scheduled_post_not_found"],
            )
        return row

    def _generated_post_row(self, generated_post_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT * FROM generated_posts WHERE id = ?",
                (generated_post_id,),
            ).fetchone()

    def _brand_row(self, brand_profile_id: str) -> sqlite3.Row | None:
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            return connection.execute(
                "SELECT * FROM brand_profiles WHERE id = ?",
                (brand_profile_id,),
            ).fetchone()

    def _media_rows(self, media_ids: list[str]) -> list[sqlite3.Row]:
        if not media_ids:
            return []
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                f"""
                SELECT id, media_type, original_path, file_name, mime_type, file_size_bytes
                FROM media_assets
                WHERE id IN ({', '.join('?' for _ in media_ids)})
                """,
                tuple(media_ids),
            ).fetchall()
        by_id = {row["id"]: row for row in rows}
        return [by_id[media_id] for media_id in media_ids if media_id in by_id]


def _decode_json(raw_value: str | None, fallback: Any) -> Any:
    if not raw_value:
        return fallback
    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        return fallback
    return decoded if isinstance(decoded, type(fallback)) else fallback


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _coerce_datetime(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(value, datetime):
        parsed = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(microsecond=0)
    normalized = value.strip()
    parsed = datetime.fromisoformat(
        normalized.removesuffix("Z") + "+00:00" if normalized.endswith("Z") else normalized
    )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value).lower()).strip("-")
    return (slug or "item")[:64]


def _safe_filename(value: str) -> str:
    name = Path(value).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-")
    return cleaned or f"media-{uuid.uuid4()}"


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    stem = path.stem
    suffix = path.suffix
    counter = 2
    while True:
        candidate = path.with_name(f"{stem}-{counter}{suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _resolve_local_path(raw_path: str) -> Path | None:
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    return path


def _first_text(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _ensure_no_secret_markers(body: str) -> None:
    lowered = body.lower()
    found = sorted(marker for marker in SECRET_MARKERS if marker in lowered)
    if found:
        raise ManualExportError(
            "Manual export output contained a secret-like marker and was blocked.",
            ["secret_marker_detected"],
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local manual posting package for a publish queue item. "
            "This never publishes to social platforms."
        )
    )
    parser.add_argument("--database", help="Path to the local SQLite database.")
    parser.add_argument("--queue-item-id", required=True, help="Publish queue item ID.")
    parser.add_argument(
        "--copy-media",
        action="store_true",
        help="Copy linked local media files into the export package when found.",
    )
    args = parser.parse_args()

    try:
        result = ManualExportService(args.database).export_queue_item(
            args.queue_item_id,
            copy_media=args.copy_media,
        )
    except ManualExportError as error:
        print(f"Manual export blocked: {error}")
        if error.error_codes:
            print("Error codes: " + ", ".join(error.error_codes))
        raise SystemExit(1) from error

    print("Manual export package created.")
    print(f"  queue_item_id: {result.queueItemId}")
    print(f"  export_path: {result.exportPath}")
    print(f"  files_created: {', '.join(result.filesCreated)}")
    print("  real_publishing: disabled")


if __name__ == "__main__":
    main()
