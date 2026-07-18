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
  const TRADE_PLANS_KEY = "gca_trade_plans_v1";
  const PORTFOLIO_RISK_KEY = "gca_portfolio_risk_v1";
  const REQUEST_HISTORY_KEY = "gca_member_service_request_history_v1";
  const REQUEST_BACKUP_SCHEMA = "gca-member-request-history-backup-v1";
  const REQUEST_HISTORY_LIMIT = 25;
  const WORKFLOW_QUEUE_LIMIT = 8;
  const WORKFLOW_PRIORITY_ORDER = Object.freeze({ critical: 0, high: 1, normal: 2, complete: 3 });
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

  function emptyTradePlanSummary() {
    return {
      count: 0,
      activeCount: 0,
      readyForReviewCount: 0,
      blockedCount: 0,
      reviewCount: 0,
      completedCount: 0,
      dueCount: 0,
      latestUpdatedAt: null
    };
  }

  function summarizeTradePlans(value, tradePlanEngine, nowMs) {
    if (!tradePlanEngine || typeof tradePlanEngine.parseBackup !== "function" || typeof tradePlanEngine.summarizePlans !== "function") {
      return emptyTradePlanSummary();
    }
    const backup = tradePlanEngine.parseBackup(value);
    if (!backup) return emptyTradePlanSummary();
    const summary = tradePlanEngine.summarizePlans(backup.plans, nowMs);
    return {
      count: summary.count,
      activeCount: summary.activeCount,
      readyForReviewCount: summary.readyForReviewCount,
      blockedCount: summary.blockedCount,
      reviewCount: summary.reviewCount,
      completedCount: summary.completedCount,
      dueCount: summary.dueCount,
      latestUpdatedAt: summary.latestUpdatedAt
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

  function safeCount(value) {
    const parsed = Number(value);
    return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
  }

  function buildWorkflowQueue(value) {
    const state = value && typeof value === "object" ? value : {};
    const training = state.training && typeof state.training === "object" ? state.training : {};
    const research = state.research && typeof state.research === "object" ? state.research : {};
    const tradePlans = state.tradePlans && typeof state.tradePlans === "object" ? state.tradePlans : {};
    const portfolio = state.portfolio && typeof state.portfolio === "object" ? state.portfolio : {};
    const journal = state.journal && typeof state.journal === "object" ? state.journal : {};
    const hasSnapshot = Boolean(
      state.snapshot &&
      typeof state.snapshot === "object" &&
      ADDRESS_RE.test(String(state.snapshot.walletAddress || "")) &&
      Number.isFinite(Date.parse(state.snapshot.savedAt))
    );
    const actions = [];
    let order = 0;
    const add = (id, priority, title, detail, href, count) => {
      if (!Object.hasOwn(WORKFLOW_PRIORITY_ORDER, priority) || actions.some((action) => action.id === id)) return;
      actions.push(Object.freeze({ id, priority, title, detail, href, count: safeCount(count), order: order++ }));
    };

    const blockedPlans = safeCount(tradePlans.blockedCount);
    const duePlans = safeCount(tradePlans.dueCount);
    const readyPlans = safeCount(tradePlans.readyForReviewCount);
    const reviewPlans = safeCount(tradePlans.reviewCount);
    const completedPlans = safeCount(tradePlans.completedCount);
    const totalPlans = safeCount(tradePlans.count);
    const dueResearch = safeCount(research.dueReviewCount);
    const activeResearch = safeCount(research.activeCount);
    const totalResearch = safeCount(research.count);
    const trainingCount = safeCount(training.count);
    const journalCount = safeCount(journal.count);
    const portfolioStatus = ["BLOCKED", "REVIEW", "WITHIN_LIMITS", "NO_POSITIONS"].includes(portfolio.status)
      ? portfolio.status
      : "NO_POSITIONS";

    if (blockedPlans) {
      add(
        "resolve-blocked-trade-plans",
        "critical",
        "Resolve blocked trade plans / 处理阻塞计划",
        `${blockedPlans} active plan(s) contain deterministic risk blockers. Review the findings before advancing any plan. / ${blockedPlans} 条活跃计划存在风控阻塞项。`,
        "trade-plans.html",
        blockedPlans
      );
    }
    if (portfolioStatus === "BLOCKED") {
      add(
        "resolve-blocked-portfolio-risk",
        "critical",
        "Resolve portfolio risk blockers / 处理组合风险阻塞",
        "The saved Portfolio Risk Map exceeds at least one configured limit. Review the local findings before adding risk. / 当前组合风险图至少超出一项自定义限制。",
        "portfolio-risk.html",
        safeCount(portfolio.positionCount)
      );
    }
    if (!hasSnapshot) {
      add(
        "refresh-member-status",
        "high",
        "Refresh member status / 刷新会员状态",
        "No current validated member snapshot is available on this device. Run the read-only account check. / 本设备没有有效会员快照，请运行只读账户检查。",
        "gca/member-access/",
        1
      );
    }
    if (dueResearch) {
      add(
        "review-due-research",
        "high",
        "Review due research / 复核到期研究",
        `${dueResearch} research note(s) reached their review date. Recheck evidence and invalidation before using them in a plan. / ${dueResearch} 条研究记录已到复核日期。`,
        "research-notes.html",
        dueResearch
      );
    }
    if (duePlans) {
      add(
        "review-due-trade-plans",
        "high",
        "Review due trade plans / 复核到期计划",
        `${duePlans} active plan(s) reached their planned date. Revalidate prices, assumptions, and risk inputs manually. / ${duePlans} 条活跃计划已到计划日期。`,
        "trade-plans.html",
        duePlans
      );
    }
    if (readyPlans) {
      add(
        "complete-plan-review",
        "high",
        "Complete manual plan review / 完成人工计划审核",
        `${readyPlans} plan(s) passed the published checks and still require human review; this is not execution approval. / ${readyPlans} 条计划已通过公开检查，仍需人工审核。`,
        "trade-plans.html",
        readyPlans
      );
    }
    if (trainingCount > 0 && training.latestStatus === "REVIEW_REQUIRED") {
      add(
        "repeat-risk-training",
        "high",
        "Review missed risk topics / 复习风控薄弱项",
        "The latest completed training attempt requires review. Revisit the missed topics before progressing a plan. / 最近一次训练仍有需要复习的风控主题。",
        "risk-training.html",
        safeCount(training.latestMissedQuestionIds?.length)
      );
    }
    if (trainingCount === 0) {
      add(
        "complete-risk-training",
        "normal",
        "Complete risk training / 完成风控训练",
        "No completed risk-discipline attempt is stored on this device. / 本设备尚无已完成的风控训练记录。",
        "risk-training.html",
        1
      );
    }
    if (totalResearch === 0) {
      add(
        "create-research-note",
        "normal",
        "Create a structured research note / 建立结构化研究记录",
        "Start with a thesis, public evidence, invalidation condition, and review date before creating a plan. / 建立计划前先记录论点、公开证据、失效条件和复核日期。",
        "research-notes.html",
        1
      );
    } else if (activeResearch > 0 && totalPlans === 0) {
      add(
        "build-first-trade-plan",
        "normal",
        "Turn reviewed research into a plan / 将研究转为计划",
        "Active research exists but no validated trade plan is stored. Use the bounded handoff, then add prices and risk inputs manually. / 已有活跃研究但尚无有效交易计划。",
        "research-notes.html",
        activeResearch
      );
    }
    if (reviewPlans) {
      add(
        "review-plan-warnings",
        "normal",
        "Review plan warnings / 复核计划警告",
        `${reviewPlans} active plan(s) have warnings without hard blockers. Recheck each warning before changing workflow status. / ${reviewPlans} 条活跃计划存在警告项。`,
        "trade-plans.html",
        reviewPlans
      );
    }
    if (portfolioStatus === "REVIEW") {
      add(
        "review-portfolio-warnings",
        "normal",
        "Review portfolio warnings / 复核组合风险警告",
        "The saved portfolio is within hard limits but contains concentration, leverage, or stress warnings that require review. / 当前组合未触发硬性限制，但仍有集中度、杠杆或压力警告。",
        "portfolio-risk.html",
        safeCount(portfolio.positionCount)
      );
    }
    if (completedPlans > 0 && journalCount === 0) {
      add(
        "record-completed-outcomes",
        "normal",
        "Record completed outcomes / 记录已完成结果",
        "Completed plans exist while the local journal is empty. If a plan was executed, enter its actual date and realized return manually. / 已有完成状态计划；如实际执行过，请手动记录日期和实际收益。",
        "trade-plans.html",
        completedPlans
      );
    }

    if (!actions.length) {
      add(
        "workflow-up-to-date",
        "complete",
        "Local workflow is up to date / 本地流程暂无待办",
        "No blocker, due-review, or missing-foundation action was found in the validated local summaries. Continue periodic manual review. / 已校验的本地摘要中没有发现阻塞、到期复核或基础缺口。",
        "tools.html",
        0
      );
    }

    return Object.freeze(
      actions
        .sort((left, right) => WORKFLOW_PRIORITY_ORDER[left.priority] - WORKFLOW_PRIORITY_ORDER[right.priority] || left.order - right.order)
        .slice(0, WORKFLOW_QUEUE_LIMIT)
        .map(({ order: _order, ...action }) => Object.freeze(action))
    );
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
    TRADE_PLANS_KEY,
    PORTFOLIO_RISK_KEY,
    REQUEST_HISTORY_KEY,
    REQUEST_BACKUP_SCHEMA,
    REQUEST_HISTORY_LIMIT,
    WORKFLOW_QUEUE_LIMIT,
    SERVICE_CATALOG,
    serviceById,
    maskWallet,
    parseMemberSnapshot,
    summarizeJournal,
    summarizeTraining,
    summarizeResearchNotes,
    summarizeTradePlans,
    summarizePortfolioRisk,
    buildWorkflowQueue,
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
