(function attachEntryReady(root, factory) {
  const engine = factory();
  root.GcaEntryReady = engine;
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
})(typeof globalThis !== "undefined" ? globalThis : this, function createEntryReady() {
  "use strict";

  const bool = (value) => value === true;
  const finite = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : NaN;
  };

  function evaluate(input) {
    const direction = input.direction === "short" ? "short" : "long";
    const entry = finite(input.entry);
    const stop = finite(input.stop);
    const target = finite(input.target);
    const riskPercent = finite(input.riskPercent);
    const leverage = finite(input.leverage);
    const thesis = String(input.thesis || "").trim();
    const timeframe = String(input.timeframe || "").trim();
    const orderType = String(input.orderType || "").trim();
    const validNumbers = [entry, stop, target, riskPercent, leverage].every(Number.isFinite) &&
      entry > 0 && stop > 0 && target > 0 && riskPercent > 0 && leverage >= 1;
    const priceStructureValid = validNumbers && (direction === "long"
      ? stop < entry && target > entry
      : stop > entry && target < entry);

    const blockers = [];
    const warnings = [];
    const categories = {
      structure: 0,
      risk: 0,
      execution: 0,
      discipline: 0
    };

    if (!validNumbers) blockers.push("Enter valid positive entry, stop, target, risk, and leverage values. / 请输入有效的价格、风险和杠杆参数。");
    if (validNumbers && !priceStructureValid) blockers.push("Stop or target is on the wrong side of entry for the selected direction. / 止损或目标价与所选方向不一致。");
    if (priceStructureValid) categories.structure += 15;
    if (thesis.length >= 20) categories.structure += 10;
    else warnings.push("Write a setup thesis of at least 20 characters. / 请写出至少 20 个字符的交易逻辑。");

    if (riskPercent > 3) blockers.push("Risk per trade is above 3%. / 单笔风险超过 3%。");
    else if (riskPercent <= 2) categories.risk += 10;
    else warnings.push("Risk per trade is above 2%. / 单笔风险超过 2%。");
    if (leverage > 20) blockers.push("Leverage is above 20x. / 杠杆超过 20 倍。");
    else if (leverage <= 10) categories.risk += 5;
    else warnings.push("Leverage is above 10x. / 杠杆超过 10 倍。");
    if (bool(input.positionSized)) categories.risk += 5;
    else blockers.push("Calculate position size before entry. / 入场前必须完成仓位计算。");
    if (bool(input.maxLossAccepted)) categories.risk += 5;
    else blockers.push("Confirm the planned maximum loss is acceptable. / 请确认能够接受计划最大损失。");
    if (bool(input.invalidationDefined)) categories.risk += 5;
    else blockers.push("Define the invalidation condition. / 必须定义交易失效条件。");

    if (bool(input.liquidityChecked)) categories.execution += 7;
    else blockers.push("Check market liquidity and expected slippage. / 必须检查流动性和预期滑点。");
    if (bool(input.costsIncluded)) categories.execution += 6;
    else warnings.push("Include fees and slippage in the plan. / 请把手续费和滑点计入计划。");
    if (orderType) categories.execution += 4;
    else warnings.push("Select an order type. / 请选择订单类型。");
    if (bool(input.volatilityReviewed)) categories.execution += 4;
    else warnings.push("Review event and volatility risk. / 请检查事件和波动风险。");
    if (timeframe) categories.execution += 4;
    else warnings.push("Select a timeframe. / 请选择交易周期。");

    if (bool(input.noRevengeTrade)) categories.discipline += 10;
    else blockers.push("Pause if this setup is driven by revenge trading. / 如果属于报复性交易，请暂停。");
    if (bool(input.noFomo)) categories.discipline += 5;
    else warnings.push("Confirm the entry is not driven by FOMO. / 请确认入场不是由追涨杀跌情绪驱动。");
    if (bool(input.exitPlanDefined)) categories.discipline += 5;
    else warnings.push("Define the exit and cancellation plan. / 请定义退出和取消计划。");

    const score = Object.values(categories).reduce((total, value) => total + value, 0);
    const status = blockers.length > 0 || score < 70
      ? "NOT_READY"
      : score >= 85 && warnings.length === 0
        ? "ENTRY_READY"
        : "REVIEW";

    return Object.freeze({
      status,
      score,
      categories: Object.freeze({ ...categories }),
      blockers: Object.freeze(blockers),
      warnings: Object.freeze(warnings),
      priceStructureValid,
      direction,
      entry,
      stop,
      target,
      riskPercent,
      leverage,
      thesis,
      timeframe,
      orderType
    });
  }

  return Object.freeze({ evaluate });
});

