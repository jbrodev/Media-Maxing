// Analytics screen - Local browser Analytics adapter.
//
// This module mirrors the local SQLite analytics service for rendering.
// When the localhost bridge is active, mutations persist through
// scripts/services/analytics.py. Direct-file mode remains a localStorage demo
// fallback. Keep manual and mock provenance visible in both modes.

(function () {
  const ANALYTICS_SNAPSHOTS_KEY = "local-social-ai-manager.analyticsSnapshots";
  const ANALYTICS_INSIGHTS_KEY = "local-social-ai-manager.analyticsInsights";
  const AI_MEMORY_KEY = "local-social-ai-manager.aiMemory";
  const WEEKLY_REPORTS_KEY = "local-social-ai-manager.weeklyReports";
  const DRAFTS_KEY = "local-social-ai-manager.drafts";
  const SETTINGS_KEY = "local-social-ai-manager.settings";
  const MANUAL_SOURCE = "manual";
  const MOCK_SOURCE = "mock";
  const platformIds = ["facebook", "instagram", "threads", "youtube", "tiktok", "linkedin", "x"];
  const numericFields = [
    "impressions",
    "reach",
    "views",
    "likes",
    "comments",
    "shares",
    "saves",
    "clicks",
    "leads",
    "messages",
    "calls",
    "websiteClicks",
  ];

  function activeApiBridge() {
    return window.localApiBridge?.available ? window.localApiBridge : null;
  }

  function currentBrandProfileId() {
    return activeApiBridge()?.snapshot?.brandProfile?.id || "demo-brand-brightside-exterior-care";
  }

  function getElement(id) {
    return document.getElementById(id);
  }

  function safeParse(raw, fallback) {
    if (!raw) return fallback;
    try {
      const parsed = JSON.parse(raw);
      return parsed == null ? fallback : parsed;
    } catch (error) {
      console.warn("analytics: failed to parse local demo data", error);
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

  function dateOnly(date) {
    return new Date(date).toISOString().slice(0, 10);
  }

  function daysAgo(days) {
    const date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() - days);
    return dateOnly(date);
  }

  function currentWeekStart() {
    const date = new Date();
    date.setHours(12, 0, 0, 0);
    const mondayOffset = (date.getDay() + 6) % 7;
    date.setDate(date.getDate() - mondayOffset);
    return dateOnly(date);
  }

  function addDays(dateValue, days) {
    const date = new Date(`${dateValue}T12:00:00`);
    date.setDate(date.getDate() + days);
    return dateOnly(date);
  }

  function formatNumber(value) {
    return new Intl.NumberFormat("en-US").format(Number(value) || 0);
  }

  function formatPercent(value) {
    return `${((Number(value) || 0) * 100).toFixed(1)}%`;
  }

  function formatStatus(value) {
    return String(value || "-").replace(/_/g, " ");
  }

  function formatEvidence(value) {
    if (!value) return "No evidence summary yet.";
    if (typeof value === "string") return value;
    if (typeof value === "object") {
      const dataPoints = value.dataPoints ?? value.data_points;
      const source = value.source || value.platform || value.angle;
      const parts = [];
      if (dataPoints != null) parts.push(`${dataPoints} data point(s)`);
      if (source) parts.push(`signal: ${source}`);
      return parts.join("; ") || "Local evidence references stored.";
    }
    return String(value);
  }

  function toMetric(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) && parsed >= 0 ? Math.round(parsed) : 0;
  }

  function defaultTrackedPosts() {
    return [
      {
        id: "analytics-demo-driveway",
        platform: "instagram",
        headline: "Driveway refresh: before and after",
        hook: "A careful cleanup can change the first impression.",
        caption: "A local driveway cleanup demo with a clear before-and-after result.",
        contentGoal: "show_transformation",
        contentAngle: "before_after",
        postedAt: daysAgo(4),
        linkTarget: "#drafts",
      },
      {
        id: "analytics-demo-gutter-faq",
        platform: "facebook",
        headline: "When should gutters be checked?",
        hook: "A quick seasonal check can prevent a messy surprise.",
        caption: "A plain-language gutter care FAQ for local homeowners.",
        contentGoal: "educate_customer",
        contentAngle: "faq",
        postedAt: daysAgo(7),
        linkTarget: "#drafts",
      },
      {
        id: "analytics-demo-team-process",
        platform: "linkedin",
        headline: "Behind the scenes: careful setup",
        hook: "Good exterior work starts before the equipment turns on.",
        caption: "A short process post showing careful preparation and local-service trust.",
        contentGoal: "build_trust",
        contentAngle: "behind_the_scenes",
        postedAt: daysAgo(10),
        linkTarget: "#drafts",
      },
      {
        id: "analytics-demo-seasonal",
        platform: "instagram",
        headline: "Seasonal exterior care reminder",
        hook: "A small seasonal reminder for the next clear-weather window.",
        caption: "A simple seasonal reminder without urgency hype.",
        contentGoal: "seasonal_reminder",
        contentAngle: "seasonal",
        postedAt: daysAgo(14),
        linkTarget: "#drafts",
      },
    ];
  }

  function normalizeTrackedDraft(draft) {
    return {
      id: draft.id,
      platform: draft.platform || "facebook",
      headline: draft.headline || "",
      hook: draft.hook || "",
      caption: draft.caption || "",
      contentGoal: draft.contentGoal || draft.content_goal || "unknown",
      contentAngle: draft.contentAngle || draft.content_angle || "other",
      postedAt: draft.updatedAt || draft.createdAt || new Date().toISOString(),
      linkTarget: "#drafts",
    };
  }

  function loadTrackedPosts() {
    const savedDrafts = safeParse(window.localStorage.getItem(DRAFTS_KEY), []);
    const posts = defaultTrackedPosts();
    const seen = new Set(posts.map((post) => post.id));
    if (Array.isArray(savedDrafts)) {
      savedDrafts.forEach((draft) => {
        if (draft?.id && !seen.has(draft.id)) {
          posts.push(normalizeTrackedDraft(draft));
          seen.add(draft.id);
        }
      });
    }
    return posts;
  }

  function calculateAnalyticsRates(metrics) {
    const likes = toMetric(metrics.likes);
    const comments = toMetric(metrics.comments);
    const shares = toMetric(metrics.shares);
    const saves = toMetric(metrics.saves);
    const clicks = toMetric(metrics.clicks);
    const leads = toMetric(metrics.leads);
    const engagementBase = Math.max(toMetric(metrics.reach) || toMetric(metrics.impressions) || toMetric(metrics.views), 1);
    const clickBase = Math.max(toMetric(metrics.impressions) || toMetric(metrics.views) || toMetric(metrics.reach), 1);
    const leadBase = Math.max(clicks || toMetric(metrics.impressions) || toMetric(metrics.views), 1);
    const engagementRate = (likes + comments + shares + saves) / engagementBase;
    const clickThroughRate = clicks / clickBase;
    const leadRate = leads / leadBase;
    const performanceScore = Math.min(
      100,
      engagementRate * 100 * 0.4 + clickThroughRate * 100 * 0.2 + leadRate * 100 * 0.3 + Math.min(saves, 10),
    );
    return { engagementRate, clickThroughRate, leadRate, performanceScore };
  }

  function normalizeSnapshot(snapshot) {
    const metrics = {};
    numericFields.forEach((field) => {
      metrics[field] = toMetric(snapshot[field]);
    });
    return {
      id: snapshot.id,
      generatedPostId: snapshot.generatedPostId,
      platform: platformIds.includes(snapshot.platform) ? snapshot.platform : "facebook",
      source: snapshot.source || MOCK_SOURCE,
      snapshotDate: snapshot.snapshotDate || dateOnly(new Date()),
      notes: snapshot.notes || "",
      demo: snapshot.demo === true || snapshot.source === MOCK_SOURCE,
      createdAt: snapshot.createdAt || new Date().toISOString(),
      updatedAt: snapshot.updatedAt || new Date().toISOString(),
      ...metrics,
      ...calculateAnalyticsRates(metrics),
    };
  }

  function defaultAnalyticsSnapshots() {
    return [
      {
        id: "analytics-snapshot-driveway",
        generatedPostId: "analytics-demo-driveway",
        platform: "instagram",
        source: "mock",
        snapshotDate: daysAgo(3),
        impressions: 2840,
        reach: 2110,
        views: 1220,
        likes: 184,
        comments: 22,
        shares: 31,
        saves: 46,
        clicks: 38,
        leads: 7,
        messages: 4,
        calls: 2,
        websiteClicks: 21,
        notes: "Clearly fake demo snapshot for UI development.",
        demo: true,
      },
      {
        id: "analytics-snapshot-gutter",
        generatedPostId: "analytics-demo-gutter-faq",
        platform: "facebook",
        source: "mock",
        snapshotDate: daysAgo(6),
        impressions: 1710,
        reach: 1420,
        views: 320,
        likes: 81,
        comments: 29,
        shares: 18,
        saves: 12,
        clicks: 31,
        leads: 5,
        messages: 3,
        calls: 1,
        websiteClicks: 14,
        notes: "Clearly fake demo snapshot for UI development.",
        demo: true,
      },
      {
        id: "analytics-snapshot-team",
        generatedPostId: "analytics-demo-team-process",
        platform: "linkedin",
        source: "mock",
        snapshotDate: daysAgo(9),
        impressions: 780,
        reach: 610,
        views: 120,
        likes: 34,
        comments: 6,
        shares: 4,
        saves: 3,
        clicks: 9,
        leads: 1,
        messages: 0,
        calls: 0,
        websiteClicks: 5,
        notes: "Clearly fake demo snapshot for UI development.",
        demo: true,
      },
      {
        id: "analytics-snapshot-seasonal",
        generatedPostId: "analytics-demo-seasonal",
        platform: "instagram",
        source: "mock",
        snapshotDate: daysAgo(13),
        impressions: 640,
        reach: 570,
        views: 210,
        likes: 23,
        comments: 2,
        shares: 3,
        saves: 4,
        clicks: 4,
        leads: 0,
        messages: 0,
        calls: 0,
        websiteClicks: 2,
        notes: "Clearly fake demo snapshot for UI development.",
        demo: true,
      },
    ].map(normalizeSnapshot);
  }

  function loadAnalyticsSnapshots() {
    const stored = safeParse(window.localStorage.getItem(ANALYTICS_SNAPSHOTS_KEY), null);
    if (!Array.isArray(stored)) {
      const seeded = defaultAnalyticsSnapshots();
      saveAnalyticsSnapshots(seeded);
      return seeded;
    }
    return stored.map(normalizeSnapshot);
  }

  function saveAnalyticsSnapshots(snapshots) {
    window.localStorage.setItem(ANALYTICS_SNAPSHOTS_KEY, JSON.stringify(snapshots.map(normalizeSnapshot)));
  }

  function defaultAnalyticsInsights() {
    return [
      {
        id: "analytics-insight-transformations",
        title: "Transformation posts are earning stronger engagement",
        summary: "The before-and-after demo post has the clearest engagement signal in the current local snapshots.",
        confidence: "low",
        evidence: "1 demo transformation post; test with more real manual snapshots.",
        recommendedAction: "Try another honest before-and-after post with a clear project photo.",
        status: "active",
      },
      {
        id: "analytics-insight-faq",
        title: "FAQ content is creating useful conversation",
        summary: "The gutter FAQ demo has more comments than the other tracked posts.",
        confidence: "low",
        evidence: "1 demo FAQ post with a higher comment count.",
        recommendedAction: "Answer one more common seasonal question in plain language.",
        status: "active",
      },
    ];
  }

  function loadAnalyticsInsights() {
    const stored = safeParse(window.localStorage.getItem(ANALYTICS_INSIGHTS_KEY), null);
    if (!Array.isArray(stored)) {
      const seeded = defaultAnalyticsInsights();
      saveAnalyticsInsights(seeded);
      return seeded;
    }
    return stored;
  }

  function saveAnalyticsInsights(insights) {
    window.localStorage.setItem(ANALYTICS_INSIGHTS_KEY, JSON.stringify(insights));
  }

  function defaultAIMemory() {
    return [
      {
        id: "analytics-memory-demo-transformations",
        memoryType: "performance_learning",
        title: "Transformation posts are a useful idea to test",
        summary: "The current local demo evidence suggests testing another honest before-and-after post.",
        confidence: "low",
        source: "mock",
        status: "active",
      },
    ];
  }

  function loadAIMemory() {
    const stored = safeParse(window.localStorage.getItem(AI_MEMORY_KEY), null);
    if (!Array.isArray(stored)) {
      const seeded = defaultAIMemory();
      saveAIMemory(seeded);
      return seeded;
    }
    return stored;
  }

  function saveAIMemory(memories) {
    window.localStorage.setItem(AI_MEMORY_KEY, JSON.stringify(memories));
  }

  function defaultWeeklyReports() {
    const weekStartDate = currentWeekStart();
    return [
      {
        id: "analytics-weekly-report-demo",
        weekStartDate,
        weekEndDate: addDays(weekStartDate, 6),
        summary: "Clearly fake mock weekly summary for local UI review.",
        wins: ["Demo metrics show one transformation-post idea worth testing."],
        concerns: ["This report contains mock/demo data. Do not treat it as real performance."],
        recommendations: ["Add manual analytics after real posting to improve future comparisons."],
        generatedBy: "ai_mock",
      },
    ];
  }

  function loadWeeklyReports() {
    const stored = safeParse(window.localStorage.getItem(WEEKLY_REPORTS_KEY), null);
    if (!Array.isArray(stored)) {
      const seeded = defaultWeeklyReports();
      saveWeeklyReports(seeded);
      return seeded;
    }
    return stored;
  }

  function saveWeeklyReports(reports) {
    window.localStorage.setItem(WEEKLY_REPORTS_KEY, JSON.stringify(reports));
  }

  function snapshotIdentity(snapshot) {
    return `${snapshot.generatedPostId}|${snapshot.platform}|${snapshot.source}|${snapshot.snapshotDate}`;
  }

  function createManualAnalyticsSnapshot(input) {
    if (!input.generatedPostId) throw new Error("Choose a post before saving analytics.");
    if (!platformIds.includes(input.platform)) throw new Error("Choose a supported platform.");
    if (!input.snapshotDate) throw new Error("Choose a snapshot date.");
    const now = new Date().toISOString();
    const snapshot = normalizeSnapshot({
      ...input,
      id: `analytics-manual-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      source: "manual",
      demo: false,
      createdAt: now,
      updatedAt: now,
    });
    const snapshots = loadAnalyticsSnapshots();
    if (snapshots.some((existing) => snapshotIdentity(existing) === snapshotIdentity(snapshot))) {
      throw new Error("A manual snapshot already exists for this post, platform, and date.");
    }
    saveAnalyticsSnapshots(snapshots.concat(snapshot));
    return snapshot;
  }

  function deterministicMetric(postId, multiplier, minimum) {
    const total = [...postId].reduce((sum, character) => sum + character.charCodeAt(0), 0);
    return minimum + ((total * multiplier) % Math.max(minimum * 7, 10));
  }

  function generateMockAnalytics() {
    if (!mockAnalyticsAllowed()) {
      throw new Error("Mock analytics generation is available only in development, demo, or test mode.");
    }
    const posts = loadTrackedPosts();
    const snapshots = loadAnalyticsSnapshots();
    const identities = new Set(snapshots.map(snapshotIdentity));
    const today = dateOnly(new Date());
    const created = [];
    posts.forEach((post) => {
      const base = deterministicMetric(post.id, 17, 240);
      const metrics = {
        impressions: base * 3,
        reach: base * 2,
        views: base,
        likes: deterministicMetric(post.id, 3, 12),
        comments: deterministicMetric(post.id, 5, 3),
        shares: deterministicMetric(post.id, 7, 2),
        saves: deterministicMetric(post.id, 11, 4),
        clicks: deterministicMetric(post.id, 13, 5),
        leads: deterministicMetric(post.id, 19, 1),
        messages: deterministicMetric(post.id, 23, 1),
        calls: deterministicMetric(post.id, 29, 1),
        websiteClicks: deterministicMetric(post.id, 31, 2),
      };
      const snapshot = normalizeSnapshot({
        id: `analytics-mock-${post.id}-${today}`,
        generatedPostId: post.id,
        platform: post.platform,
        source: "mock",
        snapshotDate: today,
        ...metrics,
        notes: "Clearly fake demo metrics generated locally. No platform API was called.",
        demo: true,
      });
      if (!identities.has(snapshotIdentity(snapshot))) {
        identities.add(snapshotIdentity(snapshot));
        created.push(snapshot);
      }
    });
    if (created.length) saveAnalyticsSnapshots(snapshots.concat(created));
    return created;
  }

  function filteredSnapshots() {
    const range = getElement("analytics-range-filter")?.value || "30";
    const platform = getElement("analytics-platform-filter")?.value || "all";
    const source = getElement("analytics-source-filter")?.value || "all";
    const cutoff = new Date();
    if (range !== "all") cutoff.setDate(cutoff.getDate() - Number(range));
    return loadAnalyticsSnapshots().filter((snapshot) => {
      if (platform !== "all" && snapshot.platform !== platform) return false;
      if (source !== "all" && snapshot.source !== source) return false;
      if (range !== "all" && new Date(`${snapshot.snapshotDate}T23:59:59`) < cutoff) return false;
      return true;
    });
  }

  function latestSnapshots(snapshots) {
    const latest = new Map();
    snapshots.forEach((snapshot) => {
      const key = `${snapshot.generatedPostId}|${snapshot.platform}`;
      const existing = latest.get(key);
      if (!existing || snapshot.snapshotDate >= existing.snapshotDate) latest.set(key, snapshot);
    });
    return [...latest.values()];
  }

  function performanceRecords(snapshots) {
    const posts = new Map(loadTrackedPosts().map((post) => [post.id, post]));
    return latestSnapshots(snapshots).map((snapshot) => ({
      ...posts.get(snapshot.generatedPostId),
      ...snapshot,
      engagements: snapshot.likes + snapshot.comments + snapshot.shares + snapshot.saves,
    }));
  }

  function summarizeRecords(records) {
    return records.reduce(
      (summary, record) => {
        summary.posts += 1;
        summary.impressions += record.impressions;
        summary.views += record.views;
        summary.engagements += record.engagements;
        summary.clicks += record.clicks;
        summary.leads += record.leads;
        summary.engagementRate += record.engagementRate;
        summary.leadRate += record.leadRate;
        summary.performanceScore += record.performanceScore;
        return summary;
      },
      { posts: 0, impressions: 0, views: 0, engagements: 0, clicks: 0, leads: 0, engagementRate: 0, leadRate: 0, performanceScore: 0 },
    );
  }

  function average(value, count) {
    return count ? value / count : 0;
  }

  function breakdown(records, key) {
    const grouped = new Map();
    records.forEach((record) => {
      const label = record[key] || "unknown";
      const list = grouped.get(label) || [];
      list.push(record);
      grouped.set(label, list);
    });
    return [...grouped.entries()]
      .map(([label, items]) => {
        const totals = summarizeRecords(items);
        return {
          label,
          ...totals,
          engagementRate: average(totals.engagementRate, totals.posts),
          leadRate: average(totals.leadRate, totals.posts),
          performanceScore: average(totals.performanceScore, totals.posts),
        };
      })
      .sort((a, b) => b.performanceScore - a.performanceScore);
  }

  function computePlatformBreakdown(records) {
    return breakdown(records, "platform");
  }

  function computeContentBreakdown(records, key) {
    return breakdown(records, key);
  }

  function computeAnalyticsSummary(records) {
    const totals = summarizeRecords(records);
    const platforms = computePlatformBreakdown(records);
    const angles = computeContentBreakdown(records, "contentAngle");
    return {
      ...totals,
      engagementRate: average(totals.engagementRate, totals.posts),
      leadRate: average(totals.leadRate, totals.posts),
      bestPlatform: platforms[0]?.label || "-",
      bestContentAngle: angles[0]?.label || "-",
    };
  }

  function identifyTopPosts(records) {
    return [...records].sort((a, b) => b.performanceScore - a.performanceScore).slice(0, 3);
  }

  function identifyUnderperformingPosts(records) {
    return [...records].sort((a, b) => a.performanceScore - b.performanceScore).slice(0, 3);
  }

  function emptyTableRow(columnCount, message) {
    return `<tr><td colspan="${columnCount}">${escapeHtml(message)}</td></tr>`;
  }

  function renderSummary(summary) {
    getElement("analytics-summary-posts").textContent = formatNumber(summary.posts);
    getElement("analytics-summary-impressions").textContent = formatNumber(summary.impressions);
    getElement("analytics-summary-views").textContent = formatNumber(summary.views);
    getElement("analytics-summary-engagements").textContent = formatNumber(summary.engagements);
    getElement("analytics-summary-engagement-rate").textContent = formatPercent(summary.engagementRate);
    getElement("analytics-summary-clicks").textContent = formatNumber(summary.clicks);
    getElement("analytics-summary-leads").textContent = formatNumber(summary.leads);
    getElement("analytics-summary-lead-rate").textContent = formatPercent(summary.leadRate);
    getElement("analytics-summary-best-platform").textContent = formatStatus(summary.bestPlatform);
    getElement("analytics-summary-best-angle").textContent = formatStatus(summary.bestContentAngle);
  }

  function renderPlatformBreakdown(records) {
    const rows = computePlatformBreakdown(records);
    getElement("analytics-platform-breakdown").innerHTML = rows.length
      ? rows.map((row) => `<tr><td>${escapeHtml(formatStatus(row.label))}</td><td>${row.posts}</td><td>${formatNumber(row.impressions)} / ${formatNumber(row.views)}</td><td>${formatNumber(row.engagements)}</td><td>${formatNumber(row.clicks)}</td><td>${formatNumber(row.leads)}</td><td>${formatPercent(row.engagementRate)}</td><td>${formatPercent(row.leadRate)}</td></tr>`).join("")
      : emptyTableRow(8, "No platform metrics in this view.");
  }

  function renderContentBreakdown(targetId, records, key) {
    const rows = computeContentBreakdown(records, key);
    getElement(targetId).innerHTML = rows.length
      ? rows.map((row) => `<tr><td>${escapeHtml(formatStatus(row.label))}</td><td>${row.posts}</td><td>${formatPercent(row.engagementRate)}</td><td>${formatPercent(row.leadRate)}</td><td>${row.performanceScore.toFixed(1)}</td></tr>`).join("")
      : emptyTableRow(5, "No content metrics in this view.");
  }

  function winningMetric(record) {
    if (record.leads > 0) return `${record.leads} lead signal${record.leads === 1 ? "" : "s"}`;
    if (record.saves > 0) return `${record.saves} saves`;
    return `${record.engagements} engagements`;
  }

  function postCardMarkup(record, weak) {
    const reason = weak
      ? "Possible reason: the current snapshot has a lower local performance score. Test a clearer hook or CTA."
      : `Main winning metric: ${winningMetric(record)}.`;
    return `
      <article class="analytics-post-card">
        <div class="card-heading">
          <h3>${escapeHtml(record.hook || record.headline || "Untitled post")}</h3>
          <span class="card-status ${record.source === MOCK_SOURCE ? "mock-mode" : "local-only"}">${escapeHtml(formatStatus(record.source))}</span>
        </div>
        <p>${escapeHtml(record.caption || "No caption preview available.")}</p>
        <div class="analytics-post-meta">
          <span>${escapeHtml(formatStatus(record.platform))}</span>
          <span>${escapeHtml(formatStatus(record.contentGoal))}</span>
          <span>${escapeHtml(formatStatus(record.contentAngle))}</span>
          <span>Score ${record.performanceScore.toFixed(1)}</span>
          <span>${escapeHtml(record.postedAt ? dateOnly(record.postedAt) : record.snapshotDate)}</span>
        </div>
        <p>${escapeHtml(reason)}</p>
        ${weak ? '<p>Suggested action: review the hook, audience fit, and CTA before repeating this approach.</p>' : ""}
        <a class="secondary-button link-button" href="${escapeHtml(record.linkTarget || "#drafts")}">Open original draft</a>
      </article>
    `;
  }

  function renderPostRankings(records) {
    const top = identifyTopPosts(records);
    const weak = identifyUnderperformingPosts(records);
    getElement("analytics-top-posts").innerHTML = top.length
      ? top.map((record) => postCardMarkup(record, false)).join("")
      : '<p class="media-state empty-state">No top posts yet.</p>';
    getElement("analytics-underperforming-posts").innerHTML = weak.length
      ? weak.map((record) => postCardMarkup(record, true)).join("")
      : '<p class="media-state empty-state">No underperforming posts yet.</p>';
  }

  function renderAnalyticsInsights() {
    const insights = loadAnalyticsInsights();
    getElement("analytics-insights").innerHTML = insights.length
      ? insights.map((insight) => `
        <article class="analytics-insight-card">
          <div class="card-heading">
            <h3>${escapeHtml(insight.title)}</h3>
            <span class="card-status ${insight.status === "active" ? "needs-review" : "local-only"}">${escapeHtml(formatStatus(insight.status))}</span>
          </div>
          <p>${escapeHtml(insight.summary)}</p>
          <div class="analytics-insight-meta">
            <span>Confidence: ${escapeHtml(insight.confidence)}</span>
            <span>Evidence: ${escapeHtml(formatEvidence(insight.evidence))}</span>
          </div>
          <p><strong>Recommended action:</strong> ${escapeHtml(insight.recommendedAction)}</p>
          <div class="analytics-insight-actions">
            <button class="secondary-button" type="button" data-analytics-insight-action="applied" data-analytics-insight-id="${escapeHtml(insight.id)}">Apply</button>
            <button class="secondary-button" type="button" data-analytics-insight-action="dismissed" data-analytics-insight-id="${escapeHtml(insight.id)}">Dismiss</button>
            <button class="secondary-button" type="button" data-analytics-insight-action="archived" data-analytics-insight-id="${escapeHtml(insight.id)}">Archive</button>
          </div>
        </article>
      `).join("")
      : '<p class="media-state empty-state">No local insights yet.</p>';
  }

  async function handleAnalyticsInsightAction(event) {
    const button = event.target.closest("[data-analytics-insight-action]");
    if (!button) return;
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/analytics/insights/${encodeURIComponent(button.dataset.analyticsInsightId)}`, {
          method: "PATCH",
          body: { status: button.dataset.analyticsInsightAction },
        });
        await bridge.sync();
        renderAnalyticsInsights();
      } catch (error) {
        console.error("analytics: insight status update failed", error);
      }
      return;
    }
    const insights = loadAnalyticsInsights().map((insight) => (
      insight.id === button.dataset.analyticsInsightId
        ? { ...insight, status: button.dataset.analyticsInsightAction, updatedAt: new Date().toISOString() }
        : insight
    ));
    saveAnalyticsInsights(insights);
    renderAnalyticsInsights();
  }

  function renderLearningReview() {
    const reports = loadWeeklyReports()
      .slice()
      .sort((a, b) => String(b.weekStartDate || "").localeCompare(String(a.weekStartDate || "")));
    getElement("analytics-weekly-reports").innerHTML = reports.length
      ? reports.slice(0, 6).map((report) => `
        <article class="analytics-learning-card">
          <div class="card-heading">
            <h4>${escapeHtml(report.weekStartDate || "-")} to ${escapeHtml(report.weekEndDate || "-")}</h4>
            <span class="card-status ${report.generatedBy === "ai_mock" ? "mock-mode" : "local-only"}">${escapeHtml(formatStatus(report.generatedBy))}</span>
          </div>
          <p>${escapeHtml(report.summary || "No summary available.")}</p>
          <p><strong>Wins:</strong> ${escapeHtml((report.wins || []).join(" "))}</p>
          <p><strong>Concerns:</strong> ${escapeHtml((report.concerns || []).join(" "))}</p>
          <p><strong>Next:</strong> ${escapeHtml((report.recommendations || []).join(" "))}</p>
        </article>
      `).join("")
      : '<p class="media-state empty-state">No weekly reports yet. Generate one from local analytics.</p>';

    const memories = loadAIMemory();
    getElement("analytics-ai-memory").innerHTML = memories.length
      ? memories.map((memory) => `
        <article class="analytics-learning-card">
          <div class="card-heading">
            <h4>${escapeHtml(memory.title || "Local learning")}</h4>
            <span class="card-status ${memory.source === "mock" ? "mock-mode" : "local-only"}">${escapeHtml(formatStatus(memory.status))}</span>
          </div>
          <p>${escapeHtml(memory.summary || memory.content || "")}</p>
          <div class="analytics-insight-meta">
            <span>Type: ${escapeHtml(formatStatus(memory.memoryType))}</span>
            <span>Confidence: ${escapeHtml(memory.confidence || "low")}</span>
            <span>Source: ${escapeHtml(formatStatus(memory.source || "local_learning"))}</span>
          </div>
          ${memory.status === "active" ? `<button class="secondary-button" type="button" data-ai-memory-archive="${escapeHtml(memory.id)}">Archive memory</button>` : ""}
        </article>
      `).join("")
      : '<p class="media-state empty-state">No AI memory yet. Refresh from local evidence after reviewing analytics or drafts.</p>';
  }

  function setLearningMessage(message) {
    const output = getElement("analytics-learning-message");
    output.hidden = !message;
    output.textContent = message;
  }

  function browserWeeklyReport(weekStartDate) {
    const start = new Date(`${weekStartDate}T12:00:00`);
    const end = new Date(start);
    end.setDate(end.getDate() + 6);
    const records = performanceRecords(filteredSnapshots());
    const summary = computeAnalyticsSummary(records);
    return {
      id: `browser-weekly-report-${weekStartDate}`,
      weekStartDate,
      weekEndDate: dateOnly(end),
      summary: `Local browser demo summary: ${summary.posts} post(s), ${summary.engagements} engagement signal(s), ${summary.clicks} click(s), and ${summary.leads} lead signal(s).`,
      wins: summary.posts ? [`Current best platform idea to test: ${formatStatus(summary.bestPlatform)}.`] : ["No clear win yet."],
      concerns: ["Direct-file mode uses local demo data. Run the localhost bridge for durable SQLite reports."],
      recommendations: ["Add manual analytics after real posting to strengthen future comparisons."],
      generatedBy: "ai_mock",
    };
  }

  async function generateWeeklyReport() {
    const weekStartDate = getElement("analytics-learning-week-start").value;
    if (!weekStartDate) {
      setLearningMessage("Choose a week start date first.");
      return;
    }
    try {
      const bridge = activeApiBridge();
      if (bridge) {
        await bridge.request("/api/weekly-reports", {
          method: "POST",
          body: {
            brand_profile_id: currentBrandProfileId(),
            week_start_date: weekStartDate,
          },
        });
        await bridge.sync();
        setLearningMessage("Weekly report generated from local SQLite analytics. Mock inputs remain clearly labeled.");
      } else {
        const report = browserWeeklyReport(weekStartDate);
        const reports = loadWeeklyReports().filter((item) => item.id !== report.id);
        saveWeeklyReports([report, ...reports]);
        setLearningMessage("Weekly report generated in direct-file demo mode. Use the localhost bridge for durable SQLite reports.");
      }
      renderLearningReview();
    } catch (error) {
      setLearningMessage(error.message || "Weekly report could not be generated.");
    }
  }

  async function refreshAIMemory() {
    try {
      const bridge = activeApiBridge();
      if (bridge) {
        const result = await bridge.request("/api/ai-memory/refresh", {
          method: "POST",
          body: { brand_profile_id: currentBrandProfileId() },
        });
        await bridge.sync();
        setLearningMessage(`AI memory refreshed from local evidence: ${result.createdCount} created, ${result.updatedCount} updated.`);
      } else {
        saveAIMemory(loadAIMemory());
        setLearningMessage("Direct-file demo memory is already refreshed. Use the localhost bridge for evidence-backed SQLite memory.");
      }
      renderLearningReview();
    } catch (error) {
      setLearningMessage(error.message || "AI memory could not be refreshed.");
    }
  }

  async function archiveAIMemory(event) {
    const button = event.target.closest("[data-ai-memory-archive]");
    if (!button) return;
    try {
      const bridge = activeApiBridge();
      if (bridge) {
        await bridge.request(`/api/ai-memory/${encodeURIComponent(button.dataset.aiMemoryArchive)}/archive`, {
          method: "POST",
          body: {},
        });
        await bridge.sync();
      } else {
        saveAIMemory(loadAIMemory().map((memory) => (
          memory.id === button.dataset.aiMemoryArchive
            ? { ...memory, status: "archived", updatedAt: new Date().toISOString() }
            : memory
        )));
      }
      setLearningMessage("AI memory archived locally. It was not deleted.");
      renderLearningReview();
    } catch (error) {
      setLearningMessage(error.message || "AI memory could not be archived.");
    }
  }

  function populateManualPostOptions() {
    const select = getElement("analytics-manual-post");
    const posts = loadTrackedPosts();
    const selected = select.value;
    select.innerHTML = posts.map((post) => `<option value="${escapeHtml(post.id)}">${escapeHtml(formatStatus(post.platform))}: ${escapeHtml(post.hook || post.headline || post.id)}</option>`).join("");
    if (posts.some((post) => post.id === selected)) select.value = selected;
    syncManualPlatform();
  }

  function syncManualPlatform() {
    const postId = getElement("analytics-manual-post").value;
    const post = loadTrackedPosts().find((item) => item.id === postId);
    if (post?.platform) getElement("analytics-manual-platform").value = post.platform;
  }

  function setManualMessage(kind, message) {
    const success = getElement("analytics-manual-success");
    const error = getElement("analytics-manual-error");
    success.hidden = kind !== "success";
    error.hidden = kind !== "error";
    success.textContent = kind === "success" ? message : "";
    error.textContent = kind === "error" ? message : "";
  }

  function setMockMessage(message) {
    const output = getElement("analytics-mock-message");
    output.hidden = !message;
    output.textContent = message;
  }

  function mockAnalyticsAllowed() {
    const settings = safeParse(window.localStorage.getItem(SETTINGS_KEY), {});
    return ["development", "demo", "test"].includes(settings.appEnvironment || "development");
  }

  async function handleManualSubmit(event) {
    event.preventDefault();
    const input = {
      generatedPostId: getElement("analytics-manual-post").value,
      platform: getElement("analytics-manual-platform").value,
      snapshotDate: getElement("analytics-manual-date").value,
      notes: getElement("analytics-manual-notes").value.trim(),
    };
    numericFields.forEach((field) => {
      const id = `analytics-manual-${field.replace(/[A-Z]/g, (character) => `-${character.toLowerCase()}`)}`;
      input[field] = getElement(id).value;
    });
    try {
      const bridge = activeApiBridge();
      if (bridge) {
        const metrics = {};
        numericFields.forEach((field) => {
          metrics[field] = toMetric(input[field]);
        });
        await bridge.request("/api/analytics/snapshots", {
          method: "POST",
          body: {
            brand_profile_id: currentBrandProfileId(),
            platform: input.platform,
            snapshot_date: input.snapshotDate,
            generated_post_id: input.generatedPostId.startsWith("analytics-demo-")
              ? null
              : input.generatedPostId,
            notes: input.notes,
            metrics,
          },
        });
        await bridge.sync();
      } else {
        createManualAnalyticsSnapshot(input);
      }
      setManualMessage(
        "success",
        bridge
          ? "Manual analytics snapshot saved to local SQLite."
          : "Manual analytics snapshot saved locally for this browser demo.",
      );
      renderAnalytics();
    } catch (error) {
      setManualMessage("error", error.message || "Manual snapshot could not be saved.");
    }
  }

  function renderAnalytics() {
    const loading = getElement("analytics-loading-state");
    const errorState = getElement("analytics-error-state");
    const empty = getElement("analytics-empty-state");
    if (!loading || !errorState || !empty) return;
    try {
      loading.hidden = true;
      errorState.hidden = true;
      const snapshots = filteredSnapshots();
      const records = performanceRecords(snapshots);
      empty.hidden = records.length > 0;
      renderSummary(computeAnalyticsSummary(records));
      renderPlatformBreakdown(records);
      renderContentBreakdown("analytics-goal-breakdown", records, "contentGoal");
      renderContentBreakdown("analytics-angle-breakdown", records, "contentAngle");
      renderPostRankings(records);
      renderAnalyticsInsights();
      renderLearningReview();
      populateManualPostOptions();
    } catch (error) {
      console.error("analytics: render failed", error);
      loading.hidden = true;
      errorState.hidden = false;
    }
  }

  function setupAnalytics() {
    const view = getElement("analytics-view");
    if (!view) return;
    getElement("analytics-range-filter").addEventListener("change", renderAnalytics);
    getElement("analytics-platform-filter").addEventListener("change", renderAnalytics);
    getElement("analytics-source-filter").addEventListener("change", renderAnalytics);
    getElement("analytics-manual-form").addEventListener("submit", handleManualSubmit);
    getElement("analytics-manual-post").addEventListener("change", syncManualPlatform);
    getElement("analytics-insights").addEventListener("click", handleAnalyticsInsightAction);
    getElement("analytics-generate-weekly-report").addEventListener("click", generateWeeklyReport);
    getElement("analytics-refresh-memory").addEventListener("click", refreshAIMemory);
    getElement("analytics-ai-memory").addEventListener("click", archiveAIMemory);
    const generateMockButton = getElement("analytics-generate-mock");
    generateMockButton.hidden = !mockAnalyticsAllowed();
    generateMockButton.addEventListener("click", async () => {
      try {
        const bridge = activeApiBridge();
        const result = bridge
          ? await bridge.request("/api/analytics/mock", {
            method: "POST",
            body: { brand_profile_id: currentBrandProfileId() },
          })
          : null;
        if (bridge) await bridge.sync();
        const created = bridge ? result.snapshots : generateMockAnalytics();
        setMockMessage(
          created.length
            ? `${created.length} clearly labeled mock snapshots generated locally. No real analytics API was called.`
            : "Mock analytics are already up to date for today. No duplicate snapshots were created.",
        );
        renderAnalytics();
      } catch (error) {
        setMockMessage(error.message || "Mock analytics could not be generated.");
      }
    });
    getElement("analytics-manual-date").value = dateOnly(new Date());
    getElement("analytics-learning-week-start").value = currentWeekStart();
    renderAnalytics();
    window.addEventListener("local-api-ready", renderAnalytics);
    window.addEventListener("hashchange", () => {
      if (window.location.hash === "#analytics") renderAnalytics();
    });
  }

  document.addEventListener("DOMContentLoaded", setupAnalytics);
})();
