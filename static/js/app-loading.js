(function () {
  const root = document.documentElement;
  const minVisibleMs = 240;
  const actionResetMs = 6000;
  const quickActionResetMs = 1800;
  const navigationFallbackMs = 12000;
  const progressCap = 92;
  const loadingControls = new Set();
  let progressValue = 0;
  let progressTimer = null;
  let finishTimer = null;
  let completeTimer = null;
  let navigationFallbackTimer = null;
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
    window.clearTimeout(completeTimer);
    completeTimer = window.setTimeout(function () {
      element.classList.add("is-complete");
      element.classList.remove("is-active");
      progressValue = 0;
      if (progressBar) {
        progressBar.style.transform = "scaleX(0)";
      }
    }, 210);
  }

  function clearSkeletonState() {
    const content = getContentElement();
    const skeleton = getSkeletonElement();
    if (content) {
      content.removeAttribute("aria-busy");
    }
    if (skeleton) {
      skeleton.dataset.ready = "";
      skeleton.innerHTML = "";
    }
  }

  function resetLoadingUi() {
    clearInterval(progressTimer);
    window.clearTimeout(finishTimer);
    window.clearTimeout(completeTimer);
    window.clearTimeout(navigationFallbackTimer);
    progressValue = 0;
    const { progressElement: element, progressBar: bar } = getProgressElements();
    if (element) {
      element.classList.remove("is-active", "is-complete");
    }
    if (bar) {
      bar.style.transform = "scaleX(0)";
    }
    root.setAttribute("data-app-loading", "false");
    root.removeAttribute("data-app-loading");
    clearSkeletonState();
    restoreAllLoadingControls();
  }

  function showActionToast(message, tone) {
    if (!message) {
      return;
    }
    let container = document.getElementById("fgActionToastStack");
    if (!container) {
      container = document.createElement("div");
      container.id = "fgActionToastStack";
      container.className = "fg-action-toast-stack";
      container.setAttribute("aria-live", "polite");
      document.body.appendChild(container);
    }

    const toast = document.createElement("div");
    toast.className = `fg-action-toast fg-action-toast--${tone || "success"}`;
    toast.textContent = message;
    container.appendChild(toast);

    window.setTimeout(function () {
      toast.classList.add("is-leaving");
      window.setTimeout(function () {
        toast.remove();
      }, 260);
    }, 2400);
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
    element.dataset.loadingGuard = "false";
    loadingControls.add(element);
    window.setTimeout(function () {
      if (element.dataset.loadingActive === "true") {
        element.dataset.loadingGuard = "true";
      }
    }, 0);
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
    element.dataset.loadingGuard = "false";
    element.style.minWidth = "";
    loadingControls.delete(element);
  }

  function restoreAllLoadingControls() {
    Array.from(loadingControls).forEach(restoreLoadingState);
  }

  function actionPattern() {
    return /save|submit|add|update|edit|delete|remove|export|download|excel|pdf|approve|confirm|create|print|send|complete|check\s?in|check\s?out|start|log/i;
  }

  function controlText(element) {
    return (
      element.dataset.originalLabel ||
      element.getAttribute("value") ||
      element.textContent ||
      ""
    ).trim();
  }

  function valueLooksLikeDownload(value) {
    if (!value) {
      return false;
    }
    return /(^|\/)(export|download)(\/|$)|\.(xlsx?|csv|pdf)(\?|#|$)|receipt\/pdf|\/pdf\/?|format=(xlsx?|csv|pdf)|type=(xlsx?|csv|pdf)/i.test(value);
  }

  function textLooksLikeDownload(text) {
    return /export|download|excel|xlsx|xls|csv|pdf/i.test(text || "");
  }

  function isPrintControl(element) {
    return Boolean(element && (element.closest("[data-print]") || /print/i.test(controlText(element))));
  }

  function isDownloadControl(element) {
    if (!element) {
      return false;
    }
    if (element.hasAttribute("download")) {
      return true;
    }
    const href = element.getAttribute("href") || "";
    return textLooksLikeDownload(controlText(element)) || valueLooksLikeDownload(href);
  }

  function isDownloadForm(form, submitter) {
    if (!form) {
      return false;
    }
    const action = form.getAttribute("action") || window.location.pathname;
    const method = (form.getAttribute("method") || "get").toLowerCase();
    const submitText = submitter ? controlText(submitter) : "";
    return (
      form.dataset.download === "true" ||
      valueLooksLikeDownload(action) ||
      textLooksLikeDownload(submitText) ||
      (method === "get" && textLooksLikeDownload(form.textContent || ""))
    );
  }

  function scheduleActionReset(element, message) {
    window.setTimeout(function () {
      restoreLoadingState(element);
      resetLoadingUi();
      showActionToast(message, "success");
    }, quickActionResetMs);
  }

  function scheduleNavigationFallback() {
    window.clearTimeout(navigationFallbackTimer);
    navigationFallbackTimer = window.setTimeout(function () {
      if (document.visibilityState !== "hidden") {
        resetLoadingUi();
      }
    }, navigationFallbackMs);
  }

  function isActionControl(element) {
    if (!element) {
      return false;
    }
    if (element.closest("[data-loading-ignore='true']")) {
      return false;
    }
    if (element.hasAttribute("data-loading-text")) {
      return true;
    }

    if (element.tagName === "INPUT") {
      const type = (element.getAttribute("type") || "").toLowerCase();
      return type === "submit" || type === "button";
    }

    if (element.tagName === "BUTTON") {
      return true;
    }

    if (element.tagName === "A") {
      const href = element.getAttribute("href") || "";
      if (
        /export|download|excel|pdf|csv|print/i.test(controlText(element)) ||
        /export|download|xlsx|xls|csv|pdf|print/i.test(href)
      ) {
        return true;
      }
      return false;
    }

    return actionPattern().test(controlText(element));
  }

  function isPrimaryActionControl(element) {
    return isActionControl(element) && actionPattern().test(controlText(element));
  }

  function isValidSubmittableControl(element) {
    if (!element) {
      return false;
    }
    if (element.tagName === "INPUT") {
      return (element.getAttribute("type") || "").toLowerCase() === "submit";
    }
    if (element.tagName !== "BUTTON") {
      return false;
    }
    const type = (element.getAttribute("type") || "submit").toLowerCase();
    return type === "submit";
  }

  function shouldActivateForControl(control) {
    if (!control || control.dataset.loadingActive === "true") {
      return false;
    }
    if (control.closest("[data-loading-ignore='true']")) {
      return false;
    }
    if (isValidSubmittableControl(control)) {
      return false;
    }
    return isPrimaryActionControl(control) || (control.tagName === "A" && isActionControl(control));
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
    if (isDownloadControl(anchor)) {
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
    window.clearTimeout(finishTimer);
    finishTimer = window.setTimeout(function () {
      root.setAttribute("data-app-loading", "finishing");
      completeProgress();
      restoreAllLoadingControls();
      completeTimer = window.setTimeout(function () {
        root.setAttribute("data-app-loading", "false");
        root.removeAttribute("data-app-loading");
        clearSkeletonState();
      }, 250);
    }, delay);
  }

  function shouldResetForPageShow(event) {
    if (event && event.persisted) {
      return true;
    }
    if (
      window.performance &&
      typeof window.performance.getEntriesByType === "function"
    ) {
      const entries = window.performance.getEntriesByType("navigation");
      if (entries.length > 0 && entries[0].type === "back_forward") {
        return true;
      }
    }
    return false;
  }

  function bindFormLoading() {
    document.addEventListener(
      "submit",
      function (event) {
        const form = event.target.closest("form");
        if (!form || event.defaultPrevented || form.closest("[data-loading-ignore='true']")) {
          return;
        }

        if (form.dataset.confirm && form.dataset.confirmHandled !== "true") {
          form.dataset.confirmHandled = "true";
          window.setTimeout(function () {
            delete form.dataset.confirmHandled;
          }, 0);
          if (!window.confirm(form.dataset.confirm)) {
            event.preventDefault();
            return;
          }
        }

        const submitter = event.submitter || form.querySelector('button[type="submit"], input[type="submit"]');
        const downloadAction = isDownloadForm(form, submitter);
        if (submitter) {
          setLoadingState(submitter);
          window.setTimeout(function () {
            restoreLoadingState(submitter);
          }, actionResetMs);
        }
        if (downloadAction) {
          scheduleActionReset(submitter, "Download started.");
          return;
        }
        startLoadingState();
        scheduleNavigationFallback();
      },
      false
    );
  }

  function bindControlLoading() {
    document.addEventListener(
      "click",
      function (event) {
        const control = event.target.closest("button[type='button'], input[type='button']");
        if (!control || !shouldActivateForControl(control)) {
          return;
        }

        setLoadingState(control);
        if (isPrintControl(control)) {
          scheduleActionReset(control, "Print dialog opened.");
          return;
        }
        window.setTimeout(function () {
          restoreLoadingState(control);
        }, actionResetMs);
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

        if (isDownloadControl(anchor)) {
          setLoadingState(anchor);
          scheduleActionReset(anchor, "Download started.");
          return;
        }

        if (isActionControl(anchor)) {
          setLoadingState(anchor);
          window.setTimeout(function () {
            restoreLoadingState(anchor);
          }, actionResetMs);
        }

        if (shouldTrackNavigation(anchor, event)) {
          startLoadingState();
          scheduleNavigationFallback();
        }
      },
      true
    );
  }

  function bindButtonProtection() {
    document.addEventListener(
      "click",
      function (event) {
        const control = event.target.closest("button, input[type='submit'], input[type='button'], a[href]");
        if (!control) {
          return;
        }
        if (control.closest("[data-loading-ignore='true']")) {
          return;
        }
        if (control.dataset.loadingActive === "true" && control.dataset.loadingGuard === "true") {
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
    bindControlLoading();
    bindFormLoading();
    bindAnchorLoading();
    bindButtonProtection();

    if (document.readyState === "complete") {
      finishLoadingState();
    } else {
      window.addEventListener("load", finishLoadingState, { once: true });
    }

    window.addEventListener("pageshow", function (event) {
      if (shouldResetForPageShow(event)) {
        resetLoadingUi();
      }
    });
    window.addEventListener("pagehide", function () {
      window.clearTimeout(navigationFallbackTimer);
    });
    window.addEventListener("afterprint", function () {
      resetLoadingUi();
    });
    window.addEventListener("focus", function () {
      restoreAllLoadingControls();
      if (root.getAttribute("data-app-loading") === "true" && document.visibilityState !== "hidden") {
        finishLoadingState();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
