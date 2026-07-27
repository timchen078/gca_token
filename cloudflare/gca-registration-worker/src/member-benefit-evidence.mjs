import {
  TRANSFER_EVENT_TOPIC,
  normalizeRpcTransferLog,
  parseRpcQuantity
} from "./holding-history.mjs";

const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;
const HASH_RE = /^0x[a-fA-F0-9]{64}$/;
const DECIMAL_UNITS_RE = /^\d+$/;

function normalizeAddress(value, fieldName) {
  const address = String(value || "").trim().toLowerCase();
  if (!ADDRESS_RE.test(address)) {
    throw new Error(`${fieldName} must be a valid EVM address`);
  }
  return address;
}

function normalizeHash(value, fieldName) {
  const hash = String(value || "").trim().toLowerCase();
  if (!HASH_RE.test(hash)) {
    throw new Error(`${fieldName} must be a valid transaction hash`);
  }
  return hash;
}

function parseUnits(value, fieldName) {
  const clean = String(value ?? "").trim();
  if (!DECIMAL_UNITS_RE.test(clean)) {
    throw new Error(`${fieldName} must be unsigned decimal token units`);
  }
  return BigInt(clean);
}

export function verifyMemberBenefitTransferReceipt({
  receipt,
  transactionHash,
  expectedContractAddress,
  expectedSourceWallet,
  expectedRecipientWallet,
  expectedAmountUnits,
  safeBlockNumber
}) {
  const txHash = normalizeHash(transactionHash, "transaction hash");
  const contract = normalizeAddress(expectedContractAddress, "expected contract address");
  const source = normalizeAddress(expectedSourceWallet, "expected source wallet");
  const recipient = normalizeAddress(expectedRecipientWallet, "expected recipient wallet");
  const amount = parseUnits(expectedAmountUnits, "expected amount");
  if (!Number.isSafeInteger(safeBlockNumber) || safeBlockNumber < 0) {
    throw new Error("safe block number must be a non-negative safe integer");
  }
  if (!receipt || typeof receipt !== "object" || Array.isArray(receipt)) {
    return {
      status: "transaction_not_found",
      matchedTransfer: false,
      failureReason: "transaction_receipt_not_found"
    };
  }

  const receiptTxHash = normalizeHash(receipt.transactionHash, "receipt transaction hash");
  if (receiptTxHash !== txHash) {
    throw new Error("receipt transaction hash does not match the requested transaction");
  }
  if (String(receipt.status || "").trim().toLowerCase() !== "0x1") {
    return {
      status: "transaction_failed",
      matchedTransfer: false,
      failureReason: "transaction_receipt_status_failed"
    };
  }

  const receiptBlockNumber = parseRpcQuantity(receipt.blockNumber, "receipt block number");
  if (receiptBlockNumber > safeBlockNumber) {
    return {
      status: "awaiting_safe_confirmation",
      matchedTransfer: false,
      failureReason: "transaction_block_is_not_safe",
      receiptBlockNumber
    };
  }
  const receiptBlockHash = normalizeHash(receipt.blockHash, "receipt block hash");
  const receiptFrom = normalizeAddress(receipt.from, "receipt sender");
  const receiptTo = normalizeAddress(receipt.to, "receipt target");
  if (receiptFrom !== source) {
    return {
      status: "source_wallet_mismatch",
      matchedTransfer: false,
      failureReason: "transaction_sender_is_not_official_reserve",
      receiptBlockNumber,
      receiptBlockHash
    };
  }
  if (receiptTo !== contract) {
    return {
      status: "contract_target_mismatch",
      matchedTransfer: false,
      failureReason: "transaction_target_is_not_gca_contract",
      receiptBlockNumber,
      receiptBlockHash
    };
  }

  const logs = Array.isArray(receipt.logs) ? receipt.logs : [];
  const matches = [];
  let relevantTransferCount = 0;
  for (const rawLog of logs) {
    if (!rawLog || typeof rawLog !== "object" || Array.isArray(rawLog)) {
      continue;
    }
    const logAddress = String(rawLog.address || "").trim().toLowerCase();
    const topics = Array.isArray(rawLog.topics) ? rawLog.topics : [];
    const firstTopic = String(topics[0] || "").trim().toLowerCase();
    if (logAddress !== contract || firstTopic !== TRANSFER_EVENT_TOPIC) {
      continue;
    }
    const event = normalizeRpcTransferLog(rawLog, contract);
    relevantTransferCount += 1;
    if (
      event.transactionHash === txHash &&
      event.blockNumber === receiptBlockNumber &&
      event.fromAddress === source &&
      event.toAddress === recipient &&
      parseUnits(event.amountUnits, "transfer amount") === amount
    ) {
      matches.push(event);
    }
  }

  if (matches.length !== 1) {
    return {
      status: matches.length > 1 ? "ambiguous_transfer_logs" : "transfer_log_mismatch",
      matchedTransfer: false,
      failureReason: matches.length > 1
        ? "multiple_exact_member_benefit_transfers_found"
        : "exact_member_benefit_transfer_not_found",
      receiptBlockNumber,
      receiptBlockHash,
      relevantTransferCount,
      exactMatchCount: matches.length
    };
  }

  const match = matches[0];
  return {
    status: "verified",
    matchedTransfer: true,
    failureReason: "",
    transactionHash: txHash,
    receiptBlockNumber,
    receiptBlockHash,
    sourceWallet: source,
    recipientWallet: recipient,
    contractAddress: contract,
    amountUnits: amount.toString(),
    transferLogIndex: match.logIndex,
    relevantTransferCount,
    exactMatchCount: 1
  };
}
