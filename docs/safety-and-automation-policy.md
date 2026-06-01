# Safety and Automation Policy

This app is local-first, mock-first, and approval-first. It may help draft, organize, schedule locally, and export content, but the MVP must not publish real posts or send real replies.

AI can draft content and suggest replies. The user must review and approve before anything is considered ready for publishing, manual posting, or replying.

## Core Product Safety Rules

### 1. No Publishing Without User Approval During MVP

Generated posts must default to `needs_review`. The app must not publish real posts during the MVP. Scheduling and manual export should only use approved, safe drafts.

Future real publishing must require explicit platform-specific work, approval gates, preflight checks, audit logs, emergency pause enforcement, secure token handling, and user confirmation.

All future scheduling and publishing flows should use the local approval queue service in `scripts/services/approval_queue.py` before treating a draft as ready. That service checks approval status, emergency pause, critical safety flags, brand profile existence, caption presence, linked media existence, and platform requirements.

Scheduled posts must snapshot caption and media at scheduling time. Later edits to the original draft must not silently change already scheduled content unless the user explicitly updates or reschedules that scheduled item.

### 2. No Fake Testimonials

AI must not invent testimonials, reviews, customer names, customer quotes, before/after claims, or social proof. Testimonials may only be used when the user provides the source content and confirms it is allowed to be used.

### 3. No Invented Guarantees

AI must not invent guarantees, promised outcomes, pricing, availability, certifications, licensing, insurance, awards, or credentials. Claims should come from the Brand Brain or another user-provided source of truth.

### 4. No Aggressive Replies

AI reply suggestions must stay calm, helpful, and professional. The app should avoid hostile, defensive, manipulative, threatening, or shaming replies.

### 5. No Scraping Social Media Platforms

The app must not scrape social platforms. Future integrations should use approved platform APIs and documented permission scopes only.

### 6. No Plain-Text API Tokens When Avoidable

API keys, access tokens, refresh tokens, authorization codes, client secrets, bearer tokens, and raw OAuth state values must not be stored in plain text when avoidable.

Token storage should default to `placeholder_not_stored` until secure storage is implemented. Future secure storage should prefer operating system keychain, encrypted local storage, or another documented secure storage layer.

### 7. No Auto-Replies To Complaints Without Approval

The app must not automatically reply to complaints, negative comments, urgent leads, sensitive messages, reviews, direct messages, or customer disputes. AI may draft a reply suggestion, but the user must review and approve it.

### 8. No Deleting Content Without Confirmation

Deleting drafts, media, scheduled posts, exports, analytics imports, engagement items, AI memory, backups, or settings should require clear user confirmation when deletion features are implemented.

Destructive actions should prefer archive, cancel, or disable states when practical.

### 9. Clear Approval Logs

The app should record review decisions and safety-relevant changes. Approval logs should capture what was approved, rejected, edited, archived, or sent back for revision.

Editing approved content should require reapproval or clearly record what changed.
For the MVP, the stricter rule is used: editing an approved draft changes its status back to `needs_review` and records an `edited_requires_reapproval` approval log entry. The edited draft must be approved again before any future scheduling, manual export readiness, or real publishing eligibility can treat it as approved.

Critical safety flags block scheduling and future publishing eligibility. Current critical flags include `invented_testimonial`, `fake_testimonial`, `unsupported_guarantee`, `approval_bypass_attempt`, `missing_approval`, `emergency_pause_enabled`, `emergency_pause_conflict`, `missing_required_brand_claim_support`, `unsupported_claim`, and `private_customer_info_risk`.

Publish queue rows are local readiness records only. Queue statuses such as `ready`, `mock_published`, and `manually_exported` must never be presented as real platform publishing.

Manual export packages are local files only. Creating an export package must not call social APIs, upload media, include secrets, or automatically change the queue item to `manually_exported`. The user marks that state only after manually posting or finishing the export workflow.

The local job runner may move due scheduled posts to `queued` and queue items to `ready` only after local preflight passes. If emergency pause is enabled, the runner must keep items blocked or paused and must not mark them ready.

Preflight uses a centralized MVP platform requirement matrix. Matrix limits are placeholders until future official platform API verification. Warnings such as missing future connected accounts do not block manual export readiness; errors such as critical safety flags, missing required media, missing captions, and emergency pause do block readiness.

### 10. Emergency Pause Or Kill Switch

The app must include an emergency pause or kill switch before meaningful automation is enabled.

Emergency pause should block:

- Scheduling new posts.
- Moving scheduled posts to ready queue.
- Creating manual posting packages in the MVP.
- Mock publishing.
- Future real publishing.
- Future real reply sending.
- Automation above the approval queue.
- Local job runner readiness changes, except safe blocked or paused states.
- AI auto-action placeholders.

Emergency pause should not block:

- Viewing data.
- Editing Brand Brain.
- Editing drafts.
- Importing media.
- Creating backups.
- Exporting diagnostic reports.
- Reading analytics.
- Adding manual notes.

The kill switch is a stronger operational control for stopping risky automation or integration behavior. It should clearly report what it blocks.

## Token And Secret Handling

Never expose, log, commit, print, or include in frontend responses:

- Access tokens.
- Refresh tokens.
- Authorization codes.
- Client secrets.
- API keys.
- Bearer tokens.
- Raw OAuth state values.
- Raw provider responses containing credentials.
- Encrypted token blobs unless explicitly needed in a server-only context.

Backups and diagnostics must redact secrets by default.

## Approval Defaults

MVP defaults:

```text
automationLevel = approval_queue
requireApprovalBeforePublishing = true
requireApprovalBeforeReplying = true
emergencyPauseEnabled = false
```

Drafts, reply suggestions, scheduled posts, and future publish queue items should keep approval state visible to the user.

## Automation Levels

### Level 1: Manual Assist

The app helps the user draft, organize, and export content. The user manually copies or posts everything outside the app.

Allowed:

- Brand Brain editing.
- Local media organization.
- AI draft generation.
- Manual export.
- Local notes.

Not allowed:

- Real publishing.
- Real replies.
- Autonomous scheduling.

### Level 2: Approval Queue

AI creates drafts or reply suggestions that require human review. This is the MVP default.

Allowed:

- AI-generated post drafts.
- AI reply suggestions.
- Review, edit, approve, reject, archive, or request revision.
- Approval logs.

Not allowed:

- Auto-approval.
- Real publishing.
- Real reply sending.

### Level 3: Semi-Auto Scheduling

Approved drafts can be scheduled locally after safety checks pass.

Allowed:

- Local-only calendar scheduling.
- Scheduling eligibility checks.
- Emergency pause enforcement.
- Local publish queue readiness checks.
- Creating local `publish_queue_items` and `publish_attempts` audit records.
- Running the local job runner manually or in a local development loop.

Not allowed:

- Real platform publishing.
- Real replies.
- Scheduling drafts that are not approved.
- Scheduling drafts with critical safety flags.
- Storing OAuth tokens or provider credentials in queue or attempt records.
- Treating local `queued` or `ready` states as real publishing.

### Level 4: Safe Auto-Posting

Planned future level. Real posting may only be considered after explicit platform-specific implementation with strict safety gates.

Required before enabling:

- Real OAuth working.
- Secure token storage.
- Platform API docs verified.
- Account selection.
- App review requirements understood.
- Preflight tests.
- Approval gates.
- Emergency pause enforcement.
- Post-publish audit logs.
- Rate limit and error handling.
- Manual export fallback.
- Explicit user confirmation.

Not allowed in the MVP:

- Real auto-posting.
- Approval bypass.
- Publishing while emergency pause is enabled.

### Level 5: Autonomous Content Engine

Planned future level. The app may recommend strategy based on Brand Brain, approvals, rejections, analytics, engagement, and AI memory.

Allowed when implemented safely:

- Strategy recommendations.
- Weekly reports.
- AI memory suggestions with evidence.
- Content planning assistance.

Not allowed unless a future explicit safety-gated task enables it:

- Autonomous real publishing.
- Autonomous real replies.
- Claims based on weak evidence.
- Guaranteed performance promises.
- Deleting or overwriting user data without confirmation.

## Non-Negotiable MVP Position

Manual export is the safe publishing path until real platform publishing is intentionally implemented later. The MVP should make approval state, mock/demo labels, local-only behavior, and disabled real publishing obvious to the user.
