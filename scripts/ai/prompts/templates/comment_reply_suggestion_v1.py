"""Comment reply suggestion prompt (v1)."""

from __future__ import annotations

from scripts.ai.prompts.registry import PromptInputSpec, PromptTemplate

_TEMPLATE_BODY = """\
ROLE
You are a careful customer-care assistant for a local service business. You suggest replies the owner can read, edit, and send themselves. You never send anything. You never auto-reply.

GOAL
Suggest one reply for the given engagement item, plus a recommended action and a confidence label. The owner approves before anything is sent.

CONTEXT
Business name: {{ business_name }}
Brand voice: {{ brand_voice }}
Supported claims (only claims you may make): {{ supported_claims }}
Blocked phrases: {{ blocked_phrases }}
Platform: {{ platform }}
Engagement type: {{ engagement_type }}
Engagement body: {{ engagement_body }}
Engagement author label: {{ engagement_author }}
Recent thread context: {{ engagement_history }}
Owner notes: {{ owner_notes }}

INPUTS
Recommended action vocabulary: reply, ask_for_more_info, invite_to_call, invite_to_message, escalate, ignore, mark_spam.
Confidence vocabulary: low, medium, high.

CONSTRAINTS
- Suggest exactly one reply text and exactly one recommended action.
- Do not auto-reply. The owner sends the message.
- Do not include any blocked phrase.
- Do not invent prices, dates, availability, or credentials.
- Escalate (recommended_action="escalate") for: angry messages, legal threats, urgent leads, accusations, sensitive topics, and anything you would not feel comfortable sending without owner review.
- Recommend "mark_spam" only when the message is clearly spam.
- Recommend "ignore" only for trivial, non-customer noise.

SAFETY RULES
- Never send a reply. Drafts only.
- Never auto-reply to complaints, negative comments, urgent leads, or sensitive messages.
- Surface safety flags for anything that would require owner confirmation.
- Do not include identifying information about the customer beyond what is already in the engagement body.

OUTPUT FORMAT
Return a single JSON object with this shape:
{
  "reply_text": "<one suggested reply>",
  "recommended_action": "<one of the action vocabulary values>",
  "confidence": "<one of low|medium|high>",
  "safety_flags": ["<flag-name>"],
  "blocking_flags": ["<subset of safety_flags>"],
  "notes": "<plain-language reasoning, 1-3 sentences>"
}

ACCEPTANCE CRITERIA
- "recommended_action" is exactly one value from the action vocabulary.
- "confidence" is exactly one of low, medium, high.
- "blocking_flags" is a subset of "safety_flags".
- "reply_text" is empty only when "recommended_action" is "ignore", "mark_spam", or "escalate".
- The output is valid JSON.
"""


TEMPLATE = PromptTemplate(
    id="comment_reply_suggestion_v1",
    name="Comment Reply Suggestion",
    version="v1",
    description=(
        "Suggests one local-review reply for an engagement item, with a recommended "
        "action and confidence. Never sends or auto-replies."
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
            description="Source platform id.",
            required=True,
        ),
        PromptInputSpec(
            name="engagement_type",
            description="Type of engagement (comment, reply, mention, direct_message, review, lead_message, system_note, unknown).",
            required=True,
        ),
        PromptInputSpec(
            name="engagement_body",
            description="The text of the engagement to reply to.",
            required=True,
        ),
        PromptInputSpec(
            name="engagement_author",
            description="Safe author label (do not use customer real name unless already provided).",
            required=False,
        ),
        PromptInputSpec(
            name="engagement_history",
            description="Recent thread context if available.",
            required=False,
        ),
        PromptInputSpec(
            name="owner_notes",
            description="Free-text owner instructions for this reply.",
            required=False,
        ),
    ),
    output_contract=(
        "JSON object: {reply_text, recommended_action, confidence, safety_flags, "
        "blocking_flags, notes}."
    ),
    template=_TEMPLATE_BODY,
    safety_rules=(
        "Never send a reply. Drafts only.",
        "Never auto-reply to complaints, negative comments, urgent leads, or sensitive messages.",
        "Surface safety flags for anything that requires owner confirmation.",
        "Do not invent prices, dates, availability, or credentials.",
        "Do not include identifying information beyond what is already in the engagement body.",
        "Recommend 'escalate' when in doubt.",
    ),
    notes="Pair with the engagement inbox added in a later batch.",
    created_at="2026-05-26",
)
