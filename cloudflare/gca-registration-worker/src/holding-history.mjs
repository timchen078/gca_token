const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;
const HASH_RE = /^0x[a-fA-F0-9]{64}$/;
const HEX_QUANTITY_RE = /^0x[0-9a-fA-F]+$/;
const DECIMAL_UNITS_RE = /^\d+$/;

export const TRANSFER_EVENT_TOPIC =
  "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef";

function normalizeAddress(value, fieldName) {
  const address = String(value || "").trim().toLowerCase();
  if (!ADDRESS_RE.test(address)) {
    throw new Error(`${fieldName} must be a valid EVM address`);
  }
  return address;
}

function parseSafeInteger(value, fieldName) {
  const parsed = typeof value === "string" && HEX_QUANTITY_RE.test(value)
    ? Number(BigInt(value))
    : Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 0) {
    throw new Error(`${fieldName} must be a non-negative safe integer`);
  }
  return parsed;
}

function parseUnits(value, fieldName) {
  const clean = String(value ?? "").trim();
  if (!DECIMAL_UNITS_RE.test(clean)) {
    throw new Error(`${fieldName} must be unsigned decimal token units`);
  }
  return BigInt(clean);
}

function transferKey(transactionHash, logIndex) {
  return `${transactionHash.toLowerCase()}:${logIndex}`;
}

export function parseRpcQuantity(value, fieldName = "RPC quantity") {
  const clean = String(value || "").trim();
  if (!HEX_QUANTITY_RE.test(clean)) {
    throw new Error(`${fieldName} must be a hexadecimal RPC quantity`);
  }
  return parseSafeInteger(clean, fieldName);
}

export function normalizeBlockscoutTransfer(item, expectedContractAddress) {
  if (!item || typeof item !== "object" || Array.isArray(item)) {
    throw new Error("Blockscout transfer item must be an object");
  }
  const expectedContract = normalizeAddress(expectedContractAddress, "expected contract address");
  const tokenAddress = normalizeAddress(item.token && item.token.address_hash, "Blockscout token address");
  if (tokenAddress !== expectedContract) {
    throw new Error("Blockscout returned a transfer for a different token");
  }
  const fromAddress = normalizeAddress(item.from && item.from.hash, "Blockscout transfer from");
  const toAddress = normalizeAddress(item.to && item.to.hash, "Blockscout transfer to");
  const transactionHash = String(item.transaction_hash || "").trim().toLowerCase();
  if (!HASH_RE.test(transactionHash)) {
    throw new Error("Blockscout transfer transaction hash is invalid");
  }
  const timestampMs = Date.parse(String(item.timestamp || ""));
  if (!Number.isFinite(timestampMs)) {
    throw new Error("Blockscout transfer timestamp is invalid");
  }
  const blockNumber = parseSafeInteger(item.block_number, "Blockscout block number");
  const logIndex = parseSafeInteger(item.log_index, "Blockscout log index");
  const amountUnits = parseUnits(item.total && item.total.value, "Blockscout transfer value");
  return {
    key: transferKey(transactionHash, logIndex),
    transactionHash,
    logIndex,
    blockNumber,
    timestampMs,
    fromAddress,
    toAddress,
    amountUnits: amountUnits.toString(),
    source: "base-blockscout-v2"
  };
}

export function normalizeRpcTransferLog(log, expectedContractAddress) {
  if (!log || typeof log !== "object" || Array.isArray(log)) {
    throw new Error("RPC transfer log must be an object");
  }
  const expectedContract = normalizeAddress(expectedContractAddress, "expected contract address");
  const logAddress = normalizeAddress(log.address, "RPC log address");
  if (logAddress !== expectedContract) {
    throw new Error("RPC returned a log for a different contract");
  }
  const topics = Array.isArray(log.topics) ? log.topics : [];
  if (
    topics.length < 3 ||
    String(topics[0] || "").toLowerCase() !== TRANSFER_EVENT_TOPIC
  ) {
    throw new Error("RPC log is not an ERC-20 Transfer event");
  }
  const topicAddress = (value, fieldName) => {
    const clean = String(value || "").trim().toLowerCase();
    if (!/^0x[a-f0-9]{64}$/.test(clean)) {
      throw new Error(`${fieldName} is invalid`);
    }
    return normalizeAddress(`0x${clean.slice(-40)}`, fieldName);
  };
  const transactionHash = String(log.transactionHash || "").trim().toLowerCase();
  if (!HASH_RE.test(transactionHash)) {
    throw new Error("RPC transfer transaction hash is invalid");
  }
  const data = String(log.data || "").trim();
  if (!/^0x[0-9a-fA-F]{1,64}$/.test(data)) {
    throw new Error("RPC transfer data is invalid");
  }
  const blockNumber = parseRpcQuantity(log.blockNumber, "RPC block number");
  const logIndex = parseRpcQuantity(log.logIndex, "RPC log index");
  return {
    key: transferKey(transactionHash, logIndex),
    transactionHash,
    logIndex,
    blockNumber,
    timestampMs: null,
    fromAddress: topicAddress(topics[1], "RPC transfer from"),
    toAddress: topicAddress(topics[2], "RPC transfer to"),
    amountUnits: BigInt(data).toString(),
    source: "base-public-rpc"
  };
}

export function dedupeTransferEvents(events) {
  const byKey = new Map();
  for (const event of events) {
    if (!event || typeof event !== "object") {
      throw new Error("transfer event must be an object");
    }
    const key = String(event.key || "").trim().toLowerCase();
    if (!key) {
      throw new Error("transfer event key is required");
    }
    const existing = byKey.get(key);
    if (!existing || existing.source !== "base-public-rpc") {
      byKey.set(key, event);
    }
  }
  return Array.from(byKey.values());
}

export function reconstructHoldingWindow({
  walletAddress,
  currentBalanceUnits,
  thresholdUnits,
  events
}) {
  const wallet = normalizeAddress(walletAddress, "wallet address");
  const currentBalance = parseUnits(currentBalanceUnits, "current balance");
  const threshold = parseUnits(thresholdUnits, "holding threshold");
  const orderedEvents = dedupeTransferEvents(events).sort((left, right) => {
    if (left.blockNumber !== right.blockNumber) {
      return right.blockNumber - left.blockNumber;
    }
    return right.logIndex - left.logIndex;
  });

  let reconstructedBalance = currentBalance;
  let minimumBalance = currentBalance;
  for (const event of orderedEvents) {
    const fromAddress = normalizeAddress(event.fromAddress, "event from address");
    const toAddress = normalizeAddress(event.toAddress, "event to address");
    const amountUnits = parseUnits(event.amountUnits, "event transfer value");
    if (fromAddress === wallet && toAddress !== wallet) {
      reconstructedBalance += amountUnits;
    } else if (toAddress === wallet && fromAddress !== wallet) {
      reconstructedBalance -= amountUnits;
    }
    if (reconstructedBalance < 0n) {
      return {
        reconstructionConsistent: false,
        failureReason: "negative_reconstructed_balance",
        currentRawBalance: currentBalance.toString(),
        windowStartRawBalance: "",
        minimumRawBalance: "",
        thresholdRawBalance: threshold.toString(),
        eventCount: orderedEvents.length,
        observedContinuousEligible: false
      };
    }
    if (reconstructedBalance < minimumBalance) {
      minimumBalance = reconstructedBalance;
    }
  }

  return {
    reconstructionConsistent: true,
    failureReason: "",
    currentRawBalance: currentBalance.toString(),
    windowStartRawBalance: reconstructedBalance.toString(),
    minimumRawBalance: minimumBalance.toString(),
    thresholdRawBalance: threshold.toString(),
    eventCount: orderedEvents.length,
    observedContinuousEligible: minimumBalance >= threshold
  };
}
