(function attachRiskWarning(root, factory) {
  const engine = factory();
  root.GcaRiskWarning = engine;
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
})(typeof globalThis !== "undefined" ? globalThis : this, function createRiskWarning() {
  "use strict";

  const finite = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : NaN;
  };
  const checked = (value) => value === true;

  function review(input) {
    const exposurePercent = finite(input.exposurePercent);
    const leverage = finite(input.leverage);
    const riskPercent = finite(input.riskPercent);
    const stopDistancePercent = finite(input.stopDistancePercent);
    const slippagePercent = finite(input.slippagePercent);
    const volatilityPercent = finite(input.volatilityPercent);
    const liquidityCoverage = finite(input.liquidityCoverage);
    const fundingPercent = finite(input.fundingPercent);
    const correlatedPositions = finite(input.correlatedPositions);
    const numbers = [exposurePercent, leverage, riskPercent, stopDistancePercent, slippagePercent, volatilityPercent, liquidityCoverage, fundingPercent, correlatedPositions];
    if (!numbers.every(Number.isFinite) || exposurePercent < 0 || leverage < 1 || riskPercent < 0 ||
        stopDistancePercent <= 0 || slippagePercent < 0 || volatilityPercent < 0 ||
        liquidityCoverage < 0 || correlatedPositions < 0) return null;

    let account = 0;
    let market = 0;
    let process = 0;
    const blockers = [];
    const warnings = [];
    const actions = [];

    if (riskPercent > 3) {
      account += 15;
      blockers.push("Risk per trade is above 3%. / 单笔风险超过 3%。");
      actions.push("Reduce the risk budget before recalculating position size. / 先降低风险预算，再重新计算仓位。");
    } else if (riskPercent > 2) {
      account += 10;
      warnings.push("Risk per trade is above 2%. / 单笔风险超过 2%。");
    } else if (riskPercent > 1) account += 4;

    if (exposurePercent > 100) {
      account += 12;
      blockers.push("Account exposure is above 100%. / 账户敞口超过 100%。");
      actions.push("Lower notional exposure or isolate the risk. / 降低名义敞口或隔离风险。");
    } else if (exposurePercent > 50) {
      account += 8;
      warnings.push("Account exposure is above 50%. / 账户敞口超过 50%。");
    } else if (exposurePercent > 25) account += 4;

    if (leverage > 20) {
      account += 13;
      blockers.push("Selected leverage is above 20x. / 选择杠杆超过 20 倍。");
      actions.push("Reduce leverage and recalculate margin use. / 降低杠杆并重新计算保证金占比。");
    } else if (leverage > 10) {
      account += 9;
      warnings.push("Selected leverage is above 10x. / 选择杠杆超过 10 倍。");
    } else if (leverage > 5) account += 5;
    else if (leverage > 2) account += 2;
    account = Math.min(40, account);

    if (slippagePercent > 2) {
      market += 10;
      blockers.push("Estimated slippage is above 2%. / 预计滑点超过 2%。");
      actions.push("Reduce order size or wait for deeper liquidity. / 降低订单规模或等待更深流动性。");
    } else if (slippagePercent > 1) market += 7;
    else if (slippagePercent > 0.5) market += 4;
    else if (slippagePercent > 0.2) market += 2;

    if (volatilityPercent > 15) market += 10;
    else if (volatilityPercent > 10) market += 7;
    else if (volatilityPercent > 5) market += 4;
    else if (volatilityPercent > 2) market += 2;
    if (volatilityPercent > 10) warnings.push("Entered volatility is above 10%. / 输入波动率超过 10%。");

    if (liquidityCoverage < 1) {
      market += 10;
      blockers.push("Visible liquidity does not cover the planned order size. / 可见流动性不足以覆盖计划订单。");
      actions.push("Do not submit the current size into insufficient liquidity. / 不要将当前规模提交到流动性不足的市场。");
    } else if (liquidityCoverage < 3) market += 7;
    else if (liquidityCoverage < 5) market += 4;
    else if (liquidityCoverage < 10) market += 2;

    const fundingAbsolute = Math.abs(fundingPercent);
    if (fundingAbsolute > 0.1) market += 5;
    else if (fundingAbsolute > 0.05) market += 3;
    else if (fundingAbsolute > 0.02) market += 1;
    if (fundingAbsolute > 0.05) warnings.push("Absolute funding rate is elevated. / 资金费率绝对值偏高。");

    if (stopDistancePercent <= slippagePercent) {
      market += 3;
      blockers.push("Stop distance is not greater than estimated slippage. / 止损距离没有大于预计滑点。");
      actions.push("Widen the invalidation structure or reduce execution friction. / 调整失效结构或降低执行摩擦。");
    } else if (stopDistancePercent <= slippagePercent * 2) {
      market += 2;
      warnings.push("Stop distance is close to estimated execution slippage. / 止损距离接近预计执行滑点。");
    }
    market = Math.min(35, market);

    if (!checked(input.stopDefined)) {
      process += 6;
      blockers.push("No stop or invalidation level is defined. / 未定义止损或失效位置。");
      actions.push("Define invalidation before entry. / 入场前先定义失效条件。");
    }
    if (!checked(input.exitPlanDefined)) {
      process += 5;
      blockers.push("No written exit plan is defined. / 未定义书面退出计划。");
    }
    if (!checked(input.liquidityChecked)) {
      process += 4;
      warnings.push("Liquidity and slippage were not independently checked. / 尚未独立检查流动性和滑点。");
    }
    if (!checked(input.dataFresh)) {
      process += 3;
      warnings.push("Inputs are not confirmed as current. / 尚未确认输入数据为最新。");
    }
    if (checked(input.eventRisk)) {
      process += 3;
      warnings.push("A known event risk is inside the holding window. / 持仓时间内存在已知事件风险。");
    }
    if (correlatedPositions >= 3) {
      process += 2;
      warnings.push("Three or more correlated positions are open. / 当前存在至少三个相关仓位。");
    }
    if (checked(input.revengeTrade)) {
      process += 5;
      blockers.push("The setup is marked as a revenge trade. / 当前交易被标记为报复性交易。");
      actions.push("Pause and do not use this setup as an immediate recovery trade. / 暂停交易，不要用该仓位立即追回损失。");
    }
    if (checked(input.fomo)) {
      process += 4;
      warnings.push("The setup is marked as FOMO-driven. / 当前交易被标记为 FOMO 驱动。");
    }
    process = Math.min(25, process);

    const score = account + market + process;
    let status = "STANDARD_REVIEW";
    if (blockers.length) status = "DO_NOT_PROCEED";
    else if (score >= 45) status = "HIGH_RISK";
    else if (score >= 25) status = "ELEVATED_REVIEW";

    if (!actions.length) actions.push("Keep the written risk limits and rerun the review if conditions change. / 保持书面风险限制，条件变化后重新检查。");

    return {
      status,
      score,
      categories: { account, market, process },
      blockers,
      warnings,
      actions: [...new Set(actions)],
      inputs: {
        exposurePercent,
        leverage,
        riskPercent,
        stopDistancePercent,
        slippagePercent,
        volatilityPercent,
        liquidityCoverage,
        fundingPercent,
        correlatedPositions
      }
    };
  }

  return { review };
});
