# Prompt Registry

Prompts are treated as versioned product assets, not random strings.
Every template has an id, version, declared inputs, an output contract,
safety rules, and an immutable template body. Construction-time
validation refuses to import a malformed template, so a broken prompt
fails fast instead of reaching the model.

## Files

- `scripts/ai/prompts/__init__.py` — public re-exports.
- `scripts/ai/prompts/registry.py` — core types and lookup functions.
- `scripts/ai/prompts/templates/` — one Python file per template
  version. Each file defines a module-level `TEMPLATE` constant.
- `tests/test_prompt_registry.py` — registry, shape, rendering, and
  definition tests.

## Public API

```python
from scripts.ai.prompts import (
    PromptTemplate,
    PromptInputSpec,
    PromptDefinitionError,
    PromptRegistryError,
    PromptRenderError,
    REQUIRED_SECTIONS,
    get_prompt,
    list_prompts,
    list_prompt_ids,
    list_versions_for_family,
)
```

## Required section headers

Every template body must contain these section headers in plain text:

```
ROLE
GOAL
CONTEXT
INPUTS
CONSTRAINTS
SAFETY RULES
OUTPUT FORMAT
ACCEPTANCE CRITERIA
```

A missing section header raises `PromptDefinitionError` at import time.

## Placeholder syntax

Variables use `{{ name }}`. This keeps `{` and `}` in JSON examples from
clashing with `str.format`. Construction-time validation enforces:

- Every placeholder in the template body is declared in
  `expected_inputs`.
- Every required input is referenced at least once in the body.
- Names are valid Python identifiers.

## Rendering a prompt

```python
from scripts.ai.prompts import get_prompt

template = get_prompt("platform_post_generator_v1")

rendered = template.render({
    "business_name": "Brightside Exterior Care Demo",
    "brand_voice": "Helpful, neighborly, practical.",
    "services": ["pressure washing", "gutter cleaning"],
    "supported_claims": ["uses careful surface checks before cleaning"],
    "blocked_phrases": ["guaranteed results"],
    "target_audience": "Local homeowners",
    "locations": ["Demo City"],
    "content_goal": "show_transformation",
    "content_angle": "before_after",
    "media_notes": ["id: media-driveway-before; stage: before"],
    "user_instructions": "Keep it honest. Mention seasonal timing.",
    "requested_platforms": ["instagram", "facebook"],
})
```

- Missing required inputs → `PromptRenderError`.
- Unknown variable names → `PromptRenderError`.
- Optional inputs that are omitted render as `[not provided]`.
- Empty lists render as `[none listed]`.
- List inputs render as `- item` bullets so the model sees a clear
  enumeration.

## Adding a new prompt version

1. Create `scripts/ai/prompts/templates/<family>_v<n>.py`. Use the
   existing files as a guide; the file must define a module-level
   `TEMPLATE = PromptTemplate(...)` constant.
2. The new `id` must end with `_v<n>` and the `version` field must match
   (for example `id="platform_post_generator_v2"`, `version="v2"`).
3. Add the new module's import to `_build_registry()` in
   `scripts/ai/prompts/registry.py` and include the constant in the
   `templates` tuple.
4. Run `python -m unittest tests.test_prompt_registry`. The
   `list_versions_for_family` test will now report two versions for the
   family; you may want to add an assertion for the new id.

Older versions stay registered so existing drafts that reference them
remain reproducible. Do not edit an old template body to "fix" a
problem — bump to a new version instead. This preserves prompt history
for evaluations.

## Required templates (v1)

| Id | Purpose |
|---|---|
| `content_strategy_brief_v1` | Plans 3–5 honest post ideas for a window. |
| `platform_post_generator_v1` | Generates one draft per requested supported platform. |
| `caption_variants_generator_v1` | Produces a fixed number of caption variants. |
| `hashtag_generator_v1` | Suggests platform-appropriate hashtags. |
| `safety_review_v1` | Reviews a draft and emits flags + blocking flags. |
| `draft_improvement_v1` | Revises an existing draft per owner feedback. |
| `comment_reply_suggestion_v1` | Suggests one local-review reply for an engagement item. |

## Safety notes

- No template instructs the model to publish anything. Every template
  is draft-only.
- Every template forbids invented testimonials, prices, availability,
  certifications, insurance, awards, and guarantees that are not in
  `supported_claims`.
- `safety_review_v1` defines a standard vocabulary of safety flags and
  requires `blocking_flags ⊆ flags`. This vocabulary will be used by
  the local safety check module in a later step.
- `comment_reply_suggestion_v1` defaults to local review and explicitly
  forbids auto-replies; it also requires escalation on sensitive items.
- `to_metadata()` returns a logging- and UI-safe snapshot. It does not
  include the full body, so it is safe to expose to a Settings UI or
  log line.
