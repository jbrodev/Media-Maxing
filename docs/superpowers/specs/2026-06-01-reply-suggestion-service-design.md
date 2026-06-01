# AI Reply Suggestion Service Design

## Goal

Add a local-only reply suggestion service for engagement items. Suggestions must use the Brand Brain, engagement context, the versioned `comment_reply_suggestion_v1` prompt, and the existing AI provider abstraction. Suggestions are drafts for owner review only. This feature must not send replies, call social APIs, publish content, or auto-approve anything.

## Chosen Approach

Create a dedicated `ReplySuggestionService` that orchestrates existing generic provider primitives. The service renders the reply prompt and calls `AIProvider.generate_structured()` with a reply-specific schema name. This keeps the provider abstraction generic and avoids adding a new required method to every real-provider stub.

The mock provider will add a deterministic `reply_suggestion` response branch for local development and tests. Real providers remain scaffolded and disabled by default.

## Data Model

Add an additive SQLite migration for `reply_suggestions`:

- `recommended_action`: one of `reply`, `ask_for_more_info`, `invite_to_call`, `invite_to_message`, `escalate`, `ignore`, or `mark_spam`.
- `needs_human_review`: boolean, default true.
- `blocking_flags_json`: compact list of critical safety flag codes.
- `safety_review_json`: detailed local review object with flag code, severity, and owner-facing message.

Keep the existing `safety_flags_json` list for compatibility with current types and future UI work.

Every generation creates a new `reply_suggestions` row. Regeneration never overwrites an older suggestion. This preserves an auditable local history for later approval and learning features.

## Service Flow

`ReplySuggestionService.generate()` will:

1. Load the engagement item and require a linked Brand Brain.
2. Load optional related generated-post context.
3. Render `comment_reply_suggestion_v1` with brand, engagement, related-post, and selected-tone context.
4. Resolve the requested provider, defaulting to `mock`.
5. Call `generate_structured()` with schema name `reply_suggestion`.
6. Validate and normalize the provider output.
7. Run deterministic local safety review against the inbound content and proposed reply.
8. Insert a new local `reply_suggestions` record with prompt provenance and safety details.
9. Set the engagement item status to `reply_suggested`.
10. Insert a `reply_approvals` audit row with action `suggest`.
11. Return a local DTO without any external-send capability.

## Prompt

Refine `comment_reply_suggestion_v1` to include:

- `ROLE`
- `GOAL`
- `BRAND CONTEXT`
- `ENGAGEMENT CONTEXT`
- `RELATED POST CONTEXT`
- `TONE`
- `SAFETY RULES`
- `OUTPUT FORMAT`
- `ACCEPTANCE CRITERIA`

The registry still requires its existing standard headers, so the prompt will retain compatible section headers where needed.

## Safety Review

The local safety reviewer will surface flags with severity `info`, `warning`, or `critical`.

Critical flags:

- `invented_price`
- `invented_availability`
- `unsupported_guarantee`
- `aggressive_language`
- `privacy_risk`
- `complaint_mishandled`
- `approval_bypass_attempt`

Critical flags remain visible and set `needs_human_review = true`. The later reply-approval service must block approval while critical flags remain unresolved.

Behavior rules:

- Praise: suggest a concise thank-you reply.
- Pricing question: invite the person to request an estimate; never invent a price.
- Booking request: ask for next-step details or invite a message; never invent availability.
- Complaint: use empathetic language and recommend escalation.
- Spam: recommend `mark_spam` with no outward reply.
- Urgent lead: provide a concise next step and recommend escalation for owner review.
- Unsupported guarantee request: avoid the guarantee and attach a critical `unsupported_guarantee` flag.
- Abusive content: recommend ignore or escalation rather than engagement.

## Error Handling

The service must fail before writing partial records when:

- the engagement item does not exist;
- the engagement item has no usable Brand Brain;
- the prompt cannot render;
- the provider is unknown or disabled;
- the provider returns malformed structured output.

SQLite writes for the suggestion, engagement-status update, and audit row occur in one transaction.

## Verification

Add tests for:

- praise, pricing, booking, complaint, spam, urgent lead, and unsupported-guarantee scenarios;
- prompt rendering and prompt provenance;
- local safety flag severity and critical blocking codes;
- engagement status update to `reply_suggested`;
- `reply_approvals` audit creation;
- regeneration creating a separate history row;
- malformed provider output failing without partial writes;
- no auto-approval and no external reply sending.

Add a CLI verification path that generates one local suggestion for an existing engagement item and prints only safe metadata.

## Documentation

Add `docs/reply-suggestions.md`, update `docs/database-schema.md`, and update shared TypeScript types. Documentation must say clearly that suggestions are local drafts and replies are never sent automatically.
