(function attachWorkspaceVault(root, factory) {
  const vault = factory();
  root.GcaWorkspaceVault = vault;
  if (typeof module !== "undefined" && module.exports) module.exports = vault;
})(typeof globalThis !== "undefined" ? globalThis : this, function createWorkspaceVault() {
  "use strict";

  const BUNDLE_SCHEMA = "gca-workspace-bundle-v1";
  const ENVELOPE_SCHEMA = "gca-encrypted-workspace-vault-v1";
  const VERSION = 1;
  const PBKDF2_ITERATIONS = 210000;
  const MIN_PASSPHRASE_LENGTH = 12;
  const MAX_PASSPHRASE_LENGTH = 256;
  const MAX_PLAINTEXT_BYTES = 4 * 1024 * 1024;
  const MAX_ENVELOPE_CHARS = 8 * 1024 * 1024;
  const MODULE_IDS = Object.freeze([
    "journal",
    "training",
    "research",
    "tradePlans",
    "portfolio",
    "requestReceipts"
  ]);
  const BOUNDARIES = Object.freeze({
    includesMemberSnapshot: false,
    includesServiceRequestPacket: false,
    mayContainUserEnteredToolContent: true,
    uploadedByPage: false,
    connectsWallet: false,
    connectsExchange: false,
    placesOrders: false
  });
  const encoder = new TextEncoder();
  const decoder = new TextDecoder("utf-8", { fatal: true });

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

  function validPassphrase(value) {
    return typeof value === "string" && value.length >= MIN_PASSPHRASE_LENGTH && value.length <= MAX_PASSPHRASE_LENGTH;
  }

  function cryptoApi(value) {
    const candidate = value || (typeof globalThis !== "undefined" ? globalThis.crypto : null);
    return candidate && candidate.subtle && typeof candidate.getRandomValues === "function" ? candidate : null;
  }

  function bytesToBase64(value) {
    const bytes = value instanceof Uint8Array ? value : new Uint8Array(value);
    if (typeof btoa === "function") {
      let binary = "";
      for (let index = 0; index < bytes.length; index += 1) binary += String.fromCharCode(bytes[index]);
      return btoa(binary);
    }
    if (typeof Buffer !== "undefined") return Buffer.from(bytes).toString("base64");
    return "";
  }

  function base64ToBytes(value, expectedLength, maxLength) {
    if (typeof value !== "string" || !value || value.length > MAX_ENVELOPE_CHARS || !/^[A-Za-z0-9+/]+={0,2}$/.test(value)) return null;
    try {
      let bytes;
      if (typeof atob === "function") {
        const binary = atob(value);
        bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
      } else if (typeof Buffer !== "undefined") {
        bytes = Uint8Array.from(Buffer.from(value, "base64"));
      } else {
        return null;
      }
      if (bytesToBase64(bytes) !== value) return null;
      if (expectedLength && bytes.length !== expectedLength) return null;
      if (maxLength && bytes.length > maxLength) return null;
      return bytes;
    } catch (error) {
      return null;
    }
  }

  function validateModules(value, validators) {
    if (!exactKeys(value, MODULE_IDS) || !validators || typeof validators !== "object") return null;
    const modules = {};
    let included = 0;
    for (const moduleId of MODULE_IDS) {
      const moduleValue = value[moduleId];
      if (moduleValue === null) {
        modules[moduleId] = null;
        continue;
      }
      const validator = validators[moduleId];
      if (typeof validator !== "function") return null;
      let validated;
      try {
        validated = validator(moduleValue);
      } catch (error) {
        return null;
      }
      if (!validated || typeof validated !== "object" || Array.isArray(validated)) return null;
      modules[moduleId] = validated;
      included += 1;
    }
    return included ? Object.freeze(modules) : null;
  }

  function parseBundle(value, validators) {
    const payload = parseJson(value);
    if (!exactKeys(payload, ["schema", "version", "exportedAt", "modules", "boundaries"])) return null;
    if (payload.schema !== BUNDLE_SCHEMA || payload.version !== VERSION || !normalizedIso(payload.exportedAt)) return null;
    if (!exactKeys(payload.boundaries, Object.keys(BOUNDARIES))) return null;
    if (Object.keys(BOUNDARIES).some((key) => payload.boundaries[key] !== BOUNDARIES[key])) return null;
    const modules = validateModules(payload.modules, validators);
    if (!modules) return null;
    const parsed = Object.freeze({
      schema: BUNDLE_SCHEMA,
      version: VERSION,
      exportedAt: payload.exportedAt,
      modules,
      boundaries: BOUNDARIES
    });
    return encoder.encode(JSON.stringify(parsed)).byteLength <= MAX_PLAINTEXT_BYTES ? parsed : null;
  }

  function buildBundle(modules, validators, exportedAt) {
    const timestamp = normalizedIso(exportedAt) || new Date().toISOString();
    return parseBundle({
      schema: BUNDLE_SCHEMA,
      version: VERSION,
      exportedAt: timestamp,
      modules,
      boundaries: BOUNDARIES
    }, validators);
  }

  function parseEnvelope(value) {
    if (typeof value === "string" && value.length > MAX_ENVELOPE_CHARS) return null;
    const payload = parseJson(value);
    if (!exactKeys(payload, ["schema", "version", "createdAt", "kdf", "cipher", "payload"])) return null;
    if (payload.schema !== ENVELOPE_SCHEMA || payload.version !== VERSION || !normalizedIso(payload.createdAt)) return null;
    if (!exactKeys(payload.kdf, ["name", "hash", "iterations", "salt"])) return null;
    if (!exactKeys(payload.cipher, ["name", "length", "tagLength", "iv"])) return null;
    if (payload.kdf.name !== "PBKDF2" || payload.kdf.hash !== "SHA-256" || payload.kdf.iterations !== PBKDF2_ITERATIONS) return null;
    if (payload.cipher.name !== "AES-GCM" || payload.cipher.length !== 256 || payload.cipher.tagLength !== 128) return null;
    const salt = base64ToBytes(payload.kdf.salt, 16);
    const iv = base64ToBytes(payload.cipher.iv, 12);
    const ciphertext = base64ToBytes(payload.payload, 0, MAX_PLAINTEXT_BYTES + 16);
    if (!salt || !iv || !ciphertext || ciphertext.length < 17) return null;
    return Object.freeze({
      envelope: Object.freeze({
        schema: ENVELOPE_SCHEMA,
        version: VERSION,
        createdAt: payload.createdAt,
        kdf: Object.freeze({ ...payload.kdf }),
        cipher: Object.freeze({ ...payload.cipher }),
        payload: payload.payload
      }),
      salt,
      iv,
      ciphertext
    });
  }

  async function deriveKey(passphrase, salt, api) {
    const material = await api.subtle.importKey(
      "raw",
      encoder.encode(passphrase),
      "PBKDF2",
      false,
      ["deriveKey"]
    );
    return api.subtle.deriveKey(
      { name: "PBKDF2", hash: "SHA-256", salt, iterations: PBKDF2_ITERATIONS },
      material,
      { name: "AES-GCM", length: 256 },
      false,
      ["encrypt", "decrypt"]
    );
  }

  async function encryptBundle(value, passphrase, validators, cryptoValue) {
    if (!validPassphrase(passphrase)) return null;
    const bundle = parseBundle(value, validators);
    const api = cryptoApi(cryptoValue);
    if (!bundle || !api) return null;
    const plaintext = encoder.encode(JSON.stringify(bundle));
    if (!plaintext.byteLength || plaintext.byteLength > MAX_PLAINTEXT_BYTES) return null;
    const salt = api.getRandomValues(new Uint8Array(16));
    const iv = api.getRandomValues(new Uint8Array(12));
    try {
      const key = await deriveKey(passphrase, salt, api);
      const encrypted = await api.subtle.encrypt(
        { name: "AES-GCM", iv, additionalData: encoder.encode(ENVELOPE_SCHEMA), tagLength: 128 },
        key,
        plaintext
      );
      return Object.freeze({
        schema: ENVELOPE_SCHEMA,
        version: VERSION,
        createdAt: bundle.exportedAt,
        kdf: Object.freeze({ name: "PBKDF2", hash: "SHA-256", iterations: PBKDF2_ITERATIONS, salt: bytesToBase64(salt) }),
        cipher: Object.freeze({ name: "AES-GCM", length: 256, tagLength: 128, iv: bytesToBase64(iv) }),
        payload: bytesToBase64(encrypted)
      });
    } catch (error) {
      return null;
    }
  }

  async function decryptBundle(value, passphrase, validators, cryptoValue) {
    if (!validPassphrase(passphrase)) return null;
    const parsedEnvelope = parseEnvelope(value);
    const api = cryptoApi(cryptoValue);
    if (!parsedEnvelope || !api) return null;
    try {
      const key = await deriveKey(passphrase, parsedEnvelope.salt, api);
      const decrypted = await api.subtle.decrypt(
        { name: "AES-GCM", iv: parsedEnvelope.iv, additionalData: encoder.encode(ENVELOPE_SCHEMA), tagLength: 128 },
        key,
        parsedEnvelope.ciphertext
      );
      if (!decrypted.byteLength || decrypted.byteLength > MAX_PLAINTEXT_BYTES) return null;
      return parseBundle(decoder.decode(decrypted), validators);
    } catch (error) {
      return null;
    }
  }

  return Object.freeze({
    BUNDLE_SCHEMA,
    ENVELOPE_SCHEMA,
    VERSION,
    PBKDF2_ITERATIONS,
    MIN_PASSPHRASE_LENGTH,
    MAX_PLAINTEXT_BYTES,
    MODULE_IDS,
    BOUNDARIES,
    validPassphrase,
    buildBundle,
    parseBundle,
    parseEnvelope,
    encryptBundle,
    decryptBundle
  });
});
