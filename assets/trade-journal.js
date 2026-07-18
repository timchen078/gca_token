(function attachTradeJournal(root, factory) {
  const journal = factory();
  root.GcaTradeJournal = journal;
  if (typeof module !== "undefined" && module.exports) module.exports = journal;
})(typeof globalThis !== "undefined" ? globalThis : this, function createTradeJournal() {
  "use strict";

  const STORAGE_KEY = "gca_trade_journal_v1";
  const SCHEMA = "gca-trade-journal-v1";
  const MAX_TRADES = 500;
  const MARKET_RE = /^[A-Z0-9][A-Z0-9._/-]{1,39}$/;
  const SENSITIVE_RE = /private\s*key|seed\s*phrase|mnemonic|api\s*secret|wallet\s*password|one[-\s]*time\s*code|withdrawal\s*permission|remote\s*control|\b(?:otp|2fa)\b|\u79c1\u94a5|\u52a9\u8bb0\u8bcd|\u5bc6\u7801|\u9a8c\u8bc1\u7801|\u63d0\u73b0\u6743\u9650|\u8fdc\u7a0b\u63a7\u5236/i;
  const TRADE_PLAN_HANDOFF_FIELDS = Object.freeze(["source", "symbol", "direction", "setup", "notes"]);

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
    const setup = cleanText(input.setup, 80);
    const notes = cleanText(input.notes, 500);
    if (!validDate(date) || !MARKET_RE.test(market) || !direction || !Number.isFinite(returnPercent) ||
        SENSITIVE_RE.test(`${setup} ${notes}`) ||
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
      setup,
      notes,
      createdAt
    };
  }

  function strictHandoffText(params, key, maxLength, minLength) {
    const values = params.getAll(key);
    if (values.length !== 1) return null;
    const value = String(values[0] || "").trim().replace(/\s+/g, " ");
    if (value.length < minLength || value.length > maxLength) return null;
    return value;
  }

  function parseTradePlanHandoff(value) {
    const raw = String(value || "").replace(/^#/, "");
    if (!raw || raw.length > 8000) return null;
    const params = new URLSearchParams(raw);
    const keys = [...params.keys()];
    if (keys.length !== TRADE_PLAN_HANDOFF_FIELDS.length || keys.some((key) => !TRADE_PLAN_HANDOFF_FIELDS.includes(key))) return null;
    const source = strictHandoffText(params, "source", 20, 1);
    const market = strictHandoffText(params, "symbol", 40, 2)?.toUpperCase() || "";
    const direction = strictHandoffText(params, "direction", 5, 4);
    const setup = strictHandoffText(params, "setup", 80, 3);
    const notes = strictHandoffText(params, "notes", 500, 20);
    if (source !== "trade-plan" || !MARKET_RE.test(market) || !["long", "short"].includes(direction) || !setup || !notes) return null;
    if (SENSITIVE_RE.test(`${setup} ${notes}`)) return null;
    return Object.freeze({ source, market, direction, setup, notes });
  }

  function orderTrades(values) {
    return values
      .map(normalizeTrade)
      .filter(Boolean)
      .sort((a, b) => a.date.localeCompare(b.date) || a.createdAt.localeCompare(b.createdAt) || a.id.localeCompare(b.id))
      .slice(-MAX_TRADES);
  }

  function filterTrades(values, filters) {
    const source = orderTrades(Array.isArray(values) ? values : []);
    const requested = filters && typeof filters === "object" ? filters : {};
    const market = cleanText(requested.market, 40).toUpperCase();
    const setup = cleanText(requested.setup, 80).toLowerCase();
    const direction = requested.direction === "long" || requested.direction === "short" ? requested.direction : "";
    const from = validDate(requested.from) ? String(requested.from) : "";
    const to = validDate(requested.to) ? String(requested.to) : "";
    return source.filter((trade) =>
      (!market || trade.market === market) &&
      (!setup || trade.setup.toLowerCase() === setup) &&
      (!direction || trade.direction === direction) &&
      (!from || trade.date >= from) &&
      (!to || trade.date <= to)
    );
  }

  function sampleQuality(count) {
    const size = Number.isFinite(Number(count)) ? Math.max(0, Math.floor(Number(count))) : 0;
    if (size >= 100) return { code: "LARGER_SAMPLE", label: "Larger sample", minimum: 100 };
    if (size >= 30) return { code: "EARLY_SAMPLE", label: "Early sample", minimum: 30 };
    return { code: "INSUFFICIENT_SAMPLE", label: "Insufficient sample", minimum: 0 };
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
      maxConsecutiveLosses,
      sampleQuality: sampleQuality(trades.length)
    };
  }

  function groupPerformance(values, dimension) {
    const key = ["market", "direction", "setup"].includes(dimension) ? dimension : "market";
    const groups = new Map();
    orderTrades(Array.isArray(values) ? values : []).forEach((trade) => {
      const label = key === "setup" ? (trade.setup || "UNTAGGED") : trade[key];
      if (!groups.has(label)) groups.set(label, []);
      groups.get(label).push(trade);
    });
    return [...groups.entries()].map(([label, trades]) => {
      const summary = summarizeTrades(trades);
      return {
        dimension: key,
        label,
        count: summary.count,
        wins: summary.wins,
        losses: summary.losses,
        winRatePercent: summary.winRatePercent,
        averageReturnPercent: summary.averageReturnPercent,
        totalReturnPercent: summary.returns.reduce((sum, value) => sum + value, 0),
        bestReturnPercent: summary.bestReturnPercent,
        worstReturnPercent: summary.worstReturnPercent,
        maxConsecutiveLosses: summary.maxConsecutiveLosses,
        sampleQuality: summary.sampleQuality
      };
    }).sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
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

  function parseCsvRows(value) {
    const source = String(value || "").replace(/^\uFEFF/, "");
    if (!source.trim()) return null;
    const rows = [];
    let row = [];
    let field = "";
    let state = "unquoted";
    const pushRow = () => {
      row.push(field);
      if (row.length > 1 || row[0].trim()) rows.push(row);
      row = [];
      field = "";
    };

    for (let index = 0; index < source.length; index += 1) {
      const character = source[index];
      if (state === "quoted") {
        if (character === '"') {
          if (source[index + 1] === '"') {
            field += '"';
            index += 1;
          } else {
            state = "after-quote";
          }
        } else {
          field += character;
        }
        continue;
      }
      if (state === "after-quote") {
        if (character === ",") {
          row.push(field);
          field = "";
          state = "unquoted";
        } else if (character === "\n") {
          pushRow();
          state = "unquoted";
        } else if (character === "\r" && source[index + 1] === "\n") {
          pushRow();
          state = "unquoted";
          index += 1;
        } else {
          return null;
        }
        continue;
      }
      if (character === '"') {
        if (field) return null;
        state = "quoted";
      } else if (character === ",") {
        row.push(field);
        field = "";
      } else if (character === "\n") {
        pushRow();
      } else if (character === "\r" && source[index + 1] === "\n") {
        pushRow();
        index += 1;
      } else {
        field += character;
      }
      if (rows.length > MAX_TRADES + 1) return null;
    }
    if (state === "quoted") return null;
    if (field || row.length) pushRow();
    return rows.length <= MAX_TRADES + 1 ? rows : null;
  }

  function stableCsvId(row, index) {
    let hash = 2166136261;
    const source = row.join("\u001f");
    for (let offset = 0; offset < source.length; offset += 1) {
      hash ^= source.charCodeAt(offset);
      hash = Math.imul(hash, 16777619);
    }
    return `csv-${(hash >>> 0).toString(16).padStart(8, "0")}-${index}`;
  }

  function parseCsv(value) {
    const rows = parseCsvRows(value);
    if (!rows || rows.length < 2) return null;
    const legacyHeader = ["date", "market", "direction", "return_percent", "setup", "notes"];
    const currentHeader = [...legacyHeader, "id", "created_at"];
    const header = rows[0].map((field) => field.trim().toLowerCase());
    const isLegacy = header.length === legacyHeader.length && header.every((field, index) => field === legacyHeader[index]);
    const isCurrent = header.length === currentHeader.length && header.every((field, index) => field === currentHeader[index]);
    if (!isLegacy && !isCurrent) return null;

    const trades = [];
    const ids = new Set();
    for (let index = 1; index < rows.length; index += 1) {
      const row = rows[index];
      if (row.length !== header.length) return null;
      const fallbackTime = Date.parse(`${row[0]}T00:00:00Z`);
      const fallbackCreatedAt = Number.isFinite(fallbackTime) ? new Date(fallbackTime + index).toISOString() : "";
      const trade = normalizeTrade({
        date: row[0],
        market: row[1],
        direction: row[2],
        returnPercent: row[3],
        setup: row[4],
        notes: row[5],
        id: isCurrent ? row[6] : stableCsvId(row, index),
        createdAt: isCurrent ? row[7] : fallbackCreatedAt
      });
      if (!trade || ids.has(trade.id) || (isCurrent && (!row[6].trim() || !Number.isFinite(Date.parse(row[7]))))) return null;
      ids.add(trade.id);
      trades.push(trade);
    }
    return trades.length ? { schema: SCHEMA, source: isCurrent ? "current-csv" : "legacy-csv", trades: orderTrades(trades) } : null;
  }

  function toCsv(values) {
    const quote = (value) => `"${String(value).replace(/"/g, '""')}"`;
    const header = ["date", "market", "direction", "return_percent", "setup", "notes", "id", "created_at"];
    const rows = orderTrades(Array.isArray(values) ? values : []).map((trade) => [
      trade.date, trade.market, trade.direction, trade.returnPercent, trade.setup, trade.notes, trade.id, trade.createdAt
    ].map(quote).join(","));
    return [header.join(","), ...rows].join("\n");
  }

  return { STORAGE_KEY, SCHEMA, MAX_TRADES, normalizeTrade, parseTradePlanHandoff, orderTrades, filterTrades, sampleQuality, summarizeTrades, groupPerformance, buildBackup, parseBackup, parseCsv, toCsv };
});
