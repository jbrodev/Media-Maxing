# Platform Preflight Matrix

The MVP preflight matrix lives in `scripts/services/preflight.py`.

It is intentionally local-only and uses practical placeholder limits. These values are not final production API limits. Real platform limits, scopes, media rules, aspect ratios, and account requirements must be verified against official platform API documentation when real integrations are implemented.

Requirement version:

```text
mvp-platform-requirements-v1
```

## Result Format

Preflight returns:

- `status`: `passed`, `warning`, or `failed`.
- `errors`: blocking issues.
- `warnings`: non-blocking issues.
- `info`: informational guidance.
- `checkedAt`: UTC timestamp.
- `platform`: platform ID.
- `requirementVersion`: matrix version used.
- `accountCheckStatus`: account readiness state, such as `missing_account`, `connected`, `limited`, or `requires_reauth`.
- `matchedSocialAccountId`: safe account ID when a matching account is found.
- `accountWarnings`: account issues that do not block manual export.
- `accountErrors`: account issues that block only future real publishing eligibility.
- `missingScopes`: scopes that may be required before future real publishing.
- `requiresReauth`: whether the matched account needs reconnect.
- `connectionStatus`: stored account connection status.
- `realPublishingEligible`: always false in this build because real publishing is disabled by policy.
- `manualExportEligible`: true when local content preflight has no blocking errors.
- `mockPublishEligible`: true only in mock mode when local content preflight has no blocking errors.

Errors block readiness. Warnings do not block readiness. Info is guidance only.

Account errors are scoped to future real publishing. They do not block manual export by themselves.

## Platform Requirements

### Instagram

- Media required: usually true for MVP preflight.
- Supported media: image, video.
- Caption max placeholder: 2,200 characters.
- Hashtags: allowed; use a small relevant set.
- Alt text: recommended when media is present.
- Video required: no.
- Title required: no.
- Description required: no.
- Future account connection: required for real publishing, warning only for manual export.
- Notes: carousel and exact media rules are future API work.

### Facebook

- Media required: no.
- Supported media: image, video.
- Caption max placeholder: 63,206 characters.
- Hashtags: optional and light.
- Alt text: recommended when media is present.
- Video required: no.
- Title required: no.
- Description required: no.
- Future account connection: required for real publishing, warning only for manual export.
- Notes: text-only posts are valid for MVP preflight.

### Threads

- Media required: no.
- Supported media: image, video.
- Text max placeholder: 500 characters.
- Hashtags: optional; concise text is preferred.
- Alt text: recommended when media is present.
- Video required: no.
- Title required: no.
- Description required: no.
- Future account connection: required for real publishing, warning only for manual export.
- Notes: short conversational text is preferred.

### TikTok

- Media required: yes.
- Supported media: video.
- Caption max placeholder: 2,200 characters.
- Hashtags: allowed; keep relevant.
- Alt text: not primary for MVP.
- Video required: yes.
- Title required: no.
- Description required: no.
- Future account connection: required for real publishing, warning only for manual export.
- Notes: vertical video is preferred but not enforced until video metadata exists.

### YouTube Shorts

- Media required: yes.
- Supported media: video.
- Description/caption max placeholder: 5,000 characters.
- Hashtags: allowed in description; keep relevant.
- Alt text: not primary for Shorts MVP.
- Video required: yes.
- Title required: yes.
- Description required: no.
- Future account connection: required for real publishing, warning only for manual export.
- Notes: vertical video is preferred but not enforced until video metadata exists.

### LinkedIn

- Media required: no.
- Supported media: image, video.
- Text max placeholder: 3,000 characters.
- Hashtags: recommended but limited.
- Alt text: recommended when media is present.
- Video required: no.
- Title required: no.
- Description required: no.
- Future account connection: required for real publishing, warning only for manual export.
- Notes: professional tone is recommended.

### X

- Media required: no.
- Supported media: image, video.
- Text max placeholder: 280 characters.
- Hashtags: optional; short text budget.
- Alt text: recommended when media is present.
- Video required: no.
- Title required: no.
- Description required: no.
- Future account connection: required for real publishing, warning only for manual export.
- Notes: strict short-text placeholder limit for MVP.

## Validation Checks

The preflight service checks:

- Draft approval status.
- Emergency pause.
- Supported platform.
- Caption/text presence.
- Caption/text length.
- Media requirement.
- Local media record existence.
- Supported media type.
- Video requirement.
- Critical safety flags.
- Brand profile existence.
- Queue item status.
- Title requirement.
- Unresolved revision request.
- Rejected or archived drafts.
- Scheduled time existence.
- Future account connection readiness.
- Missing account warning for manual export.
- Expired, revoked, or requires-reauth accounts.
- Missing account scopes for future real publishing.

## Account Readiness Rules

- Approved scheduled content can still be prepared without a connected account.
- Manual export is allowed without a connected account when all content checks pass.
- Mock publish can be eligible in mock mode without requiring a real connected account.
- Future real publishing requires a matching connected account, required scopes, and no reauth requirement.
- Future real publishing remains disabled in this build even when a mock account is connected.
- Missing accounts, missing scopes, and reconnect needs are shown clearly so the user can prepare for later integrations.

## Current Limitations

- No real platform APIs are called.
- No scraping is performed.
- Connected account checks are local readiness checks only. They do not call provider APIs.
- Exact API limits are TODOs for future official-doc verification.
- Vertical video preference is not enforced until media metadata includes dimensions/aspect ratio.

## Updating The Matrix

When real integrations are added later:

1. Verify platform limits and media requirements against official platform API documentation.
2. Update `PLATFORM_REQUIREMENT_MATRIX` in `scripts/services/preflight.py`.
3. Change `REQUIREMENT_VERSION` when behavior changes.
4. Update this document with the verified source and date.
5. Add or update tests in `tests/test_preflight_service.py`.
6. Confirm `tests/test_local_job_runner.py` and `tests/test_batch4_full_workflow.py` still pass.

Do not use scraped platform data. Do not treat placeholder limits as production-ready API guarantees.
