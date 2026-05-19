const EMAIL_REGISTRATION_VERSION = "gca_email_registration_v1";
const CONTACT_SUPPRESSION_VERSION = "gca_contact_suppression_v1";
const DEFAULT_ALLOWED_ORIGINS = [
  "https://gcagochina.com",
  "https://www.gcagochina.com",
  "http://127.0.0.1:8787",
  "http://localhost:8787",
  "http://127.0.0.1:8799",
  "http://localhost:8799"
];
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
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

function requireAdmin(request, env) {
  const token = String(env.ADMIN_READ_TOKEN || "").trim();
  const header = request.headers.get("authorization") || "";
  if (!token || header !== `Bearer ${token}`) {
    throw new ApiError("admin authorization is required", 401);
  }
}

async function listEmailRegistrations(request, env, origin) {
  requireAdmin(request, env);
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
  requireAdmin(request, env);
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

function health(origin, env) {
  return jsonResponse({
    ok: true,
    service: "gca-registration-api",
    packetVersion: EMAIL_REGISTRATION_VERSION,
    contactSuppressionVersion: CONTACT_SUPPRESSION_VERSION,
    storage: "cloudflare-d1"
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
      if (request.method === "GET" && url.pathname === "/health") {
        return health(origin, env);
      }
      if (url.pathname === "/gca/email-registrations") {
        if (request.method === "POST") {
          return submitEmailRegistration(request, env, origin);
        }
        if (request.method === "GET") {
          return listEmailRegistrations(request, env, origin);
        }
      }
      if (url.pathname === "/gca/contact-suppressions") {
        if (request.method === "POST") {
          return submitContactSuppression(request, env, origin);
        }
        if (request.method === "GET") {
          return listContactSuppressions(request, env, origin);
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
