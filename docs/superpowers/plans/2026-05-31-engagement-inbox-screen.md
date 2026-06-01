# Engagement Inbox Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a local-only Engagement Inbox screen for reviewing mock/manual engagement items and recording reply workflow status without fetching comments or sending replies.

**Architecture:** Add a dedicated `apps/web/engagement.js` browser adapter, following the existing Analytics adapter pattern. The adapter stores fake demo inbox items in `localStorage`, exposes filters and status transitions, and keeps AI reply suggestions as an explicitly unavailable placeholder until the next prompt. The Python SQLite engagement service remains the source of truth for server-side ingestion; browser-to-SQLite wiring remains a later API bridge.

**Tech Stack:** Static HTML, CSS, vanilla JavaScript, browser `localStorage`, Python `unittest`.

---

### Task 1: Define Engagement Screen Contract

**Files:**
- Create: `tests/test_web_engagement_screen.py`

- [ ] **Step 1: Write the failing screen-structure test**

Assert that `apps/web/index.html` contains the Engagement route, required filter controls, summary IDs, loading/error/empty states, item list, detail panel, action buttons, safety copy, and `engagement.js` script tag.

- [ ] **Step 2: Write the failing adapter test**

Assert that `apps/web/engagement.js` exists, uses the `local-social-ai-manager.engagementItems` storage key, provides mock ingestion and local status transition handlers, contains no `fetch(` call, and labels approved replies as local-only.

- [ ] **Step 3: Write the failing CSS contract test**

Assert that `apps/web/styles.css` includes the inbox workspace, summary, toolbar, list, card, detail, and action classes.

- [ ] **Step 4: Run the test to verify RED**

Run:

```text
python -m unittest tests.test_web_engagement_screen
```

Expected: failure because the Engagement route, adapter, and styles do not exist yet.

### Task 2: Add Engagement Inbox Markup And Routing

**Files:**
- Modify: `apps/web/index.html`
- Modify: `apps/web/settings.js`

- [ ] **Step 1: Add the route markup**

Insert `#engagement-view` before Analytics. Include:

```html
<section class="route-view" id="engagement-view" data-route="engagement" hidden>
  <header class="topbar">...</header>
  <section class="status-strip">...</section>
  <section class="engagement-summary-grid">...</section>
  <section class="workspace-section engagement-workspace">...</section>
</section>
```

- [ ] **Step 2: Add routing support**

Add `"engagement"` to `supportedRoutes` in `apps/web/settings.js`.

- [ ] **Step 3: Add the adapter script**

Load:

```html
<script src="./engagement.js"></script>
```

### Task 3: Implement Browser Demo Adapter

**Files:**
- Create: `apps/web/engagement.js`

- [ ] **Step 1: Add deterministic fake records**

Create eight fake scenarios with stable IDs: praise, pricing question, booking request, complaint, spam, review-like comment, urgent lead message, and general comment. Every record must use `source: "mock"` and contain no real customer data.

- [ ] **Step 2: Add local persistence helpers**

Implement:

```js
function loadEngagementItems() {}
function saveEngagementItems(items) {}
function generateMockEngagement() {}
function updateEngagementStatus(itemId, status) {}
```

`generateMockEngagement()` must skip existing stable IDs.

- [ ] **Step 3: Add filtering and rendering**

Implement:

```js
function filteredEngagementItems() {}
function renderEngagementSummary(items) {}
function renderEngagementList() {}
function renderEngagementDetail() {}
function renderEngagement() {}
```

Render raw provider data only as a hidden-by-design omission; do not place raw payloads in the detail panel.

- [ ] **Step 4: Add local-only actions**

Wire status buttons for `needs_reply`, `ignored`, `archived`, `spam`, `escalated`, and `replied_manually`. Keep AI suggestion generation as a visible disabled placeholder with local-review copy.

- [ ] **Step 5: Add development-only mock ingestion**

Show the button only when app environment is `development`, `demo`, or `test`.

### Task 4: Style The Existing-Shell Screen

**Files:**
- Modify: `apps/web/styles.css`

- [ ] **Step 1: Add inbox layout styles**

Add restrained styles for:

```css
.engagement-summary-grid {}
.engagement-toolbar {}
.engagement-layout {}
.engagement-list {}
.engagement-card {}
.engagement-detail-panel {}
.engagement-detail-grid {}
.engagement-actions {}
```

- [ ] **Step 2: Add responsive behavior**

Collapse the list/detail layout and filters at existing `1100px` and `720px` breakpoints.

### Task 5: Document Browser Adapter Limitations

**Files:**
- Modify: `docs/engagement-inbox.md`
- Modify: `README.md`

- [ ] **Step 1: Document the screen**

Explain local-only status actions, stable fake browser fixtures, placeholder reply suggestions, and the future API bridge.

- [ ] **Step 2: Update project status**

State honestly that the Engagement Inbox browser screen exists while SQLite wiring and AI reply suggestions remain future work.

### Task 6: Verify

- [ ] **Step 1: Run focused tests**

```text
python -m unittest tests.test_web_engagement_screen
```

- [ ] **Step 2: Run full checks**

```text
python -m unittest discover tests
python -m compileall -q scripts tests
node --check apps/web/settings.js
node --check apps/web/generate.js
node --check apps/web/analytics.js
node --check apps/web/engagement.js
python -m scripts.qa.integration_security_scan .
```

- [ ] **Step 3: Perform browser QA**

Open `apps/web/index.html#engagement`, generate mock engagement, filter complaints, open details, update ignored/escalated/replied-manually statuses, refresh, and confirm browser-local persistence.
