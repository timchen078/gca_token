(function attachResearchNotes(root, factory) {
  const notes = factory();
  root.GcaResearchNotes = notes;
  if (typeof module !== "undefined" && module.exports) module.exports = notes;
})(typeof globalThis !== "undefined" ? globalThis : this, function createResearchNotes() {
  "use strict";

  const STORAGE_KEY = "gca_research_notes_v1";
  const SCHEMA = "gca-research-notes-v1";
  const MAX_NOTES = 200;
  const NOTE_ID_RE = /^gca_note_[a-z0-9-]{8,64}$/;
  const STATUSES = Object.freeze(["watching", "active-research", "needs-review", "invalidated", "archived"]);
  const HORIZONS = Object.freeze(["event-driven", "short-term", "medium-term", "long-term", "structural"]);
  const EVIDENCE_STATES = Object.freeze(["unverified", "developing", "supported", "conflicting"]);
  const ACTIVE_STATUSES = new Set(["watching", "active-research", "needs-review"]);
  const SENSITIVE_RE = /private\s*key|seed\s*phrase|mnemonic|api\s*secret|wallet\s*password|one[-\s]*time\s*code|withdrawal\s*permission|remote\s*control|\b(?:otp|2fa)\b|\u79c1\u94a5|\u52a9\u8bb0\u8bcd|\u5bc6\u7801|\u9a8c\u8bc1\u7801|\u63d0\u73b0\u6743\u9650|\u8fdc\u7a0b\u63a7\u5236/i;
  const NOTE_FIELDS = Object.freeze([
    "version",
    "id",
    "observedOn",
    "reviewOn",
    "title",
    "theme",
    "status",
    "horizon",
    "evidenceState",
    "tags",
    "thesis",
    "evidence",
    "catalyst",
    "invalidation",
    "riskNotes",
    "sourceUrl",
    "createdAt",
    "updatedAt"
  ]);

  function cleanText(value, maxLength) {
    return String(value || "").trim().replace(/\s+/g, " ").slice(0, maxLength);
  }

  function parseJson(value) {
    try {
      return typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
  }

  function validDate(value) {
    const date = String(value || "");
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
    const parsed = new Date(`${date}T00:00:00Z`);
    return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date;
  }

  function normalizedIso(value) {
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? new Date(parsed).toISOString() : "";
  }

  function normalizeSourceUrl(value) {
    const source = cleanText(value, 500);
    if (!source) return "";
    try {
      const url = new URL(source);
      if (url.protocol !== "https:" || url.username || url.password) return "";
      url.hash = "";
      return url.href.slice(0, 500);
    } catch (error) {
      return "";
    }
  }

  function normalizeTags(value) {
    const candidates = Array.isArray(value) ? value : String(value || "").split(",");
    const seen = new Set();
    const tags = [];
    candidates.forEach((candidate) => {
      const tag = cleanText(candidate, 30);
      const key = tag.toLowerCase();
      if (!tag || seen.has(key) || tags.length >= 8) return;
      seen.add(key);
      tags.push(tag);
    });
    return tags;
  }

  function normalizeNote(input) {
    if (!input || typeof input !== "object") return null;
    const id = cleanText(input.id, 80).toLowerCase();
    const observedOn = String(input.observedOn || "");
    const reviewOn = String(input.reviewOn || "");
    const title = cleanText(input.title, 120);
    const theme = cleanText(input.theme, 80);
    const status = STATUSES.includes(input.status) ? input.status : "";
    const horizon = HORIZONS.includes(input.horizon) ? input.horizon : "";
    const evidenceState = EVIDENCE_STATES.includes(input.evidenceState) ? input.evidenceState : "";
    const tags = normalizeTags(input.tags);
    const thesis = cleanText(input.thesis, 1200);
    const evidence = cleanText(input.evidence, 1600);
    const catalyst = cleanText(input.catalyst, 800);
    const invalidation = cleanText(input.invalidation, 800);
    const riskNotes = cleanText(input.riskNotes, 800);
    const sourceInput = cleanText(input.sourceUrl, 500);
    const sourceUrl = normalizeSourceUrl(sourceInput);
    const createdAt = normalizedIso(input.createdAt);
    const updatedAt = normalizedIso(input.updatedAt);
    if (
      !NOTE_ID_RE.test(id) ||
      !validDate(observedOn) ||
      (reviewOn && (!validDate(reviewOn) || reviewOn < observedOn)) ||
      title.length < 3 ||
      theme.length < 2 ||
      !status ||
      !horizon ||
      !evidenceState ||
      thesis.length < 20 ||
      invalidation.length < 10 ||
      riskNotes.length < 10 ||
      (sourceInput && !sourceUrl) ||
      !createdAt ||
      !updatedAt ||
      Date.parse(updatedAt) < Date.parse(createdAt)
    ) return null;
    if (SENSITIVE_RE.test([title, theme, thesis, evidence, catalyst, invalidation, riskNotes].join(" "))) return null;
    return {
      version: 1,
      id,
      observedOn,
      reviewOn,
      title,
      theme,
      status,
      horizon,
      evidenceState,
      tags,
      thesis,
      evidence,
      catalyst,
      invalidation,
      riskNotes,
      sourceUrl,
      createdAt,
      updatedAt
    };
  }

  function orderNotes(values) {
    const rows = Array.isArray(values) ? values : [];
    const byId = new Map();
    rows.forEach((value) => {
      const note = normalizeNote(value);
      if (!note) return;
      const existing = byId.get(note.id);
      if (!existing || Date.parse(note.updatedAt) > Date.parse(existing.updatedAt)) byId.set(note.id, note);
    });
    return [...byId.values()]
      .sort((left, right) =>
        Date.parse(right.updatedAt) - Date.parse(left.updatedAt) ||
        right.observedOn.localeCompare(left.observedOn) ||
        left.id.localeCompare(right.id)
      )
      .slice(0, MAX_NOTES);
  }

  function reviewDate(nowMs) {
    const now = Number.isFinite(Number(nowMs)) ? Number(nowMs) : Date.now();
    const date = new Date(now);
    return Number.isFinite(date.getTime()) ? date.toISOString().slice(0, 10) : new Date().toISOString().slice(0, 10);
  }

  function isDueForReview(note, today) {
    return Boolean(note.reviewOn && note.reviewOn <= today && ACTIVE_STATUSES.has(note.status));
  }

  function filterNotes(values, filters, nowMs) {
    const requested = filters && typeof filters === "object" ? filters : {};
    const query = cleanText(requested.query, 120).toLowerCase();
    const status = STATUSES.includes(requested.status) ? requested.status : "";
    const horizon = HORIZONS.includes(requested.horizon) ? requested.horizon : "";
    const evidenceState = EVIDENCE_STATES.includes(requested.evidenceState) ? requested.evidenceState : "";
    const tag = cleanText(requested.tag, 30).toLowerCase();
    const dueOnly = requested.dueOnly === true || requested.dueOnly === "true";
    const today = reviewDate(nowMs);
    return orderNotes(values).filter((note) => {
      const searchable = [
        note.title,
        note.theme,
        note.thesis,
        note.evidence,
        note.catalyst,
        note.invalidation,
        note.riskNotes,
        note.sourceUrl,
        ...note.tags
      ].join(" ").toLowerCase();
      return (
        (!query || searchable.includes(query)) &&
        (!status || note.status === status) &&
        (!horizon || note.horizon === horizon) &&
        (!evidenceState || note.evidenceState === evidenceState) &&
        (!tag || note.tags.some((item) => item.toLowerCase() === tag)) &&
        (!dueOnly || isDueForReview(note, today))
      );
    });
  }

  function summarizeNotes(values, nowMs) {
    const notes = orderNotes(values);
    const today = reviewDate(nowMs);
    return {
      count: notes.length,
      activeCount: notes.filter((note) => ACTIVE_STATUSES.has(note.status)).length,
      sourcedCount: notes.filter((note) => Boolean(note.sourceUrl)).length,
      dueReviewCount: notes.filter((note) => isDueForReview(note, today)).length,
      invalidatedCount: notes.filter((note) => note.status === "invalidated").length,
      latestUpdatedAt: notes.length ? notes[0].updatedAt : null,
      tags: [...new Set(notes.flatMap((note) => note.tags).map((tag) => tag.toLowerCase()))].sort()
    };
  }

  function upsertNote(values, value) {
    const note = normalizeNote(value);
    if (!note) return orderNotes(values);
    return orderNotes([note, ...orderNotes(values).filter((item) => item.id !== note.id)]);
  }

  function removeNote(values, noteId) {
    return orderNotes(values).filter((note) => note.id !== noteId);
  }

  function buildBackup(values, exportedAt) {
    const timestamp = normalizedIso(exportedAt) || new Date().toISOString();
    return Object.freeze({
      schema: SCHEMA,
      version: 1,
      exportedAt: timestamp,
      notes: orderNotes(values)
    });
  }

  function exactNote(value, normalized) {
    if (!value || typeof value !== "object" || !normalized) return false;
    const keys = Object.keys(value);
    if (keys.length !== NOTE_FIELDS.length || keys.some((key) => !NOTE_FIELDS.includes(key))) return false;
    return NOTE_FIELDS.every((key) => {
      if (key === "tags") return JSON.stringify(value.tags) === JSON.stringify(normalized.tags);
      return value[key] === normalized[key];
    });
  }

  function parseBackup(value) {
    const payload = parseJson(value);
    if (!payload || typeof payload !== "object") return null;
    const keys = Object.keys(payload);
    const exportedAt = normalizedIso(payload.exportedAt);
    if (
      keys.length !== 4 ||
      keys.some((key) => !["schema", "version", "exportedAt", "notes"].includes(key)) ||
      payload.schema !== SCHEMA ||
      payload.version !== 1 ||
      !exportedAt ||
      payload.exportedAt !== exportedAt ||
      !Array.isArray(payload.notes) ||
      payload.notes.length === 0 ||
      payload.notes.length > MAX_NOTES
    ) return null;
    const normalized = payload.notes.map(normalizeNote);
    if (normalized.some((note, index) => !exactNote(payload.notes[index], note))) return null;
    const notes = orderNotes(normalized);
    if (notes.length !== payload.notes.length) return null;
    return Object.freeze({ schema: SCHEMA, version: 1, exportedAt, notes });
  }

  function mergeBackup(currentValue, backupValue) {
    const backup = parseBackup(backupValue);
    if (!backup) return null;
    const current = orderNotes(currentValue);
    const currentById = new Map(current.map((note) => [note.id, note]));
    const mergedById = new Map(currentById);
    const updatedIds = new Set();
    backup.notes.forEach((note) => {
      const existing = mergedById.get(note.id);
      if (!existing || Date.parse(note.updatedAt) > Date.parse(existing.updatedAt)) {
        mergedById.set(note.id, note);
        if (existing) updatedIds.add(note.id);
      }
    });
    const notes = orderNotes([...mergedById.values()]);
    const retainedIds = new Set(notes.map((note) => note.id));
    return Object.freeze({
      notes,
      importedNoteCount: backup.notes.length,
      addedNoteCount: backup.notes.filter((note) => !currentById.has(note.id) && retainedIds.has(note.id)).length,
      updatedNoteCount: [...updatedIds].filter((noteId) => retainedIds.has(noteId)).length,
      droppedNewNoteCount: backup.notes.filter((note) => !currentById.has(note.id) && !retainedIds.has(note.id)).length
    });
  }

  return Object.freeze({
    STORAGE_KEY,
    SCHEMA,
    MAX_NOTES,
    STATUSES,
    HORIZONS,
    EVIDENCE_STATES,
    normalizeNote,
    orderNotes,
    filterNotes,
    summarizeNotes,
    upsertNote,
    removeNote,
    buildBackup,
    parseBackup,
    mergeBackup
  });
});
