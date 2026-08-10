import {
  TRANSFER_EVENT_TOPIC,
  dedupeTransferEvents,
  normalizeBlockscoutTransfer,
  normalizeRpcTransferLog,
  parseRpcQuantity,
  reconstructHoldingWindow
} from "./holding-history.mjs";
import { verifyMemberBenefitTransferReceipt } from "./member-benefit-evidence.mjs";
import {
  buildPublicAccountStatus,
  isStatusAccessToken
} from "./account-status.mjs";

const EMAIL_REGISTRATION_VERSION = "gca_email_registration_v1";
const CONTACT_SUPPRESSION_VERSION = "gca_contact_suppression_v1";
const MEMBER_ACCESS_VERSION = "gca_member_access_v2";
const LEGACY_MEMBER_ACCESS_VERSION = "gca_member_access_v1";
const ACCOUNT_STATUS_VERSION = "gca_account_status_v1";
const ACCOUNT_STATUS_ROTATION_VERSION = "gca_account_status_rotation_v1";
const ACCOUNT_STATUS_RECOVERY_REQUEST_VERSION = "gca_account_status_recovery_request_v1";
const ACCOUNT_STATUS_RECOVERY_APPROVAL_VERSION = "gca_account_status_recovery_approval_v1";
const ACCOUNT_STATUS_RECOVERY_VERSION = "gca_account_status_recovery_v1";
const CREDIT_USAGE_VERSION = "gca_credit_usage_v1";
const SERVICE_REQUEST_VERSION = "gca_service_request_v1";
const ACCOUNT_SERVICE_REQUEST_VERSION = "gca_account_service_request_v1";
const ACCOUNT_SERVICE_REQUEST_STATUS_VERSION =
  "gca_account_service_request_status_v1";
const ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION =
  "gca_account_service_request_followup_v1";
const ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION =
  "gca_account_service_request_cancellation_v1";
const ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION =
  "gca_account_service_delivery_receipt_v1";
const SERVICE_REQUEST_REVIEW_VERSION =
  "gca_service_request_review_v1";
const MEMBER_REVIEW_VERSION = "gca_member_review_v1";
const HOLDING_VERIFICATION_VERSION = "gca_holding_verification_v1";
const MEMBER_BENEFIT_TRANSFER_VERSION = "gca_member_benefit_transfer_v1";
const WORKER_RELEASE =
  "gca-registration-worker-2026-08-10-request-followup-v1";
const OFFICIAL_CONTACT_EMAIL = "support@gcagochina.com";
const OFFICIAL_SITE_URL = "https://gcagochina.com/";
const CHAIN_ID = 8453;
const CONTRACT_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6";
const MEMBER_BENEFIT_SOURCE_WALLET = "0x5e8f84748612b913aacc937492ac25dc5630e246";
const BASE_RPC_URL = "https://mainnet.base.org";
const BASE_BLOCKSCOUT_URL = "https://base.blockscout.com";
const BALANCE_OF_SELECTOR = "0x70a08231";
const TOKEN_DECIMALS = 18n;
const TOKEN_UNIT = 10n ** TOKEN_DECIMALS;
const HOLDER_THRESHOLD_UNITS = 10_000n * TOKEN_UNIT;
const MEMBER_THRESHOLD_UNITS = 1_000_000n * TOKEN_UNIT;
const MEMBER_BENEFIT_UNITS = 10_000n * TOKEN_UNIT;
const CREDIT_AMOUNT = 100;
const CREDIT_EXPIRY_DAYS = 180;
const ACCOUNT_STATUS_ACCESS_DAYS = 365;
const ACCOUNT_STATUS_ROTATION_GRACE_MINUTES = 15;
const ACCOUNT_STATUS_RECOVERY_REQUEST_DAYS = 7;
const ACCOUNT_STATUS_RECOVERY_CREDENTIAL_MINUTES = 24 * 60;
const ACCOUNT_SERVICE_REQUEST_DAILY_LIMIT = 5;
const ACCOUNT_SERVICE_REQUEST_HISTORY_LIMIT = 25;
const ACCOUNT_SERVICE_REQUEST_FOLLOWUP_LIMIT = 5;
const MEMBER_REFRESH_DAYS = 30;
const MEMBER_HOLD_DAYS = 30;
const HOLDING_WINDOW_MS = MEMBER_HOLD_DAYS * 86_400_000;
const RECENT_RPC_BLOCK_RANGE = 10_000;
const BLOCKSCOUT_MAX_PAGES = 20;
const BLOCKSCOUT_MAX_EVENTS = 1_000;
const MEMBER_BENEFIT_AMOUNT = "10000 GCA";
const CREDIT_SERVICE_CATALOG = {
  "liquidation-replay-report": { name: "Liquidation Replay", creditUnit: 30 },
  "risk-warning-review": { name: "Risk Warning Review", creditUnit: 10 },
  "backtest-lab-run": { name: "Backtest Lab", creditUnit: 20 },
  "entry-ready-review": { name: "ENTRY_READY Review", creditUnit: 15 },
  "position-size-calculator": { name: "Position Size Calculator", creditUnit: 5 },
  "portfolio-risk-map": { name: "Portfolio Risk Map", creditUnit: 15 },
  "risk-control-training": { name: "Risk-Control Training", creditUnit: 10 },
  "member-research-notes": { name: "Member Research Notes", creditUnit: 20 },
  "support-review-queue": { name: "Support Review Queue", creditUnit: 0 }
};
const DEFAULT_ALLOWED_ORIGINS = [
  "https://gcagochina.com",
  "https://www.gcagochina.com",
  "http://127.0.0.1:8787",
  "http://localhost:8787",
  "http://127.0.0.1:8799",
  "http://localhost:8799"
];
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const ADDRESS_RE = /^0x[a-fA-F0-9]{40}$/;
const TX_HASH_RE = /^0x[a-fA-F0-9]{64}$/;
const MEMBER_LEDGER_ID_RE = /^gca_member_[a-f0-9]{20}$/;
const RECOVERY_REQUEST_ID_RE = /^gca_recovery_request_[a-f0-9]{20}$/;
const RECOVERY_CREDENTIAL_RE = /^gca_recovery_[A-Za-z0-9_-]{43}$/;
const CLIENT_SERVICE_REQUEST_ID_RE =
  /^gca_client_req_[A-Za-z0-9_-]{22,64}$/;
const SERVICE_REQUEST_ID_RE = /^gca_service_req_[a-f0-9]{20}$/;
const CLIENT_SERVICE_FOLLOWUP_ID_RE =
  /^gca_client_followup_[A-Za-z0-9_-]{22,64}$/;
const CLIENT_SERVICE_REVIEW_ID_RE =
  /^gca_client_review_[A-Za-z0-9_-]{22,64}$/;
const OPERATOR_ID_RE = /^[a-z0-9][a-z0-9_-]{2,63}$/;
const REASON_CODE_RE = /^[a-z0-9][a-z0-9_-]{1,63}$/;
const MEMBER_REVIEW_DECISIONS = new Set(["approved", "rejected", "needs_more_information"]);
const SERVICE_REQUEST_REVIEW_DECISIONS = new Set([
  "approved",
  "rejected",
  "needs_more_information",
  "delivered"
]);
const SERVICE_REQUEST_QUEUED_STATUSES = new Set([
  "queued_operator_review",
  "queued_insufficient_credits",
  "queued_expired_credit_ledger",
  "queued_missing_credit_ledger"
]);
const HONEYPOT_FIELDS = ["website", "company", "homepage"];
const FORBIDDEN_KEY_PATTERNS = [
  "privatekey",
  "seedphrase",
  "mnemonic",
  "apisecret",
  "withdrawalpermission",
  "recoveryphrase",
  "onetimecode",
  "walletpassword",
  "verificationcode",
  "remotecontrol"
];

class ApiError extends Error {
  constructor(message, status = 400) {
    super(message);
    this.status = status;
  }
}

function jsonResponse(payload, status = 200, origin = "", env = {}) {
  const headers = {
    "content-type": "application/json; charset=utf-8",
    "cache-control": "no-store",
    ...corsHeaders(origin, env)
  };
  return new Response(JSON.stringify(payload), { status, headers });
}

function corsHeaders(origin, env = {}) {
  const allowedOrigins = getAllowedOrigins(env);
  const allowOrigin = allowedOrigins.includes(origin) ? origin : allowedOrigins[0];
  return {
    "access-control-allow-origin": allowOrigin,
    "access-control-allow-methods": "GET,POST,OPTIONS",
    "access-control-allow-headers": "content-type,authorization",
    "access-control-max-age": "86400",
    "vary": "Origin"
  };
}

function getAllowedOrigins(env = {}) {
  const configured = String(env.ALLOWED_ORIGINS || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return configured.length ? configured : DEFAULT_ALLOWED_ORIGINS;
}

function normalizeEmail(value) {
  const email = String(value || "").trim().toLowerCase();
  if (email.length > 254 || !EMAIL_RE.test(email)) {
    throw new ApiError("email must be a valid email address");
  }
  return email;
}

function normalizeWallet(value) {
  const wallet = String(value || "").trim().toLowerCase();
  if (!ADDRESS_RE.test(wallet)) {
    throw new ApiError("walletAddress must be a valid EVM address");
  }
  return wallet;
}

function isTxHash(value) {
  return TX_HASH_RE.test(String(value || "").trim());
}

function normalizeTxHash(value) {
  const transactionHash = String(value || "").trim().toLowerCase();
  if (!isTxHash(transactionHash)) {
    throw new ApiError("transactionHash must be a valid Base transaction hash");
  }
  return transactionHash;
}

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function addDaysIso(isoValue, days) {
  const date = new Date(isoValue);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function addMinutesIso(isoValue, minutes) {
  const date = new Date(isoValue);
  date.setUTCMinutes(date.getUTCMinutes() + minutes);
  return date.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function holdingDaysFromDate(value) {
  const clean = String(value || "").trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(clean)) {
    return 0;
  }
  const start = new Date(`${clean}T00:00:00Z`);
  if (Number.isNaN(start.getTime())) {
    return 0;
  }
  const today = new Date();
  const todayUtc = Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate());
  const diff = todayUtc - start.getTime();
  if (diff < 0) {
    return 0;
  }
  return Math.floor(diff / 86_400_000);
}

function rejectHoneypotFields(packet) {
  for (const field of HONEYPOT_FIELDS) {
    if (Object.prototype.hasOwnProperty.call(packet, field) && String(packet[field] || "").trim() !== "") {
      throw new ApiError("bot trap field must be empty");
    }
  }
}

function balanceOfCalldata(wallet) {
  const normalized = normalizeWallet(wallet).replace(/^0x/, "");
  return `${BALANCE_OF_SELECTOR}${normalized.padStart(64, "0")}`;
}

function unitsToGca(units) {
  const raw = BigInt(units || 0);
  const whole = raw / TOKEN_UNIT;
  const fraction = raw % TOKEN_UNIT;
  if (fraction === 0n) {
    return whole.toString();
  }
  let fractionText = fraction.toString().padStart(Number(TOKEN_DECIMALS), "0").replace(/0+$/, "");
  if (fractionText.length > 6) {
    fractionText = fractionText.slice(0, 6).replace(/0+$/, "");
  }
  return fractionText ? `${whole.toString()}.${fractionText}` : whole.toString();
}

function extractMemberEvidence(packet) {
  const evidence = packet.memberBenefitReviewEvidence && typeof packet.memberBenefitReviewEvidence === "object"
    ? packet.memberBenefitReviewEvidence
    : {};
  const holdingStartDate = String(evidence.holdingStartDate || packet.holdingStartDate || "").trim();
  const evidenceTxHash = String(evidence.evidenceTxHash || packet.evidenceTxHash || "").trim().toLowerCase();
  const holdingPeriodDaysVerified = holdingDaysFromDate(holdingStartDate);
  return {
    holdingStartDate,
    holdingPeriodDaysVerified,
    holdingPeriodPreviewEligible: holdingPeriodDaysVerified >= MEMBER_HOLD_DAYS,
    evidenceTxHash,
    evidenceTxHashFormatOk: isTxHash(evidenceTxHash),
    evidenceNote: String(evidence.evidenceNote || packet.evidenceNote || "").trim().slice(0, 500)
  };
}

function rejectForbiddenKeys(value, path = "") {
  if (Array.isArray(value)) {
    value.forEach((item, index) => rejectForbiddenKeys(item, `${path}${index}.`));
    return;
  }
  if (!value || typeof value !== "object") {
    return;
  }
  for (const [key, nested] of Object.entries(value)) {
    const normalized = key.toLowerCase().replace(/[^a-z0-9]/g, "");
    if (FORBIDDEN_KEY_PATTERNS.some((pattern) => normalized.includes(pattern))) {
      throw new ApiError(`Forbidden sensitive field is not accepted: ${path}${key}`);
    }
    rejectForbiddenKeys(nested, `${path}${key}.`);
  }
}

async function readJsonRequest(request) {
  const contentLength = Number(request.headers.get("content-length") || "0");
  if (contentLength > 16_384) {
    throw new ApiError("Request body is too large", 413);
  }
  let payload;
  try {
    payload = await request.json();
  } catch (error) {
    throw new ApiError("Request body must be valid JSON");
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new ApiError("Request body must be a JSON object");
  }
  rejectHoneypotFields(payload);
  rejectForbiddenKeys(payload);
  return payload;
}

function extractEmailRegistration(packet) {
  if (packet.packetVersion && packet.packetVersion !== EMAIL_REGISTRATION_VERSION) {
    throw new ApiError(`packetVersion must be ${EMAIL_REGISTRATION_VERSION}`);
  }
  const user = packet.user && typeof packet.user === "object" ? packet.user : {};
  const acknowledgements = packet.acknowledgements && typeof packet.acknowledgements === "object"
    ? packet.acknowledgements
    : {};
  const email = normalizeEmail(packet.email || user.email || "");
  const displayName = String(packet.displayName || user.displayName || "").trim().slice(0, 120);
  const source = String(packet.source || "register.html").trim().slice(0, 120) || "register.html";
  const language = String(packet.language || user.language || "zh-CN").trim().slice(0, 32) || "zh-CN";
  const interests = Array.isArray(packet.interests)
    ? packet.interests.map((item) => String(item || "").trim().slice(0, 64)).filter(Boolean).slice(0, 12)
    : ["gca_updates"];
  const contactConsentAccepted = Boolean(packet.contactConsentAccepted || acknowledgements.emailContactConsent);
  const securityBoundaryAccepted = Boolean(packet.securityBoundaryAccepted || acknowledgements.noSecretsNoCustody);
  if (!contactConsentAccepted) {
    throw new ApiError("email contact consent is required");
  }
  if (!securityBoundaryAccepted) {
    throw new ApiError("security boundary acknowledgement is required");
  }
  return {
    email,
    displayName,
    source,
    language,
    interests,
    contactConsentAccepted,
    securityBoundaryAccepted
  };
}

function extractContactSuppression(packet) {
  if (packet.packetVersion && packet.packetVersion !== CONTACT_SUPPRESSION_VERSION) {
    throw new ApiError(`packetVersion must be ${CONTACT_SUPPRESSION_VERSION}`);
  }
  const acknowledgements = packet.acknowledgements && typeof packet.acknowledgements === "object"
    ? packet.acknowledgements
    : {};
  const email = normalizeEmail(packet.email || "");
  const reason = String(packet.reason || "unsubscribe_request").trim().slice(0, 160) || "unsubscribe_request";
  const source = String(packet.source || "unsubscribe.html").trim().slice(0, 120) || "unsubscribe.html";
  const contactSuppressionRequested = Boolean(packet.contactSuppressionRequested || acknowledgements.contactSuppressionRequested);
  const securityBoundaryAccepted = Boolean(packet.securityBoundaryAccepted || acknowledgements.noSecretsNoCustody);
  if (!contactSuppressionRequested) {
    throw new ApiError("contact suppression acknowledgement is required");
  }
  if (!securityBoundaryAccepted) {
    throw new ApiError("security boundary acknowledgement is required");
  }
  return {
    email,
    reason,
    source,
    contactSuppressionRequested,
    securityBoundaryAccepted
  };
}

function extractMemberAccess(packet) {
  const packetVersion = String(packet.packetVersion || MEMBER_ACCESS_VERSION).trim();
  if (![MEMBER_ACCESS_VERSION, LEGACY_MEMBER_ACCESS_VERSION].includes(packetVersion)) {
    throw new ApiError(
      `packetVersion must be ${MEMBER_ACCESS_VERSION} or ${LEGACY_MEMBER_ACCESS_VERSION}`
    );
  }
  const user = packet.user && typeof packet.user === "object" ? packet.user : {};
  const acknowledgements = packet.acknowledgements && typeof packet.acknowledgements === "object"
    ? packet.acknowledgements
    : {};
  const email = normalizeEmail(packet.email || user.email || "");
  const walletAddress = normalizeWallet(packet.walletAddress || user.walletAddress || "");
  const displayName = String(packet.displayName || user.displayName || "").trim().slice(0, 120);
  const source = String(packet.source || "gca/member-access").trim().slice(0, 120) || "gca/member-access";
  const language = String(packet.language || user.language || "zh-CN").trim().slice(0, 32) || "zh-CN";
  const programIntent = String(packet.programIntent || "gca_member").trim().slice(0, 64) || "gca_member";
  const statusAccessToken = String(packet.statusAccessToken || "").trim();
  const contactConsentAccepted = Boolean(packet.contactConsentAccepted || acknowledgements.emailContactConsent);
  const securityBoundaryAccepted = Boolean(packet.securityBoundaryAccepted || acknowledgements.noSecretsNoCustody);
  const termsAccepted = Boolean(packet.termsAccepted || acknowledgements.memberAccessTerms || acknowledgements.preRegistrationOnly);
  if (!contactConsentAccepted) {
    throw new ApiError("email contact consent is required");
  }
  if (!securityBoundaryAccepted) {
    throw new ApiError("security boundary acknowledgement is required");
  }
  if (!termsAccepted) {
    throw new ApiError("member access terms acknowledgement is required");
  }
  if (packetVersion === MEMBER_ACCESS_VERSION && !isStatusAccessToken(statusAccessToken)) {
    throw new ApiError("statusAccessToken must be a valid device status access key");
  }
  return {
    packetVersion,
    email,
    walletAddress,
    displayName,
    source,
    language,
    programIntent,
    contactConsentAccepted,
    securityBoundaryAccepted,
    termsAccepted,
    statusAccessToken,
    memberEvidence: extractMemberEvidence(packet)
  };
}

function extractAccountStatus(packet) {
  if (packet.packetVersion && packet.packetVersion !== ACCOUNT_STATUS_VERSION) {
    throw new ApiError(`packetVersion must be ${ACCOUNT_STATUS_VERSION}`);
  }
  const statusAccessToken = String(packet.statusAccessToken || "").trim();
  if (!isStatusAccessToken(statusAccessToken)) {
    throw new ApiError("statusAccessToken must be a valid device status access key", 401);
  }
  return { statusAccessToken };
}

function extractAccountStatusRotation(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_STATUS_ROTATION_VERSION
  ) {
    throw new ApiError(`packetVersion must be ${ACCOUNT_STATUS_ROTATION_VERSION}`);
  }
  const currentStatusAccessToken = String(
    packet.currentStatusAccessToken || ""
  ).trim();
  const newStatusAccessToken = String(packet.newStatusAccessToken || "").trim();
  if (!isStatusAccessToken(currentStatusAccessToken)) {
    throw new ApiError(
      "currentStatusAccessToken must be a valid device status access key",
      401
    );
  }
  if (!isStatusAccessToken(newStatusAccessToken)) {
    throw new ApiError(
      "newStatusAccessToken must be a valid device status access key"
    );
  }
  if (currentStatusAccessToken === newStatusAccessToken) {
    throw new ApiError("newStatusAccessToken must differ from the current key");
  }
  return { currentStatusAccessToken, newStatusAccessToken };
}

function extractAccountStatusRecoveryRequest(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_STATUS_RECOVERY_REQUEST_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_STATUS_RECOVERY_REQUEST_VERSION}`
    );
  }
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  const email = normalizeEmail(packet.email || "");
  const walletAddress = normalizeWallet(packet.walletAddress || "");
  const newStatusAccessToken = String(
    packet.newStatusAccessToken || ""
  ).trim();
  const officialEmailReviewAccepted = Boolean(
    acknowledgements.officialEmailReviewAccepted
  );
  const securityBoundaryAccepted = Boolean(
    acknowledgements.noSecretsNoCustody
  );
  if (!isStatusAccessToken(newStatusAccessToken)) {
    throw new ApiError(
      "newStatusAccessToken must be a valid device status access key"
    );
  }
  if (!officialEmailReviewAccepted) {
    throw new ApiError(
      "registered-email support review acknowledgement is required"
    );
  }
  if (!securityBoundaryAccepted) {
    throw new ApiError("security boundary acknowledgement is required");
  }
  return {
    email,
    walletAddress,
    newStatusAccessToken,
    source:
      String(
        packet.source || "gca-account-status-recovery-request"
      )
        .trim()
        .slice(0, 120) || "gca-account-status-recovery-request"
  };
}

function extractAccountStatusRecoveryApproval(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_STATUS_RECOVERY_APPROVAL_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_STATUS_RECOVERY_APPROVAL_VERSION}`
    );
  }
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  const recoveryRequestId = String(
    packet.recoveryRequestId || ""
  )
    .trim()
    .toLowerCase();
  const registeredEmail = normalizeEmail(packet.registeredEmail || "");
  const operatorId = String(packet.operatorId || "")
    .trim()
    .toLowerCase();
  const reasonCode = String(packet.reasonCode || "")
    .trim()
    .toLowerCase();
  const registeredEmailOwnershipVerified = Boolean(
    acknowledgements.registeredEmailOwnershipVerified
  );
  const manualIdentityReviewCompleted = Boolean(
    acknowledgements.manualIdentityReviewCompleted
  );
  const noSecretsRequested = Boolean(
    acknowledgements.noSecretsRequested
  );
  const noWalletAction = Boolean(acknowledgements.noWalletAction);
  if (!RECOVERY_REQUEST_ID_RE.test(recoveryRequestId)) {
    throw new ApiError("recoveryRequestId must be a valid GCA recovery request id");
  }
  if (!OPERATOR_ID_RE.test(operatorId)) {
    throw new ApiError(
      "operatorId must be a short lowercase operator identifier"
    );
  }
  if (!REASON_CODE_RE.test(reasonCode)) {
    throw new ApiError("reasonCode must be a short lowercase identifier");
  }
  if (!registeredEmailOwnershipVerified) {
    throw new ApiError(
      "registered email ownership verification acknowledgement is required"
    );
  }
  if (!manualIdentityReviewCompleted) {
    throw new ApiError("manual identity review acknowledgement is required");
  }
  if (!noSecretsRequested) {
    throw new ApiError("no-secrets acknowledgement is required");
  }
  if (!noWalletAction) {
    throw new ApiError("no-wallet-action acknowledgement is required");
  }
  return {
    recoveryRequestId,
    registeredEmail,
    operatorId,
    reasonCode,
    source:
      String(
        packet.source || "gca-account-status-recovery-operator"
      )
        .trim()
        .slice(0, 120) || "gca-account-status-recovery-operator"
  };
}

function extractAccountStatusRecovery(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_STATUS_RECOVERY_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_STATUS_RECOVERY_VERSION}`
    );
  }
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  const recoveryRequestId = String(
    packet.recoveryRequestId || ""
  )
    .trim()
    .toLowerCase();
  const recoveryCredential = String(
    packet.recoveryCredential || ""
  ).trim();
  const newStatusAccessToken = String(
    packet.newStatusAccessToken || ""
  ).trim();
  if (!RECOVERY_REQUEST_ID_RE.test(recoveryRequestId)) {
    throw new ApiError("recoveryRequestId must be a valid GCA recovery request id");
  }
  if (!RECOVERY_CREDENTIAL_RE.test(recoveryCredential)) {
    throw new ApiError("recoveryCredential is invalid", 401);
  }
  if (!isStatusAccessToken(newStatusAccessToken)) {
    throw new ApiError(
      "newStatusAccessToken must be a valid device status access key"
    );
  }
  if (!Boolean(acknowledgements.credentialOnlyRecovery)) {
    throw new ApiError("credential-only recovery acknowledgement is required");
  }
  return {
    recoveryRequestId,
    recoveryCredential,
    newStatusAccessToken
  };
}

function extractCreditUsage(packet) {
  if (packet.packetVersion && packet.packetVersion !== CREDIT_USAGE_VERSION) {
    throw new ApiError(`packetVersion must be ${CREDIT_USAGE_VERSION}`);
  }
  const creditLedgerId = String(packet.creditLedgerId || "").trim();
  const serviceId = String(packet.serviceId || "").trim();
  const service = CREDIT_SERVICE_CATALOG[serviceId];
  if (!creditLedgerId) {
    throw new ApiError("creditLedgerId is required");
  }
  if (!service) {
    throw new ApiError("serviceId is not supported");
  }
  const rawAmount = packet.creditAmountUsed ?? service.creditUnit;
  const creditAmountUsed = Number(rawAmount);
  if (!Number.isInteger(creditAmountUsed) || creditAmountUsed < 0 || creditAmountUsed > CREDIT_AMOUNT) {
    throw new ApiError("creditAmountUsed must be an integer between 0 and 100");
  }
  if (creditAmountUsed === 0 && service.creditUnit !== 0) {
    throw new ApiError("creditAmountUsed must be greater than 0 for this service");
  }
  const walletAddress = String(packet.walletAddress || "").trim()
    ? normalizeWallet(packet.walletAddress)
    : "";
  return {
    creditLedgerId,
    serviceId,
    serviceName: service.name,
    creditAmountUsed,
    walletAddress,
    operatorNote: String(packet.operatorNote || "").trim().slice(0, 500),
    source: String(packet.source || "gca-credit-usage-operator").trim().slice(0, 120) || "gca-credit-usage-operator"
  };
}

function extractServiceRequest(packet) {
  if (packet.packetVersion && packet.packetVersion !== SERVICE_REQUEST_VERSION) {
    throw new ApiError(`packetVersion must be ${SERVICE_REQUEST_VERSION}`);
  }
  const acknowledgements = packet.acknowledgements && typeof packet.acknowledgements === "object"
    ? packet.acknowledgements
    : {};
  const email = normalizeEmail(packet.email || "");
  const serviceId = String(packet.serviceId || "").trim();
  const service = CREDIT_SERVICE_CATALOG[serviceId];
  if (!service) {
    throw new ApiError("serviceId is not supported");
  }
  const noSecrets = Boolean(packet.securityBoundaryAccepted || acknowledgements.noSecretsNoCustody);
  const manualReview = Boolean(packet.manualReviewAccepted || acknowledgements.manualReviewOnly);
  const noTradingPermission = Boolean(packet.noTradingPermissionAccepted || acknowledgements.noTradingPermission);
  if (!noSecrets) {
    throw new ApiError("security boundary acknowledgement is required");
  }
  if (!manualReview) {
    throw new ApiError("manual review acknowledgement is required");
  }
  if (!noTradingPermission) {
    throw new ApiError("no trading permission acknowledgement is required");
  }
  const walletAddress = String(packet.walletAddress || "").trim()
    ? normalizeWallet(packet.walletAddress)
    : "";
  const creditLedgerId = String(packet.creditLedgerId || "").trim();
  const rawCreditHold = packet.requestedCreditHold === undefined || packet.requestedCreditHold === ""
    ? service.creditUnit
    : packet.requestedCreditHold;
  const requestedCreditHold = Number(rawCreditHold);
  if (!Number.isInteger(requestedCreditHold) || requestedCreditHold < 0 || requestedCreditHold > CREDIT_AMOUNT) {
    throw new ApiError("requestedCreditHold must be an integer between 0 and 100");
  }
  if (requestedCreditHold === 0 && service.creditUnit !== 0) {
    throw new ApiError("requestedCreditHold must be greater than 0 for this service");
  }
  return {
    email,
    walletAddress,
    creditLedgerId,
    serviceId,
    serviceName: service.name,
    requestedCreditHold,
    requestTitle: String(packet.requestTitle || "").trim().slice(0, 140),
    requestSummary: String(packet.requestSummary || "").trim().slice(0, 1200),
    marketContext: String(packet.marketContext || "").trim().slice(0, 500),
    preferredLanguage: String(packet.preferredLanguage || "zh-CN").trim().slice(0, 32) || "zh-CN",
    source: String(packet.source || "gca-service-request-operator").trim().slice(0, 120) || "gca-service-request-operator"
  };
}

function extractAccountServiceRequest(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_SERVICE_REQUEST_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_SERVICE_REQUEST_VERSION}`
    );
  }
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  const statusAccessToken = String(packet.statusAccessToken || "").trim();
  const clientRequestId = String(packet.clientRequestId || "").trim();
  const serviceId = String(packet.serviceId || "").trim();
  const service = CREDIT_SERVICE_CATALOG[serviceId];
  const requestTitle = String(packet.requestTitle || "").trim().slice(0, 140);
  const requestSummary = String(packet.requestSummary || "")
    .trim()
    .slice(0, 1200);
  const marketContext = String(packet.marketContext || "").trim().slice(0, 500);
  const preferredLanguage = String(
    packet.preferredLanguage || "zh-CN"
  ).trim();

  if (!isStatusAccessToken(statusAccessToken)) {
    throw new ApiError(
      "statusAccessToken must be a valid device status access key",
      401
    );
  }
  if (!CLIENT_SERVICE_REQUEST_ID_RE.test(clientRequestId)) {
    throw new ApiError("clientRequestId must be a valid service request id");
  }
  if (!service) {
    throw new ApiError("serviceId is not supported");
  }
  if (requestTitle.length < 3) {
    throw new ApiError("requestTitle must contain at least 3 characters");
  }
  if (requestSummary.length < 20) {
    throw new ApiError("requestSummary must contain at least 20 characters");
  }
  if (!["en", "zh-CN"].includes(preferredLanguage)) {
    throw new ApiError("preferredLanguage must be en or zh-CN");
  }
  if (!Boolean(acknowledgements.noSecretsNoCustody)) {
    throw new ApiError("security boundary acknowledgement is required");
  }
  if (!Boolean(acknowledgements.manualReviewOnly)) {
    throw new ApiError("manual review acknowledgement is required");
  }
  if (!Boolean(acknowledgements.noTradingPermission)) {
    throw new ApiError("no trading permission acknowledgement is required");
  }

  return {
    statusAccessToken,
    clientRequestId,
    serviceId,
    serviceName: service.name,
    requestedCreditHold: service.creditUnit,
    requestTitle,
    requestSummary,
    marketContext,
    preferredLanguage,
    source: "gca-member-access-account-service-request"
  };
}

function extractAccountServiceRequestStatus(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_SERVICE_REQUEST_STATUS_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_SERVICE_REQUEST_STATUS_VERSION}`
    );
  }
  const statusAccessToken = String(packet.statusAccessToken || "").trim();
  if (!isStatusAccessToken(statusAccessToken)) {
    throw new ApiError(
      "statusAccessToken must be a valid device status access key",
      401
    );
  }
  return { statusAccessToken };
}

function extractAccountServiceRequestFollowup(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION}`
    );
  }
  const statusAccessToken = String(packet.statusAccessToken || "").trim();
  const serviceRequestId = String(packet.serviceRequestId || "")
    .trim()
    .toLowerCase();
  const clientFollowupId = String(packet.clientFollowupId || "").trim();
  const responseText = String(packet.responseText || "")
    .trim()
    .slice(0, 1200);
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  if (!isStatusAccessToken(statusAccessToken)) {
    throw new ApiError(
      "statusAccessToken must be a valid device status access key",
      401
    );
  }
  if (!SERVICE_REQUEST_ID_RE.test(serviceRequestId)) {
    throw new ApiError(
      "serviceRequestId must be a valid GCA service request id"
    );
  }
  if (!CLIENT_SERVICE_FOLLOWUP_ID_RE.test(clientFollowupId)) {
    throw new ApiError(
      "clientFollowupId must be a valid service follow-up id"
    );
  }
  if (responseText.length < 20) {
    throw new ApiError("responseText must contain at least 20 characters");
  }
  if (!Boolean(acknowledgements.noSecretsNoCustody)) {
    throw new ApiError(
      "no-secrets and no-custody acknowledgement is required"
    );
  }
  if (!Boolean(acknowledgements.manualReviewOnly)) {
    throw new ApiError("manual review acknowledgement is required");
  }
  if (!Boolean(acknowledgements.noCreditOrWalletEffect)) {
    throw new ApiError(
      "no credit or wallet effect acknowledgement is required"
    );
  }
  return {
    statusAccessToken,
    serviceRequestId,
    clientFollowupId,
    responseText,
    source: "gca-member-access-service-request-followup"
  };
}

function extractAccountServiceRequestCancellation(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION}`
    );
  }
  const statusAccessToken = String(packet.statusAccessToken || "").trim();
  const serviceRequestId = String(packet.serviceRequestId || "")
    .trim()
    .toLowerCase();
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  if (!isStatusAccessToken(statusAccessToken)) {
    throw new ApiError(
      "statusAccessToken must be a valid device status access key",
      401
    );
  }
  if (!SERVICE_REQUEST_ID_RE.test(serviceRequestId)) {
    throw new ApiError(
      "serviceRequestId must be a valid GCA service request id"
    );
  }
  if (!Boolean(acknowledgements.cancelQueuedRequest)) {
    throw new ApiError("queued request cancellation acknowledgement is required");
  }
  if (!Boolean(acknowledgements.noCreditOrWalletEffect)) {
    throw new ApiError(
      "no credit or wallet effect acknowledgement is required"
    );
  }
  return { statusAccessToken, serviceRequestId };
}

function extractAccountServiceDeliveryReceipt(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION}`
    );
  }
  const statusAccessToken = String(packet.statusAccessToken || "").trim();
  const serviceRequestId = String(packet.serviceRequestId || "")
    .trim()
    .toLowerCase();
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  if (!isStatusAccessToken(statusAccessToken)) {
    throw new ApiError(
      "statusAccessToken must be a valid device status access key",
      401
    );
  }
  if (!SERVICE_REQUEST_ID_RE.test(serviceRequestId)) {
    throw new ApiError(
      "serviceRequestId must be a valid GCA service request id"
    );
  }
  if (!Boolean(acknowledgements.deliveryReceived)) {
    throw new ApiError("delivery received acknowledgement is required");
  }
  if (!Boolean(acknowledgements.noCreditOrWalletEffect)) {
    throw new ApiError(
      "no credit or wallet effect acknowledgement is required"
    );
  }
  return { statusAccessToken, serviceRequestId };
}

function extractServiceRequestReview(packet) {
  if (
    packet.packetVersion &&
    packet.packetVersion !== SERVICE_REQUEST_REVIEW_VERSION
  ) {
    throw new ApiError(
      `packetVersion must be ${SERVICE_REQUEST_REVIEW_VERSION}`
    );
  }
  const acknowledgements =
    packet.acknowledgements && typeof packet.acknowledgements === "object"
      ? packet.acknowledgements
      : {};
  const serviceRequestId = String(packet.serviceRequestId || "")
    .trim()
    .toLowerCase();
  const clientReviewId = String(packet.clientReviewId || "").trim();
  const decision = String(packet.decision || "").trim().toLowerCase();
  const reasonCode = String(packet.reasonCode || "")
    .trim()
    .toLowerCase();
  const reviewerId = String(packet.reviewerId || "gca-operator")
    .trim()
    .toLowerCase();
  const operatorNote = String(packet.operatorNote || "")
    .trim()
    .slice(0, 500);
  const memberPrompt = String(packet.memberPrompt || "")
    .trim()
    .slice(0, 500);
  const deliveryReference = String(packet.deliveryReference || "")
    .trim()
    .slice(0, 300);
  const manualReviewCompleted = Boolean(
    acknowledgements.manualReviewCompleted
  );
  const noSecretsNoCustody = Boolean(
    acknowledgements.noSecretsNoCustody
  );
  const noTradingPermission = Boolean(
    acknowledgements.noTradingPermission
  );
  const deliveryCompleted = Boolean(
    acknowledgements.deliveryCompleted
  );
  const creditSettlementAccepted = Boolean(
    acknowledgements.creditSettlementAccepted
  );

  if (!SERVICE_REQUEST_ID_RE.test(serviceRequestId)) {
    throw new ApiError(
      "serviceRequestId must be a valid GCA service request id"
    );
  }
  if (!CLIENT_SERVICE_REVIEW_ID_RE.test(clientReviewId)) {
    throw new ApiError(
      "clientReviewId must be a valid service review id"
    );
  }
  if (!SERVICE_REQUEST_REVIEW_DECISIONS.has(decision)) {
    throw new ApiError(
      "decision must be approved, rejected, needs_more_information, or delivered"
    );
  }
  if (!REASON_CODE_RE.test(reasonCode)) {
    throw new ApiError(
      "reasonCode must be a short lowercase identifier"
    );
  }
  if (!OPERATOR_ID_RE.test(reviewerId)) {
    throw new ApiError(
      "reviewerId must be a short lowercase operator identifier"
    );
  }
  if (!manualReviewCompleted) {
    throw new ApiError(
      "manual review completion acknowledgement is required"
    );
  }
  if (!noSecretsNoCustody) {
    throw new ApiError(
      "no-secrets and no-custody acknowledgement is required"
    );
  }
  if (!noTradingPermission) {
    throw new ApiError(
      "no trading permission acknowledgement is required"
    );
  }
  if (decision === "delivered" && !deliveryCompleted) {
    throw new ApiError(
      "delivery completion acknowledgement is required"
    );
  }
  if (decision === "delivered" && !creditSettlementAccepted) {
    throw new ApiError(
      "credit settlement acknowledgement is required"
    );
  }
  if (decision === "delivered" && !deliveryReference) {
    throw new ApiError(
      "deliveryReference is required when delivery is recorded"
    );
  }
  if (decision === "needs_more_information" && memberPrompt.length < 10) {
    throw new ApiError(
      "memberPrompt with at least 10 characters is required when more information is requested"
    );
  }
  if (decision !== "needs_more_information" && memberPrompt) {
    throw new ApiError(
      "memberPrompt is only accepted when decision is needs_more_information"
    );
  }

  return {
    serviceRequestId,
    clientReviewId,
    decision,
    reasonCode,
    reviewerId,
    operatorNote,
    memberPrompt,
    deliveryReference,
    deliveryCompleted,
    creditSettlementAccepted,
    source:
      String(
        packet.source || "gca-service-request-review-operator"
      )
        .trim()
        .slice(0, 120) ||
      "gca-service-request-review-operator"
  };
}

function extractMemberReview(packet) {
  if (packet.packetVersion && packet.packetVersion !== MEMBER_REVIEW_VERSION) {
    throw new ApiError(`packetVersion must be ${MEMBER_REVIEW_VERSION}`);
  }
  const acknowledgements = packet.acknowledgements && typeof packet.acknowledgements === "object"
    ? packet.acknowledgements
    : {};
  const memberLedgerId = String(packet.memberLedgerId || "").trim().toLowerCase();
  const decision = String(packet.decision || "").trim().toLowerCase();
  const reasonCode = String(packet.reasonCode || "").trim().toLowerCase();
  const reviewerId = String(packet.reviewerId || "gca-operator").trim().toLowerCase();
  const manualReviewAccepted = (
    packet.manualReviewAccepted === true ||
    acknowledgements.manualEvidenceReviewCompleted === true
  );
  const noAutomaticTransferAccepted = (
    packet.noAutomaticTransferAccepted === true ||
    acknowledgements.noAutomaticTokenTransfer === true
  );
  if (!MEMBER_LEDGER_ID_RE.test(memberLedgerId)) {
    throw new ApiError("memberLedgerId must be a valid GCA member ledger id");
  }
  if (!MEMBER_REVIEW_DECISIONS.has(decision)) {
    throw new ApiError("decision must be approved, rejected, or needs_more_information");
  }
  if (!REASON_CODE_RE.test(reasonCode)) {
    throw new ApiError("reasonCode must be a short lowercase identifier");
  }
  if (!OPERATOR_ID_RE.test(reviewerId)) {
    throw new ApiError("reviewerId must be a short lowercase operator identifier");
  }
  if (!manualReviewAccepted) {
    throw new ApiError("manual evidence review acknowledgement is required");
  }
  if (!noAutomaticTransferAccepted) {
    throw new ApiError("no automatic token transfer acknowledgement is required");
  }
  return {
    memberLedgerId,
    decision,
    reasonCode,
    reviewerId,
    operatorNote: String(packet.operatorNote || "").trim().slice(0, 500),
    source: String(packet.source || "gca-member-review-operator").trim().slice(0, 120)
      || "gca-member-review-operator"
  };
}

function extractMemberBenefitTransfer(packet) {
  if (packet.packetVersion && packet.packetVersion !== MEMBER_BENEFIT_TRANSFER_VERSION) {
    throw new ApiError(`packetVersion must be ${MEMBER_BENEFIT_TRANSFER_VERSION}`);
  }
  const acknowledgements = packet.acknowledgements && typeof packet.acknowledgements === "object"
    ? packet.acknowledgements
    : {};
  const memberLedgerId = String(packet.memberLedgerId || "").trim().toLowerCase();
  const transactionHash = normalizeTxHash(
    packet.transactionHash || packet.memberBenefitTransferTx || ""
  );
  const reviewerId = String(packet.reviewerId || "gca-operator").trim().toLowerCase();
  const reasonCode = String(
    packet.reasonCode || "manual_reserve_transfer_verified"
  ).trim().toLowerCase();
  const manualTransferCompleted = (
    packet.manualTransferCompleted === true ||
    acknowledgements.manualReserveTransferCompleted === true
  );
  const publicEvidenceAccepted = (
    packet.publicEvidenceAccepted === true ||
    acknowledgements.transactionEvidencePublic === true
  );
  const noAutomaticTransferAccepted = (
    packet.noAutomaticTransferAccepted === true ||
    acknowledgements.noAutomaticTokenTransfer === true
  );
  if (!MEMBER_LEDGER_ID_RE.test(memberLedgerId)) {
    throw new ApiError("memberLedgerId must be a valid GCA member ledger id");
  }
  if (!OPERATOR_ID_RE.test(reviewerId)) {
    throw new ApiError("reviewerId must be a short lowercase operator identifier");
  }
  if (!REASON_CODE_RE.test(reasonCode)) {
    throw new ApiError("reasonCode must be a short lowercase identifier");
  }
  if (!manualTransferCompleted) {
    throw new ApiError("manual reserve transfer completion acknowledgement is required");
  }
  if (!publicEvidenceAccepted) {
    throw new ApiError("public transaction evidence acknowledgement is required");
  }
  if (!noAutomaticTransferAccepted) {
    throw new ApiError("no automatic token transfer acknowledgement is required");
  }
  return {
    memberLedgerId,
    transactionHash,
    reviewerId,
    reasonCode,
    operatorNote: String(packet.operatorNote || "").trim().slice(0, 500),
    source: String(packet.source || "gca-member-benefit-transfer-operator").trim().slice(0, 120)
      || "gca-member-benefit-transfer-operator"
  };
}

async function sha256Hex(value) {
  const data = new TextEncoder().encode(value);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

async function stableId(prefix, ...parts) {
  const digest = await sha256Hex(parts.map((part) => String(part).trim().toLowerCase()).join("|"));
  return `${prefix}_${digest.slice(0, 20)}`;
}

function randomCredential(prefix) {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  const binary = Array.from(
    bytes,
    (byte) => String.fromCharCode(byte)
  ).join("");
  const encoded = btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/g, "");
  return `${prefix}${encoded}`;
}

async function optionalIpHash(request, env) {
  const salt = String(env.PRIVACY_HASH_SALT || "").trim();
  const ip = request.headers.get("cf-connecting-ip") || "";
  if (!salt || !ip) {
    return null;
  }
  return sha256Hex(`${salt}|${ip}`);
}

function blockTagFromNumber(blockNumber) {
  return `0x${Number(blockNumber).toString(16)}`;
}

function addressTopic(walletAddress) {
  return `0x${normalizeWallet(walletAddress).slice(2).padStart(64, "0")}`;
}

async function baseRpcRequest(method, params, env) {
  const rpcUrl = String(env.BASE_RPC_URL || BASE_RPC_URL).trim() || BASE_RPC_URL;
  const payload = {
    jsonrpc: "2.0",
    id: Date.now(),
    method,
    params
  };
  let response;
  try {
    response = await fetch(rpcUrl, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        "user-agent": "gca-registration-worker/1.0"
      },
      body: JSON.stringify(payload)
    });
  } catch (error) {
    throw new ApiError("Base RPC read failed", 502);
  }
  if (!response.ok) {
    throw new ApiError("Base RPC returned an error status", 502);
  }
  let body;
  try {
    body = await response.json();
  } catch (error) {
    throw new ApiError("Base RPC returned invalid JSON", 502);
  }
  if (body && body.error) {
    throw new ApiError("Base RPC returned an error", 502);
  }
  if (!body || !Object.prototype.hasOwnProperty.call(body, "result")) {
    throw new ApiError("Base RPC response is missing result", 502);
  }
  return body.result;
}

async function readGcaBalanceUnits(walletAddress, env, blockTag = "latest") {
  const result = String(await baseRpcRequest(
    "eth_call",
    [
      {
        to: CONTRACT_ADDRESS,
        data: balanceOfCalldata(walletAddress)
      },
      blockTag
    ],
    env
  ) || "0x0");
  if (!/^0x[0-9a-fA-F]*$/.test(result)) {
    throw new ApiError("Base RPC returned an invalid balance result", 502);
  }
  return BigInt(result || "0x0");
}

async function readBlockSnapshot(blockTag, env) {
  const block = await baseRpcRequest("eth_getBlockByNumber", [blockTag, false], env);
  if (!block || typeof block !== "object" || Array.isArray(block)) {
    throw new ApiError("Base RPC returned an invalid block snapshot", 502);
  }
  let blockNumber;
  let timestampSeconds;
  try {
    blockNumber = parseRpcQuantity(block.number, "Base block number");
    timestampSeconds = parseRpcQuantity(block.timestamp, "Base block timestamp");
  } catch (error) {
    throw new ApiError("Base RPC returned invalid block metadata", 502);
  }
  const blockHash = String(block.hash || "").trim().toLowerCase();
  if (!TX_HASH_RE.test(blockHash)) {
    throw new ApiError("Base RPC returned an invalid block hash", 502);
  }
  return {
    blockNumber,
    blockTag: blockTagFromNumber(blockNumber),
    blockHash,
    timestampMs: timestampSeconds * 1_000
  };
}

async function readRecentGcaTransferEvents(walletAddress, snapshot, env) {
  const fromBlockNumber = Math.max(0, snapshot.blockNumber - (RECENT_RPC_BLOCK_RANGE - 1));
  const fromBlockTag = blockTagFromNumber(fromBlockNumber);
  const walletTopic = addressTopic(walletAddress);
  const [outgoingLogs, incomingLogs] = await Promise.all([
    baseRpcRequest(
      "eth_getLogs",
      [{
        address: CONTRACT_ADDRESS,
        fromBlock: fromBlockTag,
        toBlock: snapshot.blockTag,
        topics: [TRANSFER_EVENT_TOPIC, walletTopic]
      }],
      env
    ),
    baseRpcRequest(
      "eth_getLogs",
      [{
        address: CONTRACT_ADDRESS,
        fromBlock: fromBlockTag,
        toBlock: snapshot.blockTag,
        topics: [TRANSFER_EVENT_TOPIC, null, walletTopic]
      }],
      env
    )
  ]);
  if (!Array.isArray(outgoingLogs) || !Array.isArray(incomingLogs)) {
    throw new ApiError("Base RPC returned invalid transfer logs", 502);
  }
  const wallet = normalizeWallet(walletAddress);
  const events = [];
  try {
    for (const rawLog of [...outgoingLogs, ...incomingLogs]) {
      const event = normalizeRpcTransferLog(rawLog, CONTRACT_ADDRESS);
      if (event.fromAddress === wallet || event.toAddress === wallet) {
        events.push(event);
      }
    }
  } catch (error) {
    throw new ApiError("Base RPC returned malformed GCA transfer history", 502);
  }
  return dedupeTransferEvents(events);
}

function blockscoutHistoryUrl(walletAddress, env, cursor = null) {
  let baseUrl;
  try {
    baseUrl = new URL(String(env.BASE_BLOCKSCOUT_URL || BASE_BLOCKSCOUT_URL).trim() || BASE_BLOCKSCOUT_URL);
  } catch (error) {
    throw new ApiError("Base Blockscout URL is invalid", 503);
  }
  if (baseUrl.protocol !== "https:") {
    throw new ApiError("Base Blockscout URL must use HTTPS", 503);
  }
  const url = new URL(
    `/api/v2/addresses/${normalizeWallet(walletAddress)}/token-transfers`,
    baseUrl
  );
  url.searchParams.set("type", "ERC-20");
  url.searchParams.set("token", CONTRACT_ADDRESS);
  if (cursor && typeof cursor === "object" && !Array.isArray(cursor)) {
    for (const [key, value] of Object.entries(cursor)) {
      if (
        /^[a-z0-9_]+$/i.test(key) &&
        (typeof value === "string" || typeof value === "number")
      ) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

async function readBlockscoutGcaTransferEvents(walletAddress, windowStartMs, snapshot, env) {
  const events = [];
  const seenCursors = new Set();
  let cursor = null;
  let historyComplete = false;
  let previousBlockNumber = Number.MAX_SAFE_INTEGER;

  for (let page = 0; page < BLOCKSCOUT_MAX_PAGES; page += 1) {
    let response;
    try {
      response = await fetch(blockscoutHistoryUrl(walletAddress, env, cursor), {
        method: "GET",
        headers: {
          accept: "application/json",
          "user-agent": "gca-registration-worker/1.0"
        }
      });
    } catch (error) {
      throw new ApiError("Base Blockscout history read failed", 502);
    }
    if (!response.ok) {
      throw new ApiError("Base Blockscout returned an error status", 502);
    }
    let body;
    try {
      body = await response.json();
    } catch (error) {
      throw new ApiError("Base Blockscout returned invalid JSON", 502);
    }
    if (!body || !Array.isArray(body.items)) {
      throw new ApiError("Base Blockscout returned an invalid transfer page", 502);
    }

    let reachedWindowStart = false;
    try {
      for (const item of body.items) {
        const event = normalizeBlockscoutTransfer(item, CONTRACT_ADDRESS);
        if (event.blockNumber > previousBlockNumber) {
          throw new Error("Blockscout transfer order is not newest-first");
        }
        previousBlockNumber = event.blockNumber;
        if (event.timestampMs <= windowStartMs) {
          reachedWindowStart = true;
        }
        if (
          event.timestampMs >= windowStartMs &&
          event.timestampMs <= snapshot.timestampMs &&
          event.blockNumber <= snapshot.blockNumber
        ) {
          events.push(event);
        }
      }
    } catch (error) {
      throw new ApiError("Base Blockscout returned malformed GCA transfer history", 502);
    }
    if (events.length > BLOCKSCOUT_MAX_EVENTS) {
      throw new ApiError("GCA holding history exceeds the verification event limit", 409);
    }

    const nextCursor = body.next_page_params;
    if (reachedWindowStart || !nextCursor) {
      historyComplete = true;
      break;
    }
    if (typeof nextCursor !== "object" || Array.isArray(nextCursor)) {
      throw new ApiError("Base Blockscout returned an invalid pagination cursor", 502);
    }
    const cursorKey = JSON.stringify(
      Object.entries(nextCursor).sort(([left], [right]) => left.localeCompare(right))
    );
    if (seenCursors.has(cursorKey)) {
      throw new ApiError("Base Blockscout returned a repeated pagination cursor", 502);
    }
    seenCursors.add(cursorKey);
    cursor = nextCursor;
  }

  if (!historyComplete) {
    throw new ApiError("GCA holding history exceeds the verification page limit", 409);
  }
  return {
    events,
    historyComplete
  };
}

async function verifyGcaHoldingWindow(memberRow, env) {
  const snapshot = await readBlockSnapshot("safe", env);
  const windowStartMs = snapshot.timestampMs - HOLDING_WINDOW_MS;
  const [currentBalance, rpcEvents, blockscoutHistory] = await Promise.all([
    readGcaBalanceUnits(memberRow.wallet_address, env, snapshot.blockTag),
    readRecentGcaTransferEvents(memberRow.wallet_address, snapshot, env),
    readBlockscoutGcaTransferEvents(memberRow.wallet_address, windowStartMs, snapshot, env)
  ]);
  let allEvents;
  let reconstruction;
  try {
    allEvents = dedupeTransferEvents([...blockscoutHistory.events, ...rpcEvents]);
    reconstruction = reconstructHoldingWindow({
      walletAddress: memberRow.wallet_address,
      currentBalanceUnits: currentBalance.toString(),
      thresholdUnits: MEMBER_THRESHOLD_UNITS.toString(),
      events: allEvents
    });
  } catch (error) {
    throw new ApiError("GCA holding history could not be reconstructed", 502);
  }
  const observedContinuousEligible = Boolean(
    blockscoutHistory.historyComplete &&
    reconstruction.reconstructionConsistent &&
    reconstruction.observedContinuousEligible
  );
  return {
    checkedAt: nowIso(),
    windowStartAt: new Date(windowStartMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
    windowEndAt: new Date(snapshot.timestampMs).toISOString().replace(/\.\d{3}Z$/, "Z"),
    snapshotBlockNumber: snapshot.blockNumber,
    snapshotBlockHash: snapshot.blockHash,
    currentRawBalance: reconstruction.currentRawBalance,
    currentGcaBalance: unitsToGca(reconstruction.currentRawBalance),
    windowStartRawBalance: reconstruction.windowStartRawBalance,
    windowStartGcaBalance: reconstruction.windowStartRawBalance
      ? unitsToGca(reconstruction.windowStartRawBalance)
      : "",
    minimumRawBalance: reconstruction.minimumRawBalance,
    minimumGcaBalance: reconstruction.minimumRawBalance
      ? unitsToGca(reconstruction.minimumRawBalance)
      : "",
    thresholdRawBalance: MEMBER_THRESHOLD_UNITS.toString(),
    thresholdGcaBalance: unitsToGca(MEMBER_THRESHOLD_UNITS),
    observedContinuousEligible,
    historyComplete: blockscoutHistory.historyComplete,
    reconstructionConsistent: reconstruction.reconstructionConsistent,
    eventCount: allEvents.length,
    blockscoutEventCount: blockscoutHistory.events.length,
    rpcEventCount: rpcEvents.length,
    historyProvider: "Base Blockscout v2 token-transfer index plus Base public RPC recent logs and snapshot balanceOf",
    status: observedContinuousEligible ? "observed_eligible" : "observed_below_threshold",
    failureReason: reconstruction.failureReason || (
      observedContinuousEligible ? "" : "minimum_balance_below_member_threshold"
    )
  };
}

async function verifyMemberBenefitTransfer(memberRow, transactionHash, env) {
  const [snapshot, receipt] = await Promise.all([
    readBlockSnapshot("safe", env),
    baseRpcRequest("eth_getTransactionReceipt", [transactionHash], env)
  ]);
  let evidence;
  try {
    evidence = verifyMemberBenefitTransferReceipt({
      receipt,
      transactionHash,
      expectedContractAddress: CONTRACT_ADDRESS,
      expectedSourceWallet: MEMBER_BENEFIT_SOURCE_WALLET,
      expectedRecipientWallet: memberRow.wallet_address,
      expectedAmountUnits: MEMBER_BENEFIT_UNITS.toString(),
      safeBlockNumber: snapshot.blockNumber
    });
  } catch (error) {
    throw new ApiError("Base RPC returned malformed member benefit transfer evidence", 502);
  }
  if (!evidence.matchedTransfer) {
    throw new ApiError(
      `transactionHash does not prove a safe, exact 10,000 GCA transfer from the official reserve wallet (${evidence.status})`,
      409
    );
  }
  return {
    ...evidence,
    checkedAt: nowIso(),
    safeSnapshotBlockNumber: snapshot.blockNumber,
    safeSnapshotBlockHash: snapshot.blockHash,
    amountGca: unitsToGca(evidence.amountUnits),
    verificationProvider: "Base public RPC safe block and eth_getTransactionReceipt"
  };
}

function requireDatabase(env) {
  if (!env.REGISTRATION_DB) {
    throw new ApiError("REGISTRATION_DB binding is not configured", 503);
  }
  return env.REGISTRATION_DB;
}

function rowToEmailRegistration(row, includeEmail = true) {
  if (!row) {
    return null;
  }
  return {
    emailRegistrationId: row.email_registration_id,
    packetVersion: EMAIL_REGISTRATION_VERSION,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    email: includeEmail ? row.email : undefined,
    displayName: row.display_name || "",
    source: row.source,
    language: row.language,
    interests: JSON.parse(row.interests_json || "[]"),
    walletRequired: Boolean(row.wallet_required),
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer)
  };
}

function rowToContactSuppression(row, includeEmail = true) {
  if (!row) {
    return null;
  }
  return {
    suppressionId: row.suppression_id,
    packetVersion: CONTACT_SUPPRESSION_VERSION,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    email: includeEmail ? row.email : undefined,
    emailSha256: row.email_hash,
    reason: row.reason,
    source: row.source,
    contactSuppressed: Boolean(row.contact_suppressed),
    requiresSignature: false,
    requiresTransaction: false,
    automaticTokenTransfer: false
  };
}

function rowToMemberAccount(row, includeEmail = true) {
  if (!row) {
    return null;
  }
  return {
    accountId: row.account_id,
    packetVersion: MEMBER_ACCESS_VERSION,
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    email: includeEmail ? row.email : undefined,
    emailSha256: row.email_hash,
    walletAddress: row.wallet_address,
    displayName: row.display_name || "",
    source: row.source,
    language: row.language,
    programIntent: row.program_intent,
    holdingStartDate: row.holding_start_date || "",
    evidenceTxHash: row.evidence_tx_hash || "",
    contactConsentAccepted: Boolean(row.contact_consent_accepted),
    securityBoundaryAccepted: Boolean(row.security_boundary_accepted),
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer)
  };
}

function rowToAccountStatusRecoveryRequest(row, includeEmail = true) {
  if (!row) {
    return null;
  }
  return {
    recoveryRequestId: row.recovery_request_id,
    packetVersion: row.packet_version,
    accountId: row.account_id,
    email: includeEmail ? row.email : undefined,
    emailSha256: row.email_hash,
    walletAddress: row.wallet_address,
    status: row.status,
    requestedAt: row.requested_at,
    expiresAt: row.expires_at,
    recoveryCredentialIssued: Boolean(
      String(row.recovery_credential_hash || "").trim()
    ),
    recoveryCredentialExpiresAt:
      row.recovery_credential_expires_at || "",
    approvedAt: row.approved_at || "",
    consumedAt: row.consumed_at || "",
    cancelledAt: row.cancelled_at || "",
    operatorId: row.operator_id || "",
    reasonCode: row.reason_code || "",
    source: row.source,
    registeredEmailVerified: Boolean(row.registered_email_verified),
    manualIdentityReviewCompleted: Boolean(
      row.manual_identity_review_completed
    ),
    noSecretsRequested: Boolean(row.no_secrets_requested),
    changesAccountOrLedgers: Boolean(row.changes_account_or_ledgers),
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    tokenHashesReturned: false,
    recoveryCredentialReturned: false
  };
}

function rowToWalletVerification(row) {
  if (!row) {
    return null;
  }
  return {
    walletVerificationId: row.wallet_verification_id,
    accountId: row.account_id || "",
    emailSha256: row.email_hash || "",
    walletAddress: row.wallet_address,
    chainId: Number(row.chain_id),
    contractAddress: row.contract_address,
    checkedAt: row.checked_at,
    rawBalance: row.raw_balance,
    gcaBalance: row.gca_balance,
    holderBonusEligible: Boolean(row.holder_bonus_eligible),
    gcaMemberEligible: Boolean(row.gca_member_eligible),
    gcaMemberHoldingPeriodEligible: Boolean(row.gca_member_holding_period_eligible),
    holdingPeriodPreviewEligible: Boolean(row.holding_period_preview_eligible),
    holdingPeriodDaysVerified: Number(row.holding_period_days_verified || 0),
    evidenceTxHash: row.evidence_tx_hash || "",
    evidenceTxHashFormatOk: Boolean(row.evidence_tx_hash_format_ok),
    verificationProvider: row.verification_provider,
    status: row.status,
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction)
  };
}

function rowToCreditLedger(row) {
  if (!row) {
    return null;
  }
  return {
    creditLedgerId: row.credit_ledger_id,
    accountId: row.account_id,
    emailSha256: row.email_hash,
    walletAddress: row.wallet_address,
    creditAmount: Number(row.credit_amount),
    creditType: row.credit_type,
    activatedAt: row.activated_at,
    expiresAt: row.expires_at,
    remainingCredits: Number(row.remaining_credits),
    source: row.source,
    transferable: Boolean(row.transferable),
    cashRedeemable: Boolean(row.cash_redeemable),
    status: row.status
  };
}

function rowToCreditUsage(row) {
  if (!row) {
    return null;
  }
  return {
    creditUsageId: row.credit_usage_id,
    serviceRequestId: row.service_request_id || "",
    creditLedgerId: row.credit_ledger_id,
    accountId: row.account_id,
    emailSha256: row.email_hash,
    walletAddress: row.wallet_address,
    serviceId: row.service_id,
    serviceName: row.service_name,
    creditAmountUsed: Number(row.credit_amount_used),
    remainingCreditsBefore: Number(row.remaining_credits_before),
    remainingCreditsAfter: Number(row.remaining_credits_after),
    usedAt: row.used_at,
    source: row.source,
    operatorNote: row.operator_note || "",
    status: row.status,
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet)
  };
}

function rowToServiceRequest(row, includeEmail = true) {
  if (!row) {
    return null;
  }
  return {
    serviceRequestId: row.service_request_id,
    packetVersion: SERVICE_REQUEST_VERSION,
    createdAt: row.created_at,
    updatedAt: row.updated_at || "",
    reviewedAt: row.reviewed_at || "",
    completedAt: row.completed_at || "",
    cancellationId: row.cancellation_id || "",
    cancelledAt: row.cancelled_at || "",
    cancellationVersion: row.cancellation_version || "",
    cancellationSource: row.cancellation_source || "",
    deliveryReceiptId: row.delivery_receipt_id || "",
    deliveryAcknowledgedAt: row.delivery_acknowledged_at || "",
    deliveryAcknowledgementVersion:
      row.delivery_acknowledgement_version || "",
    deliveryAcknowledgementSource:
      row.delivery_acknowledgement_source || "",
    status: row.status,
    email: includeEmail ? row.email : undefined,
    emailSha256: row.email_hash,
    accountId: row.account_id || "",
    walletAddress: row.wallet_address || "",
    creditLedgerId: row.credit_ledger_id || "",
    serviceId: row.service_id,
    serviceName: row.service_name,
    requestedCreditHold: Number(row.requested_credit_hold),
    remainingCreditsAtRequest: row.remaining_credits_at_request === null || row.remaining_credits_at_request === undefined
      ? null
      : Number(row.remaining_credits_at_request),
    requestTitle: row.request_title || "",
    requestSummary: row.request_summary || "",
    marketContext: row.market_context || "",
    preferredLanguage: row.preferred_language || "zh-CN",
    source: row.source,
    latestReviewId: row.latest_review_id || "",
    creditUsageId: row.credit_usage_id || "",
    operatorReviewRequired: Boolean(row.operator_review_required),
    doesNotDeductCredits: Boolean(row.does_not_deduct_credits),
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet),
    createsTradingPermission: Boolean(row.creates_trading_permission)
  };
}

function rowToServiceRequestFollowup(row) {
  if (!row) {
    return null;
  }
  return {
    serviceRequestFollowupId: row.service_request_followup_id,
    serviceRequestId: row.service_request_id,
    accountId: row.account_id,
    clientFollowupId: row.client_followup_id,
    packetVersion: row.packet_version,
    responseText: row.response_text,
    submittedAt: row.submitted_at,
    source: row.source,
    noSecretsNoCustody: Boolean(row.no_secrets_no_custody),
    manualReviewOnly: Boolean(row.manual_review_only),
    changesCredits: Boolean(row.changes_credits),
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet),
    createsTradingPermission: Boolean(row.creates_trading_permission)
  };
}

function rowToServiceRequestReview(row) {
  if (!row) {
    return null;
  }
  return {
    serviceRequestReviewId: row.service_request_review_id,
    serviceRequestId: row.service_request_id,
    packetVersion: row.packet_version,
    decision: row.decision,
    reasonCode: row.reason_code,
    reviewerId: row.reviewer_id,
    operatorNote: row.operator_note || "",
    memberPrompt: row.member_prompt || "",
    deliveryReference: row.delivery_reference || "",
    creditUsageId: row.credit_usage_id || "",
    creditAmountUsed: Number(row.credit_amount_used || 0),
    remainingCreditsBefore:
      row.remaining_credits_before === null ||
      row.remaining_credits_before === undefined
        ? null
        : Number(row.remaining_credits_before),
    remainingCreditsAfter:
      row.remaining_credits_after === null ||
      row.remaining_credits_after === undefined
        ? null
        : Number(row.remaining_credits_after),
    reviewedAt: row.reviewed_at,
    source: row.source,
    manualReviewCompleted: Boolean(row.manual_review_completed),
    deliveryCompleted: Boolean(row.delivery_completed),
    creditsDeducted: Boolean(row.credits_deducted),
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet),
    createsTradingPermission: Boolean(row.creates_trading_permission)
  };
}

function serviceRequestNextStep(
  status,
  deliveryAcknowledged = false,
  followupCount = 0
) {
  if (status === "cancelled_by_account") {
    return "This account cancelled the request before manual review. No credits were deducted.";
  }
  if (status === "queued_operator_review") {
    if (Number(followupCount || 0) > 0) {
      return "Additional information was submitted and the request returned to the manual review queue.";
    }
    return "The request is queued for manual operator review.";
  }
  if (status === "queued_insufficient_credits") {
    return "The request is queued, but the available credit balance was below the catalog unit at submission.";
  }
  if (status === "queued_expired_credit_ledger") {
    return "The request is queued, but the credit ledger was expired at submission.";
  }
  if (status === "queued_missing_credit_ledger") {
    return "The request is queued, but no account credit ledger was available at submission.";
  }
  if (status === "approved_operator_review") {
    return "Manual review approved the scope. Delivery is still pending.";
  }
  if (status === "needs_more_information") {
    return "Manual review needs more information before the request can proceed.";
  }
  if (status === "rejected_operator_review") {
    return "Manual review rejected the request. No credits were deducted.";
  }
  if (status === "delivered") {
    if (deliveryAcknowledged) {
      return "Delivery receipt was acknowledged by this account.";
    }
    return "Manual delivery was recorded. Review the credit settlement shown with this request.";
  }
  return "Check this account history for the latest operator-reviewed status.";
}

function rowToAccountServiceRequest(row) {
  if (!row) {
    return null;
  }
  return {
    serviceRequestId: row.service_request_id,
    packetVersion: ACCOUNT_SERVICE_REQUEST_VERSION,
    createdAt: row.created_at,
    status: row.status,
    serviceId: row.service_id,
    serviceName: row.service_name,
    requestedCreditHold: Number(row.requested_credit_hold),
    remainingCreditsAtRequest:
      row.remaining_credits_at_request === null ||
      row.remaining_credits_at_request === undefined
        ? null
        : Number(row.remaining_credits_at_request),
    requestTitle: row.request_title || "",
    preferredLanguage: row.preferred_language || "zh-CN",
    operatorReviewRequired: Boolean(row.operator_review_required),
    creditsReserved: false,
    creditsDeducted: Boolean(
      row.review_credits_deducted ??
        !Boolean(row.does_not_deduct_credits)
    ),
    reviewedAt: row.reviewed_at || "",
    completedAt: row.completed_at || "",
    cancelledByAccount: Boolean(row.cancellation_id),
    cancelledAt: row.cancelled_at || "",
    followupCount: Number(row.followup_count || 0),
    latestFollowup: row.followup_id
      ? {
          serviceRequestFollowupId: row.followup_id,
          submittedAt: row.followup_submitted_at || ""
        }
      : null,
    deliveryAcknowledged: Boolean(row.delivery_receipt_id),
    deliveryAcknowledgedAt: row.delivery_acknowledged_at || "",
    latestReview: row.latest_review_id
      ? {
          decision: row.review_decision || "",
          reasonCode: row.review_reason_code || "",
          memberPrompt:
            row.review_decision === "needs_more_information"
              ? row.review_member_prompt || ""
              : "",
          reviewedAt:
            row.review_reviewed_at || row.reviewed_at || "",
          deliveryCompleted: Boolean(
            row.review_delivery_completed
          ),
          deliveryReference:
            row.review_delivery_completed
              ? row.review_delivery_reference || ""
              : "",
          creditAmountUsed: Number(
            row.review_credit_amount_used || 0
          ),
          remainingCreditsAfter:
            row.review_remaining_credits_after === null ||
            row.review_remaining_credits_after === undefined
              ? null
              : Number(row.review_remaining_credits_after)
        }
      : null,
    nextStep: serviceRequestNextStep(
      row.status,
      Boolean(row.delivery_receipt_id),
      Number(row.followup_count || 0)
    )
  };
}

function rowToMemberLedger(row) {
  if (!row) {
    return null;
  }
  return {
    memberLedgerId: row.member_ledger_id,
    accountId: row.account_id,
    emailSha256: row.email_hash,
    walletAddress: row.wallet_address,
    tierName: row.tier_name,
    verifiedBalance: row.verified_balance,
    holdingStartDate: row.holding_start_date || "",
    holdingPeriodDaysVerified: Number(row.holding_period_days_verified || 0),
    evidenceTxHash: row.evidence_tx_hash || "",
    evidenceTxHashFormatOk: Boolean(row.evidence_tx_hash_format_ok),
    memberBenefitReviewEvidenceStatus: row.member_benefit_review_evidence_status,
    memberBenefitAmount: row.member_benefit_amount,
    memberBenefitClaimStatus: row.member_benefit_claim_status,
    memberBenefitTransferTx: row.member_benefit_transfer_tx || "",
    memberBenefitTransferRecordId: row.member_benefit_transfer_record_id || "",
    memberBenefitTransferVerifiedAt: row.member_benefit_transfer_verified_at || "",
    memberBenefitTransferVerificationStatus: row.member_benefit_transfer_verification_status || "",
    activatedAt: row.activated_at || "",
    nextRefreshDueAt: row.next_refresh_due_at || "",
    latestHoldingVerificationId: row.latest_holding_verification_id || "",
    onchainHoldingVerified: Boolean(row.onchain_holding_verified),
    onchainHoldingVerifiedAt: row.onchain_holding_verified_at || "",
    requiresManualReserveTransferReview: Boolean(row.requires_manual_reserve_transfer_review),
    automaticTransfer: Boolean(row.automatic_transfer),
    status: row.status,
    updatedAt: row.updated_at
  };
}

function rowToMemberBenefitTransfer(row) {
  if (!row) {
    return null;
  }
  return {
    transferRecordId: row.transfer_record_id,
    packetVersion: row.packet_version,
    memberLedgerId: row.member_ledger_id,
    accountId: row.account_id,
    walletAddress: row.wallet_address,
    sourceWallet: row.source_wallet,
    recipientWallet: row.recipient_wallet,
    chainId: Number(row.chain_id),
    contractAddress: row.contract_address,
    transactionHash: row.transaction_hash,
    baseScanTransactionUrl: `https://basescan.org/tx/${row.transaction_hash}`,
    receiptBlockNumber: Number(row.receipt_block_number),
    receiptBlockHash: row.receipt_block_hash,
    safeSnapshotBlockNumber: Number(row.safe_snapshot_block_number),
    safeSnapshotBlockHash: row.safe_snapshot_block_hash,
    transferLogIndex: Number(row.transfer_log_index),
    amountRaw: row.amount_raw,
    amountGca: row.amount_gca,
    verificationProvider: row.verification_provider,
    verificationStatus: row.verification_status,
    verifiedAt: row.verified_at,
    reviewerId: row.reviewer_id,
    reasonCode: row.reason_code,
    operatorNote: row.operator_note || "",
    source: row.source,
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet),
    observedOnchainTransaction: true
  };
}

function rowToHoldingVerification(row) {
  if (!row) {
    return null;
  }
  return {
    holdingVerificationId: row.holding_verification_id,
    packetVersion: HOLDING_VERIFICATION_VERSION,
    memberLedgerId: row.member_ledger_id,
    accountId: row.account_id,
    walletAddress: row.wallet_address,
    chainId: Number(row.chain_id),
    contractAddress: row.contract_address,
    checkedAt: row.checked_at,
    windowStartAt: row.window_start_at,
    windowEndAt: row.window_end_at,
    snapshotBlockNumber: Number(row.snapshot_block_number),
    snapshotBlockHash: row.snapshot_block_hash,
    currentRawBalance: row.current_raw_balance,
    currentGcaBalance: row.current_gca_balance,
    windowStartRawBalance: row.window_start_raw_balance,
    windowStartGcaBalance: row.window_start_gca_balance,
    minimumRawBalance: row.minimum_raw_balance,
    minimumGcaBalance: row.minimum_gca_balance,
    thresholdRawBalance: row.threshold_raw_balance,
    thresholdGcaBalance: row.threshold_gca_balance,
    observedContinuousEligible: Boolean(row.observed_continuous_eligible),
    historyComplete: Boolean(row.history_complete),
    reconstructionConsistent: Boolean(row.reconstruction_consistent),
    eventCount: Number(row.event_count || 0),
    blockscoutEventCount: Number(row.blockscout_event_count || 0),
    rpcEventCount: Number(row.rpc_event_count || 0),
    historyProvider: row.history_provider,
    status: row.status,
    failureReason: row.failure_reason || "",
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet)
  };
}

function rowToMemberReview(row) {
  if (!row) {
    return null;
  }
  return {
    memberReviewId: row.member_review_id,
    packetVersion: MEMBER_REVIEW_VERSION,
    memberLedgerId: row.member_ledger_id,
    accountId: row.account_id,
    walletAddress: row.wallet_address,
    decision: row.decision,
    reasonCode: row.reason_code,
    operatorNote: row.operator_note || "",
    reviewerId: row.reviewer_id,
    reviewedAt: row.reviewed_at,
    source: row.source,
    balanceAtReview: row.balance_at_review,
    memberThresholdMet: Boolean(row.member_threshold_met),
    holdingPeriodPreviewDays: Number(row.holding_period_preview_days || 0),
    evidenceTxHash: row.evidence_tx_hash || "",
    evidenceTxHashFormatOk: Boolean(row.evidence_tx_hash_format_ok),
    holdingVerificationId: row.holding_verification_id || "",
    onchainHoldingEligible: Boolean(row.onchain_holding_eligible),
    onchainHistoryComplete: Boolean(row.onchain_history_complete),
    onchainMinimumBalance: row.onchain_minimum_balance || "",
    previousMemberStatus: row.previous_member_status,
    resultingMemberStatus: row.resulting_member_status,
    previousClaimStatus: row.previous_claim_status,
    resultingClaimStatus: row.resulting_claim_status,
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet)
  };
}

async function submitEmailRegistration(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const registration = extractEmailRegistration(packet);
  const emailRegistrationId = await stableId("gca_email", registration.email);
  const now = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const existing = await db
    .prepare("SELECT * FROM gca_email_registrations WHERE email_registration_id = ?1 OR email = ?2 LIMIT 1")
    .bind(emailRegistrationId, registration.email)
    .first();
  if (existing) {
    await db
      .prepare("UPDATE gca_email_registrations SET updated_at = ?1 WHERE email_registration_id = ?2")
      .bind(now, existing.email_registration_id)
      .run();
    return jsonResponse({
      ok: true,
      alreadyRegistered: true,
      emailRegistration: rowToEmailRegistration({ ...existing, updated_at: now }),
      nextStep: "Email is already on the GCA user list. No wallet action, signature, or payment is required for email registration."
    }, 200, origin, env);
  }

  const emailHash = await sha256Hex(registration.email);
  const ipHash = await optionalIpHash(request, env);
  const userAgent = String(request.headers.get("user-agent") || "").slice(0, 300);
  await db
    .prepare(
      `INSERT INTO gca_email_registrations (
        email_registration_id,
        email,
        email_hash,
        display_name,
        source,
        language,
        interests_json,
        contact_consent_accepted,
        security_boundary_accepted,
        status,
        created_at,
        updated_at,
        user_agent,
        ip_hash,
        wallet_required,
        requires_signature,
        requires_transaction,
        automatic_token_transfer
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 1, 1, 'received', ?8, ?8, ?9, ?10, 0, 0, 0, 0)`
    )
    .bind(
      emailRegistrationId,
      registration.email,
      emailHash,
      registration.displayName,
      registration.source,
      registration.language,
      JSON.stringify(registration.interests),
      now,
      userAgent,
      ipHash
    )
    .run();

  return jsonResponse({
    ok: true,
    alreadyRegistered: false,
    emailRegistration: {
      emailRegistrationId,
      packetVersion: EMAIL_REGISTRATION_VERSION,
      status: "received",
      createdAt: now,
      updatedAt: now,
      email: registration.email,
      displayName: registration.displayName,
      source: registration.source,
      language: registration.language,
      interests: registration.interests,
      walletRequired: false,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false
    },
    nextStep: "GCA support can contact this email when customer registration, member access, or product updates are ready."
  }, 201, origin, env);
}

async function submitContactSuppression(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const suppression = extractContactSuppression(packet);
  const suppressionId = await stableId("gca_suppression", suppression.email);
  const now = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const emailHash = await sha256Hex(suppression.email);
  const ipHash = await optionalIpHash(request, env);
  const userAgent = String(request.headers.get("user-agent") || "").slice(0, 300);
  const existing = await db
    .prepare("SELECT * FROM gca_contact_suppressions WHERE suppression_id = ?1 OR email = ?2 LIMIT 1")
    .bind(suppressionId, suppression.email)
    .first();

  if (existing) {
    await db
      .prepare(
        `UPDATE gca_contact_suppressions
         SET reason = ?1, source = ?2, status = 'suppressed', updated_at = ?3, user_agent = ?4, ip_hash = ?5, contact_suppressed = 1
         WHERE suppression_id = ?6`
      )
      .bind(suppression.reason, suppression.source, now, userAgent, ipHash, existing.suppression_id)
      .run();
    return jsonResponse({
      ok: true,
      alreadySuppressed: true,
      contactSuppression: rowToContactSuppression({
        ...existing,
        reason: suppression.reason,
        source: suppression.source,
        status: "suppressed",
        updated_at: now,
        contact_suppressed: 1
      }),
      nextStep: "This email is on the GCA do-not-contact list. No wallet action, signature, transaction, or payment is required."
    }, 200, origin, env);
  }

  await db
    .prepare(
      `INSERT INTO gca_contact_suppressions (
        suppression_id,
        email,
        email_hash,
        reason,
        source,
        status,
        contact_suppressed,
        created_at,
        updated_at,
        user_agent,
        ip_hash
      ) VALUES (?1, ?2, ?3, ?4, ?5, 'suppressed', 1, ?6, ?6, ?7, ?8)`
    )
    .bind(
      suppressionId,
      suppression.email,
      emailHash,
      suppression.reason,
      suppression.source,
      now,
      userAgent,
      ipHash
    )
    .run();

  return jsonResponse({
    ok: true,
    alreadySuppressed: false,
    contactSuppression: {
      suppressionId,
      packetVersion: CONTACT_SUPPRESSION_VERSION,
      status: "suppressed",
      createdAt: now,
      updatedAt: now,
      email: suppression.email,
      emailSha256: emailHash,
      reason: suppression.reason,
      source: suppression.source,
      contactSuppressed: true,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false
    },
    nextStep: "GCA recorded this email on the do-not-contact list. No wallet action, signature, transaction, or payment is required."
  }, 201, origin, env);
}

function classifyWalletBalance(rawBalance, evidence) {
  const holderBonusEligible = rawBalance >= HOLDER_THRESHOLD_UNITS;
  const gcaMemberEligible = rawBalance >= MEMBER_THRESHOLD_UNITS;
  const holdingPeriodPreviewEligible = Boolean(
    gcaMemberEligible &&
    evidence.holdingPeriodDaysVerified >= MEMBER_HOLD_DAYS &&
    evidence.evidenceTxHashFormatOk
  );
  const status = holderBonusEligible ? "verified" : "below_threshold";
  const accountStatus = holdingPeriodPreviewEligible
    ? "member_review_ready"
    : gcaMemberEligible
      ? "member_queued"
      : holderBonusEligible
        ? "holder_credit_active"
        : "below_threshold";
  return {
    holderBonusEligible,
    gcaMemberEligible,
    gcaMemberHoldingPeriodEligible: false,
    holdingPeriodPreviewEligible,
    status,
    accountStatus
  };
}

async function writeWalletVerification(db, accountId, emailHash, walletAddress, rawBalance, evidence, now) {
  const classification = classifyWalletBalance(rawBalance, evidence);
  const walletVerificationId = await stableId("gca_wallet", accountId, walletAddress, now);
  const gcaBalance = unitsToGca(rawBalance);
  await db
    .prepare(
      `INSERT INTO gca_wallet_verifications (
        wallet_verification_id,
        account_id,
        email_hash,
        wallet_address,
        chain_id,
        contract_address,
        checked_at,
        raw_balance,
        gca_balance,
        holder_bonus_eligible,
        gca_member_eligible,
        gca_member_holding_period_eligible,
        holding_period_preview_eligible,
        holding_period_days_verified,
        evidence_tx_hash,
        evidence_tx_hash_format_ok,
        verification_provider,
        status,
        requires_signature,
        requires_transaction
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, ?18, 0, 0)`
    )
    .bind(
      walletVerificationId,
      accountId,
      emailHash,
      walletAddress,
      CHAIN_ID,
      CONTRACT_ADDRESS,
      now,
      rawBalance.toString(),
      gcaBalance,
      classification.holderBonusEligible ? 1 : 0,
      classification.gcaMemberEligible ? 1 : 0,
      classification.gcaMemberHoldingPeriodEligible ? 1 : 0,
      classification.holdingPeriodPreviewEligible ? 1 : 0,
      evidence.holdingPeriodDaysVerified,
      evidence.evidenceTxHash,
      evidence.evidenceTxHashFormatOk ? 1 : 0,
      "Base Mainnet public RPC eth_call balanceOf",
      classification.status
    )
    .run();
  return {
    walletVerificationId,
    accountId,
    emailSha256: emailHash,
    walletAddress,
    chainId: CHAIN_ID,
    contractAddress: CONTRACT_ADDRESS,
    checkedAt: now,
    rawBalance: rawBalance.toString(),
    gcaBalance,
    holderBonusEligible: classification.holderBonusEligible,
    gcaMemberEligible: classification.gcaMemberEligible,
    gcaMemberHoldingPeriodEligible: classification.gcaMemberHoldingPeriodEligible,
    holdingPeriodPreviewEligible: classification.holdingPeriodPreviewEligible,
    holdingPeriodDaysVerified: evidence.holdingPeriodDaysVerified,
    evidenceTxHash: evidence.evidenceTxHash,
    evidenceTxHashFormatOk: evidence.evidenceTxHashFormatOk,
    verificationProvider: "Base Mainnet public RPC eth_call balanceOf",
    status: classification.status,
    requiresSignature: false,
    requiresTransaction: false
  };
}

async function maybeWriteCreditLedger(db, account, verification, now) {
  if (!verification.holderBonusEligible) {
    return null;
  }
  const creditLedgerId = await stableId("gca_credit", account.email, account.walletAddress);
  await db
    .prepare(
      `INSERT OR IGNORE INTO gca_credit_ledger (
        credit_ledger_id,
        account_id,
        email_hash,
        wallet_address,
        credit_amount,
        credit_type,
        activated_at,
        expires_at,
        remaining_credits,
        source,
        transferable,
        cash_redeemable,
        status
      ) VALUES (?1, ?2, ?3, ?4, ?5, 'GCA AI Quant Access credits', ?6, ?7, ?5, 'cloudflare-wallet-balance-verification', 0, 0, 'ledger_recorded')`
    )
    .bind(
      creditLedgerId,
      account.accountId,
      account.emailHash,
      account.walletAddress,
      CREDIT_AMOUNT,
      now,
      addDaysIso(now, CREDIT_EXPIRY_DAYS)
    )
    .run();
  const row = await db
    .prepare("SELECT * FROM gca_credit_ledger WHERE credit_ledger_id = ?1 LIMIT 1")
    .bind(creditLedgerId)
    .first();
  return rowToCreditLedger(row);
}

async function recordCreditUsage(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse({ ok: false, error: "admin authorization is required" }, 401, origin, env);
  }
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const usageInput = extractCreditUsage(packet);
  const creditRow = await db
    .prepare("SELECT * FROM gca_credit_ledger WHERE credit_ledger_id = ?1 LIMIT 1")
    .bind(usageInput.creditLedgerId)
    .first();
  if (!creditRow) {
    throw new ApiError("creditLedgerId was not found", 404);
  }
  if (usageInput.walletAddress && usageInput.walletAddress !== creditRow.wallet_address) {
    throw new ApiError("walletAddress must match the credit ledger wallet");
  }
  const remainingBefore = Number(creditRow.remaining_credits || 0);
  if (!Number.isInteger(remainingBefore) || remainingBefore < 0) {
    throw new ApiError("credit ledger remainingCredits is invalid", 409);
  }
  if (usageInput.creditAmountUsed > remainingBefore) {
    throw new ApiError("creditAmountUsed exceeds remaining credits", 409);
  }
  const now = nowIso();
  const remainingAfter = remainingBefore - usageInput.creditAmountUsed;
  const status = remainingAfter === 0 ? "exhausted" : "usage_recorded";
  const creditStatus = remainingAfter === 0 ? "exhausted" : "ledger_recorded";
  const usageId = await stableId(
    "gca_credit_use",
    usageInput.creditLedgerId,
    usageInput.serviceId,
    usageInput.creditAmountUsed,
    now
  );
  await db
    .prepare(
      `INSERT INTO gca_credit_usage (
        credit_usage_id,
        credit_ledger_id,
        account_id,
        email_hash,
        wallet_address,
        service_id,
        service_name,
        credit_amount_used,
        remaining_credits_before,
        remaining_credits_after,
        used_at,
        source,
        operator_note,
        status,
        requires_signature,
        requires_transaction,
        automatic_token_transfer,
        writes_wallet
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, 0, 0, 0, 0)`
    )
    .bind(
      usageId,
      usageInput.creditLedgerId,
      creditRow.account_id,
      creditRow.email_hash,
      creditRow.wallet_address,
      usageInput.serviceId,
      usageInput.serviceName,
      usageInput.creditAmountUsed,
      remainingBefore,
      remainingAfter,
      now,
      usageInput.source,
      usageInput.operatorNote,
      status
    )
    .run();
  await db
    .prepare("UPDATE gca_credit_ledger SET remaining_credits = ?1, status = ?2 WHERE credit_ledger_id = ?3")
    .bind(remainingAfter, creditStatus, usageInput.creditLedgerId)
    .run();
  const usageRow = await db
    .prepare("SELECT * FROM gca_credit_usage WHERE credit_usage_id = ?1 LIMIT 1")
    .bind(usageId)
    .first();
  const updatedCreditRow = await db
    .prepare("SELECT * FROM gca_credit_ledger WHERE credit_ledger_id = ?1 LIMIT 1")
    .bind(usageInput.creditLedgerId)
    .first();
  return jsonResponse({
    ok: true,
    packetVersion: CREDIT_USAGE_VERSION,
    creditUsage: rowToCreditUsage(usageRow),
    creditLedger: rowToCreditLedger(updatedCreditRow),
    boundaries: {
      adminOnly: true,
      localOrOperatorReviewOnly: true,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false,
      writesWallet: false
    }
  }, 201, origin, env);
}

async function recordServiceRequest(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse({ ok: false, error: "admin authorization is required" }, 401, origin, env);
  }
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const requestInput = extractServiceRequest(packet);
  const emailHash = await sha256Hex(requestInput.email);
  let creditRow = null;
  let accountId = "";
  let walletAddress = requestInput.walletAddress;
  let remainingCreditsAtRequest = null;
  let status = "queued_missing_credit_ledger";

  if (requestInput.creditLedgerId) {
    creditRow = await db
      .prepare("SELECT * FROM gca_credit_ledger WHERE credit_ledger_id = ?1 LIMIT 1")
      .bind(requestInput.creditLedgerId)
      .first();
    if (!creditRow) {
      throw new ApiError("creditLedgerId was not found", 404);
    }
    if (creditRow.email_hash !== emailHash) {
      throw new ApiError("email must match the credit ledger email");
    }
    if (requestInput.walletAddress && requestInput.walletAddress !== creditRow.wallet_address) {
      throw new ApiError("walletAddress must match the credit ledger wallet");
    }
    accountId = creditRow.account_id || "";
    walletAddress = creditRow.wallet_address || requestInput.walletAddress;
    remainingCreditsAtRequest = Number(creditRow.remaining_credits || 0);
    if (!Number.isInteger(remainingCreditsAtRequest) || remainingCreditsAtRequest < 0) {
      throw new ApiError("credit ledger remainingCredits is invalid", 409);
    }
    status = requestInput.requestedCreditHold <= remainingCreditsAtRequest
      ? "queued_operator_review"
      : "queued_insufficient_credits";
  }

  const now = nowIso();
  const serviceRequestId = await stableId("gca_service_req", requestInput.email, requestInput.serviceId, now);
  await db
    .prepare(
      `INSERT INTO gca_service_requests (
        service_request_id,
        account_id,
        email,
        email_hash,
        wallet_address,
        credit_ledger_id,
        service_id,
        service_name,
        requested_credit_hold,
        remaining_credits_at_request,
        request_title,
        request_summary,
        market_context,
        preferred_language,
        source,
        status,
        created_at,
        operator_review_required,
        does_not_deduct_credits,
        requires_signature,
        requires_transaction,
        automatic_token_transfer,
        writes_wallet,
        creates_trading_permission
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, 1, 1, 0, 0, 0, 0, 0)`
    )
    .bind(
      serviceRequestId,
      accountId,
      requestInput.email,
      emailHash,
      walletAddress,
      requestInput.creditLedgerId,
      requestInput.serviceId,
      requestInput.serviceName,
      requestInput.requestedCreditHold,
      remainingCreditsAtRequest,
      requestInput.requestTitle,
      requestInput.requestSummary,
      requestInput.marketContext,
      requestInput.preferredLanguage,
      requestInput.source,
      status,
      now
    )
    .run();
  const serviceRequestRow = await db
    .prepare("SELECT * FROM gca_service_requests WHERE service_request_id = ?1 LIMIT 1")
    .bind(serviceRequestId)
    .first();
  return jsonResponse({
    ok: true,
    packetVersion: SERVICE_REQUEST_VERSION,
    serviceRequest: rowToServiceRequest(serviceRequestRow),
    creditLedger: creditRow ? rowToCreditLedger(creditRow) : null,
    nextStep: "Operator should review scope and only record credit usage after service delivery evidence exists.",
    boundaries: {
      adminOnly: true,
      operatorReviewOnly: true,
      deductsCredits: false,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false,
      writesWallet: false,
      createsTradingPermission: false
    }
  }, 201, origin, env);
}

function serviceRequestReviewBoundaries() {
  return {
    adminTokenRequired: true,
    manualReviewRequired: true,
    approvedBeforeDeliveryRequired: true,
    serverCatalogCreditUnitRequired: true,
    creditsDeductedOnlyOnDelivered: true,
    creditsDeductedAtMostOncePerRequest: true,
    memberPromptRequiredForMoreInformation: true,
    memberPromptReturnedToMatchedAccount: true,
    operatorNoteReturnedToAccount: false,
    requiresSignature: false,
    requiresTransaction: false,
    automaticTokenTransfer: false,
    writesWallet: false,
    createsTradingPermission: false
  };
}

function reviewDecisionStatus(decision) {
  if (decision === "approved") {
    return "approved_operator_review";
  }
  if (decision === "rejected") {
    return "rejected_operator_review";
  }
  if (decision === "needs_more_information") {
    return "needs_more_information";
  }
  return "delivered";
}

function serviceReviewTransitionAllowed(currentStatus, decision) {
  if (decision === "approved") {
    return (
      SERVICE_REQUEST_QUEUED_STATUSES.has(currentStatus) ||
      currentStatus === "needs_more_information"
    );
  }
  if (decision === "needs_more_information") {
    return (
      SERVICE_REQUEST_QUEUED_STATUSES.has(currentStatus) ||
      currentStatus === "approved_operator_review"
    );
  }
  if (decision === "rejected") {
    return (
      SERVICE_REQUEST_QUEUED_STATUSES.has(currentStatus) ||
      currentStatus === "approved_operator_review" ||
      currentStatus === "needs_more_information"
    );
  }
  return currentStatus === "approved_operator_review";
}

async function buildServiceRequestReviewResponse(
  db,
  reviewRow,
  origin,
  env,
  status,
  idempotentReplay
) {
  const serviceRequestRow = await db
    .prepare(
      "SELECT * FROM gca_service_requests WHERE service_request_id = ?1 LIMIT 1"
    )
    .bind(reviewRow.service_request_id)
    .first();
  const creditUsageRow = reviewRow.credit_usage_id
    ? await db
        .prepare(
          "SELECT * FROM gca_credit_usage WHERE credit_usage_id = ?1 LIMIT 1"
        )
        .bind(reviewRow.credit_usage_id)
        .first()
    : null;
  const creditLedgerRow =
    serviceRequestRow && serviceRequestRow.credit_ledger_id
      ? await db
          .prepare(
            "SELECT * FROM gca_credit_ledger WHERE credit_ledger_id = ?1 LIMIT 1"
          )
          .bind(serviceRequestRow.credit_ledger_id)
          .first()
      : null;
  return jsonResponse({
    ok: true,
    packetVersion: SERVICE_REQUEST_REVIEW_VERSION,
    idempotentReplay,
    serviceRequestReview: rowToServiceRequestReview(reviewRow),
    serviceRequest: rowToServiceRequest(serviceRequestRow),
    creditUsage: rowToCreditUsage(creditUsageRow),
    creditLedger: rowToCreditLedger(creditLedgerRow),
    boundaries: serviceRequestReviewBoundaries()
  }, status, origin, env);
}

async function reviewServiceRequest(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse(
      { ok: false, error: "admin authorization is required" },
      401,
      origin,
      env
    );
  }
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const reviewInput = extractServiceRequestReview(packet);
  const reviewId = await stableId(
    "gca_service_review",
    reviewInput.serviceRequestId,
    reviewInput.clientReviewId
  );
  const existingReview = await db
    .prepare(
      `SELECT *
      FROM gca_service_request_reviews
      WHERE service_request_review_id = ?1
      LIMIT 1`
    )
    .bind(reviewId)
    .first();
  if (existingReview) {
    if (
      existingReview.service_request_id !==
        reviewInput.serviceRequestId ||
      existingReview.decision !== reviewInput.decision ||
      existingReview.reason_code !== reviewInput.reasonCode ||
      existingReview.reviewer_id !== reviewInput.reviewerId ||
      String(existingReview.operator_note || "") !==
        reviewInput.operatorNote ||
      String(existingReview.member_prompt || "") !==
        reviewInput.memberPrompt ||
      String(existingReview.delivery_reference || "") !==
        reviewInput.deliveryReference ||
      existingReview.source !== reviewInput.source
    ) {
      throw new ApiError(
        "clientReviewId is already assigned to a different review",
        409
      );
    }
    return buildServiceRequestReviewResponse(
      db,
      existingReview,
      origin,
      env,
      200,
      true
    );
  }

  const serviceRequestRow = await db
    .prepare(
      `SELECT *
      FROM gca_service_requests
      WHERE service_request_id = ?1
      LIMIT 1`
    )
    .bind(reviewInput.serviceRequestId)
    .first();
  if (!serviceRequestRow) {
    throw new ApiError("serviceRequestId was not found", 404);
  }
  const service = CREDIT_SERVICE_CATALOG[
    serviceRequestRow.service_id
  ];
  if (!service) {
    throw new ApiError(
      "service request uses an unsupported catalog item",
      409
    );
  }
  const currentStatus = String(serviceRequestRow.status || "");
  const currentLatestReviewId = String(
    serviceRequestRow.latest_review_id || ""
  );
  if (
    !serviceReviewTransitionAllowed(
      currentStatus,
      reviewInput.decision
    )
  ) {
    throw new ApiError(
      `service request cannot move from ${currentStatus} to ${reviewInput.decision}`,
      409
    );
  }

  const now = nowIso();
  const nextStatus = reviewDecisionStatus(reviewInput.decision);
  const creditAmountUsed =
    reviewInput.decision === "delivered"
      ? service.creditUnit
      : 0;
  const terminalCompletedAt = [
    "rejected",
    "delivered"
  ].includes(reviewInput.decision)
    ? now
    : "";
  let creditLedgerRow = null;
  let creditUsageId = "";
  let remainingBefore = null;
  let remainingAfter = null;

  if (reviewInput.decision === "delivered" && creditAmountUsed > 0) {
    if (!serviceRequestRow.credit_ledger_id) {
      throw new ApiError(
        "approved service request has no credit ledger",
        409
      );
    }
    creditLedgerRow = await db
      .prepare(
        "SELECT * FROM gca_credit_ledger WHERE credit_ledger_id = ?1 LIMIT 1"
      )
      .bind(serviceRequestRow.credit_ledger_id)
      .first();
    if (
      !creditLedgerRow ||
      creditLedgerRow.account_id !== serviceRequestRow.account_id ||
      creditLedgerRow.email_hash !== serviceRequestRow.email_hash ||
      creditLedgerRow.wallet_address !==
        serviceRequestRow.wallet_address
    ) {
      throw new ApiError(
        "service request and credit ledger do not match",
        409
      );
    }
    if (String(creditLedgerRow.expires_at || "") <= now) {
      throw new ApiError("credit ledger is expired", 409);
    }
    remainingBefore = Number(
      creditLedgerRow.remaining_credits || 0
    );
    if (
      !Number.isInteger(remainingBefore) ||
      remainingBefore < creditAmountUsed
    ) {
      throw new ApiError(
        "available credits are below the server catalog unit",
        409
      );
    }
    remainingAfter = remainingBefore - creditAmountUsed;
    creditUsageId = await stableId(
      "gca_credit_use",
      reviewInput.serviceRequestId
    );
    const existingUsage = await db
      .prepare(
        `SELECT *
        FROM gca_credit_usage
        WHERE service_request_id = ?1
        LIMIT 1`
      )
      .bind(reviewInput.serviceRequestId)
      .first();
    if (existingUsage) {
      throw new ApiError(
        "service request credit settlement is already recorded",
        409
      );
    }
  }

  let batchResults;
  if (
    reviewInput.decision === "delivered" &&
    creditAmountUsed > 0
  ) {
    const creditUsageStatus =
      remainingAfter === 0 ? "exhausted" : "usage_recorded";
    const creditLedgerStatus =
      remainingAfter === 0 ? "exhausted" : "ledger_recorded";
    const insertUsage = db
      .prepare(
        `INSERT INTO gca_credit_usage (
          credit_usage_id,
          credit_ledger_id,
          account_id,
          email_hash,
          wallet_address,
          service_id,
          service_name,
          credit_amount_used,
          remaining_credits_before,
          remaining_credits_after,
          used_at,
          source,
          operator_note,
          status,
          requires_signature,
          requires_transaction,
          automatic_token_transfer,
          writes_wallet,
          service_request_id
        )
        SELECT
          ?1,
          credit.credit_ledger_id,
          credit.account_id,
          credit.email_hash,
          credit.wallet_address,
          service.service_id,
          service.service_name,
          ?2,
          ?3,
          ?4,
          ?5,
          'gca-service-request-reviewed-delivery',
          ?6,
          ?7,
          0,
          0,
          0,
          0,
          service.service_request_id
        FROM gca_service_requests AS service
        INNER JOIN gca_credit_ledger AS credit
          ON credit.credit_ledger_id = service.credit_ledger_id
        WHERE service.service_request_id = ?8
          AND service.status = ?9
          AND service.latest_review_id = ?10
          AND credit.remaining_credits = ?3
          AND credit.expires_at > ?5
          AND NOT EXISTS (
            SELECT 1
            FROM gca_credit_usage
            WHERE service_request_id = ?8
          )`
      )
      .bind(
        creditUsageId,
        creditAmountUsed,
        remainingBefore,
        remainingAfter,
        now,
        reviewInput.operatorNote,
        creditUsageStatus,
        reviewInput.serviceRequestId,
        currentStatus,
        currentLatestReviewId
      );
    const updateCreditLedger = db
      .prepare(
        `UPDATE gca_credit_ledger
        SET remaining_credits = ?1,
            status = ?2
        WHERE credit_ledger_id = ?3
          AND remaining_credits = ?4
          AND EXISTS (
            SELECT 1
            FROM gca_credit_usage
            WHERE credit_usage_id = ?5
              AND service_request_id = ?6
          )`
      )
      .bind(
        remainingAfter,
        creditLedgerStatus,
        serviceRequestRow.credit_ledger_id,
        remainingBefore,
        creditUsageId,
        reviewInput.serviceRequestId
      );
    const insertReview = db
      .prepare(
        `INSERT INTO gca_service_request_reviews (
          service_request_review_id,
          service_request_id,
          packet_version,
          decision,
          reason_code,
          reviewer_id,
          operator_note,
          member_prompt,
          delivery_reference,
          credit_usage_id,
          credit_amount_used,
          remaining_credits_before,
          remaining_credits_after,
          reviewed_at,
          source,
          manual_review_completed,
          delivery_completed,
          credits_deducted,
          requires_signature,
          requires_transaction,
          automatic_token_transfer,
          writes_wallet,
          creates_trading_permission
        )
        SELECT
          ?1, service_request_id, ?2, ?3, ?4, ?5, ?6, ?7, ?8,
          ?9, ?10, ?11, ?12, ?13, ?14, 1, 1, 1, 0, 0, 0, 0, 0
        FROM gca_service_requests
        WHERE service_request_id = ?15
          AND status = ?16
          AND latest_review_id = ?17
          AND EXISTS (
            SELECT 1
            FROM gca_credit_usage
            WHERE credit_usage_id = ?9
              AND service_request_id = ?15
          )`
      )
      .bind(
        reviewId,
        SERVICE_REQUEST_REVIEW_VERSION,
        reviewInput.decision,
        reviewInput.reasonCode,
        reviewInput.reviewerId,
        reviewInput.operatorNote,
        reviewInput.memberPrompt,
        reviewInput.deliveryReference,
        creditUsageId,
        creditAmountUsed,
        remainingBefore,
        remainingAfter,
        now,
        reviewInput.source,
        reviewInput.serviceRequestId,
        currentStatus,
        currentLatestReviewId
      );
    const updateServiceRequest = db
      .prepare(
        `UPDATE gca_service_requests
        SET status = ?1,
            latest_review_id = ?2,
            reviewed_at = ?3,
            completed_at = ?3,
            updated_at = ?3,
            credit_usage_id = ?4,
            does_not_deduct_credits = 0
        WHERE service_request_id = ?5
          AND status = ?6
          AND latest_review_id = ?7
          AND EXISTS (
            SELECT 1
            FROM gca_service_request_reviews
            WHERE service_request_review_id = ?2
              AND credit_usage_id = ?4
          )`
      )
      .bind(
        nextStatus,
        reviewId,
        now,
        creditUsageId,
        reviewInput.serviceRequestId,
        currentStatus,
        currentLatestReviewId
      );
    try {
      batchResults = await db.batch([
        insertUsage,
        updateCreditLedger,
        insertReview,
        updateServiceRequest
      ]);
    } catch (error) {
      const concurrentUsage = await db
        .prepare(
          `SELECT credit_usage_id
          FROM gca_credit_usage
          WHERE service_request_id = ?1
          LIMIT 1`
        )
        .bind(reviewInput.serviceRequestId)
        .first();
      if (concurrentUsage) {
        throw new ApiError(
          "service request credit settlement changed; reload before retrying",
          409
        );
      }
      throw error;
    }
    if (
      batchResults.some(
        (result) => Number(result?.meta?.changes || 0) !== 1
      )
    ) {
      throw new ApiError(
        "service request delivery changed; reload before retrying",
        409
      );
    }
  } else {
    const deliveryCompleted =
      reviewInput.decision === "delivered" ? 1 : 0;
    const insertReview = db
      .prepare(
        `INSERT INTO gca_service_request_reviews (
          service_request_review_id,
          service_request_id,
          packet_version,
          decision,
          reason_code,
          reviewer_id,
          operator_note,
          member_prompt,
          delivery_reference,
          credit_usage_id,
          credit_amount_used,
          remaining_credits_before,
          remaining_credits_after,
          reviewed_at,
          source,
          manual_review_completed,
          delivery_completed,
          credits_deducted,
          requires_signature,
          requires_transaction,
          automatic_token_transfer,
          writes_wallet,
          creates_trading_permission
        )
        SELECT
          ?1, service_request_id, ?2, ?3, ?4, ?5, ?6, ?7, ?8,
          '', 0, NULL, NULL, ?9, ?10, 1, ?11, 0, 0, 0, 0, 0, 0
        FROM gca_service_requests
        WHERE service_request_id = ?12
          AND status = ?13
          AND latest_review_id = ?14`
      )
      .bind(
        reviewId,
        SERVICE_REQUEST_REVIEW_VERSION,
        reviewInput.decision,
        reviewInput.reasonCode,
        reviewInput.reviewerId,
        reviewInput.operatorNote,
        reviewInput.memberPrompt,
        reviewInput.deliveryReference,
        now,
        reviewInput.source,
        deliveryCompleted,
        reviewInput.serviceRequestId,
        currentStatus,
        currentLatestReviewId
      );
    const updateServiceRequest = db
      .prepare(
        `UPDATE gca_service_requests
        SET status = ?1,
            latest_review_id = ?2,
            reviewed_at = ?3,
            completed_at = CASE
              WHEN ?4 <> '' THEN ?4
              ELSE completed_at
            END,
            updated_at = ?3,
            credit_usage_id = '',
            does_not_deduct_credits = 1
        WHERE service_request_id = ?5
          AND status = ?6
          AND latest_review_id = ?7
          AND EXISTS (
            SELECT 1
            FROM gca_service_request_reviews
            WHERE service_request_review_id = ?2
          )`
      )
      .bind(
        nextStatus,
        reviewId,
        now,
        terminalCompletedAt,
        reviewInput.serviceRequestId,
        currentStatus,
        currentLatestReviewId
      );
    batchResults = await db.batch([
      insertReview,
      updateServiceRequest
    ]);
    if (
      batchResults.some(
        (result) => Number(result?.meta?.changes || 0) !== 1
      )
    ) {
      throw new ApiError(
        "service request review changed; reload before retrying",
        409
      );
    }
  }

  const reviewRow = await db
    .prepare(
      `SELECT *
      FROM gca_service_request_reviews
      WHERE service_request_review_id = ?1
      LIMIT 1`
    )
    .bind(reviewId)
    .first();
  if (!reviewRow) {
    throw new ApiError(
      "service request review was not recorded",
      409
    );
  }
  return buildServiceRequestReviewResponse(
    db,
    reviewRow,
    origin,
    env,
    201,
    false
  );
}

async function maybeWriteMemberLedger(db, account, verification, evidence, now) {
  if (!verification.gcaMemberEligible) {
    return null;
  }
  const memberLedgerId = await stableId("gca_member", account.email, account.walletAddress);
  const evidenceStatus = verification.holdingPeriodPreviewEligible
    ? "pending_manual_review"
    : "needs_more_information";
  const status = "queued";
  const activatedAt = "";
  const nextRefreshDueAt = "";
  const claimStatus = verification.holdingPeriodPreviewEligible
    ? "pending_manual_review"
    : "needs_holding_period_review";
  await db
    .prepare(
      `INSERT INTO gca_member_ledger (
        member_ledger_id,
        account_id,
        email_hash,
        wallet_address,
        tier_name,
        verified_balance,
        holding_start_date,
        holding_period_days_verified,
        evidence_tx_hash,
        evidence_tx_hash_format_ok,
        member_benefit_review_evidence_status,
        member_benefit_amount,
        member_benefit_claim_status,
        member_benefit_transfer_tx,
        activated_at,
        next_refresh_due_at,
        requires_manual_reserve_transfer_review,
        automatic_transfer,
        status,
        updated_at
      ) VALUES (?1, ?2, ?3, ?4, 'GCA Member', ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, '', ?13, ?14, 1, 0, ?15, ?16)
      ON CONFLICT(member_ledger_id) DO UPDATE SET
        verified_balance = excluded.verified_balance,
        holding_start_date = excluded.holding_start_date,
        holding_period_days_verified = excluded.holding_period_days_verified,
        evidence_tx_hash = excluded.evidence_tx_hash,
        evidence_tx_hash_format_ok = excluded.evidence_tx_hash_format_ok,
        member_benefit_review_evidence_status = CASE
          WHEN gca_member_ledger.status = 'active' THEN gca_member_ledger.member_benefit_review_evidence_status
          ELSE excluded.member_benefit_review_evidence_status
        END,
        member_benefit_claim_status = CASE
          WHEN gca_member_ledger.status = 'active' THEN gca_member_ledger.member_benefit_claim_status
          ELSE excluded.member_benefit_claim_status
        END,
        activated_at = CASE
          WHEN gca_member_ledger.activated_at IS NOT NULL AND gca_member_ledger.activated_at != '' THEN gca_member_ledger.activated_at
          ELSE excluded.activated_at
        END,
        next_refresh_due_at = CASE
          WHEN gca_member_ledger.status = 'active' THEN gca_member_ledger.next_refresh_due_at
          ELSE excluded.next_refresh_due_at
        END,
        status = CASE
          WHEN gca_member_ledger.status = 'active' THEN gca_member_ledger.status
          ELSE excluded.status
        END,
        updated_at = excluded.updated_at`
    )
    .bind(
      memberLedgerId,
      account.accountId,
      account.emailHash,
      account.walletAddress,
      verification.gcaBalance,
      evidence.holdingStartDate,
      evidence.holdingPeriodDaysVerified,
      evidence.evidenceTxHash,
      evidence.evidenceTxHashFormatOk ? 1 : 0,
      evidenceStatus,
      MEMBER_BENEFIT_AMOUNT,
      claimStatus,
      activatedAt,
      nextRefreshDueAt,
      status,
      now
    )
    .run();
  const row = await db
    .prepare("SELECT * FROM gca_member_ledger WHERE member_ledger_id = ?1 LIMIT 1")
    .bind(memberLedgerId)
    .first();
  return rowToMemberLedger(row);
}

async function prepareHoldingVerificationInsert(db, memberRow, verification) {
  const holdingVerificationId = await stableId(
    "gca_holding",
    memberRow.member_ledger_id,
    verification.snapshotBlockNumber,
    verification.snapshotBlockHash
  );
  const statement = db
    .prepare(
      `INSERT OR IGNORE INTO gca_holding_verifications (
        holding_verification_id,
        member_ledger_id,
        account_id,
        wallet_address,
        chain_id,
        contract_address,
        checked_at,
        window_start_at,
        window_end_at,
        snapshot_block_number,
        snapshot_block_hash,
        current_raw_balance,
        current_gca_balance,
        window_start_raw_balance,
        window_start_gca_balance,
        minimum_raw_balance,
        minimum_gca_balance,
        threshold_raw_balance,
        threshold_gca_balance,
        observed_continuous_eligible,
        history_complete,
        reconstruction_consistent,
        event_count,
        blockscout_event_count,
        rpc_event_count,
        history_provider,
        status,
        failure_reason,
        requires_signature,
        requires_transaction,
        automatic_token_transfer,
        writes_wallet
      ) VALUES (
        ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16,
        ?17, ?18, ?19, ?20, ?21, ?22, ?23, ?24, ?25, ?26, ?27, ?28, 0, 0, 0, 0
      )`
    )
    .bind(
      holdingVerificationId,
      memberRow.member_ledger_id,
      memberRow.account_id,
      memberRow.wallet_address,
      CHAIN_ID,
      CONTRACT_ADDRESS,
      verification.checkedAt,
      verification.windowStartAt,
      verification.windowEndAt,
      verification.snapshotBlockNumber,
      verification.snapshotBlockHash,
      verification.currentRawBalance,
      verification.currentGcaBalance,
      verification.windowStartRawBalance,
      verification.windowStartGcaBalance,
      verification.minimumRawBalance,
      verification.minimumGcaBalance,
      verification.thresholdRawBalance,
      verification.thresholdGcaBalance,
      verification.observedContinuousEligible ? 1 : 0,
      verification.historyComplete ? 1 : 0,
      verification.reconstructionConsistent ? 1 : 0,
      verification.eventCount,
      verification.blockscoutEventCount,
      verification.rpcEventCount,
      verification.historyProvider,
      verification.status,
      verification.failureReason
    );
  return {
    holdingVerificationId,
    statement
  };
}

async function recordMemberReview(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse({ ok: false, error: "admin authorization is required" }, 401, origin, env);
  }
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const reviewInput = extractMemberReview(packet);
  const memberRow = await db
    .prepare("SELECT * FROM gca_member_ledger WHERE member_ledger_id = ?1 LIMIT 1")
    .bind(reviewInput.memberLedgerId)
    .first();
  if (!memberRow) {
    throw new ApiError("memberLedgerId was not found", 404);
  }

  const approved = reviewInput.decision === "approved";
  const rejected = reviewInput.decision === "rejected";
  const holdingVerification = approved
    ? await verifyGcaHoldingWindow(memberRow, env)
    : null;
  const rawBalance = holdingVerification
    ? BigInt(holdingVerification.currentRawBalance)
    : await readGcaBalanceUnits(memberRow.wallet_address, env);
  const balanceAtReview = unitsToGca(rawBalance);
  const memberThresholdMet = rawBalance >= MEMBER_THRESHOLD_UNITS;
  const holdingPeriodPreviewDays = Math.max(
    Number(memberRow.holding_period_days_verified || 0),
    holdingDaysFromDate(memberRow.holding_start_date || "")
  );
  const evidenceTxHashFormatOk = Boolean(memberRow.evidence_tx_hash_format_ok);
  if (
    approved &&
    (
      !memberThresholdMet ||
      holdingPeriodPreviewDays < MEMBER_HOLD_DAYS ||
      !evidenceTxHashFormatOk ||
      !holdingVerification ||
      !holdingVerification.historyComplete ||
      !holdingVerification.reconstructionConsistent ||
      !holdingVerification.observedContinuousEligible
    )
  ) {
    throw new ApiError(
      "approved review requires a current 1,000,000 GCA balance, valid submitted evidence, and an observed complete 30-day on-chain holding history",
      409
    );
  }

  const previousMemberStatus = memberRow.status;
  const previousClaimStatus = memberRow.member_benefit_claim_status;
  const resultingMemberStatus = approved ? "active" : rejected ? "review_rejected" : "queued";
  const resultingAccountStatus = approved ? "member_active" : rejected ? "member_review_rejected" : "member_queued";
  const resultingClaimStatus = approved
    ? "pending_manual_reserve_transfer"
    : rejected
      ? "not_eligible"
      : "needs_holding_period_review";
  const evidenceStatus = approved
    ? "approved_manual_review"
    : rejected
      ? "rejected_manual_review"
      : "needs_more_information";
  const now = nowIso();
  const activatedAt = approved ? (memberRow.activated_at || now) : "";
  const nextRefreshDueAt = approved ? addDaysIso(now, MEMBER_REFRESH_DAYS) : "";
  const preparedHoldingVerification = approved
    ? await prepareHoldingVerificationInsert(db, memberRow, holdingVerification)
    : null;
  const holdingVerificationId = preparedHoldingVerification
    ? preparedHoldingVerification.holdingVerificationId
    : "";
  const memberReviewId = await stableId(
    "gca_member_review",
    reviewInput.memberLedgerId,
    reviewInput.decision,
    reviewInput.reasonCode,
    reviewInput.reviewerId,
    now
  );

  const insertReview = db
    .prepare(
      `INSERT OR IGNORE INTO gca_member_reviews (
        member_review_id,
        member_ledger_id,
        account_id,
        wallet_address,
        decision,
        reason_code,
        operator_note,
        reviewer_id,
        reviewed_at,
        source,
        balance_at_review,
        member_threshold_met,
        holding_period_preview_days,
        evidence_tx_hash,
        evidence_tx_hash_format_ok,
        holding_verification_id,
        onchain_holding_eligible,
        onchain_history_complete,
        onchain_minimum_balance,
        previous_member_status,
        resulting_member_status,
        previous_claim_status,
        resulting_claim_status,
        requires_signature,
        requires_transaction,
        automatic_token_transfer,
        writes_wallet
      ) VALUES (
        ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16,
        ?17, ?18, ?19, ?20, ?21, ?22, ?23, 0, 0, 0, 0
      )`
    )
    .bind(
      memberReviewId,
      memberRow.member_ledger_id,
      memberRow.account_id,
      memberRow.wallet_address,
      reviewInput.decision,
      reviewInput.reasonCode,
      reviewInput.operatorNote,
      reviewInput.reviewerId,
      now,
      reviewInput.source,
      balanceAtReview,
      memberThresholdMet ? 1 : 0,
      holdingPeriodPreviewDays,
      memberRow.evidence_tx_hash || "",
      evidenceTxHashFormatOk ? 1 : 0,
      holdingVerificationId,
      holdingVerification && holdingVerification.observedContinuousEligible ? 1 : 0,
      holdingVerification && holdingVerification.historyComplete ? 1 : 0,
      holdingVerification ? holdingVerification.minimumGcaBalance : "",
      previousMemberStatus,
      resultingMemberStatus,
      previousClaimStatus,
      resultingClaimStatus
    );
  const updateMemberLedger = db
    .prepare(
      `UPDATE gca_member_ledger
       SET
         verified_balance = ?1,
         holding_period_days_verified = ?2,
         member_benefit_review_evidence_status = ?3,
         member_benefit_claim_status = ?4,
         activated_at = ?5,
         next_refresh_due_at = ?6,
         latest_holding_verification_id = ?7,
         onchain_holding_verified = ?8,
         onchain_holding_verified_at = ?9,
         status = ?10,
         updated_at = ?11
       WHERE member_ledger_id = ?12`
    )
    .bind(
      balanceAtReview,
      approved ? Math.max(holdingPeriodPreviewDays, MEMBER_HOLD_DAYS) : holdingPeriodPreviewDays,
      evidenceStatus,
      resultingClaimStatus,
      activatedAt,
      nextRefreshDueAt,
      approved ? holdingVerificationId : (memberRow.latest_holding_verification_id || ""),
      approved ? 1 : Number(memberRow.onchain_holding_verified || 0),
      approved ? holdingVerification.checkedAt : (memberRow.onchain_holding_verified_at || ""),
      resultingMemberStatus,
      now,
      memberRow.member_ledger_id
    );
  const updateMemberAccount = db
    .prepare(
      "UPDATE gca_member_accounts SET status = ?1, updated_at = ?2 WHERE account_id = ?3"
    )
    .bind(resultingAccountStatus, now, memberRow.account_id);

  const reviewBatch = [insertReview, updateMemberLedger, updateMemberAccount];
  if (preparedHoldingVerification) {
    reviewBatch.unshift(preparedHoldingVerification.statement);
  }
  await db.batch(reviewBatch);

  const reviewRow = await db
    .prepare("SELECT * FROM gca_member_reviews WHERE member_review_id = ?1 LIMIT 1")
    .bind(memberReviewId)
    .first();
  const updatedMemberRow = await db
    .prepare("SELECT * FROM gca_member_ledger WHERE member_ledger_id = ?1 LIMIT 1")
    .bind(memberRow.member_ledger_id)
    .first();
  const holdingVerificationRow = holdingVerificationId
    ? await db
        .prepare("SELECT * FROM gca_holding_verifications WHERE holding_verification_id = ?1 LIMIT 1")
        .bind(holdingVerificationId)
        .first()
    : null;
  return jsonResponse({
    ok: true,
    packetVersion: MEMBER_REVIEW_VERSION,
    memberReview: rowToMemberReview(reviewRow),
    memberLedger: rowToMemberLedger(updatedMemberRow),
    holdingVerification: rowToHoldingVerification(holdingVerificationRow),
    nextStep: approved
      ? "Membership is active after the observed 30-day on-chain holding history check. Any 10,000 GCA member benefit still requires a separate manual reserve-wallet transfer review and public transaction evidence."
      : rejected
        ? "Membership is not active. No member benefit transfer is authorized."
        : "Membership remains queued until the missing holding evidence is reviewed.",
    boundaries: {
      adminOnly: true,
      manualEvidenceReviewRequired: true,
      readOnlyBalanceRefresh: true,
      readOnlyHoldingHistoryVerification: true,
      holdingHistorySource: "Base Blockscout v2 plus Base public RPC",
      holdingHistoryClaim: "observed transfer-history reconstruction, not a third-party audit or guarantee",
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false,
      writesWallet: false,
      authorizesMemberBenefitTransfer: false,
      createsTradingPermission: false
    }
  }, 201, origin, env);
}

async function recordMemberBenefitTransfer(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse({ ok: false, error: "admin authorization is required" }, 401, origin, env);
  }
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const transferInput = extractMemberBenefitTransfer(packet);
  const memberRow = await db
    .prepare("SELECT * FROM gca_member_ledger WHERE member_ledger_id = ?1 LIMIT 1")
    .bind(transferInput.memberLedgerId)
    .first();
  if (!memberRow) {
    throw new ApiError("memberLedgerId was not found", 404);
  }

  const existingForMember = await db
    .prepare("SELECT * FROM gca_member_benefit_transfers WHERE member_ledger_id = ?1 LIMIT 1")
    .bind(memberRow.member_ledger_id)
    .first();
  if (existingForMember) {
    if (existingForMember.transaction_hash !== transferInput.transactionHash) {
      throw new ApiError("member benefit transfer is already recorded with a different transaction", 409);
    }
    return jsonResponse({
      ok: true,
      alreadyRecorded: true,
      memberBenefitTransfer: rowToMemberBenefitTransfer(existingForMember),
      memberLedger: rowToMemberLedger(memberRow),
      boundaries: {
        adminOnly: true,
        verifiesExistingTransactionOnly: true,
        requiresSignature: false,
        requiresTransaction: false,
        automaticTokenTransfer: false,
        writesWallet: false
      }
    }, 200, origin, env);
  }

  if (memberRow.status !== "active") {
    throw new ApiError("member ledger must be active before transfer evidence can be recorded", 409);
  }
  if (!Number(memberRow.onchain_holding_verified || 0) || !memberRow.latest_holding_verification_id) {
    throw new ApiError("member ledger must have verified 30-day on-chain holding evidence", 409);
  }
  if (memberRow.member_benefit_claim_status !== "pending_manual_reserve_transfer") {
    throw new ApiError("member benefit is not pending manual reserve transfer", 409);
  }
  if (memberRow.member_benefit_amount !== MEMBER_BENEFIT_AMOUNT) {
    throw new ApiError("member benefit amount does not match the 10,000 GCA program rule", 409);
  }

  const existingTransaction = await db
    .prepare("SELECT * FROM gca_member_benefit_transfers WHERE transaction_hash = ?1 LIMIT 1")
    .bind(transferInput.transactionHash)
    .first();
  if (existingTransaction) {
    throw new ApiError("transactionHash is already assigned to another member benefit record", 409);
  }

  const evidence = await verifyMemberBenefitTransfer(
    memberRow,
    transferInput.transactionHash,
    env
  );
  const transferRecordId = await stableId(
    "gca_benefit_transfer",
    memberRow.member_ledger_id,
    transferInput.transactionHash
  );
  const insertTransfer = db
    .prepare(
      `INSERT INTO gca_member_benefit_transfers (
        transfer_record_id,
        packet_version,
        member_ledger_id,
        account_id,
        wallet_address,
        source_wallet,
        recipient_wallet,
        chain_id,
        contract_address,
        transaction_hash,
        receipt_block_number,
        receipt_block_hash,
        safe_snapshot_block_number,
        safe_snapshot_block_hash,
        transfer_log_index,
        amount_raw,
        amount_gca,
        verification_provider,
        verification_status,
        verified_at,
        reviewer_id,
        reason_code,
        operator_note,
        source,
        requires_signature,
        requires_transaction,
        automatic_token_transfer,
        writes_wallet
      ) VALUES (
        ?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16,
        ?17, ?18, ?19, ?20, ?21, ?22, ?23, ?24, 0, 0, 0, 0
      )`
    )
    .bind(
      transferRecordId,
      MEMBER_BENEFIT_TRANSFER_VERSION,
      memberRow.member_ledger_id,
      memberRow.account_id,
      memberRow.wallet_address,
      MEMBER_BENEFIT_SOURCE_WALLET,
      memberRow.wallet_address,
      CHAIN_ID,
      CONTRACT_ADDRESS,
      transferInput.transactionHash,
      evidence.receiptBlockNumber,
      evidence.receiptBlockHash,
      evidence.safeSnapshotBlockNumber,
      evidence.safeSnapshotBlockHash,
      evidence.transferLogIndex,
      evidence.amountUnits,
      evidence.amountGca,
      evidence.verificationProvider,
      evidence.status,
      evidence.checkedAt,
      transferInput.reviewerId,
      transferInput.reasonCode,
      transferInput.operatorNote,
      transferInput.source
    );
  const updateMember = db
    .prepare(
      `UPDATE gca_member_ledger
       SET
         member_benefit_claim_status = 'transferred',
         member_benefit_transfer_tx = ?1,
         member_benefit_transfer_record_id = ?2,
         member_benefit_transfer_verified_at = ?3,
         member_benefit_transfer_verification_status = ?4,
         requires_manual_reserve_transfer_review = 0,
         automatic_transfer = 0,
         updated_at = ?3
       WHERE member_ledger_id = ?5`
    )
    .bind(
      transferInput.transactionHash,
      transferRecordId,
      evidence.checkedAt,
      evidence.status,
      memberRow.member_ledger_id
    );
  await db.batch([insertTransfer, updateMember]);

  const transferRow = await db
    .prepare("SELECT * FROM gca_member_benefit_transfers WHERE transfer_record_id = ?1 LIMIT 1")
    .bind(transferRecordId)
    .first();
  const updatedMemberRow = await db
    .prepare("SELECT * FROM gca_member_ledger WHERE member_ledger_id = ?1 LIMIT 1")
    .bind(memberRow.member_ledger_id)
    .first();
  return jsonResponse({
    ok: true,
    alreadyRecorded: false,
    packetVersion: MEMBER_BENEFIT_TRANSFER_VERSION,
    memberBenefitTransfer: rowToMemberBenefitTransfer(transferRow),
    memberLedger: rowToMemberLedger(updatedMemberRow),
    nextStep: "The already-completed manual reserve-wallet transfer is recorded with safe Base transaction evidence. No additional GCA transfer is authorized.",
    boundaries: {
      adminOnly: true,
      officialSourceWalletRequired: MEMBER_BENEFIT_SOURCE_WALLET,
      exactTransferAmountRequired: MEMBER_BENEFIT_AMOUNT,
      safeBlockConfirmationRequired: true,
      verifiesExistingTransactionOnly: true,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false,
      writesWallet: false,
      authorizesAdditionalTransfer: false
    }
  }, 201, origin, env);
}

async function submitWalletVerification(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const walletAddress = normalizeWallet(packet.walletAddress || "");
  const evidence = extractMemberEvidence(packet);
  const now = nowIso();
  const rawBalance = await readGcaBalanceUnits(walletAddress, env);
  const verification = await writeWalletVerification(
    db,
    String(packet.accountId || ""),
    "",
    walletAddress,
    rawBalance,
    evidence,
    now
  );
  return jsonResponse({
    ok: true,
    walletVerification: verification,
    thresholds: accessThresholds(),
    nextStep: verification.holderBonusEligible
      ? "Wallet balance verification passed. Submit the account form to write credits and member ledger records."
      : "Wallet balance is below 10,000 GCA. No credit or member ledger record was created."
  }, 200, origin, env);
}

async function submitMemberAccess(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const accountInput = extractMemberAccess(packet);
  const now = nowIso();
  const emailHash = await sha256Hex(accountInput.email);
  const ipHash = await optionalIpHash(request, env);
  const userAgent = String(request.headers.get("user-agent") || "").slice(0, 300);
  const accountId = await stableId("gca_account", accountInput.email, accountInput.walletAddress);
  const existingAccountRow = await db
    .prepare("SELECT account_id FROM gca_member_accounts WHERE account_id = ?1 LIMIT 1")
    .bind(accountId)
    .first();
  const existingStatusAccess = await db
    .prepare("SELECT * FROM gca_account_status_access WHERE account_id = ?1 LIMIT 1")
    .bind(accountId)
    .first();
  let statusAccessExpiresAt = existingStatusAccess ? existingStatusAccess.expires_at : "";
  let statusAccessTokenHash = "";

  if (accountInput.packetVersion === MEMBER_ACCESS_VERSION) {
    statusAccessTokenHash = await sha256Hex(accountInput.statusAccessToken);
    const statusAccessTokenOwner = await db
      .prepare("SELECT account_id FROM gca_account_status_access WHERE token_hash = ?1 LIMIT 1")
      .bind(statusAccessTokenHash)
      .first();
    if (statusAccessTokenOwner && statusAccessTokenOwner.account_id !== accountId) {
      throw new ApiError(
        "device status access key is already assigned to another account",
        409
      );
    }
    if (existingStatusAccess) {
      const revoked = Boolean(String(existingStatusAccess.revoked_at || "").trim());
      const expired = String(existingStatusAccess.expires_at || "") <= now;
      const tokenMismatch = existingStatusAccess.token_hash !== statusAccessTokenHash;
      if (revoked || expired || tokenMismatch) {
        throw new ApiError("device status access key is invalid or expired", 401);
      }
    } else if (existingAccountRow) {
      throw new ApiError(
        "this existing account needs official support to enable device status access",
        409
      );
    }
  } else if (existingStatusAccess) {
    throw new ApiError(`packetVersion ${MEMBER_ACCESS_VERSION} is required for this account`, 426);
  }

  const rawBalance = await readGcaBalanceUnits(accountInput.walletAddress, env);
  const classification = classifyWalletBalance(rawBalance, accountInput.memberEvidence);

  await db
    .prepare(
      `INSERT OR IGNORE INTO gca_email_registrations (
        email_registration_id,
        email,
        email_hash,
        display_name,
        source,
        language,
        interests_json,
        contact_consent_accepted,
        security_boundary_accepted,
        status,
        created_at,
        updated_at,
        user_agent,
        ip_hash,
        wallet_required,
        requires_signature,
        requires_transaction,
        automatic_token_transfer
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, 1, 1, 'received', ?8, ?8, ?9, ?10, 0, 0, 0, 0)`
    )
    .bind(
      await stableId("gca_email", accountInput.email),
      accountInput.email,
      emailHash,
      accountInput.displayName,
      accountInput.source,
      accountInput.language,
      JSON.stringify(["gca_updates", "member_access"]),
      now,
      userAgent,
      ipHash
    )
    .run();

  await db
    .prepare(
      `INSERT INTO gca_member_accounts (
        account_id,
        email,
        email_hash,
        wallet_address,
        display_name,
        source,
        language,
        program_intent,
        holding_start_date,
        evidence_tx_hash,
        contact_consent_accepted,
        security_boundary_accepted,
        status,
        created_at,
        updated_at,
        user_agent,
        ip_hash,
        requires_signature,
        requires_transaction,
        automatic_token_transfer
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, 1, 1, ?11, ?12, ?12, ?13, ?14, 0, 0, 0)
      ON CONFLICT(account_id) DO UPDATE SET
        display_name = excluded.display_name,
        source = excluded.source,
        language = excluded.language,
        program_intent = excluded.program_intent,
        holding_start_date = excluded.holding_start_date,
        evidence_tx_hash = excluded.evidence_tx_hash,
        status = CASE
          WHEN gca_member_accounts.status = 'member_active' THEN gca_member_accounts.status
          ELSE excluded.status
        END,
        updated_at = excluded.updated_at,
        user_agent = excluded.user_agent,
        ip_hash = excluded.ip_hash`
    )
    .bind(
      accountId,
      accountInput.email,
      emailHash,
      accountInput.walletAddress,
      accountInput.displayName,
      accountInput.source,
      accountInput.language,
      accountInput.programIntent,
      accountInput.memberEvidence.holdingStartDate,
      accountInput.memberEvidence.evidenceTxHash,
      classification.accountStatus,
      now,
      userAgent,
      ipHash
    )
    .run();

  if (accountInput.packetVersion === MEMBER_ACCESS_VERSION && !existingStatusAccess) {
    statusAccessExpiresAt = addDaysIso(now, ACCOUNT_STATUS_ACCESS_DAYS);
    const statusAccessId = await stableId("gca_status_access", accountId);
    await db
      .prepare(
        `INSERT OR IGNORE INTO gca_account_status_access (
          status_access_id,
          packet_version,
          account_id,
          token_hash,
          created_at,
          expires_at,
          revoked_at,
          source,
          read_only,
          returns_email,
          returns_token,
          requires_signature,
          requires_transaction,
          automatic_token_transfer
        ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, '', ?7, 1, 0, 0, 0, 0, 0)`
      )
      .bind(
        statusAccessId,
        ACCOUNT_STATUS_VERSION,
        accountId,
        statusAccessTokenHash,
        now,
        statusAccessExpiresAt,
        accountInput.source
      )
      .run();
    const storedStatusAccess = await db
      .prepare("SELECT token_hash, expires_at FROM gca_account_status_access WHERE account_id = ?1 LIMIT 1")
      .bind(accountId)
      .first();
    if (!storedStatusAccess || storedStatusAccess.token_hash !== statusAccessTokenHash) {
      throw new ApiError("device status access setup conflict; contact official support", 409);
    }
    statusAccessExpiresAt = storedStatusAccess.expires_at;
  }

  const verification = await writeWalletVerification(
    db,
    accountId,
    emailHash,
    accountInput.walletAddress,
    rawBalance,
    accountInput.memberEvidence,
    now
  );
  const account = {
    accountId,
    email: accountInput.email,
    emailHash,
    walletAddress: accountInput.walletAddress
  };
  const creditLedger = await maybeWriteCreditLedger(db, account, verification, now);
  const memberLedger = await maybeWriteMemberLedger(db, account, verification, accountInput.memberEvidence, now);
  const accountRow = await db
    .prepare("SELECT * FROM gca_member_accounts WHERE account_id = ?1 LIMIT 1")
    .bind(accountId)
    .first();

  return jsonResponse({
    ok: true,
    account: rowToMemberAccount(accountRow),
    walletVerification: verification,
    creditLedger,
    memberLedger,
    statusAccess: {
      enabled: accountInput.packetVersion === MEMBER_ACCESS_VERSION,
      packetVersion: ACCOUNT_STATUS_VERSION,
      endpoint: "/gca/account-status",
      expiresAt: statusAccessExpiresAt,
      accessTokenReturned: false,
      savedOnDeviceRequired: accountInput.packetVersion === MEMBER_ACCESS_VERSION
    },
    thresholds: accessThresholds(),
    boundaries: accessBoundaries(),
    nextStep: memberLedger && memberLedger.status === "active"
      ? "100 credits and GCA Member ledger records are active. The 10,000 GCA member benefit remains pending manual reserve-wallet transfer review."
      : memberLedger && verification.holdingPeriodPreviewEligible
        ? "GCA Member evidence is queued for manual operator review. The submitted holding date and transaction hash format do not activate membership automatically."
      : creditLedger
        ? "100 credits ledger is active. GCA Member needs 1,000,000 GCA and valid 30-day holding evidence."
        : "Wallet balance is below 10,000 GCA. No credit or member ledger record was created."
  }, 201, origin, env);
}

function accountStatusNextStep(walletVerification, creditLedger, memberLedger) {
  if (
    memberLedger &&
    memberLedger.memberBenefitClaimStatus === "transferred" &&
    memberLedger.memberBenefitTransferVerificationStatus === "verified"
  ) {
    return "The one-time 10,000 GCA member-benefit transfer has verified public transaction evidence.";
  }
  if (memberLedger && memberLedger.status === "active") {
    return "GCA Member is active. Any pending 10,000 GCA member benefit still requires manual reserve-wallet processing.";
  }
  if (memberLedger && memberLedger.status === "queued") {
    return "GCA Member evidence remains queued for manual review and observed 30-day holding-history verification.";
  }
  if (creditLedger) {
    return "The 100-credit ledger is active. GCA Member requires 1,000,000 GCA and verified 30-day holding evidence.";
  }
  if (walletVerification && walletVerification.status === "below_threshold") {
    return "The latest recorded wallet verification was below 10,000 GCA. Run a fresh read-only wallet check before resubmitting.";
  }
  return "No eligible credit or member ledger record is available yet.";
}

async function buildAccountStatusPayload(db, accountRow, checkedAt) {
  const accountId = accountRow.account_id;
  const walletRow = await db
    .prepare(
      "SELECT * FROM gca_wallet_verifications WHERE account_id = ?1 ORDER BY checked_at DESC LIMIT 1"
    )
    .bind(accountId)
    .first();
  const creditRow = await db
    .prepare(
      "SELECT * FROM gca_credit_ledger WHERE account_id = ?1 ORDER BY activated_at DESC LIMIT 1"
    )
    .bind(accountId)
    .first();
  const memberRow = await db
    .prepare(
      "SELECT * FROM gca_member_ledger WHERE account_id = ?1 ORDER BY updated_at DESC LIMIT 1"
    )
    .bind(accountId)
    .first();

  const account = rowToMemberAccount(accountRow, false);
  const walletVerification = rowToWalletVerification(walletRow);
  const creditLedger = rowToCreditLedger(creditRow);
  const memberLedger = rowToMemberLedger(memberRow);
  return buildPublicAccountStatus({
    account,
    walletVerification,
    creditLedger,
    memberLedger,
    checkedAt,
    nextStep: accountStatusNextStep(
      walletVerification,
      creditLedger,
      memberLedger
    )
  });
}

async function authenticateAccountStatusAccess(
  db,
  statusAccessToken,
  checkedAt
) {
  const tokenHash = await sha256Hex(statusAccessToken);
  const accountRow = await db
    .prepare(
      `SELECT
        account.*,
        access.expires_at AS status_access_expires_at,
        access.revoked_at AS status_access_revoked_at
      FROM gca_account_status_access AS access
      INNER JOIN gca_member_accounts AS account
        ON account.account_id = access.account_id
      WHERE access.token_hash = ?1
      LIMIT 1`
    )
    .bind(tokenHash)
    .first();

  if (
    !accountRow ||
    String(accountRow.status_access_revoked_at || "").trim() ||
    String(accountRow.status_access_expires_at || "") <= checkedAt
  ) {
    throw new ApiError("device status access key is invalid or expired", 401);
  }
  return accountRow;
}

async function submitAccountStatus(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const statusInput = extractAccountStatus(packet);
  const now = nowIso();
  const accountRow = await authenticateAccountStatusAccess(
    db,
    statusInput.statusAccessToken,
    now
  );

  const publicStatus = await buildAccountStatusPayload(db, accountRow, now);

  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_STATUS_VERSION,
    statusAccessExpiresAt: accountRow.status_access_expires_at,
    ...publicStatus
  }, 200, origin, env);
}

async function latestAccountCreditLedger(db, accountId) {
  return db
    .prepare(
      "SELECT * FROM gca_credit_ledger WHERE account_id = ?1 ORDER BY activated_at DESC LIMIT 1"
    )
    .bind(accountId)
    .first();
}

function accountCreditSummary(creditRow) {
  if (!creditRow) {
    return null;
  }
  return {
    creditLedgerId: creditRow.credit_ledger_id,
    remainingCredits: Number(creditRow.remaining_credits || 0),
    expiresAt: creditRow.expires_at,
    status: creditRow.status
  };
}

function publicCreditServiceCatalog() {
  return Object.entries(CREDIT_SERVICE_CATALOG).map(
    ([id, service]) => ({
      id,
      name: service.name,
      creditUnit: service.creditUnit
    })
  );
}

function accountServiceRequestBoundaries() {
  return {
    deviceKeyProtected: true,
    emailReturned: false,
    accessTokenReturned: false,
    followupEnabled: true,
    followupRequiresMoreInformationReview: true,
    followupLimitPerRequest: ACCOUNT_SERVICE_REQUEST_FOLLOWUP_LIMIT,
    followupIdempotent: true,
    followupReturnsResponseText: false,
    followupChangesCredits: false,
    followupWritesWallet: false,
    cancellationEnabled: true,
    cancellationQueuedOnly: true,
    cancellationIdempotent: true,
    cancellationChangesCredits: false,
    cancellationWritesWallet: false,
    nonSensitiveDeliveryReferenceReturnedAfterDelivered: true,
    deliveryAcknowledgementEnabled: true,
    deliveryAcknowledgementRequiresCompletedDelivery: true,
    deliveryAcknowledgementIdempotent: true,
    deliveryAcknowledgementChangesCredits: false,
    deliveryAcknowledgementWritesWallet: false,
    operatorReviewOnly: true,
    creditsReserved: false,
    creditsDeductedOnRequest: false,
    requiresSignature: false,
    requiresTransaction: false,
    automaticTokenTransfer: false,
    writesWallet: false,
    createsTradingPermission: false
  };
}

function accountServiceRequestFollowup(row) {
  return {
    packetVersion: ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION,
    serviceRequestFollowupId: row.service_request_followup_id,
    serviceRequestId: row.service_request_id,
    status: "queued_operator_review",
    submittedAt: row.submitted_at,
    responseLength: String(row.response_text || "").length,
    responseTextReturned: false,
    creditsChanged: false,
    walletAction: false,
    tokenTransfer: false,
    tradingPermissionCreated: false
  };
}

async function submitAccountServiceRequestFollowup(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const followupInput = extractAccountServiceRequestFollowup(packet);
  const now = nowIso();
  const accountRow = await authenticateAccountStatusAccess(
    db,
    followupInput.statusAccessToken,
    now
  );
  const followupId = await stableId(
    "gca_service_followup",
    accountRow.account_id,
    followupInput.serviceRequestId,
    followupInput.clientFollowupId
  );
  const existingFollowup = await db
    .prepare(
      `SELECT *
      FROM gca_service_request_followups
      WHERE service_request_followup_id = ?1
      LIMIT 1`
    )
    .bind(followupId)
    .first();

  if (existingFollowup) {
    if (
      existingFollowup.service_request_id !==
        followupInput.serviceRequestId ||
      existingFollowup.account_id !== accountRow.account_id ||
      existingFollowup.client_followup_id !==
        followupInput.clientFollowupId ||
      existingFollowup.response_text !== followupInput.responseText ||
      existingFollowup.source !== followupInput.source
    ) {
      throw new ApiError(
        "clientFollowupId is already assigned to different follow-up information",
        409
      );
    }
    return jsonResponse({
      ok: true,
      packetVersion: ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION,
      created: false,
      idempotentReplay: true,
      followup: accountServiceRequestFollowup(existingFollowup),
      boundaries: accountServiceRequestBoundaries()
    }, 200, origin, env);
  }

  const serviceRequestRow = await db
    .prepare(
      `SELECT
        service.*,
        review.decision AS review_decision
      FROM gca_service_requests AS service
      LEFT JOIN gca_service_request_reviews AS review
        ON review.service_request_review_id = service.latest_review_id
      WHERE service.service_request_id = ?1
        AND service.account_id = ?2
      LIMIT 1`
    )
    .bind(followupInput.serviceRequestId, accountRow.account_id)
    .first();
  if (!serviceRequestRow) {
    throw new ApiError(
      "service request was not found for this account",
      404
    );
  }
  if (
    serviceRequestRow.status !== "needs_more_information" ||
    serviceRequestRow.review_decision !== "needs_more_information" ||
    !serviceRequestRow.latest_review_id
  ) {
    throw new ApiError(
      "follow-up information is only accepted after the latest manual review requests more information",
      409
    );
  }

  const countRow = await db
    .prepare(
      `SELECT COUNT(*) AS followup_count
      FROM gca_service_request_followups
      WHERE service_request_id = ?1`
    )
    .bind(followupInput.serviceRequestId)
    .first();
  if (Number(countRow?.followup_count || 0) >= ACCOUNT_SERVICE_REQUEST_FOLLOWUP_LIMIT) {
    throw new ApiError(
      "service request follow-up limit reached; contact official support",
      429
    );
  }

  const insertFollowup = db
    .prepare(
      `INSERT INTO gca_service_request_followups (
        service_request_followup_id,
        service_request_id,
        account_id,
        client_followup_id,
        packet_version,
        response_text,
        submitted_at,
        source,
        no_secrets_no_custody,
        manual_review_only,
        changes_credits,
        requires_signature,
        requires_transaction,
        automatic_token_transfer,
        writes_wallet,
        creates_trading_permission
      )
      SELECT
        ?1, service.service_request_id, service.account_id, ?2, ?3, ?4,
        ?5, ?6, 1, 1, 0, 0, 0, 0, 0, 0
      FROM gca_service_requests AS service
      INNER JOIN gca_service_request_reviews AS review
        ON review.service_request_review_id = service.latest_review_id
      WHERE service.service_request_id = ?7
        AND service.account_id = ?8
        AND service.status = 'needs_more_information'
        AND service.latest_review_id = ?9
        AND review.decision = 'needs_more_information'
        AND (
          SELECT COUNT(*)
          FROM gca_service_request_followups AS existing
          WHERE existing.service_request_id = service.service_request_id
        ) < ?10
        AND NOT EXISTS (
          SELECT 1
          FROM gca_service_request_followups AS existing
          WHERE existing.service_request_followup_id = ?1
        )`
    )
    .bind(
      followupId,
      followupInput.clientFollowupId,
      ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION,
      followupInput.responseText,
      now,
      followupInput.source,
      followupInput.serviceRequestId,
      accountRow.account_id,
      serviceRequestRow.latest_review_id,
      ACCOUNT_SERVICE_REQUEST_FOLLOWUP_LIMIT
    );
  const updateServiceRequest = db
    .prepare(
      `UPDATE gca_service_requests
      SET status = 'queued_operator_review',
        updated_at = ?1
      WHERE service_request_id = ?2
        AND account_id = ?3
        AND status = 'needs_more_information'
        AND latest_review_id = ?4
        AND EXISTS (
          SELECT 1
          FROM gca_service_request_followups
          WHERE service_request_followup_id = ?5
            AND service_request_id = ?2
            AND account_id = ?3
        )`
    )
    .bind(
      now,
      followupInput.serviceRequestId,
      accountRow.account_id,
      serviceRequestRow.latest_review_id,
      followupId
    );

  let batchResults;
  try {
    batchResults = await db.batch([insertFollowup, updateServiceRequest]);
  } catch (error) {
    const concurrentFollowup = await db
      .prepare(
        `SELECT *
        FROM gca_service_request_followups
        WHERE service_request_followup_id = ?1
        LIMIT 1`
      )
      .bind(followupId)
      .first();
    if (
      concurrentFollowup &&
      concurrentFollowup.account_id === accountRow.account_id &&
      concurrentFollowup.service_request_id === followupInput.serviceRequestId &&
      concurrentFollowup.client_followup_id === followupInput.clientFollowupId &&
      concurrentFollowup.response_text === followupInput.responseText
    ) {
      return jsonResponse({
        ok: true,
        packetVersion: ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION,
        created: false,
        idempotentReplay: true,
        followup: accountServiceRequestFollowup(concurrentFollowup),
        boundaries: accountServiceRequestBoundaries()
      }, 200, origin, env);
    }
    throw error;
  }
  if (
    batchResults.some(
      (result) => Number(result?.meta?.changes || 0) !== 1
    )
  ) {
    throw new ApiError(
      "service request changed before follow-up submission; refresh and retry",
      409
    );
  }

  const followupRow = await db
    .prepare(
      `SELECT *
      FROM gca_service_request_followups
      WHERE service_request_followup_id = ?1
      LIMIT 1`
    )
    .bind(followupId)
    .first();
  if (!followupRow) {
    throw new ApiError(
      "service request follow-up was not recorded",
      409
    );
  }
  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION,
    created: true,
    idempotentReplay: false,
    followup: accountServiceRequestFollowup(followupRow),
    boundaries: accountServiceRequestBoundaries()
  }, 201, origin, env);
}

function accountServiceRequestCancellation(row) {
  return {
    packetVersion: ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION,
    serviceRequestId: row.service_request_id,
    status: "cancelled_by_account",
    cancelledAt: row.cancelled_at,
    creditsChanged: false,
    walletAction: false,
    tokenTransfer: false,
    tradingPermissionCreated: false
  };
}

async function submitAccountServiceRequestCancellation(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const cancellationInput = extractAccountServiceRequestCancellation(packet);
  const now = nowIso();
  const accountRow = await authenticateAccountStatusAccess(
    db,
    cancellationInput.statusAccessToken,
    now
  );
  let serviceRequestRow = await db
    .prepare(
      `SELECT *
      FROM gca_service_requests
      WHERE service_request_id = ?1
        AND account_id = ?2
      LIMIT 1`
    )
    .bind(cancellationInput.serviceRequestId, accountRow.account_id)
    .first();

  if (!serviceRequestRow) {
    throw new ApiError(
      "service request was not found for this account",
      404
    );
  }
  const cancellationId = await stableId(
    "gca_service_cancel",
    accountRow.account_id,
    cancellationInput.serviceRequestId
  );
  if (serviceRequestRow.cancellation_id) {
    if (serviceRequestRow.cancellation_id !== cancellationId) {
      throw new ApiError(
        "service request already has a different cancellation record",
        409
      );
    }
    return jsonResponse({
      ok: true,
      packetVersion: ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION,
      created: false,
      idempotentReplay: true,
      cancellation: accountServiceRequestCancellation(serviceRequestRow),
      boundaries: accountServiceRequestBoundaries()
    }, 200, origin, env);
  }
  if (
    !SERVICE_REQUEST_QUEUED_STATUSES.has(serviceRequestRow.status) ||
    Boolean(serviceRequestRow.latest_review_id)
  ) {
    throw new ApiError(
      "service request can only be cancelled before manual review",
      409
    );
  }

  const updateResult = await db
    .prepare(
      `UPDATE gca_service_requests
      SET status = 'cancelled_by_account',
        cancellation_id = ?1,
        cancelled_at = ?2,
        cancellation_version = ?3,
        cancellation_source = ?4,
        completed_at = ?2,
        updated_at = ?2
      WHERE service_request_id = ?5
        AND account_id = ?6
        AND status IN (
          'queued_operator_review',
          'queued_insufficient_credits',
          'queued_expired_credit_ledger',
          'queued_missing_credit_ledger'
        )
        AND latest_review_id = ''
        AND credit_usage_id = ''
        AND delivery_receipt_id = ''
        AND cancellation_id = ''`
    )
    .bind(
      cancellationId,
      now,
      ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION,
      "gca-member-access-request-cancellation",
      cancellationInput.serviceRequestId,
      accountRow.account_id
    )
    .run();
  const created = Number(
    updateResult && updateResult.meta && updateResult.meta.changes
      ? updateResult.meta.changes
      : 0
  ) > 0;
  serviceRequestRow = await db
    .prepare(
      `SELECT *
      FROM gca_service_requests
      WHERE service_request_id = ?1
        AND account_id = ?2
      LIMIT 1`
    )
    .bind(cancellationInput.serviceRequestId, accountRow.account_id)
    .first();
  if (
    !serviceRequestRow ||
    serviceRequestRow.cancellation_id !== cancellationId
  ) {
    throw new ApiError(
      "service request changed before cancellation; refresh and retry",
      409
    );
  }

  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION,
    created,
    idempotentReplay: !created,
    cancellation: accountServiceRequestCancellation(serviceRequestRow),
    boundaries: accountServiceRequestBoundaries()
  }, created ? 201 : 200, origin, env);
}

function accountServiceDeliveryReceipt(row) {
  return {
    packetVersion: ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION,
    serviceRequestId: row.service_request_id,
    status: "delivery_received",
    acknowledgedAt: row.delivery_acknowledged_at,
    creditsChanged: false,
    walletAction: false,
    tokenTransfer: false,
    tradingPermissionCreated: false
  };
}

async function submitAccountServiceDeliveryReceipt(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const receiptInput = extractAccountServiceDeliveryReceipt(packet);
  const now = nowIso();
  const accountRow = await authenticateAccountStatusAccess(
    db,
    receiptInput.statusAccessToken,
    now
  );
  let serviceRequestRow = await db
    .prepare(
      `SELECT
        service.*,
        review.delivery_completed AS review_delivery_completed
      FROM gca_service_requests AS service
      LEFT JOIN gca_service_request_reviews AS review
        ON review.service_request_review_id =
          service.latest_review_id
      WHERE service.service_request_id = ?1
        AND service.account_id = ?2
      LIMIT 1`
    )
    .bind(receiptInput.serviceRequestId, accountRow.account_id)
    .first();

  if (!serviceRequestRow) {
    throw new ApiError(
      "service request was not found for this account",
      404
    );
  }
  if (
    serviceRequestRow.status !== "delivered" ||
    !Boolean(serviceRequestRow.review_delivery_completed)
  ) {
    throw new ApiError(
      "delivery can only be acknowledged after completed delivery",
      409
    );
  }

  const deliveryReceiptId = await stableId(
    "gca_delivery_receipt",
    accountRow.account_id,
    receiptInput.serviceRequestId
  );
  if (serviceRequestRow.delivery_receipt_id) {
    if (serviceRequestRow.delivery_receipt_id !== deliveryReceiptId) {
      throw new ApiError(
        "service request already has a different delivery receipt",
        409
      );
    }
    return jsonResponse({
      ok: true,
      packetVersion: ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION,
      created: false,
      idempotentReplay: true,
      deliveryReceipt: accountServiceDeliveryReceipt(serviceRequestRow),
      boundaries: accountServiceRequestBoundaries()
    }, 200, origin, env);
  }

  const updateResult = await db
    .prepare(
      `UPDATE gca_service_requests
      SET delivery_receipt_id = ?1,
        delivery_acknowledged_at = ?2,
        delivery_acknowledgement_version = ?3,
        delivery_acknowledgement_source = ?4,
        updated_at = ?2
      WHERE service_request_id = ?5
        AND account_id = ?6
        AND status = 'delivered'
        AND EXISTS (
          SELECT 1
          FROM gca_service_request_reviews AS review
          WHERE review.service_request_review_id =
            gca_service_requests.latest_review_id
            AND review.delivery_completed = 1
        )
        AND delivery_receipt_id = ''`
    )
    .bind(
      deliveryReceiptId,
      now,
      ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION,
      "gca-member-access-delivery-receipt",
      receiptInput.serviceRequestId,
      accountRow.account_id
    )
    .run();
  const created = Number(
    updateResult &&
      updateResult.meta &&
      updateResult.meta.changes
      ? updateResult.meta.changes
      : 0
  ) > 0;
  serviceRequestRow = await db
    .prepare(
      `SELECT *
      FROM gca_service_requests
      WHERE service_request_id = ?1
        AND account_id = ?2
      LIMIT 1`
    )
    .bind(receiptInput.serviceRequestId, accountRow.account_id)
    .first();
  if (
    !serviceRequestRow ||
    serviceRequestRow.delivery_receipt_id !== deliveryReceiptId
  ) {
    throw new ApiError("delivery receipt could not be recorded", 409);
  }

  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION,
    created,
    idempotentReplay: !created,
    deliveryReceipt: accountServiceDeliveryReceipt(serviceRequestRow),
    boundaries: accountServiceRequestBoundaries()
  }, created ? 201 : 200, origin, env);
}

async function submitAccountServiceRequest(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const requestInput = extractAccountServiceRequest(packet);
  const now = nowIso();
  const accountRow = await authenticateAccountStatusAccess(
    db,
    requestInput.statusAccessToken,
    now
  );
  const serviceRequestId = await stableId(
    "gca_service_req",
    accountRow.account_id,
    requestInput.clientRequestId
  );
  const existingRow = await db
    .prepare(
      `SELECT
        service.*,
        review.decision AS review_decision,
        review.reason_code AS review_reason_code,
        review.member_prompt AS review_member_prompt,
        review.reviewed_at AS review_reviewed_at,
        review.delivery_completed AS review_delivery_completed,
        review.delivery_reference AS review_delivery_reference,
        review.credits_deducted AS review_credits_deducted,
        review.credit_amount_used AS review_credit_amount_used,
        review.remaining_credits_after AS review_remaining_credits_after
      FROM gca_service_requests AS service
      LEFT JOIN gca_service_request_reviews AS review
        ON review.service_request_review_id =
          service.latest_review_id
      WHERE service.service_request_id = ?1
      LIMIT 1`
    )
    .bind(serviceRequestId)
    .first();

  if (existingRow) {
    if (
      existingRow.account_id !== accountRow.account_id ||
      existingRow.service_id !== requestInput.serviceId ||
      String(existingRow.request_title || "") !== requestInput.requestTitle ||
      String(existingRow.request_summary || "") !== requestInput.requestSummary ||
      String(existingRow.market_context || "") !== requestInput.marketContext
    ) {
      throw new ApiError(
        "clientRequestId is already assigned to a different request",
        409
      );
    }
    return jsonResponse({
      ok: true,
      packetVersion: ACCOUNT_SERVICE_REQUEST_VERSION,
      created: false,
      idempotentReplay: true,
      serviceRequest: rowToAccountServiceRequest(existingRow),
      serviceCatalog: publicCreditServiceCatalog(),
      boundaries: accountServiceRequestBoundaries()
    }, 200, origin, env);
  }

  const oneDayAgo = addDaysIso(now, -1);
  const recentCountRow = await db
    .prepare(
      `SELECT COUNT(*) AS request_count
      FROM gca_service_requests
      WHERE account_id = ?1 AND created_at >= ?2`
    )
    .bind(accountRow.account_id, oneDayAgo)
    .first();
  if (
    Number(recentCountRow && recentCountRow.request_count
      ? recentCountRow.request_count
      : 0) >= ACCOUNT_SERVICE_REQUEST_DAILY_LIMIT
  ) {
    throw new ApiError(
      "daily service request limit reached; retry after 24 hours",
      429
    );
  }

  const creditRow = await latestAccountCreditLedger(
    db,
    accountRow.account_id
  );
  const requestedCreditHold = requestInput.requestedCreditHold;
  const remainingCreditsAtRequest = creditRow
    ? Number(creditRow.remaining_credits || 0)
    : null;
  let status = "queued_missing_credit_ledger";
  if (requestedCreditHold === 0) {
    status = "queued_operator_review";
  } else if (creditRow && String(creditRow.expires_at || "") <= now) {
    status = "queued_expired_credit_ledger";
  } else if (
    creditRow &&
    Number.isInteger(remainingCreditsAtRequest) &&
    remainingCreditsAtRequest >= requestedCreditHold
  ) {
    status = "queued_operator_review";
  } else if (creditRow) {
    status = "queued_insufficient_credits";
  }

  await db
    .prepare(
      `INSERT OR IGNORE INTO gca_service_requests (
        service_request_id,
        account_id,
        email,
        email_hash,
        wallet_address,
        credit_ledger_id,
        service_id,
        service_name,
        requested_credit_hold,
        remaining_credits_at_request,
        request_title,
        request_summary,
        market_context,
        preferred_language,
        source,
        status,
        created_at,
        operator_review_required,
        does_not_deduct_credits,
        requires_signature,
        requires_transaction,
        automatic_token_transfer,
        writes_wallet,
        creates_trading_permission
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, 1, 1, 0, 0, 0, 0, 0)`
    )
    .bind(
      serviceRequestId,
      accountRow.account_id,
      accountRow.email,
      accountRow.email_hash,
      accountRow.wallet_address,
      creditRow ? creditRow.credit_ledger_id : "",
      requestInput.serviceId,
      requestInput.serviceName,
      requestedCreditHold,
      remainingCreditsAtRequest,
      requestInput.requestTitle,
      requestInput.requestSummary,
      requestInput.marketContext,
      requestInput.preferredLanguage,
      requestInput.source,
      status,
      now
    )
    .run();
  const serviceRequestRow = await db
    .prepare(
      "SELECT * FROM gca_service_requests WHERE service_request_id = ?1 LIMIT 1"
    )
    .bind(serviceRequestId)
    .first();

  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_SERVICE_REQUEST_VERSION,
    created: true,
    idempotentReplay: false,
    serviceRequest: rowToAccountServiceRequest(serviceRequestRow),
    creditLedger: accountCreditSummary(creditRow),
    serviceCatalog: publicCreditServiceCatalog(),
    boundaries: accountServiceRequestBoundaries()
  }, 201, origin, env);
}

async function readAccountServiceRequests(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const statusInput = extractAccountServiceRequestStatus(packet);
  const now = nowIso();
  const accountRow = await authenticateAccountStatusAccess(
    db,
    statusInput.statusAccessToken,
    now
  );
  const creditRow = await latestAccountCreditLedger(
    db,
    accountRow.account_id
  );
  const { results } = await db
    .prepare(
      `SELECT
        service.*,
        review.decision AS review_decision,
        review.reason_code AS review_reason_code,
        review.member_prompt AS review_member_prompt,
        review.reviewed_at AS review_reviewed_at,
        review.delivery_completed AS review_delivery_completed,
        review.delivery_reference AS review_delivery_reference,
        review.credits_deducted AS review_credits_deducted,
        review.credit_amount_used AS review_credit_amount_used,
        review.remaining_credits_after AS review_remaining_credits_after,
        followup.service_request_followup_id AS followup_id,
        followup.submitted_at AS followup_submitted_at,
        (
          SELECT COUNT(*)
          FROM gca_service_request_followups AS counted_followup
          WHERE counted_followup.service_request_id = service.service_request_id
        ) AS followup_count
      FROM gca_service_requests AS service
      LEFT JOIN gca_service_request_reviews AS review
        ON review.service_request_review_id =
          service.latest_review_id
      LEFT JOIN gca_service_request_followups AS followup
        ON followup.service_request_followup_id = (
          SELECT latest_followup.service_request_followup_id
          FROM gca_service_request_followups AS latest_followup
          WHERE latest_followup.service_request_id = service.service_request_id
          ORDER BY latest_followup.submitted_at DESC,
            latest_followup.service_request_followup_id DESC
          LIMIT 1
        )
      WHERE service.account_id = ?1
      ORDER BY service.created_at DESC
      LIMIT ?2`
    )
    .bind(accountRow.account_id, ACCOUNT_SERVICE_REQUEST_HISTORY_LIMIT)
    .all();

  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_SERVICE_REQUEST_STATUS_VERSION,
    checkedAt: now,
    count: results.length,
    serviceRequests: results.map((row) => rowToAccountServiceRequest(row)),
    creditLedger: accountCreditSummary(creditRow),
    serviceCatalog: publicCreditServiceCatalog(),
    boundaries: accountServiceRequestBoundaries()
  }, 200, origin, env);
}

async function submitAccountStatusRotation(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const rotationInput = extractAccountStatusRotation(packet);
  const currentTokenHash = await sha256Hex(
    rotationInput.currentStatusAccessToken
  );
  const newTokenHash = await sha256Hex(rotationInput.newStatusAccessToken);
  const now = nowIso();
  let usedPreviousToken = false;
  let alreadyRotated = false;
  let accessRow = await db
    .prepare(
      "SELECT * FROM gca_account_status_access WHERE token_hash = ?1 LIMIT 1"
    )
    .bind(currentTokenHash)
    .first();

  if (!accessRow) {
    accessRow = await db
      .prepare(
        `SELECT *
        FROM gca_account_status_access
        WHERE previous_token_hash = ?1
          AND previous_token_expires_at > ?2
        LIMIT 1`
      )
      .bind(currentTokenHash, now)
      .first();
    usedPreviousToken = Boolean(accessRow);
  }

  if (
    !accessRow ||
    String(accessRow.revoked_at || "").trim() ||
    String(accessRow.expires_at || "") <= now
  ) {
    throw new ApiError("device status access key is invalid or expired", 401);
  }

  if (usedPreviousToken) {
    if (accessRow.token_hash !== newTokenHash) {
      throw new ApiError(
        "the previous device key can only retry its completed rotation",
        409
      );
    }
    alreadyRotated = true;
  } else {
    const newTokenOwner = await db
      .prepare(
        `SELECT account_id
        FROM gca_account_status_access
        WHERE token_hash = ?1 OR previous_token_hash = ?1
        LIMIT 1`
      )
      .bind(newTokenHash)
      .first();
    if (newTokenOwner) {
      throw new ApiError(
        "new device status access key is already assigned or was previously used",
        409
      );
    }

    const previousTokenExpiresAt = addMinutesIso(
      now,
      ACCOUNT_STATUS_ROTATION_GRACE_MINUTES
    );
    const statusAccessExpiresAt = addDaysIso(
      now,
      ACCOUNT_STATUS_ACCESS_DAYS
    );
    const updateResult = await db
      .prepare(
        `UPDATE gca_account_status_access
        SET previous_token_hash = token_hash,
            previous_token_expires_at = ?1,
            token_hash = ?2,
            expires_at = ?3,
            rotated_at = ?4
        WHERE account_id = ?5
          AND token_hash = ?6
          AND revoked_at = ''
          AND expires_at > ?4`
      )
      .bind(
        previousTokenExpiresAt,
        newTokenHash,
        statusAccessExpiresAt,
        now,
        accessRow.account_id,
        currentTokenHash
      )
      .run();

    const storedAccess = await db
      .prepare(
        "SELECT * FROM gca_account_status_access WHERE account_id = ?1 LIMIT 1"
      )
      .bind(accessRow.account_id)
      .first();
    if (
      !storedAccess ||
      storedAccess.token_hash !== newTokenHash ||
      storedAccess.previous_token_hash !== currentTokenHash ||
      String(storedAccess.previous_token_expires_at || "") <= now
    ) {
      throw new ApiError(
        "device status key rotation conflict; retry the same rotation",
        409
      );
    }
    const changedRows = Number(updateResult?.meta?.changes);
    alreadyRotated = Number.isFinite(changedRows) && changedRows === 0;
    accessRow = storedAccess;
  }

  const accountRow = await db
    .prepare("SELECT * FROM gca_member_accounts WHERE account_id = ?1 LIMIT 1")
    .bind(accessRow.account_id)
    .first();
  if (!accountRow) {
    throw new ApiError("device status account is unavailable", 409);
  }

  const publicStatus = await buildAccountStatusPayload(db, accountRow, now);
  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_STATUS_ROTATION_VERSION,
    statusPacketVersion: ACCOUNT_STATUS_VERSION,
    statusAccessExpiresAt: accessRow.expires_at,
    ...publicStatus,
    rotation: {
      completed: true,
      alreadyRotated,
      rotatedAt: accessRow.rotated_at,
      previousKeyRetryExpiresAt: accessRow.previous_token_expires_at,
      gracePeriodMinutes: ACCOUNT_STATUS_ROTATION_GRACE_MINUTES,
      currentTokenReturned: false,
      newTokenReturned: false
    },
    boundaries: {
      ...publicStatus.boundaries,
      keyRotationOnly: true,
      accountOrLedgerRecordsChanged: false,
      walletActionRequired: false,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false
    }
  }, 200, origin, env);
}

function accountRecoveryPublicResponse(recoveryRequestId, origin, env) {
  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_STATUS_RECOVERY_REQUEST_VERSION,
    recoveryRequestId,
    status: "pending_if_account_matches",
    requestAccepted: true,
    accountMatchReturned: false,
    requestReviewWindowDays: ACCOUNT_STATUS_RECOVERY_REQUEST_DAYS,
    recoveryCredentialReturned: false,
    newDeviceKeyReturned: false,
    nextStep:
      `Contact ${OFFICIAL_CONTACT_EMAIL} from the registered email and include only the recovery request id. GCA support will never ask for the device key, wallet secrets, a signature, or a transaction.`
  }, 202, origin, env);
}

async function submitAccountStatusRecoveryRequest(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const recoveryInput = extractAccountStatusRecoveryRequest(packet);
  const now = nowIso();
  const emailHash = await sha256Hex(recoveryInput.email);
  const newTokenHash = await sha256Hex(
    recoveryInput.newStatusAccessToken
  );
  const recoveryRequestId = await stableId(
    "gca_recovery_request",
    recoveryInput.email,
    recoveryInput.walletAddress,
    newTokenHash
  );
  const genericResponse = () =>
    accountRecoveryPublicResponse(recoveryRequestId, origin, env);
  const accountRow = await db
    .prepare(
      `SELECT account.*
      FROM gca_member_accounts AS account
      INNER JOIN gca_account_status_access AS access
        ON access.account_id = account.account_id
      WHERE account.email_hash = ?1
        AND account.wallet_address = ?2
      LIMIT 1`
    )
    .bind(emailHash, recoveryInput.walletAddress)
    .first();

  if (!accountRow) {
    return genericResponse();
  }

  const existingRequest = await db
    .prepare(
      `SELECT recovery_request_id
      FROM gca_account_status_recovery_requests
      WHERE recovery_request_id = ?1
      LIMIT 1`
    )
    .bind(recoveryRequestId)
    .first();
  if (existingRequest) {
    return genericResponse();
  }

  const usedToken = await db
    .prepare(
      `SELECT account_id
      FROM gca_account_status_access
      WHERE token_hash = ?1 OR previous_token_hash = ?1
      LIMIT 1`
    )
    .bind(newTokenHash)
    .first();
  const requestedToken = await db
    .prepare(
      `SELECT recovery_request_id
      FROM gca_account_status_recovery_requests
      WHERE new_token_hash = ?1
      LIMIT 1`
    )
    .bind(newTokenHash)
    .first();
  if (usedToken || requestedToken) {
    throw new ApiError(
      "new device status access key is already assigned or was previously used",
      409
    );
  }

  const expiresAt = addDaysIso(
    now,
    ACCOUNT_STATUS_RECOVERY_REQUEST_DAYS
  );
  const userAgent = String(
    request.headers.get("user-agent") || ""
  ).slice(0, 300);
  const ipHash = await optionalIpHash(request, env);
  const insertRequest = db
    .prepare(
      `INSERT INTO gca_account_status_recovery_requests (
        recovery_request_id,
        packet_version,
        account_id,
        email_hash,
        wallet_address,
        new_token_hash,
        status,
        requested_at,
        expires_at,
        source,
        user_agent,
        ip_hash,
        registered_email_verified,
        manual_identity_review_completed,
        no_secrets_requested,
        changes_account_or_ledgers,
        requires_signature,
        requires_transaction,
        automatic_token_transfer
      ) VALUES (
        ?1, ?2, ?3, ?4, ?5, ?6, 'pending', ?7, ?8, ?9, ?10, ?11,
        0, 0, 1, 0, 0, 0, 0
      )`
    )
    .bind(
      recoveryRequestId,
      ACCOUNT_STATUS_RECOVERY_REQUEST_VERSION,
      accountRow.account_id,
      emailHash,
      recoveryInput.walletAddress,
      newTokenHash,
      now,
      expiresAt,
      recoveryInput.source,
      userAgent,
      ipHash
    );
  await insertRequest.run();
  return genericResponse();
}

async function listAccountStatusRecoveryRequests(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse(
      { ok: false, error: "admin authorization is required" },
      401,
      origin,
      env
    );
  }
  const db = requireDatabase(env);
  const url = new URL(request.url);
  const limit = Math.max(
    1,
    Math.min(100, Number(url.searchParams.get("limit") || "50"))
  );
  const filters = [];
  const values = [];
  const recoveryRequestId = String(
    url.searchParams.get("recoveryRequestId") || ""
  )
    .trim()
    .toLowerCase();
  const email = String(url.searchParams.get("email") || "").trim();
  const status = String(url.searchParams.get("status") || "")
    .trim()
    .toLowerCase();
  if (recoveryRequestId) {
    if (!RECOVERY_REQUEST_ID_RE.test(recoveryRequestId)) {
      throw new ApiError(
        "recoveryRequestId must be a valid GCA recovery request id"
      );
    }
    filters.push(`recovery.recovery_request_id = ?${values.length + 1}`);
    values.push(recoveryRequestId);
  }
  if (email) {
    filters.push(`account.email = ?${values.length + 1}`);
    values.push(normalizeEmail(email));
  }
  if (status) {
    filters.push(`recovery.status = ?${values.length + 1}`);
    values.push(status);
  }
  const where = filters.length
    ? `WHERE ${filters.join(" AND ")}`
    : "";
  const query = db.prepare(
    `SELECT recovery.*, account.email
    FROM gca_account_status_recovery_requests AS recovery
    INNER JOIN gca_member_accounts AS account
      ON account.account_id = recovery.account_id
    ${where}
    ORDER BY recovery.requested_at DESC
    LIMIT ?${values.length + 1}`
  );
  const { results } = await query.bind(...values, limit).all();
  return jsonResponse({
    ok: true,
    count: results.length,
    records: results.map((row) =>
      rowToAccountStatusRecoveryRequest(row)
    ),
    boundaries: {
      adminTokenRequired: true,
      tokenHashesReturned: false,
      recoveryCredentialReturned: false,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false
    }
  }, 200, origin, env);
}

async function approveAccountStatusRecovery(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse(
      { ok: false, error: "admin authorization is required" },
      401,
      origin,
      env
    );
  }
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const approvalInput = extractAccountStatusRecoveryApproval(packet);
  const now = nowIso();
  const registeredEmailHash = await sha256Hex(
    approvalInput.registeredEmail
  );
  const recoveryRow = await db
    .prepare(
      `SELECT recovery.*, account.email
      FROM gca_account_status_recovery_requests AS recovery
      INNER JOIN gca_member_accounts AS account
        ON account.account_id = recovery.account_id
      WHERE recovery.recovery_request_id = ?1
      LIMIT 1`
    )
    .bind(approvalInput.recoveryRequestId)
    .first();

  if (
    !recoveryRow ||
    recoveryRow.email_hash !== registeredEmailHash ||
    normalizeEmail(recoveryRow.email) !== approvalInput.registeredEmail
  ) {
    throw new ApiError(
      "recovery request and registered email do not match",
      409
    );
  }
  if (
    !["pending", "approved"].includes(recoveryRow.status) ||
    String(recoveryRow.expires_at || "") <= now
  ) {
    throw new ApiError(
      "recovery request is not pending or has expired",
      409
    );
  }

  const reissued = recoveryRow.status === "approved";
  const recoveryCredential = randomCredential("gca_recovery_");
  const recoveryCredentialHash = await sha256Hex(
    recoveryCredential
  );
  const recoveryCredentialExpiresAt = addMinutesIso(
    now,
    ACCOUNT_STATUS_RECOVERY_CREDENTIAL_MINUTES
  );
  const supersedeOtherRequests = db
    .prepare(
      `UPDATE gca_account_status_recovery_requests
      SET status = 'superseded',
          cancelled_at = ?1
      WHERE account_id = ?2
        AND recovery_request_id <> ?3
        AND status IN ('pending', 'approved')`
    )
    .bind(
      now,
      recoveryRow.account_id,
      approvalInput.recoveryRequestId
    );
  const approveRequest = db
    .prepare(
      `UPDATE gca_account_status_recovery_requests
      SET status = 'approved',
          recovery_credential_hash = ?1,
          recovery_credential_expires_at = ?2,
          approved_at = ?3,
          operator_id = ?4,
          reason_code = ?5,
          source = ?6,
          registered_email_verified = 1,
          manual_identity_review_completed = 1,
          no_secrets_requested = 1
      WHERE recovery_request_id = ?7
        AND status IN ('pending', 'approved')
        AND expires_at > ?3`
    )
    .bind(
      recoveryCredentialHash,
      recoveryCredentialExpiresAt,
      now,
      approvalInput.operatorId,
      approvalInput.reasonCode,
      approvalInput.source,
      approvalInput.recoveryRequestId
    );
  const approvalResults = await db.batch([
    supersedeOtherRequests,
    approveRequest
  ]);
  if (Number(approvalResults?.[1]?.meta?.changes || 0) !== 1) {
    throw new ApiError(
      "recovery request approval conflict; reload the request",
      409
    );
  }

  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_STATUS_RECOVERY_APPROVAL_VERSION,
    recoveryRequestId: approvalInput.recoveryRequestId,
    status: "approved",
    approvedAt: now,
    recoveryCredentialExpiresAt,
    recoveryCredential,
    recoveryCredentialReturnedOnce: true,
    reissued,
    delivery: {
      registeredEmailOnly: true,
      emailReturned: false,
      includeDeviceKey: false,
      includeWalletSecrets: false
    },
    boundaries: {
      adminTokenRequired: true,
      manualIdentityReviewRequired: true,
      changesAccountOrLedgers: false,
      walletActionRequired: false,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false
    }
  }, 200, origin, env);
}

async function submitAccountStatusRecovery(request, env, origin) {
  const db = requireDatabase(env);
  const packet = await readJsonRequest(request);
  const recoveryInput = extractAccountStatusRecovery(packet);
  const now = nowIso();
  const recoveryCredentialHash = await sha256Hex(
    recoveryInput.recoveryCredential
  );
  const newTokenHash = await sha256Hex(
    recoveryInput.newStatusAccessToken
  );
  const recoveryRow = await db
    .prepare(
      `SELECT *
      FROM gca_account_status_recovery_requests
      WHERE recovery_request_id = ?1
      LIMIT 1`
    )
    .bind(recoveryInput.recoveryRequestId)
    .first();
  const invalidRecovery =
    !recoveryRow ||
    recoveryRow.status !== "approved" ||
    recoveryRow.recovery_credential_hash !== recoveryCredentialHash ||
    recoveryRow.new_token_hash !== newTokenHash ||
    String(recoveryRow.expires_at || "") <= now ||
    String(recoveryRow.recovery_credential_expires_at || "") <= now;
  if (invalidRecovery) {
    throw new ApiError(
      "recovery request or credential is invalid or expired",
      401
    );
  }

  const conflictingTokenOwner = await db
    .prepare(
      `SELECT account_id
      FROM gca_account_status_access
      WHERE (token_hash = ?1 OR previous_token_hash = ?1)
        AND account_id <> ?2
      LIMIT 1`
    )
    .bind(newTokenHash, recoveryRow.account_id)
    .first();
  if (conflictingTokenOwner) {
    throw new ApiError(
      "new device status access key is already assigned or was previously used",
      409
    );
  }
  const accessRow = await db
    .prepare(
      `SELECT account_id
      FROM gca_account_status_access
      WHERE account_id = ?1
      LIMIT 1`
    )
    .bind(recoveryRow.account_id)
    .first();
  if (!accessRow) {
    throw new ApiError(
      "device status access is unavailable for this account",
      409
    );
  }

  const statusAccessExpiresAt = addDaysIso(
    now,
    ACCOUNT_STATUS_ACCESS_DAYS
  );
  const updateAccess = db
    .prepare(
      `UPDATE gca_account_status_access
      SET token_hash = ?1,
          previous_token_hash = '',
          previous_token_expires_at = '',
          expires_at = ?2,
          revoked_at = '',
          recovered_at = ?3,
          recovery_request_id = ?4
      WHERE account_id = ?5
        AND EXISTS (
          SELECT 1
          FROM gca_account_status_recovery_requests
          WHERE recovery_request_id = ?4
            AND account_id = ?5
            AND status = 'approved'
            AND recovery_credential_hash = ?6
            AND new_token_hash = ?1
            AND expires_at > ?3
            AND recovery_credential_expires_at > ?3
        )`
    )
    .bind(
      newTokenHash,
      statusAccessExpiresAt,
      now,
      recoveryInput.recoveryRequestId,
      recoveryRow.account_id,
      recoveryCredentialHash
    );
  const consumeRequest = db
    .prepare(
      `UPDATE gca_account_status_recovery_requests
      SET status = 'consumed',
          consumed_at = ?1
      WHERE recovery_request_id = ?2
        AND account_id = ?3
        AND status = 'approved'
        AND recovery_credential_hash = ?4
        AND new_token_hash = ?5
        AND expires_at > ?1
        AND recovery_credential_expires_at > ?1`
    )
    .bind(
      now,
      recoveryInput.recoveryRequestId,
      recoveryRow.account_id,
      recoveryCredentialHash,
      newTokenHash
    );
  const batchResults = await db.batch([updateAccess, consumeRequest]);
  const accessChanges = Number(
    batchResults?.[0]?.meta?.changes || 0
  );
  const requestChanges = Number(
    batchResults?.[1]?.meta?.changes || 0
  );
  if (accessChanges !== 1 || requestChanges !== 1) {
    throw new ApiError(
      "recovery completion conflict; refresh with the new device key before retrying",
      409
    );
  }

  const accountRow = await db
    .prepare(
      "SELECT * FROM gca_member_accounts WHERE account_id = ?1 LIMIT 1"
    )
    .bind(recoveryRow.account_id)
    .first();
  if (!accountRow) {
    throw new ApiError("device status account is unavailable", 409);
  }
  const publicStatus = await buildAccountStatusPayload(
    db,
    accountRow,
    now
  );
  return jsonResponse({
    ok: true,
    packetVersion: ACCOUNT_STATUS_RECOVERY_VERSION,
    statusPacketVersion: ACCOUNT_STATUS_VERSION,
    statusAccessExpiresAt,
    ...publicStatus,
    recovery: {
      completed: true,
      recoveryRequestId: recoveryInput.recoveryRequestId,
      recoveredAt: now,
      oldDeviceKeyInvalidated: true,
      previousKeyRetryAllowed: false,
      recoveryCredentialConsumed: true,
      recoveryCredentialReturned: false,
      newDeviceKeyReturned: false
    },
    boundaries: {
      ...publicStatus.boundaries,
      credentialRecoveryOnly: true,
      manualIdentityReviewRequired: true,
      accountOrLedgerRecordsChanged: false,
      walletActionRequired: false,
      requiresSignature: false,
      requiresTransaction: false,
      automaticTokenTransfer: false
    }
  }, 200, origin, env);
}

function accessThresholds() {
  return {
    holderBonusMinimumGca: "10000",
    holderBonusCreditAmount: CREDIT_AMOUNT,
    holderBonusCreditType: "GCA AI Quant Access credits",
    gcaMemberMinimumGca: "1000000",
    gcaMemberHoldingDays: MEMBER_HOLD_DAYS,
    memberBenefitAmount: MEMBER_BENEFIT_AMOUNT,
    memberBenefitSourceWallet: MEMBER_BENEFIT_SOURCE_WALLET,
    creditExpiryDays: CREDIT_EXPIRY_DAYS,
    memberRefreshDays: MEMBER_REFRESH_DAYS
  };
}

function accessBoundaries() {
  return {
    readOnlyWalletVerification: true,
    readOnlyAccountStatus: true,
    accountStatusAccessMode: "browser-generated-high-entropy-device-key",
    accountStatusTokenStoredAsSha256: true,
    accountStatusReturnsEmail: false,
    accountStatusReturnsAccessToken: false,
    accountStatusAccessDays: ACCOUNT_STATUS_ACCESS_DAYS,
    accountStatusKeyRotationEnabled: true,
    accountStatusRotationGraceMinutes: ACCOUNT_STATUS_ROTATION_GRACE_MINUTES,
    accountStatusRotationReturnsAccessToken: false,
    accountStatusRotationChangesAccountOrLedgers: false,
    accountStatusRecoveryEnabled: true,
    accountStatusRecoveryMode: "registered-email-manual-review",
    accountStatusRecoveryRequestDays: ACCOUNT_STATUS_RECOVERY_REQUEST_DAYS,
    accountStatusRecoveryCredentialMinutes:
      ACCOUNT_STATUS_RECOVERY_CREDENTIAL_MINUTES,
    accountStatusRecoveryStoresCredentialAsSha256: true,
    accountStatusRecoveryReturnsAccountMatch: false,
    accountStatusRecoveryInvalidatesOldDeviceKey: true,
    accountStatusRecoveryChangesAccountOrLedgers: false,
    accountServiceRequestsEnabled: true,
    accountServiceRequestMode: "device-key-protected-manual-review",
    accountServiceRequestDailyLimit: ACCOUNT_SERVICE_REQUEST_DAILY_LIMIT,
    accountServiceRequestCreditsReserved: false,
    accountServiceRequestCreditsDeductedOnRequest: false,
    accountServiceRequestReturnsEmail: false,
    accountServiceRequestCreatesTradingPermission: false,
    accountServiceRequestFollowupEnabled: true,
    accountServiceRequestFollowupRequiresMoreInformationReview: true,
    accountServiceRequestFollowupLimitPerRequest:
      ACCOUNT_SERVICE_REQUEST_FOLLOWUP_LIMIT,
    accountServiceRequestFollowupIdempotent: true,
    accountServiceRequestFollowupReturnsResponseText: false,
    accountServiceRequestFollowupChangesCredits: false,
    accountServiceRequestFollowupWritesWallet: false,
    accountServiceRequestCancellationEnabled: true,
    accountServiceRequestCancellationQueuedOnly: true,
    accountServiceRequestCancellationIdempotent: true,
    accountServiceRequestCancellationChangesCredits: false,
    accountServiceRequestCancellationWritesWallet: false,
    accountServiceDeliveryReceiptEnabled: true,
    accountServiceDeliveryReceiptRequiresCompletedDelivery: true,
    accountServiceDeliveryReceiptIdempotent: true,
    accountServiceDeliveryReceiptChangesCredits: false,
    accountServiceDeliveryReceiptWritesWallet: false,
    serviceRequestReviewEnabled: true,
    serviceRequestReviewMode:
      "admin-token-protected-manual-review-and-delivery",
    serviceRequestReviewApprovedBeforeDeliveryRequired: true,
    serviceRequestReviewServerCatalogAuthoritative: true,
    serviceRequestReviewCreditsDeductedOnlyOnDelivered: true,
    serviceRequestReviewCreditsDeductedAtMostOnce: true,
    serviceRequestReviewReturnsToAccountHistory: true,
    serviceRequestReviewMemberPromptRequiredForMoreInformation: true,
    serviceRequestReviewMemberPromptReturnedToMatchedAccount: true,
    serviceRequestReviewOperatorNoteReturnedToAccount: false,
    serviceRequestReviewReturnsNonSensitiveDeliveryReference: true,
    requiresSignature: false,
    requiresTransaction: false,
    asksForPrivateKey: false,
    asksForSeedPhrase: false,
    asksForExchangeApiSecret: false,
    asksForWithdrawalPermission: false,
    automaticTokenTransfer: false,
    automaticMemberActivationFromSubmittedDate: false,
    onchainHoldingHistoryRequiredForApproval: true,
    holdingHistoryVerificationMode: "read-only-transfer-history-reconstruction",
    holdingHistorySources: ["Base Blockscout v2", "Base public RPC"],
    memberActivationMode: "admin-token-protected-manual-review",
    memberBenefitTransferMode: "manual-reserve-wallet-transfer-with-read-only-production-evidence",
    memberBenefitSourceWallet: MEMBER_BENEFIT_SOURCE_WALLET,
    memberBenefitExactTransferRequired: true,
    memberBenefitSafeBlockRequired: true,
    memberBenefitSelfServiceTransfer: false
  };
}

function accessConfig(origin, env) {
  const contactEmail = String(env.CONTACT_EMAIL || OFFICIAL_CONTACT_EMAIL).trim() || OFFICIAL_CONTACT_EMAIL;
  return jsonResponse({
    ok: true,
    service: "gca-registration-api",
    workerRelease: WORKER_RELEASE,
    contactEmail,
    memberAccessVersion: MEMBER_ACCESS_VERSION,
    legacyMemberAccessVersion: LEGACY_MEMBER_ACCESS_VERSION,
    accountStatusVersion: ACCOUNT_STATUS_VERSION,
    accountStatusRotationVersion: ACCOUNT_STATUS_ROTATION_VERSION,
    accountStatusRecoveryRequestVersion:
      ACCOUNT_STATUS_RECOVERY_REQUEST_VERSION,
    accountStatusRecoveryApprovalVersion:
      ACCOUNT_STATUS_RECOVERY_APPROVAL_VERSION,
    accountStatusRecoveryVersion: ACCOUNT_STATUS_RECOVERY_VERSION,
    creditUsageVersion: CREDIT_USAGE_VERSION,
    serviceRequestVersion: SERVICE_REQUEST_VERSION,
    accountServiceRequestVersion: ACCOUNT_SERVICE_REQUEST_VERSION,
    accountServiceRequestStatusVersion:
      ACCOUNT_SERVICE_REQUEST_STATUS_VERSION,
    accountServiceRequestFollowupVersion:
      ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION,
    accountServiceRequestCancellationVersion:
      ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION,
    accountServiceDeliveryReceiptVersion:
      ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION,
    serviceRequestReviewVersion:
      SERVICE_REQUEST_REVIEW_VERSION,
    memberReviewVersion: MEMBER_REVIEW_VERSION,
    holdingVerificationVersion: HOLDING_VERIFICATION_VERSION,
    memberBenefitTransferVersion: MEMBER_BENEFIT_TRANSFER_VERSION,
    chainId: CHAIN_ID,
    contractAddress: CONTRACT_ADDRESS,
    apiBaseUrl: "https://gca-registration-api.gcagochina.workers.dev",
    accountUi: "https://gcagochina.com/gca/member-access/",
    endpoints: {
      memberAccess: "/gca/member-access",
      accountStatus: "/gca/account-status",
      accountStatusRotation: "/gca/account-status/rotate",
      accountStatusRecoveryRequests:
        "/gca/account-status/recovery-requests",
      accountStatusRecoveryApprovals:
        "/gca/account-status/recovery-approvals",
      accountStatusRecovery: "/gca/account-status/recover",
      accountServiceRequests: "/gca/account-service-requests",
      accountServiceRequestStatus:
        "/gca/account-service-requests/status",
      accountServiceRequestFollowups:
        "/gca/account-service-requests/follow-ups",
      accountServiceRequestCancellations:
        "/gca/account-service-requests/cancellations",
      accountServiceDeliveryReceipts:
        "/gca/account-service-requests/delivery-receipts",
      serviceRequestReviewsAdmin:
        "/gca/service-request-reviews",
      serviceRequestFollowupsAdmin:
        "/gca/service-request-followups",
      walletVerifications: "/gca/wallet-verifications",
      creditLedgerAdmin: "/gca/credit-ledger",
      serviceRequestsAdmin: "/gca/service-requests",
      creditUsageAdmin: "/gca/credit-usage",
      memberLedgerAdmin: "/gca/member-ledger",
      memberReviewsAdmin: "/gca/member-reviews",
      holdingVerificationsAdmin: "/gca/holding-verifications",
      memberBenefitTransfersAdmin: "/gca/member-benefit-transfers"
    },
    antiSpam: {
      honeypotFields: HONEYPOT_FIELDS,
      rejectsFilledHoneypotFields: true,
      rateLimitsStillRequired: true
    },
    thresholds: accessThresholds(),
    serviceCatalog: publicCreditServiceCatalog(),
    boundaries: accessBoundaries()
  }, 200, origin, env);
}

function isAdminAuthorized(request, env) {
  const token = String(env.ADMIN_READ_TOKEN || "").trim();
  const header = request.headers.get("authorization") || "";
  return Boolean(token && header === `Bearer ${token}`);
}

async function listEmailRegistrations(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse({ ok: false, error: "admin authorization is required" }, 401, origin, env);
  }
  const db = requireDatabase(env);
  const url = new URL(request.url);
  const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit") || "50")));
  const email = url.searchParams.get("email");
  const query = email
    ? db
        .prepare("SELECT * FROM gca_email_registrations WHERE email = ?1 LIMIT ?2")
        .bind(normalizeEmail(email), limit)
    : db
        .prepare("SELECT * FROM gca_email_registrations ORDER BY created_at DESC LIMIT ?1")
        .bind(limit);
  const { results } = await query.all();
  return jsonResponse({
    ok: true,
    count: results.length,
    records: results.map((row) => rowToEmailRegistration(row))
  }, 200, origin, env);
}

async function listContactSuppressions(request, env, origin) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse({ ok: false, error: "admin authorization is required" }, 401, origin, env);
  }
  const db = requireDatabase(env);
  const url = new URL(request.url);
  const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit") || "50")));
  const email = url.searchParams.get("email");
  const query = email
    ? db
        .prepare("SELECT * FROM gca_contact_suppressions WHERE email = ?1 LIMIT ?2")
        .bind(normalizeEmail(email), limit)
    : db
        .prepare("SELECT * FROM gca_contact_suppressions ORDER BY created_at DESC LIMIT ?1")
        .bind(limit);
  const { results } = await query.all();
  return jsonResponse({
    ok: true,
    count: results.length,
    records: results.map((row) => rowToContactSuppression(row))
  }, 200, origin, env);
}

async function listMemberTable(request, env, origin, table, mapper, allowedFilters = []) {
  if (!isAdminAuthorized(request, env)) {
    return jsonResponse({ ok: false, error: "admin authorization is required" }, 401, origin, env);
  }
  const db = requireDatabase(env);
  const url = new URL(request.url);
  const limit = Math.max(1, Math.min(100, Number(url.searchParams.get("limit") || "50")));
  const filters = [];
  const values = [];
  for (const [param, column, normalizer] of allowedFilters) {
    const raw = url.searchParams.get(param);
    if (raw) {
      filters.push(`${column} = ?${values.length + 1}`);
      values.push(normalizer ? normalizer(raw) : raw);
    }
  }
  const where = filters.length ? ` WHERE ${filters.join(" AND ")}` : "";
  const orderColumn = table === "gca_wallet_verifications"
    ? "checked_at"
    : table === "gca_credit_ledger"
      ? "activated_at"
      : table === "gca_credit_usage"
        ? "used_at"
      : table === "gca_service_requests"
        ? "created_at"
      : table === "gca_service_request_reviews"
        ? "reviewed_at"
      : table === "gca_service_request_followups"
        ? "submitted_at"
      : table === "gca_member_reviews"
        ? "reviewed_at"
      : table === "gca_holding_verifications"
        ? "checked_at"
      : table === "gca_member_benefit_transfers"
        ? "verified_at"
      : table === "gca_member_ledger"
        ? "updated_at"
        : "updated_at";
  const query = db.prepare(`SELECT * FROM ${table}${where} ORDER BY ${orderColumn} DESC LIMIT ?${values.length + 1}`);
  const { results } = await query.bind(...values, limit).all();
  return jsonResponse({
    ok: true,
    count: results.length,
    records: results.map((row) => mapper(row))
  }, 200, origin, env);
}

function health(origin, env) {
  const contactEmail = String(env.CONTACT_EMAIL || OFFICIAL_CONTACT_EMAIL).trim() || OFFICIAL_CONTACT_EMAIL;
  return jsonResponse({
    ok: true,
    service: "gca-registration-api",
    workerRelease: WORKER_RELEASE,
    contactEmail,
    packetVersion: EMAIL_REGISTRATION_VERSION,
    contactSuppressionVersion: CONTACT_SUPPRESSION_VERSION,
    memberAccessVersion: MEMBER_ACCESS_VERSION,
    legacyMemberAccessVersion: LEGACY_MEMBER_ACCESS_VERSION,
    accountStatusVersion: ACCOUNT_STATUS_VERSION,
    accountStatusRotationVersion: ACCOUNT_STATUS_ROTATION_VERSION,
    accountStatusRecoveryRequestVersion:
      ACCOUNT_STATUS_RECOVERY_REQUEST_VERSION,
    accountStatusRecoveryApprovalVersion:
      ACCOUNT_STATUS_RECOVERY_APPROVAL_VERSION,
    accountStatusRecoveryVersion: ACCOUNT_STATUS_RECOVERY_VERSION,
    creditUsageVersion: CREDIT_USAGE_VERSION,
    serviceRequestVersion: SERVICE_REQUEST_VERSION,
    accountServiceRequestVersion: ACCOUNT_SERVICE_REQUEST_VERSION,
    accountServiceRequestStatusVersion:
      ACCOUNT_SERVICE_REQUEST_STATUS_VERSION,
    accountServiceRequestFollowupVersion:
      ACCOUNT_SERVICE_REQUEST_FOLLOWUP_VERSION,
    accountServiceRequestCancellationVersion:
      ACCOUNT_SERVICE_REQUEST_CANCELLATION_VERSION,
    accountServiceDeliveryReceiptVersion:
      ACCOUNT_SERVICE_DELIVERY_RECEIPT_VERSION,
    serviceRequestReviewVersion:
      SERVICE_REQUEST_REVIEW_VERSION,
    memberReviewVersion: MEMBER_REVIEW_VERSION,
    holdingVerificationVersion: HOLDING_VERIFICATION_VERSION,
    memberBenefitTransferVersion: MEMBER_BENEFIT_TRANSFER_VERSION,
    memberBenefitSourceWallet: MEMBER_BENEFIT_SOURCE_WALLET,
    chainId: CHAIN_ID,
    contractAddress: CONTRACT_ADDRESS,
    memberAccessLedger: "cloudflare-d1",
    storage: "cloudflare-d1",
    antiSpam: {
      honeypotFields: HONEYPOT_FIELDS,
      rejectsFilledHoneypotFields: true,
      rateLimitsStillRequired: true
    }
  }, 200, origin, env);
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("origin") || "";
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders(origin, env) });
    }

    try {
      const url = new URL(request.url);
      if ((request.method === "GET" || request.method === "HEAD") && url.pathname === "/") {
        return Response.redirect(OFFICIAL_SITE_URL, 302);
      }
      if (request.method === "GET" && url.pathname === "/health") {
        return health(origin, env);
      }
      if (request.method === "GET" && url.pathname === "/gca/access-config") {
        return accessConfig(origin, env);
      }
      if (url.pathname === "/gca/email-registrations") {
        if (request.method === "POST") {
          return await submitEmailRegistration(request, env, origin);
        }
        if (request.method === "GET") {
          return await listEmailRegistrations(request, env, origin);
        }
      }
      if (url.pathname === "/gca/wallet-verifications") {
        if (request.method === "POST") {
          return await submitWalletVerification(request, env, origin);
        }
        if (request.method === "GET") {
          return await listMemberTable(
            request,
            env,
            origin,
            "gca_wallet_verifications",
            rowToWalletVerification,
            [["walletAddress", "wallet_address", normalizeWallet]]
          );
        }
      }
      if (url.pathname === "/gca/member-access") {
        if (request.method === "POST") {
          return await submitMemberAccess(request, env, origin);
        }
        if (request.method === "GET") {
          return await listMemberTable(
            request,
            env,
            origin,
            "gca_member_accounts",
            rowToMemberAccount,
            [
              ["email", "email", normalizeEmail],
              ["walletAddress", "wallet_address", normalizeWallet]
            ]
          );
        }
      }
      if (url.pathname === "/gca/account-status") {
        if (request.method === "POST") {
          return await submitAccountStatus(request, env, origin);
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (url.pathname === "/gca/account-status/rotate") {
        if (request.method === "POST") {
          return await submitAccountStatusRotation(request, env, origin);
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (url.pathname === "/gca/account-status/recovery-requests") {
        if (request.method === "POST") {
          return await submitAccountStatusRecoveryRequest(request, env, origin);
        }
        if (request.method === "GET") {
          return await listAccountStatusRecoveryRequests(
            request,
            env,
            origin
          );
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (url.pathname === "/gca/account-status/recovery-approvals") {
        if (request.method === "POST") {
          return await approveAccountStatusRecovery(request, env, origin);
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (url.pathname === "/gca/account-status/recover") {
        if (request.method === "POST") {
          return await submitAccountStatusRecovery(request, env, origin);
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (url.pathname === "/gca/account-service-requests") {
        if (request.method === "POST") {
          return await submitAccountServiceRequest(request, env, origin);
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (url.pathname === "/gca/account-service-requests/status") {
        if (request.method === "POST") {
          return await readAccountServiceRequests(request, env, origin);
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (
        url.pathname ===
        "/gca/account-service-requests/follow-ups"
      ) {
        if (request.method === "POST") {
          return await submitAccountServiceRequestFollowup(
            request,
            env,
            origin
          );
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (
        url.pathname ===
        "/gca/account-service-requests/cancellations"
      ) {
        if (request.method === "POST") {
          return await submitAccountServiceRequestCancellation(
            request,
            env,
            origin
          );
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (
        url.pathname ===
        "/gca/account-service-requests/delivery-receipts"
      ) {
        if (request.method === "POST") {
          return await submitAccountServiceDeliveryReceipt(
            request,
            env,
            origin
          );
        }
        return jsonResponse({ ok: false, error: "method not allowed" }, 405, origin, env);
      }
      if (url.pathname === "/gca/credit-ledger" && request.method === "GET") {
        return await listMemberTable(
          request,
          env,
          origin,
          "gca_credit_ledger",
          rowToCreditLedger,
          [["walletAddress", "wallet_address", normalizeWallet]]
        );
      }
      if (url.pathname === "/gca/credit-usage") {
        if (request.method === "POST") {
          return await recordCreditUsage(request, env, origin);
        }
        if (request.method === "GET") {
          return await listMemberTable(
            request,
            env,
            origin,
            "gca_credit_usage",
            rowToCreditUsage,
            [
              ["walletAddress", "wallet_address", normalizeWallet],
              ["creditLedgerId", "credit_ledger_id", null]
            ]
          );
        }
      }
      if (url.pathname === "/gca/service-requests") {
        if (request.method === "POST") {
          return await recordServiceRequest(request, env, origin);
        }
        if (request.method === "GET") {
          return await listMemberTable(
            request,
            env,
            origin,
            "gca_service_requests",
            rowToServiceRequest,
            [
              ["walletAddress", "wallet_address", normalizeWallet],
              ["creditLedgerId", "credit_ledger_id", null],
              ["serviceRequestId", "service_request_id", null]
            ]
          );
        }
      }
      if (url.pathname === "/gca/service-request-reviews") {
        if (request.method === "POST") {
          return await reviewServiceRequest(request, env, origin);
        }
        if (request.method === "GET") {
          return await listMemberTable(
            request,
            env,
            origin,
            "gca_service_request_reviews",
            rowToServiceRequestReview,
            [
              [
                "serviceRequestId",
                "service_request_id",
                (value) => {
                  const normalized = String(value || "")
                    .trim()
                    .toLowerCase();
                  if (!SERVICE_REQUEST_ID_RE.test(normalized)) {
                    throw new ApiError(
                      "serviceRequestId must be a valid GCA service request id"
                    );
                  }
                  return normalized;
                }
              ],
              ["decision", "decision", null],
              ["reviewerId", "reviewer_id", null]
            ]
          );
        }
      }
      if (
        url.pathname === "/gca/service-request-followups" &&
        request.method === "GET"
      ) {
        return await listMemberTable(
          request,
          env,
          origin,
          "gca_service_request_followups",
          rowToServiceRequestFollowup,
          [
            [
              "serviceRequestId",
              "service_request_id",
              (value) => {
                const normalized = String(value || "")
                  .trim()
                  .toLowerCase();
                if (!SERVICE_REQUEST_ID_RE.test(normalized)) {
                  throw new ApiError(
                    "serviceRequestId must be a valid GCA service request id"
                  );
                }
                return normalized;
              }
            ],
            ["accountId", "account_id", null]
          ]
        );
      }
      if (url.pathname === "/gca/member-ledger" && request.method === "GET") {
        return await listMemberTable(
          request,
          env,
          origin,
          "gca_member_ledger",
          rowToMemberLedger,
          [["walletAddress", "wallet_address", normalizeWallet]]
        );
      }
      if (url.pathname === "/gca/member-reviews") {
        if (request.method === "POST") {
          return await recordMemberReview(request, env, origin);
        }
        if (request.method === "GET") {
          return await listMemberTable(
            request,
            env,
            origin,
            "gca_member_reviews",
            rowToMemberReview,
            [
              ["walletAddress", "wallet_address", normalizeWallet],
              ["memberLedgerId", "member_ledger_id", null],
              ["decision", "decision", null]
            ]
          );
        }
      }
      if (url.pathname === "/gca/holding-verifications" && request.method === "GET") {
        return await listMemberTable(
          request,
          env,
          origin,
          "gca_holding_verifications",
          rowToHoldingVerification,
          [
            ["walletAddress", "wallet_address", normalizeWallet],
            ["memberLedgerId", "member_ledger_id", null],
            ["status", "status", null]
          ]
        );
      }
      if (url.pathname === "/gca/member-benefit-transfers") {
        if (request.method === "POST") {
          return await recordMemberBenefitTransfer(request, env, origin);
        }
        if (request.method === "GET") {
          return await listMemberTable(
            request,
            env,
            origin,
            "gca_member_benefit_transfers",
            rowToMemberBenefitTransfer,
            [
              ["walletAddress", "wallet_address", normalizeWallet],
              ["memberLedgerId", "member_ledger_id", null],
              ["transactionHash", "transaction_hash", normalizeTxHash]
            ]
          );
        }
      }
      if (url.pathname === "/gca/contact-suppressions") {
        if (request.method === "POST") {
          return await submitContactSuppression(request, env, origin);
        }
        if (request.method === "GET") {
          return await listContactSuppressions(request, env, origin);
        }
      }
      return jsonResponse({ ok: false, error: "not found" }, 404, origin, env);
    } catch (error) {
      const status = error instanceof ApiError ? error.status : 500;
      const message = status === 500 ? "internal server error" : error.message;
      return jsonResponse({ ok: false, error: message }, status, origin, env);
    }
  }
};
