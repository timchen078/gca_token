(() => {
  "use strict";

  const RPC_URL = "https://mainnet.base.org";
  const CONTRACT_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6";
  const EXPECTED_CHAIN_ID = 8453n;
  const EXPECTED_CHAIN_ID_HEX = "0x2105";
  const EXPECTED_NAME = "GCA";
  const EXPECTED_SYMBOL = "GCA";
  const EXPECTED_DECIMALS = 18n;
  const EXPECTED_TOTAL_SUPPLY_RAW = 1000000000000000000000000000n;
  const REQUEST_TIMEOUT_MS = 8000;
  const MAX_RESPONSE_BYTES = 65536;

  const REQUESTS = Object.freeze([
    { jsonrpc: "2.0", id: 1, method: "eth_chainId", params: [] },
    {
      jsonrpc: "2.0",
      id: 2,
      method: "eth_getCode",
      params: [CONTRACT_ADDRESS, "latest"],
    },
    {
      jsonrpc: "2.0",
      id: 3,
      method: "eth_call",
      params: [{ to: CONTRACT_ADDRESS, data: "0x06fdde03" }, "latest"],
    },
    {
      jsonrpc: "2.0",
      id: 4,
      method: "eth_call",
      params: [{ to: CONTRACT_ADDRESS, data: "0x95d89b41" }, "latest"],
    },
    {
      jsonrpc: "2.0",
      id: 5,
      method: "eth_call",
      params: [{ to: CONTRACT_ADDRESS, data: "0x313ce567" }, "latest"],
    },
    {
      jsonrpc: "2.0",
      id: 6,
      method: "eth_call",
      params: [{ to: CONTRACT_ADDRESS, data: "0x18160ddd" }, "latest"],
    },
  ]);

  const COPY = {
    checking: "Reading the pinned contract from Base Mainnet...",
    ready: "Live identity matched: Base Mainnet, contract code, GCA metadata, and fixed total supply all agree.",
    mismatch: "Identity mismatch detected. Stop and verify the contract through the official BaseScan link before interacting.",
    failed: "Live read-only check is temporarily unavailable. The public Base RPC is rate-limited; use the official BaseScan link to verify.",
    unavailable: "Unavailable",
    refresh: "Refresh check",
  };

  function setText(container, field, value) {
    const element = container.querySelector(`[data-contract-field="${field}"]`);
    if (element) {
      element.textContent = value;
    }
  }

  function setSummary(container, state, message) {
    const summary = container.querySelector("[data-contract-summary]");
    if (!summary) {
      return;
    }
    summary.classList.remove("good", "pending", "bad");
    summary.classList.add(state);
    summary.dataset.state = state;
    summary.textContent = message;
  }

  function requireHex(value, label) {
    if (typeof value !== "string" || !/^0x(?:[0-9a-fA-F]{2})*$/.test(value)) {
      throw new Error(`${label} is not valid hexadecimal data`);
    }
    return value;
  }

  function decodeUint(value, label) {
    const hex = requireHex(value, label);
    if (hex === "0x") {
      throw new Error(`${label} is empty`);
    }
    return BigInt(hex);
  }

  function decodeAbiString(value, label) {
    const hex = requireHex(value, label).slice(2);
    if (hex.length < 128) {
      throw new Error(`${label} ABI response is too short`);
    }

    const offset = Number(BigInt(`0x${hex.slice(0, 64)}`));
    if (!Number.isSafeInteger(offset) || offset < 0 || offset % 32 !== 0) {
      throw new Error(`${label} ABI offset is invalid`);
    }
    const lengthWordStart = offset * 2;
    const lengthWordEnd = lengthWordStart + 64;
    if (lengthWordEnd > hex.length) {
      throw new Error(`${label} ABI length is missing`);
    }

    const byteLength = Number(BigInt(`0x${hex.slice(lengthWordStart, lengthWordEnd)}`));
    if (!Number.isSafeInteger(byteLength) || byteLength < 1 || byteLength > 64) {
      throw new Error(`${label} ABI string length is invalid`);
    }
    const valueStart = lengthWordEnd;
    const valueEnd = valueStart + (byteLength * 2);
    if (valueEnd > hex.length) {
      throw new Error(`${label} ABI string is truncated`);
    }

    const bytes = new Uint8Array(byteLength);
    for (let index = 0; index < byteLength; index += 1) {
      bytes[index] = Number.parseInt(hex.slice(valueStart + (index * 2), valueStart + (index * 2) + 2), 16);
    }
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  }

  function requireResponses(payload) {
    if (!Array.isArray(payload) || payload.length !== REQUESTS.length) {
      throw new Error("Base RPC batch response has the wrong shape");
    }

    const byId = new Map();
    for (const item of payload) {
      if (
        !item
        || item.jsonrpc !== "2.0"
        || !Number.isInteger(item.id)
        || !REQUESTS.some((request) => request.id === item.id)
        || Object.prototype.hasOwnProperty.call(item, "error")
        || typeof item.result !== "string"
        || byId.has(item.id)
      ) {
        throw new Error("Base RPC batch response contains an invalid item");
      }
      byId.set(item.id, item.result);
    }
    if (byId.size !== REQUESTS.length) {
      throw new Error("Base RPC batch response is incomplete");
    }
    return byId;
  }

  async function fetchIdentity() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(RPC_URL, {
        method: "POST",
        mode: "cors",
        credentials: "omit",
        cache: "no-store",
        redirect: "error",
        headers: {
          accept: "application/json",
          "content-type": "application/json",
        },
        body: JSON.stringify(REQUESTS),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`Base RPC returned HTTP ${response.status}`);
      }
      const raw = await response.text();
      if (raw.length > MAX_RESPONSE_BYTES) {
        throw new Error("Base RPC response is too large");
      }
      return requireResponses(JSON.parse(raw));
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function readIdentity(responses) {
    const chainIdHex = requireHex(responses.get(1), "chain ID").toLowerCase();
    const chainId = decodeUint(chainIdHex, "chain ID");
    const code = requireHex(responses.get(2), "contract code");
    const name = decodeAbiString(responses.get(3), "token name");
    const symbol = decodeAbiString(responses.get(4), "token symbol");
    const decimals = decodeUint(responses.get(5), "decimals");
    const totalSupplyRaw = decodeUint(responses.get(6), "total supply");
    const codeBytes = (code.length - 2) / 2;
    const matches = (
      chainId === EXPECTED_CHAIN_ID
      && chainIdHex === EXPECTED_CHAIN_ID_HEX
      && codeBytes > 0
      && name === EXPECTED_NAME
      && symbol === EXPECTED_SYMBOL
      && decimals === EXPECTED_DECIMALS
      && totalSupplyRaw === EXPECTED_TOTAL_SUPPLY_RAW
    );
    return { chainId, codeBytes, name, symbol, decimals, totalSupplyRaw, matches };
  }

  function renderIdentity(container, identity) {
    const checkedAt = new Intl.DateTimeFormat("en", {
      dateStyle: "medium",
      timeStyle: "medium",
    }).format(new Date());
    const supply = identity.totalSupplyRaw / (10n ** identity.decimals);

    setText(container, "network", `Base Mainnet / ${identity.chainId}`);
    setText(container, "code", `Present / ${identity.codeBytes.toLocaleString("en-US")} bytes`);
    setText(container, "name", identity.name);
    setText(container, "symbol", identity.symbol);
    setText(container, "decimals", identity.decimals.toString());
    setText(container, "supply", `${supply.toLocaleString("en-US")} GCA`);
    setText(container, "source", `Base public RPC / ${checkedAt}`);
    setSummary(container, identity.matches ? "good" : "bad", identity.matches ? COPY.ready : COPY.mismatch);
  }

  function renderFailure(container) {
    for (const field of ["network", "code", "name", "symbol", "decimals", "supply", "source"]) {
      setText(container, field, COPY.unavailable);
    }
    setSummary(container, "bad", COPY.failed);
  }

  async function run(container) {
    if (container.dataset.running === "true") {
      return;
    }
    const button = container.querySelector("[data-contract-action]");
    container.dataset.running = "true";
    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    }
    setSummary(container, "pending", COPY.checking);
    try {
      renderIdentity(container, readIdentity(await fetchIdentity()));
    } catch (_error) {
      renderFailure(container);
    } finally {
      if (button) {
        button.disabled = false;
        button.removeAttribute("aria-busy");
        button.textContent = COPY.refresh;
      }
      container.dataset.running = "false";
    }
  }

  for (const container of document.querySelectorAll("[data-gca-contract-identity]")) {
    const button = container.querySelector("[data-contract-action]");
    if (button) {
      button.addEventListener("click", () => run(container));
    }
    window.setTimeout(() => run(container), 0);
  }
})();
