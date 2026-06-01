# Engagement Inbox Foundation

The Engagement Inbox foundation stores local conversation records for future owner review. It does not fetch real comments, scrape platforms, or send replies.

## Local Tables

- `engagement_items`: individual comments, mentions, reviews, lead messages, and notes.
- `engagement_threads`: local conversation groupings.
- `reply_suggestions`: editable local reply drafts for a later AI-assisted workflow.
- `reply_approvals`: local decision history. Approval is not sending.
- `engagement_imports`: mock/manual/import/future-sync audit records.

## Mock Ingestion

The current ingestion service creates eight stable fake scenarios:

- Praise comment.
- Pricing question.
- Booking request.
- Complaint.
- Spam.
- Review-like comment.
- Urgent lead message.
- General comment.

Every fixture uses `source = mock`, a fake `Demo Visitor` label, and raw metadata stating that no real platform fetch or reply send occurred. Re-running ingestion skips existing stable fixture IDs and writes a new import audit with skip counts.

Run mock ingestion after initializing and seeding the local database:

```text
python -m scripts.services.engagement --database data/app.sqlite --brand-profile-id demo-brand-brightside-exterior-care --ingest-mock
```

## Browser Demo Screen

Open `apps/web/index.html#engagement` to use the current Engagement Inbox screen.

The static web shell does not have a browser-to-SQLite API bridge yet. For UI development, `apps/web/engagement.js` uses a temporary `localStorage` adapter with the same eight clearly fake scenarios. Click **Generate mock engagement** to add them. Stable IDs prevent duplicate browser fixtures.

The screen supports:

- Summary counts for new items, reply needs, urgent items, complaints, leads, and spam.
- Platform, status, sentiment, intent, priority, source, date-range, and text filters.
- Local status updates for needs reply, ignored, archived, spam, escalated, and replied manually.
- A detail panel with local context and notes.
- A visible placeholder for the future AI reply suggestion workflow.

Status changes persist in the browser after refresh. They do not update SQLite until a future local API bridge is added.

Reply approval is local approval only. It never sends content to a social platform. Marking an item replied manually means the owner handled the conversation outside the app.

## Privacy Rules

- Keep unnecessary private customer details out of the inbox.
- Prefer `content_redacted` for future UI search and display when sensitive text exists.
- Do not scrape platforms.
- Do not fetch real comments by default.
- Do not send real replies.
- Complaints and urgent leads should be escalated for human review.

## Not Built Yet

- Browser-to-SQLite API bridge for Engagement Inbox status changes.
- Manual engagement entry screen.
- CSV import parser.
- Real platform comment/message sync.
- AI reply suggestion service.
- Reply approval service.
- Real reply sending.
