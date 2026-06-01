# Roadmap

This roadmap keeps the project local-first, mock/demo-first, and safety-first. AI should draft content first, then the user reviews and approves it before scheduling, manual export, future publishing, or future replying.

Real publishing and real replies are disabled until future platform-specific work adds strict safety gates, secure token handling, preflight checks, audit logs, emergency pause enforcement, and explicit user confirmation.

## Phase 1: Local Content Generator

### Goal

Create the first local workflow for turning Brand Brain context and selected media into AI-assisted social post drafts.

### Features

- Brand Brain basics for business name, services, voice, locations, audience, supported claims, and blocked phrases.
- Local media selection from the future Media Library structure.
- Content goal and content angle inputs.
- Mock AI provider as the default generator.
- Platform-specific draft output for supported platform IDs.
- Safety flags and prompt metadata on generated drafts.
- Drafts default to `needs_review`.

### What Is Not Included Yet

- Real AI provider calls.
- Persistent database implementation.
- Full Media Library UI.
- Approval queue UI.
- Scheduling.
- Publishing.
- Social account connections.
- Analytics or engagement features.

### Acceptance Criteria

- User can describe brand context and request draft content in mock/demo mode.
- Generated content is clearly marked as a draft.
- Generated content is not approved automatically.
- Generated content is not scheduled or published automatically.
- Safety rules prevent invented testimonials, fake claims, unsupported guarantees, and fake social proof.

## Phase 2: Drafts, Approval Queue, and Calendar

### Goal

Persist drafts, let users review and approve them, and schedule approved drafts on a local-only calendar.

### Features

- Saved generated posts.
- Draft statuses: `draft`, `needs_review`, `approved`, `rejected`, `revision_requested`, and `archived`.
- Approval actions with approval logs.
- Edit flow that requires reapproval or records changes clearly.
- Calendar view for locally scheduled content.
- Scheduling eligibility checks.
- Local-only scheduled post snapshots.
- Emergency pause enforcement for scheduling and queue readiness.

### What Is Not Included Yet

- Real publishing.
- Real social API integration.
- Auto-approval.
- Autonomous scheduling.
- Engagement inbox.
- Platform analytics imports.

### Acceptance Criteria

- Only approved drafts can be scheduled.
- Drafts with critical safety flags cannot be scheduled.
- Editing an approved draft records the change or requires reapproval.
- Scheduled posts snapshot caption and media at scheduling time.
- Emergency pause blocks new scheduling.
- User approval remains required before content is treated as ready.

## Phase 3: Meta Integration

### Goal

Add safe scaffolding for Facebook, Instagram, and Threads without enabling real publishing.

### Features

- Meta platform registry entries.
- Mock OAuth flow for local testing.
- Connected Accounts screen for safe account metadata.
- Token storage abstraction with `placeholder_not_stored` as the default.
- Safe account DTOs that exclude tokens and secrets.
- Account readiness checks for preflight.
- Meta setup documentation.
- Disabled-by-policy publishing methods.

### What Is Not Included Yet

- Real publishing to Facebook, Instagram, or Threads.
- Real comment replies or DMs.
- Real OAuth unless separately enabled behind explicit safety flags.
- App review completion.
- Token storage in raw database fields.
- Scraping Meta platforms.

### Acceptance Criteria

- Meta integration can run in mock/demo mode.
- Connected account metadata never exposes tokens.
- Missing accounts warn for manual export but do not block it.
- Any publishing method returns disabled-by-policy.
- Real OAuth and real network calls remain disabled by default.
- User approval is still required before future publishing eligibility.

## Phase 4: Analytics Dashboard

### Goal

Track and visualize post performance using mock, manual, imported, estimated, or future platform data.

### Features

- Analytics snapshot model and service.
- Manual analytics entry.
- Mock/demo analytics clearly labeled.
- Basic metrics such as impressions, reach, views, likes, comments, shares, saves, clicks, and leads.
- Simple calculated rates with documented limitations.
- Analytics Dashboard views by platform, post, and date range.
- Content insight candidates for future AI learning.

### What Is Not Included Yet

- Real platform analytics API imports unless added later.
- Claims that mock analytics are real.
- Complex attribution.
- Paid ads analytics.
- Autonomous strategy changes.

### Acceptance Criteria

- Mock data is visibly labeled as mock/demo.
- Manual data is visibly labeled as manual.
- The app does not invent real analytics.
- Dashboard can show performance for local/mock/manual records.
- Calculated metrics handle missing or zero denominators safely.
- Analytics can inform future learning without overstating weak evidence.

## Phase 5: Engagement Inbox

### Goal

Manage engagement locally and generate AI-assisted reply suggestions that require user review.

### Features

- Engagement item model and local inbox.
- Mock engagement ingestion.
- Statuses such as `new`, `needs_reply`, `reply_suggested`, `reply_approved`, `replied_manually`, `ignored`, `archived`, `spam`, and `escalated`.
- AI reply suggestions using Brand Brain and engagement context.
- Reply safety flags and recommended actions.
- Local reply approval workflow.
- Manual reply tracking.

### What Is Not Included Yet

- Real comment replies.
- Real DMs.
- Auto-replies.
- Scraping social platforms.
- Automatic handling of complaints, urgent leads, negative comments, or sensitive messages.

### Acceptance Criteria

- Reply suggestions are clearly local suggestions only.
- No reply is sent externally.
- User approval is required before a reply is considered approved.
- Critical reply safety flags block approval until edited or resolved.
- Sensitive or risky engagement can be escalated.
- The app never claims a reply was sent unless the user marks a manual reply or future real sending confirms it.

## Phase 6: YouTube, TikTok, LinkedIn, and X Integrations

### Goal

Scaffold additional platform connectors safely while preserving mock-first behavior and disabled publishing.

### Features

- Platform registry entries for YouTube, TikTok, LinkedIn, and X.
- Mock OAuth support.
- Setup instructions for each platform.
- Connector health check scaffolds.
- Per-platform feature flags.
- Account readiness in preflight checks.
- Disabled-by-policy publishing methods.

### What Is Not Included Yet

- Real publishing to YouTube, TikTok, LinkedIn, or X.
- Real replies, comments, or DMs.
- Real API calls by default.
- Platform app review completion.
- Production token storage.
- Automated content posting.

### Acceptance Criteria

- Each connector can report planned/scaffolded/mock-only status.
- Missing credentials fail safely.
- Real network calls are disabled by default.
- Publishing remains disabled even when connectors exist.
- Manual export remains available as the safe path.
- User approval remains required for future publishing readiness.

## Phase 7: Autonomous Content Strategy Engine

### Goal

Use Brand Brain, approved/rejected drafts, analytics, engagement, and AI memory to recommend better content strategy over time.

### Features

- AI memory records with evidence and confidence.
- Learning from approvals, rejections, analytics, engagement, media metadata, and user preferences.
- Weekly report generation.
- Strategy recommendations by platform, goal, angle, and content format.
- Safety learning from rejected or flagged content.
- Clear confidence labels for weak, medium, and strong evidence.

### What Is Not Included Yet

- Autonomous real publishing.
- Autonomous real replies.
- Deleting memory automatically.
- Unsupported claims based on weak data.
- Guaranteed performance promises.
- Fully self-running social media management.

### Acceptance Criteria

- Strategy recommendations explain their evidence.
- Low-confidence recommendations are clearly labeled.
- AI memory does not invent claims, testimonials, pricing, availability, or guarantees.
- User remains in control of approvals, scheduling, exports, and future publishing.
- Emergency pause and kill switch still override automation.
- Autonomous publishing and autonomous replies remain locked unless a future explicit safety-gated task enables them.
