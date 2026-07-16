(function attachPortfolioRisk(root, factory) {
  const portfolio = factory();
  root.GcaPortfolioRisk = portfolio;
  if (typeof module !== "undefined" && module.exports) module.exports = portfolio;
})(typeof globalThis !== "undefined" ? globalThis : this, function createPortfolioRisk() {
  "use strict";

  const STORAGE_KEY = "gca_portfolio_risk_v1";
  const SCHEMA = "gca-portfolio-risk-v1";
  const MAX_POSITIONS = 20;
  const POSITION_ID_RE = /^gca_position_[a-z0-9-]{8,64}$/;
  const SYMBOL_RE = /^[A-Z0-9][A-Z0-9._/-]{1,23}$/;
  const SENSITIVE_RE = /private\s*key|seed\s*phrase|mnemonic|api\s*secret|wallet\s*password|one[-\s]*time\s*code|withdrawal\s*permission|remote\s*control|\b(?:otp|2fa)\b|\u79c1\u94a5|\u52a9\u8bb0\u8bcd|\u5bc6\u7801|\u9a8c\u8bc1\u7801|\u63d0\u73b0\u6743\u9650|\u8fdc\u7a0b\u63a7\u5236/i;
  const CONFIG_FIELDS = Object.freeze([
    "accountEquity",
    "riskBudgetPercent",
    "grossExposureLimitPercent",
    "marginLimitPercent",
    "scenarioShockPercent",
    "costBps"
  ]);
  const POSITION_FIELDS = Object.freeze([
    "version",
    "id",
    "symbol",
    "side",
    "quantity",
    "entry",
    "stop",
    "leverage",
    "label",
    "createdAt",
    "updatedAt"
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

  function parseJson(value) {
    try {
      return typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
  }

  function normalizeConfig(input) {
    if (!input || typeof input !== "object") return null;
    const config = {
      accountEquity: finiteNumber(input.accountEquity),
      riskBudgetPercent: finiteNumber(input.riskBudgetPercent),
      grossExposureLimitPercent: finiteNumber(input.grossExposureLimitPercent),
      marginLimitPercent: finiteNumber(input.marginLimitPercent),
      scenarioShockPercent: finiteNumber(input.scenarioShockPercent),
      costBps: finiteNumber(input.costBps)
    };
    if (
      config.accountEquity <= 0 ||
      config.accountEquity > 1e15 ||
      config.riskBudgetPercent <= 0 ||
      config.riskBudgetPercent > 20 ||
      config.grossExposureLimitPercent <= 0 ||
      config.grossExposureLimitPercent > 2000 ||
      config.marginLimitPercent <= 0 ||
      config.marginLimitPercent > 100 ||
      config.scenarioShockPercent <= 0 ||
      config.scenarioShockPercent > 50 ||
      config.costBps < 0 ||
      config.costBps > 2000 ||
      !Object.values(config).every(Number.isFinite)
    ) return null;
    return config;
  }

  function normalizePosition(input) {
    if (!input || typeof input !== "object") return null;
    const id = cleanText(input.id, 80).toLowerCase();
    const symbol = cleanText(input.symbol, 24).toUpperCase();
    const side = input.side === "long" ? "long" : input.side === "short" ? "short" : "";
    const quantity = finiteNumber(input.quantity);
    const entry = finiteNumber(input.entry);
    const stop = finiteNumber(input.stop);
    const leverage = finiteNumber(input.leverage);
    const label = cleanText(input.label, 80);
    const createdAt = normalizedIso(input.createdAt);
    const updatedAt = normalizedIso(input.updatedAt);
    const structureValid = side === "long" ? stop < entry : side === "short" ? stop > entry : false;
    if (
      !POSITION_ID_RE.test(id) ||
      !SYMBOL_RE.test(symbol) ||
      !side ||
      quantity <= 0 ||
      quantity > 1e18 ||
      entry <= 0 ||
      entry > 1e15 ||
      stop <= 0 ||
      stop > 1e15 ||
      leverage < 1 ||
      leverage > 100 ||
      ![quantity, entry, stop, leverage].every(Number.isFinite) ||
      !Number.isFinite(quantity * entry) ||
      !structureValid ||
      SENSITIVE_RE.test(label) ||
      !createdAt ||
      !updatedAt ||
      Date.parse(updatedAt) < Date.parse(createdAt)
    ) return null;
    return {
      version: 1,
      id,
      symbol,
      side,
      quantity,
      entry,
      stop,
      leverage,
      label,
      createdAt,
      updatedAt
    };
  }

  function orderPositions(values) {
    const source = Array.isArray(values) ? values : [];
    const byId = new Map();
    source.forEach((value) => {
      const position = normalizePosition(value);
      if (!position) return;
      const existing = byId.get(position.id);
      if (!existing || Date.parse(position.updatedAt) > Date.parse(existing.updatedAt)) {
        byId.set(position.id, position);
      }
    });
    return [...byId.values()]
      .sort((left, right) =>
        Date.parse(right.updatedAt) - Date.parse(left.updatedAt) ||
        left.symbol.localeCompare(right.symbol) ||
        left.id.localeCompare(right.id)
      )
      .slice(0, MAX_POSITIONS);
  }

  function upsertPosition(values, value) {
    const position = normalizePosition(value);
    if (!position) return orderPositions(values);
    return orderPositions([position, ...orderPositions(values).filter((item) => item.id !== position.id)]);
  }

  function removePosition(values, positionId) {
    return orderPositions(values).filter((position) => position.id !== positionId);
  }

  function analyzePortfolio(configValue, positionValues) {
    const config = normalizeConfig(configValue);
    const positions = orderPositions(positionValues);
    if (!config || !positions.length) return null;
    const costRate = config.costBps / 10_000;
    const shockRate = config.scenarioShockPercent / 100;
    const assetNotional = new Map();
    const rows = positions.map((position) => {
      const multiplier = position.side === "long" ? 1 : -1;
      const notional = position.quantity * position.entry;
      const stopDistance = Math.abs(position.entry - position.stop);
      const stopPercent = (stopDistance / position.entry) * 100;
      const estimatedCosts = notional * costRate;
      const plannedLoss = (position.quantity * stopDistance) + estimatedCosts;
      const requiredMargin = notional / position.leverage;
      const exposurePercent = (notional / config.accountEquity) * 100;
      const riskPercent = (plannedLoss / config.accountEquity) * 100;
      const stressDownPnl = (multiplier * notional * -shockRate) - estimatedCosts;
      const stressUpPnl = (multiplier * notional * shockRate) - estimatedCosts;
      assetNotional.set(position.symbol, (assetNotional.get(position.symbol) || 0) + notional);
      return Object.freeze({
        ...position,
        notional,
        signedNotional: multiplier * notional,
        stopDistance,
        stopPercent,
        estimatedCosts,
        plannedLoss,
        requiredMargin,
        exposurePercent,
        riskPercent,
        stressDownPnl,
        stressUpPnl
      });
    });
    const grossNotional = rows.reduce((sum, row) => sum + row.notional, 0);
    const netNotional = rows.reduce((sum, row) => sum + row.signedNotional, 0);
    const longNotional = rows.filter((row) => row.side === "long").reduce((sum, row) => sum + row.notional, 0);
    const shortNotional = rows.filter((row) => row.side === "short").reduce((sum, row) => sum + row.notional, 0);
    const totalPlannedLoss = rows.reduce((sum, row) => sum + row.plannedLoss, 0);
    const totalRequiredMargin = rows.reduce((sum, row) => sum + row.requiredMargin, 0);
    const stressDownPnl = rows.reduce((sum, row) => sum + row.stressDownPnl, 0);
    const stressUpPnl = rows.reduce((sum, row) => sum + row.stressUpPnl, 0);
    const worstStressPnl = Math.min(stressDownPnl, stressUpPnl);
    const worstStressLoss = Math.max(0, -worstStressPnl);
    const riskBudgetAmount = config.accountEquity * (config.riskBudgetPercent / 100);
    const totalRiskPercent = (totalPlannedLoss / config.accountEquity) * 100;
    const riskBudgetUsedPercent = (totalPlannedLoss / riskBudgetAmount) * 100;
    const grossExposurePercent = (grossNotional / config.accountEquity) * 100;
    const netExposurePercent = (netNotional / config.accountEquity) * 100;
    const marginUtilizationPercent = (totalRequiredMargin / config.accountEquity) * 100;
    const directionConcentrationPercent = grossNotional ? (Math.abs(netNotional) / grossNotional) * 100 : 0;
    const largestPosition = [...rows].sort((left, right) => right.notional - left.notional)[0];
    const largestRiskPosition = [...rows].sort((left, right) => right.plannedLoss - left.plannedLoss)[0];
    const largestAssetEntry = [...assetNotional.entries()].sort((left, right) => right[1] - left[1])[0];
    const largestPositionConcentrationPercent = grossNotional ? (largestPosition.notional / grossNotional) * 100 : 0;
    const largestRiskConcentrationPercent = totalPlannedLoss ? (largestRiskPosition.plannedLoss / totalPlannedLoss) * 100 : 0;
    const largestAssetConcentrationPercent = grossNotional ? (largestAssetEntry[1] / grossNotional) * 100 : 0;
    const maxLeverage = Math.max(...rows.map((row) => row.leverage));
    const findings = [];
    const addFinding = (code, level, message) => findings.push(Object.freeze({ code, level, message }));

    if (totalPlannedLoss > riskBudgetAmount) {
      addFinding("RISK_BUDGET_EXCEEDED", "blocker", "Combined planned stop loss exceeds the portfolio risk budget.");
    } else if (riskBudgetUsedPercent >= 80) {
      addFinding("RISK_BUDGET_NEAR_LIMIT", "warning", "Combined planned risk uses at least 80% of the portfolio risk budget.");
    }
    if (grossExposurePercent > config.grossExposureLimitPercent) {
      addFinding("GROSS_EXPOSURE_EXCEEDED", "blocker", "Gross notional exposure exceeds the configured portfolio limit.");
    } else if (grossExposurePercent >= config.grossExposureLimitPercent * 0.8) {
      addFinding("GROSS_EXPOSURE_NEAR_LIMIT", "warning", "Gross notional exposure is within 20% of the configured limit.");
    }
    if (marginUtilizationPercent > config.marginLimitPercent) {
      addFinding("MARGIN_LIMIT_EXCEEDED", "blocker", "Combined required margin exceeds the configured equity limit.");
    } else if (marginUtilizationPercent >= config.marginLimitPercent * 0.8) {
      addFinding("MARGIN_NEAR_LIMIT", "warning", "Combined required margin is within 20% of the configured limit.");
    }
    if (largestAssetConcentrationPercent > 50) {
      addFinding("ASSET_CONCENTRATION", "warning", "One symbol represents more than half of gross portfolio exposure.");
    }
    if (largestRiskConcentrationPercent > 50 && rows.length > 1) {
      addFinding("RISK_CONCENTRATION", "warning", "One position contributes more than half of combined planned risk.");
    }
    if (directionConcentrationPercent > 80 && rows.length > 1) {
      addFinding("DIRECTION_CONCENTRATION", "warning", "Net direction represents more than 80% of gross exposure.");
    }
    if (maxLeverage > 10) {
      addFinding("HIGH_LEVERAGE_PRESENT", "warning", "At least one position uses leverage above 10x.");
    }
    if (worstStressLoss > riskBudgetAmount) {
      addFinding("STRESS_LOSS_ABOVE_BUDGET", "warning", "The configured broad-market stress move produces a modeled loss above the portfolio risk budget.");
    }
    if (!findings.length) {
      addFinding("WITHIN_CONFIGURED_LIMITS", "good", "The entered portfolio is within the configured risk, exposure, and margin limits.");
    }
    const blockerCount = findings.filter((finding) => finding.level === "blocker").length;
    const warningCount = findings.filter((finding) => finding.level === "warning").length;
    const status = blockerCount ? "BLOCKED" : warningCount ? "REVIEW" : "WITHIN_LIMITS";

    return Object.freeze({
      config,
      positions: rows,
      status,
      blockerCount,
      warningCount,
      findings,
      positionCount: rows.length,
      grossNotional,
      netNotional,
      longNotional,
      shortNotional,
      totalPlannedLoss,
      totalRequiredMargin,
      riskBudgetAmount,
      totalRiskPercent,
      riskBudgetUsedPercent,
      grossExposurePercent,
      netExposurePercent,
      marginUtilizationPercent,
      directionConcentrationPercent,
      largestPositionSymbol: largestPosition.symbol,
      largestPositionConcentrationPercent,
      largestRiskSymbol: largestRiskPosition.symbol,
      largestRiskConcentrationPercent,
      largestAssetSymbol: largestAssetEntry[0],
      largestAssetConcentrationPercent,
      maxLeverage,
      stressDownPnl,
      stressUpPnl,
      worstStressPnl,
      worstStressLoss,
      worstStressLossPercent: (worstStressLoss / config.accountEquity) * 100
    });
  }

  function exactObject(value, normalized, fields) {
    if (!value || typeof value !== "object" || !normalized) return false;
    const keys = Object.keys(value);
    return keys.length === fields.length &&
      keys.every((key) => fields.includes(key)) &&
      fields.every((key) => value[key] === normalized[key]);
  }

  function buildBackup(configValue, positionValues, savedAt) {
    const config = normalizeConfig(configValue);
    const positions = orderPositions(positionValues);
    const timestamp = normalizedIso(savedAt) || new Date().toISOString();
    if (!config || !positions.length) return null;
    return Object.freeze({
      schema: SCHEMA,
      version: 1,
      savedAt: timestamp,
      config,
      positions
    });
  }

  function parseBackup(value) {
    const payload = parseJson(value);
    if (!payload || typeof payload !== "object") return null;
    const keys = Object.keys(payload);
    const savedAt = normalizedIso(payload.savedAt);
    if (
      keys.length !== 5 ||
      keys.some((key) => !["schema", "version", "savedAt", "config", "positions"].includes(key)) ||
      payload.schema !== SCHEMA ||
      payload.version !== 1 ||
      !savedAt ||
      payload.savedAt !== savedAt ||
      !Array.isArray(payload.positions) ||
      payload.positions.length === 0 ||
      payload.positions.length > MAX_POSITIONS
    ) return null;
    const config = normalizeConfig(payload.config);
    if (!exactObject(payload.config, config, CONFIG_FIELDS)) return null;
    const normalizedPositions = payload.positions.map(normalizePosition);
    if (normalizedPositions.some((position, index) => !exactObject(payload.positions[index], position, POSITION_FIELDS))) return null;
    const positions = orderPositions(normalizedPositions);
    if (positions.length !== payload.positions.length) return null;
    return Object.freeze({ schema: SCHEMA, version: 1, savedAt, config, positions });
  }

  return Object.freeze({
    STORAGE_KEY,
    SCHEMA,
    MAX_POSITIONS,
    normalizeConfig,
    normalizePosition,
    orderPositions,
    upsertPosition,
    removePosition,
    analyzePortfolio,
    buildBackup,
    parseBackup
  });
});
