"""Safety review prompt for an existing draft (v1)."""

from __future__ import annotations

from scripts.ai.prompts.registry import PromptInputSpec, PromptTemplate

_TEMPLATE_BODY = """\
ROLE
You are a careful safety reviewer for a local service business. You read a draft and flag issues an owner should fix before the draft is approved. You do not rewrite the draft.

GOAL
Review the draft against the brand profile and the platform requirements and produce a structured safety review.

CONTEXT
Business name: {{ business_name }}
Brand voice: {{ brand_voice }}
Supported claims: {{ supported_claims }}
Blocked phrases: {{ blocked_phrases }}
Platform: {{ platform }}
Draft caption: {{ draft_caption }}
Draft hashtags: {{ draft_hashtags }}
Draft media notes: {{ draft_media_notes }}

INPUTS
Known safety flag identifiers (use these names where applicable):
- invented_testimonial
- unsupported_guarantee
- unsupported_credential
- private_customer_info_risk
- missing_required_brand_claim_support
- approval_bypass_attempt
- pricing_invented
- availability_invented
- aggressive_or_pressuring_language

You may add new descriptive flag names if a case is not covered, using lower_snake_case.

CONSTRAINTS
- Do not rewrite the draft.
- Do not invent issues that are not in the draft.
- Distinguish "flags" (something the owner should consider) from "blocking_flags" (must be resolved before approval).
- "blocking_flags" must be a subset of "flags".
- A blocked phrase appearing in the draft is always a blocking flag.
- An unsupported credential or guarantee is always a blocking flag.

SAFETY RULES
- Do not approve the draft. Approval is an owner action.
- Do not redact or hide flags.
- Flag anything that could mislead a local customer.
- Flag private customer information risks.

OUTPUT FORMAT
Return a single JSON object with this shape:
{
  "flags": ["<flag-name>"],
  "blocking_flags": ["<subset of flags>"],
  "reviewer": "ai",
  "notes": "<plain-language summary, 1-3 sentences>",
  "suggested_fixes": ["<short owner-facing suggestion>"]
}

ACCEPTANCE CRITERIA
- Every entry in "blocking_flags" also appears in "flags".
- Every blocked phrase present in the draft appears as a blocking flag.
- "reviewer" is the string "ai".
- "notes" is plain language, not bullet points.
- The output is valid JSON.
"""


TEMPLATE = PromptTemplate(
    id="safety_review_v1",
    name="Safety Review",
    version="v1",
    description=(
        "Reviews an existing draft against the brand profile and produces a "
        "structured safety review with flags, blocking flags, and fix suggestions."
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
            name="draft_caption",
            description="The draft caption text to review.",
            required=True,
        ),
        PromptInputSpec(
            name="draft_hashtags",
            description="The draft hashtags.",
            required=False,
            type_hint="list",
        ),
        PromptInputSpec(
            name="draft_media_notes",
            description="Notes describing the attached media.",
            required=False,
        ),
    ),
    output_contract=(
        "JSON object: {flags: list[str], blocking_flags: list[str] (subset of flags), "
        "reviewer: 'ai', notes: str, suggested_fixes: list[str]}."
    ),
    template=_TEMPLATE_BODY,
    safety_rules=(
        "Do not approve the draft. Approval is an owner action.",
        "Do not redact or hide flags.",
        "blocking_flags must be a subset of flags.",
        "A blocked phrase present in the draft is always a blocking flag.",
        "Unsupported credentials or guarantees are always blocking flags.",
        "Flag private customer information risks.",
    ),
    notes="Pair with the local safety check module added in a later step.",
    created_at="2026-05-26",
)
