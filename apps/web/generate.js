// Generate screen — localhost SQLite generation with a direct-file fallback.
//
// When the localhost bridge is active, preview generation runs through the
// Python content-generation service so Brand Brain, media metadata, active AI
// memory, prompt provenance, and safety review share one source of truth.
// Direct-file mode keeps the deterministic browser mirror as a localStorage
// demo fallback.

(function () {
  const BRAND_KEY = "local-social-ai-manager.brandBrain";
  const MEDIA_KEY = "local-social-ai-manager.mediaLibrary";
  const DRAFTS_KEY = "local-social-ai-manager.drafts";
  const SETTINGS_KEY = "local-social-ai-manager.settings";
  const APPROVAL_LOGS_KEY = "local-social-ai-manager.approvalLogs";
  const SCHEDULED_POSTS_KEY = "local-social-ai-manager.scheduledPosts";
  const PUBLISH_QUEUE_ITEMS_KEY = "local-social-ai-manager.publishQueueItems";
  const APPROVAL_STATUSES = [
    "draft",
    "needs_review",
    "approved",
    "rejected",
    "revision_requested",
    "archived",
  ];
  const CRITICAL_SCHEDULING_FLAGS = new Set([
    "invented_testimonial",
    "fake_testimonial",
    "unsupported_guarantee",
    "approval_bypass_attempt",
    "missing_approval",
    "missing_required_brand_claim_support",
    "unsupported_claim",
    "private_customer_info_risk",
    "brand_mismatch",
    "platform_policy_risk",
  ]);

  function activeApiBridge() {
    return window.localApiBridge?.available ? window.localApiBridge : null;
  }

  const PLATFORMS = [
    { id: "instagram", label: "Instagram" },
    { id: "facebook", label: "Facebook" },
    { id: "threads", label: "Threads" },
    { id: "tiktok", label: "TikTok" },
    { id: "youtube", label: "YouTube Shorts" },
    { id: "linkedin", label: "LinkedIn" },
    { id: "x", label: "X" },
  ];

  const GOAL_CTA = {
    get_leads: "Reply or send a message to ask about availability.",
    show_transformation: "See more recent before-and-after work.",
    educate_customer: "Reply with a question and we'll send a plain-language answer.",
    promote_offer: "Ask about current availability.",
    build_trust: "Learn more about the team.",
    announce_availability: "Ask about open dates.",
    repurpose_old_content: "Revisit recent project notes.",
    behind_the_scenes: "See more process posts.",
    seasonal_reminder: "Plan ahead for the season.",
  };

  const ANGLE_NOTE = {
    before_after: "Shows a clear before and after change without inventing results.",
    educational: "Shares one practical tip the business can support.",
    behind_the_scenes: "Shows real preparation or process without naming any customer.",
    testimonial: "Placeholder reference to a real quote. Do not invent testimonials.",
    promotion: "Mentions an offer only when supported by the brand profile.",
    faq: "Answers one common question in plain language.",
    trust_builder: "Highlights one careful, supportable practice from the brand profile.",
    transformation: "Shows a clear change while staying honest about scope.",
    seasonal: "Connects the message to the current season without urgency hype.",
    other: "A general draft aligned to brand voice.",
  };

  // ------------------------------------------------------------------
  // localStorage helpers.
  // ------------------------------------------------------------------

  function safeParse(raw, fallback) {
    if (!raw) return fallback;
    try {
      const parsed = JSON.parse(raw);
      return parsed == null ? fallback : parsed;
    } catch (error) {
      console.warn("generate: failed to parse JSON from localStorage", error);
      return fallback;
    }
  }

  function loadBrandProfile() {
    return safeParse(window.localStorage.getItem(BRAND_KEY), null);
  }

  function loadMediaAssets() {
    const data = safeParse(window.localStorage.getItem(MEDIA_KEY), []);
    return Array.isArray(data) ? data : [];
  }

  function loadDrafts() {
    const data = safeParse(window.localStorage.getItem(DRAFTS_KEY), []);
    return Array.isArray(data) ? data : [];
  }

  function persistDrafts(drafts) {
    window.localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
  }

  function loadApprovalLogs() {
    const data = safeParse(window.localStorage.getItem(APPROVAL_LOGS_KEY), {});
    return data && typeof data === "object" && !Array.isArray(data) ? data : {};
  }

  function persistApprovalLogs(logs) {
    window.localStorage.setItem(APPROVAL_LOGS_KEY, JSON.stringify(logs));
  }

  function loadScheduledPosts() {
    const data = safeParse(window.localStorage.getItem(SCHEDULED_POSTS_KEY), []);
    return Array.isArray(data) ? data : [];
  }

  function saveScheduledPosts(posts) {
    window.localStorage.setItem(SCHEDULED_POSTS_KEY, JSON.stringify(posts));
  }

  function loadPublishQueueItems() {
    const data = safeParse(window.localStorage.getItem(PUBLISH_QUEUE_ITEMS_KEY), []);
    return Array.isArray(data) ? data : [];
  }

  function savePublishQueueItems(items) {
    window.localStorage.setItem(PUBLISH_QUEUE_ITEMS_KEY, JSON.stringify(items));
  }

  function appendApprovalLog(draftId, action, notes, changedFields) {
    const logs = loadApprovalLogs();
    const entry = {
      id: `approval-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      entityType: "generated_post",
      entityId: draftId,
      action,
      actorLabel: "local_browser_user",
      notes: notes || "",
      changedFields: changedFields || {},
      createdAt: new Date().toISOString(),
    };
    logs[draftId] = Array.isArray(logs[draftId]) ? logs[draftId].concat(entry) : [entry];
    persistApprovalLogs(logs);
    return entry;
  }

  function appendScheduleAuditLog(scheduledPostId, action, notes, changedFields) {
    const logs = loadApprovalLogs();
    const entry = {
      id: `approval-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      entityType: "scheduled_post",
      entityId: scheduledPostId,
      action,
      actorLabel: "local_browser_user",
      notes: notes || "",
      changedFields: changedFields || {},
      createdAt: new Date().toISOString(),
    };
    logs[scheduledPostId] = Array.isArray(logs[scheduledPostId])
      ? logs[scheduledPostId].concat(entry)
      : [entry];
    persistApprovalLogs(logs);
    return entry;
  }

  // ------------------------------------------------------------------
  // Deterministic mock generator (mirrors scripts/ai/providers/mock.py).
  // ------------------------------------------------------------------

  function slug(text) {
    if (typeof text !== "string") return "";
    const parts = text
      .replace(/[^a-zA-Z0-9 ]/g, " ")
      .split(/\s+/)
      .filter(Boolean);
    return parts.map((p) => p[0].toUpperCase() + p.slice(1).toLowerCase()).join("");
  }

  function buildHashtags(brand, angle, count) {
    if (count <= 0) return [];
    const candidates = [];
    const businessTag = slug(brand.businessName || "");
    if (businessTag) candidates.push("#" + businessTag);
    const angleTag = slug((angle || "").replace(/_/g, " "));
    if (angleTag) candidates.push("#" + angleTag);
    candidates.push("#LocalBusiness", "#LocalServiceBusiness");
    (brand.services || []).forEach((service) => {
      const tag = slug(service);
      if (tag) candidates.push("#" + tag);
    });
    const seen = new Set();
    const out = [];
    for (const tag of candidates) {
      if (tag && !seen.has(tag)) {
        seen.add(tag);
        out.push(tag);
      }
      if (out.length >= count) break;
    }
    return out;
  }

  function platformHook(platform, brand, angle) {
    const business = brand.businessName || "the business";
    const angleLabel = (angle || "").replace(/_/g, " ");
    const map = {
      instagram: `${business}: a ${angleLabel} moment for the feed.`,
      facebook: `${business} — a ${angleLabel} update for neighbors.`,
      threads: `Quick note from ${business} on ${angleLabel}.`,
      tiktok: `Hook: ${business} shows a ${angleLabel} clip.`,
      youtube: `${business}: short video idea on ${angleLabel}.`,
      linkedin: `${business} — a ${angleLabel} note for the local industry.`,
      x: `${business}: ${angleLabel}.`,
    };
    return map[platform] || `${business} — ${angleLabel}.`;
  }

  function suggestedPostTime(platform, index) {
    // Deterministic offset by platform so previews look varied.
    const dayOffsets = { instagram: 1, facebook: 2, threads: 1, tiktok: 3, youtube: 4, linkedin: 5, x: 1 };
    const hourMap = { instagram: 16, facebook: 13, threads: 18, tiktok: 19, youtube: 11, linkedin: 9, x: 8 };
    const now = new Date("2026-06-01T12:00:00Z"); // deterministic anchor
    const offsetDays = (dayOffsets[platform] || 1) + Math.floor(index / 7);
    const hour = hourMap[platform] || 12;
    now.setUTCDate(now.getUTCDate() + offsetDays);
    now.setUTCHours(hour, 0, 0, 0);
    return now.toISOString();
  }

  function buildCaption(platform, brand, input) {
    const business = brand.businessName || "the business";
    const services = (brand.services || []).slice(0, 2).join(", ") || "the listed services";
    const audience = input.targetAudience || brand.targetCustomers?.[0] || brand.targetAudience || "local customers";
    const angleNote = ANGLE_NOTE[input.contentAngle] || ANGLE_NOTE.other;
    const supported = (brand.supportedClaims || [])[0];
    const claimLine = supported
      ? `Supported brand claim: ${supported}.`
      : "No additional claims listed in the brand profile.";
    const voice = (brand.brandVoice || brand.voice || "helpful, practical, and honest").trim();
    const cta = input.includeCTA ? GOAL_CTA[input.contentGoal] || "Reply with a question." : null;
    const emoji = input.includeEmojis ? "✨ " : "";
    const parts = [
      `${emoji}${platformHook(platform, brand, input.contentAngle)}`,
      `Audience: ${audience}.`,
      `Focus service(s): ${services}.`,
      angleNote,
      claimLine,
      `Voice: ${voice}.`,
    ];
    if (cta) parts.push(cta);
    if (input.userInstructions) parts.push(`Owner note: ${input.userInstructions}`);
    parts.push("Mock draft. Not a real published post.");
    return parts.join(" ");
  }

  function buildVariants(caption, count) {
    if (count <= 0) return [];
    const styles = ["short", "warm", "direct"];
    const out = [];
    for (let i = 0; i < count; i += 1) {
      const style = styles[i % styles.length];
      out.push({
        style,
        text: `${caption} (${style} variation #${i + 1})`,
      });
    }
    return out;
  }

  function buildPlatformDraft(platform, brand, input, index) {
    const caption = buildCaption(platform, brand, input);
    const hashtags = input.includeHashtags ? buildHashtags(brand, input.contentAngle, 5) : [];
    return {
      platform,
      hook: platformHook(platform, brand, input.contentAngle),
      caption,
      shortCaption: caption.length > 110 ? caption.slice(0, 107).trim() + "..." : caption,
      longCaption: `${caption}\n\nMore detail: ${ANGLE_NOTE[input.contentAngle] || ""}`,
      callToAction: input.includeCTA ? GOAL_CTA[input.contentGoal] || null : null,
      hashtags,
      mediaAssetIds: input.selectedMediaIds.slice(),
      contentAngle: input.contentAngle,
      contentGoal: input.contentGoal,
      targetAudience: input.targetAudience || brand.targetCustomers?.[0] || brand.targetAudience || "local customers",
      suggestedPostTime: suggestedPostTime(platform, index),
      altText: input.selectedMediaIds.length
        ? `Image describing a recent ${input.contentAngle.replace(/_/g, " ")} moment.`
        : null,
      notes: "Generated locally with the mock provider. Mirror of scripts/ai/providers/mock.py.",
      captionVariants: buildVariants(caption, input.numberOfVariants || 0),
      safetyFlags: [],
      score: {
        overall: 72,
        breakdown: { clarity: 78, brand_voice: 70, safety_match: 68 },
        rationale: "Mock baseline score. Replace once the real provider runs.",
      },
      status: "needs_review",
    };
  }

  // ------------------------------------------------------------------
  // Local safety review (mirrors scripts/ai/safety.py).
  // ------------------------------------------------------------------

  const GUARANTEE_PATTERNS = [
    /\bguarantee[sd]?\b/i,
    /\b100\s*%\s*(?:satisfaction|guarantee|results)\b/i,
    /\bwe (?:will|always) (?:deliver|fix|solve)\b/i,
    /\bpromise(?:d)?\b/i,
  ];
  const CREDENTIAL_KEYWORDS = ["licensed", "insured", "certified", "accredited", "bonded", "award-winning", "voted best"];
  const TESTIMONIAL_PHRASES = ["one customer said", "a client told", "as our customer said", "real customer review", "review:", "said,", "told us,", "a happy customer"];
  const AGGRESSIVE_PATTERNS = [/\bact now\b/i, /\bdon'?t (?:miss|wait)\b/i, /\blast chance\b/i, /\bhurry\b/i, /\blimited time only\b/i, /!!!+/];
  const PUBLISHED_CLAIM_PHRASES = ["we posted", "we just shared", "now live on our", "as seen on our page", "we already posted"];
  const APPROVAL_BYPASS_PHRASES = ["auto-approved", "auto approved", "skip review", "no review needed", "approved automatically"];

  function runSafetyChecks(caption, brand, emergencyPauseEnabled) {
    const flags = [];
    const blocking = [];
    const fixes = [];
    const lower = (caption || "").toLowerCase();
    const supportedText = (brand.supportedClaims || []).join(" ").toLowerCase();
    const blocked = brand.bannedWords || brand.blockedPhrases || [];

    function addFlag(value, isBlocking) {
      if (!flags.includes(value)) flags.push(value);
      if (isBlocking && !blocking.includes(value)) blocking.push(value);
    }

    blocked.forEach((phrase) => {
      if (typeof phrase === "string" && phrase && lower.includes(phrase.toLowerCase())) {
        addFlag("brand_mismatch", true);
        fixes.push(`Remove blocked phrase: "${phrase}"`);
      }
    });

    if (GUARANTEE_PATTERNS.some((re) => re.test(lower))) {
      addFlag("unsupported_guarantee", true);
      fixes.push("Remove the guarantee or soften it to what the brand can actually support.");
    }
    if (TESTIMONIAL_PHRASES.some((p) => lower.includes(p))) {
      addFlag("fake_testimonial", true);
      fixes.push("Remove the testimonial unless the owner has explicitly confirmed it.");
    }
    for (const word of CREDENTIAL_KEYWORDS) {
      if (lower.includes(word) && !supportedText.includes(word)) {
        addFlag("unsupported_claim", true);
        fixes.push(`Remove "${word}" or add it to supportedClaims in the brand profile.`);
        break;
      }
    }
    if (AGGRESSIVE_PATTERNS.some((re) => re.test(lower))) {
      addFlag("aggressive_language", false);
      fixes.push("Soften the call-to-action. Avoid pressure language.");
    }
    if (PUBLISHED_CLAIM_PHRASES.some((p) => lower.includes(p))) {
      addFlag("platform_policy_risk", true);
      fixes.push("This is a draft, not a published post. Remove published-claim language.");
    }
    if (APPROVAL_BYPASS_PHRASES.some((p) => lower.includes(p))) {
      addFlag("missing_approval", true);
      fixes.push("Approval bypass attempted. Drafts must go through owner approval.");
    }
    if (emergencyPauseEnabled) {
      addFlag("emergency_pause_conflict", false);
      fixes.push("Emergency pause is enabled. Scheduling and publishing remain blocked downstream.");
    }
    return { flags, blocking, fixes };
  }

  // ------------------------------------------------------------------
  // Bundle orchestration.
  // ------------------------------------------------------------------

  function generateBundle(input, brand, emergencyPauseEnabled) {
    const platforms = input.selectedPlatforms;
    const posts = platforms.map((platform, index) => buildPlatformDraft(platform, brand, input, index));
    const dedupeFlags = new Set();
    const dedupeBlocking = new Set();
    const allFixes = [];
    posts.forEach((post) => {
      const review = runSafetyChecks(post.caption, brand, emergencyPauseEnabled);
      post.safetyFlags = review.flags;
      review.flags.forEach((f) => dedupeFlags.add(f));
      review.blocking.forEach((f) => dedupeBlocking.add(f));
      review.fixes.forEach((fix) => {
        if (!allFixes.includes(fix)) allFixes.push(fix);
      });
    });
    return {
      brandProfileId: brand.id || "brand-local",
      posts,
      promptId: "platform_post_generator_v1",
      promptVersion: "v1",
      generationProvider: "mock",
      promptMetadata: {
        promptId: "platform_post_generator_v1",
        promptVersion: "v1",
        renderFormat: "structured-mock-browser",
        contentGoal: input.contentGoal,
        contentAngle: input.contentAngle,
        selectedPlatforms: platforms.slice(),
        fallbackMode: "Direct-file browser demo. Use the localhost bridge for SQLite-backed generation.",
      },
      providerMetadata: {
        deterministic: true,
        mock: true,
        providerLabel: "Mock provider (browser mirror)",
      },
      safetyReview: {
        flags: Array.from(dedupeFlags).sort(),
        blockingFlags: Array.from(dedupeBlocking).sort(),
        reviewer: "local_rules",
        notes:
          "Local rule-based safety check completed in browser." +
          (emergencyPauseEnabled ? " Emergency pause is enabled — scheduling and publishing remain blocked elsewhere." : ""),
        suggestedFixes: allFixes,
      },
      createdAt: new Date().toISOString(),
      saveRequestId: `browser-save-${brand.id || "brand-local"}-${Date.now()}`,
    };
  }

  // ------------------------------------------------------------------
  // UI helpers.
  // ------------------------------------------------------------------

  function $(id) {
    return document.getElementById(id);
  }

  function setEmergencyPauseFromSettings() {
    const raw = safeParse(window.localStorage.getItem("local-social-ai-manager.settings"), null);
    return Boolean(raw && raw.emergencyPauseEnabled);
  }

  function renderBrandSummary() {
    const brand = loadBrandProfile();
    const empty = $("generate-brand-empty");
    const fields = $("generate-brand-fields");
    if (!brand || !brand.businessName) {
      if (empty) empty.hidden = false;
      if (fields) fields.hidden = true;
      return null;
    }
    if (empty) empty.hidden = true;
    if (fields) fields.hidden = false;
    $("generate-brand-name").textContent = brand.businessName || "—";
    $("generate-brand-industry").textContent = brand.industry || "—";
    $("generate-brand-voice").textContent = brand.brandVoice || brand.voice || "—";
    $("generate-brand-services").textContent = (brand.services || []).join(", ") || "—";
    $("generate-brand-areas").textContent =
      (brand.serviceAreas || brand.locations || []).join(", ") || "—";
    $("generate-brand-ctas").textContent = (brand.commonCTAs || []).join(", ") || "—";
    return brand;
  }

  function renderMediaGrid() {
    const container = $("generate-media-grid");
    const empty = $("generate-media-empty");
    if (!container || !empty) return [];
    container.innerHTML = "";
    const assets = loadMediaAssets();
    if (!assets.length) {
      empty.hidden = false;
      return [];
    }
    empty.hidden = true;
    assets.forEach((asset) => {
      const card = document.createElement("div");
      card.className = "generate-media-card";
      card.dataset.assetId = asset.id;
      card.setAttribute("role", "option");
      card.setAttribute("aria-selected", "false");
      card.tabIndex = 0;
      const tags = (asset.tags || []).slice(0, 4).join(", ");
      const jobContext = asset.jobContext || {};
      const usageStatus = (asset.metadata && asset.metadata.usageStatus) || asset.usageStatus || "new";
      card.innerHTML = `
        <div class="generate-media-checkbox" aria-hidden="true">✓</div>
        <h3>${escapeHtml(asset.fileName || asset.id)}</h3>
        <p class="generate-media-meta">
          <span class="generate-media-type">${escapeHtml(asset.mediaType || "media")}</span>
          ${jobContext.serviceType ? `<span>${escapeHtml(jobContext.serviceType)}</span>` : ""}
          ${jobContext.city || jobContext.state ? `<span>${escapeHtml([jobContext.city, jobContext.state].filter(Boolean).join(", "))}</span>` : ""}
          ${jobContext.contentAngle ? `<span>${escapeHtml(jobContext.contentAngle.replace(/_/g, " "))}</span>` : ""}
          <span class="generate-media-status status-${escapeHtml(usageStatus)}">${escapeHtml(usageStatus)}</span>
        </p>
        ${tags ? `<p class="generate-media-tags">${escapeHtml(tags)}</p>` : ""}
      `;
      card.addEventListener("click", () => toggleMediaCard(card));
      card.addEventListener("keydown", (event) => {
        if (event.key === " " || event.key === "Enter") {
          event.preventDefault();
          toggleMediaCard(card);
        }
      });
      container.appendChild(card);
    });
    return assets;
  }

  function toggleMediaCard(card) {
    const selected = card.classList.toggle("selected");
    card.setAttribute("aria-selected", selected ? "true" : "false");
  }

  function selectedMediaIds() {
    return Array.from(document.querySelectorAll("#generate-media-grid .generate-media-card.selected"))
      .map((node) => node.dataset.assetId)
      .filter(Boolean);
  }

  function renderPlatformChips() {
    const container = $("generate-platforms");
    if (!container) return;
    container.innerHTML = "";
    PLATFORMS.forEach((platform) => {
      const label = document.createElement("label");
      label.className = "chip-toggle";
      label.dataset.platformId = platform.id;
      label.innerHTML = `
        <input type="checkbox" name="platform" value="${escapeHtml(platform.id)}" />
        <span>${escapeHtml(platform.label)}</span>
      `;
      container.appendChild(label);
    });
    // Default selection: instagram + facebook
    const initial = container.querySelectorAll('input[value="instagram"], input[value="facebook"]');
    initial.forEach((input) => {
      input.checked = true;
      input.closest("label").classList.add("selected");
    });
    container.addEventListener("change", (event) => {
      const target = event.target;
      if (target && target.matches('input[name="platform"]')) {
        target.closest("label").classList.toggle("selected", target.checked);
      }
    });
  }

  function selectedPlatforms() {
    return Array.from(document.querySelectorAll('#generate-platforms input[name="platform"]:checked')).map(
      (node) => node.value
    );
  }

  function setError(message) {
    const node = $("generate-error");
    if (!node) return;
    if (!message) {
      node.hidden = true;
      node.textContent = "";
      return;
    }
    node.hidden = false;
    node.textContent = message;
  }

  function setLoading(isLoading) {
    const loading = $("generate-loading");
    const button = $("generate-submit");
    if (loading) loading.hidden = !isLoading;
    if (button) {
      button.disabled = isLoading;
      const spinner = button.querySelector(".button-spinner");
      const label = button.querySelector(".button-label");
      if (spinner) spinner.hidden = !isLoading;
      if (label) label.textContent = isLoading ? "Generating..." : "Generate drafts";
    }
  }

  function escapeHtml(value) {
    if (value == null) return "";
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderResults(bundle) {
    const container = $("generate-results");
    const emptyNote = $("generate-results-empty");
    const clearBtn = $("generate-clear-results");
    const saveBtn = $("generate-save-drafts");
    const reviewLink = $("generate-review-drafts");
    if (reviewLink) reviewLink.hidden = true;
    if (!container || !emptyNote) return;
    container.innerHTML = "";

    if (!bundle || !bundle.posts.length) {
      emptyNote.hidden = false;
      if (clearBtn) clearBtn.hidden = true;
      if (saveBtn) saveBtn.disabled = true;
      return;
    }

    emptyNote.hidden = true;
    if (clearBtn) clearBtn.hidden = false;
    if (saveBtn) saveBtn.disabled = false;

    const review = bundle.safetyReview;
    const reviewBlock = document.createElement("section");
    reviewBlock.className = "result-safety-summary";
    const flagItems = review.flags.length
      ? review.flags.map((f) => `<li class="safety-flag${review.blockingFlags.includes(f) ? " blocking" : ""}">${escapeHtml(f)}${review.blockingFlags.includes(f) ? " (blocking)" : ""}</li>`).join("")
      : '<li class="safety-flag none">No flags raised.</li>';
    reviewBlock.innerHTML = `
      <h3>Bundle safety review</h3>
      <ul class="safety-flag-list">${flagItems}</ul>
      <p class="safety-notes">${escapeHtml(review.notes)}</p>
    `;
    container.appendChild(reviewBlock);

    bundle.posts.forEach((post) => {
      const card = document.createElement("article");
      card.className = "result-card";
      const flagBadges = post.safetyFlags.length
        ? `<ul class="result-flags">${post.safetyFlags.map((f) => `<li class="safety-flag${review.blockingFlags.includes(f) ? " blocking" : ""}">${escapeHtml(f)}</li>`).join("")}</ul>`
        : '<p class="result-flags none">No safety flags on this draft.</p>';
      card.innerHTML = `
        <header class="result-header">
          <span class="result-platform">${escapeHtml(post.platform)}</span>
          <span class="result-status">${escapeHtml(post.status)}</span>
        </header>
        <p class="result-hook"><strong>Hook:</strong> ${escapeHtml(post.hook || "—")}</p>
        <p class="result-caption">${escapeHtml(post.caption)}</p>
        <details class="result-extras">
          <summary>Variants and longer captions</summary>
          <p><strong>Short caption:</strong> ${escapeHtml(post.shortCaption || "—")}</p>
          <p><strong>Long caption:</strong> ${escapeHtml(post.longCaption || "—")}</p>
          <p><strong>CTA:</strong> ${escapeHtml(post.callToAction || "—")}</p>
          <p><strong>Suggested post time:</strong> ${escapeHtml(post.suggestedPostTime || "—")}</p>
          <p><strong>Alt text:</strong> ${escapeHtml(post.altText || "—")}</p>
          ${post.captionVariants.length ? `<ul class="result-variants">${post.captionVariants.map((v) => `<li><em>${escapeHtml(v.style)}:</em> ${escapeHtml(v.text)}</li>`).join("")}</ul>` : ""}
        </details>
        <p class="result-hashtags">${post.hashtags.map((tag) => `<span class="hashtag">${escapeHtml(tag)}</span>`).join(" ")}</p>
        ${flagBadges}
        <p class="result-score"><strong>Score:</strong> ${escapeHtml(String(post.score?.overall ?? "—"))}/100 — ${escapeHtml(post.score?.rationale || "")}</p>
        <p class="result-notes">${escapeHtml(post.notes || "")}</p>
      `;
      container.appendChild(card);
    });
  }

  let selectedDraftId = null;

  function normalizeDraft(draft) {
    return {
      ...draft,
      approvalStatus: draft.approvalStatus || draft.status || "needs_review",
      status: draft.approvalStatus || draft.status || "needs_review",
      hashtags: Array.isArray(draft.hashtags) ? draft.hashtags : [],
      mediaAssetIds: Array.isArray(draft.mediaAssetIds) ? draft.mediaAssetIds : [],
      safetyFlags: Array.isArray(draft.safetyFlags) ? draft.safetyFlags : [],
      promptTemplateId: draft.promptTemplateId || draft.promptId || "platform_post_generator_v1",
      promptVersion: draft.promptVersion || "v1",
      generationProvider: draft.generationProvider || "mock",
      createdAt: draft.createdAt || draft.savedAt || "",
      updatedAt: draft.updatedAt || draft.savedAt || "",
      score: draft.score || {},
    };
  }

  function scoreLabel(score) {
    if (!score || typeof score.overall === "undefined") return "—";
    return `${score.overall}/100`;
  }

  function filteredDrafts() {
    const status = $("drafts-status-filter")?.value || "all";
    const platform = $("drafts-platform-filter")?.value || "all";
    const search = ($("drafts-search")?.value || "").trim().toLowerCase();
    return loadDrafts()
      .map(normalizeDraft)
      .filter((draft) => status === "all" || draft.approvalStatus === status)
      .filter((draft) => platform === "all" || draft.platform === platform)
      .filter((draft) => {
        if (!search) return true;
        return [draft.caption, draft.headline, draft.hook]
          .filter(Boolean)
          .some((value) => String(value).toLowerCase().includes(search));
      });
  }

  function mediaLabel(assetId) {
    const asset = loadMediaAssets().find((item) => item.id === assetId);
    if (!asset) return assetId;
    return asset.title || asset.fileName || asset.file_name || asset.originalFilename || assetId;
  }

  function setDraftMessage(kind, message) {
    const success = $("draft-action-message");
    const error = $("draft-action-error");
    if (!success || !error) return;
    success.hidden = kind !== "success";
    error.hidden = kind !== "error";
    success.textContent = kind === "success" ? message : "";
    error.textContent = kind === "error" ? message : "";
  }

  function clearDraftMessage() {
    const success = $("draft-action-message");
    const error = $("draft-action-error");
    if (success) {
      success.hidden = true;
      success.textContent = "";
    }
    if (error) {
      error.hidden = true;
      error.textContent = "";
    }
  }

  function renderDraftsList() {
    const list = $("drafts-list");
    const empty = $("drafts-empty");
    if (!list || !empty) return;
    list.innerHTML = "";
    const drafts = filteredDrafts();
    if (!drafts.length) {
      empty.hidden = false;
      renderSelectedDraft();
      return;
    }
    empty.hidden = true;
    drafts.forEach((draft) => {
      const card = document.createElement("article");
      card.className = "draft-card";
      card.dataset.draftId = draft.id;
      card.tabIndex = 0;
      card.setAttribute("role", "button");
      card.setAttribute("aria-label", `Open ${draft.platform} draft`);
      if (draft.id === selectedDraftId) card.classList.add("selected");
      card.innerHTML = `
        <header class="draft-card-header">
          <span class="result-platform">${escapeHtml(draft.platform)}</span>
          <span class="result-status">${escapeHtml(draft.approvalStatus)}</span>
        </header>
        <h3>${escapeHtml(draft.hook || draft.headline || "Untitled draft")}</h3>
        <p class="result-caption">${escapeHtml((draft.caption || "").slice(0, 180))}${draft.caption && draft.caption.length > 180 ? "..." : ""}</p>
        <div class="draft-card-metrics">
          <span>Safety flags: ${escapeHtml(String(draft.safetyFlags.length))}</span>
          <span>Score: ${escapeHtml(scoreLabel(draft.score))}</span>
          <span>Media: ${escapeHtml(String(draft.mediaAssetIds.length))}</span>
        </div>
        <p class="result-meta">Created ${escapeHtml(draft.createdAt || "—")} · Updated ${escapeHtml(draft.updatedAt || "—")}</p>
      `;
      card.addEventListener("click", () => selectDraft(draft.id));
      card.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectDraft(draft.id);
        }
      });
      list.appendChild(card);
    });
    if (selectedDraftId && !drafts.some((draft) => draft.id === selectedDraftId)) {
      selectedDraftId = null;
    }
    renderSelectedDraft();
  }

  function selectDraft(draftId) {
    selectedDraftId = draftId;
    clearDraftMessage();
    renderDraftsList();
  }

  function selectedDraft() {
    if (!selectedDraftId) return null;
    return loadDrafts().map(normalizeDraft).find((draft) => draft.id === selectedDraftId) || null;
  }

  function renderSelectedDraft() {
    const draft = selectedDraft();
    const empty = $("drafts-detail-empty");
    const form = $("drafts-form");
    if (!empty || !form) return;
    if (!draft) {
      empty.hidden = false;
      form.hidden = true;
      return;
    }
    empty.hidden = true;
    form.hidden = false;
    $("draft-detail-status").textContent = draft.approvalStatus;
    $("draft-detail-summary").textContent = `${draft.platform} draft for ${draft.contentGoal || "general content"}`;
    $("draft-edit-headline").value = draft.headline || "";
    $("draft-edit-hook").value = draft.hook || "";
    $("draft-edit-caption").value = draft.caption || "";
    $("draft-edit-short-caption").value = draft.shortCaption || "";
    $("draft-edit-long-caption").value = draft.longCaption || "";
    $("draft-edit-cta").value = draft.callToAction || "";
    $("draft-edit-hashtags").value = draft.hashtags.join(", ");
    $("draft-edit-alt-text").value = draft.altText || "";
    $("draft-edit-notes").value = draft.notes || "";
    $("draft-read-platform").textContent = draft.platform || "—";
    $("draft-read-brand").textContent = draft.brandProfileId || "—";
    $("draft-read-goal").textContent = draft.contentGoal || "—";
    $("draft-read-angle").textContent = draft.contentAngle || "—";
    $("draft-read-prompt-id").textContent = draft.promptTemplateId || "—";
    $("draft-read-prompt-version").textContent = draft.promptVersion || "—";
    $("draft-read-provider").textContent = draft.generationProvider || "—";
    $("draft-read-created").textContent = draft.createdAt || "—";
    $("draft-read-score").textContent = scoreLabel(draft.score);
    updateScheduleButton(draft);

    $("draft-safety-flags").innerHTML = draft.safetyFlags.length
      ? `<ul class="safety-flag-list">${draft.safetyFlags.map((flag) => `<li class="safety-flag">${escapeHtml(flag)}</li>`).join("")}</ul>`
      : '<p class="result-flags none">No safety flags recorded.</p>';
    const safetySection = $("draft-safety-section");
    if (safetySection) safetySection.open = draft.safetyFlags.length > 0;
    $("draft-linked-media").innerHTML = draft.mediaAssetIds.length
      ? `<ul class="safety-flag-list">${draft.mediaAssetIds.map((id) => `<li>${escapeHtml(mediaLabel(id))}</li>`).join("")}</ul>`
      : '<p class="result-meta">No linked media assets.</p>';
    $("draft-prompt-metadata").textContent = JSON.stringify(
      {
        promptTemplateId: draft.promptTemplateId,
        promptVersion: draft.promptVersion,
        generationProvider: draft.generationProvider,
        generationTimestamp: draft.generationTimestamp,
        promptMetadata: draft.promptMetadata || {},
        providerMetadata: draft.providerMetadata || {},
      },
      null,
      2
    );
    renderApprovalHistory(draft.id);
    renderSchedulePanelSummary(draft);
  }

  function renderApprovalHistory(draftId) {
    const node = $("draft-approval-history");
    if (!node) return;
    const logs = loadApprovalLogs()[draftId] || [];
    if (!logs.length) {
      node.innerHTML = '<p class="result-meta">No approval history yet.</p>';
      return;
    }
    node.innerHTML = logs
      .slice()
      .reverse()
      .map(
        (log) => `
          <article class="approval-history-item">
            <strong>${escapeHtml(log.action)}</strong>
            <span>${escapeHtml(log.createdAt || "")}</span>
            ${log.notes ? `<p>${escapeHtml(log.notes)}</p>` : ""}
          </article>
        `
      )
      .join("");
  }

  function replaceDraft(updatedDraft) {
    const drafts = loadDrafts().map((draft) =>
      draft.id === updatedDraft.id ? updatedDraft : draft
    );
    persistDrafts(drafts);
    renderDraftsList();
    renderSelectedDraft();
  }

  function parseHashtags(value) {
    return value
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean)
      .map((tag) => (tag.startsWith("#") ? tag : `#${tag}`));
  }

  async function saveDraftEdits(event) {
    event.preventDefault();
    const draft = selectedDraft();
    if (!draft) return;
    const caption = $("draft-edit-caption").value.trim();
    if (!caption) {
      setDraftMessage("error", "Caption is required before saving edits.");
      return;
    }
    const previousStatus = draft.approvalStatus;
    const requiresReapproval = previousStatus === "approved";
    const updatedDraft = {
      ...draft,
      headline: $("draft-edit-headline").value.trim(),
      hook: $("draft-edit-hook").value.trim(),
      caption,
      shortCaption: $("draft-edit-short-caption").value.trim(),
      longCaption: $("draft-edit-long-caption").value.trim(),
      callToAction: $("draft-edit-cta").value.trim(),
      hashtags: parseHashtags($("draft-edit-hashtags").value),
      altText: $("draft-edit-alt-text").value.trim(),
      notes: $("draft-edit-notes").value.trim(),
      approvalStatus: requiresReapproval ? "needs_review" : previousStatus,
      status: requiresReapproval ? "needs_review" : previousStatus,
      updatedAt: new Date().toISOString(),
    };
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/drafts/${encodeURIComponent(draft.id)}`, {
          method: "PATCH",
          body: {
            headline: updatedDraft.headline,
            hook: updatedDraft.hook,
            caption: updatedDraft.caption,
            shortCaption: updatedDraft.shortCaption,
            longCaption: updatedDraft.longCaption,
            callToAction: updatedDraft.callToAction,
            hashtags: updatedDraft.hashtags,
            altText: updatedDraft.altText,
            notes: updatedDraft.notes,
          },
        });
        await bridge.sync();
        renderDraftsList();
        renderSelectedDraft();
      } catch (error) {
        setDraftMessage("error", error.message || "Draft edits could not be saved to local SQLite.");
        return;
      }
    } else {
      appendApprovalLog(
        draft.id,
        requiresReapproval ? "edited_requires_reapproval" : "edited",
        requiresReapproval
          ? "Approved drafts return to needs_review after edits."
          : "Draft edited locally.",
        {
          editedFields: [
            "headline",
            "hook",
            "caption",
            "shortCaption",
            "longCaption",
            "callToAction",
            "hashtags",
            "altText",
            "notes",
          ],
          previousApprovalStatus: previousStatus,
          approvalStatus: updatedDraft.approvalStatus,
        }
      );
      replaceDraft(updatedDraft);
    }
    setDraftMessage(
      "success",
      requiresReapproval
        ? "Edits saved. This approved draft now needs review again."
        : "Draft edits saved locally."
    );
  }

  async function setSelectedDraftStatus(status, action, notes) {
    const draft = selectedDraft();
    if (!draft || !APPROVAL_STATUSES.includes(status)) return;
    const updatedDraft = {
      ...draft,
      approvalStatus: status,
      status,
      updatedAt: new Date().toISOString(),
    };
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        const bridgeActions = {
          approved: "approve",
          rejected: "reject",
          revision_requested: "request_revision",
          archived: "archive",
        };
        await bridge.request(`/api/drafts/${encodeURIComponent(draft.id)}/approval`, {
          method: "POST",
          body: {
            action: bridgeActions[action] || action,
            reason: notes || "",
          },
        });
        await bridge.sync();
        renderDraftsList();
        renderSelectedDraft();
      } catch (error) {
        setDraftMessage("error", error.message || "Draft approval action could not be saved to local SQLite.");
        return;
      }
    } else {
      appendApprovalLog(draft.id, action, notes || "", {
        previousApprovalStatus: draft.approvalStatus,
        approvalStatus: status,
        reason: notes || "",
      });
      replaceDraft(updatedDraft);
    }
    setDraftMessage("success", `Draft marked ${status}. No publishing or scheduling was performed.`);
  }

  function approveSelectedDraft() {
    setSelectedDraftStatus("approved", "approved", "");
  }

  function rejectSelectedDraft() {
    setSelectedDraftStatus("rejected", "rejected", $("draft-action-reason").value.trim());
  }

  function requestRevisionForSelectedDraft() {
    setSelectedDraftStatus(
      "revision_requested",
      "revision_requested",
      $("draft-action-reason").value.trim()
    );
  }

  function archiveSelectedDraft() {
    setSelectedDraftStatus("archived", "archived", $("draft-action-reason").value.trim());
  }

  function schedulingSettings() {
    return safeParse(window.localStorage.getItem(SETTINGS_KEY), {
      appEnvironment: "development",
      defaultTimezone: "America/New_York",
      emergencyPauseEnabled: false,
    });
  }

  function criticalSchedulingFlags(draft) {
    return (draft.safetyFlags || []).filter((flag) => CRITICAL_SCHEDULING_FLAGS.has(flag));
  }

  function checkDraftSchedulingEligibility(draft) {
    if (!draft) {
      return { eligible: false, message: "Select a draft before scheduling." };
    }
    if (draft.approvalStatus === "rejected") {
      return { eligible: false, message: "Rejected drafts cannot be scheduled." };
    }
    if (draft.approvalStatus === "revision_requested") {
      return { eligible: false, message: "This draft needs revision before scheduling." };
    }
    if (draft.approvalStatus !== "approved") {
      return { eligible: false, message: "This draft needs approval before scheduling." };
    }
    if (criticalSchedulingFlags(draft).length) {
      return { eligible: false, message: "Resolve critical safety flags before scheduling." };
    }
    if (schedulingSettings().emergencyPauseEnabled) {
      return {
        eligible: false,
        message: "Scheduling is paused because emergency pause is enabled.",
      };
    }
    if (!draft.caption || !draft.caption.trim()) {
      return { eligible: false, message: "Caption is required before scheduling." };
    }
    return { eligible: true, message: "Ready to schedule." };
  }

  function updateScheduleButton(draft) {
    const button = $("draft-schedule");
    if (!button) return;
    button.hidden = draft.approvalStatus !== "approved";
    button.disabled = draft.approvalStatus !== "approved";
  }

  function renderSchedulePanelSummary(draft) {
    const panel = $("draft-schedule-panel");
    if (!panel || panel.hidden || !draft) return;
    const flags = criticalSchedulingFlags(draft);
    $("draft-schedule-platform").textContent = draft.platform || "—";
    $("draft-schedule-media-count").textContent = String(draft.mediaAssetIds.length);
    $("draft-schedule-approval-status").textContent = draft.approvalStatus || "—";
    $("draft-schedule-safety-status").textContent = flags.length
      ? `Blocked: ${flags.join(", ")}`
      : "No critical flags";
    $("draft-schedule-caption-preview").textContent =
      draft.caption && draft.caption.length > 220
        ? `${draft.caption.slice(0, 217).trim()}...`
        : draft.caption || "Caption preview unavailable.";
    const timezone = $("draft-schedule-timezone");
    if (timezone && !timezone.value.trim()) {
      timezone.value = schedulingSettings().defaultTimezone || "America/New_York";
    }
  }

  function openSchedulePanel() {
    const draft = selectedDraft();
    const result = checkDraftSchedulingEligibility(draft);
    const panel = $("draft-schedule-panel");
    const calendarLink = $("draft-schedule-calendar-link");
    if (!result.eligible) {
      setDraftMessage("error", result.message);
      if (panel) panel.hidden = true;
      return;
    }
    if (!panel) return;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(10, 0, 0, 0);
    $("draft-schedule-date").value = tomorrow.toISOString().slice(0, 10);
    $("draft-schedule-time").value = "10:00";
    $("draft-schedule-timezone").value = schedulingSettings().defaultTimezone || "America/New_York";
    $("draft-schedule-notes").value = "";
    if (calendarLink) calendarLink.hidden = true;
    panel.hidden = false;
    renderSchedulePanelSummary(draft);
    setDraftMessage("success", "Choose a future date and time. Scheduling remains local-only.");
  }

  function closeSchedulePanel() {
    const panel = $("draft-schedule-panel");
    if (panel) panel.hidden = true;
  }

  function scheduledIsoFromForm() {
    const dateValue = $("draft-schedule-date").value;
    const timeValue = $("draft-schedule-time").value;
    if (!dateValue || !timeValue) {
      throw new Error("Date/time is required.");
    }
    const parsed = new Date(`${dateValue}T${timeValue}`);
    if (Number.isNaN(parsed.getTime())) {
      throw new Error("Choose a valid date and time before scheduling.");
    }
    return parsed.toISOString();
  }

  function existingActiveSchedule(draftId, scheduledFor) {
    return loadScheduledPosts().find(
      (post) =>
        post.generatedPostId === draftId &&
        post.scheduledFor === scheduledFor &&
        post.status !== "canceled",
    );
  }

  function createScheduledPostFromDraft(draft, scheduledFor, timezone, notes) {
    const now = new Date().toISOString();
    return {
      id: `scheduled-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      generatedPostId: draft.id,
      brandProfileId: draft.brandProfileId,
      brandName: loadBrandProfile()?.businessName || draft.brandProfileId,
      platform: draft.platform,
      scheduledFor,
      timezone,
      status: "scheduled",
      captionSnapshot: draft.caption,
      mediaAssetIds: draft.mediaAssetIds.slice(),
      platformAccountId: "",
      publishQueueItemId: "",
      recurrenceRule: "",
      isRecurringTemplate: false,
      userNotes: notes || "",
      scheduleMetadata: {
        hashtags: draft.hashtags.slice(),
        callToAction: draft.callToAction || "",
        headline: draft.headline || "",
        hook: draft.hook || "",
        altText: draft.altText || "",
        safetyFlags: draft.safetyFlags.slice(),
        approvalStatusAtScheduling: draft.approvalStatus,
      },
      preflightSnapshot: {
        eligible: true,
        errors: [],
        warnings: ["manual_export_required"],
        source: "Local browser scheduling adapter",
        realPublishing: false,
      },
      createdAt: now,
      updatedAt: now,
      canceledAt: "",
    };
  }

  function createPublishQueueItemFromDraft(draft, scheduledPost, timezone) {
    const now = new Date().toISOString();
    return {
      id: `queue-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      scheduledPostId: scheduledPost.id,
      generatedPostId: draft.id,
      brandProfileId: draft.brandProfileId,
      platform: draft.platform,
      queueStatus: "waiting",
      dueAt: scheduledPost.scheduledFor,
      timezone,
      priority: 100,
      preflightStatus: "not_checked",
      preflightErrors: [],
      preflightWarnings: ["manual_export_required"],
      mockPublishEnabled: false,
      manualExportRequired: true,
      lastCheckedAt: "",
      createdAt: now,
      updatedAt: now,
    };
  }

  let scheduleInProgress = false;

  async function confirmDraftSchedule(event) {
    event.preventDefault();
    if (scheduleInProgress) return;
    const draft = selectedDraft();
    const eligibility = checkDraftSchedulingEligibility(draft);
    if (!eligibility.eligible) {
      setDraftMessage("error", eligibility.message);
      return;
    }
    const timezone = $("draft-schedule-timezone").value.trim() || schedulingSettings().defaultTimezone || "America/New_York";
    if (!timezone) {
      setDraftMessage("error", "Timezone is required.");
      return;
    }

    let scheduledFor;
    try {
      scheduledFor = scheduledIsoFromForm();
    } catch (error) {
      setDraftMessage("error", error.message || "Choose a valid date and time before scheduling.");
      return;
    }

    const settings = schedulingSettings();
    if (new Date(scheduledFor) <= new Date()) {
      const canCreatePastTestItem =
        settings.appEnvironment === "development" &&
        window.confirm("This scheduled time is in the past. Create a development test item anyway?");
      if (!canCreatePastTestItem) {
        setDraftMessage("error", "Date/time must be in the future.");
        return;
      }
    }

    if (existingActiveSchedule(draft.id, scheduledFor)) {
      setDraftMessage("error", "This draft is already scheduled for that date and time.");
      return;
    }

    scheduleInProgress = true;
    const confirmButton = $("draft-schedule-confirm");
    if (confirmButton) confirmButton.disabled = true;
    try {
      const notes = $("draft-schedule-notes").value.trim();
      const bridge = activeApiBridge();
      if (bridge) {
        await bridge.request(`/api/drafts/${encodeURIComponent(draft.id)}/schedule`, {
          method: "POST",
          body: {
            scheduled_for: scheduledFor,
            timezone,
            user_notes: notes,
            allow_past_test_item: new Date(scheduledFor) <= new Date(),
          },
        });
        await bridge.sync();
      } else {
        const scheduledPost = createScheduledPostFromDraft(draft, scheduledFor, timezone, notes);
        const queueItem = createPublishQueueItemFromDraft(draft, scheduledPost, timezone);
        scheduledPost.publishQueueItemId = queueItem.id;
        saveScheduledPosts(loadScheduledPosts().concat(scheduledPost));
        savePublishQueueItems(loadPublishQueueItems().concat(queueItem));
        appendScheduleAuditLog(
          scheduledPost.id,
          "scheduled",
          "Draft scheduled locally from Drafts. No publishing was performed.",
          {
            generatedPostId: draft.id,
            publishQueueItemId: queueItem.id,
            scheduledFor,
            timezone,
            status: "scheduled",
            queueStatus: "waiting",
          },
        );
      }
      const calendarLink = $("draft-schedule-calendar-link");
      if (calendarLink) calendarLink.hidden = false;
      setDraftMessage("success", "Draft scheduled locally. No publishing was performed. View it in Calendar.");
      window.dispatchEvent(new StorageEvent("storage", { key: SCHEDULED_POSTS_KEY }));
    } catch (error) {
      setDraftMessage("error", error.message || "Draft could not be scheduled in local SQLite.");
    } finally {
      scheduleInProgress = false;
      if (confirmButton) confirmButton.disabled = false;
    }
  }

  // ------------------------------------------------------------------
  // Form wiring.
  // ------------------------------------------------------------------

  let lastBundle = null;

  function collectInput() {
    return {
      contentGoal: $("generate-goal").value,
      contentAngle: $("generate-angle").value,
      selectedPlatforms: selectedPlatforms(),
      selectedMediaIds: selectedMediaIds(),
      campaignName: $("generate-campaign").value.trim() || null,
      offerContext: $("generate-offer").value.trim() || null,
      userInstructions: $("generate-instructions").value.trim() || null,
      targetAudience: null,
      numberOfVariants: Number($("generate-variants").value) || 0,
      tone: $("generate-tone").value.trim() || null,
      creativityLevel: $("generate-creativity").value,
      includeHashtags: $("generate-include-hashtags").checked,
      includeEmojis: $("generate-include-emojis").checked,
      includeCTA: $("generate-include-cta").checked,
      requireSafetyReview: $("generate-require-safety").checked,
    };
  }

  function setSaveStatus(kind, message) {
    const node = $("generate-save-status");
    if (!node) return;
    node.hidden = false;
    node.dataset.kind = kind;
    node.textContent = message;
  }

  function clearSaveStatus() {
    const node = $("generate-save-status");
    if (!node) return;
    node.hidden = true;
    node.textContent = "";
    node.removeAttribute("data-kind");
  }

  async function handleGenerate(event) {
    event.preventDefault();
    clearSaveStatus();
    setError("");

    const brand = renderBrandSummary();
    if (!brand) {
      setError("Add a brand profile in Brand Brain before generating drafts.");
      return;
    }

    const input = collectInput();
    if (!input.selectedPlatforms.length) {
      setError("Pick at least one target platform.");
      return;
    }
    if (input.numberOfVariants < 0 || input.numberOfVariants > 4) {
      setError("Number of variants must be between 0 and 4.");
      return;
    }

    setLoading(true);
    try {
      // Give the loading UI a chance to paint before local generation begins.
      await new Promise((resolve) => window.setTimeout(resolve, 16));
      const bridge = activeApiBridge();
      if (bridge) {
        const bundle = await bridge.request("/api/content-generation", {
          method: "POST",
          body: {
            input: {
              ...input,
              brandProfileId: brand.id,
            },
          },
        });
        lastBundle = bundle;
        renderResults(bundle);
      } else {
        const pause = setEmergencyPauseFromSettings();
        const bundle = generateBundle(input, brand, pause);
        lastBundle = bundle;
        renderResults(bundle);
      }
    } catch (error) {
      console.error("generate: bundle failed", error);
      setError(error.message || "Could not generate drafts. Check the console for details.");
      lastBundle = null;
      renderResults(null);
    } finally {
      setLoading(false);
    }
  }

  let draftSaveInProgress = false;

  async function handleSaveToDrafts() {
    if (!lastBundle || !lastBundle.posts.length) {
      setSaveStatus("error", "Nothing to save. Generate drafts first.");
      return;
    }
    if (draftSaveInProgress) {
      setSaveStatus("error", "Draft save is already in progress.");
      return;
    }
    const existing = loadDrafts();
    const saveRequestId =
      lastBundle.saveRequestId ||
      `browser-save-${lastBundle.brandProfileId}-${lastBundle.createdAt || "unknown"}`;
    if (existing.some((draft) => draft.saveRequestId === saveRequestId)) {
      setSaveStatus("error", "These generated drafts were already saved. Generate a new preview before saving again.");
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      const saveButton = $("generate-save-drafts");
      draftSaveInProgress = true;
      if (saveButton) saveButton.disabled = true;
      try {
        const additions = await bridge.request("/api/drafts/save-generated", {
          method: "POST",
          body: {
            bundle: lastBundle,
            save_request_id: saveRequestId,
          },
        });
        await bridge.sync();
        setSaveStatus(
          "success",
          `Saved ${additions.length} draft${additions.length === 1 ? "" : "s"} to local SQLite. Review them in Drafts.`,
        );
        const reviewLink = $("generate-review-drafts");
        if (reviewLink) reviewLink.hidden = false;
        renderDraftsList();
      } catch (error) {
        setSaveStatus("error", error.message || "Generated drafts could not be saved to local SQLite.");
      } finally {
        draftSaveInProgress = false;
        if (saveButton) saveButton.disabled = false;
      }
      return;
    }
    const savedAt = new Date().toISOString();
    const additions = lastBundle.posts.map((post, index) => ({
      id: `draft-${Date.now()}-${index}`,
      saveRequestId,
      savedAt,
      createdAt: savedAt,
      updatedAt: savedAt,
      brandProfileId: lastBundle.brandProfileId,
      platform: post.platform,
      headline: post.headline,
      caption: post.caption,
      shortCaption: post.shortCaption,
      longCaption: post.longCaption,
      hook: post.hook,
      callToAction: post.callToAction,
      hashtags: post.hashtags,
      mediaAssetIds: post.mediaAssetIds,
      contentGoal: post.contentGoal,
      contentAngle: post.contentAngle,
      targetAudience: post.targetAudience,
      suggestedPostTime: post.suggestedPostTime,
      altText: post.altText,
      notes: post.notes,
      safetyFlags: post.safetyFlags,
      blockingFlags: lastBundle.safetyReview.blockingFlags.filter((f) => post.safetyFlags.includes(f)),
      score: post.score,
      approvalStatus: "needs_review",
      status: "needs_review",
      promptTemplateId: lastBundle.promptId,
      promptId: lastBundle.promptId,
      promptVersion: lastBundle.promptVersion,
      promptMetadata: lastBundle.promptMetadata,
      providerMetadata: lastBundle.providerMetadata,
      safetyReview: lastBundle.safetyReview,
      generationProvider: lastBundle.generationProvider,
      generationTimestamp: lastBundle.createdAt,
    }));
    const next = existing.concat(additions);
    persistDrafts(next);
    additions.forEach((draft) => {
      appendApprovalLog(
        draft.id,
        "generated_saved_to_drafts",
        "Generated draft saved locally for human review. No publishing or scheduling was performed.",
        {
          approvalStatus: "needs_review",
          generationProvider: draft.generationProvider,
          platform: draft.platform,
          promptTemplateId: draft.promptTemplateId,
          promptVersion: draft.promptVersion,
          saveRequestId: draft.saveRequestId,
        }
      );
    });
    setSaveStatus(
      "success",
      `Saved ${additions.length} draft${additions.length === 1 ? "" : "s"} locally. Review them in Drafts.`
    );
    const reviewLink = $("generate-review-drafts");
    if (reviewLink) reviewLink.hidden = false;
    renderDraftsList();
  }

  function handleClearResults() {
    lastBundle = null;
    renderResults(null);
    clearSaveStatus();
  }

  function handleReset() {
    const form = $("generate-form");
    if (form) form.reset();
    document
      .querySelectorAll('#generate-platforms .chip-toggle.selected')
      .forEach((label) => label.classList.remove("selected"));
    document
      .querySelectorAll("#generate-media-grid .generate-media-card.selected")
      .forEach((card) => {
        card.classList.remove("selected");
        card.setAttribute("aria-selected", "false");
      });
    renderPlatformChips();
    handleClearResults();
    setError("");
  }

  function init() {
    if (!$("generate-form")) return;
    renderBrandSummary();
    renderMediaGrid();
    renderPlatformChips();
    renderDraftsList();
    $("generate-form").addEventListener("submit", handleGenerate);
    $("generate-save-drafts").addEventListener("click", handleSaveToDrafts);
    $("generate-clear-results").addEventListener("click", handleClearResults);
    $("generate-reset").addEventListener("click", handleReset);
    $("drafts-status-filter").addEventListener("change", renderDraftsList);
    $("drafts-platform-filter").addEventListener("change", renderDraftsList);
    $("drafts-search").addEventListener("input", renderDraftsList);
    $("drafts-form").addEventListener("submit", saveDraftEdits);
    $("draft-approve").addEventListener("click", approveSelectedDraft);
    $("draft-reject").addEventListener("click", rejectSelectedDraft);
    $("draft-request-revision").addEventListener("click", requestRevisionForSelectedDraft);
    $("draft-archive").addEventListener("click", archiveSelectedDraft);
    $("draft-schedule").addEventListener("click", openSchedulePanel);
    $("draft-schedule-confirm").addEventListener("click", confirmDraftSchedule);
    $("draft-schedule-cancel").addEventListener("click", closeSchedulePanel);
    window.addEventListener("storage", (event) => {
      if (event.key === BRAND_KEY) renderBrandSummary();
      if (event.key === MEDIA_KEY) renderMediaGrid();
      if (event.key === DRAFTS_KEY) renderDraftsList();
      if (event.key === APPROVAL_LOGS_KEY) renderSelectedDraft();
      if (event.key === SETTINGS_KEY) renderSelectedDraft();
    });
    window.addEventListener("hashchange", () => {
      if (window.location.hash === "#drafts") renderDraftsList();
      if (window.location.hash === "#generate") {
        renderBrandSummary();
        renderMediaGrid();
      }
    });
    window.addEventListener("local-api-ready", () => {
      renderBrandSummary();
      renderMediaGrid();
      renderDraftsList();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
