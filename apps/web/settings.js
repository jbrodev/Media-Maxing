(function () {
  const STORAGE_KEY = "local-social-ai-manager.settings";
  const ONBOARDING_STORAGE_KEY = "local-social-ai-manager.onboarding";
  const SETUP_CHECKLIST_KEY = "local-social-ai-manager.setupChecklist";
  const SAFETY_CENTER_STORAGE_KEY = "local-social-ai-manager.safetyCenter";
  const BACKUP_STORAGE_KEY = "local-social-ai-manager.backupHistory";
  const DIAGNOSTICS_STORAGE_KEY = "local-social-ai-manager.diagnostics";
  const RECENT_ERRORS_STORAGE_KEY = "local-social-ai-manager.recentErrors";
  const BRAND_STORAGE_KEY = "local-social-ai-manager.brandBrain";
  const MEDIA_STORAGE_KEY = "local-social-ai-manager.mediaLibrary";
  const SCHEDULED_POSTS_KEY = "local-social-ai-manager.scheduledPosts";
  const PUBLISH_QUEUE_ITEMS_KEY = "local-social-ai-manager.publishQueueItems";
  const PUBLISH_ATTEMPTS_KEY = "local-social-ai-manager.publishAttempts";
  const APPROVAL_LOGS_KEY = "local-social-ai-manager.approvalLogs";
  const CONNECTED_ACCOUNTS_KEY = "local-social-ai-manager.connectedAccounts";
  const CONNECTOR_AUDIT_KEY = "local-social-ai-manager.connectorAudit";
  const mediaStatuses = ["new", "reviewed", "ready_for_generation", "used_in_draft", "published", "archived"];
  const contentAngles = [
    "before_after",
    "educational",
    "behind_the_scenes",
    "testimonial",
    "promotion",
    "faq",
    "trust_builder",
    "transformation",
    "seasonal",
    "other",
  ];
  const platformIds = ["facebook", "instagram", "threads", "youtube", "tiktok", "linkedin", "x"];
  const automationLevels = [
    "manual_assist",
    "approval_queue",
    "semi_auto_scheduling",
    "safe_auto_posting",
    "autonomous_content_engine",
  ];
  const providerIds = ["mock", "local", "openai", "anthropic"];
  const scheduledPostStatuses = [
    "scheduled",
    "queued",
    "missed",
    "canceled",
    "completed",
    "failed",
    "needs_attention",
  ];
  const mutableQueueStatuses = ["waiting", "blocked"];
  const processedQueueStatuses = ["processing", "mock_published", "manually_exported"];
  const queueStatuses = [
    "waiting",
    "ready",
    "blocked",
    "processing",
    "mock_published",
    "manually_exported",
    "failed",
    "canceled",
    "skipped",
  ];
  const preflightStatuses = ["not_checked", "passed", "warnings", "errors", "blocked"];
  const criticalQueueFlags = new Set([
    "invented_testimonial",
    "fake_testimonial",
    "unsupported_guarantee",
    "approval_bypass_attempt",
    "missing_approval",
    "emergency_pause_enabled",
    "missing_required_brand_claim_support",
    "unsupported_claim",
    "private_customer_info_risk",
    "brand_mismatch",
    "platform_policy_risk",
  ]);
  const mediaRequiredPlatforms = new Set(["instagram", "youtube", "tiktok"]);
  const supportedRoutes = ["home", "guide", "media", "generate", "drafts", "calendar", "queue", "connected", "setup", "safety", "backup", "diagnostics", "engagement", "analytics", "brand", "settings", "onboarding"];
  const onboardingStepIds = [
    "welcome",
    "local_data",
    "brand_profile",
    "business_details",
    "services_areas",
    "platforms",
    "safety",
    "media",
    "demo_draft",
    "next_steps",
  ];
  const setupChecklistLabels = {
    brand_profile_created: "Brand profile created",
    local_data_ready: "Local data directory ready",
    safety_settings_confirmed: "Safety settings confirmed",
    media_added: "Media added",
    first_draft_generated: "First draft generated",
    first_draft_approved: "First draft approved",
    first_post_scheduled: "First post scheduled",
    manual_export_tested: "Manual export tested",
    analytics_added: "Analytics demo or manual metrics added",
    social_setup_reviewed: "Social accounts mock connected or setup reviewed",
  };
  const setupChecklistIds = Object.keys(setupChecklistLabels);
  let onboardingDemoDraftRequested = false;
  const setupState = {
    selectedPlatformId: "facebook",
  };
  const safetyKillActions = {
    pause_all_automation: {
      label: "Pause all automation",
      confirmationPhrase: "PAUSE ALL",
      description: "Enable emergency pause, lock automation, and disable queue processing.",
    },
    cancel_future_scheduled_posts: {
      label: "Cancel all future scheduled posts",
      confirmationPhrase: "CANCEL FUTURE POSTS",
      description: "Cancel unprocessed scheduled posts and queue items locally.",
    },
    disable_queue_processing: {
      label: "Disable all queue processing",
      confirmationPhrase: "DISABLE QUEUE",
      description: "Keep queue items visible but stop local readiness processing.",
    },
    disconnect_accounts_locally: {
      label: "Disconnect accounts locally",
      confirmationPhrase: "DISCONNECT ACCOUNTS",
      description: "Mark mock/connected account metadata disconnected locally.",
    },
    revoke_tokens_locally: {
      label: "Mark tokens revoked locally",
      confirmationPhrase: "REVOKE TOKENS",
      description: "Mark token metadata revoked without calling providers.",
    },
    disable_ai_generation: {
      label: "Disable AI generation temporarily",
      confirmationPhrase: "DISABLE AI",
      description: "Set a local flag for UI/service checks.",
    },
    export_safety_report: {
      label: "Export safety report",
      confirmationPhrase: "EXPORT SAFETY REPORT",
      description: "Write a redacted local safety report.",
    },
    full_local_reset_placeholder: {
      label: "Full local reset placeholder",
      confirmationPhrase: "RESET PLACEHOLDER",
      description: "No data is deleted. Destructive reset is not implemented.",
    },
  };
  const mockConnectPlatformIds = ["facebook", "instagram", "youtube", "tiktok", "linkedin", "x"];
  const connectedPlatformConfigs = [
    {
      id: "facebook",
      label: "Facebook",
      badge: "FB",
      setupStatus: "mock_ready",
      accountType: "page",
      capabilities: ["Connect", "Read profile later", "Manual export fallback"],
      requiredScopes: ["pages_show_list", "pages_read_engagement"],
      missingScopes: ["real_oauth_not_configured"],
      setupInstructions: [
        "Use mock connect for local UI testing.",
        "Future real Meta OAuth must run server-side and pass app review where required.",
        "Publishing disabled in this build.",
      ],
      requiredEnvVars: ["META_CLIENT_ID", "META_CLIENT_SECRET", "META_REDIRECT_URI"],
      optionalEnvVars: ["META_GRAPH_API_VERSION", "META_ENABLE_REAL_OAUTH", "META_ENABLE_REAL_PUBLISHING"],
      redirectEnvVar: "META_REDIRECT_URI",
      docsLinks: ["Official Meta developer docs link placeholder", "Verify official docs before real OAuth."],
    },
    {
      id: "instagram",
      label: "Instagram",
      badge: "IG",
      setupStatus: "mock_ready",
      accountType: "business",
      capabilities: ["Connect", "Read profile later", "Manual export fallback"],
      requiredScopes: ["instagram_basic", "pages_show_list"],
      missingScopes: ["real_oauth_not_configured"],
      setupInstructions: [
        "Use mock connect for local UI testing.",
        "Future real setup requires an Instagram Business or Creator account connected to Meta.",
        "Publishing disabled in this build.",
      ],
      requiredEnvVars: ["META_CLIENT_ID", "META_CLIENT_SECRET", "META_REDIRECT_URI"],
      optionalEnvVars: ["META_GRAPH_API_VERSION", "META_ENABLE_REAL_OAUTH", "META_ENABLE_REAL_PUBLISHING"],
      redirectEnvVar: "META_REDIRECT_URI",
      docsLinks: ["Official Instagram developer docs link placeholder", "Verify official docs before real OAuth."],
    },
    {
      id: "threads",
      label: "Threads",
      badge: "TH",
      setupStatus: "scaffolded",
      accountType: "business",
      capabilities: ["Connect later", "Manual export fallback"],
      requiredScopes: ["threads_basic"],
      missingScopes: ["connector_scaffold_only"],
      setupInstructions: [
        "Threads is scaffolded for future Meta work.",
        "Use manual export until real OAuth is explicitly implemented.",
        "Publishing disabled in this build.",
      ],
      requiredEnvVars: ["META_CLIENT_ID", "META_CLIENT_SECRET", "META_REDIRECT_URI"],
      optionalEnvVars: ["META_GRAPH_API_VERSION", "META_ENABLE_REAL_OAUTH", "META_ENABLE_REAL_PUBLISHING"],
      redirectEnvVar: "META_REDIRECT_URI",
      docsLinks: ["Official Threads developer docs link placeholder", "Verify official docs before real OAuth."],
    },
    {
      id: "youtube",
      label: "YouTube",
      badge: "YT",
      setupStatus: "mock_ready",
      accountType: "channel",
      capabilities: ["Connect mock", "Read channel profile later", "Manual export fallback"],
      requiredScopes: [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.upload",
      ],
      missingScopes: ["real_oauth_not_configured"],
      setupInstructions: [
        "Use mock connect for local YouTube UI testing.",
        "Future real setup requires a Google Cloud project and OAuth consent screen.",
        "Enable the YouTube Data API later after verifying current scope, quota, and app verification requirements.",
        "Video upload and Shorts publishing are disabled in this build.",
        "Publishing disabled in this build.",
      ],
      requiredEnvVars: ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REDIRECT_URI"],
      optionalEnvVars: ["GOOGLE_ENABLE_REAL_OAUTH", "GOOGLE_ENABLE_REAL_PUBLISHING"],
      redirectEnvVar: "GOOGLE_REDIRECT_URI",
      docsLinks: ["Official Google/YouTube developer docs link placeholder", "Verify official docs before real OAuth."],
    },
    {
      id: "tiktok",
      label: "TikTok",
      badge: "TT",
      setupStatus: "mock_ready",
      accountType: "business",
      capabilities: ["Connect mock", "Read profile later", "Manual export fallback"],
      requiredScopes: ["user.info.basic", "video.upload"],
      missingScopes: ["real_oauth_not_configured"],
      setupInstructions: [
        "Use mock connect for local TikTok UI testing.",
        "Future real setup requires a TikTok developer app and redirect URI.",
        "Required scopes are placeholders and must be verified before production.",
        "Content posting review may be required before future video posting access.",
        "Video upload and TikTok posting are disabled in this build.",
        "Publishing disabled in this build.",
      ],
      requiredEnvVars: ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REDIRECT_URI"],
      optionalEnvVars: ["TIKTOK_ENABLE_REAL_OAUTH", "TIKTOK_ENABLE_REAL_PUBLISHING"],
      redirectEnvVar: "TIKTOK_REDIRECT_URI",
      docsLinks: ["Official TikTok developer docs link placeholder", "Verify official docs before real OAuth."],
    },
    {
      id: "linkedin",
      label: "LinkedIn",
      badge: "IN",
      setupStatus: "mock_ready",
      accountType: "organization",
      capabilities: ["Connect mock", "Read profile later", "Manual export fallback"],
      requiredScopes: ["openid", "profile", "w_member_social", "w_organization_social", "r_organization_social"],
      missingScopes: ["real_oauth_not_configured"],
      setupInstructions: [
        "Use mock connect for local LinkedIn UI testing.",
        "Future real setup requires a LinkedIn Developer app and redirect URI.",
        "Product access may be required for posting, organization pages, comments, and analytics.",
        "Organization/page access must be selected safely before any future company posting.",
        "App review may be required before live LinkedIn permissions work.",
        "LinkedIn publishing is disabled in this build.",
        "Publishing disabled in this build.",
      ],
      requiredEnvVars: ["LINKEDIN_CLIENT_ID", "LINKEDIN_CLIENT_SECRET", "LINKEDIN_REDIRECT_URI"],
      optionalEnvVars: ["LINKEDIN_ENABLE_REAL_OAUTH", "LINKEDIN_ENABLE_REAL_PUBLISHING"],
      redirectEnvVar: "LINKEDIN_REDIRECT_URI",
      docsLinks: ["Official LinkedIn developer docs link placeholder", "Verify official docs before real OAuth."],
    },
    {
      id: "x",
      label: "X",
      badge: "X",
      setupStatus: "mock_ready",
      accountType: "unknown",
      capabilities: ["Connect mock", "Read profile later", "Manual export fallback"],
      requiredScopes: ["users.read", "tweet.read", "tweet.write", "offline.access"],
      missingScopes: ["real_oauth_not_configured"],
      setupInstructions: [
        "Use mock connect for local X UI testing.",
        "Future real setup requires an X developer app and redirect URI.",
        "API access/pricing can change and must be reviewed before real OAuth or posting work.",
        "Required scopes are placeholders and must be verified before production.",
        "X publishing is disabled in this build.",
        "Publishing disabled in this build.",
      ],
      requiredEnvVars: ["X_CLIENT_ID", "X_CLIENT_SECRET", "X_REDIRECT_URI"],
      optionalEnvVars: ["X_ENABLE_REAL_OAUTH", "X_ENABLE_REAL_PUBLISHING"],
      redirectEnvVar: "X_REDIRECT_URI",
      docsLinks: ["Official X developer docs link placeholder", "Verify official docs before real OAuth."],
    },
  ];
  const calendarState = {
    view: "week",
    cursorDate: new Date(),
    selectedPostId: null,
  };
  const queueState = {
    selectedItemId: null,
  };

  function activeApiBridge() {
    return window.localApiBridge?.available ? window.localApiBridge : null;
  }

  async function persistThroughApi(path, body) {
    const bridge = activeApiBridge();
    if (!bridge) return null;
    const result = await bridge.request(path, { method: "PATCH", body });
    await bridge.sync();
    return result;
  }

  const defaultSettings = {
    appName: "Local Social AI Manager",
    appEnvironment: "development",
    localDataDirectory: "./data",
    defaultTimezone: "America/New_York",
    defaultPlatformTargets: ["facebook", "instagram"],
    automationLevel: "approval_queue",
    requireApprovalBeforePublishing: true,
    requireApprovalBeforeReplying: true,
    emergencyPauseEnabled: false,
    aiProviderPreference: "mock",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const defaultOnboardingState = {
    status: "not_started",
    currentStep: "welcome",
    completedSteps: [],
    skippedSteps: [],
    steps: onboardingStepIds.map((id, index) => ({
      id,
      label: id.replaceAll("_", " "),
      status: index === 0 ? "in_progress" : "not_started",
    })),
    checklist: setupChecklistIds.map((id) => ({
      id,
      label: setupChecklistLabels[id],
      status: "not_started",
      optional: ["media_added", "first_draft_generated", "manual_export_tested", "analytics_added", "social_setup_reviewed"].includes(id),
    })),
    checklistById: {},
    localDataDirectory: "./data",
    localDataDirectoryExists: true,
    localDataDirectoryWritable: true,
    startedAt: "",
    completedAt: "",
    skippedAt: "",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const defaultSafetyCenterState = {
    emergencyPause: {
      enabled: false,
      enabledAt: "",
      enabledBy: "",
      reason: "",
    },
    automationLevel: "approval_queue",
    publishingSafety: {
      realPublishingEnabled: false,
      futureRealPublishingEligible: false,
      status: "disabled_by_policy",
      message: "Real publishing remains disabled in this build.",
    },
    replySafety: {
      realReplySendingEnabled: false,
      approvalRequired: true,
      status: "local_approval_only",
      message: "Replies are not sent automatically.",
    },
    queueProcessing: {
      byStatus: {},
      ready: 0,
      blocked: 0,
      disabled: false,
      status: "local_only",
    },
    connectedAccountSafety: {
      byStatus: {},
      connectedOrLimited: 0,
      requiresReauth: 0,
      tokensExposed: false,
    },
    criticalSafetyFlags: {
      total: 0,
      byFlag: {},
      affectedDrafts: [],
    },
    pendingApprovals: {
      draftsNeedingReview: 0,
      replySuggestionsNeedingReview: 0,
      queueItemsNeedingAttention: 0,
    },
    blockedActions: [
      "scheduling_new_posts",
      "queue_readiness_changes",
      "mock_publishing",
      "manual_export_packages",
      "future_real_publishing",
      "future_real_reply_sending",
      "ai_auto_reply_actions",
      "automation_above_approval_queue",
    ],
    allowedActions: [
      "viewing_existing_data",
      "editing_drafts",
      "editing_brand_brain",
      "importing_media",
      "creating_backups",
      "exporting_data_backup",
      "reading_analytics",
      "manual_status_notes",
    ],
    killSwitchActions: Object.entries(safetyKillActions).map(([id, action]) => ({ id, ...action })),
    auditLogs: [],
    localFlags: {},
  };

  const defaultBrandProfile = {
    id: "demo-brand-brightside-exterior-care",
    businessName: "Brightside Exterior Care Demo",
    tagline: "Cleaner curb appeal, handled with care.",
    industry: "Exterior cleaning",
    description:
      "Fake demo profile for a local exterior cleaning service. Used only for development and UI placeholders.",
    services: ["pressure washing", "soft washing", "gutter cleaning"],
    serviceAreas: ["Demo City", "Nearby service areas"],
    targetCustomers: ["local homeowners", "small property managers", "real estate listing teams"],
    brandVoice: "Helpful, neighborly, practical, and safety-conscious.",
    toneRules: [
      "Use practical local-service language.",
      "Avoid hype, pressure, and unsupported superlatives.",
      "Explain safety limits clearly.",
    ],
    bannedWords: ["guaranteed results", "best in the city", "real customer said"],
    preferredWords: ["careful", "local", "clean", "seasonal"],
    commonCTAs: ["Request a demo estimate", "Ask about exterior cleaning options"],
    hashtags: ["#DemoBusiness", "#ExteriorCleaning", "#LocalServiceBusiness"],
    website: "https://example.local/brightside-demo",
    phone: "555-0100",
    email: "hello@brightside-demo.example",
    approvalRules: [
      "Owner approves every generated draft before scheduling.",
      "Edited approved drafts require review before publishing.",
    ],
    safetyRules: [
      "Never invent testimonials.",
      "Never invent prices, certifications, guarantees, or availability.",
      "Do not imply a post was sent when it is only a draft.",
    ],
    examplePosts: [
      "Demo post: Spring is a good time to check siding, gutters, and walkways before heavy rain.",
      "Demo post: A careful exterior cleaning plan starts with looking at the surface before choosing pressure.",
    ],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const defaultMediaAssets = [
    {
      id: "demo-media-driveway-before",
      title: "Driveway before cleaning",
      originalFilename: "demo-driveway-before.jpg",
      mediaType: "image",
      fileSizeBytes: 2400000,
      createdAt: "2026-05-01T14:00:00.000Z",
      tags: ["before", "driveway", "demo"],
      serviceType: "pressure washing",
      locationName: "Demo customer driveway",
      city: "Demo City",
      state: "NY",
      projectDate: "2026-05-01",
      contentAngle: "before_after",
      qualityRating: 4,
      usageStatus: "reviewed",
      notes: "Pair with the after image. Do not imply guaranteed results.",
      status: "reviewed",
      previewUrl: "",
    },
    {
      id: "demo-media-driveway-after",
      title: "Driveway after cleaning",
      originalFilename: "demo-driveway-after.jpg",
      mediaType: "image",
      fileSizeBytes: 2600000,
      createdAt: "2026-05-01T15:30:00.000Z",
      tags: ["after", "driveway", "ready"],
      serviceType: "pressure washing",
      locationName: "Demo customer driveway",
      city: "Demo City",
      state: "NY",
      projectDate: "2026-05-01",
      contentAngle: "before_after",
      qualityRating: 5,
      usageStatus: "ready_for_generation",
      notes: "Use with the before image and avoid unsupported claims.",
      status: "ready_for_generation",
      previewUrl: "",
    },
    {
      id: "demo-media-gutter-cleaning",
      title: "Gutter cleaning detail",
      originalFilename: "demo-gutter-cleaning.jpg",
      mediaType: "image",
      fileSizeBytes: 1900000,
      createdAt: "2026-05-04T10:15:00.000Z",
      tags: ["gutter", "maintenance"],
      serviceType: "gutter cleaning",
      locationName: "Demo residential exterior",
      city: "Demo City",
      state: "NY",
      projectDate: "2026-05-04",
      contentAngle: "educational",
      qualityRating: 4,
      usageStatus: "reviewed",
      notes: "Good for a seasonal maintenance explanation.",
      status: "reviewed",
      previewUrl: "",
    },
    {
      id: "demo-media-team-setup",
      title: "Team setup walkthrough",
      originalFilename: "demo-team-setup.mp4",
      mediaType: "video",
      fileSizeBytes: 18400000,
      createdAt: "2026-05-07T12:45:00.000Z",
      tags: ["video", "behind the scenes"],
      serviceType: "exterior cleaning",
      locationName: "Demo job setup",
      city: "Demo City",
      state: "NY",
      projectDate: "2026-05-07",
      contentAngle: "behind_the_scenes",
      qualityRating: 3,
      usageStatus: "ready_for_generation",
      notes: "Use for process-oriented posts without customer details.",
      status: "ready_for_generation",
      previewUrl: "",
    },
    {
      id: "demo-media-seasonal-reminder",
      title: "Seasonal reminder photo",
      originalFilename: "demo-seasonal-reminder.jpg",
      mediaType: "image",
      fileSizeBytes: 2100000,
      createdAt: "2026-05-10T09:20:00.000Z",
      tags: ["seasonal", "education"],
      serviceType: "exterior cleaning",
      locationName: "Demo seasonal project",
      city: "Demo City",
      state: "NY",
      projectDate: "2026-05-10",
      contentAngle: "seasonal",
      qualityRating: 3,
      usageStatus: "archived",
      notes: "Older seasonal concept kept for reference.",
      status: "archived",
      previewUrl: "",
    },
  ];

  function buildDefaultCalendarDemo() {
    const brandName = defaultBrandProfile.businessName;
    const now = new Date();
    const start = new Date(now);
    start.setHours(0, 0, 0, 0);

    function atDayOffset(dayOffset, hour, minute) {
      const value = new Date(start);
      value.setDate(value.getDate() + dayOffset);
      value.setHours(hour, minute, 0, 0);
      return value.toISOString();
    }

    const posts = [
      {
        id: "demo-scheduled-gutter-reminder",
        generatedPostId: "demo-post-gutter-reminder",
        brandProfileId: defaultBrandProfile.id,
        brandName,
        platform: "facebook",
        scheduledFor: atDayOffset(1, 13, 30),
        timezone: defaultSettings.defaultTimezone,
        status: "scheduled",
        captionSnapshot:
          "Seasonal reminder: a simple gutter check before heavy rain can help homeowners spot debris early. Mock scheduled post. Not published.",
        mediaAssetIds: ["demo-media-gutter-cleaning"],
        publishQueueItemId: "demo-queue-gutter-reminder",
        userNotes: "Use this as a local seasonal reminder. No real publishing.",
        scheduleMetadata: {
          hook: "Spring gutter check for local homeowners.",
          headline: "Seasonal gutter reminder",
          hashtags: ["#DemoBusiness", "#GutterCleaning", "#LocalServiceBusiness"],
          callToAction: "Ask about exterior maintenance options.",
          safetyFlags: [],
        },
        preflightSnapshot: {
          status: "not_checked",
          warnings: ["manual_export_required"],
          errors: [],
        },
        createdAt: atDayOffset(-1, 10, 0),
        updatedAt: atDayOffset(-1, 10, 0),
        canceledAt: "",
      },
      {
        id: "demo-scheduled-driveway-before-after",
        generatedPostId: "demo-post-driveway-before-after",
        brandProfileId: defaultBrandProfile.id,
        brandName,
        platform: "instagram",
        scheduledFor: atDayOffset(3, 16, 0),
        timezone: defaultSettings.defaultTimezone,
        status: "queued",
        captionSnapshot:
          "Before-and-after demo: show the visual change while staying honest about the project scope. Mock scheduled post. Not published.",
        mediaAssetIds: ["demo-media-driveway-before", "demo-media-driveway-after"],
        publishQueueItemId: "demo-queue-driveway-before-after",
        userNotes: "Good candidate for manual export once reviewed.",
        scheduleMetadata: {
          hook: "A careful before-and-after driveway moment.",
          headline: "Driveway project recap",
          hashtags: ["#DemoBusiness", "#BeforeAfter", "#ExteriorCleaning"],
          callToAction: "See more recent exterior care examples.",
          safetyFlags: [],
        },
        preflightSnapshot: {
          status: "warnings",
          warnings: ["missing_connected_account_warns_for_manual_export"],
          errors: [],
        },
        createdAt: atDayOffset(-2, 15, 15),
        updatedAt: atDayOffset(-1, 9, 15),
        canceledAt: "",
      },
      {
        id: "demo-scheduled-team-process",
        generatedPostId: "demo-post-team-process",
        brandProfileId: defaultBrandProfile.id,
        brandName,
        platform: "linkedin",
        scheduledFor: atDayOffset(5, 9, 0),
        timezone: defaultSettings.defaultTimezone,
        status: "needs_attention",
        captionSnapshot:
          "Behind the scenes: explain the prep process without naming customers or making unsupported claims. Mock scheduled post. Not published.",
        mediaAssetIds: ["demo-media-team-setup"],
        publishQueueItemId: "demo-queue-team-process",
        userNotes: "Needs owner review before it moves forward.",
        scheduleMetadata: {
          hook: "How the team prepares before a job.",
          headline: "Behind-the-scenes setup",
          hashtags: ["#DemoBusiness", "#BehindTheScenes", "#LocalServiceBusiness"],
          callToAction: "Learn more about the process.",
          safetyFlags: ["manual_review_recommended"],
        },
        preflightSnapshot: {
          status: "blocked",
          warnings: [],
          errors: ["needs_attention"],
        },
        createdAt: atDayOffset(-1, 11, 45),
        updatedAt: atDayOffset(-1, 11, 45),
        canceledAt: "",
      },
    ];

    const queueItems = posts.map((post, index) => ({
      id: post.publishQueueItemId,
      scheduledPostId: post.id,
      generatedPostId: post.generatedPostId,
      brandProfileId: post.brandProfileId,
      platform: post.platform,
      queueStatus:
        post.status === "queued"
          ? "ready"
          : post.status === "needs_attention"
            ? "blocked"
            : "waiting",
      dueAt: post.scheduledFor,
      timezone: post.timezone,
      priority: 100 + index,
      preflightStatus: post.preflightSnapshot.status,
      preflightErrors: post.preflightSnapshot.errors,
      preflightWarnings: post.preflightSnapshot.warnings,
      mockPublishEnabled: post.status === "queued",
      manualExportRequired: true,
      lastCheckedAt: "",
      createdAt: post.createdAt,
      updatedAt: post.updatedAt,
    }));

    return { posts, queueItems };
  }

  function settingsUpdates(settings) {
    return {
      appName: settings.appName,
      appEnvironment: settings.appEnvironment,
      localDataDirectory: settings.localDataDirectory,
      defaultTimezone: settings.defaultTimezone,
      defaultPlatformTargets: settings.defaultPlatformTargets,
      automationLevel: settings.automationLevel,
      requireApprovalBeforePublishing: Boolean(settings.requireApprovalBeforePublishing),
      requireApprovalBeforeReplying: Boolean(settings.requireApprovalBeforeReplying),
      emergencyPauseEnabled: Boolean(settings.emergencyPauseEnabled),
      aiProviderPreference: settings.aiProviderPreference,
    };
  }

  function brandProfileUpdates(profile) {
    return {
      businessName: profile.businessName,
      tagline: profile.tagline,
      industry: profile.industry,
      description: profile.description,
      services: profile.services,
      serviceAreas: profile.serviceAreas,
      targetCustomers: profile.targetCustomers,
      brandVoice: profile.brandVoice,
      toneRules: profile.toneRules,
      bannedWords: profile.bannedWords,
      preferredWords: profile.preferredWords,
      commonCTAs: profile.commonCTAs,
      hashtags: profile.hashtags,
      website: profile.website,
      phone: profile.phone,
      email: profile.email,
      approvalRules: profile.approvalRules,
      safetyRules: profile.safetyRules,
      examplePosts: profile.examplePosts,
    };
  }

  function safeJson(rawValue, fallback) {
    if (!rawValue) return fallback;
    try {
      const parsed = JSON.parse(rawValue);
      return parsed == null ? fallback : parsed;
    } catch (_error) {
      return fallback;
    }
  }

  function normalizeChecklistItem(item) {
    const id = item.id || "unknown";
    return {
      id,
      label: item.label || setupChecklistLabels[id] || id.replaceAll("_", " "),
      status: ["not_started", "in_progress", "completed", "skipped", "needs_attention"].includes(item.status)
        ? item.status
        : "not_started",
      optional: Boolean(item.optional),
    };
  }

  function computedBrowserChecklist() {
    const brand = brandBrainAdapter.loadWithoutFallback();
    const media = mediaLibraryAdapter.load();
    const drafts = loadBrowserArray("local-social-ai-manager.drafts");
    const scheduled = loadScheduledPosts();
    const queue = loadPublishQueueItems();
    const analytics = loadBrowserArray("local-social-ai-manager.analyticsSnapshots");
    const accounts = loadBrowserArray(CONNECTED_ACCOUNTS_KEY);
    const onboarding = onboardingAdapter.loadLocal();
    const completedSteps = onboarding.completedSteps || [];
    const skippedSteps = onboarding.skippedSteps || [];
    const statuses = {
      brand_profile_created: brand ? "completed" : "not_started",
      local_data_ready: "completed",
      safety_settings_confirmed: completedSteps.includes("safety") ? "completed" : "not_started",
      media_added: media.length ? "completed" : skippedSteps.includes("media") ? "skipped" : "not_started",
      first_draft_generated: drafts.length ? "completed" : skippedSteps.includes("demo_draft") ? "skipped" : "not_started",
      first_draft_approved: drafts.some((draft) => draft.approvalStatus === "approved") ? "completed" : "not_started",
      first_post_scheduled: scheduled.length ? "completed" : "not_started",
      manual_export_tested: queue.some((item) => item.queueStatus === "manually_exported") ? "completed" : "not_started",
      analytics_added: analytics.length ? "completed" : "not_started",
      social_setup_reviewed: accounts.length ? "completed" : "not_started",
    };
    return setupChecklistIds.map((id) => normalizeChecklistItem({
      id,
      label: setupChecklistLabels[id],
      status: statuses[id],
      optional: defaultOnboardingState.checklist.find((item) => item.id === id)?.optional,
    }));
  }

  function loadBrowserArray(key) {
    const parsed = safeJson(window.localStorage.getItem(key), []);
    return Array.isArray(parsed) ? parsed : [];
  }

  const onboardingAdapter = {
    loadLocal() {
      const rawState = window.localStorage.getItem(ONBOARDING_STORAGE_KEY);
      const state = rawState ? safeJson(rawState, defaultOnboardingState) : defaultOnboardingState;
      const checklist = loadSetupChecklist();
      return {
        ...defaultOnboardingState,
        ...state,
        checklist,
        checklistById: Object.fromEntries(checklist.map((item) => [item.id, item])),
      };
    },

    saveLocal(state) {
      const checklist = Array.isArray(state.checklist)
        ? state.checklist.map(normalizeChecklistItem)
        : computedBrowserChecklist();
      const nextState = {
        ...defaultOnboardingState,
        ...state,
        checklist,
        checklistById: Object.fromEntries(checklist.map((item) => [item.id, item])),
        updatedAt: new Date().toISOString(),
      };
      window.localStorage.setItem(ONBOARDING_STORAGE_KEY, JSON.stringify(nextState));
      window.localStorage.setItem(SETUP_CHECKLIST_KEY, JSON.stringify(checklist));
      return nextState;
    },

    async complete(payload) {
      const bridge = activeApiBridge();
      if (bridge) {
        const state = await bridge.request("/api/onboarding/complete", {
          method: "POST",
          body: payload,
        });
        await bridge.sync();
        return state;
      }
      return this.saveLocal({
        ...this.loadLocal(),
        status: "completed",
        currentStep: "next_steps",
        completedSteps: onboardingStepIds,
        skippedSteps: payload.skippedSteps || [],
        completedAt: new Date().toISOString(),
      });
    },

    async skip(reason) {
      const bridge = activeApiBridge();
      if (bridge) {
        const state = await bridge.request("/api/onboarding/skip", {
          method: "POST",
          body: { reason },
        });
        await bridge.sync();
        return state;
      }
      return this.saveLocal({
        ...this.loadLocal(),
        status: "skipped",
        currentStep: "next_steps",
        skippedAt: new Date().toISOString(),
      });
    },

    async restart() {
      const bridge = activeApiBridge();
      if (bridge) {
        const state = await bridge.request("/api/onboarding/restart", {
          method: "POST",
          body: {},
        });
        await bridge.sync();
        return state;
      }
      return this.saveLocal({
        ...defaultOnboardingState,
        status: "in_progress",
        startedAt: new Date().toISOString(),
      });
    },
  };

  function loadSetupChecklist() {
    const hydrated = safeJson(window.localStorage.getItem(SETUP_CHECKLIST_KEY), null);
    if (Array.isArray(hydrated) && hydrated.length) {
      return hydrated.map(normalizeChecklistItem);
    }
    return defaultOnboardingState.checklist.map(normalizeChecklistItem);
  }

  function auditEntry(action, details = {}, actorType = "user") {
    return {
      id: `safety-audit-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      action,
      actorType,
      details,
      createdAt: new Date().toISOString(),
    };
  }

  function loadSafetyAuditLogs() {
    const parsed = safeJson(window.localStorage.getItem("local-social-ai-manager.safetyAuditLogs"), []);
    return Array.isArray(parsed) ? parsed : [];
  }

  function saveSafetyAuditLogs(logs) {
    window.localStorage.setItem("local-social-ai-manager.safetyAuditLogs", JSON.stringify(logs.slice(0, 100)));
    return logs;
  }

  function appendSafetyAudit(action, details = {}, actorType = "user") {
    const logs = [auditEntry(action, details, actorType), ...loadSafetyAuditLogs()];
    saveSafetyAuditLogs(logs);
    return logs[0];
  }

  function countBy(items, field) {
    return items.reduce((counts, item) => {
      const value = item[field] || "unknown";
      counts[value] = (counts[value] || 0) + 1;
      return counts;
    }, {});
  }

  function computeSafetyState() {
    const settings = settingsAdapter.load();
    const drafts = loadBrowserArray("local-social-ai-manager.drafts");
    const queue = loadPublishQueueItems();
    const accounts = loadBrowserArray(CONNECTED_ACCOUNTS_KEY);
    const suggestions = loadBrowserArray("local-social-ai-manager.replySuggestions");
    const localState = safeJson(window.localStorage.getItem(SAFETY_CENTER_STORAGE_KEY), {});
    const auditLogs = Array.isArray(localState.auditLogs) && localState.auditLogs.length
      ? localState.auditLogs
      : loadSafetyAuditLogs();
    const enabledLog = auditLogs.find((entry) => entry.action === "emergency_pause_enabled") || {};
    const criticalFlags = {};
    const affectedDrafts = [];
    drafts.forEach((draft) => {
      const flags = Array.isArray(draft.safetyFlags) ? draft.safetyFlags : [];
      const critical = flags.filter((flag) => criticalQueueFlags.has(flag));
      if (!critical.length) return;
      critical.forEach((flag) => {
        criticalFlags[flag] = (criticalFlags[flag] || 0) + 1;
      });
      affectedDrafts.push({
        draftId: draft.id,
        platform: draft.platform,
        title: draft.headline || draft.hook || "Draft",
        flags: critical,
      });
    });
    const localFlags = localState.localFlags || {};
    return {
      ...defaultSafetyCenterState,
      ...localState,
      emergencyPause: {
        enabled: Boolean(settings.emergencyPauseEnabled),
        enabledAt: settings.emergencyPauseEnabled ? enabledLog.createdAt || "" : "",
        enabledBy: settings.emergencyPauseEnabled ? enabledLog.actorType || "" : "",
        reason: settings.emergencyPauseEnabled ? enabledLog.details?.reason || "" : "",
      },
      automationLevel: settings.automationLevel,
      queueProcessing: {
        byStatus: countBy(queue, "queueStatus"),
        ready: queue.filter((item) => item.queueStatus === "ready").length,
        blocked: queue.filter((item) => item.queueStatus === "blocked").length,
        disabled: Boolean(localFlags.queueProcessingDisabled),
        status: settings.emergencyPauseEnabled ? "paused" : "local_only",
      },
      connectedAccountSafety: {
        byStatus: countBy(accounts, "connectionStatus"),
        connectedOrLimited: accounts.filter((account) => ["connected", "limited"].includes(account.connectionStatus)).length,
        requiresReauth: accounts.filter((account) => ["expired", "requires_reauth"].includes(account.connectionStatus)).length,
        tokensExposed: false,
      },
      criticalSafetyFlags: {
        total: Object.values(criticalFlags).reduce((total, count) => total + count, 0),
        byFlag: criticalFlags,
        affectedDrafts,
      },
      pendingApprovals: {
        draftsNeedingReview: drafts.filter((draft) => ["needs_review", "revision_requested"].includes(draft.approvalStatus)).length,
        replySuggestionsNeedingReview: suggestions.filter((suggestion) => ["generated", "edited"].includes(suggestion.status)).length,
        queueItemsNeedingAttention: queue.filter((item) => ["waiting", "blocked"].includes(item.queueStatus)).length,
      },
      auditLogs,
      localFlags,
    };
  }

  const safetyCenterAdapter = {
    loadLocal() {
      const state = computeSafetyState();
      window.localStorage.setItem(SAFETY_CENTER_STORAGE_KEY, JSON.stringify(state));
      return state;
    },

    async refresh() {
      const bridge = activeApiBridge();
      if (bridge) {
        const state = await bridge.request("/api/safety-center");
        window.localStorage.setItem(SAFETY_CENTER_STORAGE_KEY, JSON.stringify(state));
        return state;
      }
      return this.loadLocal();
    },

    async setEmergencyPause(enabled, reason) {
      const bridge = activeApiBridge();
      if (bridge) {
        const state = await bridge.request("/api/safety-center/emergency-pause", {
          method: "POST",
          body: { enabled, reason, actor_type: "user" },
        });
        await bridge.sync();
        return state;
      }
      const settings = settingsAdapter.load();
      settingsAdapter.saveLocal({
        ...settings,
        emergencyPauseEnabled: Boolean(enabled),
        automationLevel: "approval_queue",
      });
      appendSafetyAudit(
        enabled ? "emergency_pause_enabled" : "emergency_pause_disabled",
        { reason: reason || "", previousEmergencyPauseEnabled: settings.emergencyPauseEnabled, newEmergencyPauseEnabled: Boolean(enabled) },
      );
      return this.loadLocal();
    },

    async setAutomationLevel(level) {
      if (!["manual_assist", "approval_queue"].includes(level)) {
        throw new Error("Automation levels above approval_queue are planned/locked in the MVP.");
      }
      const bridge = activeApiBridge();
      if (bridge) {
        const state = await bridge.request("/api/safety-center/automation-level", {
          method: "POST",
          body: { automationLevel: level, actor_type: "user" },
        });
        await bridge.sync();
        return state;
      }
      const settings = settingsAdapter.load();
      settingsAdapter.saveLocal({ ...settings, automationLevel: level });
      appendSafetyAudit("automation_level_changed", {
        previousAutomationLevel: settings.automationLevel,
        newAutomationLevel: level,
      });
      return this.loadLocal();
    },

    async runKillSwitchAction(actionId, confirmationPhrase) {
      const action = safetyKillActions[actionId];
      if (!action) {
        throw new Error("Unsupported kill switch action.");
      }
      if (confirmationPhrase !== action.confirmationPhrase) {
        throw new Error(`Type ${action.confirmationPhrase} to confirm this action.`);
      }
      const bridge = activeApiBridge();
      if (bridge) {
        const state = await bridge.request(`/api/safety-center/kill-switch/${encodeURIComponent(actionId)}`, {
          method: "POST",
          body: { confirmationPhrase, actor_type: "user" },
        });
        await bridge.sync();
        return state;
      }
      appendSafetyAudit("kill_switch_action_started", { action: actionId, label: action.label });
      const settings = settingsAdapter.load();
      if (actionId === "pause_all_automation") {
        settingsAdapter.saveLocal({ ...settings, emergencyPauseEnabled: true, automationLevel: "approval_queue" });
        const local = computeSafetyState();
        local.localFlags = { ...local.localFlags, queueProcessingDisabled: true, updatedAt: new Date().toISOString() };
        window.localStorage.setItem(SAFETY_CENTER_STORAGE_KEY, JSON.stringify(local));
        appendSafetyAudit("queue_processing_disabled", { localOnly: true });
      }
      if (actionId === "cancel_future_scheduled_posts") {
        const now = new Date().toISOString();
        saveScheduledPosts(loadScheduledPosts().map((post) =>
          ["scheduled", "queued", "missed", "failed", "needs_attention"].includes(post.status)
            ? { ...post, status: "canceled", canceledAt: post.canceledAt || now, updatedAt: now }
            : post
        ));
        savePublishQueueItems(loadPublishQueueItems().map((item) =>
          ["waiting", "ready", "blocked", "failed"].includes(item.queueStatus)
            ? { ...item, queueStatus: "canceled", updatedAt: now }
            : item
        ));
        appendSafetyAudit("scheduled_posts_canceled", { localOnly: true });
      }
      if (actionId === "disable_queue_processing") {
        const local = computeSafetyState();
        local.localFlags = { ...local.localFlags, queueProcessingDisabled: true, updatedAt: new Date().toISOString() };
        window.localStorage.setItem(SAFETY_CENTER_STORAGE_KEY, JSON.stringify(local));
        appendSafetyAudit("queue_processing_disabled", { localOnly: true });
      }
      if (actionId === "disconnect_accounts_locally") {
        const accounts = loadBrowserArray(CONNECTED_ACCOUNTS_KEY).map((account) => ({
          ...account,
          connectionStatus: "disconnected",
          disconnectedAt: new Date().toISOString(),
        }));
        window.localStorage.setItem(CONNECTED_ACCOUNTS_KEY, JSON.stringify(accounts));
        appendSafetyAudit("accounts_disconnected", { localOnly: true, count: accounts.length });
      }
      if (actionId === "revoke_tokens_locally") {
        appendSafetyAudit("tokens_marked_revoked", { localOnly: true, rawTokensStored: false });
      }
      if (actionId === "disable_ai_generation") {
        const local = computeSafetyState();
        local.localFlags = { ...local.localFlags, aiGenerationDisabled: true, updatedAt: new Date().toISOString() };
        window.localStorage.setItem(SAFETY_CENTER_STORAGE_KEY, JSON.stringify(local));
        appendSafetyAudit("ai_generation_disabled", { localOnly: true });
      }
      if (actionId === "export_safety_report") {
        appendSafetyAudit("safety_report_exported", { browserFallback: true, secretsIncluded: false });
      }
      appendSafetyAudit("kill_switch_action_completed", { action: actionId, label: action.label });
      return this.loadLocal();
    },
  };

  const backupDataAdapter = {
    loadLocal() {
      return loadBrowserArray(BACKUP_STORAGE_KEY);
    },

    saveLocal(items) {
      const normalized = Array.isArray(items) ? items : [];
      window.localStorage.setItem(BACKUP_STORAGE_KEY, JSON.stringify(normalized));
      return normalized;
    },

    async refresh() {
      const bridge = activeApiBridge();
      if (bridge) {
        const history = await bridge.request("/api/backups");
        this.saveLocal(history);
        return history;
      }
      return this.loadLocal();
    },

    async createBackup(options) {
      const bridge = activeApiBridge();
      if (bridge) {
        const result = await bridge.request("/api/backups", {
          method: "POST",
          body: options,
        });
        await bridge.sync();
        const history = await this.refresh();
        return { result, history };
      }
      const now = new Date().toISOString();
      const result = {
        backupId: `browser-backup-${Date.now()}`,
        createdAt: now,
        backupType: options.backupType || "full_local_backup",
        backupPath: `browser-demo-only/${options.backupType || "full_local_backup"}`,
        includeMedia: Boolean(options.includeMedia),
        includeSensitiveTokens: false,
        includeTokenMetadata: Boolean(options.includeTokenMetadata),
        tableCounts: {
          generated_posts: loadBrowserArray("local-social-ai-manager.drafts").length,
          media_assets: loadBrowserArray(MEDIA_STORAGE_KEY).length,
          scheduled_posts: loadScheduledPosts().length,
          publish_queue_items: loadPublishQueueItems().length,
        },
        fileCounts: {
          jsonFiles: 0,
          csvFiles: 0,
          markdownFiles: 0,
          mediaCopied: 0,
          mediaMissing: 0,
          databaseFiles: 0,
        },
        warnings: [
          "Browser-only mode cannot write backup files. Use the localhost SQLite bridge to create real local backups.",
          "Raw tokens are excluded.",
        ],
        restoreNotes: ["Use the local server for restore preview and future restore actions."],
        files: [],
        localOnly: true,
      };
      const history = [result, ...this.loadLocal()].slice(0, 50);
      this.saveLocal(history);
      return { result, history };
    },

    async previewRestore(backupPath) {
      const bridge = activeApiBridge();
      if (bridge) {
        return bridge.request("/api/backups/restore-preview", {
          method: "POST",
          body: { backupPath },
        });
      }
      return {
        status: "preview_unavailable",
        backupPath,
        backupType: "unknown",
        willRestoreTokens: false,
        requiresConfirmation: true,
        destructiveRestoreImplemented: false,
        warnings: [
          "Restore preview requires the localhost SQLite bridge.",
          "Raw tokens are not restored by default.",
        ],
        restorePlan: [
          "Start the local server.",
          "Paste the backup folder path again.",
          "Review the restore plan before overwriting local data.",
        ],
      };
    },
  };

  const diagnosticsAdapter = {
    loadLocal() {
      const cached = safeJson(window.localStorage.getItem(DIAGNOSTICS_STORAGE_KEY), null);
      return cached || this.computeBrowserFallback();
    },

    saveLocal(diagnostics) {
      window.localStorage.setItem(DIAGNOSTICS_STORAGE_KEY, JSON.stringify(diagnostics));
      return diagnostics;
    },

    recentErrors() {
      return loadBrowserArray(RECENT_ERRORS_STORAGE_KEY);
    },

    async refresh() {
      const bridge = activeApiBridge();
      if (bridge) {
        const diagnostics = await bridge.request("/api/diagnostics");
        this.saveLocal(diagnostics);
        return diagnostics;
      }
      const diagnostics = this.computeBrowserFallback();
      this.saveLocal(diagnostics);
      return diagnostics;
    },

    async exportReport() {
      const bridge = activeApiBridge();
      if (bridge) {
        const result = await bridge.request("/api/diagnostics/export", {
          method: "POST",
          body: { recentErrors: this.recentErrors() },
        });
        await bridge.sync();
        return result;
      }
      const diagnostics = this.computeBrowserFallback();
      const result = {
        reportPath: "browser-demo-only/diagnostic-report.md",
        createdAt: diagnostics.checkedAt,
        overallStatus: diagnostics.overallStatus,
        redactionNotice: "Browser-only mode cannot write files. Start the localhost bridge to export a real report.",
      };
      this.saveLocal(diagnostics);
      return result;
    },

    computeBrowserFallback() {
      const checkedAt = new Date().toISOString();
      const settings = settingsAdapter.load();
      const safety = safetyCenterAdapter.loadLocal();
      const drafts = loadBrowserArray("local-social-ai-manager.drafts");
      const queue = loadPublishQueueItems();
      const engagement = loadBrowserArray("local-social-ai-manager.engagementItems");
      const analytics = loadBrowserArray("local-social-ai-manager.analyticsSnapshots");
      const accounts = loadBrowserArray(CONNECTED_ACCOUNTS_KEY);
      const backups = backupDataAdapter.loadLocal();
      const checklist = computedBrowserChecklist();
      const recentErrors = this.recentErrors();
      const sections = [
        diagnosticsSection("local_storage", "Local storage", [
          diagnosticResult("app_environment", "App environment", "healthy", settings.appEnvironment || "development", "Browser fallback only.", "Start the localhost SQLite bridge for filesystem checks.", checkedAt),
          diagnosticResult("local_data_directory_exists", "Local data directory exists", "unknown", settings.localDataDirectory || "./data", "Browser mode cannot check filesystem paths.", "Start the localhost SQLite bridge for full diagnostics.", checkedAt),
          diagnosticResult("local_data_directory_writable", "Local data directory writable", "unknown", "Writability cannot be checked from static browser mode.", "No filesystem write is attempted in browser fallback.", "Start the localhost SQLite bridge for a real write check.", checkedAt),
          diagnosticResult("media_directory_exists", "Media directory exists", "unknown", "Browser mode cannot inspect the media directory.", "No local filesystem API is available here.", "Start the localhost SQLite bridge for full diagnostics.", checkedAt),
          diagnosticResult("export_directory_exists", "Export directory exists", "unknown", "Browser mode cannot inspect the export directory.", "No local filesystem API is available here.", "Start the localhost SQLite bridge for full diagnostics.", checkedAt),
          diagnosticResult("logs_directory_exists", "Logs directory exists", "unknown", "Browser mode cannot inspect the logs directory.", "No local filesystem API is available here.", "Start the localhost SQLite bridge for full diagnostics.", checkedAt),
          diagnosticResult("backup_directory_exists", "Backup directory exists", "unknown", "Browser mode cannot inspect the backup directory.", "No local filesystem API is available here.", "Start the localhost SQLite bridge for full diagnostics.", checkedAt),
        ]),
        diagnosticsSection("database", "Database", [
          diagnosticResult("sqlite_database_reachable", "SQLite database reachable", activeApiBridge() ? "healthy" : "warning", activeApiBridge() ? "SQLite bridge is available." : "SQLite bridge is not active.", "Static browser mode uses localStorage demo data.", "Run the local API server for real database checks.", checkedAt),
          diagnosticResult("database_migrations_status", "Database migrations status", "unknown", "Migration status is unavailable in browser fallback.", "No database query was run.", "Run the local API server for migration checks.", checkedAt),
        ]),
        diagnosticsSection("ai", "AI", [
          diagnosticResult("ai_provider_status", "AI provider status", settings.aiProviderPreference === "mock" ? "healthy" : "warning", `AI provider preference is ${settings.aiProviderPreference}.`, "Mock mode is the safe local default.", "Keep mock selected unless intentionally configuring real providers later.", checkedAt),
          diagnosticResult("mock_ai_provider_available", "Mock AI provider available", "healthy", "Mock AI is available in the local demo.", "No API key is required.", "No action needed.", checkedAt),
        ]),
        diagnosticsSection("social_integrations", "Social integrations", [
          diagnosticResult("integration_mode", "Integration mode", "healthy", "Mock/scaffold integration mode.", "Browser fallback does not read environment variables.", "Open Social Integration Setup for configuration guidance.", checkedAt),
          diagnosticResult("real_publishing_disabled", "Real publishing disabled", "healthy", "Real publishing is disabled.", "Manual export remains the safe path.", "No action needed.", checkedAt),
          diagnosticResult("connected_account_summary", "Connected account summary", "healthy", `${accounts.length} connected account record(s) in browser cache.`, "Token fields are not displayed.", "Use Connected Accounts to review mock connections.", checkedAt),
          diagnosticResult("token_storage_mode", "Token storage mode", "healthy", "placeholder_not_stored", "Browser UI never stores raw OAuth tokens.", "Use secure storage before real OAuth later.", checkedAt),
          diagnosticResult("secret_exposure_safety", "Secret exposure safety check", "healthy", "Diagnostics redacts known token and secret patterns.", "No token blobs are displayed.", "Do not paste secrets into troubleshooting messages.", checkedAt),
        ]),
        diagnosticsSection("safety", "Safety", [
          diagnosticResult("emergency_pause_status", "Emergency pause status", safety.emergencyPause?.enabled ? "warning" : "healthy", safety.emergencyPause?.enabled ? "Emergency pause is on." : "Emergency pause is off.", "Pause blocks automation and queue readiness.", "Use Safety Center to change pause state.", checkedAt),
          diagnosticResult("automation_level_status", "Automation level", safety.automationLevel === "approval_queue" ? "healthy" : "warning", `Automation level is ${safety.automationLevel}.`, "Higher levels are planned/locked.", "Keep approval_queue for MVP safety.", checkedAt),
        ]),
        diagnosticsSection("queue_jobs", "Queue and jobs", [
          diagnosticResult("job_runner_status", "Job runner status", "unknown", "No local job runner execution can be checked in browser mode.", "The runner is server-side/local Python.", "Run the local job runner from the documented command.", checkedAt),
          diagnosticResult("queue_blocked_count", "Queue blocked count", queue.some((item) => item.queueStatus === "blocked") ? "warning" : "healthy", `${queue.filter((item) => item.queueStatus === "blocked").length} queue item(s) are blocked.`, "Blocked items stay local.", "Open Publish Queue to review blockers.", checkedAt),
        ]),
        diagnosticsSection("content_workflow", "Content workflow", [
          diagnosticResult("drafts_needing_review_count", "Drafts needing review", drafts.some((draft) => ["needs_review", "revision_requested"].includes(draft.approvalStatus)) ? "warning" : "healthy", `${drafts.filter((draft) => ["needs_review", "revision_requested"].includes(draft.approvalStatus)).length} draft(s) need review.`, "Human approval is required.", "Open Drafts to review local content.", checkedAt),
          diagnosticResult("engagement_needing_reply_count", "Engagement needing reply", engagement.some((item) => ["new", "needs_reply", "reply_suggested"].includes(item.status) && item.requiresResponse) ? "warning" : "healthy", `${engagement.filter((item) => ["new", "needs_reply", "reply_suggested"].includes(item.status) && item.requiresResponse).length} engagement item(s) need reply.`, "Replies are local-only until future explicit platform work.", "Open Engagement Inbox.", checkedAt),
          diagnosticResult("analytics_data_availability", "Analytics data availability", analytics.length ? "healthy" : "warning", `${analytics.length} analytics snapshot(s) are cached.`, "Manual data is manual; mock data is fake/demo.", "Add manual metrics or generate mock analytics.", checkedAt),
          diagnosticResult("setup_checklist_status", "Setup checklist status", checklist.every((item) => item.status === "completed" || item.optional) ? "healthy" : "warning", `${checklist.filter((item) => item.status === "completed").length} of ${checklist.length} checklist item(s) complete.`, "The checklist guides first setup.", "Open Home or Onboarding to continue setup.", checkedAt),
        ]),
        diagnosticsSection("backups", "Backups", [
          diagnosticResult("backup_availability", "Backup availability", backups.length ? "healthy" : "warning", `${backups.length} backup(s) are cached.`, "Browser mode cannot create real backup files.", "Use Backup & Data through the localhost bridge to create real backups.", checkedAt),
        ]),
        diagnosticsSection("recent_errors", "Recent errors", [
          diagnosticResult("recent_safe_errors", "Recent safe errors", recentErrors.length ? "warning" : "healthy", `${recentErrors.length} recent safe error(s) recorded.`, recentErrors.slice(0, 3).map(redactDiagnosticText).join(" | ") || "No recent safe errors.", "Copy or export diagnostics when asking for help.", checkedAt),
        ]),
      ];
      const results = sections.flatMap((section) => section.results);
      const summary = diagnosticStatusSummary(results);
      return {
        checkedAt,
        overallStatus: summary.error ? "error" : summary.warning ? "warning" : summary.unknown ? "unknown" : "healthy",
        summary,
        sections,
        results,
        nextSteps: results
          .filter((result) => ["error", "warning", "unknown"].includes(result.status))
          .map((result) => result.recommendedAction)
          .filter((value, index, list) => value && list.indexOf(value) === index)
          .slice(0, 8),
        recentErrors,
        localOnly: true,
        redactionNotice: "Diagnostics redacts tokens, secrets, authorization codes, and raw provider credentials.",
      };
    },
  };

  const settingsAdapter = {
    load() {
      // api-client.js hydrates this adapter from SQLite when the localhost
      // bridge is active. Direct-file mode keeps a browser demo fallback.
      const rawSettings = window.localStorage.getItem(STORAGE_KEY);
      if (!rawSettings) {
        this.saveLocal(defaultSettings);
        return { ...defaultSettings };
      }

      try {
        return { ...defaultSettings, ...JSON.parse(rawSettings) };
      } catch (_error) {
        this.saveLocal(defaultSettings);
        return { ...defaultSettings };
      }
    },

    saveLocal(settings) {
      const now = new Date().toISOString();
      const existing = this.loadWithoutFallback();
      const nextSettings = {
        ...settings,
        createdAt: existing?.createdAt || settings.createdAt || now,
        updatedAt: now,
      };
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(nextSettings));
      return nextSettings;
    },

    async save(settings) {
      const bridge = activeApiBridge();
      if (bridge) {
        await persistThroughApi("/api/settings", settingsUpdates(settings));
        return this.load();
      }
      return this.saveLocal(settings);
    },

    loadWithoutFallback() {
      const rawSettings = window.localStorage.getItem(STORAGE_KEY);
      if (!rawSettings) {
        return null;
      }
      try {
        return JSON.parse(rawSettings);
      } catch (_error) {
        return null;
      }
    },

    async reset() {
      const bridge = activeApiBridge();
      if (bridge) {
        await persistThroughApi("/api/settings", settingsUpdates(defaultSettings));
        return this.load();
      }
      window.localStorage.removeItem(STORAGE_KEY);
      return this.load();
    },
  };

  const brandBrainAdapter = {
    load() {
      // api-client.js hydrates Brand Brain from SQLite when the localhost
      // bridge is active. Direct-file mode keeps a browser demo fallback.
      const rawProfile = window.localStorage.getItem(BRAND_STORAGE_KEY);
      if (!rawProfile) {
        this.saveLocal(defaultBrandProfile);
        return cloneBrandProfile(defaultBrandProfile);
      }

      try {
        return { ...cloneBrandProfile(defaultBrandProfile), ...JSON.parse(rawProfile) };
      } catch (_error) {
        this.saveLocal(defaultBrandProfile);
        return cloneBrandProfile(defaultBrandProfile);
      }
    },

    saveLocal(profile) {
      const now = new Date().toISOString();
      const existing = this.loadWithoutFallback();
      const nextProfile = {
        ...profile,
        id: existing?.id || profile.id || defaultBrandProfile.id,
        createdAt: existing?.createdAt || profile.createdAt || now,
        updatedAt: now,
      };
      window.localStorage.setItem(BRAND_STORAGE_KEY, JSON.stringify(nextProfile));
      return nextProfile;
    },

    async save(profile) {
      const bridge = activeApiBridge();
      const existing = this.loadWithoutFallback();
      const profileId = existing?.id || profile.id || defaultBrandProfile.id;
      if (bridge) {
        await persistThroughApi(
          `/api/brand-profiles/${encodeURIComponent(profileId)}`,
          brandProfileUpdates(profile),
        );
        return this.load();
      }
      return this.saveLocal(profile);
    },

    loadWithoutFallback() {
      const rawProfile = window.localStorage.getItem(BRAND_STORAGE_KEY);
      if (!rawProfile) {
        return null;
      }
      try {
        return JSON.parse(rawProfile);
      } catch (_error) {
        return null;
      }
    },

    async reset() {
      const bridge = activeApiBridge();
      const existing = this.loadWithoutFallback();
      const profileId = existing?.id || defaultBrandProfile.id;
      if (bridge) {
        await persistThroughApi(
          `/api/brand-profiles/${encodeURIComponent(profileId)}`,
          brandProfileUpdates(defaultBrandProfile),
        );
        return this.load();
      }
      window.localStorage.removeItem(BRAND_STORAGE_KEY);
      return this.load();
    },
  };

  const mediaLibraryAdapter = {
    load() {
      // api-client.js hydrates media records from SQLite when the localhost
      // bridge is active. Direct-file mode keeps a browser demo fallback.
      const rawMedia = window.localStorage.getItem(MEDIA_STORAGE_KEY);
      if (!rawMedia) {
        this.save(defaultMediaAssets);
        return cloneMediaAssets(defaultMediaAssets);
      }

      try {
        const assets = JSON.parse(rawMedia);
        return Array.isArray(assets) ? assets.map(normalizeMediaAsset) : cloneMediaAssets(defaultMediaAssets);
      } catch (_error) {
        this.save(defaultMediaAssets);
        return cloneMediaAssets(defaultMediaAssets);
      }
    },

    save(assets) {
      window.localStorage.setItem(MEDIA_STORAGE_KEY, JSON.stringify(assets.map(normalizeMediaAsset)));
      return assets.map(normalizeMediaAsset);
    },

    reset() {
      window.localStorage.removeItem(MEDIA_STORAGE_KEY);
      return this.load();
    },

    add(asset) {
      const assets = this.load();
      const nextAssets = [normalizeMediaAsset(asset), ...assets];
      return this.save(nextAssets);
    },
  };

  function loadScheduledPosts() {
    // api-client.js hydrates Calendar rows from SQLite when the localhost
    // bridge is active. Direct-file mode keeps a local demo fallback.
    const rawPosts = window.localStorage.getItem(SCHEDULED_POSTS_KEY);
    if (!rawPosts) {
      const demo = buildDefaultCalendarDemo();
      saveScheduledPosts(demo.posts);
      if (!window.localStorage.getItem(PUBLISH_QUEUE_ITEMS_KEY)) {
        savePublishQueueItems(demo.queueItems);
      }
      return demo.posts.map(normalizeScheduledPost);
    }

    try {
      const posts = JSON.parse(rawPosts);
      return Array.isArray(posts) ? posts.map(normalizeScheduledPost) : [];
    } catch (_error) {
      const demo = buildDefaultCalendarDemo();
      saveScheduledPosts(demo.posts);
      savePublishQueueItems(demo.queueItems);
      return demo.posts.map(normalizeScheduledPost);
    }
  }

  function saveScheduledPosts(posts) {
    window.localStorage.setItem(
      SCHEDULED_POSTS_KEY,
      JSON.stringify(posts.map(normalizeScheduledPost)),
    );
  }

  function loadPublishQueueItems() {
    const rawItems = window.localStorage.getItem(PUBLISH_QUEUE_ITEMS_KEY);
    if (!rawItems) {
      const demo = buildDefaultCalendarDemo();
      savePublishQueueItems(demo.queueItems);
      if (!window.localStorage.getItem(SCHEDULED_POSTS_KEY)) {
        saveScheduledPosts(demo.posts);
      }
      return demo.queueItems.map(normalizePublishQueueItem);
    }

    try {
      const items = JSON.parse(rawItems);
      return Array.isArray(items) ? items.map(normalizePublishQueueItem) : [];
    } catch (_error) {
      const demo = buildDefaultCalendarDemo();
      savePublishQueueItems(demo.queueItems);
      return demo.queueItems.map(normalizePublishQueueItem);
    }
  }

  function savePublishQueueItems(items) {
    window.localStorage.setItem(
      PUBLISH_QUEUE_ITEMS_KEY,
      JSON.stringify(items.map(normalizePublishQueueItem)),
    );
  }

  function loadPublishAttempts() {
    const rawAttempts = window.localStorage.getItem(PUBLISH_ATTEMPTS_KEY);
    if (!rawAttempts) {
      return [];
    }

    try {
      const attempts = JSON.parse(rawAttempts);
      return Array.isArray(attempts) ? attempts.map(normalizePublishAttempt) : [];
    } catch (_error) {
      return [];
    }
  }

  function savePublishAttempts(attempts) {
    window.localStorage.setItem(
      PUBLISH_ATTEMPTS_KEY,
      JSON.stringify(attempts.map(normalizePublishAttempt)),
    );
  }

  function loadConnectedAccounts() {
    // api-client.js hydrates safe DTOs from SQLite when the localhost bridge
    // is active. Direct-file mode stores safe mock metadata only; no platform
    // secret values are stored, shown, or sent anywhere from the browser.
    const rawAccounts = window.localStorage.getItem(CONNECTED_ACCOUNTS_KEY);
    if (!rawAccounts) {
      return [];
    }

    try {
      const accounts = JSON.parse(rawAccounts);
      return Array.isArray(accounts)
        ? accounts.map(normalizeConnectedAccount).map(safeConnectedAccount)
        : [];
    } catch (_error) {
      return [];
    }
  }

  function saveConnectedAccounts(accounts) {
    const safeAccounts = accounts.map(normalizeConnectedAccount).map(safeConnectedAccount);
    window.localStorage.setItem(CONNECTED_ACCOUNTS_KEY, JSON.stringify(safeAccounts));
    return safeAccounts;
  }

  function loadConnectorAuditLogs() {
    const rawLogs = window.localStorage.getItem(CONNECTOR_AUDIT_KEY);
    if (!rawLogs) {
      return [];
    }

    try {
      const logs = JSON.parse(rawLogs);
      return Array.isArray(logs) ? logs.map(normalizeConnectorAuditLog) : [];
    } catch (_error) {
      return [];
    }
  }

  function saveConnectorAuditLogs(logs) {
    window.localStorage.setItem(CONNECTOR_AUDIT_KEY, JSON.stringify(logs.map(normalizeConnectorAuditLog)));
  }

  function appendConnectorAuditLog(platform, action, status, message, safeMetadata) {
    const entry = normalizeConnectorAuditLog({
      id: `connector-audit-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      platform,
      action,
      status,
      message,
      safeMetadata: safeMetadata || {},
      createdAt: new Date().toISOString(),
    });
    saveConnectorAuditLogs([entry, ...loadConnectorAuditLogs()].slice(0, 50));
    return entry;
  }

  function appendPublishAttempt(queueItem, scheduledPost, attemptType, attemptStatus, details) {
    const now = new Date().toISOString();
    const attempt = normalizePublishAttempt({
      id: `attempt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      publishQueueItemId: queueItem.id,
      scheduledPostId: scheduledPost?.id || queueItem.scheduledPostId,
      platform: queueItem.platform,
      attemptType,
      attemptStatus,
      startedAt: now,
      finishedAt: now,
      errorCode: details?.errorCode || "",
      errorMessage: details?.errorMessage || "",
      providerResponse: {
        source: "Local browser Publish Queue adapter",
        realPublishing: false,
        note: details?.note || "Local-only queue action. Future real publishing remains disabled.",
      },
      createdAt: now,
    });
    savePublishAttempts(loadPublishAttempts().concat(attempt));
    return attempt;
  }

  function appendCalendarAuditLog(scheduledPostId, action, notes, changedFields) {
    const rawLogs = window.localStorage.getItem(APPROVAL_LOGS_KEY);
    let logs = {};
    try {
      logs = rawLogs ? JSON.parse(rawLogs) : {};
    } catch (_error) {
      logs = {};
    }
    const entry = {
      id: `calendar-log-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
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
    window.localStorage.setItem(APPROVAL_LOGS_KEY, JSON.stringify(logs));
    return entry;
  }

  function cloneBrandProfile(profile) {
    return JSON.parse(JSON.stringify(profile));
  }

  function cloneMediaAssets(assets) {
    return JSON.parse(JSON.stringify(assets));
  }

  function normalizeMediaAsset(asset) {
    return {
      id: asset.id || `media-${Date.now()}`,
      title: asset.title || asset.originalFilename || "Untitled media",
      description: asset.description || "",
      originalFilename: asset.originalFilename || asset.fileName || "unknown-media",
      mediaType: asset.mediaType === "video" ? "video" : "image",
      fileSizeBytes: Number(asset.fileSizeBytes || 0),
      createdAt: asset.createdAt || new Date().toISOString(),
      tags: Array.isArray(asset.tags) ? asset.tags : [],
      serviceType: asset.serviceType || "",
      locationName: asset.locationName || "",
      city: asset.city || "",
      state: asset.state || "",
      projectDate: asset.projectDate || "",
      contentAngle: contentAngles.includes(asset.contentAngle) ? asset.contentAngle : "other",
      qualityRating:
        Number(asset.qualityRating) >= 1 && Number(asset.qualityRating) <= 5
          ? Number(asset.qualityRating)
          : "",
      usageStatus: mediaStatuses.includes(asset.usageStatus || asset.status)
        ? asset.usageStatus || asset.status
        : "new",
      status: mediaStatuses.includes(asset.usageStatus || asset.status)
        ? asset.usageStatus || asset.status
        : "new",
      notes: asset.notes || "",
      previewUrl: asset.previewUrl || "",
    };
  }

  function normalizeScheduledPost(post) {
    const metadata = post.scheduleMetadata || post.schedule_metadata || {};
    return {
      id: post.id || `scheduled-${Date.now()}`,
      generatedPostId: post.generatedPostId || post.generated_post_id || "",
      brandProfileId: post.brandProfileId || post.brand_profile_id || defaultBrandProfile.id,
      brandName: post.brandName || defaultBrandProfile.businessName,
      platform: platformIds.includes(post.platform) ? post.platform : "facebook",
      scheduledFor: post.scheduledFor || post.scheduled_for || new Date().toISOString(),
      timezone: post.timezone || defaultSettings.defaultTimezone,
      status: scheduledPostStatuses.includes(post.status) ? post.status : "scheduled",
      captionSnapshot: post.captionSnapshot || post.caption_snapshot || post.caption || "",
      mediaAssetIds: Array.isArray(post.mediaAssetIds || post.media_asset_ids)
        ? post.mediaAssetIds || post.media_asset_ids
        : [],
      platformAccountId: post.platformAccountId || post.platform_account_id || "",
      publishQueueItemId: post.publishQueueItemId || post.publish_queue_item_id || "",
      recurrenceRule: post.recurrenceRule || post.recurrence_rule || "",
      isRecurringTemplate: Boolean(post.isRecurringTemplate || post.is_recurring_template),
      userNotes: post.userNotes || post.user_notes || "",
      scheduleMetadata: {
        hook: metadata.hook || post.hook || "",
        headline: metadata.headline || post.headline || "",
        hashtags: Array.isArray(metadata.hashtags) ? metadata.hashtags : [],
        callToAction: metadata.callToAction || metadata.call_to_action || post.callToAction || "",
        safetyFlags: Array.isArray(metadata.safetyFlags || post.safetyFlags)
          ? metadata.safetyFlags || post.safetyFlags
          : [],
      },
      preflightSnapshot: post.preflightSnapshot || post.preflight_snapshot || {},
      createdAt: post.createdAt || post.created_at || new Date().toISOString(),
      updatedAt: post.updatedAt || post.updated_at || new Date().toISOString(),
      canceledAt: post.canceledAt || post.canceled_at || "",
    };
  }

  function normalizePublishQueueItem(item) {
    return {
      id: item.id || `queue-${Date.now()}`,
      scheduledPostId: item.scheduledPostId || item.scheduled_post_id || "",
      generatedPostId: item.generatedPostId || item.generated_post_id || "",
      brandProfileId: item.brandProfileId || item.brand_profile_id || defaultBrandProfile.id,
      platform: platformIds.includes(item.platform) ? item.platform : "facebook",
      queueStatus: queueStatuses.includes(item.queueStatus || item.queue_status)
        ? item.queueStatus || item.queue_status
        : "waiting",
      dueAt: item.dueAt || item.due_at || new Date().toISOString(),
      timezone: item.timezone || defaultSettings.defaultTimezone,
      priority: Number(item.priority || 100),
      preflightStatus: preflightStatuses.includes(item.preflightStatus || item.preflight_status)
        ? item.preflightStatus || item.preflight_status
        : "not_checked",
      preflightErrors: Array.isArray(item.preflightErrors || item.preflight_errors)
        ? item.preflightErrors || item.preflight_errors
        : [],
      preflightWarnings: Array.isArray(item.preflightWarnings || item.preflight_warnings)
        ? item.preflightWarnings || item.preflight_warnings
        : [],
      accountCheckStatus: item.accountCheckStatus || item.account_check_status || "not_checked",
      matchedSocialAccountId: item.matchedSocialAccountId || item.matched_social_account_id || "",
      accountWarnings: Array.isArray(item.accountWarnings || item.account_warnings)
        ? item.accountWarnings || item.account_warnings
        : [],
      accountErrors: Array.isArray(item.accountErrors || item.account_errors)
        ? item.accountErrors || item.account_errors
        : [],
      missingScopes: Array.isArray(item.missingScopes || item.missing_scopes)
        ? item.missingScopes || item.missing_scopes
        : [],
      requiresReauth: Boolean(item.requiresReauth || item.requires_reauth),
      connectionStatus: item.connectionStatus || item.connection_status || "not_connected",
      realPublishingEligible: Boolean(item.realPublishingEligible || item.real_publishing_eligible),
      manualExportEligible:
        typeof item.manualExportEligible === "boolean" ? item.manualExportEligible : false,
      mockPublishEligible:
        typeof item.mockPublishEligible === "boolean" ? item.mockPublishEligible : false,
      mockPublishEnabled: Boolean(item.mockPublishEnabled),
      manualExportRequired:
        typeof item.manualExportRequired === "boolean" ? item.manualExportRequired : true,
      lastCheckedAt: item.lastCheckedAt || item.last_checked_at || "",
      createdAt: item.createdAt || item.created_at || new Date().toISOString(),
      updatedAt: item.updatedAt || item.updated_at || new Date().toISOString(),
    };
  }

  function normalizePublishAttempt(attempt) {
    return {
      id: attempt.id || `attempt-${Date.now()}`,
      publishQueueItemId: attempt.publishQueueItemId || attempt.publish_queue_item_id || "",
      scheduledPostId: attempt.scheduledPostId || attempt.scheduled_post_id || "",
      platform: platformIds.includes(attempt.platform) ? attempt.platform : "facebook",
      attemptType: attempt.attemptType || attempt.attempt_type || "preflight",
      attemptStatus: attempt.attemptStatus || attempt.attempt_status || "started",
      startedAt: attempt.startedAt || attempt.started_at || new Date().toISOString(),
      finishedAt: attempt.finishedAt || attempt.finished_at || "",
      errorCode: attempt.errorCode || attempt.error_code || "",
      errorMessage: attempt.errorMessage || attempt.error_message || "",
      providerResponse: attempt.providerResponse || attempt.provider_response || {},
      createdAt: attempt.createdAt || attempt.created_at || new Date().toISOString(),
    };
  }

  function normalizeConnectedAccount(account) {
    const platform = platformIds.includes(account.platform) ? account.platform : "facebook";
    const config = platformConfig(platform);
    return {
      id: account.id || `mock-account-${platform}-${Date.now()}`,
      platform,
      displayName: account.displayName || `Mock ${config.label} Account`,
      username: account.username || `mock_${platform}`,
      accountType: account.accountType || config.accountType || "unknown",
      connectionStatus: account.connectionStatus || "connected",
      capabilities: Array.isArray(account.capabilities) ? account.capabilities : config.capabilities,
      grantedScopes: Array.isArray(account.grantedScopes) ? account.grantedScopes : config.requiredScopes,
      missingScopes: Array.isArray(account.missingScopes) ? account.missingScopes : config.missingScopes,
      missingPermissions: Array.isArray(account.missingPermissions)
        ? account.missingPermissions
        : Array.isArray(account.missingScopes)
          ? account.missingScopes
          : config.missingScopes,
      requiresReauth: Boolean(account.requiresReauth),
      healthStatus: account.healthStatus || "not_checked",
      healthWarnings: Array.isArray(account.healthWarnings) ? account.healthWarnings : [],
      healthErrors: Array.isArray(account.healthErrors) ? account.healthErrors : [],
      lastConnectedAt: account.lastConnectedAt || new Date().toISOString(),
      lastValidatedAt: account.lastValidatedAt || new Date().toISOString(),
      disconnectedAt: account.disconnectedAt || "",
      isMock: account.isMock !== false,
      storageMode: "placeholder_not_stored",
      createdAt: account.createdAt || new Date().toISOString(),
      updatedAt: account.updatedAt || new Date().toISOString(),
    };
  }

  function safeConnectedAccount(account) {
    return {
      id: account.id,
      platform: account.platform,
      displayName: account.displayName,
      username: account.username,
      accountType: account.accountType,
      connectionStatus: account.connectionStatus,
      capabilities: Array.isArray(account.capabilities) ? account.capabilities : [],
      grantedScopes: Array.isArray(account.grantedScopes) ? account.grantedScopes : [],
      missingScopes: Array.isArray(account.missingScopes) ? account.missingScopes : [],
      missingPermissions: Array.isArray(account.missingPermissions) ? account.missingPermissions : [],
      requiresReauth: Boolean(account.requiresReauth),
      healthStatus: account.healthStatus || "not_checked",
      healthWarnings: Array.isArray(account.healthWarnings) ? account.healthWarnings : [],
      healthErrors: Array.isArray(account.healthErrors) ? account.healthErrors : [],
      lastConnectedAt: account.lastConnectedAt,
      lastValidatedAt: account.lastValidatedAt,
      disconnectedAt: account.disconnectedAt || "",
      isMock: account.isMock !== false,
      storageMode: "placeholder_not_stored",
      createdAt: account.createdAt,
      updatedAt: account.updatedAt,
    };
  }

  function normalizeConnectorAuditLog(log) {
    return {
      id: log.id || `connector-audit-${Date.now()}`,
      platform: platformIds.includes(log.platform) ? log.platform : "facebook",
      action: log.action || "mock_connect",
      status: log.status || "succeeded",
      message: log.message || "Local connector event recorded.",
      safeMetadata: log.safeMetadata || log.safe_metadata || {},
      createdAt: log.createdAt || log.created_at || new Date().toISOString(),
    };
  }

  function getElement(id) {
    return document.getElementById(id);
  }

  function setMessage(kind, text) {
    const error = getElement("settings-error");
    const success = getElement("settings-success");
    if (!error || !success) {
      return;
    }

    error.hidden = kind !== "error";
    success.hidden = kind !== "success";
    error.textContent = kind === "error" ? text : "";
    success.textContent = kind === "success" ? text : "";
  }

  function setBrandMessage(kind, text) {
    const error = getElement("brand-error");
    const success = getElement("brand-success");
    if (!error || !success) {
      return;
    }

    error.hidden = kind !== "error";
    success.hidden = kind !== "success";
    error.textContent = kind === "error" ? text : "";
    success.textContent = kind === "success" ? text : "";
  }

  function setMediaError(text) {
    const error = getElement("media-error-state");
    if (!error) {
      return;
    }

    error.hidden = !text;
    error.textContent = text || "";
  }

  function setMediaMetadataMessage(kind, text) {
    const error = getElement("media-metadata-error");
    const success = getElement("media-metadata-success");
    if (!error || !success) {
      return;
    }

    error.hidden = kind !== "error";
    success.hidden = kind !== "success";
    error.textContent = kind === "error" ? text : "";
    success.textContent = kind === "success" ? text : "";
  }

  function setConnectedMessage(kind, text) {
    const error = getElement("connected-action-error");
    const success = getElement("connected-action-message");
    if (!error || !success) {
      return;
    }

    error.hidden = kind !== "error";
    success.hidden = kind !== "success";
    error.textContent = kind === "error" ? text : "";
    success.textContent = kind === "success" ? text : "";
  }

  function formatFileSize(bytes) {
    if (!bytes) {
      return "0 B";
    }
    if (bytes < 1024 * 1024) {
      return `${Math.round(bytes / 1024)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatDate(value) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return "Unknown date";
    }

    return parsed.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }

  function formatStatus(status) {
    return status.replaceAll("_", " ");
  }

  function diagnosticResult(id, label, status, summary, details, recommendedAction, checkedAt) {
    return {
      id,
      label,
      status,
      summary: redactDiagnosticText(summary),
      details: redactDiagnosticText(details),
      recommendedAction: redactDiagnosticText(recommendedAction),
      checkedAt,
    };
  }

  function diagnosticsSection(id, label, results) {
    return { id, label, results };
  }

  function diagnosticStatusSummary(results) {
    return ["healthy", "warning", "error", "disabled", "unknown"].reduce((summary, status) => {
      summary[status] = results.filter((result) => result.status === status).length;
      return summary;
    }, {});
  }

  function diagnosticStatusClass(status) {
    if (status === "healthy") return "safe";
    if (status === "error") return "blocked";
    if (status === "disabled") return "mock-mode";
    return "needs-review";
  }

  function redactDiagnosticText(value) {
    return String(value ?? "")
      .replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]")
      .replace(/(access[_-]?token|refresh[_-]?token|client[_-]?secret|authorization[_-]?code|id[_-]?token|api[_-]?key)(\s*[:=]\s*)([^\s,;]+)/gi, "$1$2[REDACTED]")
      .replace(/(Authorization\s*:\s*)([^\n]+)/gi, "$1[REDACTED]")
      .replace(/(META|GOOGLE|TIKTOK|LINKEDIN|X)_CLIENT_SECRET(\s*[:=]\s*)([^\s,;]+)/gi, "$1_CLIENT_SECRET$2[REDACTED]");
  }

  function recordFriendlyError(error, context = "app") {
    const message = redactDiagnosticText(error?.message || String(error || "Unknown local app error."));
    const entry = {
      id: `error-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      context,
      message,
      createdAt: new Date().toISOString(),
    };
    const errors = [entry, ...loadBrowserArray(RECENT_ERRORS_STORAGE_KEY)].slice(0, 25);
    window.localStorage.setItem(RECENT_ERRORS_STORAGE_KEY, JSON.stringify(errors));
    return entry;
  }

  function checklistStatusClass(status) {
    if (status === "completed") return "safe";
    if (status === "needs_attention") return "blocked";
    if (status === "skipped") return "mock-mode";
    return "needs-review";
  }

  function renderSetupChecklist() {
    const container = getElement("home-setup-checklist");
    if (!container) return;
    const checklist = activeApiBridge()
      ? loadSetupChecklist()
      : computedBrowserChecklist();
    window.localStorage.setItem(SETUP_CHECKLIST_KEY, JSON.stringify(checklist));
    container.innerHTML = checklist
      .map((item) => `
        <article class="setup-checklist-item">
          <span class="card-status ${checklistStatusClass(item.status)}">${escapeHtml(formatStatus(item.status))}</span>
          <strong>${escapeHtml(item.label)}</strong>
          <p>${escapeHtml(checklistHelpText(item))}</p>
        </article>
      `)
      .join("");
  }

  function pluralize(count, singular, plural = `${singular}s`) {
    return `${count} ${count === 1 ? singular : plural}`;
  }

  function draftTitle(draft) {
    return draft?.headline || draft?.hook || draft?.caption?.slice(0, 54) || "Untitled draft";
  }

  function controlTaskMarkup(task) {
    const statusClass = task.statusClass || "local-only";
    const status = task.status || "Local Only";
    const meta = Array.isArray(task.meta) && task.meta.length
      ? `<div class="control-task-meta">${task.meta.map((item) => `<span class="card-status ${escapeHtml(item.className || "mock-mode")}">${escapeHtml(item.label)}</span>`).join("")}</div>`
      : "";
    const action = task.href
      ? `<a class="${task.primary ? "primary-button" : "secondary-button"} link-button" href="${escapeHtml(task.href)}" aria-label="${escapeHtml(task.actionLabel || `Open ${task.title}`)}">${escapeHtml(task.actionText || "Open")}</a>`
      : "";
    return `
      <article class="control-task-row${task.empty ? " control-task-empty" : ""}">
        <div>
          <span class="card-status ${escapeHtml(statusClass)}">${escapeHtml(status)}</span>
          <strong>${escapeHtml(task.title)}</strong>
          <p>${escapeHtml(task.copy || "")}</p>
          ${meta}
        </div>
        ${action}
      </article>
    `;
  }

  function setControlTaskList(id, tasks, emptyTask) {
    const container = getElement(id);
    if (!container) return;
    const rows = tasks.length ? tasks : [{ ...emptyTask, empty: true }];
    container.innerHTML = rows.map(controlTaskMarkup).join("");
  }

  function setControlText(id, value) {
    const element = getElement(id);
    if (element) {
      element.textContent = value;
    }
  }

  function activeScheduledPost(post) {
    return !["canceled", "completed", "failed"].includes(post.status);
  }

  function controlCenterSnapshot() {
    const settings = settingsAdapter.load();
    const onboarding = onboardingAdapter.loadLocal();
    const brand = brandBrainAdapter.loadWithoutFallback();
    const media = mediaLibraryAdapter.load();
    const drafts = loadBrowserArray("local-social-ai-manager.drafts");
    const scheduled = loadScheduledPosts();
    const queue = loadPublishQueueItems();
    const engagement = loadBrowserArray("local-social-ai-manager.engagementItems");
    const suggestions = loadBrowserArray("local-social-ai-manager.replySuggestions");
    const analytics = loadBrowserArray("local-social-ai-manager.analyticsSnapshots");
    const reports = loadBrowserArray("local-social-ai-manager.weeklyReports");
    const safety = computeSafetyState();
    const now = new Date();
    const weekEnd = addDays(now, 7);
    const reviewDrafts = drafts.filter((draft) => ["needs_review", "revision_requested"].includes(draft.approvalStatus));
    const activeScheduledDraftIds = new Set(scheduled.filter(activeScheduledPost).map((post) => post.generatedPostId));
    const approvedUnscheduledDrafts = drafts.filter(
      (draft) => draft.approvalStatus === "approved" && !activeScheduledDraftIds.has(draft.id),
    );
    const criticalDrafts = drafts.filter((draft) =>
      (Array.isArray(draft.safetyFlags) ? draft.safetyFlags : []).some((flag) => criticalQueueFlags.has(flag)),
    );
    const upcomingPosts = scheduled
      .filter((post) => activeScheduledPost(post))
      .filter((post) => {
        const scheduledFor = new Date(post.scheduledFor);
        return !Number.isNaN(scheduledFor.getTime()) && scheduledFor >= now && scheduledFor <= weekEnd;
      })
      .sort((left, right) => new Date(left.scheduledFor) - new Date(right.scheduledFor));
    const readyQueue = queue.filter((item) => item.queueStatus === "ready");
    const blockedQueue = queue.filter((item) => ["blocked", "failed"].includes(item.queueStatus));
    const waitingQueue = queue.filter((item) => item.queueStatus === "waiting");
    const engagementNeedingReply = engagement.filter((item) =>
      ["new", "needs_reply", "reply_suggested"].includes(item.status) && item.requiresResponse !== false,
    );
    const urgentEngagement = engagement.filter((item) =>
      item.priority === "urgent" && !["archived", "spam", "replied_manually"].includes(item.status),
    );
    const pendingSuggestions = suggestions.filter((suggestion) => ["generated", "edited"].includes(suggestion.status));
    const mediaReady = media.filter((asset) =>
      ["ready_for_generation", "reviewed", "new"].includes(asset.status || asset.usageStatus),
    );
    const latestReport = reports
      .slice()
      .sort((left, right) => new Date(right.createdAt || right.weekEndDate || 0) - new Date(left.createdAt || left.weekEndDate || 0))[0];

    return {
      settings,
      onboarding,
      brand,
      media,
      drafts,
      scheduled,
      queue,
      analytics,
      reports,
      safety,
      reviewDrafts,
      approvedUnscheduledDrafts,
      criticalDrafts,
      upcomingPosts,
      readyQueue,
      blockedQueue,
      waitingQueue,
      engagementNeedingReply,
      urgentEngagement,
      pendingSuggestions,
      mediaReady,
      latestReport,
    };
  }

  function recommendedControlAction(snapshot) {
    if (!["completed", "skipped"].includes(snapshot.onboarding.status)) {
      return {
        title: "Continue onboarding",
        copy: "Finish the guided setup so Brand Brain, safety defaults, and local workflow basics are in place.",
        href: "#onboarding",
        actionText: "Continue setup",
        status: "Setup",
        statusClass: "needs-review",
      };
    }
    if (!snapshot.brand) {
      return {
        title: "Finish Brand Brain",
        copy: "Add the business identity before generating real draft ideas.",
        href: "#brand",
        actionText: "Open Brand Brain",
        status: "Needs setup",
        statusClass: "needs-review",
      };
    }
    if (!snapshot.media.length) {
      return {
        title: "Add your first media",
        copy: "Upload or import job photos/videos so generated content can be grounded in real work.",
        href: "#media",
        actionText: "Open Media Library",
        status: "Local media",
        statusClass: "local-only",
      };
    }
    if (!snapshot.drafts.length) {
      return {
        title: "Generate your first draft",
        copy: "Use mock AI generation to create draft content. Generated posts start as needs_review.",
        href: "#generate",
        actionText: "Generate draft",
        status: "Mock Data",
        statusClass: "mock-mode",
      };
    }
    if (snapshot.reviewDrafts.length) {
      return {
        title: "Review draft approvals",
        copy: `${pluralize(snapshot.reviewDrafts.length, "draft")} need human review before scheduling.`,
        href: "#drafts",
        actionText: "Review drafts",
        status: "Approval Required",
        statusClass: "needs-review",
      };
    }
    if (snapshot.approvedUnscheduledDrafts.length) {
      return {
        title: "Schedule approved drafts",
        copy: `${pluralize(snapshot.approvedUnscheduledDrafts.length, "approved draft")} can be placed on the local calendar.`,
        href: "#drafts",
        actionText: "Schedule drafts",
        status: "Local Only",
        statusClass: "local-only",
      };
    }
    if (snapshot.readyQueue.length || snapshot.blockedQueue.length) {
      return {
        title: "Check Publish Queue",
        copy: `${snapshot.readyQueue.length} ready and ${snapshot.blockedQueue.length} blocked queue item(s). Manual Export is the safe posting path.`,
        href: "#queue",
        actionText: "Open queue",
        status: "Manual Export",
        statusClass: "mock-mode",
      };
    }
    if (snapshot.engagementNeedingReply.length) {
      return {
        title: "Review Engagement Inbox",
        copy: `${pluralize(snapshot.engagementNeedingReply.length, "item")} may need a local reply decision. Replies are not sent automatically.`,
        href: "#engagement",
        actionText: "Open inbox",
        status: "Local Approval",
        statusClass: "needs-review",
      };
    }
    return {
      title: "Review analytics and plan next week",
      copy: "Use local analytics, weekly reports, and AI memory to decide what content to create next.",
      href: "#analytics",
      actionText: "Open analytics",
      status: "Local Learning",
      statusClass: "local-only",
    };
  }

  function renderControlCenter() {
    const snapshot = controlCenterSnapshot();
    const next = recommendedControlAction(snapshot);
    const nextLink = getElement("control-next-action");
    if (nextLink) {
      nextLink.href = next.href;
      nextLink.textContent = next.actionText;
      nextLink.setAttribute("aria-label", next.actionLabel || next.actionText);
    }
    setControlText("control-next-heading", next.title);
    setControlText("control-next-copy", next.copy);
    const status = getElement("control-next-status");
    if (status) {
      status.className = `card-status ${next.statusClass}`;
      status.textContent = next.status;
    }

    setControlText("control-summary-drafts", String(snapshot.reviewDrafts.length));
    setControlText("control-summary-scheduled", String(snapshot.upcomingPosts.length));
    setControlText("control-summary-queue", String(snapshot.readyQueue.length + snapshot.blockedQueue.length));
    setControlText("control-summary-engagement", String(snapshot.engagementNeedingReply.length));

    const needs = [];
    if (snapshot.settings.emergencyPauseEnabled) {
      needs.push({
        title: "Emergency pause is enabled",
        copy: "Scheduling, queue readiness, mock publishing, manual export packages, and future real actions are blocked.",
        href: "#safety",
        actionText: "Open Safety Center",
        status: "Paused",
        statusClass: "needs-review",
        primary: true,
      });
    }
    if (snapshot.criticalDrafts.length) {
      needs.push({
        title: "Critical draft safety flags",
        copy: `${pluralize(snapshot.criticalDrafts.length, "draft")} have critical flags that block scheduling and future publishing.`,
        href: "#drafts",
        actionText: "Review flags",
        status: "Blocked",
        statusClass: "needs-review",
      });
    }
    if (snapshot.reviewDrafts.length) {
      needs.push({
        title: "Drafts need review",
        copy: `${snapshot.reviewDrafts.slice(0, 2).map(draftTitle).join(", ")}${snapshot.reviewDrafts.length > 2 ? ", and more" : ""}`,
        href: "#drafts",
        actionText: "Review",
        status: "Approval Required",
        statusClass: "needs-review",
        meta: [{ label: pluralize(snapshot.reviewDrafts.length, "draft"), className: "needs-review" }],
      });
    }
    if (snapshot.blockedQueue.length) {
      needs.push({
        title: "Publish Queue has blocked items",
        copy: "Open blocked local queue items to see preflight errors, account warnings, or emergency pause messages.",
        href: "#queue",
        actionText: "Open queue",
        status: "Blocked",
        statusClass: "needs-review",
        meta: [{ label: pluralize(snapshot.blockedQueue.length, "item"), className: "needs-review" }],
      });
    }
    if (snapshot.urgentEngagement.length) {
      needs.push({
        title: "Urgent engagement needs review",
        copy: "Review urgent mock/manual engagement locally. No replies are sent automatically.",
        href: "#engagement",
        actionText: "Review inbox",
        status: "Local Approval",
        statusClass: "needs-review",
        meta: [{ label: pluralize(snapshot.urgentEngagement.length, "urgent item"), className: "needs-review" }],
      });
    }

    const ready = [];
    if (snapshot.approvedUnscheduledDrafts.length) {
      ready.push({
        title: "Approved drafts are ready to schedule",
        copy: `${pluralize(snapshot.approvedUnscheduledDrafts.length, "draft")} can move to the local calendar if preflight stays safe.`,
        href: "#drafts",
        actionText: "Schedule",
        status: "Local Only",
        statusClass: "local-only",
      });
    }
    if (snapshot.readyQueue.length) {
      ready.push({
        title: "Manual export packages are ready",
        copy: `${pluralize(snapshot.readyQueue.length, "queue item")} can be exported manually after review. This is not automatic publishing.`,
        href: "#queue",
        actionText: "Manual export",
        status: "Manual Export",
        statusClass: "mock-mode",
      });
    }
    if (snapshot.pendingSuggestions.length) {
      ready.push({
        title: "Reply suggestions await local approval",
        copy: `${pluralize(snapshot.pendingSuggestions.length, "suggestion")} can be edited, approved locally, rejected, or escalated.`,
        href: "#engagement",
        actionText: "Review replies",
        status: "Local Approval",
        statusClass: "needs-review",
      });
    }
    if (snapshot.mediaReady.length) {
      ready.push({
        title: "Media is ready for content ideas",
        copy: `${pluralize(snapshot.mediaReady.length, "media item")} can support new mock drafts.`,
        href: "#generate",
        actionText: "Generate",
        status: "Mock Data",
        statusClass: "mock-mode",
      });
    }

    const week = [];
    snapshot.upcomingPosts.slice(0, 3).forEach((post) => {
      week.push({
        title: post.scheduleMetadata?.hook || post.scheduleMetadata?.headline || `${formatStatus(post.platform)} scheduled post`,
        copy: `${formatDateTime(post.scheduledFor)} · ${formatStatus(post.status)} · ${post.captionSnapshot?.slice(0, 90) || "Caption snapshot saved."}`,
        href: "#calendar",
        actionText: "View",
        status: post.platform || "Calendar",
        statusClass: "local-only",
      });
    });
    if (snapshot.latestReport) {
      week.push({
        title: "Latest weekly report is available",
        copy: snapshot.latestReport.summary || "Review local wins, concerns, and recommendations for next week.",
        href: "#analytics",
        actionText: "Open report",
        status: "Weekly Reports",
        statusClass: "local-only",
      });
    }
    if (snapshot.analytics.length) {
      week.push({
        title: "Analytics are ready to review",
        copy: `${pluralize(snapshot.analytics.length, "snapshot")} stored locally. Mock and manual data remain labeled by source.`,
        href: "#analytics",
        actionText: "Review",
        status: "Local Learning",
        statusClass: "local-only",
      });
    }
    if (snapshot.waitingQueue.length && !snapshot.upcomingPosts.length) {
      week.push({
        title: "Queue has waiting local items",
        copy: `${pluralize(snapshot.waitingQueue.length, "item")} are waiting for due time or preflight. Local jobs never publish externally.`,
        href: "#queue",
        actionText: "Open queue",
        status: "Local Only",
        statusClass: "local-only",
      });
    }

    const safetyRows = [
      {
        title: snapshot.settings.emergencyPauseEnabled ? "Emergency pause is on" : "Emergency pause is off",
        copy: snapshot.settings.emergencyPauseEnabled
          ? "Automation and queue readiness are paused until you disable it in Safety Center."
          : "Safe local actions can continue. Use Safety Center if anything feels off.",
        href: "#safety",
        actionText: "Safety Center",
        status: snapshot.settings.emergencyPauseEnabled ? "Paused" : "Ready",
        statusClass: snapshot.settings.emergencyPauseEnabled ? "needs-review" : "safe",
      },
      {
        title: "Real publishing is disabled",
        copy: "Publish Queue supports Manual Export and mock/demo actions only. No real social APIs are called.",
        href: "#queue",
        actionText: "Publish Queue",
        status: "Disabled",
        statusClass: "needs-review",
      },
      {
        title: "Replies are not sent automatically",
        copy: "AI can suggest replies, but approval is local only and does not send to platforms.",
        href: "#engagement",
        actionText: "Engagement",
        status: "Approval Required",
        statusClass: "needs-review",
      },
    ];

    setControlTaskList("control-needs-list", needs, {
      title: "Nothing urgent right now",
      copy: "No blocked queue items, critical draft flags, urgent engagement, or emergency pause are active.",
      status: "All clear",
      statusClass: "safe",
      href: "#diagnostics",
      actionText: "Diagnostics",
    });
    setControlTaskList("control-ready-list", ready, {
      title: "No ready local tasks yet",
      copy: "Generate drafts, approve them, schedule them, or run mock engagement to create your next workflow item.",
      status: "Next step",
      statusClass: "mock-mode",
      href: "#generate",
      actionText: "Generate",
    });
    setControlTaskList("control-week-list", week, {
      title: "No weekly items yet",
      copy: "Schedule an approved draft or add analytics to populate this week view.",
      status: "Local Only",
      statusClass: "local-only",
      href: "#calendar",
      actionText: "Calendar",
    });
    setControlTaskList("control-safety-list", safetyRows, {
      title: "Safety status unavailable",
      copy: "Open Safety Center or Diagnostics to refresh local safety checks.",
      status: "Needs check",
      statusClass: "needs-review",
      href: "#safety",
      actionText: "Open",
    });
    renderSetupChecklist();
  }

  function checklistHelpText(item) {
    const copy = {
      brand_profile_created: "Add the first Brand Brain profile before generating real drafts.",
      local_data_ready: "Use a stable local folder, not a temporary download or cache folder.",
      safety_settings_confirmed: "Approval stays required and real publishing remains disabled.",
      media_added: "Upload or import at least one real photo or video when ready.",
      first_draft_generated: "Generate a mock draft and save it as needs_review.",
      first_draft_approved: "Approve a reviewed draft before scheduling.",
      first_post_scheduled: "Put an approved draft on the local calendar.",
      manual_export_tested: "Create or record a manual export before relying on the queue.",
      analytics_added: "Add manual metrics or generate demo analytics.",
      social_setup_reviewed: "Mock-connect or review setup. Real accounts are optional.",
    };
    return copy[item.id] || "Complete this setup step when ready.";
  }

  function setOnboardingMessage(kind, text) {
    const error = getElement("onboarding-error");
    const success = getElement("onboarding-success");
    if (!error || !success) return;
    error.hidden = kind !== "error";
    success.hidden = kind !== "success";
    error.textContent = kind === "error" ? text : "";
    success.textContent = kind === "success" ? text : "";
  }

  function renderOnboarding() {
    const view = getElement("onboarding-view");
    if (!view) return;
    const state = onboardingAdapter.loadLocal();
    const settings = settingsAdapter.load();
    getElement("onboarding-local-data-directory").textContent = state.localDataDirectory || settings.localDataDirectory;
    getElement("onboarding-local-data-exists").textContent = state.localDataDirectoryExists ? "Yes" : "Not yet";
    getElement("onboarding-local-data-writable").textContent = state.localDataDirectoryWritable ? "Yes" : "Needs attention";

    const progress = getElement("onboarding-progress");
    if (progress) {
      progress.innerHTML = (state.steps || defaultOnboardingState.steps)
        .map((step) => `<li data-status="${escapeHtml(step.status)}">${escapeHtml(step.label || formatStatus(step.id))}</li>`)
        .join("");
    }
  }

  function collectOnboardingBrandProfile() {
    const cta = getElement("onboarding-commonCTA").value.trim();
    return {
      businessName: getElement("onboarding-businessName").value.trim(),
      industry: getElement("onboarding-industry").value.trim(),
      description: getElement("onboarding-description").value.trim(),
      services: listFromValue(getElement("onboarding-services").value),
      serviceAreas: listFromValue(getElement("onboarding-serviceAreas").value),
      brandVoice: getElement("onboarding-brandVoice").value.trim(),
      commonCTAs: cta ? [cta] : [],
      website: getElement("onboarding-website").value.trim(),
      phone: getElement("onboarding-phone").value.trim(),
      email: getElement("onboarding-email").value.trim(),
      approvalRules: ["Owner approves every generated draft before scheduling."],
      safetyRules: [
        "Never invent testimonials.",
        "Never invent prices, guarantees, or availability.",
      ],
    };
  }

  function listFromValue(value) {
    return String(value || "")
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function collectOnboardingPlatforms() {
    return Array.from(document.querySelectorAll('input[name="onboarding-platforms"]:checked'))
      .map((input) => input.value)
      .filter((value) => platformIds.includes(value));
  }

  function validateOnboardingPayload(payload) {
    if (!payload.brandProfile.businessName) {
      return "Add a business name before completing onboarding.";
    }
    if (!payload.brandProfile.services.length) {
      return "Add at least one service before completing onboarding.";
    }
    if (!payload.brandProfile.serviceAreas.length) {
      return "Add at least one service area before completing onboarding.";
    }
    if (!payload.settings.defaultPlatformTargets.length) {
      return "Choose at least one default platform.";
    }
    if (payload.brandProfile.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(payload.brandProfile.email)) {
      return "Enter a valid public business email address or leave email blank.";
    }
    return "";
  }

  async function createOnboardingDemoDraft() {
    const bridge = activeApiBridge();
    const platforms = collectOnboardingPlatforms();
    const platform = platforms[0] || "facebook";
    if (bridge) {
      await bridge.sync();
      const brand = brandBrainAdapter.load();
      const bundle = await bridge.request("/api/content-generation", {
        method: "POST",
        body: {
          input: {
            brandProfileId: brand.id,
            contentGoal: "build_trust",
            contentAngle: "educational",
            selectedPlatforms: [platform],
            selectedMediaIds: [],
            userInstructions: "Create a clearly labeled first onboarding demo draft.",
          },
        },
      });
      await bridge.request("/api/drafts/save-generated", {
        method: "POST",
        body: {
          bundle,
          selected_platforms: [platform],
          save_request_id: `onboarding-demo-${Date.now()}`,
        },
      });
      await bridge.sync();
      return;
    }

    const brand = brandBrainAdapter.load();
    const now = new Date().toISOString();
    const draft = {
      id: `onboarding-demo-draft-${Date.now()}`,
      brandProfileId: brand.id,
      platform,
      headline: "First local demo draft",
      hook: `${brand.businessName || "Your business"}: a simple setup post.`,
      caption: `Mock onboarding draft for ${brand.businessName || "your business"}. Use this only as a starting point and review before scheduling.`,
      hashtags: ["#LocalBusiness", "#DemoDraft"],
      mediaAssetIds: [],
      approvalStatus: "needs_review",
      generationProvider: "mock",
      safetyFlags: [],
      createdAt: now,
      updatedAt: now,
      saveRequestId: `onboarding-demo-${now}`,
    };
    const drafts = loadBrowserArray("local-social-ai-manager.drafts");
    window.localStorage.setItem("local-social-ai-manager.drafts", JSON.stringify(drafts.concat(draft)));
  }

  async function completeOnboarding() {
    const payload = {
      brandProfile: collectOnboardingBrandProfile(),
      settings: {
        localDataDirectory: settingsAdapter.load().localDataDirectory,
        defaultPlatformTargets: collectOnboardingPlatforms(),
        requireApprovalBeforePublishing: true,
        requireApprovalBeforeReplying: true,
        emergencyPauseEnabled: false,
        automationLevel: "approval_queue",
      },
      completedSteps: onboardingStepIds,
      skippedSteps: [],
    };
    const validationMessage = validateOnboardingPayload(payload);
    if (validationMessage) {
      setOnboardingMessage("error", validationMessage);
      return;
    }

    try {
      await onboardingAdapter.complete(payload);
      if (!activeApiBridge()) {
        brandBrainAdapter.saveLocal(payload.brandProfile);
        settingsAdapter.saveLocal({ ...settingsAdapter.load(), ...payload.settings });
      }
      if (onboardingDemoDraftRequested && window.confirm("Save one mock onboarding draft as needs_review?")) {
        await createOnboardingDemoDraft();
      }
      renderSetupChecklist();
      renderOnboarding();
      setOnboardingMessage("success", "Setup complete. You can now generate, review, schedule, and manually export local content.");
      window.location.hash = "#home";
    } catch (error) {
      setOnboardingMessage("error", error.message || "Onboarding could not be completed.");
    }
  }

  async function skipOnboarding() {
    if (!window.confirm("Skip onboarding? You can restart it from Settings, and the app will remain usable.")) {
      return;
    }
    try {
      await onboardingAdapter.skip("Owner skipped first-run onboarding.");
      renderSetupChecklist();
      renderOnboarding();
      setOnboardingMessage("success", "Onboarding skipped. You can restart it from Settings.");
      window.location.hash = "#home";
    } catch (error) {
      setOnboardingMessage("error", error.message || "Onboarding could not be skipped.");
    }
  }

  async function restartOnboarding() {
    try {
      await onboardingAdapter.restart();
      renderSetupChecklist();
      renderOnboarding();
      setMessage("success", "Onboarding restarted. Open Onboarding to continue.");
      window.location.hash = "#onboarding";
    } catch (error) {
      setMessage("error", error.message || "Onboarding could not be restarted.");
    }
  }

  function maybeRouteToOnboarding() {
    const state = onboardingAdapter.loadLocal();
    const currentRoute = routeFromHash();
    if (
      !window.location.hash &&
      !["completed", "skipped"].includes(state.status) &&
      currentRoute === "home"
    ) {
      window.location.hash = "#onboarding";
    }
  }

  function setSafetyMessage(kind, text) {
    const success = getElement("safety-message");
    const error = getElement("safety-error");
    if (!success || !error) return;
    success.hidden = kind !== "success";
    error.hidden = kind !== "error";
    success.textContent = kind === "success" ? text : "";
    error.textContent = kind === "error" ? text : "";
  }

  function safetyLabel(value) {
    return String(value || "none").replaceAll("_", " ");
  }

  function safetyStatusBadge(status) {
    if (["blocked", "paused", "disabled_by_policy", "needs_attention"].includes(status)) {
      return "needs-review";
    }
    if (["local_only", "local_approval_only", "completed"].includes(status)) {
      return "local-only";
    }
    return "mock-mode";
  }

  function renderSafetyList(elementId, values) {
    const element = getElement(elementId);
    if (!element) return;
    element.innerHTML = values.length
      ? values.map((value) => `<li>${escapeHtml(safetyLabel(value))}</li>`).join("")
      : "<li>None</li>";
  }

  function renderSafetyCenter(state = safetyCenterAdapter.loadLocal()) {
    const view = getElement("safety-view");
    if (!view) return;
    const paused = Boolean(state.emergencyPause?.enabled);
    const toggle = getElement("safety-emergency-toggle");
    if (toggle) {
      toggle.checked = paused;
    }
    getElement("safety-emergency-state").textContent = paused ? "Paused" : "Active";
    getElement("safety-emergency-enabled-at").textContent = state.emergencyPause?.enabledAt || "-";
    getElement("safety-emergency-enabled-by").textContent = state.emergencyPause?.enabledBy || "-";
    getElement("safety-emergency-reason").textContent = state.emergencyPause?.reason || "-";

    getElement("safety-publishing-status").innerHTML = `
      <span class="status-dot blocked" aria-hidden="true"></span>
      <strong>Publishing safety status</strong>
      <span>${escapeHtml(state.publishingSafety?.message || "Real publishing remains disabled")}</span>
    `;
    getElement("safety-reply-status").innerHTML = `
      <span class="status-dot warning" aria-hidden="true"></span>
      <strong>Reply safety status</strong>
      <span>${escapeHtml(state.replySafety?.message || "Replies are not sent automatically")}</span>
    `;
    getElement("safety-queue-status").innerHTML = `
      <span class="status-dot ${paused || state.queueProcessing?.disabled ? "blocked" : "safe"}" aria-hidden="true"></span>
      <strong>Queue processing status</strong>
      <span>${escapeHtml(state.queueProcessing?.disabled ? "Disabled locally" : safetyLabel(state.queueProcessing?.status || "local_only"))}</span>
    `;

    const automationSelect = getElement("safety-automation-level");
    if (automationSelect) {
      automationSelect.value = state.automationLevel || "approval_queue";
    }
    getElement("safety-automation-levels").innerHTML = (state.automationLevels || [])
      .map((level) => `
        <article class="safety-row">
          <span class="card-status ${level.locked ? "needs-review" : level.current ? "local-only" : "mock-mode"}">${escapeHtml(level.current ? "current" : level.locked ? "locked" : "available")}</span>
          <div><strong>${escapeHtml(level.label)}</strong><p>${escapeHtml(level.note || "")}</p></div>
        </article>
      `)
      .join("");

    const connected = state.connectedAccountSafety || {};
    getElement("safety-connected-status").innerHTML = `
      <article class="safety-row"><strong>Connected or limited</strong><span>${escapeHtml(String(connected.connectedOrLimited || 0))}</span></article>
      <article class="safety-row"><strong>Requires reauth</strong><span>${escapeHtml(String(connected.requiresReauth || 0))}</span></article>
      <article class="safety-row"><strong>Tokens exposed</strong><span>${connected.tokensExposed ? "Needs attention" : "No"}</span></article>
    `;

    const flags = state.criticalSafetyFlags || {};
    const flagRows = Object.entries(flags.byFlag || {});
    getElement("safety-critical-flags").innerHTML = flagRows.length
      ? flagRows.map(([flag, count]) => `<article class="safety-row"><strong>${escapeHtml(safetyLabel(flag))}</strong><span>${escapeHtml(String(count))}</span></article>`).join("")
      : '<p class="result-meta">No critical safety flags found in local draft records.</p>';

    const pending = state.pendingApprovals || {};
    getElement("safety-pending-approvals").innerHTML = `
      <article class="safety-row"><strong>Drafts needing review</strong><span>${escapeHtml(String(pending.draftsNeedingReview || 0))}</span></article>
      <article class="safety-row"><strong>Reply suggestions needing review</strong><span>${escapeHtml(String(pending.replySuggestionsNeedingReview || 0))}</span></article>
      <article class="safety-row"><strong>Queue items needing attention</strong><span>${escapeHtml(String(pending.queueItemsNeedingAttention || 0))}</span></article>
    `;

    renderSafetyList("safety-blocked-actions", state.blockedActions || defaultSafetyCenterState.blockedActions);
    renderSafetyList("safety-allowed-actions", state.allowedActions || defaultSafetyCenterState.allowedActions);

    getElement("safety-kill-actions").innerHTML = (state.killSwitchActions || defaultSafetyCenterState.killSwitchActions)
      .map((action) => `
        <article class="safety-kill-action">
          <div>
            <h3>${escapeHtml(action.label)}</h3>
            <p>${escapeHtml(action.description)}</p>
            <p class="result-meta">Type: ${escapeHtml(action.confirmationPhrase)}</p>
          </div>
          <button class="secondary-button" type="button" data-safety-kill-action="${escapeHtml(action.id)}">Run</button>
        </article>
      `)
      .join("");

    const logs = state.auditLogs || [];
    getElement("safety-audit-log").innerHTML = logs.length
      ? logs.map((entry) => `
        <article class="safety-audit-entry">
          <strong>${escapeHtml(safetyLabel(entry.action))}</strong>
          <span>${escapeHtml(entry.actorType || "user")} | ${escapeHtml(formatDateTime(entry.createdAt))}</span>
          <p>${escapeHtml(JSON.stringify(entry.details || {}))}</p>
        </article>
      `).join("")
      : '<p class="result-meta">No safety audit log entries yet.</p>';
  }

  async function refreshSafetyCenter() {
    try {
      const state = await safetyCenterAdapter.refresh();
      renderSafetyCenter(state);
      setSafetyMessage("success", "Safety Center refreshed.");
    } catch (error) {
      setSafetyMessage("error", error.message || "Safety Center could not refresh.");
    }
  }

  async function toggleEmergencyPause(event) {
    const enabled = Boolean(event.target.checked);
    const phrase = enabled ? "ENABLE PAUSE" : "DISABLE PAUSE";
    const typed = window.prompt(`Type ${phrase} to ${enabled ? "enable" : "disable"} emergency pause.`);
    if (typed !== phrase) {
      event.target.checked = !enabled;
      setSafetyMessage("error", "Emergency pause change canceled.");
      return;
    }
    const reason = window.prompt("Optional reason for the safety audit log:") || "";
    try {
      const state = await safetyCenterAdapter.setEmergencyPause(enabled, reason);
      renderSafetyCenter(state);
      applySettingsToForm(settingsAdapter.load());
      setSafetyMessage("success", enabled ? "Emergency pause enabled." : "Emergency pause disabled.");
    } catch (error) {
      event.target.checked = !enabled;
      setSafetyMessage("error", error.message || "Emergency pause could not be updated.");
    }
  }

  async function changeSafetyAutomationLevel(event) {
    try {
      const state = await safetyCenterAdapter.setAutomationLevel(event.target.value);
      renderSafetyCenter(state);
      applySettingsToForm(settingsAdapter.load());
      setSafetyMessage("success", "Automation level updated locally.");
    } catch (error) {
      event.target.value = settingsAdapter.load().automationLevel;
      setSafetyMessage("error", error.message || "Automation level could not be changed.");
    }
  }

  async function runKillSwitchAction(actionId) {
    const action = safetyKillActions[actionId];
    if (!action) {
      setSafetyMessage("error", "Unknown kill switch action.");
      return;
    }
    const typed = window.prompt(`${action.label}\n\n${action.description}\n\nType ${action.confirmationPhrase} to confirm.`);
    if (typed !== action.confirmationPhrase) {
      setSafetyMessage("error", "Kill switch action canceled.");
      return;
    }
    try {
      const state = await safetyCenterAdapter.runKillSwitchAction(actionId, typed);
      renderSafetyCenter(state);
      renderCalendar();
      renderPublishQueue();
      applySettingsToForm(settingsAdapter.load());
      setSafetyMessage("success", `${action.label} completed locally.`);
    } catch (error) {
      setSafetyMessage("error", error.message || "Kill switch action could not run.");
    }
  }

  function setBackupMessage(kind, text) {
    const success = getElement("backup-message");
    const error = getElement("backup-error");
    if (!success || !error) return;
    success.hidden = kind !== "success";
    error.hidden = kind !== "error";
    success.textContent = kind === "success" ? text : "";
    error.textContent = kind === "error" ? text : "";
  }

  function backupLabel(value) {
    return String(value || "unknown").replaceAll("_", " ");
  }

  function renderBackupData(history = backupDataAdapter.loadLocal()) {
    const view = getElement("backup-view");
    if (!view) return;
    const list = getElement("backup-history-list");
    if (list) {
      list.innerHTML = history.length
        ? history.map((item) => `
          <article class="backup-history-card">
            <div>
              <span class="card-status local-only">${escapeHtml(backupLabel(item.backupType))}</span>
              <h3>${escapeHtml(item.backupId || "Local backup")}</h3>
              <p>${escapeHtml(item.backupPath || "Path unavailable")}</p>
            </div>
            <dl class="backup-history-meta">
              <div><dt>Created</dt><dd>${escapeHtml(formatDateTime(item.createdAt))}</dd></div>
              <div><dt>Media</dt><dd>${item.includeMedia ? "Included" : "Metadata only"}</dd></div>
              <div><dt>Raw tokens</dt><dd>${item.includeSensitiveTokens ? "Included" : "Excluded"}</dd></div>
            </dl>
            <button class="secondary-button" type="button" data-backup-preview-path="${escapeHtml(item.backupPath || "")}">Preview restore</button>
          </article>
        `).join("")
        : '<p class="empty-state">No backups found yet. Create one to protect your local data.</p>';
    }
  }

  async function refreshBackupHistory() {
    try {
      const history = await backupDataAdapter.refresh();
      renderBackupData(history);
      setBackupMessage("success", "Backup history refreshed.");
    } catch (error) {
      setBackupMessage("error", error.message || "Backup history could not be loaded.");
    }
  }

  async function createBackup(eventOrType) {
    if (eventOrType?.preventDefault) {
      eventOrType.preventDefault();
    }
    const typeOverride = typeof eventOrType === "string" ? eventOrType : null;
    const backupType = typeOverride || getElement("backup-type")?.value || "full_local_backup";
    const backupName = getElement("backup-name")?.value || backupType;
    const includeMedia = Boolean(getElement("backup-include-media")?.checked);
    const includeTokenMetadata = Boolean(getElement("backup-include-token-metadata")?.checked);
    try {
      const { result, history } = await backupDataAdapter.createBackup({
        backupType,
        backupName,
        includeMedia,
        includeTokenMetadata,
        includeSensitiveTokens: false,
      });
      renderBackupData(history);
      setBackupMessage(
        "success",
        `Created ${backupLabel(result.backupType)} at ${result.backupPath}. Raw tokens are excluded.`,
      );
    } catch (error) {
      setBackupMessage("error", error.message || "Backup could not be created.");
    }
  }

  async function previewRestore(eventOrPath) {
    if (eventOrPath?.preventDefault) {
      eventOrPath.preventDefault();
    }
    const path = typeof eventOrPath === "string"
      ? eventOrPath
      : getElement("backup-restore-path")?.value;
    const output = getElement("backup-restore-preview");
    if (!path || !path.trim()) {
      setBackupMessage("error", "Enter a backup folder path to preview.");
      return;
    }
    try {
      const preview = await backupDataAdapter.previewRestore(path.trim());
      if (output) {
        output.innerHTML = `
          <article class="backup-preview-card">
            <span class="card-status needs-review">${escapeHtml(backupLabel(preview.status))}</span>
            <h3>${escapeHtml(backupLabel(preview.backupType))}</h3>
            <p>${escapeHtml(preview.backupPath || path)}</p>
            <dl class="backup-history-meta">
              <div><dt>Requires confirmation</dt><dd>${preview.requiresConfirmation ? "Yes" : "No"}</dd></div>
              <div><dt>Will restore tokens</dt><dd>${preview.willRestoreTokens ? "Yes" : "No"}</dd></div>
              <div><dt>Destructive restore</dt><dd>${preview.destructiveRestoreImplemented ? "Implemented" : "Preview only"}</dd></div>
            </dl>
            <h4>Restore plan</h4>
            <ul class="backup-warning-list">${(preview.restorePlan || []).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ul>
            <h4>Warnings</h4>
            <ul class="backup-warning-list">${(preview.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul>
          </article>
        `;
      }
      setBackupMessage("success", "Restore preview loaded. No data was changed.");
    } catch (error) {
      if (output) {
        output.innerHTML = '<p class="result-meta">Restore preview failed. Check the path and manifest.</p>';
      }
      setBackupMessage("error", error.message || "Restore preview failed safely.");
    }
  }

  function setDiagnosticsMessage(kind, text) {
    const success = getElement("diagnostics-message");
    const error = getElement("diagnostics-error");
    if (!success || !error) return;
    success.hidden = kind !== "success";
    error.hidden = kind !== "error";
    success.textContent = kind === "success" ? text : "";
    error.textContent = kind === "error" ? text : "";
  }

  function sectionElementId(sectionId) {
    const map = {
      local_storage: "diagnostics-local-storage",
      database: "diagnostics-database",
      ai: "diagnostics-ai",
      social_integrations: "diagnostics-integrations",
      safety: "diagnostics-safety",
      queue_jobs: "diagnostics-queue-jobs",
      content_workflow: "diagnostics-workflow",
      backups: "diagnostics-backups",
      recent_errors: "diagnostics-recent-errors",
    };
    return map[sectionId];
  }

  function renderDiagnosticResults(containerId, results = []) {
    const container = getElement(containerId);
    if (!container) return;
    container.innerHTML = results.length
      ? results.map((result) => `
        <article class="diagnostics-result-card">
          <div>
            <span class="card-status ${diagnosticStatusClass(result.status)}">${escapeHtml(formatStatus(result.status))}</span>
            <h3>${escapeHtml(result.label)}</h3>
            <p>${escapeHtml(result.summary)}</p>
          </div>
          <dl class="diagnostics-result-meta">
            <div><dt>Details</dt><dd>${escapeHtml(result.details || "-")}</dd></div>
            <div><dt>What to do next</dt><dd>${escapeHtml(result.recommendedAction || "No action needed.")}</dd></div>
            <div><dt>Checked</dt><dd>${escapeHtml(formatDateTime(result.checkedAt))}</dd></div>
          </dl>
        </article>
      `).join("")
      : '<p class="empty-state">No checks in this section yet.</p>';
  }

  function renderDiagnostics(diagnostics = diagnosticsAdapter.loadLocal()) {
    const view = getElement("diagnostics-view");
    if (!view) return;
    getElement("diagnostics-overall-status").textContent = formatStatus(diagnostics.overallStatus || "unknown");
    (diagnostics.sections || []).forEach((section) => {
      const elementId = sectionElementId(section.id);
      if (elementId) {
        renderDiagnosticResults(elementId, section.results || []);
      }
    });
    const nextSteps = getElement("diagnostics-next-steps");
    if (nextSteps) {
      const steps = diagnostics.nextSteps || [];
      nextSteps.innerHTML = steps.length
        ? `<ul class="diagnostics-next-list">${steps.map((step) => `<li>${escapeHtml(step)}</li>`).join("")}</ul>`
        : '<p class="empty-state">No urgent action needed. Keep backups current and use manual export until real publishing is enabled.</p>';
    }
  }

  async function refreshDiagnostics() {
    try {
      const diagnostics = await diagnosticsAdapter.refresh();
      renderDiagnostics(diagnostics);
      setDiagnosticsMessage("success", "Diagnostics refreshed. No external APIs were called.");
    } catch (error) {
      const safeError = recordFriendlyError(error, "diagnostics_refresh");
      renderDiagnostics();
      setDiagnosticsMessage("error", safeError.message || "Diagnostics could not be refreshed.");
    }
  }

  async function exportDiagnosticReport() {
    try {
      const result = await diagnosticsAdapter.exportReport();
      renderDiagnostics();
      setDiagnosticsMessage(
        "success",
        `Diagnostic report exported to ${result.reportPath}. Secrets are redacted.`,
      );
    } catch (error) {
      const safeError = recordFriendlyError(error, "diagnostics_export");
      setDiagnosticsMessage("error", safeError.message || "Diagnostic report could not be exported.");
    }
  }

  async function copyDiagnosticSummary() {
    const diagnostics = diagnosticsAdapter.loadLocal();
    const text = redactDiagnosticText([
      `Diagnostics checked: ${diagnostics.checkedAt || "unknown"}`,
      `Overall status: ${formatStatus(diagnostics.overallStatus || "unknown")}`,
      ...(diagnostics.nextSteps || []).map((step) => `Next: ${step}`),
      "No secrets, tokens, authorization codes, or raw provider payloads are included.",
    ].join("\n"));
    try {
      await navigator.clipboard.writeText(text);
      setDiagnosticsMessage("success", "Diagnostic summary copied.");
    } catch (_error) {
      setDiagnosticsMessage("error", "Clipboard is unavailable. Export a diagnostic report instead.");
    }
  }

  function tagsFromInput(value) {
    return value
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function uniqueStrings(values) {
    return Array.from(new Set((values || []).filter(Boolean)));
  }

  function validateSettings(settings) {
    if (!settings.appName.trim()) {
      return "App name is required.";
    }

    if (!settings.localDataDirectory.trim()) {
      return "Local data directory is required.";
    }

    if (!settings.defaultTimezone.trim()) {
      return "Default timezone is required.";
    }

    if (!settings.defaultPlatformTargets.length) {
      return "Choose at least one default platform target.";
    }

    const unsupportedPlatform = settings.defaultPlatformTargets.find(
      (platform) => !platformIds.includes(platform),
    );
    if (unsupportedPlatform) {
      return `Unsupported platform target: ${unsupportedPlatform}.`;
    }

    if (!automationLevels.includes(settings.automationLevel)) {
      return `Unsupported automation level: ${settings.automationLevel}.`;
    }

    if (!providerIds.includes(settings.aiProviderPreference)) {
      return `Unsupported AI provider preference: ${settings.aiProviderPreference}.`;
    }

    if (settings.automationLevel === "autonomous_content_engine") {
      return "Autonomous mode cannot bypass approval in the MVP.";
    }

    if (!settings.requireApprovalBeforePublishing) {
      return "MVP safety requires approval before publishing.";
    }

    if (!settings.requireApprovalBeforeReplying) {
      return "MVP safety requires approval before replying.";
    }

    return "";
  }

  function collectSettingsFromForm() {
    const selectedPlatforms = Array.from(
      document.querySelectorAll('input[name="defaultPlatformTargets"]:checked'),
    ).map((input) => input.value);

    return {
      appName: getElement("appName").value.trim(),
      appEnvironment: "development",
      localDataDirectory: getElement("localDataDirectory").value.trim(),
      defaultTimezone: getElement("defaultTimezone").value,
      defaultPlatformTargets: selectedPlatforms,
      automationLevel: getElement("automationLevel").value,
      requireApprovalBeforePublishing: getElement("requireApprovalBeforePublishing").checked,
      requireApprovalBeforeReplying: getElement("requireApprovalBeforeReplying").checked,
      emergencyPauseEnabled: getElement("emergencyPauseEnabled").checked,
      aiProviderPreference: getElement("aiProviderPreference").value,
    };
  }

  function listFromTextarea(id) {
    const element = getElement(id);
    if (!element) {
      return [];
    }

    return element.value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function writeListToTextarea(id, values) {
    const element = getElement(id);
    if (element) {
      element.value = Array.isArray(values) ? values.join("\n") : "";
    }
  }

  function validateBrandProfile(profile) {
    if (!profile.businessName.trim()) {
      return "businessName is required. Add the public business name before saving.";
    }

    if (profile.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(profile.email)) {
      return "Enter a valid public business email address or leave email blank.";
    }

    if (profile.website && !/^https?:\/\/.+\..+/.test(profile.website)) {
      return "Enter a valid public website URL starting with http:// or https://, or leave website blank.";
    }

    return "";
  }

  function collectBrandProfileFromForm() {
    const existing = brandBrainAdapter.loadWithoutFallback() || defaultBrandProfile;
    return {
      id: existing.id || defaultBrandProfile.id,
      businessName: getElement("brand-businessName").value.trim(),
      tagline: getElement("brand-tagline").value.trim(),
      industry: getElement("brand-industry").value.trim(),
      description: getElement("brand-description").value.trim(),
      services: listFromTextarea("brand-services"),
      serviceAreas: listFromTextarea("brand-serviceAreas"),
      targetCustomers: listFromTextarea("brand-targetCustomers"),
      brandVoice: getElement("brand-brandVoice").value.trim(),
      toneRules: listFromTextarea("brand-toneRules"),
      bannedWords: listFromTextarea("brand-bannedWords"),
      preferredWords: listFromTextarea("brand-preferredWords"),
      commonCTAs: listFromTextarea("brand-commonCTAs"),
      hashtags: listFromTextarea("brand-hashtags"),
      website: getElement("brand-website").value.trim(),
      phone: getElement("brand-phone").value.trim(),
      email: getElement("brand-email").value.trim(),
      approvalRules: listFromTextarea("brand-approvalRules"),
      safetyRules: listFromTextarea("brand-safetyRules"),
      examplePosts: listFromTextarea("brand-examplePosts"),
      createdAt: existing.createdAt,
    };
  }

  function applyBrandProfileToForm(profile) {
    getElement("brand-businessName").value = profile.businessName || "";
    getElement("brand-tagline").value = profile.tagline || "";
    getElement("brand-industry").value = profile.industry || "";
    getElement("brand-description").value = profile.description || "";
    getElement("brand-brandVoice").value = profile.brandVoice || "";
    getElement("brand-website").value = profile.website || "";
    getElement("brand-phone").value = profile.phone || "";
    getElement("brand-email").value = profile.email || "";

    writeListToTextarea("brand-services", profile.services);
    writeListToTextarea("brand-serviceAreas", profile.serviceAreas);
    writeListToTextarea("brand-targetCustomers", profile.targetCustomers);
    writeListToTextarea("brand-toneRules", profile.toneRules);
    writeListToTextarea("brand-bannedWords", profile.bannedWords);
    writeListToTextarea("brand-preferredWords", profile.preferredWords);
    writeListToTextarea("brand-commonCTAs", profile.commonCTAs);
    writeListToTextarea("brand-hashtags", profile.hashtags);
    writeListToTextarea("brand-approvalRules", profile.approvalRules);
    writeListToTextarea("brand-safetyRules", profile.safetyRules);
    writeListToTextarea("brand-examplePosts", profile.examplePosts);

    updateBrandMemorySummary(profile);
  }

  function updateBrandMemorySummary(profile) {
    const name = getElement("brand-memory-name");
    const summary = getElement("brand-memory-summary");
    const serviceCount = getElement("brand-service-count");
    const ruleCount = getElement("brand-rule-count");
    const exampleCount = getElement("brand-example-count");

    if (name) {
      name.textContent = profile.businessName || "Untitled Brand Brain";
    }
    if (summary) {
      const industry = profile.industry || "local service business";
      const voice = profile.brandVoice || "brand voice not set yet";
      summary.textContent = `${industry} memory using a ${voice} voice. Stored locally through the SQLite bridge when available.`;
    }
    if (serviceCount) {
      serviceCount.textContent = String((profile.services || []).length);
    }
    if (ruleCount) {
      ruleCount.textContent = String((profile.safetyRules || []).length);
    }
    if (exampleCount) {
      exampleCount.textContent = String((profile.examplePosts || []).length);
    }
  }

  function applySettingsToForm(settings) {
    getElement("appName").value = settings.appName;
    getElement("localDataDirectory").value = settings.localDataDirectory;
    getElement("defaultTimezone").value = settings.defaultTimezone;
    getElement("automationLevel").value = settings.automationLevel;
    getElement("requireApprovalBeforePublishing").checked = Boolean(
      settings.requireApprovalBeforePublishing,
    );
    getElement("requireApprovalBeforeReplying").checked = Boolean(
      settings.requireApprovalBeforeReplying,
    );
    getElement("emergencyPauseEnabled").checked = Boolean(settings.emergencyPauseEnabled);
    getElement("aiProviderPreference").value = settings.aiProviderPreference;

    document.querySelectorAll('input[name="defaultPlatformTargets"]').forEach((input) => {
      input.checked = settings.defaultPlatformTargets.includes(input.value);
    });

    updatePauseDisplay(settings.emergencyPauseEnabled);
  }

  function updatePauseDisplay(isPaused) {
    const pausePanel = getElement("emergency-pause-panel");
    const pauseStatusCard = getElement("pause-status-card");
    const pauseStatusText = getElement("pause-status-text");

    if (pausePanel) {
      pausePanel.classList.toggle("is-paused", isPaused);
    }
    if (pauseStatusCard) {
      pauseStatusCard.classList.toggle("pause-active", isPaused);
    }
    if (pauseStatusText) {
      pauseStatusText.textContent = isPaused ? "On - automation blocked" : "Off";
    }
  }

  function filterMediaAssets(assets) {
    const searchValue = (getElement("media-search")?.value || "").trim().toLowerCase();
    const typeValue = getElement("media-type-filter")?.value || "all";
    const statusValue = getElement("media-status-filter")?.value || "all";

    return assets.filter((asset) => {
      const matchesSearch =
        !searchValue ||
        asset.originalFilename.toLowerCase().includes(searchValue) ||
        asset.title.toLowerCase().includes(searchValue) ||
        asset.tags.join(" ").toLowerCase().includes(searchValue) ||
        asset.serviceType.toLowerCase().includes(searchValue);
      const matchesType = typeValue === "all" || asset.mediaType === typeValue;
      const matchesStatus = statusValue === "all" || asset.usageStatus === statusValue;
      return matchesSearch && matchesType && matchesStatus;
    });
  }

  function mediaPreviewMarkup(asset) {
    if (asset.previewUrl) {
      if (asset.mediaType === "video") {
        return `<video src="${escapeHtml(asset.previewUrl)}" muted playsinline aria-label="${escapeHtml(asset.originalFilename)} preview"></video>`;
      }
      return `<img src="${escapeHtml(asset.previewUrl)}" alt="${escapeHtml(asset.originalFilename)} preview" />`;
    }

    const label = asset.mediaType === "video" ? "Video" : "Image";
    return `<div class="media-placeholder" aria-hidden="true">${label}</div>`;
  }

  function mediaCardMarkup(asset) {
    const tags = asset.tags.length
      ? asset.tags.map((tag) => `<span>${escapeHtml(tag)}</span>`).join("")
      : "<span>untagged</span>";
    const filename = escapeHtml(asset.originalFilename);
    const title = escapeHtml(asset.title);
    const status = escapeHtml(formatStatus(asset.status));
    const mediaType = escapeHtml(asset.mediaType);
    const serviceType = escapeHtml(asset.serviceType || "Service not set");
    const contentAngle = escapeHtml(formatStatus(asset.contentAngle || "other"));
    const quality = asset.qualityRating ? `${asset.qualityRating}/5` : "Not rated";

    return `
      <article class="media-card" data-media-id="${escapeHtml(asset.id)}">
        <div class="media-preview ${mediaType}">
          ${mediaPreviewMarkup(asset)}
        </div>
        <div class="media-card-body">
          <div class="card-heading">
            <div>
              <h3>${filename}</h3>
              <p>${title}</p>
            </div>
            <span class="card-status local-only">${mediaType}</span>
          </div>
          <dl class="media-details">
            <div>
              <dt>Size</dt>
              <dd>${formatFileSize(asset.fileSizeBytes)}</dd>
            </div>
            <div>
              <dt>Created</dt>
              <dd>${formatDate(asset.createdAt)}</dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>${status}</dd>
            </div>
            <div>
              <dt>Service</dt>
              <dd>${serviceType}</dd>
            </div>
            <div>
              <dt>Angle</dt>
              <dd>${contentAngle}</dd>
            </div>
            <div>
              <dt>Quality</dt>
              <dd>${quality}</dd>
            </div>
          </dl>
          <div class="tag-list" aria-label="Tags for ${filename}">
            ${tags}
          </div>
          <button class="secondary-button media-edit-button" type="button" data-edit-media-id="${escapeHtml(asset.id)}">Edit metadata</button>
        </div>
      </article>
    `;
  }

  function renderMediaLibrary() {
    const grid = getElement("media-grid");
    const loading = getElement("media-loading-state");
    const empty = getElement("media-empty-state");
    const count = getElement("media-count");

    if (!grid || !loading || !empty || !count) {
      return;
    }

    try {
      loading.hidden = false;
      setMediaError("");
      const assets = mediaLibraryAdapter.load();
      const visibleAssets = filterMediaAssets(assets);

      count.textContent = String(visibleAssets.length);
      grid.innerHTML = visibleAssets.map(mediaCardMarkup).join("");
      empty.hidden = visibleAssets.length > 0;
    } catch (_error) {
      grid.innerHTML = "";
      empty.hidden = true;
      count.textContent = "0";
      setMediaError("Media Library could not load from the local demo adapter.");
    } finally {
      loading.hidden = true;
    }
  }

  function importedMediaAssetFromFile(file) {
    const isImage = file.type.startsWith("image/");
    const isVideo = file.type.startsWith("video/");
    if (!isImage && !isVideo) {
      throw new Error("Unsupported file type. Import an image or video file.");
    }

    return {
      id: `browser-import-${Date.now()}`,
      title: file.name.replace(/\.[^.]+$/, ""),
      originalFilename: file.name,
      mediaType: isVideo ? "video" : "image",
      fileSizeBytes: file.size,
      createdAt: new Date().toISOString(),
      tags: ["browser import"],
      description: "",
      serviceType: "",
      locationName: "",
      city: "",
      state: "",
      projectDate: "",
      contentAngle: "other",
      qualityRating: "",
      usageStatus: "new",
      status: "new",
      notes: "",
      previewUrl: "",
    };
  }

  function openMediaDetailPanel(mediaId) {
    const panel = getElement("media-detail-panel");
    const asset = mediaLibraryAdapter.load().find((item) => item.id === mediaId);
    if (!panel || !asset) {
      return;
    }

    getElement("media-selected-id").value = asset.id;
    getElement("media-title").value = asset.title;
    getElement("media-description").value = asset.description;
    getElement("media-tags").value = asset.tags.join(", ");
    getElement("media-serviceType").value = asset.serviceType;
    getElement("media-locationName").value = asset.locationName;
    getElement("media-city").value = asset.city;
    getElement("media-state").value = asset.state;
    getElement("media-projectDate").value = asset.projectDate;
    getElement("media-contentAngle").value = asset.contentAngle;
    getElement("media-qualityRating").value = asset.qualityRating || "";
    getElement("media-usageStatus").value = asset.usageStatus;
    getElement("media-notes").value = asset.notes;
    setMediaMetadataMessage("", "");
    panel.hidden = false;
    getElement("media-title").focus();
  }

  function collectMediaMetadataFromForm() {
    const qualityValue = getElement("media-qualityRating").value;
    return {
      id: getElement("media-selected-id").value,
      title: getElement("media-title").value.trim(),
      description: getElement("media-description").value.trim(),
      tags: tagsFromInput(getElement("media-tags").value),
      serviceType: getElement("media-serviceType").value.trim(),
      locationName: getElement("media-locationName").value.trim(),
      city: getElement("media-city").value.trim(),
      state: getElement("media-state").value.trim(),
      projectDate: getElement("media-projectDate").value,
      contentAngle: getElement("media-contentAngle").value,
      qualityRating: qualityValue ? Number(qualityValue) : "",
      usageStatus: getElement("media-usageStatus").value,
      status: getElement("media-usageStatus").value,
      notes: getElement("media-notes").value.trim(),
    };
  }

  function validateMediaMetadata(metadata) {
    if (!metadata.title) {
      return "Title is required before saving media metadata.";
    }
    if (!contentAngles.includes(metadata.contentAngle)) {
      return "Choose a supported content angle.";
    }
    if (!mediaStatuses.includes(metadata.usageStatus)) {
      return "Choose a supported usage status.";
    }
    if (metadata.qualityRating && (metadata.qualityRating < 1 || metadata.qualityRating > 5)) {
      return "Quality rating must be between 1 and 5.";
    }
    return "";
  }

  async function saveMediaMetadata() {
    const metadata = collectMediaMetadataFromForm();
    const validationMessage = validateMediaMetadata(metadata);
    if (validationMessage) {
      setMediaMetadataMessage("error", validationMessage);
      return;
    }

    const assets = mediaLibraryAdapter.load();
    const nextAssets = assets.map((asset) => {
      if (asset.id !== metadata.id) {
        return asset;
      }
      return normalizeMediaAsset({
        ...asset,
        ...metadata,
      });
    });
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        const updates = { ...metadata };
        delete updates.id;
        delete updates.status;
        await bridge.request(`/api/media/${encodeURIComponent(metadata.id)}`, {
          method: "PATCH",
          body: updates,
        });
        await bridge.sync();
      } catch (error) {
        setMediaMetadataMessage("error", error.message || "Media metadata could not be saved to local SQLite.");
        return;
      }
    } else {
      mediaLibraryAdapter.save(nextAssets);
    }
    renderMediaLibrary();
    openMediaDetailPanel(metadata.id);
    setMediaMetadataMessage(
      "success",
      bridge
        ? "Media metadata saved to local SQLite."
        : "Media metadata saved locally for this browser demo.",
    );
  }

  function startOfDay(date) {
    const value = new Date(date);
    value.setHours(0, 0, 0, 0);
    return value;
  }

  function startOfWeek(date) {
    const value = startOfDay(date);
    value.setDate(value.getDate() - value.getDay());
    return value;
  }

  function endOfWeek(date) {
    const value = startOfWeek(date);
    value.setDate(value.getDate() + 6);
    value.setHours(23, 59, 59, 999);
    return value;
  }

  function startOfMonth(date) {
    const value = startOfDay(date);
    value.setDate(1);
    return value;
  }

  function endOfMonth(date) {
    const value = startOfMonth(date);
    value.setMonth(value.getMonth() + 1);
    value.setDate(0);
    value.setHours(23, 59, 59, 999);
    return value;
  }

  function addDays(date, days) {
    const value = new Date(date);
    value.setDate(value.getDate() + days);
    return value;
  }

  function sameDay(left, right) {
    return (
      left.getFullYear() === right.getFullYear() &&
      left.getMonth() === right.getMonth() &&
      left.getDate() === right.getDate()
    );
  }

  function formatDateTime(value) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return "Unknown date";
    }
    return parsed.toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatTime(value) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return "Unknown";
    }
    return parsed.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
  }

  function formatCalendarRange() {
    if (calendarState.view === "list") {
      return "All locally scheduled posts";
    }
    const start = calendarState.view === "month"
      ? startOfMonth(calendarState.cursorDate)
      : startOfWeek(calendarState.cursorDate);
    const end = calendarState.view === "month"
      ? endOfMonth(calendarState.cursorDate)
      : endOfWeek(calendarState.cursorDate);
    return `${formatDate(start.toISOString())} - ${formatDate(end.toISOString())}`;
  }

  function datetimeLocalValue(value) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return "";
    }
    const offsetMs = parsed.getTimezoneOffset() * 60 * 1000;
    return new Date(parsed.getTime() - offsetMs).toISOString().slice(0, 16);
  }

  function findQueueItemForPost(post) {
    return loadPublishQueueItems().find((item) => item.id === post.publishQueueItemId) || null;
  }

  function scheduledPostForQueueItem(item) {
    return loadScheduledPosts().find((post) => post.id === item.scheduledPostId) || null;
  }

  function selectedQueueItem() {
    if (!queueState.selectedItemId) {
      return null;
    }
    return loadPublishQueueItems().find((item) => item.id === queueState.selectedItemId) || null;
  }

  function connectedAccountForPlatform(platform) {
    const activeStatuses = ["connected", "limited", "expired", "revoked", "requires_reauth", "error"];
    return loadConnectedAccounts()
      .filter((account) => account.platform === platform && activeStatuses.includes(account.connectionStatus))
      .sort((left, right) => {
        const rank = { connected: 0, limited: 1, requires_reauth: 2, expired: 3, revoked: 4, error: 5 };
        return (rank[left.connectionStatus] ?? 9) - (rank[right.connectionStatus] ?? 9);
      })[0] || null;
  }

  function queueAccountReadiness(item, errors) {
    const account = connectedAccountForPlatform(item.platform);
    const config = platformConfig(item.platform);
    const accountWarnings = [];
    const accountErrors = [];
    let accountCheckStatus = "missing_account";
    let connectionStatus = "not_connected";
    let matchedSocialAccountId = "";
    let missingScopes = [];
    let requiresReauth = false;

    if (!account) {
      accountWarnings.push("missing_connected_account: Future real publishing will require a connected account; manual export is still allowed.");
      accountErrors.push("future_real_publish_blocked: Missing connected account.");
    } else {
      matchedSocialAccountId = account.id;
      connectionStatus = account.connectionStatus;
      missingScopes = Array.from(new Set(
        config.requiredScopes
          .filter((scope) => !(account.grantedScopes || []).includes(scope))
          .concat(account.missingScopes || []),
      ));
      requiresReauth = Boolean(account.requiresReauth) || ["expired", "revoked", "requires_reauth", "error"].includes(account.connectionStatus);
      if (requiresReauth) {
        accountCheckStatus = "requires_reauth";
        accountWarnings.push("account_requires_reauth: Connected account needs reconnect before future real publishing.");
        accountErrors.push("future_real_publish_blocked: Account requires reauth.");
      } else if (account.connectionStatus === "limited") {
        accountCheckStatus = "limited";
      } else {
        accountCheckStatus = "connected";
      }
      if (missingScopes.length) {
        accountWarnings.push(`missing_account_scopes: Future real publishing may need scopes: ${missingScopes.join(", ")}`);
        if (!requiresReauth) {
          accountErrors.push("future_real_publish_blocked: Missing required account scopes.");
        }
      }
    }

    accountWarnings.push("real_publishing_disabled_by_policy: Real publishing disabled in this build.");
    return {
      accountCheckStatus,
      matchedSocialAccountId,
      matchedAccountDisplayName: account?.displayName || "",
      accountWarnings,
      accountErrors,
      missingScopes,
      requiresReauth,
      connectionStatus,
      realPublishingEligible: false,
      manualExportEligible: errors.length === 0 && item.queueStatus !== "canceled",
      mockPublishEligible: errors.length === 0 && settingsAdapter.load().appEnvironment === "development",
    };
  }

  function queueCaption(item) {
    return scheduledPostForQueueItem(item)?.captionSnapshot || "";
  }

  function queueHook(item) {
    return scheduledPostForQueueItem(item)?.scheduleMetadata?.hook || "";
  }

  function queueBrandName(item) {
    const post = scheduledPostForQueueItem(item);
    return post?.brandName || brandBrainAdapter.load().businessName || item.brandProfileId;
  }

  function populateQueueBrandFilter(items) {
    const select = getElement("queue-brand-filter");
    if (!select) {
      return;
    }
    const current = select.value || "all";
    const brands = new Map();
    items.forEach((item) => {
      brands.set(item.brandProfileId, queueBrandName(item));
    });
    select.innerHTML = '<option value="all">All Brand Brains</option>';
    Array.from(brands.entries()).forEach(([id, name]) => {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = name;
      select.appendChild(option);
    });
    select.value = brands.has(current) ? current : "all";
  }

  function filterQueueItems(items) {
    const platform = getElement("queue-platform-filter")?.value || "all";
    const queueStatus = getElement("queue-status-filter")?.value || "all";
    const preflightStatus = getElement("queue-preflight-filter")?.value || "all";
    const dateRange = getElement("queue-date-filter")?.value || "all";
    const brand = getElement("queue-brand-filter")?.value || "all";
    const search = (getElement("queue-search")?.value || "").trim().toLowerCase();
    const now = new Date();
    const todayStart = startOfDay(now);
    const todayEnd = new Date(todayStart);
    todayEnd.setHours(23, 59, 59, 999);
    const nextSeven = addDays(todayStart, 7);

    return items
      .filter((item) => platform === "all" || item.platform === platform)
      .filter((item) => queueStatus === "all" || item.queueStatus === queueStatus)
      .filter((item) => preflightStatus === "all" || item.preflightStatus === preflightStatus)
      .filter((item) => brand === "all" || item.brandProfileId === brand)
      .filter((item) => {
        const due = new Date(item.dueAt);
        if (Number.isNaN(due.getTime()) || dateRange === "all") return true;
        if (dateRange === "today") return due >= todayStart && due <= todayEnd;
        if (dateRange === "next_7_days") return due >= todayStart && due <= nextSeven;
        if (dateRange === "overdue") return due < now && !["mock_published", "manually_exported", "canceled", "skipped"].includes(item.queueStatus);
        return true;
      })
      .filter((item) => {
        if (!search) return true;
        const haystack = [
          item.platform,
          item.queueStatus,
          item.preflightStatus,
          queueCaption(item),
          queueHook(item),
          queueBrandName(item),
        ].join(" ").toLowerCase();
        return haystack.includes(search);
      })
      .sort((left, right) => new Date(left.dueAt) - new Date(right.dueAt));
  }

  function renderQueueSummary(items) {
    const scheduled = loadScheduledPosts();
    const summary = {
      waiting: items.filter((item) => item.queueStatus === "waiting").length,
      ready: items.filter((item) => item.queueStatus === "ready").length,
      blocked: items.filter((item) => item.queueStatus === "blocked").length,
      mockPublished: items.filter((item) => item.queueStatus === "mock_published").length,
      failed: items.filter((item) => item.queueStatus === "failed").length,
      needsAttention: scheduled.filter((post) => post.status === "needs_attention").length,
    };
    getElement("queue-summary-waiting").textContent = String(summary.waiting);
    getElement("queue-summary-ready").textContent = String(summary.ready);
    getElement("queue-summary-blocked").textContent = String(summary.blocked);
    getElement("queue-summary-mock-published").textContent = String(summary.mockPublished);
    getElement("queue-summary-failed").textContent = String(summary.failed);
    getElement("queue-summary-needs-attention").textContent = String(summary.needsAttention);
  }

  function renderQueueList(items) {
    const list = getElement("queue-list");
    if (!list) {
      return;
    }
    list.innerHTML = items
      .map((item) => {
        const post = scheduledPostForQueueItem(item);
        const metadata = post?.scheduleMetadata || {};
        const safetyFlagCount = (metadata.safetyFlags || []).length;
        const errorCount = item.preflightErrors.length;
        const warningCount = item.preflightWarnings.length;
        const title = metadata.hook || metadata.headline || `${item.platform} queue item`;
        const selected = item.id === queueState.selectedItemId ? " selected" : "";
        const account = queueAccountReadiness(item, item.preflightErrors);
        const accountStatus = item.accountCheckStatus !== "not_checked"
          ? item.accountCheckStatus
          : account.accountCheckStatus;
        const accountName = account.matchedAccountDisplayName || "No account connected";
        return `
          <article class="queue-card${selected}" data-queue-item-id="${escapeHtml(item.id)}" tabindex="0">
            <div class="draft-card-header">
              <span class="card-status local-only">${escapeHtml(item.platform)}</span>
              <span class="result-status">${escapeHtml(formatStatus(item.queueStatus))}</span>
            </div>
            <h3>${escapeHtml(title)}</h3>
            <p class="card-copy">${escapeHtml((post?.captionSnapshot || "").slice(0, 180))}</p>
            <div class="draft-card-metrics">
              <span>Due ${escapeHtml(formatDateTime(item.dueAt))}</span>
              <span>Preflight ${escapeHtml(formatStatus(item.preflightStatus))}</span>
              <span>Scheduled ${escapeHtml(formatStatus(post?.status || "missing"))}</span>
              <span>${safetyFlagCount} safety</span>
              <span>${errorCount} errors</span>
              <span>${warningCount} warnings</span>
              <span>Priority ${item.priority}</span>
              <span>Account ${escapeHtml(formatStatus(accountStatus))}</span>
              <span>${escapeHtml(accountName)}</span>
              <span>${account.manualExportEligible || item.manualExportEligible ? "Manual export available" : "Manual export blocked"}</span>
              <span>Checked ${escapeHtml(item.lastCheckedAt ? formatDateTime(item.lastCheckedAt) : "never")}</span>
            </div>
          </article>
        `;
      })
      .join("");
  }

  function renderPreflightMessages(containerId, messages, emptyText) {
    const container = getElement(containerId);
    if (!container) {
      return;
    }
    container.innerHTML = messages.length
      ? `<ul class="safety-flag-list">${messages.map((message) => `<li>${escapeHtml(message)}</li>`).join("")}</ul>`
      : `<p class="result-meta">${escapeHtml(emptyText)}</p>`;
  }

  function queueAttempts(item) {
    return loadPublishAttempts()
      .filter((attempt) => attempt.publishQueueItemId === item.id)
      .sort((left, right) => new Date(right.createdAt) - new Date(left.createdAt));
  }

  function renderAttemptHistory(item) {
    const container = getElement("queue-attempt-history");
    if (!container) {
      return;
    }
    const attempts = queueAttempts(item);
    container.innerHTML = attempts.length
      ? attempts
          .map(
            (attempt) => `
              <div class="approval-history-item">
                <strong>${escapeHtml(formatStatus(attempt.attemptType))} - ${escapeHtml(formatStatus(attempt.attemptStatus))}</strong>
                <span>${escapeHtml(formatDateTime(attempt.createdAt))}</span>
                <p>${escapeHtml(attempt.errorMessage || "Local attempt recorded. No external API was called.")}</p>
              </div>
            `,
          )
          .join("")
      : '<p class="result-meta">No publish attempts recorded yet.</p>';
  }

  function setQueueMessage(kind, text) {
    const error = getElement("queue-action-error");
    const success = getElement("queue-action-message");
    if (!error || !success) {
      return;
    }
    error.hidden = kind !== "error";
    success.hidden = kind !== "success";
    error.textContent = kind === "error" ? text : "";
    success.textContent = kind === "success" ? text : "";
  }

  function updateQueueActionButtons(item) {
    const mockButton = getElement("queue-mock-publish");
    const manualButton = getElement("queue-manual-export");
    const cancelButton = getElement("queue-cancel");
    const processed = ["mock_published", "manually_exported", "canceled", "skipped"].includes(item.queueStatus);
    if (mockButton) {
      mockButton.disabled = processed || !item.mockPublishEnabled || item.preflightStatus !== "passed" || item.queueStatus !== "ready";
      mockButton.title = mockButton.disabled
        ? "Mock publish requires ready queue status, passed preflight, and mock publishing enabled."
        : "Record a mock/demo publish locally. No external API is called.";
    }
    if (manualButton) {
      manualButton.disabled = processed;
    }
    if (cancelButton) {
      cancelButton.disabled = processed;
    }
  }

  function renderQueueDetail() {
    const item = selectedQueueItem();
    const empty = getElement("queue-detail-empty");
    const content = getElement("queue-detail-content");
    if (!empty || !content) {
      return;
    }
    if (!item) {
      empty.hidden = false;
      content.hidden = true;
      return;
    }
    const post = scheduledPostForQueueItem(item);
    const metadata = post?.scheduleMetadata || {};
    const account = queueAccountReadiness(item, item.preflightErrors);
    const accountCheckStatus = item.accountCheckStatus !== "not_checked"
      ? item.accountCheckStatus
      : account.accountCheckStatus;
    const connectionStatus = item.connectionStatus !== "not_connected"
      ? item.connectionStatus
      : account.connectionStatus;
    const missingScopes = item.missingScopes.length ? item.missingScopes : account.missingScopes;
    const manualExportEligible = item.manualExportEligible || account.manualExportEligible;
    const mockPublishEligible = item.mockPublishEligible || account.mockPublishEligible;
    const warnings = uniqueStrings(item.preflightWarnings.concat(item.accountWarnings, item.accountErrors, account.accountWarnings, account.accountErrors));
    const errors = uniqueStrings(item.preflightErrors);
    empty.hidden = true;
    content.hidden = false;
    getElement("queue-detail-status").textContent = formatStatus(item.queueStatus);
    getElement("queue-detail-summary").textContent =
      metadata.hook || metadata.headline || "Manual export is the safe path. Future real publishing remains disabled.";
    getElement("queue-detail-platform").textContent = item.platform;
    getElement("queue-detail-due").textContent = formatDateTime(item.dueAt);
    getElement("queue-detail-timezone").textContent = item.timezone || "-";
    getElement("queue-detail-preflight").textContent = formatStatus(item.preflightStatus);
    getElement("queue-detail-account-status").textContent = `${formatStatus(accountCheckStatus)} (${formatStatus(connectionStatus)})`;
    getElement("queue-detail-account-name").textContent = account.matchedAccountDisplayName || "No matching connected account";
    getElement("queue-detail-account-scopes").textContent = missingScopes.length ? missingScopes.join(", ") : "No missing scopes recorded";
    getElement("queue-detail-manual-export").textContent = manualExportEligible ? "Available when preflight has no blocking errors" : "Blocked by preflight or canceled state";
    getElement("queue-detail-real-publishing").textContent = item.realPublishingEligible ? "Eligible for future real publishing" : "Real publishing disabled in this build";
    getElement("queue-detail-mock-publish").textContent = mockPublishEligible ? "Mock/demo eligible when queue is ready" : "Not mock-ready";
    getElement("queue-detail-scheduled").textContent = post ? `${post.id} (${formatStatus(post.status)})` : "Missing scheduled post";
    getElement("queue-detail-draft").textContent = item.generatedPostId || "-";
    getElement("queue-detail-created").textContent = formatDateTime(item.createdAt);
    getElement("queue-detail-updated").textContent = formatDateTime(item.updatedAt);
    getElement("queue-detail-caption").textContent = post?.captionSnapshot || "-";
    getElement("queue-detail-hashtags").innerHTML = (metadata.hashtags || [])
      .map((tag) => `<span class="hashtag">${escapeHtml(tag)}</span>`)
      .join("");
    getElement("queue-detail-cta").textContent = metadata.callToAction
      ? `CTA: ${metadata.callToAction}`
      : "CTA: none";
    getElement("queue-detail-media").innerHTML = post?.mediaAssetIds?.length
      ? `<ul class="safety-flag-list">${post.mediaAssetIds.map((id) => `<li>${escapeHtml(id)}</li>`).join("")}</ul>`
      : '<p class="result-meta">No linked media assets.</p>';
    renderPreflightMessages("queue-detail-errors", errors, "No blocking preflight errors.");
    renderPreflightMessages("queue-detail-warnings", warnings, "No preflight warnings.");
    renderAttemptHistory(item);
    updateQueueActionButtons(item);
  }

  function renderPublishQueue() {
    const loading = getElement("queue-loading-state");
    const error = getElement("queue-error-state");
    const empty = getElement("queue-empty-state");
    if (!loading || !error || !empty) {
      return;
    }
    try {
      loading.hidden = false;
      error.hidden = true;
      const items = loadPublishQueueItems();
      populateQueueBrandFilter(items);
      renderQueueSummary(items);
      const filtered = filterQueueItems(items);
      if (queueState.selectedItemId && !filtered.some((item) => item.id === queueState.selectedItemId)) {
        queueState.selectedItemId = null;
      }
      if (!queueState.selectedItemId && filtered.length) {
        queueState.selectedItemId = filtered[0].id;
      }
      renderQueueList(filtered);
      empty.hidden = filtered.length > 0;
      renderQueueDetail();
    } catch (errorObject) {
      console.error("queue: render failed", errorObject);
      error.hidden = false;
      empty.hidden = true;
    } finally {
      loading.hidden = true;
    }
  }

  function platformConfig(platform) {
    return connectedPlatformConfigs.find((config) => config.id === platform) || connectedPlatformConfigs[0];
  }

  function activeConnectedAccountForPlatform(platform) {
    return loadConnectedAccounts().find(
      (account) => account.platform === platform && account.connectionStatus !== "disconnected",
    ) || null;
  }

  function platformCardMarkup(config) {
    const account = activeConnectedAccountForPlatform(config.id);
    const status = account ? account.connectionStatus : "not_connected";
    const missingScopes = account ? account.missingScopes : config.missingScopes;
    const grantedScopes = account ? account.grantedScopes : [];
    const canMockConnect = mockConnectPlatformIds.includes(config.id);
    const connectLabel = canMockConnect ? "Connect mock" : "Connect later";
    const connectDisabled = account || !canMockConnect ? " disabled" : "";
    const disconnectButton = account
      ? `<button class="secondary-button" type="button" data-connected-action="disconnect" data-account-id="${escapeHtml(account.id)}">Disconnect</button>`
      : "";
    const reconnectButton = account
      ? `<button class="secondary-button" type="button" data-connected-action="reconnect" data-platform="${escapeHtml(config.id)}">Reconnect later</button>`
      : "";
    const validateButton = account
      ? `<button class="secondary-button" type="button" data-connected-action="validate" data-account-id="${escapeHtml(account.id)}">Check connection</button>`
      : "";

    return `
      <article class="connected-platform-card" data-platform="${escapeHtml(config.id)}">
        <div class="connected-card-header">
          <span class="connected-platform-badge" aria-hidden="true">${escapeHtml(config.badge)}</span>
          <div>
            <h3>${escapeHtml(config.label)}</h3>
            <p>${escapeHtml(formatStatus(config.setupStatus))} · ${escapeHtml(config.accountType)}</p>
          </div>
        </div>
        <div class="connected-status-row">
          <span class="card-status ${account ? "local-only" : "mock-mode"}">${escapeHtml(formatStatus(status))}</span>
          <span class="card-status needs-review">Publishing disabled in this build</span>
        </div>
        <dl class="connected-platform-details">
          <div><dt>Connection health</dt><dd>${account ? escapeHtml(formatStatus(account.healthStatus || "not_checked")) : "Not connected"}</dd></div>
          <div><dt>Capabilities</dt><dd>${escapeHtml(config.capabilities.join(", "))}</dd></div>
          <div><dt>Granted scopes</dt><dd>${escapeHtml(grantedScopes.length ? grantedScopes.join(", ") : "None yet")}</dd></div>
          <div><dt>Missing scopes</dt><dd>${escapeHtml(missingScopes.length ? missingScopes.join(", ") : "None")}</dd></div>
        </dl>
        <div class="calendar-actions">
          <button class="primary-button" type="button" data-connected-action="connect" data-platform="${escapeHtml(config.id)}"${connectDisabled}>${connectLabel}</button>
          ${disconnectButton}
          ${reconnectButton}
          ${validateButton}
          <button class="secondary-button" type="button" data-connected-action="setup" data-platform="${escapeHtml(config.id)}">View setup instructions</button>
        </div>
      </article>
    `;
  }

  function connectedAccountCardMarkup(account) {
    return `
      <article class="connected-account-card">
        <div class="connected-card-header">
          <span class="connected-platform-badge" aria-hidden="true">${escapeHtml(platformConfig(account.platform).badge)}</span>
          <div>
            <h3>${escapeHtml(account.displayName)}</h3>
            <p>${escapeHtml(platformConfig(account.platform).label)} · ${escapeHtml(account.username || "username not set")}</p>
          </div>
          <span class="card-status ${account.connectionStatus === "connected" ? "local-only" : "needs-review"}">${escapeHtml(formatStatus(account.connectionStatus))}</span>
        </div>
        <dl class="connected-account-details">
          <div><dt>Account type</dt><dd>${escapeHtml(account.accountType)}</dd></div>
          <div><dt>Connection health</dt><dd>${escapeHtml(formatStatus(account.healthStatus || "not_checked"))}</dd></div>
          <div><dt>Mock connection</dt><dd>${account.isMock ? "Yes - mock/demo" : "No"}</dd></div>
          <div><dt>Safe storage mode</dt><dd>${escapeHtml(account.storageMode)}</dd></div>
          <div><dt>Granted scopes</dt><dd>${escapeHtml(account.grantedScopes.join(", ") || "None")}</dd></div>
          <div><dt>Missing scopes</dt><dd>${escapeHtml(account.missingScopes.join(", ") || "None")}</dd></div>
          <div><dt>Missing permissions</dt><dd>${escapeHtml(account.missingPermissions.join(", ") || "None")}</dd></div>
          <div><dt>Requires reauth</dt><dd>${account.requiresReauth ? "Yes" : "No"}</dd></div>
          <div><dt>Health warnings</dt><dd>${escapeHtml(account.healthWarnings.join(" ") || "None")}</dd></div>
          <div><dt>Health errors</dt><dd>${escapeHtml(account.healthErrors.join(" ") || "None")}</dd></div>
          <div><dt>Last connected</dt><dd>${escapeHtml(formatDateTime(account.lastConnectedAt))}</dd></div>
          <div><dt>Last validated</dt><dd>${escapeHtml(formatDateTime(account.lastValidatedAt))}</dd></div>
        </dl>
        <div class="calendar-actions">
          <button class="secondary-button" type="button" data-connected-action="validate" data-account-id="${escapeHtml(account.id)}">Check connection</button>
          <button class="secondary-button" type="button" data-connected-action="disconnect" data-account-id="${escapeHtml(account.id)}"${account.connectionStatus === "disconnected" ? " disabled" : ""}>Disconnect</button>
          <button class="secondary-button" type="button" data-connected-action="reconnect" data-platform="${escapeHtml(account.platform)}">Reconnect placeholder</button>
        </div>
      </article>
    `;
  }

  function renderConnectedAccountList(accounts) {
    const list = getElement("connected-account-list");
    const empty = getElement("connected-empty-state");
    if (!list || !empty) {
      return;
    }
    const activeAccounts = accounts.filter((account) => account.connectionStatus !== "disconnected");
    empty.hidden = activeAccounts.length > 0;
    list.innerHTML = activeAccounts.length
      ? activeAccounts.map(connectedAccountCardMarkup).join("")
      : "";
  }

  function renderConnectorAuditLog() {
    const list = getElement("connected-audit-list");
    if (!list) {
      return;
    }
    const logs = loadConnectorAuditLogs();
    list.innerHTML = logs.length
      ? logs.slice(0, 8).map((log) => `
        <article class="approval-history-item">
          <strong>${escapeHtml(formatStatus(log.action))} · ${escapeHtml(platformConfig(log.platform).label)}</strong>
          <span>${escapeHtml(formatStatus(log.status))} · ${escapeHtml(formatDateTime(log.createdAt))}</span>
          <p>${escapeHtml(log.message)}</p>
        </article>
      `).join("")
      : '<p class="result-meta">No connector audit events yet.</p>';
  }

  function renderConnectedAccounts() {
    const loading = getElement("connected-loading-state");
    const error = getElement("connected-error-state");
    const grid = getElement("connected-platform-grid");
    if (!loading || !error || !grid) {
      return;
    }

    try {
      loading.hidden = false;
      error.hidden = true;
      const accounts = loadConnectedAccounts();
      grid.innerHTML = connectedPlatformConfigs.map(platformCardMarkup).join("");
      renderConnectedAccountList(accounts);
      renderConnectorAuditLog();
    } catch (errorObject) {
      console.error("connected accounts: render failed", errorObject);
      error.hidden = false;
    } finally {
      loading.hidden = true;
    }
  }

  async function mockConnectPlatform(platform) {
    const config = platformConfig(platform);
    if (!mockConnectPlatformIds.includes(config.id)) {
      setConnectedMessage("error", `${config.label} is scaffolded only. Mock connect is available only for mock-ready connectors in this build.`);
      return;
    }

    const accounts = loadConnectedAccounts();
    const existing = accounts.find(
      (account) => account.platform === config.id && account.connectionStatus !== "disconnected",
    );
    if (existing) {
      setConnectedMessage("error", `${config.label} already has an active mock connection.`);
      return;
    }

    const bridge = activeApiBridge();
    if (bridge) {
      try {
        const result = await bridge.request(`/api/connect/${encodeURIComponent(config.id)}/mock-connect`, {
          method: "POST",
          body: {},
        });
        if (!result.success) {
          throw new Error(result.message || "Mock connection could not be created.");
        }
        await bridge.sync();
        setConnectedMessage("success", `${config.label} mock connection saved to local SQLite. Real publishing remains disabled.`);
        renderConnectedAccounts();
      } catch (error) {
        setConnectedMessage("error", error.message || "Mock connection could not be created.");
      }
      return;
    }

    const now = new Date().toISOString();
    const account = safeConnectedAccount(normalizeConnectedAccount({
      id: `mock-${config.id}-${Date.now()}`,
      platform: config.id,
      displayName: `Mock ${config.label} ${config.accountType}`,
      username: `mock_${config.id}_demo`,
      accountType: config.accountType,
      connectionStatus: "connected",
      capabilities: config.capabilities,
      grantedScopes: config.requiredScopes,
      missingScopes: [],
      missingPermissions: [],
      requiresReauth: false,
      healthStatus: "healthy",
      healthWarnings: [],
      healthErrors: [],
      lastConnectedAt: now,
      lastValidatedAt: now,
      isMock: true,
      createdAt: now,
      updatedAt: now,
    }));

    saveConnectedAccounts([account, ...accounts]);
    appendConnectorAuditLog(config.id, "mock_oauth_connected", "succeeded", "Mock account connected locally. No real API was called.", {
      accountId: account.id,
      storageMode: "placeholder_not_stored",
    });
    setConnectedMessage("success", `${config.label} mock connection saved locally. Real publishing remains disabled.`);
    renderConnectedAccounts();
  }

  async function validateConnectedAccount(accountId) {
    const accounts = loadConnectedAccounts();
    const account = accounts.find((item) => item.id === accountId);
    if (!account) {
      setConnectedMessage("error", "Connected account was not found.");
      return;
    }
    if (account.connectionStatus === "disconnected") {
      setConnectedMessage("error", "Disconnected accounts cannot be checked until they are reconnected.");
      return;
    }

    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/connect/${encodeURIComponent(account.platform)}/validate`, {
          method: "POST",
          body: { socialAccountId: account.id },
        });
        await bridge.sync();
        setConnectedMessage("success", `${platformConfig(account.platform).label} connection checked through the local scaffold. No real API was called.`);
        renderConnectedAccounts();
      } catch (error) {
        setConnectedMessage("error", error.message || "Local connection check could not be completed.");
      }
      return;
    }

    const now = new Date().toISOString();
    const config = platformConfig(account.platform);
    const missingScopes = Array.isArray(account.missingScopes) ? account.missingScopes : [];
    const missingPermissions = uniqueStrings([
      ...(Array.isArray(account.missingPermissions) ? account.missingPermissions : []),
      ...missingScopes,
    ]);
    const healthWarnings = [];
    const healthErrors = [];
    let healthStatus = "healthy";
    let connectionStatus = "connected";
    let requiresReauth = Boolean(account.requiresReauth);

    if (requiresReauth || account.connectionStatus === "requires_reauth" || account.connectionStatus === "expired") {
      healthStatus = "expired";
      connectionStatus = "requires_reauth";
      requiresReauth = true;
      healthErrors.push("This mock connection needs reauthorization before future real checks.");
    } else if (missingPermissions.length) {
      healthStatus = "missing_permissions";
      connectionStatus = "limited";
      healthWarnings.push(`Missing permissions: ${missingPermissions.join(", ")}.`);
    }

    if (account.platform === "instagram" && !["business", "creator"].includes(account.accountType)) {
      healthStatus = healthStatus === "healthy" ? "limited" : healthStatus;
      connectionStatus = connectionStatus === "connected" ? "limited" : connectionStatus;
      healthWarnings.push("Instagram should be a Business or Creator account for future real discovery.");
    }

    if (!account.isMock) {
      healthWarnings.push("Real provider discovery is scaffolded only. No real API was called.");
    } else {
      healthWarnings.push("Mock/demo health check only. No real API was called.");
    }

    const nextAccounts = accounts.map((item) =>
      item.id === accountId
        ? safeConnectedAccount({
            ...item,
            connectionStatus,
            requiresReauth,
            missingPermissions,
            healthStatus,
            healthWarnings: uniqueStrings(healthWarnings),
            healthErrors: uniqueStrings(healthErrors),
            lastValidatedAt: now,
            updatedAt: now,
          })
        : item,
    );

    saveConnectedAccounts(nextAccounts);
    appendConnectorAuditLog(
      account.platform,
      "connection_validate",
      healthStatus,
      `${config.label} connection checked locally. No real API was called.`,
      {
        accountId: account.id,
        healthStatus,
        connectionStatus,
        missingPermissions,
        requiresReauth,
      },
    );
    setConnectedMessage("success", `${config.label} connection checked locally. No real API was called.`);
    renderConnectedAccounts();
  }

  async function disconnectConnectedAccount(accountId) {
    const accounts = loadConnectedAccounts();
    const account = accounts.find((item) => item.id === accountId);
    if (!account) {
      setConnectedMessage("error", "Connected account was not found.");
      return;
    }
    if (!window.confirm("Disconnect this mock account locally? The record stays in audit history.")) {
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        const result = await bridge.request(`/api/connect/${encodeURIComponent(account.platform)}/disconnect`, {
          method: "POST",
          body: { socialAccountId: account.id },
        });
        if (!result.success) {
          throw new Error(result.message || "Local disconnect could not be completed.");
        }
        await bridge.sync();
        setConnectedMessage("success", `${platformConfig(account.platform).label} mock account disconnected in local SQLite.`);
        renderConnectedAccounts();
      } catch (error) {
        setConnectedMessage("error", error.message || "Local disconnect could not be completed.");
      }
      return;
    }
    const now = new Date().toISOString();
    const nextAccounts = accounts.map((item) =>
      item.id === accountId
        ? safeConnectedAccount({
            ...item,
            connectionStatus: "disconnected",
            disconnectedAt: now,
            updatedAt: now,
          })
        : item,
    );
    saveConnectedAccounts(nextAccounts);
    appendConnectorAuditLog(account.platform, "disconnect", "succeeded", "Mock account disconnected locally. No external revoke was attempted.", {
      accountId: account.id,
    });
    setConnectedMessage("success", `${platformConfig(account.platform).label} mock account disconnected locally.`);
    renderConnectedAccounts();
  }

  function showConnectedSetupInstructions(platform) {
    const config = platformConfig(platform);
    const summary = getElement("connected-setup-summary");
    const content = getElement("connected-setup-content");
    if (!summary || !content) {
      return;
    }
    summary.textContent = `${config.label} setup status: ${formatStatus(config.setupStatus)}.`;
    content.innerHTML = `
      <dl class="connected-account-details">
        <div><dt>Required account type</dt><dd>${escapeHtml(config.accountType)}</dd></div>
        <div><dt>Required permissions/scopes</dt><dd>${escapeHtml(config.requiredScopes.join(", "))}</dd></div>
        <div><dt>Setup status</dt><dd>${escapeHtml(formatStatus(config.setupStatus))}</dd></div>
      </dl>
      <ul class="safety-flag-list">
        ${config.setupInstructions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
      </ul>
    `;
    setConnectedMessage("success", `${config.label} setup instructions shown. Real publishing is still disabled.`);
  }

  function showReconnectPlaceholder(platform) {
    const config = platformConfig(platform);
    setConnectedMessage("error", `${config.label} reconnect is a placeholder until real OAuth is explicitly enabled.`);
    showConnectedSetupInstructions(platform);
  }

  function setupDemoEnvironment() {
    const settings = settingsAdapter.load();
    // Direct-file fallback only. The localhost bridge returns server-safe masked status.
    return {
      APP_ENV: settings.appEnvironment || "development",
      LOCAL_DATA_DIR: settings.localDataDirectory || "./data",
      INTEGRATIONS_MODE: "mock",
      ENABLE_REAL_OAUTH: "false",
      ENABLE_REAL_PUBLISHING: "false",
      TOKEN_STORAGE_MODE: "placeholder_not_stored",
      META_CLIENT_ID: "",
      META_CLIENT_SECRET: "",
      META_REDIRECT_URI: "",
      META_GRAPH_API_VERSION: "",
      META_ENABLE_REAL_OAUTH: "false",
      META_ENABLE_REAL_PUBLISHING: "false",
      GOOGLE_CLIENT_ID: "",
      GOOGLE_CLIENT_SECRET: "",
      GOOGLE_REDIRECT_URI: "",
      GOOGLE_ENABLE_REAL_OAUTH: "false",
      GOOGLE_ENABLE_REAL_PUBLISHING: "false",
      TIKTOK_CLIENT_KEY: "",
      TIKTOK_CLIENT_SECRET: "",
      TIKTOK_REDIRECT_URI: "",
      TIKTOK_ENABLE_REAL_OAUTH: "false",
      TIKTOK_ENABLE_REAL_PUBLISHING: "false",
      LINKEDIN_CLIENT_ID: "",
      LINKEDIN_CLIENT_SECRET: "",
      LINKEDIN_REDIRECT_URI: "",
      LINKEDIN_ENABLE_REAL_OAUTH: "false",
      LINKEDIN_ENABLE_REAL_PUBLISHING: "false",
      X_CLIENT_ID: "",
      X_CLIENT_SECRET: "",
      X_REDIRECT_URI: "",
      X_ENABLE_REAL_OAUTH: "false",
      X_ENABLE_REAL_PUBLISHING: "false",
    };
  }

  function maskSetupValue(name, value) {
    const cleanValue = String(value || "").trim();
    if (!cleanValue) {
      return "Not configured";
    }
    if (name.includes("SECRET") || name.includes("TOKEN") || name.includes("API_KEY")) {
      return "Configured, hidden";
    }
    if (name.includes("REDIRECT_URI")) {
      return cleanValue;
    }
    if (cleanValue.length <= 4) {
      return "Configured";
    }
    return `${cleanValue.slice(0, 2)}...${cleanValue.slice(-2)}`;
  }

  function setupPlatformStatus(config, environment) {
    const requiredEnvVars = config.requiredEnvVars || [];
    const optionalEnvVars = config.optionalEnvVars || [];
    const missingRequired = requiredEnvVars.filter((name) => !String(environment[name] || "").trim());
    const realPublishingFlag = optionalEnvVars.find((name) => name.endsWith("ENABLE_REAL_PUBLISHING"));
    const realOAuthFlag = optionalEnvVars.find((name) => name.endsWith("ENABLE_REAL_OAUTH"));
    const integrationsMode = environment.INTEGRATIONS_MODE || "mock";
    const platformRealPublishingRequested = String(environment[realPublishingFlag] || "false").toLowerCase() === "true";
    const globalRealPublishingRequested = String(environment.ENABLE_REAL_PUBLISHING || "false").toLowerCase() === "true";
    const platformRealOAuthRequested = String(environment[realOAuthFlag] || "false").toLowerCase() === "true";
    const globalRealOAuthRequested = String(environment.ENABLE_REAL_OAUTH || "false").toLowerCase() === "true";
    const realNetworkEnabled = String(environment.ENABLE_REAL_NETWORK_CALLS || "false").toLowerCase() === "true";
    const mockConnectAvailable = mockConnectPlatformIds.includes(config.id);
    const status = platformRealPublishingRequested || globalRealPublishingRequested
      ? "publishing_disabled_by_policy"
      : integrationsMode === "disabled"
        ? "disabled"
        : integrationsMode === "mock"
          ? "mock_ready"
          : integrationsMode === "real_oauth" && globalRealOAuthRequested && platformRealOAuthRequested && missingRequired.length
            ? "missing_config"
            : integrationsMode === "real_oauth" && globalRealOAuthRequested && platformRealOAuthRequested && !realNetworkEnabled
              ? "real_network_disabled"
              : integrationsMode === "real_oauth" && globalRealOAuthRequested && platformRealOAuthRequested
                ? "real_oauth_ready"
                : "disabled";
    const envVars = requiredEnvVars.concat(optionalEnvVars).map((name) => ({
      name,
      required: requiredEnvVars.includes(name),
      configured: Boolean(String(environment[name] || "").trim()),
      displayValue: maskSetupValue(name, environment[name]),
      secret: name.includes("SECRET") || name.includes("TOKEN"),
    }));
    const fallbackRedirect = `http://localhost:8000/api/connect/${config.id}/callback`;
    return {
      ...config,
      status,
      envVars,
      missingRequired,
      mockConnectAvailable,
      realOAuthAvailable: status === "real_oauth_ready",
      realPublishingAvailable: false,
      redirectUri: environment[config.redirectEnvVar] || fallbackRedirect,
      checklist: [
        "Stay in mock mode while learning the setup flow.",
        missingRequired.length
          ? `Add missing env vars later: ${missingRequired.join(", ")}.`
          : "Required env vars are present locally.",
        "Confirm the redirect URI in the provider developer app.",
        "Run a mock connection test before real OAuth work.",
        "Keep real publishing disabled until a future safety-gated batch.",
      ],
    };
  }

  function normalizeServerIntegrationSetup(serverStatus) {
    const platformStatuses = connectedPlatformConfigs.map((config) => {
      const safeStatus = serverStatus.platforms?.[config.id] || {};
      return {
        ...config,
        ...safeStatus,
        id: config.id,
        label: safeStatus.label || config.label,
        setupStatus: safeStatus.connectorFeatureStatus || config.setupStatus,
        accountType: safeStatus.requiredAccountType || config.accountType,
        requiredScopes: safeStatus.requiredScopes || config.requiredScopes,
        missingRequired: safeStatus.missingRequiredEnvVars || [],
        envVars: Object.values(safeStatus.envVars || {}),
        checklist: safeStatus.checklist || config.setupInstructions,
        docsLinks: safeStatus.docsLinks || config.docsLinks,
        redirectUri: safeStatus.redirectUri || `http://localhost:8000/api/connect/${config.id}/callback`,
        realPublishingAvailable: false,
      };
    });
    return {
      ...serverStatus,
      platforms: platformStatuses,
      summary: {
        ready: platformStatuses.filter((item) => item.status === "real_oauth_ready").length,
        missing: platformStatuses.filter((item) => item.status === "missing_config").length,
        mockReady: platformStatuses.filter((item) => item.status === "mock_ready").length,
        disabled: platformStatuses.filter((item) => item.status === "disabled").length,
        publishingBlocked: platformStatuses.filter((item) => item.status === "publishing_disabled_by_policy").length,
        errors: serverStatus.errorCodes?.length || 0,
      },
    };
  }

  function validateIntegrationSetupConfig(environment = null) {
    const serverStatus = environment ? null : activeApiBridge()?.snapshot?.integrationSetup;
    if (serverStatus) {
      return normalizeServerIntegrationSetup(serverStatus);
    }
    const resolvedEnvironment = environment || setupDemoEnvironment();
    const platformStatuses = connectedPlatformConfigs.map((config) => setupPlatformStatus(config, resolvedEnvironment));
    const summary = {
      ready: platformStatuses.filter((item) => item.status === "real_oauth_ready").length,
      missing: platformStatuses.filter((item) => item.status === "missing_config").length,
      mockReady: platformStatuses.filter((item) => item.status === "mock_ready").length,
      disabled: platformStatuses.filter((item) => item.status === "disabled").length,
      publishingBlocked: platformStatuses.filter((item) => item.status === "publishing_disabled_by_policy").length,
      errors: 0,
    };
    return {
      appEnvironment: resolvedEnvironment.APP_ENV || "development",
      localDataDirectory: resolvedEnvironment.LOCAL_DATA_DIR || "./data",
      integrationsMode: resolvedEnvironment.INTEGRATIONS_MODE || "mock",
      tokenStorageMode: resolvedEnvironment.TOKEN_STORAGE_MODE || "placeholder_not_stored",
      realOAuthEnabled: resolvedEnvironment.ENABLE_REAL_OAUTH === "true",
      realPublishingEnabled: resolvedEnvironment.ENABLE_REAL_PUBLISHING === "true",
      realPublishingAvailable: false,
      platforms: platformStatuses,
      summary,
    };
  }

  function selectedSetupPlatform(status) {
    return status.platforms.find((platform) => platform.id === setupState.selectedPlatformId) || status.platforms[0];
  }

  function setupStatusBadge(status) {
    if (status === "real_oauth_ready") return "local-only";
    if (status === "mock_ready") return "mock-mode";
    return "needs-review";
  }

  function renderSocialSetup() {
    const summary = getElement("social-setup-summary");
    const list = getElement("social-setup-platform-list");
    const detail = getElement("social-setup-detail-panel");
    if (!summary || !list || !detail) {
      return;
    }
    const status = validateIntegrationSetupConfig();
    const selected = selectedSetupPlatform(status);
    summary.innerHTML = `
      <article><strong>${status.summary.mockReady}</strong><span>Mock ready</span></article>
      <article><strong>${status.summary.missing}</strong><span>Missing configuration</span></article>
      <article><strong>${status.summary.disabled + status.summary.publishingBlocked}</strong><span>Disabled or policy-blocked</span></article>
      <article><strong>0</strong><span>Real publishing available</span></article>
    `;
    list.innerHTML = status.platforms
      .map((platform) => `
        <button class="social-setup-card ${platform.id === selected.id ? "selected" : ""}" type="button" data-setup-platform="${escapeHtml(platform.id)}">
          <span class="connected-platform-badge" aria-hidden="true">${escapeHtml(platform.badge)}</span>
          <span>
            <strong>${escapeHtml(platform.label)}</strong>
            <small>${escapeHtml(formatStatus(platform.status))}</small>
          </span>
          <span class="card-status ${setupStatusBadge(platform.status)}">${escapeHtml(formatStatus(platform.setupStatus))}</span>
        </button>
      `)
      .join("");
    getElement("social-setup-detail-title").textContent = `${selected.label} setup`;
    getElement("social-setup-detail-status").textContent = formatStatus(selected.status);
    getElement("social-setup-redirect-uri").textContent = selected.redirectUri;
    getElement("social-setup-account-type").textContent = selected.accountType;
    getElement("social-setup-scopes").textContent = selected.requiredScopes.length
      ? selected.requiredScopes.join(", ")
      : "Scopes are placeholders until real OAuth is implemented.";
    getElement("social-setup-feature-status").textContent = formatStatus(selected.setupStatus);
    getElement("social-setup-mock-mode").textContent = selected.mockConnectAvailable
      ? "Mock connection test available"
      : "Mock connection test placeholder";
    getElement("social-setup-real-oauth").textContent = selected.realOAuthAvailable
      ? "Real OAuth configured, still guarded"
      : "Real OAuth unavailable or disabled";
    getElement("social-setup-real-publishing").textContent = "Real publishing disabled in this build";
    getElement("social-setup-env-list").innerHTML = selected.envVars
      .map((envVar) => `
        <div class="setup-env-row">
          <span>${escapeHtml(envVar.name)}</span>
          <strong>${envVar.required ? "Required" : "Optional"}</strong>
          <em>${escapeHtml(envVar.displayValue)}</em>
        </div>
      `)
      .join("");
    getElement("social-setup-checklist").innerHTML = selected.checklist
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
    getElement("social-setup-docs-links").innerHTML = selected.docsLinks
      .map((item) => `<li>${escapeHtml(item)}</li>`)
      .join("");
    getElement("social-setup-mock-test").disabled = !selected.mockConnectAvailable;
  }

  function setSocialSetupMessage(kind, text) {
    const error = getElement("social-setup-action-error");
    const success = getElement("social-setup-action-message");
    if (!error || !success) {
      return;
    }
    error.hidden = kind !== "error";
    success.hidden = kind !== "success";
    error.textContent = kind === "error" ? text : "";
    success.textContent = kind === "success" ? text : "";
  }

  function selectSetupPlatform(platform) {
    setupState.selectedPlatformId = platform;
    setSocialSetupMessage("", "");
    renderSocialSetup();
  }

  async function runSetupMockConnectionTest() {
    const status = validateIntegrationSetupConfig();
    const selected = selectedSetupPlatform(status);
    if (!selected.mockConnectAvailable) {
      setSocialSetupMessage("error", `${selected.label} mock connection is a placeholder for a later batch.`);
      return;
    }
    await mockConnectPlatform(selected.id);
    setSocialSetupMessage("success", `${selected.label} mock connection test completed locally. No real API was called.`);
    renderSocialSetup();
  }

  function copySetupRedirectUri() {
    const status = validateIntegrationSetupConfig();
    const selected = selectedSetupPlatform(status);
    if (!navigator.clipboard) {
      setSocialSetupMessage("error", "Clipboard access is unavailable in this browser.");
      return;
    }
    navigator.clipboard
      .writeText(selected.redirectUri)
      .then(() => setSocialSetupMessage("success", "Redirect URI copied. It is not a secret."))
      .catch(() => setSocialSetupMessage("error", "Could not copy the redirect URI."));
  }

  function chooseAddKeysLater() {
    setSocialSetupMessage("success", "No problem. Keep mock mode on and use manual export until you are ready to add API keys.");
  }

  function handleConnectedAccountsClick(event) {
    const button = event.target.closest("[data-connected-action]");
    if (!button) {
      return;
    }
    const action = button.dataset.connectedAction;
    if (action === "connect") {
      mockConnectPlatform(button.dataset.platform);
    }
    if (action === "disconnect") {
      disconnectConnectedAccount(button.dataset.accountId);
    }
    if (action === "validate") {
      validateConnectedAccount(button.dataset.accountId);
    }
    if (action === "setup") {
      showConnectedSetupInstructions(button.dataset.platform);
    }
    if (action === "reconnect") {
      showReconnectPlaceholder(button.dataset.platform);
    }
  }

  function selectQueueItem(itemId) {
    queueState.selectedItemId = itemId;
    setQueueMessage("", "");
    renderPublishQueue();
  }

  function runQueuePreflight(item) {
    const post = scheduledPostForQueueItem(item);
    const errors = [];
    const warnings = ["manual_export_only: Manual export is the safe path; future real publishing remains disabled."];
    const settings = settingsAdapter.load();
    if (settings.emergencyPauseEnabled) {
      errors.push("emergency_pause_enabled: Emergency pause blocks queue readiness and mock publishing.");
    }
    if (!post) {
      errors.push("missing_scheduled_post: Queue item has no related scheduled post.");
    }
    if (post && ["canceled", "completed", "missed"].includes(post.status)) {
      errors.push(`scheduled_post_${post.status}: Scheduled post is not active.`);
    }
    if (!platformIds.includes(item.platform)) {
      errors.push("invalid_platform: Queue platform is not supported.");
    }
    if (!post?.captionSnapshot?.trim()) {
      errors.push("missing_caption: Caption snapshot is required.");
    }
    const flags = post?.scheduleMetadata?.safetyFlags || [];
    const critical = flags.filter((flag) => criticalQueueFlags.has(flag));
    if (critical.length) {
      errors.push(`critical_safety_flags: Resolve critical safety flags before queue readiness: ${critical.join(", ")}`);
    }
    const mediaIds = post?.mediaAssetIds || [];
    if (mediaRequiredPlatforms.has(item.platform) && !mediaIds.length) {
      errors.push("missing_required_media: Platform requires linked media.");
    }
    const mediaAssets = mediaLibraryAdapter.load();
    const missingMedia = mediaIds.filter((mediaId) => !mediaAssets.some((asset) => asset.id === mediaId));
    if (missingMedia.length) {
      errors.push(`missing_linked_media: Linked media does not exist: ${missingMedia.join(", ")}`);
    }
    if (["youtube", "tiktok"].includes(item.platform) && !post?.scheduleMetadata?.headline?.trim()) {
      errors.push("missing_required_metadata: Title/headline is required for this platform.");
    }
    const account = queueAccountReadiness(item, errors);
    warnings.push(...account.accountWarnings);
    return {
      eligible: errors.length === 0,
      errors,
      warnings: uniqueStrings(warnings),
      preflightStatus: errors.length
        ? errors.some((message) => message.startsWith("emergency_pause_enabled"))
          ? "blocked"
          : "errors"
        : "passed",
      accountCheckStatus: account.accountCheckStatus,
      matchedSocialAccountId: account.matchedSocialAccountId,
      accountWarnings: account.accountWarnings,
      accountErrors: account.accountErrors,
      missingScopes: account.missingScopes,
      requiresReauth: account.requiresReauth,
      connectionStatus: account.connectionStatus,
      realPublishingEligible: account.realPublishingEligible,
      manualExportEligible: account.manualExportEligible,
      mockPublishEligible: account.mockPublishEligible,
    };
  }

  function updateQueueAndScheduled(queueItem, scheduledPost, queueUpdates, scheduledUpdates, action, notes) {
    const now = new Date().toISOString();
    const nextQueue = normalizePublishQueueItem({ ...queueItem, ...queueUpdates, updatedAt: now });
    savePublishQueueItems(loadPublishQueueItems().map((item) => (item.id === queueItem.id ? nextQueue : item)));
    if (scheduledPost && scheduledUpdates) {
      const nextScheduled = normalizeScheduledPost({ ...scheduledPost, ...scheduledUpdates, updatedAt: now });
      saveScheduledPosts(loadScheduledPosts().map((post) => (post.id === scheduledPost.id ? nextScheduled : post)));
      appendCalendarAuditLog(
        scheduledPost.id,
        action,
        notes,
        {
          publishQueueItemId: queueItem.id,
          queueStatus: nextQueue.queueStatus,
          scheduledStatus: nextScheduled.status,
        },
      );
    }
    queueState.selectedItemId = nextQueue.id;
    renderPublishQueue();
    return nextQueue;
  }

  async function runSelectedQueuePreflight() {
    const item = selectedQueueItem();
    if (!item) {
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/publish-queue/${encodeURIComponent(item.id)}/preflight`, {
          method: "POST",
          body: {},
        });
        await bridge.sync();
        setQueueMessage("success", "Preflight recorded in local SQLite. No external API was called.");
        renderPublishQueue();
      } catch (error) {
        setQueueMessage("error", error.message || "Local SQLite preflight could not be completed.");
      }
      return;
    }
    const post = scheduledPostForQueueItem(item);
    const result = runQueuePreflight(item);
    const queueStatus = result.eligible ? "ready" : "blocked";
    const scheduledStatus = result.eligible && new Date(item.dueAt) <= new Date()
      ? "queued"
      : result.eligible
        ? post?.status || "scheduled"
        : "needs_attention";
    const updatedQueue = updateQueueAndScheduled(
      item,
      post,
      {
        queueStatus,
        preflightStatus: result.preflightStatus,
        preflightErrors: result.errors,
        preflightWarnings: result.warnings,
        accountCheckStatus: result.accountCheckStatus,
        matchedSocialAccountId: result.matchedSocialAccountId,
        accountWarnings: result.accountWarnings,
        accountErrors: result.accountErrors,
        missingScopes: result.missingScopes,
        requiresReauth: result.requiresReauth,
        connectionStatus: result.connectionStatus,
        realPublishingEligible: result.realPublishingEligible,
        manualExportEligible: result.manualExportEligible,
        mockPublishEligible: result.mockPublishEligible,
        lastCheckedAt: new Date().toISOString(),
      },
      post ? { status: scheduledStatus } : null,
      "queue_preflight_checked",
      "Local queue preflight checked. No publishing was performed.",
    );
    appendPublishAttempt(updatedQueue, post, "preflight", result.eligible ? "succeeded" : "failed", {
      errorCode: result.errors[0]?.split(":", 1)[0] || "",
      errorMessage: result.errors.join("; "),
      note: "Local preflight check recorded. No external API was called.",
    });
    setQueueMessage(result.eligible ? "success" : "error", result.eligible ? "Preflight passed locally. Item is ready for manual/mock action." : "Preflight blocked this item. Review the errors.");
    renderPublishQueue();
  }

  async function markSelectedQueueManualExported() {
    const item = selectedQueueItem();
    if (!item) {
      return;
    }
    if (["mock_published", "manually_exported", "canceled", "skipped"].includes(item.queueStatus)) {
      setQueueMessage("error", "This queue item is already processed or canceled.");
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/publish-queue/${encodeURIComponent(item.id)}/mark-manually-exported`, {
          method: "POST",
          body: {},
        });
        await bridge.sync();
        setQueueMessage("success", "Manual export recorded in local SQLite. No external API was called.");
        renderPublishQueue();
      } catch (error) {
        setQueueMessage("error", error.message || "Manual export completion could not be recorded.");
      }
      return;
    }
    const post = scheduledPostForQueueItem(item);
    const updatedQueue = updateQueueAndScheduled(
      item,
      post,
      { queueStatus: "manually_exported" },
      post ? { status: "completed" } : null,
      "manual_export_recorded",
      "Manual export recorded locally. No external API was called.",
    );
    appendPublishAttempt(updatedQueue, post, "manual_export", "succeeded", {
      note: "Manual export recorded locally. No external API was called.",
    });
    setQueueMessage("success", "Manual export recorded locally. No external API was called.");
    renderPublishQueue();
  }

  async function mockPublishSelectedQueueItem() {
    const item = selectedQueueItem();
    if (!item) {
      return;
    }
    if (settingsAdapter.load().emergencyPauseEnabled) {
      setQueueMessage("error", "Emergency pause blocks mock publishing.");
      return;
    }
    if (!item.mockPublishEnabled) {
      setQueueMessage("error", "Mock publishing is not enabled for this queue item.");
      return;
    }
    if (item.preflightStatus !== "passed" || item.queueStatus !== "ready") {
      setQueueMessage("error", "Mock publish requires passed preflight and ready queue status.");
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/publish-queue/${encodeURIComponent(item.id)}/mock-publish`, {
          method: "POST",
          body: {},
        });
        await bridge.sync();
        setQueueMessage("success", "Mock publish recorded in local SQLite. No external API was called.");
        renderPublishQueue();
      } catch (error) {
        setQueueMessage("error", error.message || "Mock publish could not be recorded.");
      }
      return;
    }
    const post = scheduledPostForQueueItem(item);
    const updatedQueue = updateQueueAndScheduled(
      item,
      post,
      { queueStatus: "mock_published" },
      post ? { status: "completed" } : null,
      "mock_publish_recorded",
      "Mock publish recorded locally. No external API was called.",
    );
    appendPublishAttempt(updatedQueue, post, "mock_publish", "succeeded", {
      note: "Mock publish recorded locally. No external API was called.",
    });
    setQueueMessage("success", "Mock publish recorded locally. No external API was called.");
    renderPublishQueue();
  }

  async function cancelSelectedQueueItem() {
    const item = selectedQueueItem();
    if (!item) {
      return;
    }
    if (!window.confirm("Cancel this local queue item? No draft or media will be deleted.")) {
      return;
    }
    const post = scheduledPostForQueueItem(item);
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/publish-queue/${encodeURIComponent(item.id)}/cancel`, {
          method: "POST",
          body: { reason: "Queue item canceled locally by owner." },
        });
        await bridge.sync();
        setQueueMessage("success", "Queue item canceled in local SQLite.");
        renderPublishQueue();
      } catch (error) {
        setQueueMessage("error", error.message || "Queue item could not be canceled.");
      }
      return;
    }
    const shouldCancelScheduled = post && !["completed", "canceled"].includes(post.status);
    updateQueueAndScheduled(
      item,
      post,
      { queueStatus: "canceled" },
      shouldCancelScheduled ? { status: "canceled", canceledAt: new Date().toISOString() } : null,
      "queue_item_canceled",
      "Queue item canceled locally. No content was deleted or published.",
    );
    setQueueMessage("success", "Queue item canceled locally.");
  }

  function copySelectedQueueCaption() {
    const item = selectedQueueItem();
    if (!item) {
      return;
    }
    const caption = queueCaption(item);
    if (!navigator.clipboard) {
      setQueueMessage("error", "Clipboard access is unavailable in this browser.");
      return;
    }
    navigator.clipboard
      .writeText(caption)
      .then(() => setQueueMessage("success", "Caption copied for manual posting only."))
      .catch(() => setQueueMessage("error", "Could not copy caption."));
  }

  async function exportSelectedQueuePackage() {
    const item = selectedQueueItem();
    if (!item) {
      return;
    }
    if (settingsAdapter.load().emergencyPauseEnabled) {
      setQueueMessage("error", "Emergency pause blocks manual export packages in the MVP.");
      return;
    }
    if (item.queueStatus === "canceled") {
      setQueueMessage("error", "Canceled queue items cannot be exported.");
      return;
    }
    if (["errors", "blocked"].includes(item.preflightStatus)) {
      setQueueMessage("error", "Resolve failed preflight before exporting a manual package.");
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        const result = await bridge.request(`/api/publish-queue/${encodeURIComponent(item.id)}/export-package`, {
          method: "POST",
          body: {},
        });
        setQueueMessage("success", `Manual export package created locally at ${result.exportPath}. Queue status was not changed.`);
      } catch (error) {
        setQueueMessage("error", error.message || "Manual export package could not be created.");
      }
      return;
    }
    const post = scheduledPostForQueueItem(item);
    const metadata = post?.scheduleMetadata || {};
    const body = [
      "Local Social AI Manager - manual export package mirror",
      "Real publishing disabled. This browser demo downloads a local mirror only.",
      "The SQLite source-of-truth exporter creates data/exports/manual-posts/YYYY-MM-DD/platform-slug-queueItemId/.",
      "Do not treat this as an automatic publish.",
      "",
      `Platform: ${item.platform}`,
      `Due: ${formatDateTime(item.dueAt)} (${item.timezone})`,
      `Queue status: ${formatStatus(item.queueStatus)}`,
      `Preflight status: ${formatStatus(item.preflightStatus)}`,
      "",
      "Caption:",
      post?.captionSnapshot || "",
      "",
      "Hashtags:",
      (metadata.hashtags || []).join(" "),
      "",
      "CTA:",
      metadata.callToAction || "",
      "",
      "Media asset IDs:",
      (post?.mediaAssetIds || []).join(", ") || "None",
      "",
      "Preflight errors:",
      item.preflightErrors.join("; ") || "None",
      "",
      "Preflight warnings:",
      item.preflightWarnings.join("; ") || "None",
      "",
      "Next step:",
      "After posting/exporting manually, use Mark manually exported. This download does not change queue status.",
    ].join("\n");
    const blob = new Blob([body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${item.id}-manual-export-package.txt`;
    link.click();
    URL.revokeObjectURL(url);
    setQueueMessage("success", "Manual export package mirror downloaded locally. Queue status was not changed.");
  }

  function filteredCalendarPosts() {
    const platform = getElement("calendar-platform-filter")?.value || "all";
    const status = getElement("calendar-status-filter")?.value || "all";
    let posts = loadScheduledPosts().slice();

    if (calendarState.view !== "list") {
      const rangeStart = calendarState.view === "month"
        ? startOfMonth(calendarState.cursorDate)
        : startOfWeek(calendarState.cursorDate);
      const rangeEnd = calendarState.view === "month"
        ? endOfMonth(calendarState.cursorDate)
        : endOfWeek(calendarState.cursorDate);
      posts = posts.filter((post) => {
        const scheduled = new Date(post.scheduledFor);
        return scheduled >= rangeStart && scheduled <= rangeEnd;
      });
    }

    return posts
      .filter((post) => platform === "all" || post.platform === platform)
      .filter((post) => status === "all" || post.status === status)
      .sort((left, right) => new Date(left.scheduledFor) - new Date(right.scheduledFor));
  }

  function calendarCardMarkup(post) {
    const queue = findQueueItemForPost(post);
    const metadata = post.scheduleMetadata || {};
    const title = metadata.hook || metadata.headline || "Scheduled post";
    const flags = Array.isArray(metadata.safetyFlags) ? metadata.safetyFlags.length : 0;
    const caption = post.captionSnapshot || "";
    return `
      <article class="calendar-post-card" data-calendar-post-id="${escapeHtml(post.id)}" tabindex="0" role="button" aria-label="Open scheduled ${escapeHtml(post.platform)} post">
        <header class="draft-card-header">
          <span class="result-platform">${escapeHtml(post.platform)}</span>
          <span class="result-status">${escapeHtml(formatStatus(post.status))}</span>
        </header>
        <h3>${escapeHtml(title)}</h3>
        <p class="result-meta">${escapeHtml(formatDateTime(post.scheduledFor))}</p>
        <p class="result-caption">${escapeHtml(caption.slice(0, 140))}${caption.length > 140 ? "..." : ""}</p>
        <div class="draft-card-metrics">
          <span>Media: ${escapeHtml(String(post.mediaAssetIds.length))}</span>
          <span>Safety flags: ${escapeHtml(String(flags))}</span>
          <span>Queue: ${escapeHtml(queue ? formatStatus(queue.queueStatus) : "none")}</span>
        </div>
        <p class="result-meta">${escapeHtml(post.brandName || "Business not set")}</p>
      </article>
    `;
  }

  function renderCalendarAgenda(posts) {
    if (!posts.length) {
      return "";
    }
    const groups = new Map();
    posts.forEach((post) => {
      const key = new Date(post.scheduledFor).toISOString().slice(0, 10);
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key).push(post);
    });
    return Array.from(groups.values())
      .map(
        (items) => `
          <section class="calendar-agenda-day">
            <h3 class="calendar-agenda-date">${escapeHtml(formatDate(items[0].scheduledFor))}</h3>
            <div class="calendar-agenda-items">${items.map(calendarCardMarkup).join("")}</div>
          </section>
        `
      )
      .join("");
  }

  function updateCalendarFilterBadge() {
    const badge = getElement("calendar-filter-badge");
    if (!badge) {
      return;
    }
    const platform = getElement("calendar-platform-filter")?.value || "all";
    const status = getElement("calendar-status-filter")?.value || "all";
    const active = (platform !== "all" ? 1 : 0) + (status !== "all" ? 1 : 0);
    badge.textContent = String(active);
    badge.hidden = active === 0;
  }

  function calendarDaysForView() {
    if (calendarState.view === "week") {
      const start = startOfWeek(calendarState.cursorDate);
      return Array.from({ length: 7 }, (_, index) => addDays(start, index));
    }
    const monthStart = startOfMonth(calendarState.cursorDate);
    const gridStart = startOfWeek(monthStart);
    return Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));
  }

  function renderCalendarGrid(posts) {
    const grid = getElement("calendar-grid");
    const list = getElement("calendar-list");
    if (!grid || !list) {
      return;
    }
    if (calendarState.view === "list") {
      grid.hidden = true;
      list.hidden = false;
      list.innerHTML = renderCalendarAgenda(posts);
      return;
    }

    grid.hidden = false;
    list.hidden = true;
    grid.classList.toggle("month-view", calendarState.view === "month");
    const days = calendarDaysForView();
    grid.innerHTML = days
      .map((day) => {
        const dayPosts = posts.filter((post) => sameDay(new Date(post.scheduledFor), day));
        const outsideMonth =
          calendarState.view === "month" && day.getMonth() !== calendarState.cursorDate.getMonth();
        return `
          <section class="calendar-day ${outsideMonth ? "outside-month" : ""}">
            <header>
              <span>${escapeHtml(day.toLocaleDateString(undefined, { weekday: "short" }))}</span>
              <strong>${escapeHtml(String(day.getDate()))}</strong>
            </header>
            <div class="calendar-day-items">
              ${dayPosts.length ? dayPosts.map(calendarCardMarkup).join("") : '<p class="result-meta">No posts</p>'}
            </div>
          </section>
        `;
      })
      .join("");
  }

  function setCalendarMessage(kind, text) {
    const success = getElement("calendar-action-message");
    const error = getElement("calendar-action-error");
    if (!success || !error) {
      return;
    }
    success.hidden = kind !== "success";
    error.hidden = kind !== "error";
    success.textContent = kind === "success" ? text : "";
    error.textContent = kind === "error" ? text : "";
  }

  function selectedCalendarPost() {
    if (!calendarState.selectedPostId) {
      return null;
    }
    return loadScheduledPosts().find((post) => post.id === calendarState.selectedPostId) || null;
  }

  function renderCalendarDetail() {
    const post = selectedCalendarPost();
    const empty = getElement("calendar-detail-empty");
    const content = getElement("calendar-detail-content");
    const modal = getElement("calendar-detail-modal");
    if (!empty || !content) {
      return;
    }
    if (!post) {
      empty.hidden = false;
      content.hidden = true;
      if (modal) modal.hidden = true;
      return;
    }
    if (modal) modal.hidden = false;
    const queue = findQueueItemForPost(post);
    const metadata = post.scheduleMetadata || {};
    empty.hidden = true;
    content.hidden = false;
    getElement("calendar-detail-status").textContent = formatStatus(post.status);
    getElement("calendar-detail-summary").textContent = metadata.hook || metadata.headline || "Local scheduled post";
    getElement("calendar-detail-platform").textContent = post.platform;
    getElement("calendar-detail-datetime").textContent = formatDateTime(post.scheduledFor);
    getElement("calendar-detail-timezone").textContent = post.timezone;
    getElement("calendar-detail-queue-status").textContent = queue ? formatStatus(queue.queueStatus) : "No queue item";
    getElement("calendar-detail-preflight").textContent = queue
      ? formatStatus(queue.preflightStatus)
      : formatStatus(post.preflightSnapshot.status || "not_checked");
    getElement("calendar-detail-draft-id").textContent = post.generatedPostId || "-";
    getElement("calendar-detail-created").textContent = formatDateTime(post.createdAt);
    getElement("calendar-detail-updated").textContent = formatDateTime(post.updatedAt);
    getElement("calendar-detail-caption").textContent = post.captionSnapshot || "-";
    getElement("calendar-detail-hashtags").innerHTML = (metadata.hashtags || [])
      .map((tag) => `<span class="hashtag">${escapeHtml(tag)}</span>`)
      .join("");
    getElement("calendar-detail-cta").textContent = metadata.callToAction
      ? `CTA: ${metadata.callToAction}`
      : "CTA: none";
    getElement("calendar-detail-media").innerHTML = post.mediaAssetIds.length
      ? `<ul class="safety-flag-list">${post.mediaAssetIds.map((id) => `<li>${escapeHtml(id)}</li>`).join("")}</ul>`
      : '<p class="result-meta">No linked media assets.</p>';
    getElement("calendar-reschedule-datetime").value = datetimeLocalValue(post.scheduledFor);
    getElement("calendar-reschedule-timezone").value = post.timezone || defaultSettings.defaultTimezone;
    getElement("calendar-notes").value = post.userNotes || "";
    getElement("calendar-open-draft").href = "#drafts";
    getElement("calendar-open-draft").title = post.generatedPostId || "Open Drafts";
    getElement("calendar-view-queue-item").href = "#queue";
    getElement("calendar-view-queue-item").title = queue ? queue.id : "No queue item";
  }

  function renderCalendar() {
    const loading = getElement("calendar-loading-state");
    const error = getElement("calendar-error-state");
    const empty = getElement("calendar-empty-state");
    const range = getElement("calendar-range-label");
    if (!loading || !error || !empty || !range) {
      return;
    }

    try {
      loading.hidden = false;
      error.hidden = true;
      range.textContent = formatCalendarRange();
      const viewSelect = getElement("calendar-view-select");
      if (viewSelect) viewSelect.value = calendarState.view;
      const dateNav = getElement("calendar-date-nav");
      if (dateNav) dateNav.classList.toggle("is-hidden", calendarState.view === "list");
      updateCalendarFilterBadge();
      const posts = filteredCalendarPosts();
      if (calendarState.selectedPostId && !loadScheduledPosts().some((post) => post.id === calendarState.selectedPostId)) {
        calendarState.selectedPostId = null;
      }
      renderCalendarGrid(posts);
      empty.hidden = posts.length > 0;
      renderCalendarDetail();
    } catch (errorObject) {
      console.error("calendar: render failed", errorObject);
      error.hidden = false;
      empty.hidden = true;
    } finally {
      loading.hidden = true;
    }
  }

  function selectCalendarPost(postId) {
    calendarState.selectedPostId = postId;
    setCalendarMessage("", "");
    renderCalendar();
  }

  function closeCalendarDetail() {
    calendarState.selectedPostId = null;
    setCalendarMessage("", "");
    const modal = getElement("calendar-detail-modal");
    if (modal) modal.hidden = true;
    renderCalendarDetail();
  }

  function persistUpdatedCalendarPost(updatedPost, action, notes, changedFields) {
    const now = new Date().toISOString();
    const posts = loadScheduledPosts().map((post) =>
      post.id === updatedPost.id ? normalizeScheduledPost({ ...updatedPost, updatedAt: now }) : post
    );
    saveScheduledPosts(posts);
    appendCalendarAuditLog(updatedPost.id, action, notes, changedFields);
    renderCalendar();
  }

  async function rescheduleSelectedPost(event) {
    event.preventDefault();
    const post = selectedCalendarPost();
    if (!post) {
      return;
    }
    if (settingsAdapter.load().emergencyPauseEnabled) {
      setCalendarMessage("error", "Emergency pause blocks rescheduling active local posts.");
      return;
    }
    const queue = findQueueItemForPost(post);
    if (queue && !mutableQueueStatuses.includes(queue.queueStatus)) {
      setCalendarMessage("error", "Only waiting or blocked queue items can be rescheduled.");
      return;
    }
    const datetimeValue = getElement("calendar-reschedule-datetime").value;
    const parsed = new Date(datetimeValue);
    if (!datetimeValue || Number.isNaN(parsed.getTime())) {
      setCalendarMessage("error", "Choose a valid date and time before rescheduling.");
      return;
    }
    const nextScheduledFor = parsed.toISOString();
    const timezone = getElement("calendar-reschedule-timezone").value.trim() || defaultSettings.defaultTimezone;
    const notes = getElement("calendar-notes").value.trim();
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/calendar/${encodeURIComponent(post.id)}/reschedule`, {
          method: "POST",
          body: {
            scheduled_for: nextScheduledFor,
            timezone,
          },
        });
        await bridge.request(`/api/calendar/${encodeURIComponent(post.id)}/notes`, {
          method: "POST",
          body: { user_notes: notes },
        });
        await bridge.sync();
        setCalendarMessage("success", "Scheduled post rescheduled in local SQLite.");
        renderCalendar();
      } catch (error) {
        setCalendarMessage("error", error.message || "Scheduled post could not be rescheduled.");
      }
      return;
    }
    if (queue) {
      const queueItems = loadPublishQueueItems().map((item) =>
        item.id === queue.id
          ? normalizePublishQueueItem({
              ...item,
              dueAt: nextScheduledFor,
              timezone,
              updatedAt: new Date().toISOString(),
            })
          : item
      );
      savePublishQueueItems(queueItems);
    }
    persistUpdatedCalendarPost(
      { ...post, scheduledFor: nextScheduledFor, timezone, userNotes: notes },
      "rescheduled",
      "Scheduled post date/time updated locally. No publishing was performed.",
      {
        previousScheduledFor: post.scheduledFor,
        scheduledFor: nextScheduledFor,
        timezone,
      },
    );
    setCalendarMessage("success", "Scheduled post rescheduled locally.");
  }

  async function cancelSelectedPost() {
    const post = selectedCalendarPost();
    if (!post) {
      return;
    }
    if (!window.confirm("Cancel this scheduled post locally? This will not delete the draft.")) {
      return;
    }
    const queue = findQueueItemForPost(post);
    if (queue && processedQueueStatuses.includes(queue.queueStatus)) {
      setCalendarMessage("error", "Processed queue items cannot be canceled from Calendar.");
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/calendar/${encodeURIComponent(post.id)}/cancel`, {
          method: "POST",
          body: { reason: "Scheduled post canceled locally by owner." },
        });
        await bridge.sync();
        setCalendarMessage("success", "Scheduled post canceled in local SQLite.");
        renderCalendar();
      } catch (error) {
        setCalendarMessage("error", error.message || "Scheduled post could not be canceled.");
      }
      return;
    }
    const now = new Date().toISOString();
    if (queue) {
      const queueItems = loadPublishQueueItems().map((item) =>
        item.id === queue.id
          ? normalizePublishQueueItem({ ...item, queueStatus: "canceled", updatedAt: now })
          : item
      );
      savePublishQueueItems(queueItems);
    }
    persistUpdatedCalendarPost(
      { ...post, status: "canceled", canceledAt: now },
      "canceled",
      "Scheduled post canceled locally. No content was deleted or published.",
      {
        previousStatus: post.status,
        status: "canceled",
        publishQueueItemId: queue ? queue.id : "",
      },
    );
    setCalendarMessage("success", "Scheduled post canceled locally.");
  }

  async function markSelectedNeedsAttention() {
    const post = selectedCalendarPost();
    if (!post) {
      return;
    }
    const bridge = activeApiBridge();
    if (bridge) {
      try {
        await bridge.request(`/api/calendar/${encodeURIComponent(post.id)}/needs-attention`, {
          method: "POST",
          body: {},
        });
        await bridge.sync();
        setCalendarMessage("success", "Scheduled post marked needs attention in local SQLite.");
        renderCalendar();
      } catch (error) {
        setCalendarMessage("error", error.message || "Scheduled post could not be marked needs attention.");
      }
      return;
    }
    const queue = findQueueItemForPost(post);
    if (queue && mutableQueueStatuses.includes(queue.queueStatus)) {
      const queueItems = loadPublishQueueItems().map((item) =>
        item.id === queue.id
          ? normalizePublishQueueItem({
              ...item,
              queueStatus: "blocked",
              preflightStatus: "blocked",
              preflightErrors: item.preflightErrors.includes("needs_attention")
                ? item.preflightErrors
                : item.preflightErrors.concat("needs_attention"),
              updatedAt: new Date().toISOString(),
            })
          : item
      );
      savePublishQueueItems(queueItems);
    }
    persistUpdatedCalendarPost(
      { ...post, status: "needs_attention" },
      "marked_needs_attention",
      "Scheduled post marked needs attention locally.",
      { previousStatus: post.status, status: "needs_attention" },
    );
    setCalendarMessage("success", "Scheduled post marked needs attention.");
  }

  function copySelectedCaption() {
    const post = selectedCalendarPost();
    if (!post) {
      return;
    }
    if (!navigator.clipboard) {
      setCalendarMessage("error", "Clipboard access is unavailable in this browser.");
      return;
    }
    navigator.clipboard
      .writeText(post.captionSnapshot || "")
      .then(() => setCalendarMessage("success", "Caption copied. Manual posting only."))
      .catch(() => setCalendarMessage("error", "Could not copy caption."));
  }

  function setupCalendar() {
    const view = getElement("calendar-view");
    if (!view) {
      return;
    }
    renderCalendar();

    getElement("calendar-view-select").addEventListener("change", (event) => {
      calendarState.view = event.target.value;
      renderCalendar();
    });
    getElement("calendar-prev").addEventListener("click", () => {
      const nextDate = new Date(calendarState.cursorDate);
      if (calendarState.view === "month") {
        nextDate.setMonth(nextDate.getMonth() - 1);
      } else {
        nextDate.setDate(nextDate.getDate() - 7);
      }
      calendarState.cursorDate = nextDate;
      renderCalendar();
    });
    getElement("calendar-today").addEventListener("click", () => {
      calendarState.cursorDate = new Date();
      renderCalendar();
    });
    getElement("calendar-next").addEventListener("click", () => {
      const nextDate = new Date(calendarState.cursorDate);
      if (calendarState.view === "month") {
        nextDate.setMonth(nextDate.getMonth() + 1);
      } else {
        nextDate.setDate(nextDate.getDate() + 7);
      }
      calendarState.cursorDate = nextDate;
      renderCalendar();
    });
    getElement("calendar-platform-filter").addEventListener("change", renderCalendar);
    getElement("calendar-status-filter").addEventListener("change", renderCalendar);

    const filterToggle = getElement("calendar-filter-toggle");
    const filterPopover = getElement("calendar-filter-popover");
    if (filterToggle && filterPopover) {
      filterToggle.addEventListener("click", (event) => {
        event.stopPropagation();
        const willOpen = filterPopover.hidden;
        filterPopover.hidden = !willOpen;
        filterToggle.setAttribute("aria-expanded", willOpen ? "true" : "false");
      });
      document.addEventListener("click", (event) => {
        if (filterPopover.hidden) return;
        if (filterPopover.contains(event.target) || filterToggle.contains(event.target)) return;
        filterPopover.hidden = true;
        filterToggle.setAttribute("aria-expanded", "false");
      });
      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !filterPopover.hidden) {
          filterPopover.hidden = true;
          filterToggle.setAttribute("aria-expanded", "false");
        }
      });
    }
    getElement("calendar-filter-clear").addEventListener("click", () => {
      getElement("calendar-platform-filter").value = "all";
      getElement("calendar-status-filter").value = "all";
      renderCalendar();
    });
    getElement("calendar-grid").addEventListener("click", (event) => {
      const card = event.target.closest("[data-calendar-post-id]");
      if (card) selectCalendarPost(card.dataset.calendarPostId);
    });
    getElement("calendar-list").addEventListener("click", (event) => {
      const card = event.target.closest("[data-calendar-post-id]");
      if (card) selectCalendarPost(card.dataset.calendarPostId);
    });
    getElement("calendar-grid").addEventListener("keydown", (event) => {
      const card = event.target.closest("[data-calendar-post-id]");
      if (card && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        selectCalendarPost(card.dataset.calendarPostId);
      }
    });
    getElement("calendar-list").addEventListener("keydown", (event) => {
      const card = event.target.closest("[data-calendar-post-id]");
      if (card && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        selectCalendarPost(card.dataset.calendarPostId);
      }
    });
    getElement("calendar-detail-close").addEventListener("click", closeCalendarDetail);
    getElement("calendar-detail-modal").addEventListener("click", (event) => {
      if (event.target === event.currentTarget) closeCalendarDetail();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      const modal = getElement("calendar-detail-modal");
      if (modal && !modal.hidden) closeCalendarDetail();
    });
    getElement("calendar-reschedule-form").addEventListener("submit", rescheduleSelectedPost);
    getElement("calendar-cancel-button").addEventListener("click", cancelSelectedPost);
    getElement("calendar-copy-caption").addEventListener("click", copySelectedCaption);
    getElement("calendar-mark-needs-attention").addEventListener("click", markSelectedNeedsAttention);
    getElement("calendar-view-queue-item").addEventListener("click", (event) => {
      const post = selectedCalendarPost();
      const queue = post ? findQueueItemForPost(post) : null;
      if (!queue) {
        event.preventDefault();
        setCalendarMessage("error", "No publish queue item is linked to this scheduled post.");
        return;
      }
      queueState.selectedItemId = queue.id;
    });
  }

  function setupPublishQueue() {
    const view = getElement("queue-view");
    if (!view) {
      return;
    }
    renderPublishQueue();
    [
      "queue-platform-filter",
      "queue-status-filter",
      "queue-preflight-filter",
      "queue-date-filter",
      "queue-brand-filter",
      "queue-search",
    ].forEach((id) => {
      const control = getElement(id);
      if (!control) return;
      control.addEventListener("input", renderPublishQueue);
      control.addEventListener("change", renderPublishQueue);
    });
    getElement("queue-list").addEventListener("click", (event) => {
      const card = event.target.closest("[data-queue-item-id]");
      if (card) selectQueueItem(card.dataset.queueItemId);
    });
    getElement("queue-list").addEventListener("keydown", (event) => {
      const card = event.target.closest("[data-queue-item-id]");
      if (card && (event.key === "Enter" || event.key === " ")) {
        event.preventDefault();
        selectQueueItem(card.dataset.queueItemId);
      }
    });
    getElement("queue-run-preflight").addEventListener("click", runSelectedQueuePreflight);
    getElement("queue-manual-export").addEventListener("click", markSelectedQueueManualExported);
    getElement("queue-mock-publish").addEventListener("click", mockPublishSelectedQueueItem);
    getElement("queue-cancel").addEventListener("click", cancelSelectedQueueItem);
    getElement("queue-copy-caption").addEventListener("click", copySelectedQueueCaption);
    getElement("queue-export-package").addEventListener("click", exportSelectedQueuePackage);
    getElement("queue-open-calendar").addEventListener("click", () => {
      const item = selectedQueueItem();
      if (item) {
        calendarState.selectedPostId = item.scheduledPostId;
      }
    });
  }

  function setupConnectedAccounts() {
    const view = getElement("connected-view");
    if (!view) {
      return;
    }
    renderConnectedAccounts();
    getElement("connected-platform-grid").addEventListener("click", handleConnectedAccountsClick);
    getElement("connected-account-list").addEventListener("click", handleConnectedAccountsClick);
    getElement("connected-refresh").addEventListener("click", () => {
      setConnectedMessage("success", "Local mock connection status refreshed. No real API was called.");
      renderConnectedAccounts();
    });
  }

  function setupSocialSetup() {
    const view = getElement("social-setup-view");
    if (!view) {
      return;
    }
    renderSocialSetup();
    getElement("social-setup-platform-list").addEventListener("click", (event) => {
      const button = event.target.closest("[data-setup-platform]");
      if (button) {
        selectSetupPlatform(button.dataset.setupPlatform);
      }
    });
    getElement("social-setup-mock-test").addEventListener("click", runSetupMockConnectionTest);
    getElement("social-setup-copy-redirect").addEventListener("click", copySetupRedirectUri);
    getElement("social-setup-later").addEventListener("click", chooseAddKeysLater);
  }

  function setupOnboarding() {
    const view = getElement("onboarding-view");
    if (!view) {
      return;
    }

    renderOnboarding();

    getElement("onboarding-local-data-default")?.addEventListener("click", () => {
      setOnboardingMessage("success", "Default local data directory confirmed.");
    });

    getElement("onboarding-media-import")?.addEventListener("click", () => {
      getElement("onboarding-media-input")?.click();
    });

    getElement("onboarding-media-input")?.addEventListener("change", async (event) => {
      const files = Array.from(event.target.files || []);
      const status = getElement("onboarding-media-status");
      if (!files.length) {
        return;
      }
      try {
        const uploaded = [];
        for (const file of files) {
          const bridge = activeApiBridge();
          if (bridge) {
            uploaded.push(await bridge.upload("/api/media/import", file));
            await bridge.sync();
          } else {
            const asset = importedMediaAssetFromFile(file);
            mediaLibraryAdapter.add(asset);
            uploaded.push(asset);
          }
        }
        if (status) {
          status.textContent = `${uploaded.length} media item${uploaded.length === 1 ? "" : "s"} added locally.`;
        }
        renderSetupChecklist();
        setOnboardingMessage("success", "Media saved locally. You can organize details in Media Library.");
      } catch (error) {
        if (status) {
          status.textContent = "Media import failed.";
        }
        setOnboardingMessage("error", error.message || "Media could not be imported.");
      } finally {
        event.target.value = "";
      }
    });

    getElement("onboarding-media-skip")?.addEventListener("click", () => {
      const state = onboardingAdapter.loadLocal();
      onboardingAdapter.saveLocal({
        ...state,
        status: state.status === "not_started" ? "in_progress" : state.status,
        skippedSteps: uniqueStrings([...(state.skippedSteps || []), "media"]),
      });
      const status = getElement("onboarding-media-status");
      if (status) {
        status.textContent = "Media step skipped. You can upload real media later.";
      }
      setOnboardingMessage("success", "Media import skipped for now.");
      renderSetupChecklist();
    });

    getElement("onboarding-demo-draft")?.addEventListener("click", () => {
      onboardingDemoDraftRequested = true;
      const status = getElement("onboarding-demo-draft-status");
      if (status) {
        status.textContent = "Demo draft will be created when you complete onboarding.";
      }
      setOnboardingMessage("success", "Demo draft requested. It will be saved as needs review.");
    });

    getElement("onboarding-complete")?.addEventListener("click", completeOnboarding);
    getElement("onboarding-skip")?.addEventListener("click", skipOnboarding);
  }

  function routeFromHash() {
    const route = window.location.hash.replace("#", "") || "home";
    return supportedRoutes.includes(route)
      ? route
      : "home";
  }

  function setupRouting() {
    const links = document.querySelectorAll(".nav-link");
    const views = document.querySelectorAll(".route-view");

    function showRoute(route) {
      views.forEach((view) => {
        const isActive = view.dataset.route === route;
        view.hidden = !isActive;
        view.classList.toggle("active", isActive);
      });

      links.forEach((link) => {
        const isActive = link.getAttribute("href") === `#${route}`;
        link.classList.toggle("active", isActive);
        if (isActive) {
          link.setAttribute("aria-current", "page");
        } else {
          link.removeAttribute("aria-current");
        }
      });

      document.querySelectorAll(".nav-group").forEach((group) => {
        const hasActiveLink = Boolean(group.querySelector(".nav-link.active"));
        group.classList.toggle("active", hasActiveLink);
        group.open = hasActiveLink || (route === "home" && Boolean(group.querySelector('a[href="#generate"]')));
      });
    }

    window.addEventListener("hashchange", () => {
      showRoute(routeFromHash());
      if (routeFromHash() === "calendar") {
        renderCalendar();
      }
      if (routeFromHash() === "queue") {
        renderPublishQueue();
      }
      if (routeFromHash() === "connected") {
        renderConnectedAccounts();
      }
      if (routeFromHash() === "setup") {
        renderSocialSetup();
      }
      if (routeFromHash() === "safety") {
        renderSafetyCenter();
      }
      if (routeFromHash() === "backup") {
        renderBackupData();
      }
      if (routeFromHash() === "diagnostics") {
        renderDiagnostics();
      }
      if (routeFromHash() === "onboarding") {
        renderOnboarding();
      }
      if (routeFromHash() === "home") {
        renderControlCenter();
      }
    });

    showRoute(routeFromHash());
    if (routeFromHash() === "onboarding") {
      renderOnboarding();
    }
    if (routeFromHash() === "home") {
      renderControlCenter();
    }
    if (routeFromHash() === "queue") {
      renderPublishQueue();
    }
    if (routeFromHash() === "calendar") {
      renderCalendar();
    }
    if (routeFromHash() === "connected") {
      renderConnectedAccounts();
    }
    if (routeFromHash() === "setup") {
      renderSocialSetup();
    }
    if (routeFromHash() === "safety") {
      renderSafetyCenter();
    }
    if (routeFromHash() === "backup") {
      renderBackupData();
    }
    if (routeFromHash() === "diagnostics") {
      renderDiagnostics();
    }
  }

  function setupSafetyCenter() {
    const view = getElement("safety-view");
    if (!view) {
      return;
    }

    renderSafetyCenter();
    getElement("safety-refresh")?.addEventListener("click", refreshSafetyCenter);
    getElement("safety-export-report")?.addEventListener("click", () => {
      runKillSwitchAction("export_safety_report");
    });
    getElement("safety-emergency-toggle")?.addEventListener("change", toggleEmergencyPause);
    getElement("safety-automation-level")?.addEventListener("change", changeSafetyAutomationLevel);
    getElement("safety-kill-actions")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-safety-kill-action]");
      if (!button) {
        return;
      }
      runKillSwitchAction(button.dataset.safetyKillAction);
    });
  }

  function setupBackupData() {
    const view = getElement("backup-view");
    if (!view) {
      return;
    }

    renderBackupData();
    getElement("backup-create-form")?.addEventListener("submit", createBackup);
    getElement("backup-refresh-history")?.addEventListener("click", refreshBackupHistory);
    getElement("backup-restore-form")?.addEventListener("submit", previewRestore);
    getElement("backup-export-actions")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-backup-export-type]");
      if (!button) {
        return;
      }
      createBackup(button.dataset.backupExportType);
    });
    getElement("backup-history-list")?.addEventListener("click", (event) => {
      const button = event.target.closest("[data-backup-preview-path]");
      if (!button) {
        return;
      }
      const path = button.dataset.backupPreviewPath || "";
      const input = getElement("backup-restore-path");
      if (input) {
        input.value = path;
      }
      previewRestore(path);
    });
  }

  function setupDiagnostics() {
    const view = getElement("diagnostics-view");
    if (!view) {
      return;
    }

    renderDiagnostics();
    getElement("diagnostics-refresh")?.addEventListener("click", refreshDiagnostics);
    getElement("diagnostics-export-report")?.addEventListener("click", exportDiagnosticReport);
    getElement("diagnostics-copy-report")?.addEventListener("click", copyDiagnosticSummary);
    window.addEventListener("error", (event) => {
      recordFriendlyError(event.error || event.message, "window_error");
    });
    window.addEventListener("unhandledrejection", (event) => {
      recordFriendlyError(event.reason || "Unhandled promise rejection", "unhandled_rejection");
    });
  }

  function setupSettingsForm() {
    const form = getElement("settings-form");
    const resetButton = getElement("reset-settings");
    const pauseToggle = getElement("emergencyPauseEnabled");

    if (!form) {
      return;
    }

    applySettingsToForm(settingsAdapter.load());

    pauseToggle.addEventListener("change", (event) => {
      updatePauseDisplay(event.target.checked);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const settings = collectSettingsFromForm();
      const validationMessage = validateSettings(settings);

      if (validationMessage) {
        setMessage("error", validationMessage);
        return;
      }

      try {
        const savedSettings = await settingsAdapter.save(settings);
        applySettingsToForm(savedSettings);
        setMessage(
          "success",
          activeApiBridge()
            ? "Settings saved to local SQLite."
            : "Settings saved locally for this browser demo.",
        );
      } catch (error) {
        setMessage("error", error.message || "Settings could not be saved to local SQLite.");
      }
    });

    resetButton.addEventListener("click", async () => {
      try {
        const resetSettings = await settingsAdapter.reset();
        applySettingsToForm(resetSettings);
        setMessage(
          "success",
          activeApiBridge()
            ? "Settings reset to approval-required defaults in local SQLite."
            : "Demo settings reset to approval-required defaults.",
        );
      } catch (error) {
        setMessage("error", error.message || "Settings could not be reset in local SQLite.");
      }
    });

    getElement("settings-restart-onboarding")?.addEventListener("click", restartOnboarding);
  }

  function setupBrandBrainForm() {
    const form = getElement("brand-brain-form");
    const resetButton = getElement("reset-brand-brain");
    if (!form) {
      return;
    }

    applyBrandProfileToForm(brandBrainAdapter.load());

    document.querySelectorAll("[data-add-list-item]").forEach((button) => {
      button.addEventListener("click", () => {
        const target = getElement(button.dataset.addListItem);
        if (!target) {
          return;
        }
        target.value = target.value.trimEnd() ? `${target.value.trimEnd()}\n` : "";
        target.focus();
      });
    });

    form.addEventListener("input", () => {
      updateBrandMemorySummary(collectBrandProfileFromForm());
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const profile = collectBrandProfileFromForm();
      const validationMessage = validateBrandProfile(profile);

      if (validationMessage) {
        setBrandMessage("error", validationMessage);
        return;
      }

      try {
        const savedProfile = await brandBrainAdapter.save(profile);
        applyBrandProfileToForm(savedProfile);
        setBrandMessage(
          "success",
          activeApiBridge()
            ? "Brand Brain saved to local SQLite."
            : "Brand Brain saved locally for this browser demo.",
        );
      } catch (error) {
        setBrandMessage("error", error.message || "Brand Brain could not be saved to local SQLite.");
      }
    });

    resetButton.addEventListener("click", async () => {
      try {
        const resetProfile = await brandBrainAdapter.reset();
        applyBrandProfileToForm(resetProfile);
        setBrandMessage(
          "success",
          activeApiBridge()
            ? "Brand Brain reset to demo defaults in local SQLite."
            : "Demo Brand Brain reset.",
        );
      } catch (error) {
        setBrandMessage("error", error.message || "Brand Brain could not be reset in local SQLite.");
      }
    });
  }

  function setupMediaLibrary() {
    const importButton = getElement("media-import-button");
    const importInput = getElement("media-import-input");
    const resetButton = getElement("media-reset-button");
    const grid = getElement("media-grid");
    const detailPanel = getElement("media-detail-panel");
    const detailClose = getElement("media-detail-close");
    const metadataForm = getElement("media-metadata-form");
    const searchInput = getElement("media-search");
    const typeFilter = getElement("media-type-filter");
    const statusFilter = getElement("media-status-filter");

    if (
      !importButton ||
      !importInput ||
      !resetButton ||
      !grid ||
      !detailPanel ||
      !detailClose ||
      !metadataForm ||
      !searchInput ||
      !typeFilter ||
      !statusFilter
    ) {
      return;
    }

    renderMediaLibrary();

    [searchInput, typeFilter, statusFilter].forEach((control) => {
      control.addEventListener("input", renderMediaLibrary);
      control.addEventListener("change", renderMediaLibrary);
    });

    importButton.addEventListener("click", () => {
      importInput.click();
    });

    grid.addEventListener("click", (event) => {
      const button = event.target.closest("[data-edit-media-id]");
      if (!button) {
        return;
      }
      openMediaDetailPanel(button.dataset.editMediaId);
    });

    detailClose.addEventListener("click", () => {
      detailPanel.hidden = true;
    });

    metadataForm.addEventListener("submit", (event) => {
      event.preventDefault();
      saveMediaMetadata();
    });

    importInput.addEventListener("change", async () => {
      const file = importInput.files?.[0];
      if (!file) {
        return;
      }

      try {
        const bridge = activeApiBridge();
        if (bridge) {
          await bridge.upload("/api/media/import", file);
          await bridge.sync();
        } else {
          const asset = importedMediaAssetFromFile(file);
          mediaLibraryAdapter.add(asset);
        }
        searchInput.value = "";
        typeFilter.value = "all";
        statusFilter.value = "all";
        setMediaError("");
        renderMediaLibrary();
        // Localhost mode copies the file into local app storage. Direct-file
        // mode remains a browser metadata demo. Nothing uploads to the cloud.
      } catch (error) {
        setMediaError(error.message || "Unsupported file type. Import an image or video file.");
      } finally {
        importInput.value = "";
      }
    });

    resetButton.addEventListener("click", () => {
      mediaLibraryAdapter.reset();
      detailPanel.hidden = true;
      searchInput.value = "";
      typeFilter.value = "all";
      statusFilter.value = "all";
      setMediaError("");
      renderMediaLibrary();
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    setupRouting();
    setupMediaLibrary();
    setupCalendar();
    setupPublishQueue();
    setupConnectedAccounts();
    setupSocialSetup();
    setupOnboarding();
    setupSafetyCenter();
    setupBackupData();
    setupDiagnostics();
    setupSettingsForm();
    setupBrandBrainForm();
    renderControlCenter();
    maybeRouteToOnboarding();
    window.addEventListener("local-api-ready", () => {
      renderMediaLibrary();
      renderCalendar();
      renderPublishQueue();
      renderConnectedAccounts();
      renderSocialSetup();
      renderOnboarding();
      renderSafetyCenter();
      renderBackupData();
      renderDiagnostics();
      renderControlCenter();
      maybeRouteToOnboarding();
      if (routeFromHash() === "settings") {
        applySettingsToForm(settingsAdapter.load());
      }
      if (routeFromHash() === "brand") {
        applyBrandProfileToForm(brandBrainAdapter.load());
      }
    });
  });
})();
