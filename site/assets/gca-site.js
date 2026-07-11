(() => {
  "use strict";

  const script = document.currentScript;
  const rootUrl = script ? new URL("../", script.src) : new URL("./", document.baseURI);
  const isChinese = (document.documentElement.lang || "").toLowerCase().startsWith("zh");
  const labels = isChinese
    ? {
        skip: "跳到主要内容",
        menu: "打开主菜单",
        close: "关闭主菜单",
        top: "返回顶部",
        links: [
          ["首页", "zh-cn.html"],
          ["验证", "verify.html"],
          ["购买", "zh-buy.html"],
          ["会员", "gca/member-access/"],
          ["进度", "zh-status.html"],
          ["支持", "zh-support.html"],
          ["EN", "index.html"]
        ]
      }
    : {
        skip: "Skip to main content",
        menu: "Open main menu",
        close: "Close main menu",
        top: "Back to top",
        links: [
          ["Home", "index.html"],
          ["Verify", "verify.html"],
          ["Buy", "buy.html"],
          ["Tools", "tools.html"],
          ["Product", "product.html"],
          ["Members", "gca/member-access/"],
          ["Trust", "trust.html"],
          ["中文", "zh-cn.html"]
        ]
      };

  const main = document.querySelector("main");
  if (main) {
    if (!main.id) main.id = "main-content";
    const skip = document.createElement("a");
    skip.className = "gca-skip-link";
    skip.href = `#${main.id}`;
    skip.textContent = labels.skip;
    document.body.prepend(skip);
  }

  const nav = document.querySelector("header nav");
  const navLinks = nav && nav.querySelector(".nav-links");
  let menuButton = null;

  const normalizePath = (value) => {
    const path = value.replace(/\/index\.html$/, "/").replace(/\/$/, "");
    return path || "/";
  };

  if (nav && navLinks && !document.body.dataset.gcaNavPreserve) {
    navLinks.replaceChildren();
    labels.links.forEach(([label, path]) => {
      const anchor = document.createElement("a");
      anchor.href = new URL(path, rootUrl).href;
      anchor.textContent = label;
      const anchorPath = normalizePath(new URL(anchor.href).pathname);
      const currentPath = normalizePath(window.location.pathname);
      if (anchorPath === currentPath) anchor.setAttribute("aria-current", "page");
      navLinks.append(anchor);
    });

    if (!navLinks.id) navLinks.id = "gca-primary-links";
    menuButton = document.createElement("button");
    menuButton.type = "button";
    menuButton.className = "gca-menu-button";
    menuButton.setAttribute("aria-controls", navLinks.id);
    menuButton.setAttribute("aria-expanded", "false");
    menuButton.setAttribute("aria-label", labels.menu);
    menuButton.title = labels.menu;
    menuButton.innerHTML = '<span class="gca-menu-icon" aria-hidden="true"></span>';
    nav.insertBefore(menuButton, navLinks);

    const setMenu = (open) => {
      menuButton.setAttribute("aria-expanded", String(open));
      menuButton.setAttribute("aria-label", open ? labels.close : labels.menu);
      menuButton.title = open ? labels.close : labels.menu;
      navLinks.classList.toggle("is-open", open);
      document.body.classList.toggle("gca-menu-open", open);
    };

    menuButton.addEventListener("click", () => {
      setMenu(menuButton.getAttribute("aria-expanded") !== "true");
    });
    navLinks.addEventListener("click", (event) => {
      if (event.target.closest("a")) setMenu(false);
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        setMenu(false);
        menuButton.focus();
      }
    });
    document.addEventListener("click", (event) => {
      if (!nav.contains(event.target)) setMenu(false);
    });
    window.addEventListener("resize", () => {
      if (window.innerWidth > 820) setMenu(false);
    });
  }

  document.querySelectorAll("a[href]").forEach((anchor) => {
    let target;
    try {
      target = new URL(anchor.getAttribute("href"), document.baseURI);
    } catch {
      return;
    }

    if (/^https?:$/.test(target.protocol) && target.origin !== window.location.origin) {
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
    }

    const isLocalJson = target.pathname.endsWith(".json") &&
      (target.origin === window.location.origin || window.location.protocol === "file:");
    if (isLocalJson && !anchor.hasAttribute("data-raw-json")) {
      const viewer = new URL("data-viewer.html", rootUrl);
      viewer.searchParams.set("source", target.href);
      anchor.href = viewer.href;
      anchor.classList.add("gca-data-link");
    }
  });

  const topButton = document.createElement("button");
  topButton.type = "button";
  topButton.className = "gca-back-to-top";
  topButton.setAttribute("aria-label", labels.top);
  topButton.title = labels.top;
  topButton.textContent = "↑";
  topButton.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  document.body.append(topButton);

  const updateTopButton = () => topButton.classList.toggle("is-visible", window.scrollY > 560);
  updateTopButton();
  window.addEventListener("scroll", updateTopButton, { passive: true });
})();
