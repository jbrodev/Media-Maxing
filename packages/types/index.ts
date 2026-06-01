export type Platform =
  | "facebook"
  | "instagram"
  | "threads"
  | "youtube"
  | "tiktok"
  | "linkedin"
  | "x";

export type ApprovalStatus =
  | "draft"
  | "needs_review"
  | "approved"
  | "rejected"
  | "revision_requested"
  | "archived";

export type AutomationLevel =
  | "manual_assist"
  | "approval_queue"
  | "semi_auto_scheduling"
  | "safe_auto_posting"
  | "autonomous_content_engine";

export type SocialPlatform = Platform;

export type PlatformFeatureStatus =
  | "unavailable"
  | "planned"
  | "scaffolded"
  | "mock_only"
  | "requires_credentials"
  | "requires_app_review"
  | "ready_for_testing"
  | "enabled";

export interface ConnectorCapabilities {
  canConnect: boolean;
  canRefreshToken: boolean;
  canPublishText: boolean;
  canPublishImage: boolean;
  canPublishVideo: boolean;
  canPublishCarousel: boolean;
  canReadComments: boolean;
  canReplyToComments: boolean;
  canReadAnalytics: boolean;
  canReadProfile: boolean;
  canScheduleNatively: boolean;
  requiresBusinessAccount: boolean;
  requiresAppReview: boolean;
  supportsOAuth: boolean;
  supportsManualExportFallback: boolean;
}

export interface PlatformPermissionScope {
  id: string;
  label: string;
  description: string;
  required: boolean;
  status: PlatformFeatureStatus;
}

export interface OAuthConfig {
  platform: SocialPlatform;
  authorizationUrl?: string;
  tokenUrl?: string;
  redirectUri?: string;
  clientIdConfigured: boolean;
  scopes: PlatformPermissionScope[];
  status: PlatformFeatureStatus;
  notes?: string;
}

export interface OAuthStartRequest {
  platform: SocialPlatform;
  redirectUri?: string;
  requestedScopes: string[];
  metadata?: Record<string, unknown>;
}

export interface OAuthStartResult {
  success: boolean;
  authorizationUrl?: string;
  stateId?: string;
  status: string;
  message: string;
}

export interface OAuthCallbackRequest {
  platform: SocialPlatform;
  code?: string;
  state?: string;
  error?: string;
  metadata?: Record<string, unknown>;
}

export interface OAuthCallbackResult {
  success: boolean;
  accountProfile?: ConnectedAccountProfile;
  status: string;
  message: string;
}

export interface ConnectedAccountProfile {
  platform: SocialPlatform;
  providerAccountId: string;
  displayName: string;
  handle?: string;
  accountType?: string;
  profileUrl?: string;
  metadata?: Record<string, unknown>;
}

export interface TokenSet {
  platform: SocialPlatform;
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: string;
  scopes: string[];
  tokenType?: string;
}

export type TokenStorageMode =
  | "keychain"
  | "encrypted_file"
  | "encrypted_database"
  | "placeholder_not_stored"
  | "insecure_dev_only";

export interface TokenStorageResult {
  success: boolean;
  storageMode: TokenStorageMode;
  encryptionStatus:
    | "encrypted"
    | "keychain"
    | "placeholder_not_stored"
    | "insecure_dev_only"
    | "missing";
  tokenVersion?: number;
  accessTokenExpiresAt?: string;
  refreshTokenExpiresAt?: string;
  warnings: string[];
  errors: string[];
}

export interface TokenRedactionResult<T = unknown> {
  value: T;
  redacted: boolean;
  redactedFields: string[];
}

export type TokenAccessPolicy = "server_connector_only" | "frontend_safe_dto";

export interface SafeTokenMetadataDTO {
  success: boolean;
  status: string;
  platform?: SocialPlatform;
  tokenType?: string;
  accessTokenExpiresAt?: string;
  refreshTokenExpiresAt?: string;
  scope?: string;
  tokenVersion?: number;
  encryptionStatus?:
    | "encrypted"
    | "keychain"
    | "placeholder_not_stored"
    | "insecure_dev_only"
    | "missing";
  lastRefreshAt?: string;
  revokedAt?: string;
  createdAt?: string;
  updatedAt?: string;
  message?: string;
}

export interface TokenRefreshResult {
  success: boolean;
  tokenSet?: TokenSet;
  status: string;
  message: string;
}

export interface ConnectorHealthResult {
  platform: SocialPlatform;
  status: string;
  featureStatus: PlatformFeatureStatus;
  canUseRealNetwork: boolean;
  message: string;
  checkedAt?: string;
}

export interface ConnectorActionResult {
  success: boolean;
  status: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface ConnectorError {
  code: string;
  message: string;
  platform?: SocialPlatform;
  retryable: boolean;
  safeMetadata?: Record<string, unknown>;
}

export interface SocialConnector {
  getPlatform(): SocialPlatform;
  getCapabilities(): ConnectorCapabilities;
  getOAuthConfig(): OAuthConfig;
  buildAuthorizationUrl(request: OAuthStartRequest): OAuthStartResult;
  handleOAuthCallback(request: OAuthCallbackRequest): OAuthCallbackResult;
  refreshToken(tokenReference?: string): TokenRefreshResult;
  validateConnection(accountId?: string): ConnectorHealthResult;
  disconnect(accountId?: string): ConnectorActionResult;
  getAccountProfile(accountId?: string): ConnectedAccountProfile | undefined;
  getRequiredScopes(): PlatformPermissionScope[];
  getSetupInstructions(): string[];
}

export type MediaType = "image" | "video" | "audio" | "document" | "unknown";

export type EngagementType =
  | "comment"
  | "reply"
  | "mention"
  | "direct_message"
  | "review"
  | "lead_message"
  | "system_note"
  | "unknown";

export type EngagementStatus =
  | "new"
  | "needs_reply"
  | "reply_suggested"
  | "reply_approved"
  | "replied_manually"
  | "ignored"
  | "archived"
  | "spam"
  | "escalated";

export type EngagementDirection = "inbound" | "outbound" | "internal";

export type EngagementSentiment =
  | "positive"
  | "neutral"
  | "negative"
  | "mixed"
  | "unknown";

export type EngagementIntent =
  | "praise"
  | "question"
  | "price_request"
  | "booking_request"
  | "complaint"
  | "spam"
  | "partnership"
  | "general"
  | "urgent"
  | "unknown";

export type EngagementPriority = "low" | "normal" | "high" | "urgent";

export type EngagementSource = "mock" | "manual" | "platform_api" | "imported_csv";

export type EngagementThreadStatus =
  | "open"
  | "needs_attention"
  | "resolved"
  | "archived"
  | "spam";

export type ReplySuggestionStatus =
  | "generated"
  | "edited"
  | "approved"
  | "rejected"
  | "archived";

export type ReplyApprovalAction =
  | "suggest"
  | "edit"
  | "approve"
  | "reject"
  | "mark_replied_manually"
  | "archive"
  | "escalate"
  | "mark_spam";

export type ReplyRecommendedAction =
  | "reply"
  | "ask_for_more_info"
  | "invite_to_call"
  | "invite_to_message"
  | "escalate"
  | "ignore"
  | "mark_spam";

export type ReplySafetySeverity = "info" | "warning" | "critical";

export type AnalyticsSource =
  | "manual"
  | "mock"
  | "platform_api"
  | "imported_csv"
  | "estimated";

export type PerformanceTrend = "improving" | "flat" | "declining" | "unknown";

export type AnalyticsImportType =
  | "manual_entry"
  | "mock_sync"
  | "csv_upload"
  | "platform_sync";

export type AnalyticsImportStatus = "pending" | "completed" | "partial" | "failed";

export type ContentInsightType =
  | "best_content_type"
  | "best_platform"
  | "best_hook"
  | "best_time"
  | "weak_content_type"
  | "audience_signal"
  | "lead_signal"
  | "hashtag_signal"
  | "media_signal"
  | "safety_signal"
  | "recommendation";

export type ContentInsightStatus = "active" | "dismissed" | "applied" | "archived";

export type AIMemoryType =
  | "brand_rule"
  | "content_preference"
  | "audience_learning"
  | "platform_learning"
  | "performance_learning"
  | "safety_learning"
  | "user_preference"
  | "rejected_strategy"
  | "approved_strategy";

export type AIMemoryConfidence = "low" | "medium" | "high";

export type WeeklyReportGeneratedBy = "system" | "ai_mock" | "ai_provider" | "manual";

export interface SocialAccount {
  id: string;
  brandProfileId?: string;
  platform: Platform;
  platformAccountId?: string;
  displayName: string;
  username?: string;
  profileUrl?: string;
  profileImageUrl?: string;
  accountType:
    | "personal"
    | "business"
    | "creator"
    | "page"
    | "channel"
    | "organization"
    | "unknown";
  connectionStatus:
    | "not_connected"
    | "connecting"
    | "connected"
    | "limited"
    | "expired"
    | "revoked"
    | "disconnected"
    | "error"
    | "requires_reauth";
  // Safe account metadata only. Tokens, OAuth state, and raw provider responses must not be exposed here.
  capabilities?: Record<string, boolean | string | number | null>;
  grantedScopes?: string[];
  missingScopes?: string[];
  requiresReauth: boolean;
  lastConnectedAt?: string;
  lastValidatedAt?: string;
  disconnectedAt?: string;
  tokenStorageStatus:
    | "encrypted"
    | "keychain"
    | "placeholder_not_stored"
    | "insecure_dev_only"
    | "missing";
  createdAt: string;
  updatedAt: string;
}

export interface SafeSocialAccountDTO {
  id: string;
  platform: Platform;
  displayName: string;
  username?: string;
  accountType: SocialAccount["accountType"];
  connectionStatus: SocialAccount["connectionStatus"];
  capabilities: Record<string, boolean | string | number | null>;
  grantedScopes: string[];
  missingScopes: string[];
  requiresReauth: boolean;
  lastConnectedAt?: string;
  lastValidatedAt?: string;
  tokenStorageStatus: SocialAccount["tokenStorageStatus"];
}

export interface MediaAsset {
  id: string;
  mediaType: MediaType;
  originalPath: string;
  processedPath?: string;
  thumbnailPath?: string;
  mimeType?: string;
  fileName: string;
  tags: string[];
  // Job, customer, location, or campaign context stored locally by the user.
  contextNotes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface BrandProfile {
  id: string;
  businessName: string;
  description?: string;
  voice?: string;
  services: string[];
  locations: string[];
  targetAudience?: string;
  // Claims should be supportable. AI must not invent unsupported claims.
  supportedClaims: string[];
  blockedPhrases?: string[];
  createdAt: string;
  updatedAt: string;
}

export interface ContentIdea {
  id: string;
  brandProfileId: string;
  goal:
    | "get_leads"
    | "show_transformation"
    | "educate_customer"
    | "promote_offer"
    | "build_trust"
    | "announce_availability"
    | "repurpose_old_content"
    | "behind_the_scenes"
    | "seasonal_reminder";
  angle:
    | "before_after"
    | "educational"
    | "behind_the_scenes"
    | "testimonial"
    | "promotion"
    | "faq"
    | "trust_builder"
    | "transformation"
    | "seasonal"
    | "other";
  targetPlatforms: Platform[];
  mediaAssetIds: string[];
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface GeneratedPost {
  id: string;
  contentIdeaId?: string;
  brandProfileId: string;
  platform: Platform;
  headline?: string;
  hook?: string;
  caption: string;
  shortCaption?: string;
  longCaption?: string;
  callToAction?: string;
  hashtags: string[];
  mediaAssetIds: string[];
  contentGoal?: ContentGoal;
  contentAngle?: ContentAngle;
  targetAudience?: string;
  campaignName?: string;
  offerContext?: string;
  userInstructions?: string;
  suggestedPostTime?: string;
  altText?: string;
  notes?: string;
  score?: {
    overall: number;
    breakdown?: Record<string, number>;
    rationale?: string;
  };
  approvalStatus: ApprovalStatus;
  safetyFlags: string[];
  generationProvider: "mock" | "openai" | "anthropic" | "local";
  promptTemplateId?: string;
  promptVersion?: string;
  promptMetadata?: Record<string, unknown>;
  generationTimestamp?: string;
  createdAt: string;
  updatedAt: string;
}

export interface ScheduledPost {
  id: string;
  generatedPostId: string;
  platform: Platform;
  scheduledFor: string;
  status: "scheduled" | "blocked" | "canceled" | "ready" | "completed";
  // Snapshot fields prevent later draft edits from silently changing scheduled content.
  captionSnapshot: string;
  mediaAssetIdSnapshot: string[];
  createdAt: string;
  updatedAt: string;
}

export interface PublishedPost {
  id: string;
  scheduledPostId?: string;
  generatedPostId?: string;
  platform: Platform;
  publishMode: "mock" | "manual_export" | "platform_api";
  externalPostId?: string;
  permalink?: string;
  publishedAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface EngagementItem {
  id: string;
  brandProfileId?: string;
  platform: Platform;
  socialAccountId?: string;
  generatedPostId?: string;
  scheduledPostId?: string;
  publishedPostId?: string;
  externalItemId?: string;
  threadId?: string;
  itemType: EngagementType;
  direction: EngagementDirection;
  authorName?: string;
  authorHandle?: string;
  authorProfileUrl?: string;
  content: string;
  contentRedacted: string;
  receivedAt: string;
  sentiment: EngagementSentiment;
  intent: EngagementIntent;
  priority: EngagementPriority;
  status: EngagementStatus;
  requiresResponse: boolean;
  assignedTo?: string;
  source: EngagementSource;
  safetyFlags: string[];
  rawData?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface EngagementThread {
  id: string;
  brandProfileId: string;
  platform: Platform;
  externalThreadId?: string;
  relatedPostId?: string;
  subject?: string;
  status: EngagementThreadStatus;
  lastMessageAt: string;
  createdAt: string;
  updatedAt: string;
}

export interface ReplySuggestion {
  id: string;
  engagementItemId: string;
  brandProfileId: string;
  suggestedReply: string;
  tone?: string;
  confidence: AIMemoryConfidence;
  safetyFlags: string[];
  blockingFlags: string[];
  safetyReview: ReplySafetyFlag[];
  recommendedAction: ReplyRecommendedAction;
  needsHumanReview: boolean;
  reasoningSummary?: string;
  provider: string;
  promptTemplateId: string;
  promptVersion: string;
  status: ReplySuggestionStatus;
  createdAt: string;
  updatedAt: string;
}

export interface ReplySafetyFlag {
  code: string;
  severity: ReplySafetySeverity;
  message: string;
}

export interface ReplyApproval {
  id: string;
  replySuggestionId?: string;
  engagementItemId: string;
  action: ReplyApprovalAction;
  previousStatus?: string;
  newStatus: string;
  reason?: string;
  actorType: "user" | "system" | "ai" | "test";
  createdAt: string;
}

export interface EngagementImport {
  id: string;
  source: EngagementSource;
  platform?: Platform;
  importType: "mock_ingestion" | "manual_entry" | "csv_upload" | "platform_sync";
  status: "pending" | "completed" | "partial" | "failed";
  recordsImported: number;
  recordsSkipped: number;
  errorMessage?: string;
  importedAt: string;
  createdAt: string;
}

export interface AnalyticsSnapshot {
  id: string;
  publishedPostId?: string;
  scheduledPostId?: string;
  generatedPostId?: string;
  brandProfileId?: string;
  platform: Platform;
  source: AnalyticsSource;
  snapshotDate: string;
  impressions: number;
  reach: number;
  views: number;
  likes: number;
  comments: number;
  shares: number;
  saves: number;
  clicks: number;
  profileVisits: number;
  follows: number;
  leads: number;
  messages: number;
  calls: number;
  websiteClicks: number;
  engagementRate: number;
  clickThroughRate: number;
  leadRate: number;
  rawMetrics?: Record<string, unknown>;
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

export interface PostPerformanceMetrics {
  id: string;
  generatedPostId?: string;
  scheduledPostId?: string;
  publishedPostId?: string;
  brandProfileId: string;
  platform: Platform;
  contentGoal?: string;
  contentAngle?: string;
  mediaAssetIds: string[];
  postedAt?: string;
  firstSnapshotAt?: string;
  latestSnapshotAt?: string;
  totalImpressions: number;
  totalReach: number;
  totalViews: number;
  totalLikes: number;
  totalComments: number;
  totalShares: number;
  totalSaves: number;
  totalClicks: number;
  totalLeads: number;
  engagementRate: number;
  leadRate: number;
  performanceScore: number;
  trend: PerformanceTrend;
  createdAt: string;
  updatedAt: string;
}

export interface AnalyticsImport {
  id: string;
  source: AnalyticsSource;
  platform?: Platform;
  importType: AnalyticsImportType;
  status: AnalyticsImportStatus;
  recordsImported: number;
  recordsSkipped: number;
  errorMessage?: string;
  importedAt: string;
  createdAt: string;
}

export interface ContentInsight {
  id: string;
  brandProfileId: string;
  insightType: ContentInsightType;
  title: string;
  summary: string;
  evidence: Record<string, unknown>;
  confidence: AIMemoryConfidence;
  relatedPostIds: string[];
  relatedMediaAssetIds: string[];
  recommendedAction?: string;
  status: ContentInsightStatus;
  createdAt: string;
  updatedAt: string;
}

export interface AIMemory {
  id: string;
  brandProfileId?: string;
  memoryType: AIMemoryType;
  title: string;
  content: string;
  evidence: Record<string, unknown>;
  confidence: AIMemoryConfidence;
  source: string;
  status: "active" | "archived" | "superseded";
  createdAt: string;
  updatedAt: string;
}

export interface WeeklyReport {
  id: string;
  brandProfileId: string;
  weekStartDate: string;
  weekEndDate: string;
  summary: string;
  wins: string[];
  concerns: string[];
  recommendations: string[];
  topPosts: Record<string, unknown>[] | string[];
  platformBreakdown: Record<string, unknown>;
  metricTotals: Record<string, unknown>;
  generatedBy: WeeklyReportGeneratedBy;
  createdAt: string;
  updatedAt: string;
}
