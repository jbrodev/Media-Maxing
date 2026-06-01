from __future__ import annotations

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
DEFAULT_DATABASE_PATH = REPO_ROOT / "data" / "app.sqlite"


def resolve_database_path(raw_path: str | os.PathLike[str] | None = None) -> Path:
    if raw_path:
        return Path(raw_path).expanduser().resolve()

    database_url = os.environ.get("DATABASE_URL")
    if database_url and database_url.startswith("file:"):
        return (REPO_ROOT / database_url.removeprefix("file:")).resolve()

    return DEFAULT_DATABASE_PATH


def _migration_files() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def initialize_database(database_path: str | os.PathLike[str] | Path | None = None) -> Path:
    db_path = resolve_database_path(database_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
              version TEXT PRIMARY KEY,
              applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        for migration_file in _migration_files():
            version = migration_file.stem
            already_applied = connection.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                (version,),
            ).fetchone()

            if already_applied:
                continue

            connection.executescript(migration_file.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT OR IGNORE INTO schema_migrations (version) VALUES (?)",
                (version,),
            )
        connection.commit()

    return db_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize or migrate the local SQLite database."
    )
    parser.add_argument(
        "--database",
        help="Path to the SQLite database. Defaults to DATABASE_URL or data/app.sqlite.",
    )
    args = parser.parse_args()

    db_path = initialize_database(args.database)
    print(f"Initialized local SQLite database at {db_path}")


if __name__ == "__main__":
    main()
