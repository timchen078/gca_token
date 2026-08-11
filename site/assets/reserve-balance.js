(() => {
  "use strict";

  const RPC_URL = "https://mainnet.base.org";
  const CONTRACT_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6";
  const RESERVE_ADDRESS = "0x5e8F84748612B913aAcC937492AC25dc5630E246";
  const EXPECTED_CHAIN_ID = 8453n;
  const EXPECTED_CHAIN_ID_HEX = "0x2105";
  const EXPECTED_TOTAL_SUPPLY_RAW = 1000000000000000000000000000n;
  const PUBLISHED_RESERVE_RAW = 600000000000000000000000000n;
  const DECIMALS = 18n;
  const REQUEST_TIMEOUT_MS = 8000;
  const MAX_RESPONSE_BYTES = 65536;
  const BALANCE_OF_CALL_DATA = `0x70a08231${RESERVE_ADDRESS.slice(2).toLowerCase().padStart(64, "0")}`;

  const NETWORK_REQUESTS = Object.freeze([
    { jsonrpc: "2.0", id: 1, method: "eth_chainId", params: [] },
    { jsonrpc: "2.0", id: 2, method: "eth_blockNumber", params: [] },
  ]);

  function buildStateRequests(blockNumberHex) {
    return Object.freeze([
      {
        jsonrpc: "2.0",
        id: 3,
        method: "eth_call",
        params: [{ to: CONTRACT_ADDRESS, data: "0x18160ddd" }, blockNumberHex],
      },
      {
        jsonrpc: "2.0",
        id: 4,
        method: "eth_call",
        params: [{ to: CONTRACT_ADDRESS, data: BALANCE_OF_CALL_DATA }, blockNumberHex],
      },
    ]);
  }

  const isChinese = (document.documentElement.lang || "").toLowerCase().startsWith("zh");
  const COPY = isChinese
    ? {
        checking: "正在从 Base Mainnet 读取储备地址当前 GCA 余额……",
        matched: (balance, share) => `只读核验成功：当前余额为 ${balance} GCA，占固定总量 ${share}，与已发布的 600,000,000 GCA 储备参考值一致。`,
        changed: (balance, share) => `只读核验成功，但当前余额为 ${balance} GCA（固定总量的 ${share}），与已发布的 600,000,000 GCA 储备参考值不同。请先核对 BaseScan。`,
        mismatch: "链或固定总量身份不一致。请停止依赖该读数，并通过官方 BaseScan 合约页核对。",
        failed: "实时只读余额检查暂时不可用。Base 公共 RPC 有频率限制，请通过官方 BaseScan 地址页核对。",
        unavailable: "暂不可用",
        refresh: "刷新余额",
        source: "Base 公共 RPC",
        locale: "zh-CN",
      }
    : {
        checking: "Reading the reserve wallet's current GCA balance from Base Mainnet...",
        matched: (balance, share) => `Read-only check passed: the current balance is ${balance} GCA, or ${share} of fixed totalSupply, matching the published 600,000,000 GCA reserve reference.`,
        changed: (balance, share) => `Read-only check passed, but the current balance is ${balance} GCA (${share} of fixed totalSupply), which differs from the published 600,000,000 GCA reserve reference. Review BaseScan first.`,
        mismatch: "The chain or fixed totalSupply identity did not match. Stop relying on this reading and verify through the official BaseScan contract page.",
        failed: "The live read-only balance check is temporarily unavailable. The public Base RPC is rate-limited; use the official BaseScan address page to verify.",
        unavailable: "Unavailable",
        refresh: "Refresh balance",
        source: "Base public RPC",
        locale: "en",
      };

  function setText(container, field, value) {
    const element = container.querySelector(`[data-reserve-field="${field}"]`);
    if (element) {
      element.textContent = value;
    }
  }

  function setSummary(container, state, message) {
    const summary = container.querySelector("[data-reserve-summary]");
    if (!summary) {
      return;
    }
    summary.classList.remove("good", "pending", "bad");
    summary.classList.add(state);
    summary.dataset.state = state;
    summary.textContent = message;
  }

  function requireHexQuantity(value, label) {
    if (typeof value !== "string" || !/^0x(?:0|[1-9a-fA-F][0-9a-fA-F]*)$/.test(value)) {
      throw new Error(`${label} is not a valid hexadecimal quantity`);
    }
    return value;
  }

  function requireHexData(value, label) {
    if (typeof value !== "string" || !/^0x(?:[0-9a-fA-F]{2})*$/.test(value)) {
      throw new Error(`${label} is not valid hexadecimal data`);
    }
    return value;
  }

  function decodeQuantity(value, label) {
    return BigInt(requireHexQuantity(value, label));
  }

  function decodeUint(value, label) {
    const hex = requireHexData(value, label);
    if (hex === "0x") {
      throw new Error(`${label} is empty`);
    }
    return BigInt(hex);
  }

  function requireResponses(payload, requests) {
    if (!Array.isArray(payload) || payload.length !== requests.length) {
      throw new Error("Base RPC batch response has the wrong shape");
    }

    const byId = new Map();
    for (const item of payload) {
      if (
        !item
        || item.jsonrpc !== "2.0"
        || !Number.isInteger(item.id)
        || !requests.some((request) => request.id === item.id)
        || Object.prototype.hasOwnProperty.call(item, "error")
        || typeof item.result !== "string"
        || byId.has(item.id)
      ) {
        throw new Error("Base RPC batch response contains an invalid item");
      }
      byId.set(item.id, item.result);
    }
    if (byId.size !== requests.length) {
      throw new Error("Base RPC batch response is incomplete");
    }
    return byId;
  }

  async function fetchRpc(requests) {
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
        body: JSON.stringify(requests),
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`Base RPC returned HTTP ${response.status}`);
      }
      const raw = await response.text();
      if (raw.length > MAX_RESPONSE_BYTES) {
        throw new Error("Base RPC response is too large");
      }
      return requireResponses(JSON.parse(raw), requests);
    } finally {
      window.clearTimeout(timeout);
    }
  }

  async function fetchReserveSnapshot() {
    const networkResponses = await fetchRpc(NETWORK_REQUESTS);
    const blockNumberHex = requireHexQuantity(networkResponses.get(2), "block number").toLowerCase();
    const stateResponses = await fetchRpc(buildStateRequests(blockNumberHex));
    return new Map([...networkResponses, ...stateResponses]);
  }

  function formatUnits(value) {
    const scale = 10n ** DECIMALS;
    const whole = value / scale;
    const fraction = (value % scale).toString().padStart(Number(DECIMALS), "0").replace(/0+$/, "");
    return `${whole.toLocaleString("en-US")}${fraction ? `.${fraction}` : ""}`;
  }

  function formatShare(value, total) {
    if (total === 0n) {
      throw new Error("total supply is zero");
    }
    const hundredths = (value * 10000n) / total;
    return `${hundredths / 100n}.${(hundredths % 100n).toString().padStart(2, "0")}%`;
  }

  function readSnapshot(responses) {
    const chainIdHex = requireHexQuantity(responses.get(1), "chain ID").toLowerCase();
    const chainId = decodeQuantity(chainIdHex, "chain ID");
    const blockNumber = decodeQuantity(responses.get(2), "block number");
    const totalSupplyRaw = decodeUint(responses.get(3), "total supply");
    const balanceRaw = decodeUint(responses.get(4), "reserve balance");
    const identityMatches = (
      chainId === EXPECTED_CHAIN_ID
      && chainIdHex === EXPECTED_CHAIN_ID_HEX
      && totalSupplyRaw === EXPECTED_TOTAL_SUPPLY_RAW
      && balanceRaw <= totalSupplyRaw
    );
    return {
      chainId,
      blockNumber,
      totalSupplyRaw,
      balanceRaw,
      identityMatches,
      disclosureMatches: balanceRaw === PUBLISHED_RESERVE_RAW,
    };
  }

  function renderSnapshot(container, snapshot) {
    const checkedAt = new Intl.DateTimeFormat(COPY.locale, {
      dateStyle: "medium",
      timeStyle: "medium",
    }).format(new Date());
    const balance = formatUnits(snapshot.balanceRaw);
    const supply = formatUnits(snapshot.totalSupplyRaw);
    const share = formatShare(snapshot.balanceRaw, snapshot.totalSupplyRaw);

    setText(container, "network", `Base Mainnet / ${snapshot.chainId}`);
    setText(container, "block", snapshot.blockNumber.toLocaleString("en-US"));
    setText(container, "wallet", RESERVE_ADDRESS);
    setText(container, "balance", `${balance} GCA`);
    setText(container, "share", share);
    setText(container, "supply", `${supply} GCA`);
    setText(container, "source", `${COPY.source} / ${checkedAt}`);

    if (!snapshot.identityMatches) {
      setSummary(container, "bad", COPY.mismatch);
    } else if (snapshot.disclosureMatches) {
      setSummary(container, "good", COPY.matched(balance, share));
    } else {
      setSummary(container, "pending", COPY.changed(balance, share));
    }
  }

  function renderFailure(container) {
    for (const field of ["network", "block", "wallet", "balance", "share", "supply", "source"]) {
      setText(container, field, COPY.unavailable);
    }
    setSummary(container, "bad", COPY.failed);
  }

  async function run(container) {
    if (container.dataset.running === "true") {
      return;
    }
    const button = container.querySelector("[data-reserve-action]");
    container.dataset.running = "true";
    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    }
    setSummary(container, "pending", COPY.checking);
    try {
      renderSnapshot(container, readSnapshot(await fetchReserveSnapshot()));
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

  for (const container of document.querySelectorAll("[data-gca-reserve-balance]")) {
    const button = container.querySelector("[data-reserve-action]");
    if (button) {
      button.addEventListener("click", () => run(container));
    }
    window.setTimeout(() => run(container), 0);
  }
})();
