(function attachRiskTraining(root, factory) {
  const engine = factory();
  root.GcaRiskTraining = engine;
  if (typeof module !== "undefined" && module.exports) module.exports = engine;
})(typeof globalThis !== "undefined" ? globalThis : this, function createRiskTraining() {
  "use strict";

  const DRAFT_KEY = "gca_risk_training_draft_v1";
  const HISTORY_KEY = "gca_risk_training_history_v1";
  const HISTORY_LIMIT = 20;
  const ATTEMPT_ID_RE = /^gca_training_[a-z0-9-]{8,64}$/;
  const RESULT_STATUSES = Object.freeze(["REVIEW_REQUIRED", "FOUNDATION_READY"]);

  const questions = [
    {
      id: "position-size",
      category: "Risk budget / 风险预算",
      prompt: "Before opening a trade, what should determine position size?",
      promptZh: "开仓前，应该用什么决定仓位大小？",
      options: [
        { id: "conviction", label: "How strongly I believe the idea", labelZh: "我对交易想法有多自信" },
        { id: "risk-budget", label: "Account risk budget and distance to invalidation", labelZh: "账户风险预算与失效点距离" },
        { id: "available-leverage", label: "The maximum leverage the venue offers", labelZh: "交易场所提供的最大杠杆" }
      ],
      correctOptionId: "risk-budget",
      explanation: "Define maximum acceptable loss first, then calculate size from the entry-to-stop distance and expected costs.",
      explanationZh: "先定义可接受的最大损失，再根据入场价到止损价的距离和预计成本计算仓位。",
      reviewUrl: "risk-calculator.html"
    },
    {
      id: "invalidation",
      category: "Trade plan / 交易计划",
      prompt: "Price approaches the planned stop. Which response follows the original risk plan?",
      promptZh: "价格接近计划止损位，哪种处理符合原风险计划？",
      options: [
        { id: "move-stop", label: "Move the stop farther away to avoid realizing a loss", labelZh: "把止损移远，避免确认亏损" },
        { id: "follow-invalidation", label: "Follow the predefined invalidation and review afterward", labelZh: "执行预设失效条件，事后复盘" },
        { id: "double-size", label: "Double the position to improve the average entry", labelZh: "加倍仓位以改善平均入场价" }
      ],
      correctOptionId: "follow-invalidation",
      explanation: "An invalidation rule is useful only when it is defined before entry and followed without widening risk during the trade.",
      explanationZh: "失效规则只有在入场前定义，并且交易中不扩大风险时才有意义。",
      reviewUrl: "entry-ready.html"
    },
    {
      id: "leverage-distance",
      category: "Risk budget / 风险预算",
      prompt: "Estimated liquidation is too close to the planned invalidation. What is the safer adjustment?",
      promptZh: "预计清算价离计划失效点太近，更稳妥的调整是什么？",
      options: [
        { id: "increase-leverage", label: "Increase leverage so less margin is used", labelZh: "提高杠杆以减少保证金占用" },
        { id: "reduce-risk", label: "Reduce size or leverage, or skip the setup", labelZh: "降低仓位或杠杆，必要时放弃交易" },
        { id: "remove-stop", label: "Remove the stop because liquidation already limits the loss", labelZh: "取消止损，因为清算会限制损失" }
      ],
      correctOptionId: "reduce-risk",
      explanation: "Liquidation should not replace a stop. Reduce exposure until the planned invalidation can operate before forced liquidation.",
      explanationZh: "清算不能代替止损。应降低敞口，使计划失效规则能在强制清算前生效。",
      reviewUrl: "liquidation-replay.html"
    },
    {
      id: "loss-streak",
      category: "Discipline / 交易纪律",
      prompt: "After several consecutive losses, what is the risk-first response?",
      promptZh: "连续多次亏损后，什么是风险优先的处理方式？",
      options: [
        { id: "recover-fast", label: "Increase size to recover losses quickly", labelZh: "加大仓位快速追回亏损" },
        { id: "pause-review", label: "Pause new entries and review the plan, journal, and risk limits", labelZh: "暂停新开仓，复核计划、日志和风险限制" },
        { id: "switch-randomly", label: "Immediately switch to an untested strategy", labelZh: "立即切换到未经测试的策略" }
      ],
      correctOptionId: "pause-review",
      explanation: "A loss streak is a reason to enter a safe state and inspect process quality, not to increase risk through revenge trading.",
      explanationZh: "连亏应触发安全状态并检查执行质量，而不是通过报复性交易增加风险。",
      reviewUrl: "trade-journal.html"
    },
    {
      id: "execution-costs",
      category: "Execution / 执行条件",
      prompt: "What belongs in the plan before an order is considered executable?",
      promptZh: "判断订单是否可执行前，计划中必须包含什么？",
      options: [
        { id: "chart-only", label: "Only the chart pattern", labelZh: "只看图表形态" },
        { id: "cost-liquidity", label: "Fees, slippage, liquidity, volatility, and order type", labelZh: "手续费、滑点、流动性、波动率和订单类型" },
        { id: "social-volume", label: "Only social-media activity", labelZh: "只看社交媒体热度" }
      ],
      correctOptionId: "cost-liquidity",
      explanation: "A theoretical setup can fail in execution when costs, liquidity, volatility, or order behavior are ignored.",
      explanationZh: "忽略成本、流动性、波动和订单行为时，理论上的交易设置可能在执行中失效。",
      reviewUrl: "risk-warning.html"
    },
    {
      id: "journal-review",
      category: "Review / 复盘",
      prompt: "Which journal record is most useful after a completed trade?",
      promptZh: "一笔交易结束后，哪种日志记录最有复盘价值？",
      options: [
        { id: "pnl-only", label: "Profit or loss only", labelZh: "只记录盈亏" },
        { id: "plan-execution", label: "Plan, actual execution, costs, outcome, and process deviations", labelZh: "计划、实际执行、成本、结果和流程偏差" },
        { id: "delete-losses", label: "Keep winners and delete losing trades", labelZh: "只保留盈利交易并删除亏损交易" }
      ],
      correctOptionId: "plan-execution",
      explanation: "A useful journal separates market outcome from process quality and preserves both wins and losses for review.",
      explanationZh: "有效日志应区分市场结果和执行质量，并保留盈利与亏损交易供复盘。",
      reviewUrl: "trade-journal.html"
    },
    {
      id: "api-security",
      category: "Security / 安全",
      prompt: "Which rule belongs in any future exchange API connection?",
      promptZh: "未来如连接交易所 API，哪条规则必须遵守？",
      options: [
        { id: "withdrawal-enabled", label: "Enable withdrawals for faster settlement", labelZh: "开启提现权限以便快速结算" },
        { id: "share-secret", label: "Paste the API secret into public support messages", labelZh: "把 API Secret 粘贴到公开客服消息" },
        { id: "no-withdrawal", label: "No withdrawal permission; never submit secrets to a public page", labelZh: "禁止提现权限，绝不向公开页面提交密钥" }
      ],
      correctOptionId: "no-withdrawal",
      explanation: "A non-custodial workflow must not request withdrawal permission, private keys, seed phrases, or secrets through public forms.",
      explanationZh: "非托管流程不得索取提现权限、私钥、助记词，也不得通过公开表单收集密钥。",
      reviewUrl: "security.html"
    },
    {
      id: "simulation-first",
      category: "Release safety / 上线安全",
      prompt: "What must happen before any future automated order flow reaches live markets?",
      promptZh: "未来任何自动下单流程进入真实市场前，必须先做什么？",
      options: [
        { id: "live-first", label: "Start live immediately with a large position", labelZh: "直接用大仓位上线" },
        { id: "skip-risk", label: "Skip risk checks when the signal looks strong", labelZh: "信号看起来很强时跳过风控" },
        { id: "test-first", label: "Pass risk checks and run simulation or testnet validation first", labelZh: "先通过风控，并完成模拟盘或测试网验证" }
      ],
      correctOptionId: "test-first",
      explanation: "Future execution must be gated by risk checks and validated in simulation or testnet before any controlled live release.",
      explanationZh: "未来执行必须经过风控，并在模拟盘或测试网验证后，才能进入受控真实环境。",
      reviewUrl: "release-gates.html"
    }
  ];

  function normalizeAnswers(input) {
    const value = input && typeof input === "object" ? input : {};
    return Object.fromEntries(questions.map((question) => [question.id, String(value[question.id] || "")]));
  }

  function parseJson(value) {
    try {
      return typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
  }

  function normalizedIso(value) {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? new Date(parsed).toISOString() : null;
  }

  function validAnswerMap(input) {
    const normalized = normalizeAnswers(input);
    return Object.fromEntries(questions.flatMap((question) => {
      const selected = normalized[question.id];
      return question.options.some((option) => option.id === selected) ? [[question.id, selected]] : [];
    }));
  }

  function createTrainingDraft(input, savedAt) {
    const answers = validAnswerMap(input);
    const timestamp = normalizedIso(savedAt);
    if (!timestamp || Object.keys(answers).length === 0) return null;
    return Object.freeze({
      version: 1,
      savedAt: timestamp,
      answers: Object.freeze(answers)
    });
  }

  function parseTrainingDraft(value) {
    const draft = parseJson(value);
    if (!draft || draft.version !== 1 || !draft.answers || typeof draft.answers !== "object") return null;
    return createTrainingDraft(draft.answers, draft.savedAt);
  }

  function evaluateAnswers(input) {
    const answers = normalizeAnswers(input);
    const questionResults = questions.map((question) => {
      const selectedOptionId = answers[question.id];
      const answered = question.options.some((option) => option.id === selectedOptionId);
      return Object.freeze({
        id: question.id,
        category: question.category,
        prompt: question.prompt,
        promptZh: question.promptZh,
        selectedOptionId,
        answered,
        correct: answered && selectedOptionId === question.correctOptionId,
        explanation: question.explanation,
        explanationZh: question.explanationZh,
        reviewUrl: question.reviewUrl
      });
    });
    const answeredCount = questionResults.filter((item) => item.answered).length;
    const correctCount = questionResults.filter((item) => item.correct).length;
    const percent = Math.round((correctCount / questions.length) * 100);
    const status = answeredCount < questions.length
      ? "NOT_COMPLETE"
      : percent >= 75
        ? "FOUNDATION_READY"
        : "REVIEW_REQUIRED";
    const categories = [...new Set(questions.map((question) => question.category))].map((category) => {
      const results = questionResults.filter((item) => item.category === category);
      return Object.freeze({
        category,
        total: results.length,
        answered: results.filter((item) => item.answered).length,
        correct: results.filter((item) => item.correct).length
      });
    });
    return Object.freeze({
      status,
      total: questions.length,
      answeredCount,
      correctCount,
      percent,
      questionResults: Object.freeze(questionResults),
      categories: Object.freeze(categories)
    });
  }

  function buildReviewPlan(result) {
    if (!result || !Array.isArray(result.questionResults)) return Object.freeze([]);
    const items = [];
    result.questionResults.forEach((item) => {
      if (item.correct) return;
      items.push(Object.freeze({
        id: item.id,
        category: item.category,
        prompt: item.prompt,
        promptZh: item.promptZh,
        explanation: item.explanation,
        explanationZh: item.explanationZh,
        reviewUrl: item.reviewUrl,
        reason: item.answered ? "incorrect" : "unanswered"
      }));
    });
    return Object.freeze(items);
  }

  function sanitizeAttemptReceipt(value) {
    if (!value || typeof value !== "object" || value.version !== 1) return null;
    const attemptId = String(value.attemptId || "").trim().toLowerCase();
    const completedAt = normalizedIso(value.completedAt);
    const status = String(value.status || "");
    const total = Number(value.total);
    const answeredCount = Number(value.answeredCount);
    const correctCount = Number(value.correctCount);
    const percent = Number(value.percent);
    if (!ATTEMPT_ID_RE.test(attemptId) || !completedAt || !RESULT_STATUSES.includes(status)) return null;
    if (!Number.isInteger(total) || total !== questions.length || answeredCount !== total) return null;
    if (!Number.isInteger(correctCount) || correctCount < 0 || correctCount > total) return null;
    if (!Number.isInteger(percent) || percent !== Math.round((correctCount / total) * 100)) return null;
    if ((status === "FOUNDATION_READY") !== (percent >= 75)) return null;
    const knownIds = new Set(questions.map((question) => question.id));
    const missedQuestionIds = [...new Set(Array.isArray(value.missedQuestionIds) ? value.missedQuestionIds.map(String) : [])]
      .filter((id) => knownIds.has(id));
    if (missedQuestionIds.length !== total - correctCount) return null;
    return Object.freeze({
      version: 1,
      attemptId,
      completedAt,
      status,
      total,
      answeredCount,
      correctCount,
      percent,
      missedQuestionIds: Object.freeze(missedQuestionIds)
    });
  }

  function normalizeAttemptId(value, completedAt) {
    const requested = String(value || "").trim().toLowerCase();
    if (ATTEMPT_ID_RE.test(requested)) return requested;
    return `gca_training_${Date.parse(completedAt).toString(36)}-local`;
  }

  function createAttemptReceipt(result, completedAt, attemptId) {
    const timestamp = normalizedIso(completedAt);
    if (!timestamp || !result || result.answeredCount !== questions.length || !Array.isArray(result.questionResults)) return null;
    return sanitizeAttemptReceipt({
      version: 1,
      attemptId: normalizeAttemptId(attemptId, timestamp),
      completedAt: timestamp,
      status: result.status,
      total: result.total,
      answeredCount: result.answeredCount,
      correctCount: result.correctCount,
      percent: result.percent,
      missedQuestionIds: result.questionResults.filter((item) => !item.correct).map((item) => item.id)
    });
  }

  function parseAttemptHistory(value) {
    const rows = parseJson(value);
    if (!Array.isArray(rows)) return Object.freeze([]);
    const seen = new Set();
    const history = rows
      .map(sanitizeAttemptReceipt)
      .filter((receipt) => {
        if (!receipt || seen.has(receipt.attemptId)) return false;
        seen.add(receipt.attemptId);
        return true;
      })
      .sort((left, right) => Date.parse(right.completedAt) - Date.parse(left.completedAt))
      .slice(0, HISTORY_LIMIT);
    return Object.freeze(history);
  }

  function upsertAttemptHistory(value, receipt) {
    const current = parseAttemptHistory(value);
    const sanitized = sanitizeAttemptReceipt(receipt);
    if (!sanitized) return current;
    return parseAttemptHistory([sanitized, ...current.filter((item) => item.attemptId !== sanitized.attemptId)]);
  }

  function summarizeAttemptHistory(value) {
    const history = parseAttemptHistory(value);
    const latest = history[0] || null;
    return Object.freeze({
      count: history.length,
      latestStatus: latest ? latest.status : "NO_ATTEMPTS",
      latestPercent: latest ? latest.percent : 0,
      latestCompletedAt: latest ? latest.completedAt : null,
      bestPercent: history.reduce((best, item) => Math.max(best, item.percent), 0),
      foundationReadyCount: history.filter((item) => item.status === "FOUNDATION_READY").length,
      latestMissedQuestionIds: Object.freeze(latest ? [...latest.missedQuestionIds] : [])
    });
  }

  return Object.freeze({
    DRAFT_KEY,
    HISTORY_KEY,
    HISTORY_LIMIT,
    questions: Object.freeze(questions.map((question) => Object.freeze({
      ...question,
      options: Object.freeze(question.options.map((option) => Object.freeze({ ...option })))
    }))),
    evaluateAnswers,
    buildReviewPlan,
    createTrainingDraft,
    parseTrainingDraft,
    createAttemptReceipt,
    parseAttemptHistory,
    upsertAttemptHistory,
    summarizeAttemptHistory
  });
});
