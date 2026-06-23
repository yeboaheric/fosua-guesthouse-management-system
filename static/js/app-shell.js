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

  function boot() {
    bindThemeToggle();
    bindSidebarToggle();

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
