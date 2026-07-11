(function attachRiskTools(root, factory) {
  const workspace = factory();
  root.GcaRiskTools = workspace;
  if (typeof module !== "undefined" && module.exports) module.exports = workspace;
})(typeof globalThis !== "undefined" ? globalThis : this, function createRiskTools() {
  "use strict";

  const tools = {
    "risk-calculator": {
      name: "Position Size Calculator",
      shortName: "Size",
      url: "risk-calculator.html",
      stage: "Before entry",
      purpose: "Turn equity, stop distance, costs, and risk budget into a planned position size."
    },
    "risk-warning": {
      name: "Risk Warning Review",
      shortName: "Warn",
      url: "risk-warning.html",
      stage: "Before entry",
      purpose: "Score exposure, leverage, liquidity, volatility, execution friction, and discipline."
    },
    "entry-ready": {
      name: "ENTRY_READY Review",
      shortName: "Gate",
      url: "entry-ready.html",
      stage: "Final pre-entry gate",
      purpose: "Check structure, invalidation, execution conditions, and readiness blockers."
    },
    "backtest-lab": {
      name: "Backtest Lab",
      shortName: "Test",
      url: "backtest-lab.html",
      stage: "Strategy research",
      purpose: "Analyze entered trade-return samples, costs, expectancy, drawdown, and streaks."
    },
    "liquidation-replay": {
      name: "Liquidation & Loss Replay",
      shortName: "Replay",
      url: "liquidation-replay.html",
      stage: "After exit",
      purpose: "Review account impact, effective exposure, margin use, stop deviation, and process errors."
    }
  };

  const workflows = {
    prepare: {
      name: "Prepare a Trade",
      description: "Size first, review risk second, then run the final readiness gate.",
      toolIds: ["risk-calculator", "risk-warning", "entry-ready"]
    },
    research: {
      name: "Research a Strategy",
      description: "Analyze the sample, stress the current risk conditions, then validate the setup process.",
      toolIds: ["backtest-lab", "risk-warning", "entry-ready"]
    },
    review: {
      name: "Review a Loss",
      description: "Replay the loss, correct position sizing, reassess risk, then rebuild the entry gate.",
      toolIds: ["liquidation-replay", "risk-calculator", "risk-warning", "entry-ready"]
    },
    all: {
      name: "All Risk Tools",
      description: "Open any public browser-only GCA tool directly.",
      toolIds: ["risk-calculator", "risk-warning", "entry-ready", "backtest-lab", "liquidation-replay"]
    }
  };

  function getWorkflow(mode) {
    const key = Object.prototype.hasOwnProperty.call(workflows, mode) ? mode : "prepare";
    const workflow = workflows[key];
    return {
      mode: key,
      name: workflow.name,
      description: workflow.description,
      tools: workflow.toolIds.map((id, index) => ({ id, order: index + 1, ...tools[id] }))
    };
  }

  function buildPlanLinks(input) {
    const plan = {
      direction: input.direction === "short" ? "short" : "long",
      equity: Number(input.equity),
      risk: Number(input.risk),
      entry: Number(input.entry),
      stop: Number(input.stop),
      target: Number(input.target),
      leverage: Number(input.leverage),
      exposure: Number(input.exposure),
      fees: Number(input.fees || 0),
      slippage: Number(input.slippage),
      volatility: Number(input.volatility),
      liquidity: Number(input.liquidity)
    };
    const numericValues = [plan.equity, plan.risk, plan.entry, plan.stop, plan.target,
      plan.leverage, plan.exposure, plan.fees, plan.slippage, plan.volatility, plan.liquidity];
    const valid = numericValues.every(Number.isFinite) &&
      plan.equity > 0 && plan.risk >= 0.1 && plan.risk <= 5 &&
      plan.entry > 0 && plan.stop > 0 && plan.target > 0 &&
      plan.leverage >= 1 && plan.leverage <= 100 && plan.exposure >= 0 &&
      plan.fees >= 0 && plan.fees <= 10 && plan.slippage >= 0 &&
      plan.slippage <= 10 && plan.volatility >= 0 && plan.liquidity >= 0;
    const structureValid = plan.direction === "long"
      ? plan.stop < plan.entry && plan.target > plan.entry
      : plan.stop > plan.entry && plan.target < plan.entry;
    if (!valid || !structureValid) return null;

    const stopDistance = (Math.abs(plan.entry - plan.stop) / plan.entry) * 100;
    const riskBudget = plan.equity * (plan.risk / 100);
    const riskPerUnit = Math.abs(plan.entry - plan.stop) +
      (plan.entry * ((plan.fees + plan.slippage) / 100));
    const quantity = riskBudget / riskPerUnit;
    const estimatedFees = plan.entry * quantity * (plan.fees / 100);
    const slippageAmount = plan.entry * (plan.slippage / 100);
    const scenarioExit = plan.direction === "long"
      ? Math.max(Number.EPSILON, plan.stop - slippageAmount)
      : plan.stop + slippageAmount;
    const fragment = (values) => new URLSearchParams(values).toString();
    return {
      plan: { ...plan, stopDistance, riskBudget, riskPerUnit, quantity, estimatedFees, scenarioExit },
      calculator: `risk-calculator.html#${fragment({ equity: plan.equity, entry: plan.entry, stop: plan.stop, target: plan.target, risk: plan.risk, leverage: plan.leverage, feeBps: plan.fees * 100, slippageBps: plan.slippage * 100 })}`,
      riskWarning: `risk-warning.html#${fragment({ exposure: plan.exposure, leverage: plan.leverage, risk: plan.risk, stopDistance, slippage: plan.slippage, volatility: plan.volatility, liquidity: plan.liquidity })}`,
      entryReady: `entry-ready.html#${fragment({ direction: plan.direction, entry: plan.entry, stop: plan.stop, target: plan.target, risk: plan.risk, leverage: plan.leverage })}`,
      backtest: `backtest-lab.html#${fragment({ source: "plan", startingEquity: plan.equity, risk: plan.risk })}`,
      replay: `liquidation-replay.html#${fragment({ source: "plan", direction: plan.direction, accountEquity: plan.equity, quantity, entry: plan.entry, exit: scenarioExit, plannedStop: plan.stop, leverage: plan.leverage, fees: estimatedFees, funding: 0 })}`
    };
  }

  return { tools, workflows, getWorkflow, buildPlanLinks };
});
