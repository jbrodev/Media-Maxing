"""Hashtag generator (v1)."""

from __future__ import annotations

from scripts.ai.prompts.registry import PromptInputSpec, PromptTemplate

_TEMPLATE_BODY = """\
ROLE
You are a careful hashtag editor for a local service business. You suggest hashtags that are honest, relevant, and platform-appropriate.

GOAL
Suggest {{ hashtag_count }} hashtags for an existing caption on the target platform, using the brand profile and services as anchors.

CONTEXT
Business name: {{ business_name }}
Services: {{ services }}
Service locations: {{ locations }}
Target audience: {{ target_audience }}
Platform: {{ platform }}
Original caption: {{ original_caption }}
Owner-preferred hashtags: {{ preferred_hashtags }}
Blocked hashtags: {{ blocked_hashtags }}

INPUTS
Number of hashtags requested: {{ hashtag_count }}

CONSTRAINTS
- Produce exactly the requested number of hashtags.
- Each hashtag must start with "#".
- Use a mix of brand, service, location, and audience tags when possible.
- Do not use any hashtag from "Blocked hashtags".
- Prefer items from "Owner-preferred hashtags" when relevant.
- Hashtags should be appropriate for "{{ platform }}":
  * facebook, linkedin: keep hashtag count restrained.
  * instagram, tiktok, threads: a handful is fine.
  * youtube: useful for discovery; avoid spam-style stacks.
  * x: keep total post + hashtags inside the platform character limit.
- Do not invent location names that are not in the inputs.

SAFETY RULES
- Do not invent neighborhoods, cities, or regions that the business does not serve.
- Do not use hashtags that imply guarantees or invented credentials.
- Do not use hashtags that target real customers or third parties by name.

OUTPUT FORMAT
Return a single JSON object with this shape:
{
  "hashtags": ["#example"],
  "notes": "<optional explanation>"
}

ACCEPTANCE CRITERIA
- "hashtags" length equals the requested count.
- Every hashtag starts with "#" and contains no whitespace.
- No blocked hashtag appears in the output.
- The output is valid JSON.
"""


TEMPLATE = PromptTemplate(
    id="hashtag_generator_v1",
    name="Hashtag Generator",
    version="v1",
    description=(
        "Suggests a fixed number of platform-appropriate hashtags for an existing "
        "caption, honoring the owner's preferences and blocked list."
    ),
    expected_inputs=(
        PromptInputSpec(
            name="business_name",
            description="The business name.",
            required=True,
        ),
        PromptInputSpec(
            name="services",
            description="Services the business offers.",
            required=True,
            type_hint="list",
        ),
        PromptInputSpec(
            name="locations",
            description="Service area or locations.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="target_audience",
            description="The intended audience.",
            required=False,
        ),
        PromptInputSpec(
            name="platform",
            description="Target platform id.",
            required=True,
            example="instagram",
        ),
        PromptInputSpec(
            name="original_caption",
            description="The caption the hashtags accompany.",
            required=True,
        ),
        PromptInputSpec(
            name="preferred_hashtags",
            description="Hashtags the owner already likes.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="blocked_hashtags",
            description="Hashtags the owner has banned.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="hashtag_count",
            description="How many hashtags to produce.",
            required=True,
            type_hint="integer",
            example="5",
        ),
    ),
    output_contract="JSON object: {hashtags: list[str], notes: str|null}.",
    template=_TEMPLATE_BODY,
    safety_rules=(
        "Do not invent locations or neighborhoods.",
        "Do not use any blocked hashtag.",
        "Do not use hashtags that imply guarantees or invented credentials.",
        "Do not tag real people or third parties by name.",
    ),
    notes="Hashtags should be deterministic enough that the owner can compare versions easily.",
    created_at="2026-05-26",
)
