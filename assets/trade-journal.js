(function attachTradeJournal(root, factory) {
  const journal = factory();
  root.GcaTradeJournal = journal;
  if (typeof module !== "undefined" && module.exports) module.exports = journal;
})(typeof globalThis !== "undefined" ? globalThis : this, function createTradeJournal() {
  "use strict";

  const STORAGE_KEY = "gca_trade_journal_v1";
  const SCHEMA = "gca-trade-journal-v1";
  const MAX_TRADES = 500;

  function cleanText(value, maxLength) {
    return String(value || "").trim().replace(/\s+/g, " ").slice(0, maxLength);
  }

  function validDate(value) {
    const date = String(value || "");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
    const parsed = new Date(`${date}T00:00:00Z`);
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date;
  }

  function normalizeTrade(input) {
    if (!input || typeof input !== "object") return null;
    const date = String(input.date || "");
    const market = cleanText(input.market, 40).toUpperCase();
    const direction = input.direction === "short" ? "short" : input.direction === "long" ? "long" : "";
    const returnPercent = Number(input.returnPercent);
    if (!validDate(date) || !market || !direction || !Number.isFinite(returnPercent) ||
        returnPercent <= -100 || returnPercent > 1000) return null;
    const id = cleanText(input.id, 80) || `${date}-${market}-${returnPercent}`;
    const createdAt = Number.isFinite(Date.parse(input.createdAt))
      ? new Date(input.createdAt).toISOString()
      : new Date(`${date}T00:00:00Z`).toISOString();
    return {
      id,
      date,
      market,
      direction,
      returnPercent,
      setup: cleanText(input.setup, 80),
      notes: cleanText(input.notes, 500),
      createdAt
    };
  }

  function orderTrades(values) {
    return values
      .map(normalizeTrade)
      .filter(Boolean)
      .sort((a, b) => a.date.localeCompare(b.date) || a.createdAt.localeCompare(b.createdAt) || a.id.localeCompare(b.id))
      .slice(-MAX_TRADES);
  }

  function summarizeTrades(values) {
    const trades = orderTrades(Array.isArray(values) ? values : []);
    const returns = trades.map((trade) => trade.returnPercent);
    const wins = returns.filter((value) => value > 0).length;
    const losses = returns.filter((value) => value < 0).length;
    let currentLosses = 0;
    let maxConsecutiveLosses = 0;
    returns.forEach((value) => {
      currentLosses = value < 0 ? currentLosses + 1 : 0;
      maxConsecutiveLosses = Math.max(maxConsecutiveLosses, currentLosses);
    });
    const total = returns.reduce((sum, value) => sum + value, 0);
    return {
      trades,
      returns,
      count: trades.length,
      wins,
      losses,
      flats: trades.length - wins - losses,
      winRatePercent: trades.length ? (wins / trades.length) * 100 : 0,
      averageReturnPercent: trades.length ? total / trades.length : 0,
      bestReturnPercent: trades.length ? Math.max(...returns) : 0,
      worstReturnPercent: trades.length ? Math.min(...returns) : 0,
      maxConsecutiveLosses
    };
  }

  function buildBackup(values, exportedAt) {
    return {
      schema: SCHEMA,
      exportedAt: Number.isFinite(Date.parse(exportedAt)) ? new Date(exportedAt).toISOString() : new Date().toISOString(),
      trades: orderTrades(Array.isArray(values) ? values : [])
    };
  }

  function parseBackup(value) {
    let payload;
    try {
      payload = typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
    if (!payload || payload.schema !== SCHEMA || !Array.isArray(payload.trades) || payload.trades.length > MAX_TRADES) return null;
    const trades = orderTrades(payload.trades);
    if (trades.length !== payload.trades.length) return null;
    return { schema: SCHEMA, exportedAt: payload.exportedAt || null, trades };
  }

  function toCsv(values) {
    const quote = (value) => `"${String(value).replace(/"/g, '""')}"`;
    const header = ["date", "market", "direction", "return_percent", "setup", "notes"];
    const rows = orderTrades(Array.isArray(values) ? values : []).map((trade) => [
      trade.date, trade.market, trade.direction, trade.returnPercent, trade.setup, trade.notes
    ].map(quote).join(","));
    return [header.join(","), ...rows].join("\n");
  }

  return { STORAGE_KEY, SCHEMA, MAX_TRADES, normalizeTrade, orderTrades, summarizeTrades, buildBackup, parseBackup, toCsv };
});
