(function attachGcaRiskCalculator(root, factory) {
  const calculator = factory();
  root.GcaRiskCalculator = calculator;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = calculator;
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function createGcaRiskCalculator() {
  "use strict";

  function finiteNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : NaN;
  }

  function calculatePositionPlan(input) {
    const equity = finiteNumber(input.equity);
    const riskPercent = finiteNumber(input.riskPercent);
    const entry = finiteNumber(input.entry);
    const stop = finiteNumber(input.stop);
    const target = finiteNumber(input.target);
    const leverage = finiteNumber(input.leverage);
    const feeBps = finiteNumber(input.feeBps);
    const slippageBps = finiteNumber(input.slippageBps);

    if (![equity, riskPercent, entry, stop, leverage, feeBps, slippageBps].every(Number.isFinite) ||
        equity <= 0 || riskPercent <= 0 || riskPercent > 5 || entry <= 0 || stop <= 0 ||
        entry === stop || leverage < 1 || leverage > 100 || feeBps < 0 || slippageBps < 0) {
      return null;
    }

    const direction = stop < entry ? "long" : "short";
    const riskBudget = equity * (riskPercent / 100);
    const stopDistance = Math.abs(entry - stop);
    const stopPercent = (stopDistance / entry) * 100;
    const costRate = (feeBps + slippageBps) / 10_000;
    const riskPerUnit = stopDistance + (entry * costRate);
    const positionQuantity = riskBudget / riskPerUnit;
    const positionNotional = positionQuantity * entry;
    const estimatedCosts = positionNotional * costRate;
    const plannedLoss = (positionQuantity * stopDistance) + estimatedCosts;
    const requiredMargin = positionNotional / leverage;
    const exposurePercent = (positionNotional / equity) * 100;
    const targetDistance = Number.isFinite(target) && target > 0 ? Math.abs(target - entry) : 0;
    const rewardRisk = targetDistance > 0 ? targetDistance / riskPerUnit : null;
    const targetOnCorrectSide = !targetDistance || (direction === "long" ? target > entry : target < entry);

    return Object.freeze({
      equity,
      riskPercent,
      entry,
      stop,
      target,
      leverage,
      feeBps,
      slippageBps,
      direction,
      riskBudget,
      stopDistance,
      stopPercent,
      costRate,
      riskPerUnit,
      positionQuantity,
      positionNotional,
      estimatedCosts,
      plannedLoss,
      requiredMargin,
      exposurePercent,
      rewardRisk,
      targetOnCorrectSide
    });
  }

  return Object.freeze({ calculatePositionPlan });
});

