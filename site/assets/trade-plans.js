(function attachTradePlans(root, factory) {
  const tradePlans = factory();
  root.GcaTradePlans = tradePlans;
  if (typeof module !== "undefined" && module.exports) module.exports = tradePlans;
})(typeof globalThis !== "undefined" ? globalThis : this, function createTradePlans() {
  "use strict";

  const STORAGE_KEY = "gca_trade_plans_v1";
  const SCHEMA = "gca-trade-plans-v1";
  const MAX_PLANS = 100;
  const PLAN_ID_RE = /^gca_plan_[a-z0-9-]{8,64}$/;
  const SYMBOL_RE = /^[A-Z0-9][A-Z0-9._/-]{1,23}$/;
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
  const SENSITIVE_RE = /private\s*key|seed\s*phrase|mnemonic|api\s*secret|wallet\s*password|one[-\s]*time\s*code|withdrawal\s*permission|remote\s*control|\b(?:otp|2fa)\b|\u79c1\u94a5|\u52a9\u8bb0\u8bcd|\u5bc6\u7801|\u9a8c\u8bc1\u7801|\u63d0\u73b0\u6743\u9650|\u8fdc\u7a0b\u63a7\u5236/i;
  const TIMEFRAMES = Object.freeze(["15m", "1h", "4h", "1d", "1w", "other"]);
  const WORKFLOW_STATUSES = Object.freeze(["draft", "under-review", "completed", "invalidated", "cancelled"]);
  const ORDER_TYPES = Object.freeze(["market", "limit", "stop", "other"]);
  const RESEARCH_HANDOFF_FIELDS = Object.freeze(["source", "title", "theme", "thesis", "invalidation", "riskNotes"]);
  const BOOLEAN_FIELDS = Object.freeze([
    "positionSized",
    "maxLossAccepted",
    "liquidityChecked",
    "volatilityReviewed",
    "noRevengeTrade",
    "noFomo",
    "exitPlanDefined",
    "simulationReviewed"
  ]);
  const PLAN_FIELDS = Object.freeze([
    "version",
    "id",
    "createdAt",
    "updatedAt",
    "plannedFor",
    "symbol",
    "direction",
    "timeframe",
    "workflowStatus",
    "thesis",
    "invalidation",
    "entry",
    "stop",
    "target",
    "equity",
    "riskPercent",
    "leverage",
    "feeBps",
    "slippageBps",
    "exposureLimitPercent",
    "volatilityPercent",
    "liquidityCoverage",
    "orderType",
    ...BOOLEAN_FIELDS
  ]);

  function cleanText(value, maxLength) {
    return String(value || "").trim().replace(/\s+/g, " ").slice(0, maxLength);
  }

  function finiteNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : NaN;
  }

  function normalizedIso(value) {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? new Date(parsed).toISOString() : "";
  }

  function normalizeDate(value) {
    const date = cleanText(value, 10);
    if (!date) return "";
    if (!DATE_RE.test(date)) return null;
    const parsed = Date.parse(`${date}T00:00:00Z`);
    return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 10) === date ? date : null;
  }

  function parseJson(value) {
    try {
      return typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
  }

  function strictHandoffText(params, key, maxLength, minLength) {
    const values = params.getAll(key);
    if (values.length !== 1) return null;
    const value = String(values[0] || "").trim().replace(/\s+/g, " ");
    if (value.length < minLength || value.length > maxLength) return null;
    return value;
  }

  function parseResearchHandoff(value) {
    const raw = String(value || "").replace(/^#/, "");
    if (!raw || raw.length > 12000) return null;
    const params = new URLSearchParams(raw);
    const keys = [...params.keys()];
    if (keys.length !== RESEARCH_HANDOFF_FIELDS.length || keys.some((key) => !RESEARCH_HANDOFF_FIELDS.includes(key))) return null;
    const source = strictHandoffText(params, "source", 20, 1);
    const title = strictHandoffText(params, "title", 100, 3);
    const theme = strictHandoffText(params, "theme", 60, 2);
    const thesis = strictHandoffText(params, "thesis", 400, 20);
    const invalidation = strictHandoffText(params, "invalidation", 250, 10);
    const riskNotes = strictHandoffText(params, "riskNotes", 200, 10);
    if (!source || source !== "research-note" || !title || !theme || !thesis || !invalidation || !riskNotes) return null;
    if (SENSITIVE_RE.test(`${title} ${theme} ${thesis} ${invalidation} ${riskNotes}`)) return null;
    return Object.freeze({
      source,
      title,
      theme,
      timeframe: "other",
      workflowStatus: "draft",
      thesis: cleanText(`${title} [${theme}]. ${thesis} Risk context: ${riskNotes}`, 800),
      invalidation
    });
  }

  function normalizePlan(input) {
    if (!input || typeof input !== "object") return null;
    const id = cleanText(input.id, 80).toLowerCase();
    const createdAt = normalizedIso(input.createdAt);
    const updatedAt = normalizedIso(input.updatedAt);
    const plannedFor = normalizeDate(input.plannedFor);
    const symbol = cleanText(input.symbol, 24).toUpperCase();
    const direction = input.direction === "short" ? "short" : input.direction === "long" ? "long" : "";
    const timeframe = TIMEFRAMES.includes(input.timeframe) ? input.timeframe : "";
    const workflowStatus = WORKFLOW_STATUSES.includes(input.workflowStatus) ? input.workflowStatus : "";
    const thesis = cleanText(input.thesis, 800);
    const invalidation = cleanText(input.invalidation, 500);
    const entry = finiteNumber(input.entry);
    const stop = finiteNumber(input.stop);
    const target = finiteNumber(input.target);
    const equity = finiteNumber(input.equity);
    const riskPercent = finiteNumber(input.riskPercent);
    const leverage = finiteNumber(input.leverage);
    const feeBps = finiteNumber(input.feeBps);
    const slippageBps = finiteNumber(input.slippageBps);
    const exposureLimitPercent = finiteNumber(input.exposureLimitPercent);
    const volatilityPercent = finiteNumber(input.volatilityPercent);
    const liquidityCoverage = finiteNumber(input.liquidityCoverage);
    const orderType = ORDER_TYPES.includes(input.orderType) ? input.orderType : "";
    const priceStructureValid = direction === "long"
      ? stop < entry && target > entry
      : direction === "short"
        ? stop > entry && target < entry
        : false;
    const numericValues = [entry, stop, target, equity, riskPercent, leverage, feeBps, slippageBps, exposureLimitPercent, volatilityPercent, liquidityCoverage];
    if (
      !PLAN_ID_RE.test(id) ||
      !createdAt ||
      !updatedAt ||
      Date.parse(updatedAt) < Date.parse(createdAt) ||
      plannedFor === null ||
      !SYMBOL_RE.test(symbol) ||
      !direction ||
      !timeframe ||
      !workflowStatus ||
      thesis.length < 20 ||
      invalidation.length < 10 ||
      SENSITIVE_RE.test(`${thesis} ${invalidation}`) ||
      !numericValues.every(Number.isFinite) ||
      entry <= 0 || entry > 1e15 ||
      stop <= 0 || stop > 1e15 ||
      target <= 0 || target > 1e15 ||
      equity <= 0 || equity > 1e15 ||
      riskPercent < 0.1 || riskPercent > 5 ||
      leverage < 1 || leverage > 100 ||
      feeBps < 0 || feeBps > 2000 ||
      slippageBps < 0 || slippageBps > 2000 ||
      exposureLimitPercent < 1 || exposureLimitPercent > 2000 ||
      volatilityPercent < 0 || volatilityPercent > 1000 ||
      liquidityCoverage < 0 || liquidityCoverage > 1e9 ||
      !orderType ||
      !priceStructureValid
    ) return null;
    return {
      version: 1,
      id,
      createdAt,
      updatedAt,
      plannedFor,
      symbol,
      direction,
      timeframe,
      workflowStatus,
      thesis,
      invalidation,
      entry,
      stop,
      target,
      equity,
      riskPercent,
      leverage,
      feeBps,
      slippageBps,
      exposureLimitPercent,
      volatilityPercent,
      liquidityCoverage,
      orderType,
      ...Object.fromEntries(BOOLEAN_FIELDS.map((field) => [field, input[field] === true]))
    };
  }

  function orderPlans(values) {
    const byId = new Map();
    (Array.isArray(values) ? values : []).forEach((value) => {
      const plan = normalizePlan(value);
      if (!plan) return;
      const existing = byId.get(plan.id);
      if (!existing || Date.parse(plan.updatedAt) > Date.parse(existing.updatedAt)) byId.set(plan.id, plan);
    });
    return [...byId.values()]
      .sort((left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt) || left.symbol.localeCompare(right.symbol) || left.id.localeCompare(right.id))
      .slice(0, MAX_PLANS);
  }

  function upsertPlan(values, value) {
    const plan = normalizePlan(value);
    if (!plan) return orderPlans(values);
    return orderPlans([plan, ...orderPlans(values).filter((item) => item.id !== plan.id)]);
  }

  function removePlan(values, planId) {
    return orderPlans(values).filter((plan) => plan.id !== planId);
  }

  function analyzePlan(value) {
    const plan = normalizePlan(value);
    if (!plan) return null;
    const costRate = (plan.feeBps + plan.slippageBps) / 10_000;
    const stopDistance = Math.abs(plan.entry - plan.stop);
    const targetDistance = Math.abs(plan.target - plan.entry);
    const stopPercent = (stopDistance / plan.entry) * 100;
    const riskBudget = plan.equity * (plan.riskPercent / 100);
    const riskPerUnit = stopDistance + (plan.entry * costRate);
    const positionQuantity = riskBudget / riskPerUnit;
    const positionNotional = positionQuantity * plan.entry;
    const estimatedCosts = positionNotional * costRate;
    const plannedLoss = (positionQuantity * stopDistance) + estimatedCosts;
    const requiredMargin = positionNotional / plan.leverage;
    const exposurePercent = (positionNotional / plan.equity) * 100;
    const exposureLimitUsedPercent = (exposurePercent / plan.exposureLimitPercent) * 100;
    const rewardRisk = targetDistance / riskPerUnit;
    const targetPnlAfterCosts = (positionQuantity * targetDistance) - estimatedCosts;
    const findings = [];
    const addFinding = (code, level, message) => findings.push(Object.freeze({ code, level, message }));
    const archived = ["completed", "invalidated", "cancelled"].includes(plan.workflowStatus);

    if (!archived) {
      if (plan.riskPercent > 3) addFinding("RISK_ABOVE_HARD_LIMIT", "blocker", "Risk per trade is above the published 3% hard limit.");
      else if (plan.riskPercent > 2) addFinding("RISK_ABOVE_REVIEW_LEVEL", "warning", "Risk per trade is above the published 2% review level.");
      if (plan.leverage > 20) addFinding("LEVERAGE_ABOVE_HARD_LIMIT", "blocker", "Leverage is above the published 20x hard limit.");
      else if (plan.leverage > 10) addFinding("LEVERAGE_ABOVE_REVIEW_LEVEL", "warning", "Leverage is above the published 10x review level.");
      if (exposurePercent > plan.exposureLimitPercent) addFinding("EXPOSURE_LIMIT_EXCEEDED", "blocker", "Calculated notional exposure exceeds the user-defined account exposure limit.");
      else if (exposureLimitUsedPercent >= 80) addFinding("EXPOSURE_NEAR_LIMIT", "warning", "Calculated notional exposure uses at least 80% of the user-defined limit.");
      if (rewardRisk < 1) addFinding("REWARD_RISK_BELOW_ONE", "warning", "Modeled reward-to-risk is below 1 after estimated costs.");
      if (!plan.positionSized) addFinding("POSITION_SIZE_NOT_REVIEWED", "blocker", "Confirm that the calculated position size has been reviewed.");
      if (!plan.maxLossAccepted) addFinding("MAX_LOSS_NOT_ACCEPTED", "blocker", "Confirm that the planned maximum loss is acceptable.");
      if (!plan.liquidityChecked) addFinding("LIQUIDITY_NOT_REVIEWED", "blocker", "Review liquidity and expected slippage before the plan can advance.");
      if (!plan.noRevengeTrade) addFinding("REVENGE_TRADE_NOT_CLEARED", "blocker", "Confirm that the plan is not driven by revenge trading.");
      if (!plan.simulationReviewed) addFinding("SIMULATION_NOT_REVIEWED", "blocker", "Complete a simulation or testnet review before the plan can advance.");
      if (!plan.volatilityReviewed) addFinding("VOLATILITY_NOT_REVIEWED", "warning", "Review event and volatility risk.");
      if (!plan.noFomo) addFinding("FOMO_NOT_CLEARED", "warning", "Confirm that the entry is not driven by FOMO.");
      if (!plan.exitPlanDefined) addFinding("EXIT_PLAN_INCOMPLETE", "warning", "Define the exit and cancellation process.");
      if (plan.liquidityCoverage < 5) addFinding("LOW_DECLARED_LIQUIDITY_COVERAGE", "warning", "Declared liquidity coverage is below 5x planned notional.");
    } else {
      addFinding("ARCHIVED_WORKFLOW", "good", `This plan is archived with workflow status ${plan.workflowStatus}.`);
    }
    if (!findings.length) addFinding("READY_FOR_MANUAL_REVIEW", "good", "All published trade-plan checks passed for manual review.");
    const blockerCount = findings.filter((item) => item.level === "blocker").length;
    const warningCount = findings.filter((item) => item.level === "warning").length;
    const status = archived
      ? plan.workflowStatus.toUpperCase().replaceAll("-", "_")
      : blockerCount
        ? "NOT_READY"
        : warningCount
          ? "REVIEW"
          : "READY_FOR_REVIEW";
    return Object.freeze({
      plan,
      status,
      blockerCount,
      warningCount,
      findings,
      riskBudget,
      stopDistance,
      stopPercent,
      riskPerUnit,
      positionQuantity,
      positionNotional,
      estimatedCosts,
      plannedLoss,
      requiredMargin,
      exposurePercent,
      exposureLimitUsedPercent,
      rewardRisk,
      targetPnlAfterCosts
    });
  }

  function summarizePlans(values, nowMs) {
    const plans = orderPlans(values);
    const today = new Date(Number.isFinite(Number(nowMs)) ? Number(nowMs) : Date.now()).toISOString().slice(0, 10);
    const analyses = plans.map(analyzePlan).filter(Boolean);
    const active = analyses.filter((item) => ["draft", "under-review"].includes(item.plan.workflowStatus));
    return Object.freeze({
      count: plans.length,
      activeCount: active.length,
      readyForReviewCount: active.filter((item) => item.status === "READY_FOR_REVIEW").length,
      blockedCount: active.filter((item) => item.status === "NOT_READY").length,
      reviewCount: active.filter((item) => item.status === "REVIEW").length,
      completedCount: analyses.filter((item) => item.plan.workflowStatus === "completed").length,
      archivedCount: analyses.filter((item) => ["completed", "invalidated", "cancelled"].includes(item.plan.workflowStatus)).length,
      dueCount: active.filter((item) => item.plan.plannedFor && item.plan.plannedFor <= today).length,
      latestUpdatedAt: plans.length ? plans[0].updatedAt : null
    });
  }

  function filterPlans(values, filters, nowMs) {
    const requested = filters && typeof filters === "object" ? filters : {};
    const query = cleanText(requested.query, 100).toLowerCase();
    const workflowStatus = WORKFLOW_STATUSES.includes(requested.workflowStatus) ? requested.workflowStatus : "";
    const readiness = ["NOT_READY", "REVIEW", "READY_FOR_REVIEW"].includes(requested.readiness) ? requested.readiness : "";
    const dueOnly = requested.dueOnly === true;
    const today = new Date(Number.isFinite(Number(nowMs)) ? Number(nowMs) : Date.now()).toISOString().slice(0, 10);
    return orderPlans(values).filter((plan) => {
      const analysis = analyzePlan(plan);
      if (query && !`${plan.symbol} ${plan.timeframe} ${plan.thesis} ${plan.invalidation}`.toLowerCase().includes(query)) return false;
      if (workflowStatus && plan.workflowStatus !== workflowStatus) return false;
      if (readiness && analysis.status !== readiness) return false;
      if (dueOnly && (!plan.plannedFor || plan.plannedFor > today || !["draft", "under-review"].includes(plan.workflowStatus))) return false;
      return true;
    });
  }

  function fragment(values) {
    return new URLSearchParams(Object.entries(values).map(([key, value]) => [key, String(value)])).toString();
  }

  function buildHandoffLinks(value) {
    const analysis = analyzePlan(value);
    if (!analysis) return null;
    const plan = analysis.plan;
    const slipPrice = plan.entry * (plan.slippageBps / 10_000);
    const scenarioExit = plan.direction === "long" ? Math.max(Number.EPSILON, plan.stop - slipPrice) : plan.stop + slipPrice;
    const checklist = {
      positionSized: plan.positionSized ? 1 : 0,
      maxLossAccepted: plan.maxLossAccepted ? 1 : 0,
      invalidationDefined: 1,
      liquidityChecked: plan.liquidityChecked ? 1 : 0,
      costsIncluded: 1,
      volatilityReviewed: plan.volatilityReviewed ? 1 : 0,
      noRevengeTrade: plan.noRevengeTrade ? 1 : 0,
      noFomo: plan.noFomo ? 1 : 0,
      exitPlanDefined: plan.exitPlanDefined ? 1 : 0
    };
    const journalNotes = cleanText(`Plan thesis: ${plan.thesis} Invalidation: ${plan.invalidation}`, 500);
    return Object.freeze({
      calculator: `risk-calculator.html#${fragment({ source: "trade-plan", equity: plan.equity, entry: plan.entry, stop: plan.stop, target: plan.target, risk: plan.riskPercent, leverage: plan.leverage, feeBps: plan.feeBps, slippageBps: plan.slippageBps })}`,
      portfolio: `portfolio-risk.html#${fragment({ source: "trade-plan", symbol: plan.symbol, side: plan.direction, quantity: analysis.positionQuantity, entry: plan.entry, stop: plan.stop, leverage: plan.leverage, label: `${plan.timeframe} trade plan` })}`,
      warning: `risk-warning.html#${fragment({ source: "trade-plan", exposure: analysis.exposurePercent, leverage: plan.leverage, risk: plan.riskPercent, stopDistance: analysis.stopPercent, slippage: plan.slippageBps / 100, volatility: plan.volatilityPercent, liquidity: plan.liquidityCoverage })}`,
      entryReady: `entry-ready.html#${fragment({ source: "trade-plan", direction: plan.direction, timeframe: plan.timeframe, entry: plan.entry, stop: plan.stop, target: plan.target, risk: plan.riskPercent, leverage: plan.leverage, orderType: plan.orderType === "stop" ? "stop-limit" : plan.orderType, thesis: plan.thesis.slice(0, 300), ...checklist })}`,
      replay: `liquidation-replay.html#${fragment({ source: "trade-plan", direction: plan.direction, accountEquity: plan.equity, quantity: analysis.positionQuantity, entry: plan.entry, exit: scenarioExit, plannedStop: plan.stop, leverage: plan.leverage, fees: analysis.estimatedCosts, funding: 0 })}`,
      journal: plan.workflowStatus === "completed"
        ? `trade-journal.html#${fragment({ source: "trade-plan", symbol: plan.symbol, direction: plan.direction, setup: `${plan.timeframe} ${plan.orderType} plan`, notes: journalNotes })}`
        : null
    });
  }

  function exactPlan(value, normalized) {
    if (!value || typeof value !== "object" || !normalized) return false;
    const keys = Object.keys(value);
    return keys.length === PLAN_FIELDS.length && keys.every((key) => PLAN_FIELDS.includes(key)) && PLAN_FIELDS.every((key) => value[key] === normalized[key]);
  }

  function buildBackup(values, exportedAt) {
    const plans = orderPlans(values);
    const timestamp = normalizedIso(exportedAt) || new Date().toISOString();
    if (!plans.length) return null;
    return Object.freeze({ schema: SCHEMA, version: 1, exportedAt: timestamp, plans });
  }

  function parseBackup(value) {
    const payload = parseJson(value);
    if (!payload || typeof payload !== "object") return null;
    const keys = Object.keys(payload);
    const exportedAt = normalizedIso(payload.exportedAt);
    if (
      keys.length !== 4 ||
      keys.some((key) => !["schema", "version", "exportedAt", "plans"].includes(key)) ||
      payload.schema !== SCHEMA ||
      payload.version !== 1 ||
      !exportedAt ||
      payload.exportedAt !== exportedAt ||
      !Array.isArray(payload.plans) ||
      payload.plans.length === 0 ||
      payload.plans.length > MAX_PLANS
    ) return null;
    const normalized = payload.plans.map(normalizePlan);
    if (normalized.some((plan, index) => !exactPlan(payload.plans[index], plan))) return null;
    const plans = orderPlans(normalized);
    if (plans.length !== payload.plans.length) return null;
    return Object.freeze({ schema: SCHEMA, version: 1, exportedAt, plans });
  }

  function mergeBackup(currentValues, backupValue) {
    const backup = parseBackup(backupValue);
    if (!backup) return null;
    const current = orderPlans(currentValues);
    const currentById = new Map(current.map((plan) => [plan.id, plan]));
    const merged = new Map(currentById);
    const updatedIds = new Set();
    backup.plans.forEach((plan) => {
      const existing = merged.get(plan.id);
      if (!existing || Date.parse(plan.updatedAt) > Date.parse(existing.updatedAt)) {
        merged.set(plan.id, plan);
        if (existing) updatedIds.add(plan.id);
      }
    });
    const plans = orderPlans([...merged.values()]);
    const retained = new Set(plans.map((plan) => plan.id));
    return Object.freeze({
      plans,
      importedPlanCount: backup.plans.length,
      addedPlanCount: backup.plans.filter((plan) => !currentById.has(plan.id) && retained.has(plan.id)).length,
      updatedPlanCount: [...updatedIds].filter((id) => retained.has(id)).length,
      droppedNewPlanCount: backup.plans.filter((plan) => !currentById.has(plan.id) && !retained.has(plan.id)).length
    });
  }

  return Object.freeze({
    STORAGE_KEY,
    SCHEMA,
    MAX_PLANS,
    TIMEFRAMES,
    WORKFLOW_STATUSES,
    ORDER_TYPES,
    normalizePlan,
    orderPlans,
    upsertPlan,
    removePlan,
    analyzePlan,
    summarizePlans,
    filterPlans,
    parseResearchHandoff,
    buildHandoffLinks,
    buildBackup,
    parseBackup,
    mergeBackup
  });
});
