const EMAIL_REGISTRATION_VERSION = "gca_email_registration_v1";
const CONTACT_SUPPRESSION_VERSION = "gca_contact_suppression_v1";
const MEMBER_ACCESS_VERSION = "gca_member_access_v1";
const CREDIT_USAGE_VERSION = "gca_credit_usage_v1";
const SERVICE_REQUEST_VERSION = "gca_service_request_v1";
const WORKER_RELEASE = "gca-registration-worker-2026-07-23-service-routes-v1";
const OFFICIAL_CONTACT_EMAIL = "support@gcagochina.com";
const OFFICIAL_SITE_URL = "https://gcagochina.com/";
const CHAIN_ID = 8453;
const CONTRACT_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6";
const BASE_RPC_URL = "https://mainnet.base.org";
const BALANCE_OF_SELECTOR = "0x70a08231";
const TOKEN_DECIMALS = 18n;
const TOKEN_UNIT = 10n ** TOKEN_DECIMALS;
const HOLDER_THRESHOLD_UNITS = 10_000n * TOKEN_UNIT;
const MEMBER_THRESHOLD_UNITS = 1_000_000n * TOKEN_UNIT;
const CREDIT_AMOUNT = 100;
const CREDIT_EXPIRY_DAYS = 180;
const MEMBER_REFRESH_DAYS = 30;
const MEMBER_HOLD_DAYS = 30;
const MEMBER_BENEFIT_AMOUNT = "10000 GCA";
const CREDIT_SERVICE_CATALOG = {
  "liquidation-replay-report": { name: "Liquidation Replay", creditUnit: 30 },
  "risk-warning-review": { name: "Risk Warning Review", creditUnit: 10 },
  "backtest-lab-run": { name: "Backtest Lab", creditUnit: 20 },
  "entry-ready-review": { name: "ENTRY_READY Review", creditUnit: 15 },
  "position-size-calculator": { name: "Position Size Calculator", creditUnit: 5 },
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

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
}

function addDaysIso(isoValue, days) {
  const date = new Date(isoValue);
  date.setUTCDate(date.getUTCDate() + days);
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
  if (packet.packetVersion && packet.packetVersion !== MEMBER_ACCESS_VERSION) {
    throw new ApiError(`packetVersion must be ${MEMBER_ACCESS_VERSION}`);
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
  return {
    email,
    walletAddress,
    displayName,
    source,
    language,
    programIntent,
    contactConsentAccepted,
    securityBoundaryAccepted,
    termsAccepted,
    memberEvidence: extractMemberEvidence(packet)
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

async function optionalIpHash(request, env) {
  const salt = String(env.PRIVACY_HASH_SALT || "").trim();
  const ip = request.headers.get("cf-connecting-ip") || "";
  if (!salt || !ip) {
    return null;
  }
  return sha256Hex(`${salt}|${ip}`);
}

async function readGcaBalanceUnits(walletAddress, env) {
  const rpcUrl = String(env.BASE_RPC_URL || BASE_RPC_URL).trim() || BASE_RPC_URL;
  const payload = {
    jsonrpc: "2.0",
    id: Date.now(),
    method: "eth_call",
    params: [
      {
        to: CONTRACT_ADDRESS,
        data: balanceOfCalldata(walletAddress)
      },
      "latest"
    ]
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
  const result = String((body && body.result) || "0x0");
  if (!/^0x[0-9a-fA-F]*$/.test(result)) {
    throw new ApiError("Base RPC returned an invalid balance result", 502);
  }
  return BigInt(result || "0x0");
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
    operatorReviewRequired: Boolean(row.operator_review_required),
    doesNotDeductCredits: Boolean(row.does_not_deduct_credits),
    requiresSignature: Boolean(row.requires_signature),
    requiresTransaction: Boolean(row.requires_transaction),
    automaticTokenTransfer: Boolean(row.automatic_token_transfer),
    writesWallet: Boolean(row.writes_wallet),
    createsTradingPermission: Boolean(row.creates_trading_permission)
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
    activatedAt: row.activated_at || "",
    nextRefreshDueAt: row.next_refresh_due_at || "",
    requiresManualReserveTransferReview: Boolean(row.requires_manual_reserve_transfer_review),
    automaticTransfer: Boolean(row.automatic_transfer),
    status: row.status,
    updatedAt: row.updated_at
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
  const gcaMemberHoldingPeriodEligible = Boolean(
    gcaMemberEligible &&
    evidence.holdingPeriodDaysVerified >= MEMBER_HOLD_DAYS &&
    evidence.evidenceTxHashFormatOk
  );
  const status = holderBonusEligible ? "verified" : "below_threshold";
  const accountStatus = gcaMemberHoldingPeriodEligible
    ? "member_active"
    : gcaMemberEligible
      ? "member_queued"
      : holderBonusEligible
        ? "holder_credit_active"
        : "below_threshold";
  return {
    holderBonusEligible,
    gcaMemberEligible,
    gcaMemberHoldingPeriodEligible,
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
        holding_period_days_verified,
        evidence_tx_hash,
        evidence_tx_hash_format_ok,
        verification_provider,
        status,
        requires_signature,
        requires_transaction
      ) VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11, ?12, ?13, ?14, ?15, ?16, ?17, 0, 0)`
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

async function maybeWriteMemberLedger(db, account, verification, evidence, now) {
  if (!verification.gcaMemberEligible) {
    return null;
  }
  const memberLedgerId = await stableId("gca_member", account.email, account.walletAddress);
  const evidenceStatus = verification.gcaMemberHoldingPeriodEligible ? "eligible" : "needs_more_information";
  const status = evidenceStatus === "eligible" ? "active" : "queued";
  const activatedAt = status === "active" ? now : "";
  const nextRefreshDueAt = status === "active" ? addDaysIso(now, MEMBER_REFRESH_DAYS) : "";
  const claimStatus = status === "active" ? "pending_manual_reserve_transfer" : "needs_holding_period_review";
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
        member_benefit_review_evidence_status = excluded.member_benefit_review_evidence_status,
        member_benefit_claim_status = excluded.member_benefit_claim_status,
        activated_at = CASE
          WHEN gca_member_ledger.activated_at IS NOT NULL AND gca_member_ledger.activated_at != '' THEN gca_member_ledger.activated_at
          ELSE excluded.activated_at
        END,
        next_refresh_due_at = excluded.next_refresh_due_at,
        status = excluded.status,
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
        status = excluded.status,
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
    thresholds: accessThresholds(),
    boundaries: accessBoundaries(),
    nextStep: memberLedger && memberLedger.status === "active"
      ? "100 credits and GCA Member ledger records are active. The 10,000 GCA member benefit remains pending manual reserve-wallet transfer review."
      : creditLedger
        ? "100 credits ledger is active. GCA Member needs 1,000,000 GCA and valid 30-day holding evidence."
        : "Wallet balance is below 10,000 GCA. No credit or member ledger record was created."
  }, 201, origin, env);
}

function accessThresholds() {
  return {
    holderBonusMinimumGca: "10000",
    holderBonusCreditAmount: CREDIT_AMOUNT,
    holderBonusCreditType: "GCA AI Quant Access credits",
    gcaMemberMinimumGca: "1000000",
    gcaMemberHoldingDays: MEMBER_HOLD_DAYS,
    memberBenefitAmount: MEMBER_BENEFIT_AMOUNT,
    creditExpiryDays: CREDIT_EXPIRY_DAYS,
    memberRefreshDays: MEMBER_REFRESH_DAYS
  };
}

function accessBoundaries() {
  return {
    readOnlyWalletVerification: true,
    requiresSignature: false,
    requiresTransaction: false,
    asksForPrivateKey: false,
    asksForSeedPhrase: false,
    asksForExchangeApiSecret: false,
    asksForWithdrawalPermission: false,
    automaticTokenTransfer: false,
    memberBenefitTransferMode: "manual-reserve-wallet-review-only",
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
    creditUsageVersion: CREDIT_USAGE_VERSION,
    serviceRequestVersion: SERVICE_REQUEST_VERSION,
    chainId: CHAIN_ID,
    contractAddress: CONTRACT_ADDRESS,
    apiBaseUrl: "https://gca-registration-api.gcagochina.workers.dev",
    accountUi: "https://gcagochina.com/gca/member-access/",
    endpoints: {
      memberAccess: "/gca/member-access",
      walletVerifications: "/gca/wallet-verifications",
      creditLedgerAdmin: "/gca/credit-ledger",
      serviceRequestsAdmin: "/gca/service-requests",
      creditUsageAdmin: "/gca/credit-usage",
      memberLedgerAdmin: "/gca/member-ledger"
    },
    antiSpam: {
      honeypotFields: HONEYPOT_FIELDS,
      rejectsFilledHoneypotFields: true,
      rateLimitsStillRequired: true
    },
    thresholds: accessThresholds(),
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
    creditUsageVersion: CREDIT_USAGE_VERSION,
    serviceRequestVersion: SERVICE_REQUEST_VERSION,
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
      if (request.method === "GET" && url.pathname === "/") {
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
