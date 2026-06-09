(function () {
  const root = document.documentElement;
  const minVisibleMs = 240;
  const actionResetMs = 6000;
  const progressCap = 92;
  const loadingControls = new Set();
  let progressValue = 0;
  let progressTimer = null;
  let progressElement = null;
  let progressBar = null;

  function getLoadingStartedAt() {
    return Number(root.getAttribute("data-loading-started-at") || Date.now());
  }

  function getContentElement() {
    return document.getElementById("fgPageContent");
  }

  function getSkeletonElement() {
    return document.getElementById("fgPageSkeleton");
  }

  function getProgressElements() {
    if (!progressElement) {
      progressElement = document.getElementById("fgTopProgress");
      progressBar = progressElement ? progressElement.querySelector(".fg-top-progress__bar") : null;
    }
    return { progressElement, progressBar };
  }

  function setProgress(value) {
    const { progressElement: element, progressBar: bar } = getProgressElements();
    if (!element || !bar) {
      return;
    }
    progressValue = Math.max(0, Math.min(100, value));
    element.classList.add("is-active");
    element.classList.remove("is-complete");
    bar.style.transform = `scaleX(${progressValue / 100})`;
  }

  function startProgress() {
    clearInterval(progressTimer);
    setProgress(Math.max(progressValue, 12));
    progressTimer = window.setInterval(function () {
      if (progressValue >= progressCap) {
        clearInterval(progressTimer);
        return;
      }
      const step = Math.max(1.2, (progressCap - progressValue) * 0.12);
      setProgress(progressValue + step);
    }, 170);
  }

  function completeProgress() {
    const { progressElement: element } = getProgressElements();
    if (!element) {
      return;
    }
    clearInterval(progressTimer);
    setProgress(100);
    window.setTimeout(function () {
      element.classList.add("is-complete");
      element.classList.remove("is-active");
      progressValue = 0;
      if (progressBar) {
        progressBar.style.transform = "scaleX(0)";
      }
    }, 210);
  }

  function actionLabelFor(element) {
    const explicit = element.getAttribute("data-loading-text");
    if (explicit) {
      return explicit;
    }

    const text = (
      element.dataset.originalLabel ||
      element.getAttribute("value") ||
      element.textContent ||
      ""
    ).trim().toLowerCase();

    const labelMap = [
      [/export|download|excel|pdf/, "Exporting..."],
      [/approve|confirm/, "Approving..."],
      [/delete|remove/, "Deleting..."],
      [/update|edit/, "Updating..."],
      [/save/, "Saving..."],
      [/submit/, "Submitting..."],
      [/add/, "Adding..."],
      [/create/, "Creating..."],
      [/check\s?in|check\s?out|complete|start|log/, "Saving..."],
      [/filter|apply/, "Applying..."],
      [/send/, "Sending..."],
    ];

    for (const [pattern, label] of labelMap) {
      if (pattern.test(text)) {
        return label;
      }
    }
    return "Working...";
  }

  function rememberOriginalState(element) {
    if (element.dataset.loadingBound === "true") {
      return;
    }
    element.dataset.loadingBound = "true";
    if (element.tagName === "INPUT") {
      element.dataset.originalLabel = element.value;
    } else {
      element.dataset.originalLabel = element.innerHTML;
    }
    element.dataset.originalWidth = String(element.offsetWidth || 0);
  }

  function setLoadingState(element) {
    if (!element || element.dataset.loadingActive === "true") {
      return;
    }
    rememberOriginalState(element);
    const label = actionLabelFor(element);
    const minWidth = Number(element.dataset.originalWidth || 0);

    if (minWidth > 0) {
      element.style.minWidth = `${minWidth}px`;
    }

    if (element.tagName === "INPUT") {
      element.value = label;
      element.disabled = true;
    } else {
      element.innerHTML = `<span class="fg-loading-action__content"><span class="fg-inline-spinner" aria-hidden="true"></span><span>${label}</span></span>`;
      if ("disabled" in element) {
        element.disabled = true;
      }
      if (element.tagName === "A") {
        element.setAttribute("aria-disabled", "true");
        element.classList.add("disabled");
      }
    }

    element.classList.add("fg-loading-action");
    element.dataset.loadingActive = "true";
    loadingControls.add(element);
  }

  function restoreLoadingState(element) {
    if (!element || element.dataset.loadingActive !== "true") {
      return;
    }

    if (element.tagName === "INPUT") {
      element.value = element.dataset.originalLabel || element.value;
      element.disabled = false;
    } else {
      element.innerHTML = element.dataset.originalLabel || element.innerHTML;
      if ("disabled" in element) {
        element.disabled = false;
      }
      if (element.tagName === "A") {
        element.removeAttribute("aria-disabled");
        element.classList.remove("disabled");
      }
    }

    element.classList.remove("fg-loading-action");
    element.dataset.loadingActive = "false";
    element.style.minWidth = "";
    loadingControls.delete(element);
  }

  function restoreAllLoadingControls() {
    Array.from(loadingControls).forEach(restoreLoadingState);
  }

  function actionAnchor(element) {
    if (!element || element.tagName !== "A" || !element.classList.contains("btn")) {
      return false;
    }
    const text = (element.textContent || "").trim().toLowerCase();
    return /export|download|excel|pdf|print/.test(text);
  }

  function shouldTrackNavigation(anchor, event) {
    if (!anchor || !anchor.href) {
      return false;
    }
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return false;
    }
    if (anchor.target && anchor.target !== "_self") {
      return false;
    }
    if (anchor.hasAttribute("download")) {
      return false;
    }
    if (anchor.getAttribute("href").startsWith("#")) {
      return false;
    }
    try {
      const url = new URL(anchor.href, window.location.href);
      if (url.origin !== window.location.origin) {
        return false;
      }
      if (
        url.pathname === window.location.pathname &&
        url.search === window.location.search &&
        url.hash
      ) {
        return false;
      }
      return true;
    } catch (error) {
      return false;
    }
  }

  function buildSkeletonMarkup(content) {
    if (!content) {
      return "";
    }

    const tableCount = Math.min(
      4,
      content.querySelectorAll(".table-responsive, .soft-table, table.table").length
    );
    const chartCount = Math.min(3, content.querySelectorAll("canvas").length);
    const formCount = Math.min(2, content.querySelectorAll("form").length);
    const metricCount = Math.min(
      6,
      Math.max(
        content.querySelectorAll(".mini-metric, .kpi-card, .dashboard-card, .result-card").length,
        4
      )
    );

    const sections = [];

    sections.push(
      `<section class="fg-skeleton-section">
        <div class="fg-skeleton-row justify-content-between align-items-start">
          <div style="flex: 1 1 340px;">
            <div class="fg-skeleton-line" style="width: 7rem;"></div>
            <div class="fg-skeleton-line" style="width: min(26rem, 82%); height: 1.45rem; margin-top: 1rem;"></div>
            <div class="fg-skeleton-line" style="width: min(18rem, 60%); margin-top: 0.85rem;"></div>
          </div>
          <div class="fg-skeleton-row" style="width: min(22rem, 100%); justify-content: flex-end;">
            <div class="fg-skeleton-pill" style="width: 8.5rem;"></div>
            <div class="fg-skeleton-pill" style="width: 8.5rem;"></div>
          </div>
        </div>
      </section>`
    );

    if (formCount > 0) {
      for (let index = 0; index < formCount; index += 1) {
        sections.push(
          `<section class="fg-skeleton-form">
            <div class="fg-skeleton-form-grid">
              <div><div class="fg-skeleton-line" style="width: 5rem; margin-bottom: 0.65rem;"></div><div class="fg-skeleton-pill"></div></div>
              <div><div class="fg-skeleton-line" style="width: 6rem; margin-bottom: 0.65rem;"></div><div class="fg-skeleton-pill"></div></div>
              <div><div class="fg-skeleton-line" style="width: 5.4rem; margin-bottom: 0.65rem;"></div><div class="fg-skeleton-pill"></div></div>
              <div><div class="fg-skeleton-line" style="width: 4.8rem; margin-bottom: 0.65rem;"></div><div class="fg-skeleton-pill"></div></div>
            </div>
            <div class="fg-skeleton-row mt-3">
              <div class="fg-skeleton-pill" style="width: 8rem;"></div>
              <div class="fg-skeleton-pill" style="width: 7rem;"></div>
            </div>
          </section>`
        );
      }
    }

    sections.push(
      `<section class="fg-skeleton-grid">
        ${Array.from({ length: metricCount })
          .map(function (_, index) {
            return `<div class="fg-skeleton-card">
              <div class="fg-skeleton-line" style="width: ${5.6 + (index % 3) * 0.8}rem;"></div>
              <div class="fg-skeleton-line" style="width: ${4.2 + (index % 2) * 1.5}rem; height: 1.7rem; margin-top: 1rem;"></div>
              <div class="fg-skeleton-line" style="width: 6.5rem; margin-top: 1rem;"></div>
            </div>`;
          })
          .join("")}
      </section>`
    );

    if (chartCount > 0) {
      sections.push(
        `<section class="fg-skeleton-grid">
          ${Array.from({ length: chartCount })
            .map(function (_, index) {
              return `<div class="fg-skeleton-chart">
                <div class="fg-skeleton-line" style="width: ${8 + index}rem; margin-bottom: 1rem;"></div>
                <div class="fg-skeleton-block" style="height: 210px;"></div>
              </div>`;
            })
            .join("")}
        </section>`
      );
    }

    if (tableCount > 0) {
      for (let index = 0; index < tableCount; index += 1) {
        sections.push(
          `<section class="fg-skeleton-table">
            <div class="fg-skeleton-table__inner">
              <div class="fg-skeleton-line" style="width: ${9 + index}rem; margin-bottom: 1rem;"></div>
              <div class="fg-skeleton-table__header">
                <div class="fg-skeleton-cell"></div>
                <div class="fg-skeleton-cell"></div>
                <div class="fg-skeleton-cell"></div>
                <div class="fg-skeleton-cell"></div>
                <div class="fg-skeleton-cell"></div>
              </div>
              ${Array.from({ length: 5 })
                .map(function () {
                  return `<div class="fg-skeleton-table__row">
                    <div class="fg-skeleton-cell"></div>
                    <div class="fg-skeleton-cell"></div>
                    <div class="fg-skeleton-cell"></div>
                    <div class="fg-skeleton-cell"></div>
                    <div class="fg-skeleton-cell"></div>
                  </div>`;
                })
                .join("")}
            </div>
          </section>`
        );
      }
    }

    return `<div class="fg-skeleton-stack">${sections.join("")}</div>`;
  }

  function prepareSkeleton() {
    const content = getContentElement();
    const skeleton = getSkeletonElement();
    if (!content || !skeleton) {
      return;
    }
    content.setAttribute("aria-busy", "true");
    if (!skeleton.dataset.ready) {
      skeleton.innerHTML = buildSkeletonMarkup(content);
      skeleton.dataset.ready = "true";
    }
  }

  function startLoadingState() {
    root.setAttribute("data-app-loading", "true");
    root.setAttribute("data-loading-started-at", String(Date.now()));
    prepareSkeleton();
    startProgress();
  }

  function finishLoadingState() {
    const delay = Math.max(0, minVisibleMs - (Date.now() - getLoadingStartedAt()));
    window.setTimeout(function () {
      root.setAttribute("data-app-loading", "finishing");
      completeProgress();
      restoreAllLoadingControls();
      window.setTimeout(function () {
        root.setAttribute("data-app-loading", "false");
        root.removeAttribute("data-app-loading");
        const content = getContentElement();
        const skeleton = getSkeletonElement();
        if (content) {
          content.removeAttribute("aria-busy");
        }
        if (skeleton) {
          skeleton.dataset.ready = "";
          skeleton.innerHTML = "";
        }
      }, 250);
    }, delay);
  }

  function bindFormLoading() {
    document.addEventListener(
      "submit",
      function (event) {
        const submitter = event.submitter || event.target.querySelector('button[type="submit"], input[type="submit"]');
        if (submitter) {
          setLoadingState(submitter);
          window.setTimeout(function () {
            restoreLoadingState(submitter);
          }, actionResetMs);
        }
        startLoadingState();
      },
      true
    );
  }

  function bindAnchorLoading() {
    document.addEventListener(
      "click",
      function (event) {
        const anchor = event.target.closest("a[href]");
        if (!anchor) {
          return;
        }

        if (actionAnchor(anchor)) {
          setLoadingState(anchor);
          window.setTimeout(function () {
            restoreLoadingState(anchor);
          }, actionResetMs);
        }

        if (shouldTrackNavigation(anchor, event)) {
          startLoadingState();
        }
      },
      true
    );
  }

  function bindButtonProtection() {
    document.addEventListener(
      "click",
      function (event) {
        const control = event.target.closest("button, input[type='submit'], a.btn");
        if (!control) {
          return;
        }
        if (control.dataset.loadingActive === "true") {
          event.preventDefault();
          event.stopPropagation();
        }
      },
      true
    );
  }

  function boot() {
    prepareSkeleton();
    startProgress();
    bindFormLoading();
    bindAnchorLoading();
    bindButtonProtection();

    if (document.readyState === "complete") {
      finishLoadingState();
    } else {
      window.addEventListener("load", finishLoadingState, { once: true });
    }

    window.addEventListener("pageshow", restoreAllLoadingControls);
    window.addEventListener("focus", restoreAllLoadingControls);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
