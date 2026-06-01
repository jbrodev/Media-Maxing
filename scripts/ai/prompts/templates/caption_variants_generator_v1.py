"""Caption variants generator (v1)."""

from __future__ import annotations

from scripts.ai.prompts.registry import PromptInputSpec, PromptTemplate

_TEMPLATE_BODY = """\
ROLE
You are a careful copy editor for a local service business. You produce alternative captions for an existing draft so the owner can pick the one that fits their voice today.

GOAL
Given an existing caption, generate {{ variant_count }} alternative captions on the same topic, with different lengths or angles, while staying true to the brand profile.

CONTEXT
Business name: {{ business_name }}
Brand voice: {{ brand_voice }}
Supported claims (only claims you may make): {{ supported_claims }}
Blocked phrases (do not use these): {{ blocked_phrases }}
Platform: {{ platform }}
Original caption: {{ original_caption }}
Owner notes: {{ owner_notes }}

INPUTS
Number of variants requested: {{ variant_count }}
Allowed variant styles: short, warm, direct, playful, formal.

CONSTRAINTS
- Produce exactly the requested number of variants. Do not produce more.
- Each variant must cover the same core message as the original.
- Do not introduce new facts or claims.
- Do not include any phrase from "Blocked phrases".
- Respect the platform's tone and length expectations.

SAFETY RULES
- Do not invent testimonials, customer names, prices, dates, or availability.
- Do not promise guaranteed results.
- Do not imply the post was sent. Drafts only.
- Do not add credentials not present in supported claims.

OUTPUT FORMAT
Return a single JSON object with this shape:
{
  "variants": [
    {
      "style": "<one of the allowed styles>",
      "text": "<caption variant>",
      "notes": "<optional caveat or unknown>"
    }
  ]
}

ACCEPTANCE CRITERIA
- "variants" length equals the requested variant count.
- Each variant uses a distinct style.
- No variant uses a blocked phrase or invents new claims.
- The output is valid JSON.
"""


TEMPLATE = PromptTemplate(
    id="caption_variants_generator_v1",
    name="Caption Variants Generator",
    version="v1",
    description=(
        "Rewrites an existing caption into a fixed number of variants with different "
        "styles, while preserving facts and respecting brand rules."
    ),
    expected_inputs=(
        PromptInputSpec(
            name="business_name",
            description="The business name for context.",
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
            example="instagram",
        ),
        PromptInputSpec(
            name="original_caption",
            description="The caption to rewrite.",
            required=True,
        ),
        PromptInputSpec(
            name="owner_notes",
            description="Free-text owner notes for this rewrite.",
            required=False,
        ),
        PromptInputSpec(
            name="variant_count",
            description="How many variants to produce.",
            required=True,
            type_hint="integer",
            example="3",
        ),
    ),
    output_contract=(
        "JSON object: {variants: [{style, text, notes}]} where len(variants) equals variant_count."
    ),
    template=_TEMPLATE_BODY,
    safety_rules=(
        "Do not introduce new facts or claims beyond the original.",
        "Do not use any blocked phrase.",
        "Do not invent credentials, prices, dates, or availability.",
        "Respect the target platform's tone and length expectations.",
    ),
    notes="Pair with platform_post_generator_v1 outputs to expand the owner's choices.",
    created_at="2026-05-26",
)
