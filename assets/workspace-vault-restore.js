(function attachWorkspaceVaultRestore(root, factory) {
  const restore = factory();
  root.GcaWorkspaceVaultRestore = restore;
  if (typeof module !== "undefined" && module.exports) module.exports = restore;
})(typeof globalThis !== "undefined" ? globalThis : this, function createWorkspaceVaultRestore() {
  "use strict";

  const PLAN_SCHEMA = "gca-workspace-restore-plan-v1";
  const BUNDLE_SCHEMA = "gca-workspace-bundle-v1";
  const VERSION = 1;
  const MAX_WRITE_CHARS = 8 * 1024 * 1024;
  const MODULE_IDS = Object.freeze([
    "journal",
    "training",
    "research",
    "tradePlans",
    "portfolio",
    "requestReceipts"
  ]);
  const ENGINE_IDS = Object.freeze([
    "journal",
    "training",
    "research",
    "tradePlans",
    "portfolio",
    "workspace"
  ]);
  const STATE_FIELDS = Object.freeze([
    "journal",
    "trainingHistory",
    "trainingDraft",
    "research",
    "tradePlans",
    "portfolio",
    "requestReceipts"
  ]);
  const STORAGE_KEYS = Object.freeze({
    journal: "gca_trade_journal_v1",
    trainingHistory: "gca_risk_training_history_v1",
    trainingDraft: "gca_risk_training_draft_v1",
    research: "gca_research_notes_v1",
    tradePlans: "gca_trade_plans_v1",
    portfolio: "gca_portfolio_risk_v1",
    requestReceipts: "gca_member_service_request_history_v1"
  });
  const BOUNDARIES = Object.freeze({
    includesMemberSnapshot: false,
    includesServiceRequestPacket: false,
    mayContainUserEnteredToolContent: true,
    uploadedByPage: false,
    connectsWallet: false,
    connectsExchange: false,
    placesOrders: false
  });
  const IMPACT_FIELDS = Object.freeze([
    "id",
    "incoming",
    "added",
    "updated",
    "retained",
    "dropped",
    "localRemoved",
    "changed",
    "action"
  ]);

  function parseJson(value) {
    try {
      return typeof value === "string" ? JSON.parse(value) : value;
    } catch (error) {
      return null;
    }
  }

  function exactKeys(value, fields) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false;
    const keys = Object.keys(value);
    return keys.length === fields.length && keys.every((key) => fields.includes(key));
  }

  function normalizedIso(value) {
    const parsed = Date.parse(value);
    if (!Number.isFinite(parsed)) return null;
    const normalized = new Date(parsed).toISOString();
    return normalized === value ? normalized : null;
  }

  function validRawState(value) {
    return value === null || typeof value === "string";
  }

  function exactBundle(value) {
    if (!exactKeys(value, ["schema", "version", "exportedAt", "modules", "boundaries"])) return false;
    if (value.schema !== BUNDLE_SCHEMA || value.version !== VERSION || !normalizedIso(value.exportedAt)) return false;
    if (!exactKeys(value.modules, MODULE_IDS) || !exactKeys(value.boundaries, Object.keys(BOUNDARIES))) return false;
    if (Object.keys(BOUNDARIES).some((key) => value.boundaries[key] !== BOUNDARIES[key])) return false;
    return MODULE_IDS.some((moduleId) => value.modules[moduleId] !== null);
  }

  function validEngines(engines) {
    if (!exactKeys(engines, ENGINE_IDS)) return false;
    const required = [
      [engines.journal, "STORAGE_KEY", STORAGE_KEYS.journal, ["parseBackup", "buildBackup", "orderTrades"]],
      [engines.training, "HISTORY_KEY", STORAGE_KEYS.trainingHistory, ["parseTrainingBackup", "parseAttemptHistory", "parseTrainingDraft"]],
      [engines.training, "DRAFT_KEY", STORAGE_KEYS.trainingDraft, []],
      [engines.research, "STORAGE_KEY", STORAGE_KEYS.research, ["parseBackup", "buildBackup", "mergeBackup"]],
      [engines.tradePlans, "STORAGE_KEY", STORAGE_KEYS.tradePlans, ["parseBackup", "buildBackup", "mergeBackup"]],
      [engines.portfolio, "STORAGE_KEY", STORAGE_KEYS.portfolio, ["parseBackup"]],
      [engines.workspace, "REQUEST_HISTORY_KEY", STORAGE_KEYS.requestReceipts, ["parseRequestHistory", "parseRequestHistoryBackup", "mergeRequestHistoryBackup"]]
    ];
    return required.every(([engine, key, expected, methods]) =>
      engine && engine[key] === expected && methods.every((method) => typeof engine[method] === "function")
    );
  }

  function validCurrentState(value) {
    return exactKeys(value, STATE_FIELDS) && STATE_FIELDS.every((field) => validRawState(value[field]));
  }

  function frozenImpact(id, incoming, added, updated, retained, dropped, localRemoved, changed, action) {
    return Object.freeze({ id, incoming, added, updated, retained, dropped, localRemoved, changed, action });
  }

  function journalBackupFromRaw(value, journal, timestamp) {
    if (value === null) return { ok: true, backup: null };
    const direct = journal.parseBackup(value);
    if (direct && direct.trades.length) return { ok: true, backup: direct };
    const rows = parseJson(value);
    if (!Array.isArray(rows) || !rows.length) return { ok: false, backup: null };
    const backup = journal.parseBackup(journal.buildBackup(rows, timestamp));
    return { ok: Boolean(backup), backup };
  }

  function strictArrayState(value, parser) {
    if (value === null) return { ok: true, rows: [] };
    const raw = parseJson(value);
    if (!Array.isArray(raw)) return { ok: false, rows: [] };
    const rows = parser(value);
    return { ok: Array.isArray(rows) && rows.length === raw.length, rows };
  }

  function recordsById(values, field) {
    return new Map((Array.isArray(values) ? values : []).map((value) => [value[field], value]));
  }

  function sameValue(left, right) {
    return JSON.stringify(left) === JSON.stringify(right);
  }

  function checkedWrite(key, value) {
    if (!Object.values(STORAGE_KEYS).includes(key)) return null;
    if (value !== null && (typeof value !== "string" || value.length > MAX_WRITE_CHARS)) return null;
    return Object.freeze({ key, value });
  }

  function buildRestorePlan(bundleValue, currentState, engines, restoredAt) {
    const bundle = parseJson(bundleValue);
    const timestamp = normalizedIso(restoredAt);
    if (!exactBundle(bundle) || !timestamp || !validEngines(engines) || !validCurrentState(currentState)) return null;

    try {
      const writes = [];
      const impacts = [];

      if (bundle.modules.journal) {
        const incoming = engines.journal.parseBackup(bundle.modules.journal);
        const currentResult = journalBackupFromRaw(currentState.journal, engines.journal, timestamp);
        if (!incoming || !currentResult.ok) return null;
        const current = currentResult.backup ? currentResult.backup.trades : [];
        const currentIds = new Set(current.map((trade) => trade.id));
        const newTrades = incoming.trades.filter((trade) => !currentIds.has(trade.id));
        const combined = engines.journal.orderTrades([...current, ...newTrades]);
        const combinedIds = new Set(combined.map((trade) => trade.id));
        if (current.some((trade) => !combinedIds.has(trade.id))) return null;
        const added = newTrades.filter((trade) => combinedIds.has(trade.id)).length;
        const dropped = newTrades.length - added;
        const retained = incoming.trades.length - newTrades.length;
        const changed = added > 0;
        if (changed) {
          const backup = engines.journal.parseBackup(engines.journal.buildBackup(combined, timestamp));
          const write = backup && checkedWrite(STORAGE_KEYS.journal, JSON.stringify(backup));
          if (!write) return null;
          writes.push(write);
        }
        impacts.push(frozenImpact(
          "journal",
          incoming.trades.length,
          added,
          0,
          retained,
          dropped,
          0,
          changed,
          changed ? "Merge new journal records" : "Keep current journal records"
        ));
      }

      if (bundle.modules.training) {
        const incoming = engines.training.parseTrainingBackup(bundle.modules.training);
        const currentHistoryResult = strictArrayState(currentState.trainingHistory, engines.training.parseAttemptHistory);
        const currentDraft = currentState.trainingDraft === null ? null : engines.training.parseTrainingDraft(currentState.trainingDraft);
        if (!incoming || !currentHistoryResult.ok || (currentState.trainingDraft !== null && !currentDraft)) return null;
        const currentHistory = currentHistoryResult.rows;
        const currentIds = new Set(currentHistory.map((item) => item.attemptId));
        const history = engines.training.parseAttemptHistory([...currentHistory, ...incoming.history]);
        const historyIds = new Set(history.map((item) => item.attemptId));
        if (currentHistory.some((item) => !historyIds.has(item.attemptId))) return null;
        const newHistory = incoming.history.filter((item) => !currentIds.has(item.attemptId));
        const addedHistory = newHistory.filter((item) => historyIds.has(item.attemptId)).length;
        const droppedHistory = newHistory.length - addedHistory;
        const incomingDraftApplied = Boolean(
          incoming.draft && (!currentDraft || Date.parse(incoming.draft.savedAt) > Date.parse(currentDraft.savedAt))
        );
        const draftAdded = incomingDraftApplied && !currentDraft ? 1 : 0;
        const draftUpdated = incomingDraftApplied && currentDraft ? 1 : 0;
        const incomingDraftRetained = incoming.draft && !incomingDraftApplied ? 1 : 0;
        const changed = addedHistory > 0 || incomingDraftApplied;
        if (addedHistory > 0) {
          const write = checkedWrite(STORAGE_KEYS.trainingHistory, JSON.stringify(history));
          if (!write) return null;
          writes.push(write);
        }
        if (incomingDraftApplied) {
          const write = checkedWrite(STORAGE_KEYS.trainingDraft, JSON.stringify(incoming.draft));
          if (!write) return null;
          writes.push(write);
        }
        impacts.push(frozenImpact(
          "training",
          incoming.history.length + (incoming.draft ? 1 : 0),
          addedHistory + draftAdded,
          draftUpdated,
          incoming.history.length - newHistory.length + incomingDraftRetained,
          droppedHistory,
          0,
          changed,
          changed ? "Merge attempts and use only a newer draft" : "Keep current training history and draft"
        ));
      }

      if (bundle.modules.research) {
        const incoming = engines.research.parseBackup(bundle.modules.research);
        const current = currentState.research === null ? null : engines.research.parseBackup(currentState.research);
        if (!incoming || (currentState.research !== null && !current)) return null;
        const currentNotes = current ? current.notes : [];
        const currentIds = new Set(currentNotes.map((note) => note.id));
        const merged = engines.research.mergeBackup(currentNotes, incoming);
        if (!merged) return null;
        const mergedIds = new Set(merged.notes.map((note) => note.id));
        if (currentNotes.some((note) => !mergedIds.has(note.id))) return null;
        const added = merged.addedNoteCount;
        const updated = merged.updatedNoteCount;
        const dropped = merged.droppedNewNoteCount;
        const retained = incoming.notes.length - added - updated - dropped;
        const changed = added + updated > 0;
        if (changed) {
          const backup = engines.research.parseBackup(engines.research.buildBackup(merged.notes, timestamp));
          const write = backup && checkedWrite(STORAGE_KEYS.research, JSON.stringify(backup));
          if (!write) return null;
          writes.push(write);
        }
        impacts.push(frozenImpact(
          "research",
          incoming.notes.length,
          added,
          updated,
          retained,
          dropped,
          0,
          changed,
          changed ? "Merge newer research records" : "Keep current research records"
        ));
      }

      if (bundle.modules.tradePlans) {
        const incoming = engines.tradePlans.parseBackup(bundle.modules.tradePlans);
        const current = currentState.tradePlans === null ? null : engines.tradePlans.parseBackup(currentState.tradePlans);
        if (!incoming || (currentState.tradePlans !== null && !current)) return null;
        const currentPlans = current ? current.plans : [];
        const merged = engines.tradePlans.mergeBackup(currentPlans, incoming);
        if (!merged) return null;
        const mergedIds = new Set(merged.plans.map((plan) => plan.id));
        if (currentPlans.some((plan) => !mergedIds.has(plan.id))) return null;
        const added = merged.addedPlanCount;
        const updated = merged.updatedPlanCount;
        const dropped = merged.droppedNewPlanCount;
        const retained = incoming.plans.length - added - updated - dropped;
        const changed = added + updated > 0;
        if (changed) {
          const backup = engines.tradePlans.parseBackup(engines.tradePlans.buildBackup(merged.plans, timestamp));
          const write = backup && checkedWrite(STORAGE_KEYS.tradePlans, JSON.stringify(backup));
          if (!write) return null;
          writes.push(write);
        }
        impacts.push(frozenImpact(
          "tradePlans",
          incoming.plans.length,
          added,
          updated,
          retained,
          dropped,
          0,
          changed,
          changed ? "Merge newer trade plans" : "Keep current trade plans"
        ));
      }

      if (bundle.modules.portfolio) {
        const incoming = engines.portfolio.parseBackup(bundle.modules.portfolio);
        const current = currentState.portfolio === null ? null : engines.portfolio.parseBackup(currentState.portfolio);
        if (!incoming || (currentState.portfolio !== null && !current)) return null;
        const currentById = recordsById(current ? current.positions : [], "id");
        const incomingById = recordsById(incoming.positions, "id");
        const newer = !current || Date.parse(incoming.savedAt) > Date.parse(current.savedAt);
        const sameSnapshot = Boolean(current && sameValue(current.config, incoming.config) && sameValue(current.positions, incoming.positions));
        const changed = newer && !sameSnapshot;
        let added = 0;
        let updated = 0;
        let retained = incoming.positions.length;
        let localRemoved = 0;
        if (changed) {
          added = incoming.positions.filter((position) => !currentById.has(position.id)).length;
          updated = incoming.positions.filter((position) => {
            const existing = currentById.get(position.id);
            return existing && !sameValue(existing, position);
          }).length;
          retained = incoming.positions.length - added - updated;
          localRemoved = [...currentById.keys()].filter((id) => !incomingById.has(id)).length;
          const write = checkedWrite(STORAGE_KEYS.portfolio, JSON.stringify(incoming));
          if (!write) return null;
          writes.push(write);
        }
        impacts.push(frozenImpact(
          "portfolio",
          incoming.positions.length,
          added,
          updated,
          retained,
          0,
          localRemoved,
          changed,
          changed
            ? `Replace the portfolio snapshot${localRemoved ? `; ${localRemoved} local position(s) are not in the newer copy` : ""}`
            : "Keep the current portfolio snapshot"
        ));
      }

      if (bundle.modules.requestReceipts) {
        const incoming = engines.workspace.parseRequestHistoryBackup(bundle.modules.requestReceipts);
        const currentResult = strictArrayState(currentState.requestReceipts, engines.workspace.parseRequestHistory);
        if (!incoming || !currentResult.ok) return null;
        const current = currentResult.rows;
        const currentIds = new Set(current.map((receipt) => receipt.requestId));
        const merged = engines.workspace.mergeRequestHistoryBackup(currentState.requestReceipts, incoming);
        if (!merged) return null;
        const mergedIds = new Set(merged.receipts.map((receipt) => receipt.requestId));
        if (current.some((receipt) => !mergedIds.has(receipt.requestId))) return null;
        const added = merged.addedReceiptCount;
        const updated = merged.updatedReceiptCount;
        const dropped = incoming.receipts.filter((receipt) => !currentIds.has(receipt.requestId) && !mergedIds.has(receipt.requestId)).length;
        const retained = incoming.receipts.length - added - updated - dropped;
        const changed = added + updated > 0;
        if (changed) {
          const write = checkedWrite(STORAGE_KEYS.requestReceipts, JSON.stringify(merged.receipts));
          if (!write) return null;
          writes.push(write);
        }
        impacts.push(frozenImpact(
          "requestReceipts",
          incoming.receipts.length,
          added,
          updated,
          retained,
          dropped,
          0,
          changed,
          changed ? "Merge newer request receipts" : "Keep current request receipts"
        ));
      }

      if (!impacts.length) return null;
      const changedModuleCount = impacts.filter((impact) => impact.changed).length;
      const plan = Object.freeze({
        schema: PLAN_SCHEMA,
        version: VERSION,
        createdAt: timestamp,
        bundleExportedAt: bundle.exportedAt,
        impacts: Object.freeze(impacts),
        writes: Object.freeze(writes),
        changedModuleCount,
        writeCount: writes.length,
        hasChanges: writes.length > 0
      });
      return parseRestorePlan(plan);
    } catch (error) {
      return null;
    }
  }

  function parseRestorePlan(value) {
    const payload = parseJson(value);
    if (!exactKeys(payload, ["schema", "version", "createdAt", "bundleExportedAt", "impacts", "writes", "changedModuleCount", "writeCount", "hasChanges"])) return null;
    if (payload.schema !== PLAN_SCHEMA || payload.version !== VERSION || !normalizedIso(payload.createdAt) || !normalizedIso(payload.bundleExportedAt)) return null;
    if (!Array.isArray(payload.impacts) || !payload.impacts.length || payload.impacts.length > MODULE_IDS.length) return null;
    const impactIds = new Set();
    const impacts = [];
    for (const impact of payload.impacts) {
      if (!exactKeys(impact, IMPACT_FIELDS) || !MODULE_IDS.includes(impact.id) || impactIds.has(impact.id)) return null;
      impactIds.add(impact.id);
      const counts = [impact.incoming, impact.added, impact.updated, impact.retained, impact.dropped, impact.localRemoved];
      if (!counts.every((count) => Number.isInteger(count) && count >= 0)) return null;
      if (impact.incoming !== impact.added + impact.updated + impact.retained + impact.dropped) return null;
      if (typeof impact.changed !== "boolean" || typeof impact.action !== "string" || !impact.action || impact.action.length > 240) return null;
      impacts.push(frozenImpact(...IMPACT_FIELDS.map((field) => impact[field])));
    }
    if (!Array.isArray(payload.writes) || payload.writes.length > Object.keys(STORAGE_KEYS).length) return null;
    const writeKeys = new Set();
    const writes = [];
    for (const entry of payload.writes) {
      if (!exactKeys(entry, ["key", "value"]) || writeKeys.has(entry.key)) return null;
      const write = checkedWrite(entry.key, entry.value);
      if (!write) return null;
      writeKeys.add(write.key);
      writes.push(write);
    }
    const changedModuleCount = impacts.filter((impact) => impact.changed).length;
    if (!Number.isInteger(payload.changedModuleCount) || payload.changedModuleCount !== changedModuleCount) return null;
    if (!Number.isInteger(payload.writeCount) || payload.writeCount !== writes.length) return null;
    if (payload.hasChanges !== (writes.length > 0) || (changedModuleCount > 0) !== payload.hasChanges) return null;
    return Object.freeze({
      schema: PLAN_SCHEMA,
      version: VERSION,
      createdAt: payload.createdAt,
      bundleExportedAt: payload.bundleExportedAt,
      impacts: Object.freeze(impacts),
      writes: Object.freeze(writes),
      changedModuleCount,
      writeCount: writes.length,
      hasChanges: writes.length > 0
    });
  }

  function result(ok, stage, appliedWriteCount, rollbackComplete, rollbackFailureCount) {
    return Object.freeze({ ok, stage, appliedWriteCount, rollbackComplete, rollbackFailureCount });
  }

  function applyRestorePlan(planValue, storage) {
    const plan = parseRestorePlan(planValue);
    if (!plan) return result(false, "invalid-plan", 0, true, 0);
    if (!storage || typeof storage.getItem !== "function" || typeof storage.setItem !== "function" || typeof storage.removeItem !== "function") {
      return result(false, "invalid-storage", 0, true, 0);
    }
    const previous = [];
    try {
      plan.writes.forEach((entry) => {
        const value = storage.getItem(entry.key);
        if (value !== null && typeof value !== "string") throw new Error("invalid-snapshot");
        previous.push(Object.freeze({ key: entry.key, value }));
      });
    } catch (error) {
      return result(false, "snapshot-failed", 0, true, 0);
    }
    let appliedWriteCount = 0;
    try {
      plan.writes.forEach((entry) => {
        if (entry.value === null) storage.removeItem(entry.key);
        else storage.setItem(entry.key, entry.value);
        appliedWriteCount += 1;
      });
      return result(true, "complete", appliedWriteCount, true, 0);
    } catch (error) {
      let rollbackFailureCount = 0;
      [...previous].reverse().forEach((entry) => {
        try {
          if (entry.value === null) storage.removeItem(entry.key);
          else storage.setItem(entry.key, entry.value);
        } catch (rollbackError) {
          rollbackFailureCount += 1;
        }
      });
      return result(false, "write-failed", appliedWriteCount, rollbackFailureCount === 0, rollbackFailureCount);
    }
  }

  return Object.freeze({
    PLAN_SCHEMA,
    MODULE_IDS,
    STATE_FIELDS,
    STORAGE_KEYS,
    buildRestorePlan,
    parseRestorePlan,
    applyRestorePlan
  });
});
