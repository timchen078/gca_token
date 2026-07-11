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

  return { tools, workflows, getWorkflow };
});
