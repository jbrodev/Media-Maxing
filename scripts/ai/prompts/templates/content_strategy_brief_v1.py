"""Content strategy brief generator (v1)."""

from __future__ import annotations

from scripts.ai.prompts.registry import PromptInputSpec, PromptTemplate

_TEMPLATE_BODY = """\
ROLE
You are a thoughtful content strategist for a local service business. You produce short, honest planning briefs that an owner-operator can act on in a week.

GOAL
Produce a content strategy brief that recommends 3-5 specific post ideas, each tied to a content goal, a content angle, suitable media, and a one-line rationale. The brief is planning input only. No content is generated or published here.

CONTEXT
Business name: {{ business_name }}
Brand voice: {{ brand_voice }}
Services: {{ services }}
Supported claims (only claims you may rely on): {{ supported_claims }}
Target audience: {{ target_audience }}
Service locations: {{ locations }}
Recent performance notes: {{ performance_notes }}
Available media inventory: {{ available_media }}
Owner priorities: {{ owner_priorities }}
Planning window: {{ planning_window }}

INPUTS
Supported content goals: get_leads, show_transformation, educate_customer, promote_offer, build_trust, announce_availability, repurpose_old_content, behind_the_scenes, seasonal_reminder.
Supported content angles: before_after, educational, behind_the_scenes, testimonial, promotion, faq, trust_builder, transformation, seasonal, other.

CONSTRAINTS
- Recommend 3-5 ideas, no more.
- Pull every claim from "Supported claims". If a desirable angle lacks support, skip it or mark it "[needs supporting claim]".
- Never recommend fake testimonials, fake social proof, or invented credentials.
- Do not include promotion ideas unless an offer is implied by owner priorities.
- Stay within the planning window.

SAFETY RULES
- Do not invent customer stories, prices, availability, or guarantees.
- Do not propose ideas that require permissions or assets the business does not have.
- Surface any idea that would require owner confirmation before drafting.

OUTPUT FORMAT
Return a single JSON object with this shape:
{
  "summary": "<2-3 sentence planning rationale>",
  "ideas": [
    {
      "title": "<short idea title>",
      "content_goal": "<one of the supported goals>",
      "content_angle": "<one of the supported angles>",
      "media_asset_ids": ["<media id from inventory>"],
      "rationale": "<one sentence>",
      "needs_owner_confirmation": false
    }
  ],
  "open_questions": ["<question for the owner>"]
}

ACCEPTANCE CRITERIA
- "ideas" contains 3 to 5 items.
- Each idea has a goal and angle from the supported lists.
- Media references exist in the supplied inventory or are recorded in "open_questions" instead.
- The output is valid JSON.
"""


TEMPLATE = PromptTemplate(
    id="content_strategy_brief_v1",
    name="Content Strategy Brief",
    version="v1",
    description=(
        "Recommends 3-5 honest post ideas for a planning window using the brand "
        "profile, available media, and recent performance notes."
    ),
    expected_inputs=(
        PromptInputSpec(
            name="business_name",
            description="The local service business name from the Brand Brain.",
            required=True,
        ),
        PromptInputSpec(
            name="brand_voice",
            description="One-sentence voice description.",
            required=False,
        ),
        PromptInputSpec(
            name="services",
            description="Services the business offers.",
            required=True,
            type_hint="list",
        ),
        PromptInputSpec(
            name="supported_claims",
            description="Claims the business can actually support.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="target_audience",
            description="Who the brief is planning for.",
            required=False,
        ),
        PromptInputSpec(
            name="locations",
            description="Service area or locations.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="performance_notes",
            description="Summary of recent performance signals or AI memory.",
            required=False,
        ),
        PromptInputSpec(
            name="available_media",
            description="Brief inventory of media assets available for the brief.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="owner_priorities",
            description="Free-text owner priorities for this window.",
            required=False,
        ),
        PromptInputSpec(
            name="planning_window",
            description="The window the brief should cover (e.g. 'this week').",
            required=True,
            example="next 7 days",
        ),
    ),
    output_contract=(
        "JSON object: {summary, ideas: [{title, content_goal, content_angle, "
        "media_asset_ids, rationale, needs_owner_confirmation}], open_questions}."
    ),
    template=_TEMPLATE_BODY,
    safety_rules=(
        "Do not invent customer stories, prices, availability, or guarantees.",
        "Recommend only claims that appear in supported_claims.",
        "Surface any idea that needs owner confirmation before drafting.",
        "Stay inside the supported content goal and angle lists.",
    ),
    notes="Planning-only. Drafts are generated by platform_post_generator_v1 later.",
    created_at="2026-05-26",
)
