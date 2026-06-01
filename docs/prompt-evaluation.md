# Prompt Evaluation

This app treats prompts as versioned product assets. A prompt change can alter tone, safety behavior, platform fit, and what gets stored as a draft, so each prompt version needs repeatable checks before it is trusted in the local workflow.

## Why Prompts Are Versioned

Prompts include an ID and version so generated drafts can record exactly what created them. This matters for debugging, comparing future prompt changes, and learning which prompt versions produce useful drafts.

Versioned prompts also make rollback possible. If a future prompt version starts producing weak or unsafe content, saved drafts and evaluation results can still point back to the earlier version.

## Why Structured Output Is Required

Generated content is stored as structured data, not loose text. The mock content generator returns `GeneratedContentBundle` objects with platform drafts, prompt metadata, safety review data, hashtags, calls to action, media links, and review status.

Structured output lets the app validate drafts before saving them, show safety flags clearly, and keep every generated post in `needs_review` until a human approves it.

## How Prompt Quality Is Tested

Prompt evaluation fixtures live in:

```text
scripts/evaluations/fixtures/
```

The evaluation runner loads each fixture, runs deterministic mock generation, and checks the result for structure, platform coverage, safety behavior, prompt metadata, and approval defaults.

Run the evaluation suite with:

```bash
python -m scripts.evaluations.prompt_evaluation
```

The script prints one `PASS` or `FAIL` line per fixture and includes readable failure reasons.

## Safety Rules Tested

Current fixtures check that generated drafts:

- stay local and use the mock provider only
- validate against the structured content schemas
- respect the selected platform list
- include non-empty captions
- include hooks when the fixture requires them
- include hashtags and CTAs only when expected
- carry prompt template metadata
- default to `needs_review`
- flag unsupported guarantees
- flag fake testimonials
- surface emergency pause conflicts
- block scheduling eligibility when critical safety flags or emergency pause are present
- show platform-specific differences for multi-platform generation

These tests do not publish, schedule, connect accounts, call real AI APIs, or require API keys.

## Evaluation Cases

The initial fixture set covers:

- local service business before/after transformation post
- educational FAQ post
- promotional offer post
- behind-the-scenes post
- trust-building post
- seasonal reminder post
- missing brand profile fields
- media with weak metadata
- user asks for an unsupported guarantee
- user asks for a fake testimonial
- emergency pause enabled
- multi-platform generation

## Adding New Evaluation Cases

Add a JSON object to a fixture file under `scripts/evaluations/fixtures/`. Each case should include:

- `name`
- `brandProfile`
- `selectedMedia`
- `selectedPlatforms`
- `contentGoal`
- `contentAngle`
- `userInstructions`
- `expected.safetyOutcome`
- `expected.expectedPlatformOutputs`
- `expected.blockedConditions`

Prefer checking structure and safety outcomes instead of exact long captions. Exact caption matching makes tests brittle and discourages prompt improvement.

## Comparing Future Prompt Versions

When a prompt changes, add a new prompt version and run this evaluation suite before using it in the app. Future comparison can store the same fixture outputs for two prompt versions and compare:

- pass/fail status
- safety flags
- platform coverage
- caption completeness
- tone differences
- owner approval readiness

Prompt comparison should never be treated as automatic approval. It is a quality signal for builders and future reviewers.

## Why Human Approval Is Still Required

Passing evaluations means the mock generator followed basic structure and safety expectations for known cases. It does not mean generated content is ready to publish.

The product still requires human approval because the business owner must confirm real-world facts, media context, offers, customer claims, and brand fit before anything moves toward scheduling, export, or future publishing.
