# Content Generation Service

`ContentGenerationService` is the orchestration layer that turns a
`ContentGenerationInput` into a validated `GeneratedContentBundle`. It
wires the brand profile, media metadata, prompt registry, AI provider,
and local safety review into one call. Mock is the default provider so
the service runs end-to-end without any API keys.

The generation service:

- does not persist drafts
- does not call the network
- does not depend on UI components
- is safe to invoke from tests or from a future API route

Draft persistence is handled by `scripts/db/drafts.py`. That service
takes a validated `GeneratedContentBundle`, saves selected platform
drafts into `generated_posts`, and writes one `approval_logs` record
per saved draft.

## Files

- `scripts/ai/safety.py` — deterministic local safety checks.
- `scripts/services/__init__.py`
- `scripts/services/content_generation.py` — `ContentGenerationService`,
  `SettingsSnapshot`, `ContentGenerationError`, and the
  `generate_content` convenience function.
- `scripts/db/drafts.py` — local SQLite draft persistence for generated
  bundles.
- `tests/test_ai_safety.py` — safety check unit tests.
- `tests/test_content_generation_service.py` — service scenario tests.
- `tests/test_draft_persistence.py` — generated draft save and approval
  log tests.

## Service flow

1. **Validate input.** `ContentGenerationInput.validate()` and
   `ContentGenerationOptions.validate()` run first. Bad enums and
   empty selected_platforms raise `SchemaValidationError` immediately.
2. **Resolve brand profile.** If `input.brand_profile` already has
   `businessName`, the service uses it. Otherwise it calls the
   configured `brand_loader(brand_id)` and merges any non-`None`
   fields from the input on top. A missing loader on an incomplete
   profile raises `ContentGenerationError`.
3. **Resolve media assets.** If every selected asset is `{"id": "..."}`
   and a `media_loader` is configured, the loader fetches the full
   metadata list. Otherwise the input list is used as-is.
4. **Load settings (optional).** If a `settings_loader` is configured,
   the service reads `emergency_pause_enabled`. The service accepts
   any object with that attribute or the camelCase `emergencyPauseEnabled`.
5. **Render prompt.** `get_prompt(options.prompt_id)` loads the prompt
   template (default `platform_post_generator_v1`) and renders it with
   variables built from the resolved brand, media, and input. The
   rendered prompt is not sent to the mock provider (mock is
   deterministic without it) but its length, template id, and version
   are recorded in `bundle.prompt_metadata` for traceability.
6. **Call provider.** `get_provider(options.provider_name)` returns the
   adapter. Mock is default; real adapters raise
   `ProviderDisabledError` until enabled in a later batch, which the
   service surfaces as `ContentGenerationError`.
7. **Schema validation.** `GeneratedContentBundle.__post_init__`
   validates structure as soon as the provider returns.
8. **Safety review.** `run_safety_checks(caption, brand_profile,
   emergency_pause_enabled=...)` runs on each post's caption.
   Per-post `safety_flags` are populated, and a bundle-level
   `GeneratedPostSafetyReview` is constructed with the deduped union
   of flags, blocking flags, and suggested fixes. `blocking_flags ⊆
   flags` always holds.
9. **Return bundle.** No persistence in this step.

## Safety flag categories produced by the local checker

| Flag | Trigger | Blocking? |
|---|---|---|
| `brand_mismatch` | Caption contains a phrase from brand `blockedPhrases` / `bannedWords`. | Yes |
| `unsupported_guarantee` | Caption contains guarantee language (`guarantee`, `100% satisfaction`, `we promise`, ...). | Yes |
| `fake_testimonial` | Caption contains testimonial markers (`one customer said`, `review:`, ...). | Yes |
| `unsupported_claim` | Caption mentions a credential word (`licensed`, `insured`, `certified`, ...) not present in `supportedClaims`. | Yes |
| `aggressive_language` | Caption contains pressure phrases (`act now`, `last chance`, `hurry`, `!!!`). | No (informational) |
| `platform_policy_risk` | Caption claims it was already posted (`we posted`, `now live on our page`, ...). | Yes |
| `missing_approval` | Caption contains explicit approval-bypass language (`auto-approved`, `skip review`, ...). | Yes |
| `emergency_pause_conflict` | Settings report `emergency_pause_enabled=True`. | No (scheduling/publishing are blocked downstream; generation stays available for review) |

## How to run generation locally

No API keys needed. From the repo root:

```bash
python -c "
from scripts.services.content_generation import generate_content
from scripts.ai.schemas import ContentGenerationInput, ContentGenerationOptions

bundle = generate_content(
    ContentGenerationInput(
        brand_profile={
            'id': 'brand-demo',
            'businessName': 'Brightside Exterior Care Demo',
            'voice': 'Helpful, neighborly, practical.',
            'services': ['pressure washing', 'gutter cleaning'],
            'supportedClaims': ['Uses careful surface checks before cleaning.'],
            'blockedPhrases': ['guaranteed results'],
            'targetAudience': 'local homeowners',
            'locations': ['Demo City'],
        },
        content_goal='show_transformation',
        content_angle='before_after',
        selected_platforms=['instagram', 'facebook'],
        selected_media_assets=[{'id': 'media-driveway-before'}],
        user_instructions='Keep claims supportable.',
    ),
    ContentGenerationOptions(number_of_variants=2),
)

for p in bundle.posts:
    print(p.platform, '->', p.status, p.safety_flags)
"
```

## How to plug in real loaders

`ContentGenerationService` accepts optional loaders so it can run
either standalone (with everything in the input) or against the local
SQLite layer:

```python
from scripts.db.brand_profiles import get_brand_profile
from scripts.db.settings import load_app_settings
from scripts.services.content_generation import (
    ContentGenerationService,
    SettingsSnapshot,
)

def load_brand(brand_id: str):
    profile = get_brand_profile(None, brand_id)
    return profile.__dict__ if profile else None

def load_settings():
    settings = load_app_settings(None)
    return SettingsSnapshot(
        emergency_pause_enabled=settings.emergencyPauseEnabled,
        ai_provider_preference=settings.aiProviderPreference,
    )

service = ContentGenerationService(
    brand_loader=load_brand,
    settings_loader=load_settings,
)
```

The service does not call the loaders unnecessarily: if the input
already includes a complete brand profile or fully-detailed media
assets, the loader is skipped.

## Saving generated drafts locally

Use `save_generated_bundle_to_drafts` after generation when the user
explicitly clicks Save to Drafts:

```python
from scripts.db.drafts import save_generated_bundle_to_drafts

saved = save_generated_bundle_to_drafts(
    "data/app.sqlite",
    bundle,
    selected_platforms=["instagram", "facebook"],
    save_request_id="ui-generated-save-token",
)

for draft in saved:
    print(draft.id, draft.platform, draft.approvalStatus)
```

The persistence flow:

1. Validates that the input is a `GeneratedContentBundle`.
2. Saves one `generated_posts` row per selected platform draft.
3. Forces `approval_status` to `needs_review`, even if the preview had
   a different status.
4. Stores media IDs, safety flags, scores, prompt template ID/version,
   generation provider, and generation timestamp.
5. Creates an `approval_logs` row with action
   `generated_saved_to_drafts`.
6. Rejects a repeated `save_request_id` so an accidental double click
   does not duplicate drafts.

No publishing, scheduling, social API calls, or real AI calls happen in
this save step.

## Safety, secrets, and persistence

- Mock provider is the default. Real providers stay disabled until
  the env gates from `docs/ai-providers.md` are flipped on.
- The generation service does not write to `generated_posts`; draft
  persistence is a separate explicit user action through
  `scripts/db/drafts.py`.
- API keys are never read here. The provider stubs read env vars in
  their own constructors and raise `ProviderDisabledError` if the
  gates are off.
- The service does not log captions or brand fields. Callers control
  what gets logged.
