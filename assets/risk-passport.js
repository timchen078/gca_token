(function attachRiskPassport(root, factory) {
  const passport = factory();
  root.GcaRiskPassport = passport;
  if (typeof module !== "undefined" && module.exports) module.exports = passport;
})(typeof globalThis !== "undefined" ? globalThis : this, function createRiskPassport() {
  "use strict";

  const SCHEMA = "gca-risk-passport-v1";
  const VERSION = 1;
  const COVERAGE_TOTAL = 6;
  const MAX_ACTIONS = 8;
  const MAX_COUNT = 100000;
  const ACTION_ID_RE = /^[a-z0-9][a-z0-9-]{1,79}$/;
  const PRIORITIES = Object.freeze(["critical", "high", "normal", "complete"]);
  const TRAINING_STATUSES = Object.freeze(["NO_ATTEMPTS", "REVIEW_REQUIRED", "FOUNDATION_READY", "UNKNOWN"]);
  const PORTFOLIO_STATUSES = Object.freeze(["NO_POSITIONS", "BLOCKED", "REVIEW", "WITHIN_LIMITS", "UNKNOWN"]);
  const COVERAGE_STATES = Object.freeze(["no-evidence", "started", "established", "all-pillars-covered"]);
  const WORKFLOW_STATES = Object.freeze(["start", "attention-required", "review-required", "in-progress", "current"]);
  const MEMBER_STATES = Object.freeze(["not-available", "not-active", "pending-review", "active"]);
  const CREDIT_STATES = Object.freeze(["not-available", "not-active", "available", "exhausted"]);
  const TOP_LEVEL_FIELDS = Object.freeze([
    "schema",
    "version",
    "generatedAt",
    "scope",
    "coverage",
    "account",
    "training",
    "research",
    "planning",
    "portfolio",
    "journal",
    "workflow",
    "boundaries"
  ]);
  const BOUNDARIES = Object.freeze({
    containsIdentityData: false,
    containsEmail: false,
    containsWalletAddress: false,
    containsGcaBalance: false,
    containsCreditBalance: false,
    containsResearchOrPlanText: false,
    containsPositionOrJournalDetails: false,
    uploadsData: false,
    fetchesMarketData: false,
    connectsExchange: false,
    placesOrders: false,
    issuesCertification: false,
    createsTradingSignal: false
  });

  function parseJson(value) {
    try {
      return typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
  }

  function exactKeys(value, fields) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value);
    return keys.length === fields.length && keys.every((key) => fields.includes(key));
  }

  function normalizedIso(value, fallback) {
    const parsed = Date.parse(value);
    if (Number.isFinite(parsed)) return new Date(parsed).toISOString();
    const fallbackParsed = Date.parse(fallback);
    return Number.isFinite(fallbackParsed) ? new Date(fallbackParsed).toISOString() : new Date().toISOString();
  }

  function count(value) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed) || parsed < 0) return 0;
    return Math.min(MAX_COUNT, Math.floor(parsed));
  }

  function oneOf(value, allowed, fallback) {
    return allowed.includes(value) ? value : fallback;
  }

  function memberState(snapshot) {
    if (!snapshot) return "not-available";
    const value = String(snapshot.memberStatus || "").toLowerCase();
    if (!value || value === "not_created" || value === "not-created") return "not-active";
    if (value === "active" || value === "ledger_recorded" || value === "ledger-recorded") return "active";
    return "pending-review";
  }

  function creditState(snapshot) {
    if (!snapshot) return "not-available";
    const value = String(snapshot.creditStatus || "").toLowerCase();
    if (!value || value === "not_created" || value === "not-created") return "not-active";
    return count(snapshot.remainingCredits) > 0 ? "available" : "exhausted";
  }

  function trainingStatus(summary) {
    const attempts = count(summary && summary.count);
    if (!attempts) return "NO_ATTEMPTS";
    return oneOf(summary && summary.latestStatus, TRAINING_STATUSES, "UNKNOWN");
  }

  function portfolioStatus(summary) {
    const positions = count(summary && summary.positionCount);
    if (!positions) return "NO_POSITIONS";
    return oneOf(summary && summary.status, PORTFOLIO_STATUSES, "UNKNOWN");
  }

  function journalQuality(summary) {
    const code = summary && summary.sampleQuality && summary.sampleQuality.code;
    return oneOf(code, ["INSUFFICIENT_SAMPLE", "EARLY_SAMPLE", "LARGER_SAMPLE"], "INSUFFICIENT_SAMPLE");
  }

  function sanitizeActionIds(queue) {
    const source = Array.isArray(queue) ? queue : [];
    const seen = new Set();
    return source.slice(0, MAX_ACTIONS).reduce((items, item) => {
      const id = String(item && item.id || "").trim().toLowerCase();
      const priority = oneOf(item && item.priority, PRIORITIES, "normal");
      if (!ACTION_ID_RE.test(id) || seen.has(id)) return items;
      seen.add(id);
      items.push(Object.freeze({ id, priority }));
      return items;
    }, []);
  }

  function coverageState(completed) {
    if (completed === 0) return "no-evidence";
    if (completed <= 2) return "started";
    if (completed < COVERAGE_TOTAL) return "established";
    return "all-pillars-covered";
  }

  function workflowState(counts) {
    if (counts.criticalCount > 0) return "attention-required";
    if (counts.highCount > 0) return "review-required";
    if (counts.normalCount > 0) return "in-progress";
    if (counts.completeCount > 0) return "current";
    return "start";
  }

  function completedPillars(value) {
    return [
      value.account.snapshotAvailable,
      value.training.attemptCount > 0,
      value.research.noteCount > 0,
      value.planning.planCount > 0,
      value.portfolio.positionCount > 0,
      value.journal.tradeCount > 0
    ].filter(Boolean).length;
  }

  function buildPassport(input, generatedAt) {
    const source = input && typeof input === "object" ? input : {};
    const snapshot = source.snapshot && typeof source.snapshot === "object" ? source.snapshot : null;
    const training = source.training && typeof source.training === "object" ? source.training : {};
    const research = source.research && typeof source.research === "object" ? source.research : {};
    const planning = source.tradePlans && typeof source.tradePlans === "object" ? source.tradePlans : {};
    const portfolio = source.portfolio && typeof source.portfolio === "object" ? source.portfolio : {};
    const journal = source.journal && typeof source.journal === "object" ? source.journal : {};
    const actions = sanitizeActionIds(source.queue);

    const accountSummary = Object.freeze({
      snapshotAvailable: Boolean(snapshot),
      memberState: memberState(snapshot),
      creditState: creditState(snapshot)
    });
    const trainingSummary = Object.freeze({
      attemptCount: count(training.count),
      latestStatus: trainingStatus(training),
      foundationReadyCount: count(training.foundationReadyCount)
    });
    const researchSummary = Object.freeze({
      noteCount: count(research.count),
      activeCount: count(research.activeCount),
      sourcedCount: count(research.sourcedCount),
      dueReviewCount: count(research.dueReviewCount)
    });
    const planningSummary = Object.freeze({
      planCount: count(planning.count),
      readyForReviewCount: count(planning.readyForReviewCount),
      blockedCount: count(planning.blockedCount),
      reviewCount: count(planning.reviewCount),
      completedCount: count(planning.completedCount),
      dueCount: count(planning.dueCount)
    });
    const portfolioSummary = Object.freeze({
      positionCount: count(portfolio.positionCount),
      status: portfolioStatus(portfolio)
    });
    const journalSummary = Object.freeze({
      tradeCount: count(journal.count),
      sampleQuality: journalQuality(journal)
    });
    const completed = completedPillars({
      account: accountSummary,
      training: trainingSummary,
      research: researchSummary,
      planning: planningSummary,
      portfolio: portfolioSummary,
      journal: journalSummary
    });
    const priorityCounts = {
      criticalCount: actions.filter((item) => item.priority === "critical").length,
      highCount: actions.filter((item) => item.priority === "high").length,
      normalCount: actions.filter((item) => item.priority === "normal").length,
      completeCount: actions.filter((item) => item.priority === "complete").length
    };

    return Object.freeze({
      schema: SCHEMA,
      version: VERSION,
      generatedAt: normalizedIso(generatedAt, new Date().toISOString()),
      scope: "browser-local-workflow-summary",
      coverage: Object.freeze({ completed, total: COVERAGE_TOTAL, state: coverageState(completed) }),
      account: accountSummary,
      training: trainingSummary,
      research: researchSummary,
      planning: planningSummary,
      portfolio: portfolioSummary,
      journal: journalSummary,
      workflow: Object.freeze({
        state: workflowState(priorityCounts),
        ...priorityCounts,
        actionIds: Object.freeze(actions.map((item) => item.id))
      }),
      boundaries: BOUNDARIES
    });
  }

  function parsePassport(value) {
    const payload = parseJson(value);
    if (!exactKeys(payload, TOP_LEVEL_FIELDS)) return null;
    if (payload.schema !== SCHEMA || payload.version !== VERSION || payload.scope !== "browser-local-workflow-summary") return null;
    const generatedAt = normalizedIso(payload.generatedAt, "");
    if (!Number.isFinite(Date.parse(payload.generatedAt)) || generatedAt !== payload.generatedAt) return null;
    if (!exactKeys(payload.coverage, ["completed", "total", "state"])) return null;
    if (!exactKeys(payload.account, ["snapshotAvailable", "memberState", "creditState"])) return null;
    if (!exactKeys(payload.training, ["attemptCount", "latestStatus", "foundationReadyCount"])) return null;
    if (!exactKeys(payload.research, ["noteCount", "activeCount", "sourcedCount", "dueReviewCount"])) return null;
    if (!exactKeys(payload.planning, ["planCount", "readyForReviewCount", "blockedCount", "reviewCount", "completedCount", "dueCount"])) return null;
    if (!exactKeys(payload.portfolio, ["positionCount", "status"])) return null;
    if (!exactKeys(payload.journal, ["tradeCount", "sampleQuality"])) return null;
    if (!exactKeys(payload.workflow, ["state", "criticalCount", "highCount", "normalCount", "completeCount", "actionIds"])) return null;
    if (!exactKeys(payload.boundaries, Object.keys(BOUNDARIES))) return null;

    const allCounts = [
      payload.coverage.completed,
      payload.training.attemptCount,
      payload.training.foundationReadyCount,
      payload.research.noteCount,
      payload.research.activeCount,
      payload.research.sourcedCount,
      payload.research.dueReviewCount,
      payload.planning.planCount,
      payload.planning.readyForReviewCount,
      payload.planning.blockedCount,
      payload.planning.reviewCount,
      payload.planning.completedCount,
      payload.planning.dueCount,
      payload.portfolio.positionCount,
      payload.journal.tradeCount,
      payload.workflow.criticalCount,
      payload.workflow.highCount,
      payload.workflow.normalCount,
      payload.workflow.completeCount
    ];
    if (allCounts.some((value) => !Number.isInteger(value) || value < 0 || value > MAX_COUNT)) return null;
    if (payload.coverage.completed > COVERAGE_TOTAL || payload.coverage.total !== COVERAGE_TOTAL) return null;
    if (payload.coverage.completed !== completedPillars(payload)) return null;
    if (payload.coverage.state !== coverageState(payload.coverage.completed)) return null;
    if (typeof payload.account.snapshotAvailable !== "boolean") return null;
    if (!MEMBER_STATES.includes(payload.account.memberState) || !CREDIT_STATES.includes(payload.account.creditState)) return null;
    if (!payload.account.snapshotAvailable && (payload.account.memberState !== "not-available" || payload.account.creditState !== "not-available")) return null;
    if (payload.account.snapshotAvailable && (payload.account.memberState === "not-available" || payload.account.creditState === "not-available")) return null;
    if (!TRAINING_STATUSES.includes(payload.training.latestStatus)) return null;
    if (payload.training.foundationReadyCount > payload.training.attemptCount) return null;
    if (payload.training.attemptCount === 0 && payload.training.latestStatus !== "NO_ATTEMPTS") return null;
    if (payload.training.attemptCount > 0 && payload.training.latestStatus === "NO_ATTEMPTS") return null;
    if ([payload.research.activeCount, payload.research.sourcedCount, payload.research.dueReviewCount].some((value) => value > payload.research.noteCount)) return null;
    if ([payload.planning.readyForReviewCount, payload.planning.blockedCount, payload.planning.reviewCount, payload.planning.completedCount, payload.planning.dueCount].some((value) => value > payload.planning.planCount)) return null;
    if (!PORTFOLIO_STATUSES.includes(payload.portfolio.status)) return null;
    if (payload.portfolio.positionCount === 0 && payload.portfolio.status !== "NO_POSITIONS") return null;
    if (payload.portfolio.positionCount > 0 && payload.portfolio.status === "NO_POSITIONS") return null;
    if (!["INSUFFICIENT_SAMPLE", "EARLY_SAMPLE", "LARGER_SAMPLE"].includes(payload.journal.sampleQuality)) return null;
    if (payload.journal.tradeCount === 0 && payload.journal.sampleQuality !== "INSUFFICIENT_SAMPLE") return null;
    if (!WORKFLOW_STATES.includes(payload.workflow.state)) return null;
    if (!Array.isArray(payload.workflow.actionIds) || payload.workflow.actionIds.length > MAX_ACTIONS) return null;
    if (new Set(payload.workflow.actionIds).size !== payload.workflow.actionIds.length) return null;
    if (payload.workflow.actionIds.some((id) => typeof id !== "string" || !ACTION_ID_RE.test(id))) return null;
    const actionCount = payload.workflow.criticalCount + payload.workflow.highCount + payload.workflow.normalCount + payload.workflow.completeCount;
    if (actionCount !== payload.workflow.actionIds.length) return null;
    if (payload.workflow.state !== workflowState(payload.workflow)) return null;
    if (Object.keys(BOUNDARIES).some((key) => payload.boundaries[key] !== BOUNDARIES[key])) return null;
    return Object.freeze(payload);
  }

  function formatPassport(value) {
    const passport = parsePassport(value);
    if (!passport) return "Invalid GCA Risk Passport";
    return [
      "GCA Risk Passport / Browser-Local Workflow Summary",
      `Generated: ${passport.generatedAt}`,
      `Coverage: ${passport.coverage.completed}/${passport.coverage.total} (${passport.coverage.state})`,
      `Account: ${passport.account.memberState}; credits ${passport.account.creditState}`,
      `Training: ${passport.training.attemptCount} attempt(s); ${passport.training.latestStatus}`,
      `Research: ${passport.research.noteCount} note(s); ${passport.research.dueReviewCount} due`,
      `Planning: ${passport.planning.planCount} plan(s); ${passport.planning.blockedCount} blocked; ${passport.planning.completedCount} completed`,
      `Portfolio: ${passport.portfolio.positionCount} position summary record(s); ${passport.portfolio.status}`,
      `Journal: ${passport.journal.tradeCount} completed-trade record(s); ${passport.journal.sampleQuality}`,
      `Workflow: ${passport.workflow.state}; ${passport.workflow.actionIds.length} local action(s)`,
      "Boundary: no identity, wallet address, balances, note text, plan text, position details, journal details, market data, exchange connection, order execution, signal, or certification."
    ].join("\n");
  }

  return Object.freeze({
    SCHEMA,
    VERSION,
    COVERAGE_TOTAL,
    MAX_ACTIONS,
    BOUNDARIES,
    buildPassport,
    parsePassport,
    formatPassport
  });
});
