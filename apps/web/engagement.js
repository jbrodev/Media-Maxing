// Engagement Inbox screen - Temporary browser Engagement adapter.
//
// This module mirrors the local SQLite engagement service closely enough for
// static UI development. TODO: replace localStorage reads and writes with a
// thin local API bridge into scripts/services/engagement.py. Replies are not
// sent automatically. A reply approval means approved locally only. Local
// status changes never call social platform APIs.

(function () {
  const ENGAGEMENT_ITEMS_KEY = "local-social-ai-manager.engagementItems";
  const SETTINGS_KEY = "local-social-ai-manager.settings";
  const platformIds = ["facebook", "instagram", "threads", "youtube", "tiktok", "linkedin", "x"];
  const engagementStatuses = [
    "new",
    "needs_reply",
    "reply_suggested",
    "reply_approved",
    "replied_manually",
    "ignored",
    "archived",
    "spam",
    "escalated",
  ];
  let selectedEngagementId = null;

  function getElement(id) {
    return document.getElementById(id);
  }

  function safeParse(raw, fallback) {
    if (!raw) return fallback;
    try {
      const parsed = JSON.parse(raw);
      return parsed == null ? fallback : parsed;
    } catch (error) {
      console.warn("engagement: failed to parse local demo data", error);
      return fallback;
    }
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatStatus(value) {
    return String(value || "-").replace(/_/g, " ");
  }

  function formatDateTime(value) {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "-";
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(date);
  }

  function daysAgoIso(days, hour) {
    const date = new Date();
    date.setDate(date.getDate() - days);
    date.setHours(hour, 0, 0, 0);
    return date.toISOString();
  }

  function defaultMockEngagementItems() {
    return [
      {
        id: "browser-mock-engagement-praise-comment",
        platform: "instagram",
        itemType: "comment",
        authorName: "Demo Visitor A",
        authorHandle: "@demo_neighbor_a",
        content: "The refreshed walkway looks great. Nice work keeping the edges tidy.",
        receivedAt: daysAgoIso(0, 9),
        sentiment: "positive",
        intent: "praise",
        priority: "low",
        status: "new",
        requiresResponse: false,
        relatedPost: "Driveway refresh: before and after",
        threadContext: "Public demo comment on a mock transformation post.",
        notes: "Clearly fake local fixture.",
      },
      {
        id: "browser-mock-engagement-pricing-question",
        platform: "facebook",
        itemType: "comment",
        authorName: "Demo Visitor B",
        authorHandle: "@demo_homeowner_b",
        content: "Do you provide estimates for gutter cleaning? I am comparing options for later this month.",
        receivedAt: daysAgoIso(0, 10),
        sentiment: "neutral",
        intent: "price_request",
        priority: "normal",
        status: "needs_reply",
        requiresResponse: true,
        relatedPost: "When should gutters be checked?",
        threadContext: "Public demo comment on a mock FAQ post.",
        notes: "Do not invent pricing. Invite the person to request an estimate.",
      },
      {
        id: "browser-mock-engagement-booking-request",
        platform: "instagram",
        itemType: "direct_message",
        authorName: "Demo Visitor C",
        authorHandle: "@demo_neighbor_c",
        content: "I would like to ask about booking an exterior cleanup. What is the best way to get started?",
        receivedAt: daysAgoIso(1, 14),
        sentiment: "neutral",
        intent: "booking_request",
        priority: "high",
        status: "needs_reply",
        requiresResponse: true,
        relatedPost: "Driveway refresh: before and after",
        threadContext: "Private demo message. Keep any future response general and owner-reviewed.",
        notes: "Fake fixture with no customer contact details.",
      },
      {
        id: "browser-mock-engagement-complaint",
        platform: "facebook",
        itemType: "comment",
        authorName: "Demo Visitor D",
        authorHandle: "@demo_neighbor_d",
        content: "I expected a clearer explanation of what the seasonal service includes.",
        receivedAt: daysAgoIso(1, 16),
        sentiment: "negative",
        intent: "complaint",
        priority: "high",
        status: "escalated",
        requiresResponse: true,
        relatedPost: "Seasonal exterior care reminder",
        threadContext: "Public demo complaint. Human review is required before any response.",
        notes: "Escalated by default. Never auto-reply to complaints.",
      },
      {
        id: "browser-mock-engagement-spam",
        platform: "threads",
        itemType: "mention",
        authorName: "Demo Visitor E",
        authorHandle: "@demo_offer_e",
        content: "Promote your page instantly with our unrelated demo offer.",
        receivedAt: daysAgoIso(2, 11),
        sentiment: "unknown",
        intent: "spam",
        priority: "low",
        status: "spam",
        requiresResponse: false,
        relatedPost: "-",
        threadContext: "Mock spam mention.",
        notes: "Safe to mark as spam locally. No deletion occurs.",
      },
      {
        id: "browser-mock-engagement-review-like-comment",
        platform: "facebook",
        itemType: "review",
        authorName: "Demo Visitor F",
        authorHandle: "@demo_neighbor_f",
        content: "The process explanation was helpful and straightforward.",
        receivedAt: daysAgoIso(3, 13),
        sentiment: "positive",
        intent: "praise",
        priority: "normal",
        status: "new",
        requiresResponse: false,
        relatedPost: "Behind the scenes: careful setup",
        threadContext: "Clearly fake review-like comment for local UI testing.",
        notes: "Do not reuse this as a real testimonial.",
      },
      {
        id: "browser-mock-engagement-urgent-lead",
        platform: "instagram",
        itemType: "lead_message",
        authorName: "Demo Visitor G",
        authorHandle: "@demo_neighbor_g",
        content: "I need to understand whether you cover my area before I arrange a walkthrough.",
        receivedAt: daysAgoIso(0, 8),
        sentiment: "neutral",
        intent: "urgent",
        priority: "urgent",
        status: "escalated",
        requiresResponse: true,
        relatedPost: "Driveway refresh: before and after",
        threadContext: "Urgent demo lead. Owner follow-up is required.",
        notes: "Do not invent service-area coverage or availability.",
      },
      {
        id: "browser-mock-engagement-general-comment",
        platform: "linkedin",
        itemType: "comment",
        authorName: "Demo Visitor H",
        authorHandle: "@demo_local_h",
        content: "Thanks for showing the preparation steps behind the project.",
        receivedAt: daysAgoIso(4, 15),
        sentiment: "positive",
        intent: "general",
        priority: "normal",
        status: "new",
        requiresResponse: false,
        relatedPost: "Behind the scenes: careful setup",
        threadContext: "Public demo comment on a mock process post.",
        notes: "Clearly fake local fixture.",
      },
    ];
  }

  function normalizeEngagementItem(item) {
    const now = new Date().toISOString();
    return {
      id: item.id,
      platform: platformIds.includes(item.platform) ? item.platform : "facebook",
      itemType: item.itemType || "unknown",
      authorName: item.authorName || "",
      authorHandle: item.authorHandle || "",
      content: item.content || "",
      receivedAt: item.receivedAt || now,
      sentiment: item.sentiment || "unknown",
      intent: item.intent || "unknown",
      priority: item.priority || "normal",
      status: engagementStatuses.includes(item.status) ? item.status : "new",
      requiresResponse: item.requiresResponse === true,
      source: item.source || "manual",
      relatedPost: item.relatedPost || "-",
      threadContext: item.threadContext || "No additional local thread context.",
      notes: item.notes || "",
      createdAt: item.createdAt || now,
      updatedAt: item.updatedAt || now,
    };
  }

  function loadEngagementItems() {
    const stored = safeParse(window.localStorage.getItem(ENGAGEMENT_ITEMS_KEY), []);
    return Array.isArray(stored) ? stored.map(normalizeEngagementItem) : [];
  }

  function saveEngagementItems(items) {
    window.localStorage.setItem(
      ENGAGEMENT_ITEMS_KEY,
      JSON.stringify(items.map(normalizeEngagementItem)),
    );
  }

  function generateMockEngagement() {
    if (!mockEngagementAllowed()) {
      throw new Error("Mock engagement is available only in development, demo, or test mode.");
    }
    const existing = loadEngagementItems();
    const knownIds = new Set(existing.map((item) => item.id));
    const createdAt = new Date().toISOString();
    const created = defaultMockEngagementItems()
      .filter((item) => !knownIds.has(item.id))
      .map((item) => normalizeEngagementItem({
        ...item,
        source: "mock",
        createdAt,
        updatedAt: createdAt,
      }));
    if (created.length) saveEngagementItems(existing.concat(created));
    return created;
  }

  function updateEngagementStatus(itemId, status) {
    if (!engagementStatuses.includes(status)) {
      throw new Error("Choose a supported local engagement status.");
    }
    const items = loadEngagementItems();
    const item = items.find((entry) => entry.id === itemId);
    if (!item) throw new Error("Select an engagement item before recording an action.");
    item.status = status;
    item.requiresResponse = ["needs_reply", "reply_suggested", "reply_approved", "escalated"].includes(status);
    item.updatedAt = new Date().toISOString();
    saveEngagementItems(items);
    return item;
  }

  function mockEngagementAllowed() {
    const settings = safeParse(window.localStorage.getItem(SETTINGS_KEY), {});
    return ["development", "demo", "test"].includes(settings.appEnvironment || "development");
  }

  function dateRangeMatches(item, days) {
    if (days === "all") return true;
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() - Number(days));
    return new Date(item.receivedAt) >= cutoff;
  }

  function filteredEngagementItems() {
    const platform = getElement("engagement-platform-filter")?.value || "all";
    const status = getElement("engagement-status-filter")?.value || "all";
    const sentiment = getElement("engagement-sentiment-filter")?.value || "all";
    const intent = getElement("engagement-intent-filter")?.value || "all";
    const priority = getElement("engagement-priority-filter")?.value || "all";
    const source = getElement("engagement-source-filter")?.value || "all";
    const range = getElement("engagement-date-filter")?.value || "all";
    const search = (getElement("engagement-search")?.value || "").trim().toLowerCase();
    return loadEngagementItems()
      .filter((item) => platform === "all" || item.platform === platform)
      .filter((item) => status === "all" || item.status === status)
      .filter((item) => sentiment === "all" || item.sentiment === sentiment)
      .filter((item) => intent === "all" || item.intent === intent)
      .filter((item) => priority === "all" || item.priority === priority)
      .filter((item) => source === "all" || item.source === source)
      .filter((item) => dateRangeMatches(item, range))
      .filter((item) => {
        if (!search) return true;
        return `${item.content} ${item.authorName} ${item.authorHandle} ${item.platform}`
          .toLowerCase()
          .includes(search);
      })
      .sort((a, b) => new Date(b.receivedAt) - new Date(a.receivedAt));
  }

  function count(items, predicate) {
    return items.filter(predicate).length;
  }

  function renderEngagementSummary(items) {
    getElement("engagement-summary-new").textContent = count(items, (item) => item.status === "new");
    getElement("engagement-summary-needs-reply").textContent = count(items, (item) => item.status === "needs_reply");
    getElement("engagement-summary-reply-suggested").textContent = count(items, (item) => item.status === "reply_suggested");
    getElement("engagement-summary-approved").textContent = count(items, (item) => item.status === "reply_approved");
    getElement("engagement-summary-urgent").textContent = count(items, (item) => item.priority === "urgent");
    getElement("engagement-summary-complaints").textContent = count(items, (item) => item.intent === "complaint");
    getElement("engagement-summary-leads").textContent = count(items, (item) => ["booking_request", "price_request", "urgent"].includes(item.intent));
    getElement("engagement-summary-spam").textContent = count(items, (item) => item.status === "spam" || item.intent === "spam");
  }

  function badgeClass(value) {
    if (["spam", "escalated", "negative", "urgent"].includes(value)) return "engagement-badge danger";
    if (["needs_reply", "complaint", "high"].includes(value)) return "engagement-badge warning";
    if (["positive", "replied_manually"].includes(value)) return "engagement-badge success";
    return "engagement-badge";
  }

  function engagementCardMarkup(item) {
    const author = item.authorHandle || item.authorName || "Unknown local author";
    return `
      <button class="engagement-card${item.id === selectedEngagementId ? " selected" : ""}" type="button" data-engagement-id="${escapeHtml(item.id)}">
        <div class="engagement-card-header">
          <span class="engagement-platform">${escapeHtml(formatStatus(item.platform))}</span>
          <span class="${badgeClass(item.source)}">${escapeHtml(formatStatus(item.source))}</span>
        </div>
        <h3>${escapeHtml(author)}</h3>
        <p>${escapeHtml(item.content)}</p>
        <div class="engagement-card-meta">
          <span>${escapeHtml(formatStatus(item.itemType))}</span>
          <span class="${badgeClass(item.sentiment)}">${escapeHtml(formatStatus(item.sentiment))}</span>
          <span class="${badgeClass(item.intent)}">${escapeHtml(formatStatus(item.intent))}</span>
          <span class="${badgeClass(item.priority)}">${escapeHtml(formatStatus(item.priority))}</span>
          <span class="${badgeClass(item.status)}">${escapeHtml(formatStatus(item.status))}</span>
        </div>
        <small>${escapeHtml(formatDateTime(item.receivedAt))}${item.relatedPost !== "-" ? ` · ${escapeHtml(item.relatedPost)}` : ""}</small>
      </button>
    `;
  }

  function renderEngagementList() {
    const items = filteredEngagementItems();
    const list = getElement("engagement-list");
    const empty = getElement("engagement-empty-state");
    empty.hidden = items.length > 0;
    list.innerHTML = items.map(engagementCardMarkup).join("");
    if (!items.some((item) => item.id === selectedEngagementId)) {
      selectedEngagementId = items[0]?.id || null;
    }
    renderEngagementDetail();
  }

  function setText(id, value) {
    getElement(id).textContent = value || "-";
  }

  function renderEngagementDetail() {
    const empty = getElement("engagement-detail-empty");
    const content = getElement("engagement-detail-content");
    const item = loadEngagementItems().find((entry) => entry.id === selectedEngagementId);
    empty.hidden = Boolean(item);
    content.hidden = !item;
    if (!item) return;
    setText("engagement-detail-full-content", item.content);
    setText("engagement-detail-platform", formatStatus(item.platform));
    setText("engagement-detail-author", item.authorHandle || item.authorName || "-");
    setText("engagement-detail-received", formatDateTime(item.receivedAt));
    setText("engagement-detail-sentiment", formatStatus(item.sentiment));
    setText("engagement-detail-intent", formatStatus(item.intent));
    setText("engagement-detail-priority", formatStatus(item.priority));
    setText("engagement-detail-status", formatStatus(item.status));
    setText("engagement-detail-related-post", item.relatedPost);
    setText("engagement-detail-thread", item.threadContext);
    setText("engagement-detail-notes", item.notes);
  }

  function setActionMessage(kind, message) {
    const success = getElement("engagement-action-message");
    const error = getElement("engagement-action-error");
    success.hidden = kind !== "success";
    error.hidden = kind !== "error";
    success.textContent = kind === "success" ? message : "";
    error.textContent = kind === "error" ? message : "";
  }

  function handleStatusAction(status) {
    try {
      updateEngagementStatus(selectedEngagementId, status);
      setActionMessage(
        "success",
        status === "replied_manually"
          ? "Marked replied manually. Manual reply tracking is local only."
          : `Local status updated to ${formatStatus(status)}. Replies are not sent automatically.`,
      );
      renderEngagement();
    } catch (error) {
      setActionMessage("error", error.message || "The local engagement action could not be recorded.");
    }
  }

  function renderEngagement() {
    const loading = getElement("engagement-loading-state");
    const error = getElement("engagement-error-state");
    if (!loading || !error) return;
    try {
      loading.hidden = true;
      error.hidden = true;
      const items = loadEngagementItems();
      renderEngagementSummary(items);
      renderEngagementList();
    } catch (renderError) {
      console.error("engagement: render failed", renderError);
      loading.hidden = true;
      error.hidden = false;
    }
  }

  function setupEngagement() {
    const view = getElement("engagement-view");
    if (!view) return;
    [
      "engagement-platform-filter",
      "engagement-status-filter",
      "engagement-sentiment-filter",
      "engagement-intent-filter",
      "engagement-priority-filter",
      "engagement-source-filter",
      "engagement-date-filter",
    ].forEach((id) => getElement(id).addEventListener("change", renderEngagement));
    getElement("engagement-search").addEventListener("input", renderEngagement);
    getElement("engagement-list").addEventListener("click", (event) => {
      const card = event.target.closest("[data-engagement-id]");
      if (!card) return;
      selectedEngagementId = card.dataset.engagementId;
      renderEngagementList();
    });
    const statusActions = {
      "engagement-mark-needs-reply": "needs_reply",
      "engagement-ignore": "ignored",
      "engagement-archive": "archived",
      "engagement-mark-spam": "spam",
      "engagement-escalate": "escalated",
      "engagement-mark-replied-manually": "replied_manually",
    };
    Object.entries(statusActions).forEach(([id, status]) => {
      getElement(id).addEventListener("click", () => handleStatusAction(status));
    });
    const mockButton = getElement("engagement-generate-mock");
    mockButton.hidden = !mockEngagementAllowed();
    mockButton.addEventListener("click", () => {
      try {
        const created = generateMockEngagement();
        const message = created.length
          ? `${created.length} clearly labeled mock engagement items generated locally. No comments were fetched and no replies were sent.`
          : "Mock engagement is already loaded. Existing stable demo records were kept without duplicates.";
        getElement("engagement-mock-message").textContent = message;
        getElement("engagement-mock-message").hidden = false;
        renderEngagement();
      } catch (error) {
        setActionMessage("error", error.message || "Mock engagement could not be generated.");
      }
    });
    renderEngagement();
    window.addEventListener("hashchange", () => {
      if (window.location.hash === "#engagement") renderEngagement();
    });
  }

  document.addEventListener("DOMContentLoaded", setupEngagement);
})();
