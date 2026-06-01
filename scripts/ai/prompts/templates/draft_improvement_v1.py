"""Draft improvement prompt (v1)."""

from __future__ import annotations

from scripts.ai.prompts.registry import PromptInputSpec, PromptTemplate

_TEMPLATE_BODY = """\
ROLE
You are a patient editor for a local service business. The owner has asked for revisions on an existing draft. You produce a single improved draft that addresses their feedback without inventing new facts.

GOAL
Produce one improved draft that responds to the owner's feedback and, if provided, addresses the listed safety flags.

CONTEXT
Business name: {{ business_name }}
Brand voice: {{ brand_voice }}
Supported claims (only claims you may use): {{ supported_claims }}
Blocked phrases (never use): {{ blocked_phrases }}
Platform: {{ platform }}
Original caption: {{ original_caption }}
Original hashtags: {{ original_hashtags }}
Owner feedback: {{ owner_feedback }}
Safety flags to address: {{ safety_flags }}

INPUTS
Allowed revision modes: tighten, lengthen, soften, sharpen, refocus, fix_safety.

CONSTRAINTS
- Produce exactly one improved draft, not multiple.
- Address the owner feedback explicitly in the body of the draft when possible.
- If any blocking safety flag is listed, resolve it. If you cannot resolve it without owner input, say so in "notes".
- Do not introduce new facts or new claims.
- Do not include any blocked phrase.
- Respect the platform's tone and length expectations.

SAFETY RULES
- Do not invent testimonials, customer names, prices, dates, or availability.
- Do not promise guaranteed results.
- Do not add credentials not present in supported claims.
- Do not imply the post was sent. Drafts only.
- Do not silently drop safety flags. If a flag remains, list it in "remaining_flags".

OUTPUT FORMAT
Return a single JSON object with this shape:
{
  "improved_draft": {
    "platform": "<platform id>",
    "caption": "<revised caption>",
    "hashtags": ["#example"],
    "notes": "<explanation of what changed and any unknowns>"
  },
  "revision_modes_applied": ["<one or more allowed revision modes>"],
  "remaining_flags": ["<safety flag still present>"]
}

ACCEPTANCE CRITERIA
- "improved_draft" is a single object, not a list.
- "revision_modes_applied" is non-empty and uses only allowed modes.
- "remaining_flags" is a subset of the input safety flags. New flags are not invented here.
- No blocked phrase appears in the improved caption or hashtags.
- The output is valid JSON.
"""


TEMPLATE = PromptTemplate(
    id="draft_improvement_v1",
    name="Draft Improvement",
    version="v1",
    description=(
        "Revises an existing draft using owner feedback and optional safety flags, "
        "without inventing new facts."
    ),
    expected_inputs=(
        PromptInputSpec(
            name="business_name",
            description="The business name.",
            required=True,
        ),
        PromptInputSpec(
            name="brand_voice",
            description="One-sentence voice description.",
            required=False,
        ),
        PromptInputSpec(
            name="supported_claims",
            description="Claims the business can actually support.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="blocked_phrases",
            description="Phrases the brand does not allow.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="platform",
            description="Target platform id.",
            required=True,
        ),
        PromptInputSpec(
            name="original_caption",
            description="The caption to improve.",
            required=True,
        ),
        PromptInputSpec(
            name="original_hashtags",
            description="The original hashtags.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="owner_feedback",
            description="The owner's revision request in plain language.",
            required=True,
        ),
        PromptInputSpec(
            name="safety_flags",
            description="Safety flags the revision should address.",
            required=False,
            type_hint="list",
        ),
    ),
    output_contract=(
        "JSON object: {improved_draft: {platform, caption, hashtags, notes}, "
        "revision_modes_applied: list[str], remaining_flags: list[str]}."
    ),
    template=_TEMPLATE_BODY,
    safety_rules=(
        "Do not invent new facts or claims.",
        "Do not use any blocked phrase.",
        "Do not silently drop safety flags; list any remaining ones in remaining_flags.",
        "Do not add credentials not present in supported_claims.",
        "Drafts only; never imply the post was sent.",
    ),
    notes="Use after platform_post_generator_v1 when an owner requests a revision.",
    created_at="2026-05-26",
)
