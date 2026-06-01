Project Identity
This repository is for a local-first AI social media manager designed for small businesses, local service businesses, and owner-operators who want help creating, scheduling, tracking, and managing social media content without becoming social media experts.
The product should help a non-coder user:
Define a business identity in a Brand Brain.
Upload and organize photos/videos in a Media Library.
Generate platform-specific social media drafts with AI.
Review, edit, approve, reject, and revise drafts.
Schedule approved drafts on a local content calendar.
Prepare posts in a Publish Queue.
Export manual posting packages before real API publishing exists.
Track analytics manually or with mock/demo analytics.
Manage engagement locally with AI-assisted reply suggestions.
Learn from performance, approvals, rejections, and engagement.
Maintain safety through approval requirements, emergency pause, and kill switch controls.
Back up/export local data and diagnose app health.
This app is intentionally local-first. It should run locally, store user data locally by default, and avoid unnecessary cloud dependencies.
---
Product North Star
Build a safe, useful, local-first AI social media command center that turns business media and brand context into approved social media content, learns what performs over time, and prepares the foundation for future real platform integrations.
The app should feel like:
> "A local AI social media manager for service businesses that turns real job photos/videos into drafts, schedules content, tracks performance, helps manage engagement, and learns what gets leads."
Do not build a generic Buffer/Hootsuite clone. Focus on business memory, media-first content generation, human approval, local control, and safety.
---
Target User
Assume the primary user is not a developer.
The user may make minor edits such as:
adding API keys
adding login credentials
editing `.env`
running commands copied from docs
approving changes in Codex, Claude Code, or another builder
The user should not need to manually write application code.
Every feature should be understandable, guided, and documented in plain language.
---
Hard Safety Rules
These rules override feature requests unless a future explicit task safely changes them.
Publishing and Replies
Do not publish real posts to any social platform unless a future prompt explicitly enables one real platform with safety gates.
Do not send real comment replies or DMs.
Do not auto-reply to complaints, negative comments, urgent leads, or sensitive messages.
AI can draft content and reply suggestions, but the user must approve before anything is treated as ready.
Real publishing and real reply sending must remain disabled by default.
Approval
MVP default is approval required.
Generated posts default to `needs_review`.
Reply suggestions default to local review only.
Editing an approved draft should require reapproval or clearly record that it changed.
Scheduling should only allow approved, safe drafts.
Future real publishing should only allow approved, preflight-passed content.
Emergency Pause
Emergency pause must block:
scheduling new posts
moving scheduled posts to ready queue
mock publishing
future real publishing
future real reply sending
automation above approval queue
local job runner readiness changes, except safe blocked/paused states
AI auto-action placeholders
Emergency pause should not block:
viewing data
editing Brand Brain
editing drafts
importing media
creating backups
exporting diagnostic reports
reading analytics
adding manual notes
Content Integrity
AI must not:
invent testimonials
invent customer names
invent pricing
invent scheduling availability
invent certifications, licensing, insurance, awards, or guarantees
claim a post/reply was sent when it was only drafted
promise guaranteed results
make aggressive replies
hide safety flags
create fake social proof
scrape social platforms
Secrets and Tokens
Never expose, log, commit, print, or include in frontend responses:
access tokens
refresh tokens
authorization codes
client secrets
API keys
bearer tokens
encrypted token blobs unless explicitly needed in a server-only context
raw OAuth state values
raw provider responses containing credentials
Use safe DTOs for frontend-facing account data.
---
Development Philosophy
Use the 80-prompt build plan as the project sequence. Each prompt is meant to be small, testable, and reversible.
When a prompt says checkpoint, do not change code. Inspect and report.
When implementing:
Read this `AGENTS.md`.
Inspect the repo before changing files.
Reuse existing conventions.
Make the smallest safe change that completes the task.
Keep mock mode working.
Keep real external calls disabled by default.
Update docs when behavior changes.
Run available checks.
Report files changed, commands run, and any errors honestly.
Do not skip safety, validation, or documentation just to make a feature appear complete.
---
Preferred Build Order
The project is organized into 8 batches of 10 prompts each.
Batch 1: Foundation and App Shell
Goal: create repo structure, docs, environment templates, `.gitignore`, shared types, database schema plan, roadmap, safety policy, and initial app shell.
Core outputs:
root project structure
`README.md`
`.env.example`
`.gitignore`
shared product types
`docs/database-schema.md`
`docs/roadmap.md`
`docs/safety-and-automation-policy.md`
app navigation shell
Batch 2: Local Database, Settings, Brand Brain, Media Library
Goal: create local SQLite foundation, app settings, Brand Brain, media storage, and media metadata.
Core outputs:
SQLite database/models/migrations
seed script
settings service and UI
Brand Brain service and UI
local media storage service
Media Library UI
media tagging/job context metadata
Batch 3: AI Generation, Drafts, Approval Workflow
Goal: create AI provider abstraction, mock provider, prompt registry, structured outputs, generation service, Generate screen, draft persistence, approval queue, and prompt evaluations.
Core outputs:
AI provider interface
mock AI provider
versioned prompt registry
structured output schemas
content generation service
Generate screen
saved drafts
Drafts screen
approval queue service
prompt evaluation docs/fixtures
Batch 4: Calendar, Scheduling, Publish Queue, Local Jobs
Goal: schedule approved drafts locally, process queue readiness with local jobs, validate preflight, and export manual posting packages.
Core outputs:
scheduled posts models
publish queue models
scheduling service
Calendar screen
schedule-from-draft flow
local job runner
Publish Queue screen
platform preflight matrix
manual export package
Batch 5: Social Account Connections and OAuth Scaffolding
Goal: create social connector architecture, mock OAuth, connected accounts UI, token security foundation, Meta-first scaffolding, and account-aware preflight.
Core outputs:
connector interfaces
platform registry
social accounts/tokens/oauth state models
token security service
OAuth state service
mock OAuth routes
Connected Accounts UI
Meta connector scaffold
account readiness in Publish Queue
setup wizard
Batch 6: Real OAuth Readiness and Platform Scaffolds
Goal: harden real-integration readiness without enabling publishing. Add safe HTTP client, feature flags, guarded Meta token exchange, health checks, and scaffolds for YouTube, TikTok, LinkedIn, and X.
Core outputs:
server-only platform HTTP client
integration feature flags
guarded Meta OAuth exchange path
Meta discovery/health scaffold
YouTube connector scaffold
TikTok connector scaffold
LinkedIn connector scaffold
X connector scaffold
connector health checks
integration docs/tests
Batch 7: Analytics, Engagement Inbox, AI Learning Loop
Goal: track performance, manage engagement locally, suggest replies, approve replies locally, create learning memory, and generate weekly reports.
Core outputs:
analytics model refinements
manual/mock analytics service
Analytics Dashboard
engagement model refinements
mock engagement ingestion
Engagement Inbox
AI reply suggestion service
local reply approval workflow
AI learning loop
weekly report generator
Batch 8: Production Hardening and Launch Readiness
Goal: make the app usable by a non-coder through onboarding, safety center, backup/export, diagnostics, desktop prep, docs, final tests, and handoff.
Core outputs:
first-run onboarding
setup checklist
Safety Center
emergency pause hardening
kill switch controls
backup/restore/export
diagnostics
desktop packaging preparation
user-facing docs
launch checklist
release notes
final handoff docs
---
Recommended Architecture
Prefer this architecture unless the existing repo clearly uses something else:
```text
/apps
  /web
  /desktop
  /api
/packages
  /shared
  /ui
  /types
  /config
/docs
/scripts
/data
  /media
  /exports
  /logs
```
Preferred stack:
Frontend: Next.js or existing web framework
Desktop: Tauri preferred if not already chosen, Electron if already present
Backend/API: FastAPI, Node/Nest, or framework already present
Database: SQLite for MVP
ORM: Continue existing ORM. If none exists, choose Prisma/Drizzle for TypeScript or SQLAlchemy/SQLModel for Python.
Media: local file storage
AI: mock provider by default, real providers later
Jobs: lightweight local runner first
Charts: simple native UI or existing chart library
OAuth: server-side only
Tokens: secure local storage/keychain/encryption when available, placeholder-not-stored if not
Do not force a new framework if the repo already has a working direction.
---
Local Data Rules
Local data should live under a local app data directory.
Suggested structure:
```text
data/
  media/
    originals/
    processed/
    thumbnails/
  exports/
    manual-posts/
    backups/
    diagnostics/
  logs/
  db/
```
Do not commit:
real user media
local databases
exports
logs
`.env`
tokens
secrets
generated backups
Always keep `.env.example` committed.
---
Core Domain Models
The app should include or evolve these concepts:
`User`
`BrandProfile`
`AppSettings`
`SocialAccount`
`PlatformToken`
`OAuthState`
`ConnectorAuditLog`
`MediaAsset`
`ContentIdea`
`GeneratedPost`
`ScheduledPost`
`PublishQueueItem`
`PublishAttempt`
`PublishedPost`
`EngagementItem`
`EngagementThread`
`ReplySuggestion`
`ReplyApproval`
`AnalyticsSnapshot`
`PostPerformanceMetrics`
`AnalyticsImport`
`ContentInsight`
`AIMemory`
`WeeklyReport`
`ApprovalLog`
`SafetyAuditLog`
Use JSON fields where practical for SQLite simplicity, especially for arrays, metadata, evidence, capabilities, scopes, and raw mock data.
---
Platform Identifiers
Use consistent platform IDs:
`facebook`
`instagram`
`threads`
`youtube`
`tiktok`
`linkedin`
`x`
User-facing labels can be:
Facebook
Instagram
Threads
YouTube Shorts
TikTok
LinkedIn
X
Do not use inconsistent platform strings in models, UI, or preflight checks.
---
Automation Levels
Supported automation levels:
`manual_assist`
`approval_queue`
`semi_auto_scheduling`
`safe_auto_posting`
`autonomous_content_engine`
MVP default:
```text
automationLevel = approval_queue
requireApprovalBeforePublishing = true
requireApprovalBeforeReplying = true
emergencyPauseEnabled = false
```
Levels above `approval_queue` can exist in the UI as planned/locked, but must not enable real autonomous publishing or real replies unless a future explicit task implements them with safety gates.
---
AI Rules
Provider Design
Create a provider abstraction that supports:
`mock`
`openai`
`anthropic`
`local`
Mock provider must be default for development and tests.
Real provider adapters should:
require explicit configuration
fail safely if missing keys
never expose secrets
avoid network calls in tests by default
return structured outputs
include provider metadata
Prompt Registry
Prompts should be treated like versioned product assets.
Prompt templates should include:
id
name
version
description
expected inputs
output contract
safety rules
template text
evaluation notes
Prompt sections should generally include:
ROLE
GOAL
CONTEXT
INPUTS
CONSTRAINTS
SAFETY RULES
OUTPUT FORMAT
ACCEPTANCE CRITERIA
Required prompt families:
`content_strategy_brief_v1`
`platform_post_generator_v1`
`caption_variants_generator_v1`
`hashtag_generator_v1`
`safety_review_v1`
`draft_improvement_v1`
`comment_reply_suggestion_v1`
Structured Output
Do not accept random free-form AI output as production data.
Generated content should validate against structured schemas such as:
`ContentGenerationInput`
`ContentGenerationOptions`
`PlatformPostDraft`
`CaptionVariant`
`HashtagSet`
`ContentStrategyBrief`
`GeneratedContentBundle`
`GeneratedPostSafetyReview`
`GeneratedPostScore`
`DraftImprovementSuggestion`
Reply suggestions should also be structured and safety-reviewed.
---
Content Generation Behavior
Content generation should use:
Brand Brain
selected media metadata
selected platforms
content goal
content angle
target audience
campaign/offer context
user instructions
active AI memory, when available
safety rules
Supported content goals:
`get_leads`
`show_transformation`
`educate_customer`
`promote_offer`
`build_trust`
`announce_availability`
`repurpose_old_content`
`behind_the_scenes`
`seasonal_reminder`
Supported content angles:
`before_after`
`educational`
`behind_the_scenes`
`testimonial`
`promotion`
`faq`
`trust_builder`
`transformation`
`seasonal`
`other`
Generated drafts must:
be platform-specific
include safety flags
include prompt metadata
include generation provider
default to `needs_review`
not publish automatically
not schedule automatically unless the user explicitly schedules an approved draft
---
Approval Workflow
Draft statuses:
`draft`
`needs_review`
`approved`
`rejected`
`revision_requested`
`archived`
Approval service should support:
list drafts needing review
approve draft
reject draft
request revision
archive draft
create approval log
check scheduling eligibility
check future publishing eligibility
Critical safety flags should block scheduling and future publishing.
Examples of critical flags:
`invented_testimonial`
`unsupported_guarantee`
`approval_bypass_attempt`
`emergency_pause_enabled`
`missing_required_brand_claim_support`
`private_customer_info_risk`
---
Scheduling and Queue Rules
Scheduling is local-only in the MVP.
A draft can be scheduled only if:
approval status is `approved`
emergency pause is false
platform is valid
caption/content exists
no critical safety flags exist
brand profile exists
required media exists or media is not required
scheduled time is valid
Scheduling should create:
`scheduled_posts`
`publish_queue_items`
audit/approval log records
Scheduled posts should snapshot caption/media at scheduling time. Later edits to the original draft should not silently change scheduled content.
Publish Queue supports:
waiting
ready
blocked
processing
mock_published
manually_exported
failed
canceled
skipped
No real publishing should occur in the queue until a future explicit real-publishing task.
---
Preflight Rules
Create a centralized platform requirement matrix.
Preflight should check:
approval status
emergency pause
platform support
caption/text presence
platform text length placeholder
media requirement
local media existence
supported media type
critical safety flags
brand profile
queue status
title requirements where applicable
unresolved revision request
account readiness
Missing connected account should:
warn for manual export
block only future real publishing eligibility
Warnings do not block manual export. Errors block readiness.
Platform requirements can use practical placeholder limits, but mark TODOs for future API verification.
---
Social Connector Rules
Connectors must be safe by default.
Supported feature statuses:
`unavailable`
`planned`
`scaffolded`
`mock_only`
`requires_credentials`
`requires_app_review`
`ready_for_testing`
`enabled`
Connectors should expose:
`getPlatform`
`getCapabilities`
`getOAuthConfig`
`buildAuthorizationUrl`
`handleOAuthCallback`
`refreshToken`
`validateConnection`
`disconnect`
`getAccountProfile`
`getRequiredScopes`
`getSetupInstructions`
Publishing methods, if present, must return disabled-by-policy until future prompts explicitly enable them.
Meta
Meta includes:
Facebook
Instagram
Threads
Meta real OAuth may be implemented only behind explicit safety flags and server-only code. Real publishing remains disabled.
YouTube, TikTok, LinkedIn, X
These connectors should be scaffolded with:
setup instructions
mock OAuth support
health check scaffold
disabled publishing methods
feature flags
safe missing-config behavior
Do not call their real APIs by default.
---
OAuth and Token Rules
OAuth state:
generate secure random state
store only a hash
expire quickly, around 10 minutes unless configured otherwise
reject missing/wrong/expired/reused state
create audit logs
Token storage:
use keychain/encrypted storage when available
otherwise default to `placeholder_not_stored`
raw token storage is forbidden unless explicit development-only insecure mode is enabled
never expose tokens to frontend
never log tokens
never include tokens in backups by default
Safe frontend account DTOs must exclude:
access tokens
refresh tokens
encrypted token blobs
authorization codes
client secrets
full OAuth state values
---
Integration Feature Flags
Use safe defaults.
Global flags:
`INTEGRATIONS_MODE=mock`
`ENABLE_REAL_NETWORK_CALLS=false`
`ENABLE_REAL_OAUTH=false`
`ENABLE_REAL_PUBLISHING=false`
`ALLOW_NETWORK_IN_TESTS=false`
`TOKEN_STORAGE_MODE=placeholder_not_stored`
Per-platform flags should exist for Meta, Google/YouTube, TikTok, LinkedIn, and X.
Even if `ENABLE_REAL_PUBLISHING=true`, publishing must remain disabled unless a future explicit real-publishing implementation changes this policy with tests and documentation.
---
Analytics Rules
Analytics sources:
`manual`
`mock`
`platform_api`
`imported_csv`
`estimated`
Mock analytics must be clearly labeled as mock/demo.
Manual analytics must be clearly labeled as manual.
Do not invent real analytics.
Recommended simple formulas:
```text
engagementRate = (likes + comments + shares + saves) / max(reach or impressions or views, 1)
clickThroughRate = clicks / max(impressions or views or reach, 1)
leadRate = leads / max(clicks or impressions or views, 1)
```
Document limitations. Do not pretend these formulas are perfect.
---
Engagement and Reply Rules
Engagement item types:
`comment`
`reply`
`mention`
`direct_message`
`review`
`lead_message`
`system_note`
`unknown`
Engagement statuses:
`new`
`needs_reply`
`reply_suggested`
`reply_approved`
`replied_manually`
`ignored`
`archived`
`spam`
`escalated`
AI reply suggestions must:
use Brand Brain
use engagement context
include recommended action
include confidence
include safety flags
default to local review
never send externally
Recommended reply actions:
`reply`
`ask_for_more_info`
`invite_to_call`
`invite_to_message`
`escalate`
`ignore`
`mark_spam`
Critical reply safety flags should block local approval until edited or resolved.
---
AI Learning Rules
The app should learn from:
analytics
performance metrics
content insights
approved/rejected drafts
approval logs
engagement items
reply suggestions
reply approvals
media metadata
Brand Brain
Memory types:
`brand_rule`
`content_preference`
`audience_learning`
`platform_learning`
`performance_learning`
`safety_learning`
`user_preference`
`rejected_strategy`
`approved_strategy`
Confidence rules:
low confidence: fewer than 5 relevant data points
medium confidence: 5 to 20 relevant data points
high confidence: more than 20 data points and consistent pattern
Do not delete memory automatically. Store evidence. Be honest when data is weak.
---
Backup, Export, and Diagnostics Rules
Backups must exclude by default:
raw OAuth tokens
refresh tokens
access tokens
API keys
client secrets
cache folders
sensitive logs
Backups should include a manifest.
Manual exports should include caption, hashtags, metadata, media manifest, and posting instructions, but never secrets.
Diagnostics reports must redact secrets and avoid private media contents.
---
UI and UX Standards
The app should use consistent names:
Home
Onboarding
Brand Brain
Media Library
Generate
Drafts
Calendar
Publish Queue
Manual Export
Connected Accounts
Social Integration Setup
Analytics
Engagement Inbox
Weekly Reports
AI Memory
Settings
Safety Center
Backup & Data
Diagnostics
Every main screen should have:
clear header
primary action
empty state
loading state
error state
safety labels where relevant
Labels must distinguish:
mock/demo data
local-only actions
manual export
mock publish
local approval
real publishing disabled
Accessibility basics:
buttons have labels
forms have labels
keyboard focus is visible
status is not conveyed only by color
long captions wrap/truncate safely
dangerous actions require confirmation
---
Documentation Requirements
When adding or changing behavior, update relevant docs.
Important docs include:
`docs/roadmap.md`
`docs/database-schema.md`
`docs/safety-and-automation-policy.md`
`docs/prompt-evaluation.md`
`docs/scheduling.md`
`docs/publish-queue.md`
`docs/local-job-runner.md`
`docs/manual-export.md`
`docs/platform-preflight-matrix.md`
`docs/social-connectors.md`
`docs/oauth-flow.md`
`docs/token-security.md`
`docs/meta-integration.md`
`docs/connected-accounts.md`
`docs/social-integration-setup.md`
`docs/integration-feature-flags.md`
`docs/platform-http-client.md`
`docs/connector-health-checks.md`
`docs/analytics.md`
`docs/engagement-inbox.md`
`docs/reply-suggestions.md`
`docs/ai-learning-loop.md`
`docs/weekly-reports.md`
`docs/user-guide.md`
`docs/non-coder-setup.md`
`docs/operator-manual.md`
`docs/common-workflows.md`
`docs/troubleshooting.md`
`docs/privacy-and-local-data.md`
`docs/safety-controls.md`
`docs/glossary.md`
`docs/launch-candidate-checklist.md`
Docs should be plain language and honest about unfinished features.
Do not claim production readiness unless launch checks pass.
---
Testing and Verification
Run available checks after implementation:
typecheck
lint
tests
database migration/generation
seed script
build
desktop build/check if configured
launch check script if configured
security scan if configured
If a command fails, report:
exact command
high-level error
likely cause
smallest next fix
Do not hide failures.
Mock/Test Defaults
Tests must not call real external APIs by default.
Network calls in tests should be blocked unless `ALLOW_NETWORK_IN_TESTS=true`.
Mock provider should produce deterministic output for tests.
Required Test Themes
Over time, tests should cover:
prompt rendering
structured output validation
mock generation
draft persistence
approval queue
scheduling eligibility
emergency pause
publish queue preflight
manual export
OAuth state validation
token redaction
safe DTOs
connector registry
account readiness
analytics formulas
engagement status updates
reply suggestion safety
AI memory confidence
backup secret exclusion
diagnostics redaction
launch workflow
---
Security Scan Requirements
Search for accidental secret exposure before launch or after integration work.
Risky patterns:
`access_token`
`refresh_token`
`client_secret`
`Authorization`
`Bearer`
`id_token`
`appsecret_proof`
`signed_request`
`OPENAI_API_KEY`
`ANTHROPIC_API_KEY`
`META_CLIENT_SECRET`
`GOOGLE_CLIENT_SECRET`
`TIKTOK_CLIENT_SECRET`
`LINKEDIN_CLIENT_SECRET`
`X_CLIENT_SECRET`
It is okay for docs and `.env.example` to mention variable names. It is not okay to include real-looking secret values.
Do not print suspected secrets. Redact them.
---
Environment Variables
Keep `.env.example` updated.
Expected variables include:
```text
APP_ENV=
DATABASE_URL=
LOCAL_DATA_DIR=

OPENAI_API_KEY=
ANTHROPIC_API_KEY=

INTEGRATIONS_MODE=mock
ENABLE_REAL_NETWORK_CALLS=false
ENABLE_REAL_OAUTH=false
ENABLE_REAL_PUBLISHING=false
ALLOW_NETWORK_IN_TESTS=false
TOKEN_STORAGE_MODE=placeholder_not_stored

META_CLIENT_ID=
META_CLIENT_SECRET=
META_REDIRECT_URI=
META_GRAPH_API_VERSION=
META_ENABLE_REAL_OAUTH=false
META_ENABLE_REAL_PUBLISHING=false

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
GOOGLE_ENABLE_REAL_OAUTH=false
GOOGLE_ENABLE_REAL_PUBLISHING=false

TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_REDIRECT_URI=
TIKTOK_ENABLE_REAL_OAUTH=false
TIKTOK_ENABLE_REAL_PUBLISHING=false

LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=
LINKEDIN_ENABLE_REAL_OAUTH=false
LINKEDIN_ENABLE_REAL_PUBLISHING=false

X_CLIENT_ID=
X_CLIENT_SECRET=
X_REDIRECT_URI=
X_ENABLE_REAL_OAUTH=false
X_ENABLE_REAL_PUBLISHING=false
```
Never commit `.env`.
---
Commands
Use the repo's actual commands. If unsure, inspect `package.json`, `pyproject.toml`, `Makefile`, or equivalent.
Common command names may include:
```text
npm run dev
npm run build
npm run lint
npm run typecheck
npm run test
npm run db:migrate
npm run db:seed
npm run jobs:once
npm run jobs:dev
npm run launch:check
npm run desktop:dev
npm run desktop:build
```
Do not invent commands in final reports. If a command does not exist, say so and recommend adding it.
---
Definition of Done
A task is done only when:
It follows this `AGENTS.md`.
It completes the requested scope.
It preserves local-first behavior.
It does not expose secrets.
It does not enable real publishing accidentally.
It keeps mock mode working.
It validates inputs and handles errors.
It updates docs where behavior changed.
It runs available checks.
It reports failures honestly.
---
Reporting Format for Builder Agents
At the end of each prompt/task, report:
What was completed.
Files changed.
How to use or verify the feature.
Commands run.
Results of checks.
Errors, skipped checks, or blockers.
Safety notes.
Recommended next step.
For checkpoint prompts, report:
Repo status summary.
Dependency checklist.
Recommended implementation plan.
Risks/blockers.
Exact next prompt to run.
---
Non-Negotiable Do Not List
Do not:
publish real posts
send real replies
scrape social platforms
expose tokens
commit secrets
store raw tokens by default
hide safety flags
auto-approve content
auto-reply to complaints
invent claims/testimonials/prices
delete user data without confirmation
overwrite backups without warning
call real APIs in tests by default
claim unfinished features are complete
claim production readiness unless launch checks pass
---
Future Real Publishing Rule
Real publishing should be implemented later, one platform at a time.
Before enabling real publishing, require:
real OAuth working
secure token storage
platform API docs verified
account selection
app review requirements understood
preflight tests
approval gates
emergency pause enforcement
post-publish audit logs
rate limit handling
rollback/error handling
manual export fallback
launch checklist update
explicit user confirmation
Until then, manual export is the safe path.
