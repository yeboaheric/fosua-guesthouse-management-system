(function () {
  const root = document.documentElement;
  const themeStorageKey = "fg-theme";
  const sidebarStorageKey = "fg-sidebar-state";

  function applyTheme(theme) {
    if (!theme) {
      return;
    }
    root.setAttribute("data-theme", theme);
    localStorage.setItem(themeStorageKey, theme);
    window.dispatchEvent(new CustomEvent("fg:themechange", { detail: { theme } }));
  }

  function currentSidebarState() {
    return root.getAttribute("data-sidebar-state") || localStorage.getItem(sidebarStorageKey) || "expanded";
  }

  function applySidebarState(state) {
    const normalized = state === "collapsed" ? "collapsed" : "expanded";
    root.setAttribute("data-sidebar-state", normalized);
    localStorage.setItem(sidebarStorageKey, normalized);

    const toggle = document.getElementById("sidebarToggle");
    if (toggle) {
      const expanded = normalized !== "collapsed";
      toggle.setAttribute("aria-expanded", String(expanded));
      toggle.setAttribute("aria-label", expanded ? "Collapse navigation" : "Expand navigation");
    }
  }

  function bindThemeToggle() {
    const toggle = document.getElementById("themeToggle");
    if (!toggle) {
      return;
    }
    toggle.addEventListener("click", function () {
      const nextTheme = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
    });
  }

  function bindSidebarToggle() {
    const toggle = document.getElementById("sidebarToggle");
    if (!toggle) {
      return;
    }

    applySidebarState(currentSidebarState());
    toggle.addEventListener("click", function () {
      const nextState = currentSidebarState() === "collapsed" ? "expanded" : "collapsed";
      applySidebarState(nextState);
    });
  }

  function directChildrenMatching(container, selector) {
    return Array.from(container.children || []).filter(function (child) {
      return child.matches(selector);
    });
  }

  function hasNearbyPagination(element) {
    const section = element.closest(".module-card, .dashboard-panel, .card, section, article");
    return Boolean(section && section.querySelector(".pagination, .page-link, [data-pagination]"));
  }

  function collapsedHeightFor(target, items, visibleCount) {
    const firstHidden = items[visibleCount];
    if (!firstHidden) {
      return target.scrollHeight;
    }

    const targetTop = target.getBoundingClientRect().top;
    const hiddenTop = firstHidden.getBoundingClientRect().top;
    const measured = Math.ceil(hiddenTop - targetTop);
    return measured > 80 ? measured : Math.min(target.scrollHeight, 520);
  }

  function enhanceShowMoreTarget(target, items, options) {
    if (!target || target.dataset.showMoreBound === "true" || target.dataset.showMore === "off") {
      return;
    }

    const visibleCount = Number(target.dataset.showMoreCount || options.visibleCount || 10);
    if (!items || items.length <= visibleCount || hasNearbyPagination(target)) {
      return;
    }

    target.dataset.showMoreBound = "true";
    target.classList.add("fg-show-more-target", "is-collapsed");

    const toggleWrap = document.createElement("div");
    toggleWrap.className = "fg-show-more-toggle-wrap";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "btn btn-outline-primary fg-show-more-toggle";
    button.setAttribute("aria-expanded", "false");
    button.textContent = "Show More";

    toggleWrap.appendChild(button);
    target.insertAdjacentElement("afterend", toggleWrap);

    function applyState(expanded) {
      const collapsedHeight = collapsedHeightFor(target, items, visibleCount);
      target.classList.toggle("is-expanded", expanded);
      target.classList.toggle("is-collapsed", !expanded);
      target.style.maxHeight = expanded ? `${target.scrollHeight}px` : `${collapsedHeight}px`;
      button.textContent = expanded ? "Show Less" : "Show More";
      button.setAttribute("aria-expanded", String(expanded));
    }

    button.addEventListener("click", function () {
      applyState(!target.classList.contains("is-expanded"));
    });

    window.addEventListener("resize", function () {
      applyState(target.classList.contains("is-expanded"));
    });

    requestAnimationFrame(function () {
      applyState(false);
    });
  }

  function bindShowMoreLists() {
    const content = document.getElementById("fgPageContent") || document;

    content.querySelectorAll(".table-responsive").forEach(function (wrapper) {
      const rows = Array.from(wrapper.querySelectorAll("table tbody tr")).filter(function (row) {
        return !row.querySelector("[colspan]");
      });
      enhanceShowMoreTarget(wrapper, rows, {
        visibleCount: wrapper.classList.contains("dashboard-list-table") ? 5 : 10
      });
    });

    content.querySelectorAll(".dashboard-live-feed, .dashboard-activity-list, .timeline-list").forEach(function (list) {
      const items = directChildrenMatching(list, ".dashboard-feed-item, .dashboard-activity-item, .timeline-item");
      enhanceShowMoreTarget(list, items, { visibleCount: 5 });
    });

    content.querySelectorAll(".module-card-body").forEach(function (body) {
      const cards = directChildrenMatching(body, ".result-card");
      enhanceShowMoreTarget(body, cards, { visibleCount: 5 });
    });

    content.querySelectorAll(".list-group").forEach(function (list) {
      const items = directChildrenMatching(list, ".list-group-item");
      enhanceShowMoreTarget(list, items, { visibleCount: 10 });
    });
  }

  function boot() {
    bindThemeToggle();
    bindSidebarToggle();
    bindShowMoreLists();

    if (window.lucide) {
      window.lucide.createIcons();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
