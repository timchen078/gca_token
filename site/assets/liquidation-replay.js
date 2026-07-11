(function attachLiquidationReplay(root, factory) {
  const engine = factory();
  root.GcaLiquidationReplay = engine;
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
})(typeof globalThis !== "undefined" ? globalThis : this, function createLiquidationReplay() {
  "use strict";

  const finite = (value) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : NaN;
  };

  const checked = (value) => value === true;

  function replay(input) {
    const direction = input.direction === "short" ? "short" : "long";
    const accountEquity = finite(input.accountEquity);
    const entry = finite(input.entry);
    const exit = finite(input.exit);
    const quantity = finite(input.quantity);
    const leverage = finite(input.leverage);
    const fees = Math.max(0, finite(input.fees) || 0);
    const funding = Math.max(0, finite(input.funding) || 0);
    const plannedStop = finite(input.plannedStop);
    const valid = [accountEquity, entry, exit, quantity, leverage].every(Number.isFinite) &&
      accountEquity > 0 && entry > 0 && exit > 0 && quantity > 0 && leverage >= 1;

    if (!valid) return null;

    const signedMove = direction === "long" ? exit - entry : entry - exit;
    const grossPnl = signedMove * quantity;
    const totalCosts = fees + funding;
    const netPnl = grossPnl - totalCosts;
    const netLoss = Math.max(0, -netPnl);
    const accountImpactPercent = (netPnl / accountEquity) * 100;
    const adverseMovePercent = Math.max(0, (-signedMove / entry) * 100);
    const positionNotional = entry * quantity;
    const effectiveLeverage = positionNotional / accountEquity;
    const initialMargin = positionNotional / leverage;
    const marginUtilizationPercent = (initialMargin / accountEquity) * 100;
    const simpleLeverageMovePercent = 100 / leverage;
    const plannedStopValid = Number.isFinite(plannedStop) && plannedStop > 0 &&
      (direction === "long" ? plannedStop < entry : plannedStop > entry);
    const plannedStopDistancePercent = plannedStopValid
      ? (Math.abs(entry - plannedStop) / entry) * 100
      : null;
    const plannedGrossLoss = plannedStopValid
      ? Math.abs(entry - plannedStop) * quantity
      : null;
    const lossMultiple = plannedGrossLoss && plannedGrossLoss > 0
      ? netLoss / plannedGrossLoss
      : null;
    const costSharePercent = netLoss > 0 ? (totalCosts / netLoss) * 100 : 0;

    const flags = [];
    const actions = [];
    let severity = 0;

    if (netPnl >= 0) {
      flags.push({ level: "info", message: "This replay is not a net-loss trade. Review execution and costs anyway. / 本次复盘不是净亏损交易，仍可检查执行与成本。" });
    }

    if (accountImpactPercent <= -5) {
      severity = Math.max(severity, 2);
      flags.push({ level: "critical", message: "Account loss is 5% or more. / 账户损失达到或超过 5%。" });
      actions.push("Pause new risk and define a lower per-trade loss limit. / 暂停新增风险，并重新设定更低的单笔损失上限。");
    } else if (accountImpactPercent <= -2) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "Account loss is above 2%. / 账户损失超过 2%。" });
      actions.push("Reduce the next planned risk budget and position size. / 下调下一笔计划风险预算和仓位。");
    }

    if (effectiveLeverage > 10) {
      severity = Math.max(severity, 2);
      flags.push({ level: "critical", message: "Effective account exposure is above 10x. / 账户实际敞口超过 10 倍。" });
      actions.push("Set a hard account-exposure cap before the next trade. / 下一笔交易前设置账户敞口硬上限。");
    } else if (effectiveLeverage > 5) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "Effective account exposure is above 5x. / 账户实际敞口超过 5 倍。" });
    }

    if (marginUtilizationPercent > 100) {
      severity = Math.max(severity, 2);
      flags.push({ level: "critical", message: "Entered margin is greater than account equity. Check the inputs or cross-margin exposure. / 输入保证金大于账户权益，请检查参数或全仓敞口。" });
    } else if (marginUtilizationPercent > 50) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "More than half of account equity was committed as initial margin. / 初始保证金占账户权益超过一半。" });
    }

    if (!plannedStopValid) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "No valid planned stop was entered for the selected direction. / 未填写与方向一致的有效计划止损。" });
      actions.push("Write the invalidation price before calculating the next position. / 下一笔仓位计算前先写明失效价格。");
    } else if (lossMultiple !== null && lossMultiple > 1.25) {
      severity = Math.max(severity, lossMultiple > 2 ? 2 : 1);
      flags.push({
        level: lossMultiple > 2 ? "critical" : "warning",
        message: "Actual net loss materially exceeded the price risk at the planned stop. / 实际净损失明显超过计划止损对应的价格风险。"
      });
      actions.push("Compare the actual exit with the planned stop and document the execution gap. / 对比实际退出价与计划止损，记录执行偏差。");
    }

    if (costSharePercent > 20 && netLoss > 0) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "Fees and funding are more than 20% of the net loss. / 手续费与资金费超过净损失的 20%。" });
      actions.push("Review order type, holding duration, turnover, and venue costs. / 检查订单类型、持仓时间、换手频率和交易场所成本。");
    }

    if (!checked(input.positionPlanned)) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "Position size was not confirmed before entry. / 入场前没有确认仓位计算。" });
      actions.push("Use the GCA Position Size Calculator before the next entry. / 下一次入场前使用 GCA 仓位计算器。");
    }
    if (!checked(input.stopRespected)) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "The planned stop was not respected. / 没有遵守计划止损。" });
    }
    if (checked(input.addedToLosing)) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "Size was added while the position was losing. / 浮亏期间继续加仓。" });
      actions.push("Define whether adding is prohibited or pre-planned with a fixed total risk cap. / 明确禁止浮亏加仓，或仅允许在固定总风险内预先规划加仓。");
    }
    if (!checked(input.exitRuleFollowed)) {
      severity = Math.max(severity, 1);
      flags.push({ level: "warning", message: "The written exit rule was not followed. / 没有执行书面退出规则。" });
    }
    if (!checked(input.journalComplete)) {
      flags.push({ level: "info", message: "Add the trade thesis, screenshots, and timestamps to the journal. / 在交易日志中补充逻辑、截图和时间记录。" });
      actions.push("Complete the journal before taking another similar setup. / 再做同类交易前完成本次日志。");
    }

    if (!actions.length) actions.push("Keep the same risk cap and record what worked. / 保持当前风险上限，并记录有效做法。");

    return {
      direction,
      accountEquity,
      entry,
      exit,
      quantity,
      leverage,
      grossPnl,
      totalCosts,
      netPnl,
      netLoss,
      accountImpactPercent,
      adverseMovePercent,
      positionNotional,
      effectiveLeverage,
      initialMargin,
      marginUtilizationPercent,
      simpleLeverageMovePercent,
      plannedStopValid,
      plannedStopDistancePercent,
      plannedGrossLoss,
      lossMultiple,
      costSharePercent,
      status: severity === 2 ? "CRITICAL_REVIEW" : severity === 1 ? "PROCESS_REVIEW" : "CONTROLLED",
      flags,
      actions: [...new Set(actions)]
    };
  }

  return { replay };
});
