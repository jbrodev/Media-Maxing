# Approval Queue Service

The approval queue service is the reusable local safety gate for generated post drafts. Future Calendar, Publish Queue, manual export readiness, and real publishing work should call this service before treating a draft as ready.

The implementation lives in `scripts/services/approval_queue.py`.

## What The Service Does

- Lists drafts with `needs_review`.
- Lists approved drafts.
- Reads the current approval status for a draft.
- Approves, rejects, requests revision, and archives drafts.
- Writes approval log entries for status changes.
- Checks scheduling eligibility.
- Checks future publishing eligibility.

The service does not publish, schedule, connect social accounts, or delete drafts.

## Actor Types

Approval actions support these actor types:

- `user`
- `system`
- `ai`
- `test`

Approval logs store draft ID, action, previous status, new status, reason, actor type, optional actor name or ID, and timestamp.

## Critical Safety Flags

Critical flags block scheduling and future publishing:

- `invented_testimonial`
- `fake_testimonial`
- `unsupported_guarantee`
- `approval_bypass_attempt`
- `missing_approval`
- `emergency_pause_enabled`
- `emergency_pause_conflict`
- `missing_required_brand_claim_support`
- `unsupported_claim`
- `private_customer_info_risk`

Severity levels are:

- `info`
- `warning`
- `critical`

## Scheduling Eligibility

A draft is eligible for scheduling only when:

- Approval status is `approved`.
- Emergency pause is off.
- Platform is one of the supported platform IDs.
- Caption/content exists.
- No critical safety flags are present.
- The Brand Brain record still exists.
- Linked media records exist.
- Media-required platforms have media attached.

The current media-required platforms are:

- Instagram
- YouTube Shorts
- TikTok

The service only returns an eligibility decision. It does not create a scheduled post.

## Publishing Eligibility

Future publishing eligibility requires everything scheduling requires, plus:

- Platform-specific metadata is present when needed.
- No unresolved revision request, rejected status, or archived status exists.
- If a `social_accounts` table exists in a future batch, a connected account must exist for the target platform.

Real publishing remains disabled by policy. The service currently returns a warning named `real_publishing_disabled_by_policy` even when a draft passes the future publishing gate.

## Usage Example

```python
from scripts.services.approval_queue import Actor, ApprovalQueueService

queue = ApprovalQueueService("data/app.sqlite")
drafts = queue.list_drafts_needing_review()

approved = queue.approve(
    drafts[0].id,
    actor=Actor(actorType="user", actorName="Owner"),
)

scheduling = queue.check_scheduling_eligibility(approved.id)
if scheduling.eligible:
    print("Eligible for future local scheduling")
else:
    print(scheduling.errors)
```

## Safety Notes

- Do not bypass this service in future scheduling or publishing code.
- Do not treat approval logs as permission to publish.
- Do not hide critical safety flags.
- Do not auto-approve generated drafts.
- Do not publish or schedule from this service.
