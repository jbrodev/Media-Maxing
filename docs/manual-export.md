# Manual Export

Manual export is the safe posting path before real social platform APIs exist.

It creates a local posting package for a Publish Queue item. It does not publish, upload, call social APIs, connect accounts, or mark the queue item as manually exported.

## Export Location

The Python service writes packages under the local data export directory:

```text
data/exports/manual-posts/YYYY-MM-DD/platform-slug-queueItemId/
```

If a custom local data directory is configured in app settings, that directory is used instead of `data/`.

Existing export folders are never overwritten. A numeric suffix is added when the same item is exported more than once.

## Files Created

Each package includes:

- `caption.txt`: final scheduled caption snapshot only.
- `hashtags.txt`: hashtags when the scheduled post has them.
- `post.md`: human-readable package summary with platform, scheduled time, caption, CTA, media list, and notes.
- `metadata.json`: queue, scheduled post, generated post, platform, due time, preflight status, media IDs, safety flags, and local/manual-only markers.
- `media-manifest.json`: linked local media records and file paths.
- `posting-instructions.md`: manual posting steps and reminders.

By default, media files are referenced by local path in `media-manifest.json`. The service can copy found local media into a package `media/` folder when run with `--copy-media`.

## Eligibility

Manual export is allowed only when:

- Emergency pause is off.
- The queue item exists.
- The related scheduled post exists.
- The queue item is not canceled, processing, or skipped.
- Stored preflight status has not failed.
- Current local preflight has no errors.

Warning-only preflight is allowed. Missing connected account is a warning because real publishing is not implemented.

Failed preflight blocks export. A development-only override exists in the service API for local testing, but the MVP UI should not expose it.

## Command

```text
python -m scripts.services.manual_export --database data/app.sqlite --queue-item-id QUEUE_ITEM_ID
```

Optional media copy:

```text
python -m scripts.services.manual_export --database data/app.sqlite --queue-item-id QUEUE_ITEM_ID --copy-media
```

The command prints the export path and file names only. It does not print secrets.

## Publish Queue UI

The static web app has an **Export package** button in Publish Queue detail.
When launched through the localhost bridge, the button calls the Python
exporter and creates the package under `data/exports`. Direct-file mode keeps
a browser-only text download fallback for static UI inspection.

Use **Mark manually exported** only after the user has manually posted or finished exporting. Exporting a package does not change queue status by itself.

The backend action for that final state is `PublishQueueService.mark_manually_exported`. It records a local `publish_attempt` with `attempt_type = manual_export` and marks the related scheduled post `completed`.

## Manual Posting Steps

1. Export the package.
2. Open `posting-instructions.md`.
3. Open the correct social account manually.
4. Copy the caption from `caption.txt`.
5. Add hashtags from `hashtags.txt` if it exists.
6. Attach or locate media using `media-manifest.json`.
7. Double-check the account, caption, media, safety flags, and platform fit.
8. Post manually outside the app, or keep the package for later.
9. Return to the Publish Queue and mark the item manually exported only after the manual work is done.

## Safety Notes

- Real publishing remains disabled.
- No external APIs are called.
- No OAuth tokens or API keys are included.
- Export folders live under ignored local data paths and should not be committed.
- Caption comes from the scheduled post snapshot, so later draft edits do not silently change the export.
- The user should double-check account, media, caption, and safety flags before posting manually.
