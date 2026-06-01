# Local-First Database Schema

This document describes the local SQLite schema for the MVP. The schema is implemented with SQL migrations in `scripts/db/migrations/`.

The database should live in the local app data directory, such as `data/app.sqlite` during development. JSON fields are acceptable for SQLite where they keep the MVP simpler, especially for arrays, metadata, safety evidence, prompt metadata, and mock provider data.

## General Principles

- SQLite is the MVP database.
- Data is local-first by default.
- Real platform publishing is not implemented.
- Real reply sending is not implemented.
- Raw access tokens, refresh tokens, API keys, authorization codes, and client secrets must not be stored in normal app tables.
- Mock/demo data must be clearly distinguishable from manual, imported, or future platform data.
- Deleting user data should require explicit confirmation in the app when implemented.

## users

### Purpose

Stores the local app user, owner, or operator profile. The MVP may only need one user, but keeping this table makes future multi-profile support easier.

### Important Fields

- `id`: primary key.
- `display_name`: user-facing name.
- `email`: optional local contact email.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- One `users` row can own many `brand_profiles`.
- One `users` row can own one or more `app_settings` records, though the MVP should usually use one active settings record.

### Privacy/Security Notes

- Email is optional and should not be required for local use.
- Do not assume a cloud login exists.
- Do not store social platform credentials here.

## brand_profiles

### Purpose

Stores the Brand Brain: business identity, voice, services, audience, supported claims, offers, and content preferences.

### Important Fields

- `id`: primary key.
- `user_id`: owner reference.
- `business_name`: business name used in drafts.
- `description`: plain-language business description.
- `voice`: brand voice and writing style.
- `services_json`: services offered.
- `locations_json`: service areas or store locations.
- `target_audience`: intended customer types.
- `supported_claims_json`: claims the business has evidence for.
- `blocked_phrases_json`: words or claims AI should avoid.
- `preferences_json`: extra Brand Brain fields such as tagline, industry, tone rules, preferred words, common CTAs, hashtags, website, phone, email, approval rules, safety rules, and example posts.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Belongs to `users`.
- Referenced by `content_ideas`, `generated_posts`, and `ai_memory`.
- May be used by future reply suggestions and safety checks.

### Privacy/Security Notes

- Brand claims should be user-provided and supportable.
- AI must not invent testimonials, certifications, licensing, insurance, pricing, awards, guarantees, or availability.
- Private customer information should not be stored in brand-level fields.
- Brand profile contact fields are business contact fields only. Do not store API keys, OAuth tokens, or private customer data here.

## social_accounts

### Purpose

Stores safe metadata for mock or future connected social accounts.

### Important Fields

- `id`: primary key.
- `brand_profile_id`: optional Brand Brain owner reference for account-specific business profiles.
- `platform`: one of `facebook`, `instagram`, `threads`, `youtube`, `tiktok`, `linkedin`, or `x`.
- `platform_account_id`: optional provider account identifier.
- `display_name`: user-facing account name.
- `username`: optional handle or channel username.
- `profile_url`: optional public profile URL.
- `profile_image_url`: optional public profile image URL.
- `account_type`: `personal`, `business`, `creator`, `page`, `channel`, `organization`, or `unknown`.
- `connection_status`: `not_connected`, `connecting`, `connected`, `limited`, `expired`, `revoked`, `disconnected`, `error`, or `requires_reauth`.
- `capabilities_json`: safe feature/capability metadata.
- `granted_scopes_json`: safe list of granted scope names.
- `missing_scopes_json`: safe list of missing scope names.
- `requires_reauth`: boolean flag for accounts that need reconnecting.
- `last_connected_at`: optional connection timestamp.
- `last_validated_at`: optional last connector check timestamp.
- `disconnected_at`: optional disconnect timestamp.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Can have one or more `platform_tokens` records.
- Can have `connector_audit_logs` and `connector_health_checks`.
- May be associated with future account-aware preflight checks.

### Privacy/Security Notes

- This table must not contain access tokens, refresh tokens, authorization codes, client secrets, or raw OAuth responses.
- Frontend account DTOs should be built from this table and should remain token-free.
- Missing connected accounts should not block manual export.

## platform_tokens

### Purpose

Stores encrypted token fields or secure-storage metadata for future OAuth integrations. MVP default is `placeholder_not_stored`, which means token values are not stored.

### Important Fields

- `id`: primary key.
- `social_account_id`: related social account.
- `platform`: social platform ID.
- `token_type`: `oauth_access`, `oauth_refresh`, `long_lived_access`, `page_access`, `app_token_placeholder`, or `unknown`.
- `encrypted_access_token`: nullable server-only encrypted token field. This remains null for `placeholder_not_stored`.
- `encrypted_refresh_token`: nullable server-only encrypted refresh token field. This remains null for `placeholder_not_stored`.
- `access_token_expires_at`: optional access token expiry timestamp.
- `refresh_token_expires_at`: optional refresh token expiry timestamp.
- `scope`: granted or expected scopes as a safe string.
- `token_version`: integer token record version.
- `encryption_status`: `encrypted`, `keychain`, `placeholder_not_stored`, `insecure_dev_only`, or `missing`.
- `last_refresh_at`: optional token refresh timestamp.
- `revoked_at`: optional local revoke/disconnect timestamp.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Belongs to `social_accounts`.
- May be referenced by future connector health checks.

### Privacy/Security Notes

- Raw token storage is forbidden by default.
- A database check prevents `placeholder_not_stored` and `missing` rows from containing encrypted token blobs.
- Do not log token values.
- Do not expose token data to frontend responses.
- Do not include tokens in normal backups or diagnostics.

## oauth_states

### Purpose

Stores local OAuth state tracking for future and mock OAuth flows. The table stores only a hash of the OAuth state value.

### Important Fields

- `id`: primary key.
- `platform`: social platform ID.
- `state_hash`: unique hash of the OAuth state. Raw state values are never stored.
- `redirect_uri`: callback URI used for the flow.
- `code_verifier_hash`: optional PKCE verifier hash. Raw verifiers are not stored.
- `requested_scopes_json`: requested scopes.
- `status`: `created`, `consumed`, `expired`, or `failed`.
- `created_at`: creation timestamp.
- `expires_at`: expiry timestamp.
- `consumed_at`: optional consume timestamp.
- `error_message`: optional safe error text.

### Relationships

- May lead to a `social_accounts` row after a safe mock or future real callback.
- OAuth lifecycle events should be recorded in `connector_audit_logs`.

### Privacy/Security Notes

- Never store raw OAuth state values.
- Never store authorization codes in this table.
- State values should expire quickly, around 10 minutes unless future configuration safely changes this.

## connector_audit_logs

### Purpose

Stores safe local audit history for connector actions.

### Important Fields

- `id`: primary key.
- `platform`: social platform ID.
- `social_account_id`: optional related social account.
- `action`: `oauth_start`, `oauth_callback`, `token_exchange`, `token_refresh`, `connection_validate`, `disconnect`, `reauth_required`, or `error`.
- `status`: safe action result status.
- `message`: safe human-readable message.
- `safe_metadata_json`: redacted metadata only.
- `created_at`: creation timestamp.

### Relationships

- May reference `social_accounts`.

### Privacy/Security Notes

- Do not log tokens, authorization codes, client secrets, bearer headers, OAuth state values, or raw provider responses.
- Safe metadata should be redacted before insertion.

## connector_health_checks

### Purpose

Stores local health/readiness snapshots for scaffolded or mock connectors.

### Important Fields

- `id`: primary key.
- `platform`: social platform ID.
- `social_account_id`: optional related social account.
- `health_status`: local health status such as `mock_connected`, `scaffolded`, or `requires_reauth`.
- `feature_status`: connector feature status such as `mock_only` or `scaffolded`.
- `message`: safe human-readable message.
- `safe_metadata_json`: redacted metadata only.
- `checked_at`: health check timestamp.
- `created_at`: creation timestamp.

### Relationships

- May reference `social_accounts`.

### Privacy/Security Notes

- Health checks must not call real platform APIs unless future integration flags explicitly allow it.
- Health check rows must not contain secrets or raw provider responses.

## media_assets

### Purpose

Stores metadata for local uploaded media such as photos, videos, processed files, and thumbnails.

### Important Fields

- `id`: primary key.
- `media_type`: `image`, `video`, `audio`, `document`, or `unknown`.
- `original_path`: local path to original media.
- `processed_path`: optional local path to processed media.
- `thumbnail_path`: optional local thumbnail path.
- `file_name`: original or display filename.
- `mime_type`: detected media type.
- `file_size_bytes`: file size captured during local import.
- `tags_json`: user or AI-assisted tags.
- `job_context_json`: optional job, campaign, location, or project context. The MVP stores AI-useful context here, including `serviceType`, `locationName`, `city`, `state`, `projectDate`, and `contentAngle`.
- `metadata_json`: local storage metadata such as original filename, safe internal filename, dimensions, duration, or other local metadata. The MVP stores editable library fields here, including `title`, `description`, `qualityRating`, `usageStatus`, and `notes`.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Can be referenced by `content_ideas`.
- Can be referenced by `generated_posts`.
- May contribute evidence to `ai_memory`.

### Privacy/Security Notes

- Real user media should remain local and should not be committed.
- The media storage service copies supported images and videos into the local app data directory under `data/media/originals` by default.
- The MVP does not upload media to cloud services or run heavy processing.
- Metadata editing is manual for now. AI media analysis and auto-tagging are not implemented.
- Diagnostics should avoid including private media contents.
- Exports should include only intentional media manifests or copied files selected by the user.

## content_ideas

### Purpose

Stores content concepts before AI generation or manual drafting.

### Important Fields

- `id`: primary key.
- `brand_profile_id`: related Brand Brain.
- `goal`: content goal such as `get_leads`, `educate_customer`, or `build_trust`.
- `angle`: content angle such as `before_after`, `faq`, or `seasonal`.
- `target_platforms_json`: planned platforms.
- `media_asset_ids_json`: selected media references.
- `notes`: user instructions or context.
- `status`: idea state such as `open`, `used`, `archived`, or `rejected`.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Belongs to `brand_profiles`.
- Can reference many `media_assets` through JSON IDs for MVP simplicity.
- Can have many `generated_posts`.

### Privacy/Security Notes

- Notes may contain business-sensitive context and should stay local.
- Ideas should not imply content was posted.
- AI should treat idea notes as context, not verified claims.

## generated_posts

### Purpose

Stores AI-generated or manually created draft posts. Generated content defaults to review, not approval.

### Important Fields

- `id`: primary key.
- `content_idea_id`: optional related idea.
- `brand_profile_id`: related Brand Brain.
- `platform`: target platform.
- `headline`: optional short draft headline/title.
- `hook`: optional opening hook.
- `caption`: drafted post text.
- `short_caption`: optional short variant for compact surfaces.
- `long_caption`: optional long variant.
- `call_to_action`: optional CTA text.
- `hashtags_json`: generated or edited hashtags.
- `media_asset_ids_json`: related local media.
- `content_goal`: generation goal such as `show_transformation` or `get_leads`.
- `content_angle`: generation angle such as `before_after` or `educational`.
- `target_audience`: target audience snapshot used during generation.
- `campaign_name`: optional campaign context.
- `offer_context`: optional offer context supplied by the user.
- `user_instructions`: optional user instructions supplied during generation.
- `suggested_post_time`: AI-suggested local posting time, not a scheduled time.
- `alt_text`: optional accessibility text for associated media.
- `notes`: local draft notes.
- `score_json`: structured generated draft score.
- `approval_status`: `draft`, `needs_review`, `approved`, `rejected`, `revision_requested`, or `archived`.
- `safety_flags_json`: warnings and blockers.
- `generation_provider`: `mock`, `openai`, `anthropic`, or `local`.
- `prompt_metadata_json`: prompt ID, version, and rendering metadata.
- `provider_metadata_json`: safe provider metadata, never secrets.
- `prompt_template_id`: prompt template identifier used to create the draft.
- `prompt_version`: prompt template version.
- `generation_timestamp`: timestamp from the generation bundle.
- `last_scheduled_at`: last time this draft was copied into a local scheduled post.
- `publish_readiness_status`: local readiness summary such as `not_scheduled`, `waiting`, `ready`, `blocked`, `manually_exported`, or `mock_published`.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Belongs to `brand_profiles`.
- May belong to `content_ideas`.
- Can reference many `media_assets` through JSON IDs for MVP simplicity.
- Can have many `scheduled_posts`.
- Can have many `publish_queue_items` through scheduled posts.
- Can have many `approval_logs`.

### Privacy/Security Notes

- Drafts must not be treated as published content.
- Saving generated content to drafts must create local `generated_posts` records with `approval_status = needs_review`.
- Saving generated content to drafts must also create `approval_logs` records so the origin is traceable.
- Critical safety flags should block scheduling and future publishing eligibility.
- Editing an approved draft should require reapproval or leave a clear audit trail.
- Provider metadata must not include API keys, tokens, raw responses containing credentials, or secrets.

## scheduled_posts

### Purpose

Stores approved posts scheduled on the local-only content calendar. A scheduled post is a snapshot of a generated draft at the time the user schedules it.

### Important Fields

- `id`: primary key.
- `generated_post_id`: related approved draft.
- `brand_profile_id`: Brand Brain copied from the source draft.
- `platform`: target platform.
- `scheduled_for`: intended scheduled time stored as an ISO timestamp.
- `timezone`: timezone selected or inherited from app settings.
- `status`: `scheduled`, `queued`, `missed`, `canceled`, `completed`, `failed`, or `needs_attention`.
- `caption_snapshot`: caption copied at scheduling time.
- `media_asset_ids_json`: media asset IDs copied at scheduling time.
- `media_snapshot_json`: backward-compatible media snapshot field for older local records.
- `platform_account_id`: nullable future account reference.
- `publish_queue_item_id`: nullable queue item reference for convenience.
- `recurrence_rule`: nullable future recurrence rule.
- `is_recurring_template`: boolean flag for future recurring content templates.
- `user_notes`: optional local scheduling notes.
- `preflight_snapshot_json`: safety/preflight result at scheduling time.
- `schedule_metadata_json`: additional snapshot fields such as hashtags, CTA, hook, headline, alt text, and safety flags.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.
- `canceled_at`: cancellation timestamp when the local schedule item is canceled.

### Relationships

- Belongs to `generated_posts`.
- Belongs to `brand_profiles`.
- Should have one `publish_queue_items` row for local queue readiness.
- May lead to one `published_posts` record for mock, manual export, or future real publish records.
- Can have many `approval_logs`.

### Privacy/Security Notes

- Scheduling must require an approved draft, no critical safety flags, and emergency pause disabled.
- Snapshot fields prevent later draft edits from silently changing scheduled content. A user must explicitly reschedule or update the scheduled item to change the scheduled copy.
- Scheduling is local-only in the MVP.

## publish_queue_items

### Purpose

Stores local publish queue readiness for scheduled posts. This table separates calendar scheduling from queue processing so the app can say whether a scheduled item is waiting, ready, blocked, manually exported, or mock-published without calling real social APIs.

### Important Fields

- `id`: primary key.
- `scheduled_post_id`: related scheduled post.
- `generated_post_id`: source generated draft.
- `brand_profile_id`: related Brand Brain.
- `platform`: target platform.
- `queue_status`: `waiting`, `ready`, `blocked`, `processing`, `mock_published`, `manually_exported`, `failed`, `canceled`, or `skipped`.
- `due_at`: timestamp when the item should become ready for local queue checks.
- `timezone`: source timezone for display and local schedule interpretation.
- `priority`: integer priority for future queue sorting.
- `preflight_status`: `not_checked`, `passed`, `warnings`, `errors`, or `blocked`.
- `preflight_errors_json`: blocking readiness errors.
- `preflight_warnings_json`: non-blocking warnings.
- `mock_publish_enabled`: boolean flag for future mock publishing only.
- `manual_export_required`: boolean flag indicating manual export is the safe path.
- `last_checked_at`: last local preflight/readiness check timestamp.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Belongs to `scheduled_posts`.
- Belongs to `generated_posts`.
- Belongs to `brand_profiles`.
- Can have many `publish_attempts`.

### Privacy/Security Notes

- Queue readiness is local-only.
- Missing connected accounts should warn for manual export, not block manual export.
- `ready`, `mock_published`, and `manually_exported` must not be described as real platform publishing.
- Emergency pause must block moving items to `ready`, mock publishing, and future real publishing.

## publish_attempts

### Purpose

Stores local audit records for queue checks and safe non-real publish actions. Attempts can record preflight checks, mock publishing, manual export, or a future disabled real-publish placeholder.

### Important Fields

- `id`: primary key.
- `publish_queue_item_id`: related queue item.
- `scheduled_post_id`: related scheduled post.
- `platform`: target platform.
- `attempt_type`: `preflight`, `mock_publish`, `manual_export`, or `future_real_publish`.
- `attempt_status`: `started`, `succeeded`, `failed`, `skipped`, or `blocked`.
- `started_at`: attempt start timestamp.
- `finished_at`: nullable finish timestamp.
- `error_code`: nullable machine-readable error code.
- `error_message`: nullable human-readable error message.
- `provider_response_json`: nullable safe response metadata. MVP rows must not store real provider credentials or raw token-bearing responses.
- `created_at`: creation timestamp.

### Relationships

- Belongs to `publish_queue_items`.
- Belongs to `scheduled_posts`.

### Privacy/Security Notes

- Attempt rows are audit records, not proof of real publishing.
- `future_real_publish` must remain disabled by policy until a later explicit real-platform task.
- `provider_response_json` must not include secrets, tokens, authorization codes, bearer values, or raw OAuth responses.

## local_job_locks

### Purpose

Stores short-lived local locks for the lightweight job runner so overlapping local readiness checks do not run at the same time.

### Important Fields

- `id`: primary key, currently `local_job_runner`.
- `owner`: generated runner owner ID for the current process.
- `locked_at`: when the lock was acquired.
- `expires_at`: when the lock can be cleaned up as stale.

### Relationships

- No direct foreign keys.
- Used by `scripts/jobs/local_runner.py`.

### Privacy/Security Notes

- Lock rows contain no secrets, tokens, media contents, customer data, or provider data.
- Stale locks can be cleaned locally by the runner.
- Locks only coordinate local SQLite work. They do not create OS scheduled tasks or cloud jobs.

## published_posts

### Purpose

Stores records for mock-published, manually exported, or future platform-published posts.

### Important Fields

- `id`: primary key.
- `scheduled_post_id`: optional related scheduled post.
- `generated_post_id`: optional source draft.
- `platform`: target platform.
- `publish_mode`: `mock`, `manual_export`, or `platform_api`.
- `external_post_id`: future provider post ID.
- `permalink`: future post URL.
- `published_at`: timestamp for mock/manual/future publish record.
- `metadata_json`: safe publish metadata.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- May belong to `scheduled_posts`.
- May belong to `generated_posts`.
- Can have many `engagement_items`.
- Can have many `analytics_snapshots`.

### Privacy/Security Notes

- The MVP must not create real platform posts.
- `publish_mode` must clearly distinguish `mock` and `manual_export` from future `platform_api`.
- Do not claim a post was sent externally unless a future real publishing implementation confirms it.

## engagement_items

### Purpose

Stores local, mock, manually entered, imported, or future guarded platform engagement such as comments, replies, mentions, reviews, and lead messages.

### Important Fields

- `brand_profile_id`, `platform`, and optional post/account IDs: local context links.
- `external_item_id` and `thread_id`: optional provider/import and local conversation references.
- `item_type` and `direction`: message shape and inbound/outbound/internal direction.
- `author_name`, `author_handle`, and `author_profile_url`: optional local display context. Store only what is needed.
- `content` and `content_redacted`: local original text and privacy-reduced display/search text.
- `sentiment`, `intent`, `priority`, `status`, and `requires_response`: inbox triage fields.
- `source`: `mock`, `manual`, `platform_api`, or `imported_csv`.
- `safety_flags_json` and `raw_data_json`: local warnings and mock/import metadata.

### Relationships

- May belong to `brand_profiles`, `social_accounts`, `generated_posts`, `scheduled_posts`, `published_posts`, and `engagement_threads`.
- May have many `reply_suggestions` and `reply_approvals`.

### Privacy/Security Notes

- Mock records must use fake labels and `source = mock`.
- Private customer data should be minimized and kept local.
- Scraping social platforms is not allowed.
- Replies are never sent externally by this model.

## engagement_threads

### Purpose

Groups local engagement items into a conversation or review thread.

### Important Fields

- `brand_profile_id`, `platform`, and optional `related_post_id`: local context.
- `external_thread_id`: optional future provider/import reference.
- `subject`, `status`, and `last_message_at`: inbox grouping and triage.

### Privacy/Security Notes

- Thread records remain local.
- `needs_attention` supports complaint and urgent-lead escalation without auto-replying.

## reply_suggestions

### Purpose

Stores one editable local AI or mock reply draft for owner review.

### Important Fields

- `engagement_item_id` and `brand_profile_id`: suggestion context.
- `suggested_reply`, `tone`, `confidence`, and `reasoning_summary`: local-review output.
- `safety_flags_json`: approval blockers and warnings.
- `provider`, `prompt_template_id`, and `prompt_version`: generation provenance.
- `status`: `generated`, `edited`, `approved`, `rejected`, or `archived`.

### Privacy/Security Notes

- Suggestions are drafts only.
- Approval does not send a reply.
- Critical safety flags must block approval until resolved.

## reply_approvals

### Purpose

Records local suggestion, edit, approval, rejection, escalation, spam, archive, and manual-reply decisions.

### Important Fields

- `reply_suggestion_id` and `engagement_item_id`: local workflow links.
- `action`, `previous_status`, `new_status`, `reason`, and `actor_type`: audit trail.

### Privacy/Security Notes

- Audit records should distinguish approval from actual manual replying.
- No action in this table sends content externally.

## engagement_imports

### Purpose

Audits mock ingestion, manual entry, CSV imports, and future guarded platform sync.

### Important Fields

- `source`, `platform`, `import_type`, and `status`: provenance.
- `records_imported`, `records_skipped`, and `error_message`: readable outcome.
- `imported_at` and `created_at`: timing.

### Privacy/Security Notes

- Mock ingestion uses fake data only.
- Future platform sync must remain behind explicit integration safety gates.

## analytics_snapshots

### Purpose

Stores point-in-time performance metrics from manual entry, mock/demo data, imported CSVs, estimates, or future platform APIs.

### Important Fields

- `id`: primary key.
- `published_post_id`: optional related post.
- `scheduled_post_id`: optional related local schedule item.
- `generated_post_id`: optional related draft.
- `brand_profile_id`: optional related Brand Brain. Older snapshots without a resolvable brand remain valid.
- `platform`: platform measured.
- `source`: `manual`, `mock`, `platform_api`, `imported_csv`, or `estimated`.
- `snapshot_date`: timestamp for the metrics snapshot.
- `impressions`, `reach`, `views`, `likes`, `comments`, `shares`, `saves`, and `clicks`: standard performance counts.
- `profile_visits`, `follows`, `leads`, `messages`, `calls`, and `website_clicks`: local conversion-oriented counts.
- `engagement_rate`, `click_through_rate`, and `lead_rate`: simple calculated rates.
- `raw_metrics_json`: optional extra platform-specific or import metadata.
- `notes`: optional local notes.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- May belong to `published_posts`.
- May belong to `scheduled_posts`, `generated_posts`, and `brand_profiles`.
- Can contribute to `post_performance_metrics`.
- Can contribute evidence to `ai_memory`.

### Privacy/Security Notes

- Mock analytics must be labeled as mock/demo.
- Manual analytics must be labeled as manual.
- Do not invent real analytics.
- Platform API metrics are future-only and must respect integration safety flags.

## post_performance_metrics

### Purpose

Stores a local aggregate performance view for a post so later analytics screens and learning services do not need to recalculate common totals on every read.

### Important Fields

- `id`: primary key.
- `generated_post_id`, `scheduled_post_id`, and `published_post_id`: optional lifecycle links.
- `brand_profile_id`: related Brand Brain.
- `platform`: measured platform.
- `content_goal` and `content_angle`: generation context used for later comparisons.
- `media_asset_ids_json`: related media IDs.
- `posted_at`, `first_snapshot_at`, and `latest_snapshot_at`: performance timeline.
- `total_*`: aggregate impression, reach, view, engagement, click, and lead totals.
- `engagement_rate`, `lead_rate`, and `performance_score`: local summary values.
- `trend`: `improving`, `flat`, `declining`, or `unknown`.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- May belong to `generated_posts`, `scheduled_posts`, and `published_posts`.
- Belongs to `brand_profiles`.
- Can contribute evidence to `content_insights` and `ai_memory`.

### Privacy/Security Notes

- Aggregates must preserve the provenance of their underlying snapshots.
- A score is a local comparison aid, not a guarantee or authoritative platform metric.

## analytics_imports

### Purpose

Stores an audit trail for manual entry, mock sync, CSV import, and future platform sync runs.

### Important Fields

- `id`: primary key.
- `source`: analytics source.
- `platform`: optional platform.
- `import_type`: `manual_entry`, `mock_sync`, `csv_upload`, or `platform_sync`.
- `status`: `pending`, `completed`, `partial`, or `failed`.
- `records_imported` and `records_skipped`: safe result counts.
- `error_message`: optional safe error message.
- `imported_at`: import timestamp.
- `created_at`: creation timestamp.

### Relationships

- No required foreign keys. Imported snapshots retain their own post and brand links.

### Privacy/Security Notes

- Import rows should not contain uploaded CSV contents, tokens, or raw provider responses.
- Error messages should avoid private customer details.

## content_insights

### Purpose

Stores explainable local observations and recommendations derived from performance, approvals, engagement, or media metadata.

### Important Fields

- `id`: primary key.
- `brand_profile_id`: related Brand Brain.
- `insight_type`: categorizes the observation, such as `best_content_type`, `lead_signal`, `media_signal`, `safety_signal`, or `recommendation`.
- `title` and `summary`: plain-language explanation.
- `evidence_json`: evidence IDs and data-point counts.
- `confidence`: `low`, `medium`, or `high`.
- `related_post_ids_json` and `related_media_asset_ids_json`: supporting local references.
- `recommended_action`: optional next step.
- `status`: `active`, `dismissed`, `applied`, or `archived`.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Belongs to `brand_profiles`.
- May reference posts, analytics snapshots, and local media through JSON evidence.
- Can contribute evidence to `ai_memory`.

### Privacy/Security Notes

- Insights should be explainable and evidence-backed.
- Low-confidence patterns must remain clearly labeled.
- Insights must not turn weak correlations into unsupported claims.

## weekly_reports

### Purpose

Stores local weekly summaries for later reporting screens.

### Important Fields

- `id`: primary key.
- `brand_profile_id`: related Brand Brain.
- `week_start_date` and `week_end_date`: report range.
- `summary`: plain-language overview.
- `wins_json`, `concerns_json`, and `recommendations_json`: structured report sections.
- `top_posts_json`, `platform_breakdown_json`, and `metric_totals_json`: local summary data.
- `generated_by`: `system`, `ai_mock`, `ai_provider`, or `manual`.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- Belongs to `brand_profiles`.
- May summarize `analytics_snapshots`, `post_performance_metrics`, and `content_insights`.

### Privacy/Security Notes

- Mock reports must use `generated_by = ai_mock`.
- Reports should distinguish fake demo metrics, manual metrics, and future API metrics.
- Reports are local summaries and should not include unnecessary private customer details.

## approval_logs

### Purpose

Stores human review and approval history for drafts, scheduled posts, queue-like states, and future reply suggestions.

The approval queue service records structured action metadata in `changed_fields_json` for status transitions. Future scheduling and publishing gates should read draft state through `scripts/services/approval_queue.py` rather than inferring readiness from logs alone.

### Important Fields

- `id`: primary key.
- `entity_type`: reviewed entity type, such as `generated_post`, `scheduled_post`, or future `reply_suggestion`.
- `entity_id`: reviewed entity ID.
- `action`: `approved`, `rejected`, `revision_requested`, `archived`, `edited`, or similar action.
- `actor_label`: local display label for who acted.
- `notes`: optional review notes.
- `changed_fields_json`: edited fields or summarized changes.
- `created_at`: creation timestamp.

### Relationships

- Can reference `generated_posts` by entity fields.
- Can reference `scheduled_posts` by entity fields.
- May be used as evidence for `ai_memory`.

### Privacy/Security Notes

- Approval logs should preserve a local audit trail for safety decisions.
- Logs may contain sensitive review notes and should stay local.
- Do not use approval logs to bypass future approval requirements.
- Editing an approved draft should create `edited_requires_reapproval`, set the draft back to `needs_review`, and preserve the edited fields in `changed_fields_json`.

## ai_memory

### Purpose

Stores learning records from approvals, rejections, analytics, engagement, media metadata, and Brand Brain updates.

### Important Fields

- `id`: primary key.
- `brand_profile_id`: optional related Brand Brain.
- `memory_type`: `brand_rule`, `content_preference`, `audience_learning`, `platform_learning`, `performance_learning`, `safety_learning`, `user_preference`, `rejected_strategy`, or `approved_strategy`.
- `title`: short memory label.
- `content`: plain-language memory.
- `summary`: backward-compatible legacy summary retained for existing local records.
- `confidence`: `low`, `medium`, or `high`.
- `evidence_json`: supporting record IDs or summarized evidence.
- `source`: provenance label such as `mock`, `manual`, or a future learning-service source.
- `status`: `active`, `archived`, or `superseded`.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- May belong to `brand_profiles`.
- May reference `generated_posts`, `approval_logs`, `analytics_snapshots`, `engagement_items`, and `media_assets` through evidence JSON.

### Privacy/Security Notes

- Do not delete memory automatically.
- Store evidence so the app can explain why it learned something.
- Be honest when data is weak.
- AI memory should not convert weak patterns into unsupported claims.
- Demo memory must be clearly labeled with `source = mock`.

## app_settings

### Purpose

Stores local app settings, safety controls, automation defaults, and integration feature flags.

### Important Fields

- `id`: primary key.
- `user_id`: optional owner reference.
- `automation_level`: `manual_assist`, `approval_queue`, `semi_auto_scheduling`, `safe_auto_posting`, or `autonomous_content_engine`.
- `require_approval_before_publishing`: default `true`.
- `require_approval_before_replying`: default `true`.
- `emergency_pause_enabled`: default `false`.
- `kill_switch_enabled`: default `false`.
- `integrations_mode`: default `mock`.
- `enable_real_network_calls`: default `false`.
- `enable_real_oauth`: default `false`.
- `enable_real_publishing`: default `false`.
- `token_storage_mode`: default `placeholder_not_stored`.
- `settings_json`: extra local settings.
- `created_at`: creation timestamp.
- `updated_at`: last update timestamp.

### Relationships

- May belong to `users`.
- Read by scheduling, publishing, connector, AI, and engagement services.
- Used by future safety center and diagnostics.

### Privacy/Security Notes

- MVP defaults must require approval and keep real publishing disabled.
- Emergency pause must block scheduling, queue readiness, mock publishing, future real publishing, future real replies, and unsafe automation.
- Settings should not store secrets.
- Real integration flags should fail closed when missing or invalid.
