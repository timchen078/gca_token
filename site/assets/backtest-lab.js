(function attachBacktestLab(root, factory) {
  const engine = factory();
  root.GcaBacktestLab = engine;
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
})(typeof globalThis !== "undefined" ? globalThis : this, function createBacktestLab() {
  "use strict";

  function parseReturns(value) {
    const source = Array.isArray(value)
      ? value
      : String(value || "")
          .replace(/%/g, "")
          .split(/[\s,;]+/)
          .filter(Boolean);
    if (!source.length || source.length > 5000) return null;
    const values = source.map(Number);
    return values.every(Number.isFinite) ? values : null;
  }

  function analyzeSequence(input) {
    const startingEquity = Number(input.startingEquity);
    const costPercent = Number(input.costPercent || 0);
    const rawReturns = parseReturns(input.tradeReturns);
    if (!Number.isFinite(startingEquity) || startingEquity <= 0 ||
        !Number.isFinite(costPercent) || costPercent < 0 || costPercent > 10 ||
        !rawReturns) return null;

    const netReturns = rawReturns.map((value) => value - costPercent);
    if (netReturns.some((value) => value <= -100 || value > 1000)) return null;

    let equity = startingEquity;
    let peak = startingEquity;
    let maxDrawdownPercent = 0;
    let maxDrawdownAmount = 0;
    let currentWins = 0;
    let currentLosses = 0;
    let maxConsecutiveWins = 0;
    let maxConsecutiveLosses = 0;
    let totalWins = 0;
    let totalLosses = 0;
    let wins = 0;
    let losses = 0;
    let flat = 0;
    const curve = [{ trade: 0, rawReturn: 0, netReturn: 0, equity, drawdownPercent: 0 }];

    netReturns.forEach((netReturn, index) => {
      const rawReturn = rawReturns[index];
      equity *= 1 + (netReturn / 100);
      peak = Math.max(peak, equity);
      const drawdownAmount = peak - equity;
      const drawdownPercent = peak > 0 ? (drawdownAmount / peak) * 100 : 0;
      maxDrawdownPercent = Math.max(maxDrawdownPercent, drawdownPercent);
      maxDrawdownAmount = Math.max(maxDrawdownAmount, drawdownAmount);

      if (netReturn > 0) {
        wins += 1;
        totalWins += netReturn;
        currentWins += 1;
        currentLosses = 0;
        maxConsecutiveWins = Math.max(maxConsecutiveWins, currentWins);
      } else if (netReturn < 0) {
        losses += 1;
        totalLosses += Math.abs(netReturn);
        currentLosses += 1;
        currentWins = 0;
        maxConsecutiveLosses = Math.max(maxConsecutiveLosses, currentLosses);
      } else {
        flat += 1;
        currentWins = 0;
        currentLosses = 0;
      }

      curve.push({ trade: index + 1, rawReturn, netReturn, equity, drawdownPercent });
    });

    const tradeCount = netReturns.length;
    const averageReturnPercent = netReturns.reduce((sum, value) => sum + value, 0) / tradeCount;
    const averageWinPercent = wins ? totalWins / wins : 0;
    const averageLossPercent = losses ? totalLosses / losses : 0;
    const winRatePercent = (wins / tradeCount) * 100;
    const profitFactor = totalLosses > 0 ? totalWins / totalLosses : null;
    const compoundedReturnPercent = ((equity / startingEquity) - 1) * 100;
    const netProfit = equity - startingEquity;
    const recoveryFactor = maxDrawdownAmount > 0 ? netProfit / maxDrawdownAmount : null;
    const bestReturnPercent = Math.max(...netReturns);
    const worstReturnPercent = Math.min(...netReturns);
    const totalCostDragPercent = costPercent * tradeCount;
    const warnings = [];

    if (tradeCount < 30) warnings.push("Sample has fewer than 30 trades. / 样本少于 30 笔交易。");
    if (tradeCount < 100) warnings.push("Treat the result as an early sample, not robust validation. / 当前仍是早期样本，不能视为稳健验证。");
    if (profitFactor === null) warnings.push("No net losing trade exists in the sample; check selection bias. / 样本没有净亏损交易，请检查选择偏差。");
    if (maxDrawdownPercent > 20) warnings.push("Maximum drawdown is above 20%. / 最大回撤超过 20%。");
    if (maxConsecutiveLosses >= 5) warnings.push("The sequence contains at least five consecutive losses. / 样本出现至少 5 笔连续亏损。");
    if (costPercent > 0 && averageReturnPercent <= costPercent) warnings.push("Per-trade cost is large relative to average net return. / 单笔成本相对平均净收益较高。");

    let status = "RESEARCH_READY";
    if (averageReturnPercent <= 0 || compoundedReturnPercent <= 0 || (profitFactor !== null && profitFactor < 1)) {
      status = "NEGATIVE_EXPECTANCY";
    } else if (tradeCount < 30) {
      status = "INSUFFICIENT_SAMPLE";
    } else if (maxDrawdownPercent > 25 || maxConsecutiveLosses >= 7 || (profitFactor !== null && profitFactor < 1.2)) {
      status = "PROCESS_REVIEW";
    }

    return {
      status,
      startingEquity,
      finalEquity: equity,
      tradeCount,
      wins,
      losses,
      flat,
      winRatePercent,
      averageReturnPercent,
      averageWinPercent,
      averageLossPercent,
      profitFactor,
      compoundedReturnPercent,
      netProfit,
      maxDrawdownPercent,
      maxDrawdownAmount,
      maxConsecutiveWins,
      maxConsecutiveLosses,
      bestReturnPercent,
      worstReturnPercent,
      recoveryFactor,
      costPercent,
      totalCostDragPercent,
      curve,
      warnings
    };
  }

  return { parseReturns, analyzeSequence };
});
