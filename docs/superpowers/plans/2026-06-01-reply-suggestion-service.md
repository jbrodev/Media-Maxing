# AI Reply Suggestion Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, local-only AI reply suggestion service that stores reviewable suggestions and never sends replies externally.

**Architecture:** Add an additive SQLite migration and validated reply schemas, refine the registered prompt asset, extend the existing generic mock provider's structured-output branch, and add a dedicated orchestration service. The service renders the prompt, resolves the provider, runs local safety review, and persists the suggestion, engagement status update, and audit row in one transaction.

**Tech Stack:** Python standard library, raw `sqlite3`, dataclasses, existing prompt registry, existing AI provider abstraction, SQLite migrations, `unittest`.

---

## File Structure

- Create `scripts/db/migrations/009_batch7_reply_suggestions.sql`: additive reply suggestion columns.
- Modify `scripts/db/engagement_models.py`: reply actions, safety severity, and critical-flag constants.
- Modify `scripts/ai/schemas.py`: validated reply output and safety review dataclasses.
- Modify `scripts/ai/prompts/templates/comment_reply_suggestion_v1.py`: complete reply-specific context and safety sections.
- Modify `scripts/ai/providers/mock.py`: deterministic `reply_suggestion` structured payloads.
- Create `scripts/services/reply_suggestions.py`: local generation, safety review, persistence, history listing, and CLI.
- Create `tests/test_reply_suggestion_service.py`: requested scenarios and transaction behavior.
- Modify `tests/test_batch7_engagement_models.py`: migration-column coverage.
- Modify `tests/test_ai_mock_provider.py`: provider reply-payload coverage.
- Modify `tests/test_prompt_registry.py`: reply prompt section coverage.
- Modify `packages/types/index.ts`: shared reply action and safety-review types.
- Create `docs/reply-suggestions.md`: plain-language operator documentation.
- Modify `docs/database-schema.md`: persisted reply suggestion fields.
- Modify `README.md`: mark the local reply suggestion service as available.

### Task 1: Extend The Local Reply Suggestion Schema

**Files:**
- Create: `scripts/db/migrations/009_batch7_reply_suggestions.sql`
- Modify: `scripts/db/engagement_models.py`
- Modify: `tests/test_batch7_engagement_models.py`

- [ ] **Step 1: Write failing model tests**

Add assertions that `reply_suggestions` contains:

```python
{
    "recommended_action",
    "needs_human_review",
    "blocking_flags_json",
    "safety_review_json",
}.issubset(self._columns(connection, "reply_suggestions"))
```

Add constant assertions:

```python
self.assertIn("mark_spam", REPLY_RECOMMENDED_ACTIONS)
self.assertIn("critical", REPLY_SAFETY_SEVERITIES)
self.assertIn("unsupported_guarantee", CRITICAL_REPLY_SAFETY_FLAGS)
```

- [ ] **Step 2: Run the model test and confirm failure**

Run:

```powershell
python -m unittest tests.test_batch7_engagement_models
```

Expected: failure because the new columns and constants do not exist.

- [ ] **Step 3: Add the migration and constants**

Create the migration:

```sql
ALTER TABLE reply_suggestions
  ADD COLUMN recommended_action TEXT NOT NULL DEFAULT 'reply'
    CHECK (recommended_action IN (
      'reply', 'ask_for_more_info', 'invite_to_call', 'invite_to_message',
      'escalate', 'ignore', 'mark_spam'
    ));

ALTER TABLE reply_suggestions
  ADD COLUMN needs_human_review INTEGER NOT NULL DEFAULT 1
    CHECK (needs_human_review IN (0, 1));

ALTER TABLE reply_suggestions
  ADD COLUMN blocking_flags_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE reply_suggestions
  ADD COLUMN safety_review_json TEXT NOT NULL DEFAULT '{}';
```

Add constants:

```python
REPLY_RECOMMENDED_ACTIONS = (
    "reply", "ask_for_more_info", "invite_to_call", "invite_to_message",
    "escalate", "ignore", "mark_spam",
)

REPLY_SAFETY_SEVERITIES = ("info", "warning", "critical")

CRITICAL_REPLY_SAFETY_FLAGS = (
    "invented_price", "invented_availability", "unsupported_guarantee",
    "aggressive_language", "privacy_risk", "complaint_mishandled",
    "approval_bypass_attempt",
)
```

- [ ] **Step 4: Run the model test and confirm pass**

Run:

```powershell
python -m unittest tests.test_batch7_engagement_models
```

Expected: pass.

### Task 2: Add Validated Reply Output Schemas

**Files:**
- Modify: `scripts/ai/schemas.py`
- Create: `tests/test_reply_suggestion_service.py`

- [ ] **Step 1: Write failing schema tests**

Add tests for:

```python
ReplySuggestionOutput(
    suggested_reply="Thanks for the kind words.",
    tone="friendly",
    confidence="high",
    safety_flags=[],
    blocking_flags=[],
    recommended_action="reply",
    needs_human_review=True,
    reason_summary="Friendly thank-you draft for owner review.",
)
```

Assert invalid actions, invalid severities, and blocking flags not present in `safety_flags` raise `SchemaValidationError`.

- [ ] **Step 2: Run schema tests and confirm failure**

Run:

```powershell
python -m unittest tests.test_reply_suggestion_service
```

Expected: import failure because reply schemas do not exist.

- [ ] **Step 3: Add reply dataclasses**

Implement:

```python
@dataclass
class ReplySafetyFlag:
    code: str
    severity: str
    message: str

@dataclass
class ReplySuggestionOutput:
    suggested_reply: str
    tone: str
    confidence: str
    safety_flags: list[ReplySafetyFlag]
    blocking_flags: list[str]
    recommended_action: str
    needs_human_review: bool
    reason_summary: str
```

Validate confidence, action vocabulary, safety severity, boolean review state, and the blocking-subset invariant. Allow an empty `suggested_reply` only for `ignore`, `mark_spam`, or `escalate`.

- [ ] **Step 4: Run schema tests and confirm pass**

Run:

```powershell
python -m unittest tests.test_reply_suggestion_service
```

Expected: schema tests pass while service tests remain pending.

### Task 3: Refine The Prompt And Deterministic Mock Provider

**Files:**
- Modify: `scripts/ai/prompts/templates/comment_reply_suggestion_v1.py`
- Modify: `scripts/ai/providers/mock.py`
- Modify: `tests/test_prompt_registry.py`
- Modify: `tests/test_ai_mock_provider.py`

- [ ] **Step 1: Add failing prompt and provider tests**

Assert the prompt body contains:

```python
for section in (
    "BRAND CONTEXT", "ENGAGEMENT CONTEXT", "RELATED POST CONTEXT", "TONE",
):
    self.assertIn(section, prompt.template)
```

Assert the mock provider returns a deterministic `reply_suggestion` payload with:

```python
{
    "suggestedReply",
    "tone",
    "confidence",
    "safetyFlags",
    "recommendedAction",
    "needsHumanReview",
    "reasonSummary",
}
```

- [ ] **Step 2: Run tests and confirm failure**

Run:

```powershell
python -m unittest tests.test_prompt_registry tests.test_ai_mock_provider
```

Expected: failure because the specialized sections and mock payload do not exist.

- [ ] **Step 3: Refine the prompt**

Keep registry-compatible standard headers and add reply-specific subsections. Add prompt variables for:

```python
"engagement_sentiment",
"engagement_intent",
"engagement_priority",
"related_post_context",
"selected_tone",
```

Update the output contract to the camel-case service payload.

- [ ] **Step 4: Add deterministic mock reply generation**

Add a `reply_suggestion` branch to `_mock_structured_payload()` using request metadata. Produce stable cases:

```python
if intent == "spam":
    return {
        "suggestedReply": "",
        "tone": tone,
        "confidence": "high",
        "safetyFlags": [],
        "recommendedAction": "mark_spam",
        "needsHumanReview": True,
        "reasonSummary": "Spam should not receive an outward reply.",
    }
```

Add equivalent safe responses for praise, pricing, booking, complaints, urgent leads, and general questions.

- [ ] **Step 5: Run tests and confirm pass**

Run:

```powershell
python -m unittest tests.test_prompt_registry tests.test_ai_mock_provider
```

Expected: pass.

### Task 4: Implement Local Safety Review And Persistence Service

**Files:**
- Create: `scripts/services/reply_suggestions.py`
- Modify: `tests/test_reply_suggestion_service.py`

- [ ] **Step 1: Add failing service tests**

Cover:

```python
suggestion = service.generate(engagement_item_id="mock-engagement-pricing-question")
self.assertEqual(suggestion.recommendedAction, "invite_to_message")
self.assertNotRegex(suggestion.suggestedReply, r"\$\d+")
self.assertTrue(suggestion.needsHumanReview)
```

Add tests for praise, booking, complaint, spam, urgent lead, unsupported guarantee, persistence, engagement status, audit record, regeneration history, malformed output rollback, default mock provider, and absence of auto-approval.

- [ ] **Step 2: Run service tests and confirm failure**

Run:

```powershell
python -m unittest tests.test_reply_suggestion_service
```

Expected: failure because `ReplySuggestionService` does not exist.

- [ ] **Step 3: Implement safety review**

Implement a deterministic reviewer:

```python
def run_reply_safety_review(
    *,
    engagement_content: str,
    intent: str,
    suggested_reply: str,
) -> ReplySafetyReview:
    ...
```

Review inbound request and proposed reply for invented price, invented availability, unsupported guarantee, aggressive language, privacy risk, complaint mishandling, approval bypass, spam, and abusive-content indicators. Return detailed flags and critical blocking codes.

- [ ] **Step 4: Implement `ReplySuggestionService`**

Implement:

```python
class ReplySuggestionService:
    def generate(
        self,
        *,
        engagement_item_id: str,
        tone: str | None = None,
        provider_name: str = "mock",
    ) -> ReplySuggestion:
        ...

    def list_for_engagement(self, engagement_item_id: str) -> list[ReplySuggestion]:
        ...
```

Use the prompt registry, `get_provider()`, `AIStructuredGenerationRequest`, Brand Brain row mapping, related generated-post context, local safety review, and a single SQLite transaction.

- [ ] **Step 5: Run service tests and confirm pass**

Run:

```powershell
python -m unittest tests.test_reply_suggestion_service
```

Expected: pass.

### Task 5: Add CLI Verification And Documentation

**Files:**
- Modify: `scripts/services/reply_suggestions.py`
- Modify: `packages/types/index.ts`
- Create: `docs/reply-suggestions.md`
- Modify: `docs/database-schema.md`
- Modify: `README.md`
- Modify: `tests/test_reply_suggestion_service.py`

- [ ] **Step 1: Add failing CLI test**

Run the module with:

```powershell
python -m scripts.services.reply_suggestions --database <db> --engagement-item-id mock-engagement-praise-comment
```

Assert stdout includes:

```text
reply_suggestion_created=
recommended_action=reply
provider=mock
real_reply_send=false
```

- [ ] **Step 2: Implement safe CLI output**

Print IDs, action, provider, and safety counts only. Do not print engagement content, suggested reply text, private data, or provider payloads.

- [ ] **Step 3: Update shared types and docs**

Add TypeScript types:

```typescript
export type ReplyRecommendedAction =
  | "reply"
  | "ask_for_more_info"
  | "invite_to_call"
  | "invite_to_message"
  | "escalate"
  | "ignore"
  | "mark_spam";

export interface ReplySafetyFlag {
  code: string;
  severity: "info" | "warning" | "critical";
  message: string;
}
```

Extend `ReplySuggestion` with `recommendedAction`, `needsHumanReview`, `blockingFlags`, and `safetyReview`.

Document local-only behavior, prompt provenance, history preservation, critical flags, CLI verification, and the fact that no reply is sent externally.

- [ ] **Step 4: Run focused checks**

Run:

```powershell
python -m unittest tests.test_batch7_engagement_models tests.test_prompt_registry tests.test_ai_mock_provider tests.test_reply_suggestion_service
python -m compileall -q scripts tests
```

Expected: pass.

### Task 6: Run Full Local Verification

**Files:**
- Verify only.

- [ ] **Step 1: Initialize and seed a disposable database**

Run:

```powershell
python -m scripts.db.init_db --database data/reply-suggestions-check.sqlite
python -m scripts.db.seed_demo --database data/reply-suggestions-check.sqlite
python -m scripts.services.engagement --database data/reply-suggestions-check.sqlite --brand-profile-id demo-brand-brightside --ingest-mock
python -m scripts.services.reply_suggestions --database data/reply-suggestions-check.sqlite --engagement-item-id mock-engagement-pricing-question
```

Expected: safe local records are created and `real_reply_send=false` is printed.

- [ ] **Step 2: Run full tests and compile checks**

Run:

```powershell
python -m unittest discover tests
python -m compileall -q scripts tests
node --check apps\web\settings.js
node --check apps\web\generate.js
node --check apps\web\analytics.js
node --check apps\web\engagement.js
```

Expected: pass.

- [ ] **Step 3: Scan for accidental outbound behavior**

Run:

```powershell
rg -n "requests\\.|urllib\\.request|httpx\\.|aiohttp\\.|fetch\\(|send_reply|reply_send|auto.?reply" scripts tests docs README.md
```

Expected: no new external reply-sending path; documentation may mention that sending is disabled.

- [ ] **Step 4: Remove disposable database**

Resolve the absolute path under the repo `data` directory, verify that boundary, then remove only `data/reply-suggestions-check.sqlite`.

## Commit Note

This workspace does not contain a `.git` directory. Skip commit steps and report that version-control commits were unavailable.
