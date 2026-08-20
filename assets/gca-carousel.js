(() => {
  "use strict";

  const carousels = document.querySelectorAll("[data-carousel]");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  carousels.forEach((carousel) => {
    const track = carousel.querySelector("[data-carousel-track]");
    const slides = Array.from(carousel.querySelectorAll("[data-carousel-slide]"));
    const dots = Array.from(carousel.querySelectorAll("[data-carousel-dot]"));
    const previous = carousel.querySelector("[data-carousel-prev]");
    const next = carousel.querySelector("[data-carousel-next]");
    const counter = carousel.querySelector("[data-carousel-counter]");
    const status = carousel.querySelector("[data-carousel-status]");
    if (!track || slides.length < 2) return;

    const isChinese = (document.documentElement.lang || "").toLowerCase().startsWith("zh");
    const slideLabel = isChinese ? "当前显示第" : "Showing banner";
    const ofLabel = isChinese ? "张，共" : "of";
    const endLabel = isChinese ? "张" : "";
    let index = 0;
    let timer = null;
    let pointerStart = null;

    const render = (nextIndex, announce = false) => {
      index = (nextIndex + slides.length) % slides.length;
      track.style.transform = `translateX(-${index * 100}%)`;
      slides.forEach((slide, slideIndex) => {
        const active = slideIndex === index;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", String(!active));
        slide.querySelectorAll("a, button").forEach((control) => {
          if (active) control.removeAttribute("tabindex");
          else control.setAttribute("tabindex", "-1");
        });
      });
      dots.forEach((dot, dotIndex) => {
        const active = dotIndex === index;
        dot.classList.toggle("is-active", active);
        dot.setAttribute("aria-selected", String(active));
        dot.tabIndex = active ? 0 : -1;
      });
      if (counter) counter.textContent = `${String(index + 1).padStart(2, "0")} / ${String(slides.length).padStart(2, "0")}`;
      if (announce && status) status.textContent = `${slideLabel} ${index + 1} ${ofLabel} ${slides.length}${endLabel}`;
    };

    const stop = () => {
      if (timer) window.clearInterval(timer);
      timer = null;
    };

    const start = () => {
      stop();
      if (reducedMotion.matches || document.hidden) return;
      timer = window.setInterval(() => render(index + 1), 6500);
    };

    const select = (nextIndex) => {
      render(nextIndex, true);
      start();
    };

    previous?.addEventListener("click", () => select(index - 1));
    next?.addEventListener("click", () => select(index + 1));
    dots.forEach((dot, dotIndex) => {
      dot.addEventListener("click", () => select(dotIndex));
      dot.addEventListener("keydown", (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
        event.preventDefault();
        const direction = event.key === "ArrowRight" ? 1 : -1;
        const targetIndex = (dotIndex + direction + dots.length) % dots.length;
        select(targetIndex);
        dots[targetIndex].focus();
      });
    });

    carousel.addEventListener("mouseenter", stop);
    carousel.addEventListener("mouseleave", start);
    carousel.addEventListener("focusin", stop);
    carousel.addEventListener("focusout", (event) => {
      if (!carousel.contains(event.relatedTarget)) start();
    });
    carousel.addEventListener("pointerdown", (event) => {
      pointerStart = event.clientX;
    });
    carousel.addEventListener("pointerup", (event) => {
      if (pointerStart === null) return;
      const distance = event.clientX - pointerStart;
      pointerStart = null;
      if (Math.abs(distance) > 48) select(index + (distance < 0 ? 1 : -1));
    });
    carousel.addEventListener("pointercancel", () => {
      pointerStart = null;
    });
    document.addEventListener("visibilitychange", start);
    reducedMotion.addEventListener?.("change", start);

    render(0);
    start();
  });
})();
