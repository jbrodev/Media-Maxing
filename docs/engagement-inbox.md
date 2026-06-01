# Engagement Inbox Foundation

The Engagement Inbox foundation stores local conversation records for future owner review. It does not fetch real comments, scrape platforms, or send replies.

## Local Tables

- `engagement_items`: individual comments, mentions, reviews, lead messages, and notes.
- `engagement_threads`: local conversation groupings.
- `reply_suggestions`: editable local AI-assisted reply drafts for owner review.
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

When the static web shell is launched through the localhost bridge,
`apps/web/engagement.js` persists mock ingestion, inbox status updates, reply
suggestions, and local reply approvals to SQLite. Opening the HTML file
directly uses a temporary `localStorage` demo fallback with the same eight
clearly fake scenarios. Stable IDs prevent duplicate fixtures.

The screen supports:

- Summary counts for new items, reply needs, urgent items, complaints, leads, and spam.
- Platform, status, sentiment, intent, priority, source, date-range, and text filters.
- Local status updates for needs reply, ignored, archived, spam, escalated, and replied manually.
- A detail panel with local context and notes.
- Local mock AI reply suggestions with editable text, tone, confidence, recommended action, reason summary, and visible safety flags.
- Local approval, rejection, manual-reply tracking, escalation, spam marking, archive actions, and a reply audit history.

When launched through the localhost bridge, status changes persist to SQLite.
Direct-file mode persists browser-only demo state after refresh.

Reply approval is local approval only. It never sends content to a social platform. Marking an item replied manually means the owner handled the conversation outside the app.

## Privacy Rules

- Keep unnecessary private customer details out of the inbox.
- Prefer `content_redacted` for future UI search and display when sensitive text exists.
- Do not scrape platforms.
- Do not fetch real comments by default.
- Do not send real replies.
- Complaints and urgent leads should be escalated for human review.

## Not Built Yet

- Manual engagement entry screen.
- CSV import parser.
- Real platform comment/message sync.
- Real reply sending.
