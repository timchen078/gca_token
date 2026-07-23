(() => {
  "use strict";

  const API_BASE_URL = "https://gca-registration-api.gcagochina.workers.dev";
  const CHAIN_ID = 8453;
  const CONTRACT_ADDRESS = "0x3197c42f4a06f7be32a9a742ac2a766f0ff682c6";
  const REQUEST_TIMEOUT_MS = 8000;
  const MAX_PUBLIC_JSON_BYTES = 32768;
  const ADMIN_PATHS = [
    "/gca/email-registrations",
    "/gca/contact-suppressions",
    "/gca/wallet-verifications",
    "/gca/member-access",
    "/gca/credit-ledger",
    "/gca/member-ledger",
    "/gca/member-reviews",
  ];
  const PENDING_PATHS = [
    "/gca/service-requests",
    "/gca/credit-usage",
  ];

  const COPY = {
    en: {
      waiting: "Waiting",
      checking: "Checking...",
      rerun: "Run live check",
      healthOk: "Service, chain and contract match",
      configOk: "Identity and no-custody boundaries match",
      protectedOk: (count) => `${count}/${ADMIN_PATHS.length} anonymous reads rejected`,
      pendingNotDeployed: "2/2 prepared routes are not deployed",
      pendingProtected: "2/2 routes are deployed and token protected",
      pendingMixed: "Prepared-route state needs operator review",
      unavailable: "Live response unavailable",
      healthInvalid: "Service identity does not match",
      configInvalid: "Access configuration does not match",
      protectionInvalid: "Anonymous read protection failed",
      summaryHealthyPending: "Core API healthy; two prepared routes remain undeployed",
      summaryAllLive: "Core API healthy; all checked admin routes reject anonymous reads",
      summaryDegraded: "One or more core API checks need operator review",
      checkedAt: (value) => `Checked in this browser at ${value}. No records were written.`,
    },
    zh: {
      waiting: "等待检查",
      checking: "检查中...",
      rerun: "重新检查",
      healthOk: "服务、链和合约一致",
      configOk: "身份与非托管边界一致",
      protectedOk: (count) => `${count}/${ADMIN_PATHS.length} 个匿名读取已拦截`,
      pendingNotDeployed: "2/2 个准备中路由尚未部署",
      pendingProtected: "2/2 个路由已部署并受 token 保护",
      pendingMixed: "准备中路由状态需要运营复核",
      unavailable: "无法取得实时响应",
      healthInvalid: "服务身份不一致",
      configInvalid: "访问配置不一致",
      protectionInvalid: "匿名读取保护检查失败",
      summaryHealthyPending: "核心 API 正常；两个准备中路由仍未部署",
      summaryAllLive: "核心 API 正常；已检查的管理员路由都拒绝匿名读取",
      summaryDegraded: "一个或多个核心 API 检查需要运营复核",
      checkedAt: (value) => `本浏览器检查时间：${value}。本次检查没有写入记录。`,
    },
  };

  function localeFor(container) {
    return container.dataset.locale === "zh" ? "zh" : "en";
  }

  function copyFor(container) {
    return COPY[localeFor(container)];
  }

  function formatCheckedAt(locale) {
    return new Intl.DateTimeFormat(locale === "zh" ? "zh-CN" : "en", {
      dateStyle: "medium",
      timeStyle: "medium",
    }).format(new Date());
  }

  function setState(element, state, text) {
    element.classList.remove("good", "pending", "bad");
    if (state) {
      element.classList.add(state);
    }
    element.textContent = text;
  }

  function setRow(container, id, state, text) {
    const result = container.querySelector(`[data-api-check="${id}"] [data-check-status]`);
    if (result) {
      setState(result, state, text);
    }
  }

  async function request(path, { parseJson = false } = {}) {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        method: "GET",
        mode: "cors",
        credentials: "omit",
        cache: "no-store",
        redirect: "error",
        headers: { accept: "application/json" },
        signal: controller.signal,
      });
      if (!parseJson) {
        return { reached: true, status: response.status };
      }
      if (!response.ok) {
        return { reached: true, status: response.status, payload: null };
      }
      const text = await response.text();
      if (text.length > MAX_PUBLIC_JSON_BYTES) {
        return { reached: true, status: response.status, payload: null };
      }
      try {
        return { reached: true, status: response.status, payload: JSON.parse(text) };
      } catch (_error) {
        return { reached: true, status: response.status, payload: null };
      }
    } catch (_error) {
      return { reached: false, status: 0, payload: null };
    } finally {
      window.clearTimeout(timeout);
    }
  }

  function healthMatches(result) {
    const payload = result.payload;
    return Boolean(
      result.reached
      && result.status === 200
      && payload
      && payload.ok === true
      && payload.service === "gca-registration-api"
      && Number(payload.chainId) === CHAIN_ID
      && String(payload.contractAddress || "").toLowerCase() === CONTRACT_ADDRESS
      && payload.memberAccessVersion === "gca_member_access_v1"
      && payload.memberReviewVersion === "gca_member_review_v1"
    );
  }

  function configMatches(result) {
    const payload = result.payload;
    const boundaries = payload && payload.boundaries;
    return Boolean(
      result.reached
      && result.status === 200
      && payload
      && payload.ok === true
      && Number(payload.chainId) === CHAIN_ID
      && String(payload.contractAddress || "").toLowerCase() === CONTRACT_ADDRESS
      && payload.memberAccessVersion === "gca_member_access_v1"
      && payload.memberReviewVersion === "gca_member_review_v1"
      && boundaries
      && boundaries.readOnlyWalletVerification === true
      && boundaries.requiresSignature === false
      && boundaries.requiresTransaction === false
      && boundaries.automaticTokenTransfer === false
      && boundaries.automaticMemberActivationFromSubmittedDate === false
    );
  }

  async function runCheck(container) {
    if (container.dataset.running === "true") {
      return;
    }
    container.dataset.running = "true";
    const copy = copyFor(container);
    const locale = localeFor(container);
    const button = container.querySelector("[data-api-health-action]");
    const summary = container.querySelector("[data-api-health-summary]");
    const liveFact = document.querySelector("[data-api-live-fact]");
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    setState(summary, "", copy.checking);
    for (const id of ["health", "config", "admin", "pending"]) {
      setRow(container, id, "", copy.checking);
    }

    const [health, config, adminResults, pendingResults] = await Promise.all([
      request("/health", { parseJson: true }),
      request("/gca/access-config", { parseJson: true }),
      Promise.all(ADMIN_PATHS.map((path) => request(path))),
      Promise.all(PENDING_PATHS.map((path) => request(path))),
    ]);

    const healthOk = healthMatches(health);
    const configOk = configMatches(config);
    const protectedCount = adminResults.filter((result) => result.reached && result.status === 401).length;
    const adminOk = protectedCount === ADMIN_PATHS.length;
    const anonymousReadExposed = adminResults.some((result) => result.reached && result.status === 200);
    const pendingStatuses = pendingResults.map((result) => result.status);
    const pendingNotDeployed = pendingResults.every((result) => result.reached && result.status === 404);
    const pendingProtected = pendingResults.every((result) => result.reached && result.status === 401);

    setRow(
      container,
      "health",
      healthOk ? "good" : "bad",
      healthOk ? copy.healthOk : (health.reached ? copy.healthInvalid : copy.unavailable),
    );
    setRow(
      container,
      "config",
      configOk ? "good" : "bad",
      configOk ? copy.configOk : (config.reached ? copy.configInvalid : copy.unavailable),
    );
    setRow(
      container,
      "admin",
      adminOk ? "good" : "bad",
      adminOk ? copy.protectedOk(protectedCount) : copy.protectionInvalid,
    );
    setRow(
      container,
      "pending",
      pendingProtected ? "good" : (pendingNotDeployed ? "pending" : "bad"),
      pendingProtected
        ? copy.pendingProtected
        : (pendingNotDeployed ? copy.pendingNotDeployed : copy.pendingMixed),
    );

    const coreOk = healthOk && configOk && adminOk && !anonymousReadExposed;
    let summaryText = copy.summaryDegraded;
    let summaryState = "bad";
    let resultCode = "core-review-required";
    if (coreOk && pendingProtected) {
      summaryText = copy.summaryAllLive;
      summaryState = "good";
      resultCode = "all-checked-routes-protected";
    } else if (coreOk && pendingNotDeployed) {
      summaryText = copy.summaryHealthyPending;
      summaryState = "good";
      resultCode = "core-healthy-pending-routes-undeployed";
    }
    const checkedAt = formatCheckedAt(locale);
    const summarySeparator = locale === "zh" ? "。" : ". ";
    setState(summary, summaryState, `${summaryText}${summarySeparator}${copy.checkedAt(checkedAt)}`);
    summary.dataset.result = resultCode;
    summary.dataset.pendingStatuses = pendingStatuses.join(",");
    if (liveFact) {
      setState(liveFact, summaryState, summaryText);
    }

    button.disabled = false;
    button.removeAttribute("aria-busy");
    button.textContent = copy.rerun;
    container.dataset.running = "false";
  }

  function initialize(container) {
    const button = container.querySelector("[data-api-health-action]");
    if (!button || !container.querySelector("[data-api-health-summary]")) {
      return;
    }
    button.addEventListener("click", () => runCheck(container));
    window.setTimeout(() => runCheck(container), 0);
  }

  document.querySelectorAll("[data-gca-api-health]").forEach(initialize);
})();
