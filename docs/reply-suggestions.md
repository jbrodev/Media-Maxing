# Local AI Reply Suggestions

The reply suggestion service creates local drafts for Engagement Inbox items. It does not send comments, messages, or direct replies to any social platform.

## What It Uses

Each suggestion uses:

- the linked Brand Brain;
- the engagement text, platform, sentiment, intent, and priority;
- optional related generated-post context;
- the versioned `comment_reply_suggestion_v1` prompt;
- the configured AI provider, with deterministic offline `mock` mode as the default.

## Safety Review

Every suggestion is reviewed locally before storage. Safety flags use `info`, `warning`, or `critical` severity.

Critical flags include:

- `invented_price`
- `invented_availability`
- `unsupported_guarantee`
- `aggressive_language`
- `privacy_risk`
- `complaint_mishandled`
- `approval_bypass_attempt`

Critical flags remain visible for the later reply approval workflow. Suggestions always set `needs_human_review = true`.

## Local History

Generating a suggestion creates:

1. a new `reply_suggestions` row;
2. an Engagement Inbox status update to `reply_suggested`;
3. a `reply_approvals` audit row with action `suggest`.

Regeneration creates a new suggestion row. It never overwrites prior history.

## Verify Locally

Initialize, seed, and add fake inbox items:

```text
python -m scripts.db.init_db --database data/reply-suggestions-check.sqlite
python -m scripts.db.seed_demo --database data/reply-suggestions-check.sqlite
python -m scripts.services.engagement --database data/reply-suggestions-check.sqlite --brand-profile-id demo-brand-brightside-exterior-care --ingest-mock
```

Generate one local-only suggestion:

```text
python -m scripts.services.reply_suggestions --database data/reply-suggestions-check.sqlite --engagement-item-id mock-engagement-pricing-question
```

The command prints safe metadata only. It does not print inbox content, reply text, provider payloads, or private information.

## Limits

- Browser Inbox wiring comes later with the local API bridge.
- Local approval editing and approval actions are implemented separately.
- Real reply sending is not available.
- Real platform APIs are not called.
