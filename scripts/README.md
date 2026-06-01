# Scripts

Project utility scripts live here.

Current scripts:

- `db/init_db.py`: Initializes or migrates the local SQLite database.
- `db/seed_demo.py`: Seeds safe fake demo data for local development and UI placeholders.
- `db/brand_profiles.py`: Provides the Brand Brain data model and CRUD service.
- `db/settings.py`: Provides the local app settings data layer.
- `db/media_storage.py`: Imports local image and video files into ignored local media storage and records metadata in SQLite.
- `services/preflight.py`: Centralized platform requirement matrix and local preflight validation service for scheduled posts and queue items.
- `services/publish_queue.py`: Local-only Publish Queue actions for manual-export completion and mock publishing. It never calls platform APIs.
- `services/manual_export.py`: Creates local manual posting packages for eligible Publish Queue items. It writes files only and never publishes.
- `jobs/local_runner.py`: Runs local scheduled-post readiness jobs and preflight checks. It updates SQLite only and never publishes.

Job runner examples:

```powershell
python -m scripts.jobs.local_runner --database data/app.sqlite --once
python -m scripts.jobs.local_runner --database data/app.sqlite --watch --interval-seconds 30
```

Manual export example:

```powershell
python -m scripts.services.manual_export --database data/app.sqlite --queue-item-id QUEUE_ITEM_ID
```
