import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from scripts.db.init_db import initialize_database
from scripts.db.media_storage import (
    MediaStorageValidationError,
    ensure_media_directories,
    get_media_asset,
    import_media_file,
    list_media_assets,
    update_media_asset_metadata,
)


class LocalMediaStorageTest(unittest.TestCase):
    def test_ensure_media_directories_creates_expected_folders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local_data_dir = Path(temp_dir) / "data"

            directories = ensure_media_directories(local_data_dir)

            self.assertEqual(directories.mediaDirectory, local_data_dir / "media")
            self.assertTrue(directories.originalsDirectory.is_dir())
            self.assertTrue(directories.processedDirectory.is_dir())
            self.assertTrue(directories.thumbnailsDirectory.is_dir())

    def test_import_media_file_copies_image_and_stores_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "app.sqlite"
            local_data_dir = root / "app-data"
            source_dir = root / "source uploads"
            source_dir.mkdir()
            source_path = source_dir / "My Job Photo.JPG"
            source_path.write_bytes(b"\xff\xd8\xff\xe0fake-demo-jpeg")
            initialize_database(db_path)

            result = import_media_file(
                db_path,
                source_path,
                local_data_dir=local_data_dir,
            )

            stored_path = Path(result.internalPath)
            self.assertEqual(result.mediaType, "image")
            self.assertEqual(result.originalFilename, "My Job Photo.JPG")
            self.assertEqual(result.mimeType, "image/jpeg")
            self.assertEqual(result.fileSizeBytes, source_path.stat().st_size)
            self.assertTrue(result.internalFilename.endswith(".jpg"))
            self.assertNotIn(" ", result.internalFilename)
            self.assertTrue(stored_path.exists())
            self.assertEqual(stored_path.parent, local_data_dir / "media" / "originals")
            self.assertEqual(stored_path.read_bytes(), source_path.read_bytes())

            with closing(sqlite3.connect(db_path)) as connection:
                connection.row_factory = sqlite3.Row
                row = connection.execute(
                    "SELECT * FROM media_assets WHERE id = ?",
                    (result.id,),
                ).fetchone()

            self.assertIsNotNone(row)
            self.assertEqual(row["media_type"], "image")
            self.assertEqual(row["file_name"], "My Job Photo.JPG")
            self.assertEqual(row["original_path"], str(stored_path))
            self.assertEqual(row["mime_type"], "image/jpeg")
            self.assertEqual(row["file_size_bytes"], source_path.stat().st_size)
            metadata = json.loads(row["metadata_json"])
            self.assertEqual(metadata["originalFilename"], "My Job Photo.JPG")
            self.assertEqual(metadata["internalFilename"], result.internalFilename)
            self.assertEqual(metadata["storage"], "local")

    def test_import_media_file_copies_video_and_stores_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "app.sqlite"
            local_data_dir = root / "app-data"
            source_path = root / "quick-walkthrough.mp4"
            source_path.write_bytes(b"\x00\x00\x00\x18ftypmp42demo")
            initialize_database(db_path)

            result = import_media_file(
                db_path,
                source_path,
                local_data_dir=local_data_dir,
            )

            self.assertEqual(result.mediaType, "video")
            self.assertEqual(result.mimeType, "video/mp4")
            self.assertTrue(Path(result.internalPath).exists())

    def test_import_media_file_rejects_unsupported_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "app.sqlite"
            local_data_dir = root / "app-data"
            source_path = root / "notes.txt"
            source_path.write_text("not media", encoding="utf-8")
            initialize_database(db_path)

            with self.assertRaises(MediaStorageValidationError) as error:
                import_media_file(
                    db_path,
                    source_path,
                    local_data_dir=local_data_dir,
                )

            self.assertIn("Unsupported media type", str(error.exception))
            self.assertFalse((local_data_dir / "media" / "originals").exists())

            with closing(sqlite3.connect(db_path)) as connection:
                count = connection.execute("SELECT COUNT(*) FROM media_assets").fetchone()[0]

            self.assertEqual(count, 0)

    def test_import_media_file_rejects_oversized_files_before_copying(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "app.sqlite"
            local_data_dir = root / "app-data"
            source_path = root / "too-large.png"
            source_path.write_bytes(b"\x89PNG\r\n\x1a\noversized")
            initialize_database(db_path)

            with self.assertRaises(MediaStorageValidationError) as error:
                import_media_file(
                    db_path,
                    source_path,
                    local_data_dir=local_data_dir,
                    max_file_size_bytes=4,
                )

            self.assertIn("larger than the allowed limit", str(error.exception))
            self.assertFalse((local_data_dir / "media" / "originals").exists())

    def test_media_asset_metadata_can_be_read_and_updated_for_ai_context(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "app.sqlite"
            source_path = root / "driveway-after.jpg"
            source_path.write_bytes(b"\xff\xd8\xff\xe0fake-demo-jpeg")
            initialize_database(db_path)
            imported = import_media_file(
                db_path,
                source_path,
                local_data_dir=root / "app-data",
            )

            updated = update_media_asset_metadata(
                db_path,
                imported.id,
                {
                    "title": "Driveway after cleaning",
                    "description": "After photo showing a cleaner driveway surface.",
                    "tags": ["after", "driveway", "ready"],
                    "serviceType": "pressure washing",
                    "locationName": "Demo customer driveway",
                    "city": "Demo City",
                    "state": "NY",
                    "projectDate": "2026-05-12",
                    "contentAngle": "before_after",
                    "qualityRating": 5,
                    "usageStatus": "ready_for_generation",
                    "notes": "Pair with the before photo for a transformation draft.",
                },
            )

            self.assertEqual(updated.title, "Driveway after cleaning")
            self.assertEqual(updated.tags, ["after", "driveway", "ready"])
            self.assertEqual(updated.serviceType, "pressure washing")
            self.assertEqual(updated.locationName, "Demo customer driveway")
            self.assertEqual(updated.city, "Demo City")
            self.assertEqual(updated.state, "NY")
            self.assertEqual(updated.projectDate, "2026-05-12")
            self.assertEqual(updated.contentAngle, "before_after")
            self.assertEqual(updated.qualityRating, 5)
            self.assertEqual(updated.usageStatus, "ready_for_generation")
            self.assertEqual(updated.notes, "Pair with the before photo for a transformation draft.")

            loaded = get_media_asset(db_path, imported.id)
            self.assertEqual(loaded, updated)

            all_assets = list_media_assets(db_path)
            self.assertEqual([asset.id for asset in all_assets], [imported.id])

    def test_media_asset_metadata_rejects_invalid_angle_status_and_rating(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            db_path = root / "app.sqlite"
            source_path = root / "crew.mp4"
            source_path.write_bytes(b"\x00\x00\x00\x18ftypmp42demo")
            initialize_database(db_path)
            imported = import_media_file(
                db_path,
                source_path,
                local_data_dir=root / "app-data",
            )

            invalid_cases = [
                {"contentAngle": "magic"},
                {"usageStatus": "auto_published"},
                {"qualityRating": 6},
            ]

            for updates in invalid_cases:
                with self.subTest(updates=updates):
                    with self.assertRaises(MediaStorageValidationError):
                        update_media_asset_metadata(db_path, imported.id, updates)


if __name__ == "__main__":
    unittest.main()
