(() => {
  "use strict";

  const NETWORK = "base";
  const POOL_ADDRESS = "0xfe6a598bf738d7eec9640897064ca3a490128d3d447ced96077aef8e9dd1c1d0";
  const GCA_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6";
  const USDT_ADDRESS = "0xfde4c96c8593536e31f229ea8f37b2ada2699bb2";
  const DEX_ID = "uniswap-v4-base";
  const API_VERSION = "20230302";
  const API_URL = `https://api.geckoterminal.com/api/v2/networks/${NETWORK}/pools/${POOL_ADDRESS}`;
  const REQUEST_TIMEOUT_MS = 8000;
  const MAX_RESPONSE_BYTES = 65536;

  const COPY = {
    checking: "Checking the official pool...",
    ready: "Official pool identity verified. Values below are a browser-time GeckoTerminal snapshot.",
    failed: "Live snapshot unavailable or pool identity did not match. Use the official GeckoTerminal link to verify current data.",
    waiting: "Waiting for live snapshot",
    unavailable: "Unavailable",
    refresh: "Refresh snapshot",
  };

  function setText(container, field, value) {
    const element = container.querySelector(`[data-market-field="${field}"]`);
    if (element) {
      element.textContent = value;
    }
  }

  function setSummary(container, state, text) {
    const summary = container.querySelector("[data-market-summary]");
    if (!summary) {
      return;
    }
    summary.classList.remove("good", "pending", "bad");
    summary.classList.add(state);
    summary.dataset.state = state;
    summary.textContent = text;
  }

  function finiteNumber(value, label) {
    const number = Number(value);
    if (!Number.isFinite(number)) {
      throw new Error(`${label} is not a finite number`);
    }
    return number;
  }

  function formatUsd(value) {
    const maximumFractionDigits = value >= 1 ? 2 : (value >= 0.01 ? 6 : 12);
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      minimumFractionDigits: value >= 1 || value === 0 ? 2 : 0,
      maximumFractionDigits,
    }).format(value);
  }

  function formatChange(value) {
    const prefix = value > 0 ? "+" : "";
    return `${prefix}${value.toFixed(2)}%`;
  }

  function requireIdentity(payload) {
    const data = payload && payload.data;
    const attributes = data && data.attributes;
    const relationships = data && data.relationships;
    const expectedPoolId = `${NETWORK}_${POOL_ADDRESS}`;
    const expectedGcaId = `${NETWORK}_${GCA_ADDRESS}`;
    const expectedUsdtId = `${NETWORK}_${USDT_ADDRESS}`;

    if (
      !data
      || data.type !== "pool"
      || String(data.id || "").toLowerCase() !== expectedPoolId
      || !attributes
      || String(attributes.address || "").toLowerCase() !== POOL_ADDRESS
      || String(relationships?.base_token?.data?.id || "").toLowerCase() !== expectedGcaId
      || String(relationships?.quote_token?.data?.id || "").toLowerCase() !== expectedUsdtId
      || String(relationships?.dex?.data?.id || "") !== DEX_ID
    ) {
      throw new Error("official pool identity mismatch");
    }
    return attributes;
  }

  async function fetchSnapshot() {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(API_URL, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        cache: "no-store",
        redirect: "error",
        headers: {
          accept: `application/json;version=${API_VERSION}`,
        },
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`GeckoTerminal returned HTTP ${response.status}`);
      }
      const raw = await response.text();
      if (raw.length > MAX_RESPONSE_BYTES) {
        throw new Error("GeckoTerminal response is too large");
      }
      return JSON.parse(raw);
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function renderSnapshot(container, payload) {
    const attributes = requireIdentity(payload);
    const price = finiteNumber(attributes.base_token_price_usd, "GCA price");
    const reserve = finiteNumber(attributes.reserve_in_usd, "pool reserve");
    const volume = finiteNumber(attributes.volume_usd?.h24, "24h volume");
    const priceChange = finiteNumber(attributes.price_change_percentage?.h24, "24h price change");
    const buys = finiteNumber(attributes.transactions?.h24?.buys, "24h buys");
    const sells = finiteNumber(attributes.transactions?.h24?.sells, "24h sells");
    const checkedAt = new Intl.DateTimeFormat("en", {
      dateStyle: "medium",
      timeStyle: "medium",
    }).format(new Date());

    setText(container, "price", formatUsd(price));
    setText(container, "reserve", formatUsd(reserve));
    setText(container, "volume", formatUsd(volume));
    setText(container, "trades", `${buys + sells} (${buys} buys / ${sells} sells)`);
    setText(container, "change", formatChange(priceChange));
    setText(container, "source", `GeckoTerminal / ${checkedAt}`);

    const changeElement = container.querySelector('[data-market-field="change"]');
    if (changeElement) {
      changeElement.classList.remove("good", "bad");
      if (priceChange > 0) {
        changeElement.classList.add("good");
      } else if (priceChange < 0) {
        changeElement.classList.add("bad");
      }
    }
    setSummary(container, "good", COPY.ready);
  }

  function renderFailure(container) {
    for (const field of ["price", "reserve", "volume", "trades", "change", "source"]) {
      setText(container, field, COPY.unavailable);
    }
    setSummary(container, "bad", COPY.failed);
  }

  async function run(container) {
    if (container.dataset.running === "true") {
      return;
    }
    const button = container.querySelector("[data-market-action]");
    container.dataset.running = "true";
    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    }
    setSummary(container, "pending", COPY.checking);
    try {
      renderSnapshot(container, await fetchSnapshot());
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

  for (const container of document.querySelectorAll("[data-gca-market-snapshot]")) {
    const button = container.querySelector("[data-market-action]");
    if (button) {
      button.addEventListener("click", () => run(container));
    }
    window.setTimeout(() => run(container), 0);
  }
})();
