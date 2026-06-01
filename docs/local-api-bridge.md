# Localhost SQLite Bridge

The web shell can run through a small localhost-only Python server:

```powershell
python -m apps.api.local_server --database data/app.sqlite --port 8000
```

The server loads the repo-root `.env` file automatically when it exists. To
use a different local file, pass `--env-file PATH`. Secret values are never
printed during loading.

Then open:

```text
http://127.0.0.1:8000
```

The server binds to loopback addresses only. It serves the static files in
`apps/web` and exposes a thin JSON API backed by the local SQLite service
layer. It does not call social platforms, publish posts, send replies, or
expose token blobs.

## SQLite-backed browser workflows

When the web shell is opened through the localhost bridge, these actions
persist to SQLite:

- settings and Brand Brain updates
- media metadata edits
- generated preview saves to Drafts
- draft edits, approval actions, and scheduling
- Calendar reschedule, cancel, notes, and needs-attention actions
- Publish Queue preflight, mock completion, manual completion, and export
- manual and mock analytics snapshots
- analytics insight status updates
- mock engagement ingestion, inbox status updates, reply suggestions, and
  local reply approvals
- mock connected-account creation, local validation scaffolds, and disconnect
- server-safe Social Integration Setup status with masked secret fields

The bridge hydrates the existing browser adapters from `/api/bootstrap` so
the static UI can keep its current rendering code while SQLite remains the
source of truth.

## Direct-file fallback

Opening `apps/web/index.html` directly still works as a local demo fallback.
In that mode, the browser adapters use `localStorage`. Direct-file mode is
useful for static UI inspection, but it is not the durable SQLite-backed app
path.

Media file import remains a browser-demo action for now. The Python media
storage service already imports local files safely, but the static browser
shell does not yet have a trusted desktop file-picker bridge that can pass an
absolute local source path to it.

## Safety boundary

- The server refuses non-loopback binding.
- Normal connected-account responses use token-safe DTOs.
- OAuth mock connect consumes local state without returning raw token values.
- Manual export writes local files only.
- Mock publish records a local status only.
- Reply approval records a local decision only.
- Real publishing and real reply sending remain unavailable.
