"""Platform-specific social post draft generator (v1)."""

from __future__ import annotations

from scripts.ai.prompts.registry import PromptInputSpec, PromptTemplate

_TEMPLATE_BODY = """\
ROLE
You are an experienced social media draft writer for a local service business. You write practical, supportable, owner-friendly drafts. You never publish anything. The local business owner reviews and approves every draft before it leaves the app.

GOAL
Generate one social media draft per requested platform for a local service business using the brand profile and media metadata as the source of truth. Output is a draft only.

CONTEXT
Business name: {{ business_name }}
Brand voice: {{ brand_voice }}
Services: {{ services }}
Supported claims (only claims you may make): {{ supported_claims }}
Blocked phrases (do not use these): {{ blocked_phrases }}
Target audience: {{ target_audience }}
Service locations: {{ locations }}
Content goal: {{ content_goal }}
Content angle: {{ content_angle }}
Media metadata: {{ media_notes }}
User instructions: {{ user_instructions }}

INPUTS
Requested platforms: {{ requested_platforms }}
Supported platform identifiers: facebook, instagram, threads, tiktok, youtube, linkedin, x.
Only generate drafts for the platforms listed in "Requested platforms". If a requested platform is not in the supported list, skip it and note the skip in your output.

CONSTRAINTS
- Do not invent facts.
- Do not invent testimonials, customer names, prices, dates, or availability.
- Do not promise guaranteed results.
- Do not claim licenses, certifications, insurance, awards, or guarantees unless they appear in "Supported claims".
- Do not publish anything. This is a draft only.
- Keep posts appropriate for local service businesses.
- Use the brand profile and media metadata as the source of truth.
- If information is missing, write around it safely or mark the gap with "[unknown]".
- Include a clear call-to-action only when it is appropriate for the content goal.
- Respect platform-specific tone and length expectations:
  * facebook: friendly, approachable, 80-200 words is fine.
  * instagram: visual-led caption, 60-150 words, hashtags welcome.
  * threads: conversational, 40-100 words, light on hashtags.
  * tiktok: short, hook-led, 30-100 words, casual.
  * youtube: description-style, 100-200 words, may include sections.
  * linkedin: professional, 100-200 words, restrained hashtag use.
  * x: concise; the whole post (including any hashtags) must fit roughly 280 characters.

SAFETY RULES
- Do not invent testimonials or fake social proof.
- Do not invent pricing or scheduling availability.
- Do not invent certifications, licensing, insurance, or guarantees.
- Do not imply a post was sent when it is only a draft.
- Do not make aggressive or pressuring claims.
- Do not scrape or reference content from third-party social platforms.
- Surface a safety flag for anything that would require owner confirmation.

OUTPUT FORMAT
Return a single JSON object with this shape:
{
  "drafts": [
    {
      "platform": "<one of the supported platform ids>",
      "caption": "<draft caption text>",
      "hashtags": ["#example"],
      "media_asset_ids": ["<media id from inputs>"],
      "notes": "<caveats, unknowns, or skip reasons>"
    }
  ],
  "safety_review": {
    "flags": ["<flag-name>"],
    "blocking_flags": ["<subset of flags>"],
    "reviewer": "ai",
    "notes": "<short summary>"
  }
}

ACCEPTANCE CRITERIA
- One draft entry per requested supported platform; skipped platforms are recorded in "notes".
- Each caption respects the platform's tone and length expectations above.
- Hashtags are appropriate for the platform.
- No invented claims, testimonials, prices, dates, or credentials.
- No private customer data is added unless explicitly provided in inputs.
- "safety_review.blocking_flags" is a subset of "safety_review.flags".
- The whole output is valid JSON.
"""


TEMPLATE = PromptTemplate(
    id="platform_post_generator_v1",
    name="Platform Post Generator",
    version="v1",
    description=(
        "Generates one platform-specific draft per requested platform using the brand "
        "profile and media metadata as the source of truth. Drafts only; never publishes."
    ),
    expected_inputs=(
        PromptInputSpec(
            name="business_name",
            description="The local service business name from the Brand Brain.",
            required=True,
            example="Brightside Exterior Care Demo",
        ),
        PromptInputSpec(
            name="brand_voice",
            description="One-sentence voice description.",
            required=False,
            example="Helpful, neighborly, practical.",
        ),
        PromptInputSpec(
            name="services",
            description="Services the business offers.",
            required=True,
            type_hint="list",
            example="[pressure washing, gutter cleaning]",
        ),
        PromptInputSpec(
            name="supported_claims",
            description="Claims the business can actually support. Only these may appear in drafts.",
            required=False,
            type_hint="list",
            example="[uses careful surface checks before cleaning]",
        ),
        PromptInputSpec(
            name="blocked_phrases",
            description="Phrases the brand does not allow.",
            required=False,
            type_hint="list",
            example="[guaranteed results, best in town]",
        ),
        PromptInputSpec(
            name="target_audience",
            description="Who the post is intended for.",
            required=False,
            example="Local homeowners and small property managers.",
        ),
        PromptInputSpec(
            name="locations",
            description="Service area or locations.",
            required=False,
            type_hint="list",
            example="[Demo City, Nearby County]",
        ),
        PromptInputSpec(
            name="content_goal",
            description="The marketing goal for this post (e.g. get_leads, build_trust).",
            required=True,
            example="show_transformation",
        ),
        PromptInputSpec(
            name="content_angle",
            description="The content angle (e.g. before_after, educational).",
            required=True,
            example="before_after",
        ),
        PromptInputSpec(
            name="media_notes",
            description="Summary of the selected media assets.",
            required=False,
            type_hint="list",
            example="[id: media-driveway-before, stage: before, service: pressure washing]",
        ),
        PromptInputSpec(
            name="user_instructions",
            description="Free-text owner instructions for this draft.",
            required=False,
        ),
        PromptInputSpec(
            name="requested_platforms",
            description="The platforms the user wants drafts for.",
            required=True,
            type_hint="list",
            example="[instagram, facebook]",
        ),
    ),
    output_contract=(
        "JSON object: {drafts: [{platform, caption, hashtags, media_asset_ids, notes}], "
        "safety_review: {flags, blocking_flags, reviewer, notes}}. "
        "One entry per requested supported platform."
    ),
    template=_TEMPLATE_BODY,
    safety_rules=(
        "Do not invent testimonials, customer names, prices, dates, or availability.",
        "Do not promise guaranteed results.",
        "Do not claim licenses, certifications, insurance, awards, or guarantees not in supported_claims.",
        "Do not publish. Drafts only.",
        "Use the brand profile and media metadata as the source of truth.",
        "Surface a safety flag for any item that requires owner confirmation.",
    ),
    notes=(
        "If a requested platform is not in the supported identifier list, record the skip in "
        "the draft notes rather than fabricating an entry."
    ),
    created_at="2026-05-26",
)
