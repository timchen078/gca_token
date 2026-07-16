(function attachMemberWorkspace(root, factory) {
  const workspace = factory();
  root.GcaMemberWorkspace = workspace;
  if (typeof module !== "undefined" && module.exports) module.exports = workspace;
})(typeof globalThis !== "undefined" ? globalThis : this, function createMemberWorkspace() {
  "use strict";

  const SNAPSHOT_KEY = "gca_member_access_snapshot_v1";
  const SNAPSHOT_MAX_AGE_MS = 30 * 24 * 60 * 60 * 1000;
  const JOURNAL_KEY = "gca_trade_journal_v1";
  const TRAINING_HISTORY_KEY = "gca_risk_training_history_v1";
  const RESEARCH_NOTES_KEY = "gca_research_notes_v1";
  const PORTFOLIO_RISK_KEY = "gca_portfolio_risk_v1";
  const REQUEST_HISTORY_KEY = "gca_member_service_request_history_v1";
  const REQUEST_BACKUP_SCHEMA = "gca-member-request-history-backup-v1";
  const REQUEST_HISTORY_LIMIT = 25;
  const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;
  const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  const SENSITIVE_RE = /private\s*key|seed\s*phrase|mnemonic|api\s*secret|wallet\s*password|one[-\s]*time\s*code|withdrawal\s*permission|remote\s*control|\b(?:otp|2fa)\b|\u79c1\u94a5|\u52a9\u8bb0\u8bcd|\u5bc6\u7801|\u9a8c\u8bc1\u7801|\u63d0\u73b0\u6743\u9650|\u8fdc\u7a0b\u63a7\u5236/i;
  const REQUEST_ID_RE = /^gca_local_req_[a-z0-9-]{8,64}$/;
  const REQUEST_ACTIONS = Object.freeze(["packet_created", "packet_copied", "packet_downloaded", "email_client_opened"]);
  const CREDIT_CHECK_STATUSES = Object.freeze(["status-refresh-required", "no-credit-hold", "credit-ledger-not-active", "insufficient-credits", "credits-available"]);
  const REQUEST_RECEIPT_FIELDS = Object.freeze([
    "version",
    "requestId",
    "createdAt",
    "updatedAt",
    "serviceId",
    "serviceName",
    "creditUnit",
    "preferredLanguage",
    "deviceCreditCheck",
    "deviceCreditsAvailable",
    "localAction"
  ]);

  const SERVICE_CATALOG = Object.freeze([
    { id: "position-size-calculator", name: "Position Size Calculator", creditUnit: 5, previewUrl: "risk-calculator.html", stage: "public-preview" },
    { id: "portfolio-risk-map", name: "Portfolio Risk Map", creditUnit: 15, previewUrl: "portfolio-risk.html", stage: "public-preview" },
    { id: "risk-warning-review", name: "Risk Warning Review", creditUnit: 10, previewUrl: "risk-warning.html", stage: "public-preview" },
    { id: "entry-ready-review", name: "ENTRY_READY Review", creditUnit: 15, previewUrl: "entry-ready.html", stage: "public-preview" },
    { id: "backtest-lab-run", name: "Backtest Lab", creditUnit: 20, previewUrl: "backtest-lab.html", stage: "public-preview" },
    { id: "liquidation-replay-report", name: "Liquidation Replay", creditUnit: 30, previewUrl: "liquidation-replay.html", stage: "public-preview" },
    { id: "risk-control-training", name: "Risk-Control Training", creditUnit: 10, previewUrl: "risk-training.html", stage: "public-preview" },
    { id: "member-research-notes", name: "Member Research Notes", creditUnit: 20, previewUrl: "research-notes.html", stage: "public-preview" },
    { id: "support-review-queue", name: "Support Review Queue", creditUnit: 0, previewUrl: "support.html", stage: "manual-review" }
  ]);

  function cleanText(value, maxLength) {
    return String(value || "").trim().replace(/\s+/g, " ").slice(0, maxLength);
  }

  function parseJson(value) {
    try {
      return typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
  }

  function serviceById(serviceId) {
    return SERVICE_CATALOG.find((service) => service.id === serviceId) || null;
  }

  function maskWallet(value) {
    const wallet = String(value || "");
    return ADDRESS_RE.test(wallet) ? `${wallet.slice(0, 8)}...${wallet.slice(-6)}` : "Not verified / \u672a\u9a8c\u8bc1";
  }

  function parseMemberSnapshot(value, nowMs) {
    const snapshot = parseJson(value);
    if (!snapshot || snapshot.version !== 1 || !ADDRESS_RE.test(String(snapshot.walletAddress || ""))) return null;
    const savedTime = Date.parse(snapshot.savedAt);
    const now = Number.isFinite(Number(nowMs)) ? Number(nowMs) : Date.now();
    const ageMs = now - savedTime;
    if (!Number.isFinite(savedTime) || !Number.isFinite(ageMs) || ageMs < 0 || ageMs > SNAPSHOT_MAX_AGE_MS) return null;
    const balance = String(snapshot.gcaBalance || "0");
    if (!/^\d+(?:\.\d+)?$/.test(balance)) return null;
    const creditAmount = Number(snapshot.creditAmount || 0);
    const remainingCredits = Number(snapshot.remainingCredits ?? creditAmount);
    if (!Number.isInteger(creditAmount) || creditAmount < 0 || !Number.isInteger(remainingCredits) || remainingCredits < 0) return null;
    const holdingDays = Number(snapshot.holdingPeriodDaysVerified || 0);
    if (!Number.isFinite(holdingDays) || holdingDays < 0) return null;
    return {
      version: 1,
      savedAt: new Date(savedTime).toISOString(),
      walletAddress: String(snapshot.walletAddress),
      gcaBalance: balance,
      holderBonusEligible: Boolean(snapshot.holderBonusEligible),
      gcaMemberEligible: Boolean(snapshot.gcaMemberEligible),
      holdingPeriodDaysVerified: Math.floor(holdingDays),
      creditAmount,
      remainingCredits,
      creditStatus: cleanText(snapshot.creditStatus, 60) || "not_created",
      memberStatus: cleanText(snapshot.memberStatus, 60) || "not_created",
      memberBenefitClaimStatus: cleanText(snapshot.memberBenefitClaimStatus, 80) || "not_applicable",
      nextStep: cleanText(snapshot.nextStep, 500)
    };
  }

  function emptyJournalSummary() {
    return {
      count: 0,
      winRatePercent: 0,
      averageReturnPercent: 0,
      maxConsecutiveLosses: 0,
      sampleQuality: { code: "INSUFFICIENT_SAMPLE", label: "Insufficient sample" }
    };
  }

  function summarizeJournal(value, journalEngine) {
    const parsed = parseJson(value);
    const backup = journalEngine && typeof journalEngine.parseBackup === "function"
      ? journalEngine.parseBackup(value)
      : null;
    const rows = backup ? backup.trades : parsed;
    if (!Array.isArray(rows) || !journalEngine || typeof journalEngine.summarizeTrades !== "function") return emptyJournalSummary();
    const summary = journalEngine.summarizeTrades(rows);
    return {
      count: summary.count,
      winRatePercent: summary.winRatePercent,
      averageReturnPercent: summary.averageReturnPercent,
      maxConsecutiveLosses: summary.maxConsecutiveLosses,
      sampleQuality: summary.sampleQuality
    };
  }

  function emptyTrainingSummary() {
    return {
      count: 0,
      latestStatus: "NO_ATTEMPTS",
      latestPercent: 0,
      latestCompletedAt: null,
      bestPercent: 0,
      foundationReadyCount: 0,
      latestMissedQuestionIds: []
    };
  }

  function summarizeTraining(value, trainingEngine) {
    if (!trainingEngine || typeof trainingEngine.summarizeAttemptHistory !== "function") return emptyTrainingSummary();
    const summary = trainingEngine.summarizeAttemptHistory(value);
    return {
      count: summary.count,
      latestStatus: summary.latestStatus,
      latestPercent: summary.latestPercent,
      latestCompletedAt: summary.latestCompletedAt,
      bestPercent: summary.bestPercent,
      foundationReadyCount: summary.foundationReadyCount,
      latestMissedQuestionIds: [...summary.latestMissedQuestionIds]
    };
  }

  function emptyResearchSummary() {
    return {
      count: 0,
      activeCount: 0,
      sourcedCount: 0,
      dueReviewCount: 0,
      latestUpdatedAt: null
    };
  }

  function summarizeResearchNotes(value, researchEngine, nowMs) {
    if (!researchEngine || typeof researchEngine.parseBackup !== "function" || typeof researchEngine.summarizeNotes !== "function") {
      return emptyResearchSummary();
    }
    const backup = researchEngine.parseBackup(value);
    if (!backup) return emptyResearchSummary();
    const summary = researchEngine.summarizeNotes(backup.notes, nowMs);
    return {
      count: summary.count,
      activeCount: summary.activeCount,
      sourcedCount: summary.sourcedCount,
      dueReviewCount: summary.dueReviewCount,
      latestUpdatedAt: summary.latestUpdatedAt
    };
  }

  function emptyPortfolioSummary() {
    return {
      positionCount: 0,
      status: "NO_POSITIONS",
      totalRiskPercent: 0,
      grossExposurePercent: 0,
      marginUtilizationPercent: 0,
      savedAt: null
    };
  }

  function summarizePortfolioRisk(value, portfolioEngine) {
    if (!portfolioEngine || typeof portfolioEngine.parseBackup !== "function" || typeof portfolioEngine.analyzePortfolio !== "function") {
      return emptyPortfolioSummary();
    }
    const backup = portfolioEngine.parseBackup(value);
    if (!backup) return emptyPortfolioSummary();
    const analysis = portfolioEngine.analyzePortfolio(backup.config, backup.positions);
    if (!analysis) return emptyPortfolioSummary();
    return {
      positionCount: analysis.positionCount,
      status: analysis.status,
      totalRiskPercent: analysis.totalRiskPercent,
      grossExposurePercent: analysis.grossExposurePercent,
      marginUtilizationPercent: analysis.marginUtilizationPercent,
      savedAt: backup.savedAt
    };
  }

  function creditCheck(snapshot, service) {
    if (!snapshot) return { status: "status-refresh-required", available: 0 };
    if (service.creditUnit === 0) return { status: "no-credit-hold", available: snapshot.remainingCredits };
    if (snapshot.creditStatus === "not_created") return { status: "credit-ledger-not-active", available: 0 };
    if (snapshot.remainingCredits < service.creditUnit) return { status: "insufficient-credits", available: snapshot.remainingCredits };
    return { status: "credits-available", available: snapshot.remainingCredits };
  }

  function normalizedIso(value, fallback) {
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) return new Date(parsed).toISOString();
    const fallbackParsed = Date.parse(fallback);
    return Number.isFinite(fallbackParsed) ? new Date(fallbackParsed).toISOString() : new Date().toISOString();
  }

  function normalizeRequestId(value, generatedTime) {
    const requestedId = cleanText(value, 96).toLowerCase();
    if (REQUEST_ID_RE.test(requestedId)) return requestedId;
    return `gca_local_req_${Date.parse(generatedTime).toString(36)}`;
  }

  function buildServiceRequest(input, snapshot, generatedAt, requestId) {
    const requested = input && typeof input === "object" ? input : {};
    const service = serviceById(requested.serviceId);
    const email = cleanText(requested.email, 160).toLowerCase();
    const title = cleanText(requested.title, 120);
    const summary = cleanText(requested.summary, 1200);
    const marketContext = cleanText(requested.marketContext, 600);
    const preferredLanguage = requested.preferredLanguage === "zh-CN" ? "zh-CN" : "en";
    if (!service) return { ok: false, error: "invalid-service" };
    if (!EMAIL_RE.test(email)) return { ok: false, error: "invalid-email" };
    if (title.length < 3) return { ok: false, error: "title-required" };
    if (summary.length < 20) return { ok: false, error: "summary-too-short" };
    if (SENSITIVE_RE.test(`${title} ${summary} ${marketContext}`)) return { ok: false, error: "sensitive-content" };
    const generatedTime = normalizedIso(generatedAt, new Date().toISOString());
    const localRequestId = normalizeRequestId(requestId, generatedTime);
    const status = creditCheck(snapshot, service);
    const wallet = snapshot ? snapshot.walletAddress : "Not verified / \u672a\u9a8c\u8bc1";
    const packet = [
      "GCA Member Service Request / GCA \u4f1a\u5458\u670d\u52a1\u7533\u8bf7",
      `Local request ID / \u672c\u5730\u7533\u8bf7\u7f16\u53f7: ${localRequestId}`,
      `Generated at / \u751f\u6210\u65f6\u95f4: ${generatedTime}`,
      "Request mode / \u7533\u8bf7\u6a21\u5f0f: manual operator review only / \u4ec5\u4eba\u5de5\u5ba1\u6838",
      "Credit effect / \u79ef\u5206\u5f71\u54cd: request creation does not deduct credits / \u751f\u6210\u7533\u8bf7\u4e0d\u6263\u9664\u79ef\u5206",
      "",
      `Service / \u670d\u52a1: ${service.name}`,
      `Service ID: ${service.id}`,
      `Catalog credit unit / \u76ee\u5f55\u79ef\u5206\u5355\u4f4d: ${service.creditUnit}`,
      `Device credit check / \u672c\u8bbe\u5907\u79ef\u5206\u68c0\u67e5: ${status.status}`,
      `Device credits available / \u672c\u8bbe\u5907\u663e\u793a\u53ef\u7528\u79ef\u5206: ${status.available}`,
      `Email / \u90ae\u7bb1: ${email}`,
      `Wallet / \u94b1\u5305: ${wallet}`,
      `Preferred language / \u9996\u9009\u8bed\u8a00: ${preferredLanguage}`,
      `Title / \u6807\u9898: ${title}`,
      `Summary / \u8bf4\u660e: ${summary}`,
      `Market context / \u5e02\u573a\u80cc\u666f: ${marketContext || "Not provided / \u672a\u586b\u5199"}`,
      "",
      "Operator boundary / \u8fd0\u8425\u8fb9\u754c",
      "This packet is a request for review. It does not reserve or deduct credits, create trading permission, connect an exchange, place an order, request a wallet signature, or transfer tokens.",
      "\u672c\u8d44\u6599\u5305\u53ea\u662f\u5ba1\u6838\u7533\u8bf7\uff0c\u4e0d\u4f1a\u9884\u6263\u6216\u6263\u9664\u79ef\u5206\uff0c\u4e0d\u4f1a\u5f00\u901a\u4ea4\u6613\u6743\u9650\u3001\u8fde\u63a5\u4ea4\u6613\u6240\u3001\u4e0b\u5355\u3001\u8981\u6c42\u94b1\u5305\u7b7e\u540d\u6216\u8f6c\u79fb\u4ee3\u5e01\u3002",
      "Do not add private keys, seed phrases, passwords, exchange API secrets, withdrawal permission, one-time codes, or remote-control access.",
      "\u4e0d\u8981\u6dfb\u52a0\u79c1\u94a5\u3001\u52a9\u8bb0\u8bcd\u3001\u5bc6\u7801\u3001\u4ea4\u6613\u6240 API Secret\u3001\u63d0\u73b0\u6743\u9650\u3001\u9a8c\u8bc1\u7801\u6216\u8fdc\u7a0b\u63a7\u5236\u6743\u9650\u3002"
    ].join("\n");
    return { ok: true, requestId: localRequestId, generatedAt: generatedTime, service, creditCheck: status, packet };
  }

  function sanitizeRequestReceipt(value) {
    if (!value || typeof value !== "object" || value.version !== 1) return null;
    const service = serviceById(value.serviceId);
    const requestId = cleanText(value.requestId, 96).toLowerCase();
    const createdAt = normalizedIso(value.createdAt, "");
    const updatedAt = normalizedIso(value.updatedAt, createdAt);
    const localAction = cleanText(value.localAction, 40);
    const creditCheckStatus = cleanText(value.deviceCreditCheck, 60);
    const creditsAvailable = Number(value.deviceCreditsAvailable || 0);
    if (!service || !REQUEST_ID_RE.test(requestId)) return null;
    if (!Number.isFinite(Date.parse(value.createdAt)) || !Number.isFinite(Date.parse(value.updatedAt))) return null;
    if (!REQUEST_ACTIONS.includes(localAction) || !CREDIT_CHECK_STATUSES.includes(creditCheckStatus)) return null;
    if (!Number.isInteger(creditsAvailable) || creditsAvailable < 0) return null;
    return {
      version: 1,
      requestId,
      createdAt,
      updatedAt,
      serviceId: service.id,
      serviceName: service.name,
      creditUnit: service.creditUnit,
      preferredLanguage: value.preferredLanguage === "zh-CN" ? "zh-CN" : "en",
      deviceCreditCheck: creditCheckStatus,
      deviceCreditsAvailable: creditsAvailable,
      localAction
    };
  }

  function parseRequestHistory(value) {
    const rows = parseJson(value);
    if (!Array.isArray(rows)) return [];
    const seen = new Set();
    return rows
      .map(sanitizeRequestReceipt)
      .filter((receipt) => {
        if (!receipt || seen.has(receipt.requestId)) return false;
        seen.add(receipt.requestId);
        return true;
      })
      .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt))
      .slice(0, REQUEST_HISTORY_LIMIT);
  }

  function createRequestReceipt(result, input, actionAt) {
    if (!result || result.ok !== true || !result.service || !result.creditCheck) return null;
    const requested = input && typeof input === "object" ? input : {};
    return sanitizeRequestReceipt({
      version: 1,
      requestId: result.requestId,
      createdAt: result.generatedAt,
      updatedAt: normalizedIso(actionAt, result.generatedAt),
      serviceId: result.service.id,
      preferredLanguage: requested.preferredLanguage,
      deviceCreditCheck: result.creditCheck.status,
      deviceCreditsAvailable: result.creditCheck.available,
      localAction: "packet_created"
    });
  }

  function upsertRequestHistory(value, receipt) {
    const current = parseRequestHistory(value);
    const sanitized = sanitizeRequestReceipt(receipt);
    if (!sanitized) return current;
    return parseRequestHistory([sanitized, ...current.filter((item) => item.requestId !== sanitized.requestId)]);
  }

  function markRequestAction(value, requestId, action, actionAt) {
    const current = parseRequestHistory(value);
    if (!REQUEST_ACTIONS.includes(action)) return current;
    const updatedTime = normalizedIso(actionAt, new Date().toISOString());
    return parseRequestHistory(current.map((receipt) => receipt.requestId === requestId
      ? { ...receipt, localAction: action, updatedAt: updatedTime }
      : receipt));
  }

  function removeRequestReceipt(value, requestId) {
    return parseRequestHistory(value).filter((receipt) => receipt.requestId !== requestId);
  }

  function exactRequestReceipt(value, sanitized) {
    if (!value || typeof value !== "object" || !sanitized) return false;
    const keys = Object.keys(value);
    if (keys.length !== REQUEST_RECEIPT_FIELDS.length || keys.some((key) => !REQUEST_RECEIPT_FIELDS.includes(key))) return false;
    return REQUEST_RECEIPT_FIELDS.every((key) => value[key] === sanitized[key]);
  }

  function buildRequestHistoryBackup(value, exportedAt) {
    const parsedTime = Date.parse(exportedAt);
    return Object.freeze({
      schema: REQUEST_BACKUP_SCHEMA,
      version: 1,
      exportedAt: Number.isFinite(parsedTime) ? new Date(parsedTime).toISOString() : new Date().toISOString(),
      receipts: parseRequestHistory(value)
    });
  }

  function parseRequestHistoryBackup(value) {
    const payload = parseJson(value);
    if (!payload || typeof payload !== "object") return null;
    const keys = Object.keys(payload);
    if (
      keys.length !== 4 ||
      keys.some((key) => !["schema", "version", "exportedAt", "receipts"].includes(key)) ||
      payload.schema !== REQUEST_BACKUP_SCHEMA ||
      payload.version !== 1 ||
      !Number.isFinite(Date.parse(payload.exportedAt)) ||
      !Array.isArray(payload.receipts) ||
      payload.receipts.length === 0 ||
      payload.receipts.length > REQUEST_HISTORY_LIMIT
    ) return null;
    const sanitized = payload.receipts.map(sanitizeRequestReceipt);
    if (sanitized.some((receipt, index) => !exactRequestReceipt(payload.receipts[index], receipt))) return null;
    const receipts = parseRequestHistory(sanitized);
    if (receipts.length !== payload.receipts.length) return null;
    return Object.freeze({
      schema: REQUEST_BACKUP_SCHEMA,
      version: 1,
      exportedAt: new Date(payload.exportedAt).toISOString(),
      receipts
    });
  }

  function mergeRequestHistoryBackup(currentValue, backupValue) {
    const backup = parseRequestHistoryBackup(backupValue);
    if (!backup) return null;
    const current = parseRequestHistory(currentValue);
    const currentById = new Map(current.map((receipt) => [receipt.requestId, receipt]));
    const mergedById = new Map(currentById);
    const updatedIds = new Set();
    backup.receipts.forEach((receipt) => {
      const existing = mergedById.get(receipt.requestId);
      if (!existing || Date.parse(receipt.updatedAt) > Date.parse(existing.updatedAt)) {
        mergedById.set(receipt.requestId, receipt);
        if (existing) updatedIds.add(receipt.requestId);
      }
    });
    const receipts = parseRequestHistory([...mergedById.values()]);
    const retainedIds = new Set(receipts.map((receipt) => receipt.requestId));
    return Object.freeze({
      receipts,
      importedReceiptCount: backup.receipts.length,
      addedReceiptCount: backup.receipts.filter(
        (receipt) => !currentById.has(receipt.requestId) && retainedIds.has(receipt.requestId)
      ).length,
      updatedReceiptCount: [...updatedIds].filter((requestId) => retainedIds.has(requestId)).length
    });
  }

  return {
    SNAPSHOT_KEY,
    SNAPSHOT_MAX_AGE_MS,
    JOURNAL_KEY,
    TRAINING_HISTORY_KEY,
    RESEARCH_NOTES_KEY,
    PORTFOLIO_RISK_KEY,
    REQUEST_HISTORY_KEY,
    REQUEST_BACKUP_SCHEMA,
    REQUEST_HISTORY_LIMIT,
    SERVICE_CATALOG,
    serviceById,
    maskWallet,
    parseMemberSnapshot,
    summarizeJournal,
    summarizeTraining,
    summarizeResearchNotes,
    summarizePortfolioRisk,
    buildServiceRequest,
    parseRequestHistory,
    createRequestReceipt,
    upsertRequestHistory,
    markRequestAction,
    removeRequestReceipt,
    buildRequestHistoryBackup,
    parseRequestHistoryBackup,
    mergeRequestHistoryBackup
  };
});
