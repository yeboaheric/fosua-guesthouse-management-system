(function () {
  const root = document.documentElement;
  const themeStorageKey = "fg-theme";
  const sidebarStorageKey = "fg-sidebar-state";
  const pageHistoryStorageKey = "fg-page-history";
  const sidebarSubmenus = {
    Reservations: [
      { label: "All Reservations", url: "/bookings/" },
      { label: "New Reservation", url: "/bookings/new/" },
      { label: "Event Reservations", url: "/bookings/events/" },
      { label: "Operations Overview", url: "/bookings/operations/" }
    ],
    Rooms: [
      { label: "Rooms List", url: "/rooms/" },
      { label: "Add Room", url: "/rooms/new/" },
      { label: "Availability", url: "/rooms/availability/" }
    ],
    Payments: [
      { label: "Payments Center", url: "/dashboard/payments/" },
      { label: "Sales Deposits", url: "/dashboard/sales-deposits/" }
    ],
    Finance: [
      { label: "Finance Overview", url: "/dashboard/finance/" },
      { label: "Expenses", url: "/dashboard/finance/#expenses" },
      { label: "Profit & Loss", url: "/dashboard/finance/#profit-loss" },
      { label: "Balance Sheet", url: "/dashboard/finance/#balance-sheet" }
    ],
    Services: [
      { label: "Event Reservations", url: "/dashboard/services/" },
      { label: "Event Ledger", url: "/bookings/events/" },
      { label: "New Event", url: "/bookings/events/new/" }
    ],
    Housekeeping: [
      { label: "Add Item", url: "/rooms/housekeeping/?mode=item" },
      { label: "Add Log Entry", url: "/rooms/housekeeping/?mode=log" },
      { label: "Daily Report", url: "/rooms/housekeeping/?report=daily" },
      { label: "Monthly Report", url: "/rooms/housekeeping/?report=monthly" }
    ],
    "Shift Handovers": [
      { label: "Handovers", url: "/handovers/" },
      { label: "New Handover", url: "/handovers/new/" },
      { label: "Duty Roster", url: "/handovers/roster/" }
    ],
    Inventory: [
      { label: "Inventory Dashboard", url: "/inventory/" },
      { label: "Items", url: "/inventory/items/" },
      { label: "Categories", url: "/inventory/categories/" },
      { label: "Subcategories", url: "/inventory/subcategories/" },
      { label: "Suppliers", url: "/inventory/suppliers/" },
      { label: "Transactions", url: "/inventory/transactions/" },
      { label: "POS Sales", url: "/inventory/sales/" },
      { label: "Reports", url: "/inventory/reports/" }
    ],
    POS: [
      { label: "POS Terminal", url: "/inventory/pos/" },
      { label: "Sales History", url: "/inventory/sales/" },
      { label: "POS Reports", url: "/inventory/reports/" }
    ],
    "Staff Management": [
      { label: "Employees", url: "/dashboard/admin/hr/" },
      { label: "Add Employee", url: "/dashboard/admin/hr/new/" },
      { label: "Duty Roster", url: "/dashboard/admin/hr/rotas/" }
    ],
    Reports: [
      { label: "Daily", url: "/dashboard/admin/reports/?period=daily" },
      { label: "Weekly", url: "/dashboard/admin/reports/?period=weekly" },
      { label: "Monthly", url: "/dashboard/admin/reports/?period=monthly" },
      { label: "Yearly", url: "/dashboard/admin/reports/?period=yearly" }
    ],
    Analytics: [
      { label: "Daily", url: "/dashboard/analytics/?period=daily" },
      { label: "Weekly", url: "/dashboard/analytics/?period=weekly" },
      { label: "Monthly", url: "/dashboard/analytics/?period=monthly" },
      { label: "Yearly", url: "/dashboard/analytics/?period=yearly" }
    ]
  };

  const pageNameRules = [
    [/^\/$/, "Dashboard"],
    [/^\/dashboard\/?$/, "Dashboard"],
    [/^\/dashboard\/admin\/?$/, "Dashboard"],
    [/^\/dashboard\/reception\/?$/, "Dashboard"],
    [/^\/dashboard\/admin\/activity-feed\/?$/, "Activity Feed"],
    [/^\/dashboard\/admin\/reports\/?$/, "Reports"],
    [/^\/dashboard\/search\/?$/, "Search Results"],
    [/^\/dashboard\/payments\/?$/, "Payments"],
    [/^\/dashboard\/finance\/expenses\/\d+\/edit\/?$/, "Edit Expense"],
    [/^\/dashboard\/finance\/?$/, "Finance"],
    [/^\/dashboard\/owner-withdrawals\/?$/, "Owner Withdrawals"],
    [/^\/dashboard\/sales-deposits\/\d+\/edit\/?$/, "Edit Sales Deposit"],
    [/^\/dashboard\/sales-deposits\/?$/, "Sales Deposits"],
    [/^\/dashboard\/services\/?$/, "Event Reservations"],
    [/^\/dashboard\/housekeeping\/?$/, "Housekeeping"],
    [/^\/dashboard\/notifications\/?$/, "Notifications"],
    [/^\/dashboard\/analytics\/?$/, "Analytics"],
    [/^\/dashboard\/settings\/?$/, "Settings"],
    [/^\/dashboard\/users-roles\/?$/, "Users & Roles"],
    [/^\/dashboard\/admin\/hr\/new\/?$/, "Add Employee"],
    [/^\/dashboard\/admin\/hr\/rotas\/new\/?$/, "New Duty Roster"],
    [/^\/dashboard\/admin\/hr\/rotas\/\d+\/edit\/?$/, "Edit Duty Roster"],
    [/^\/dashboard\/admin\/hr\/rotas\/\d+\/?$/, "Duty Roster Detail"],
    [/^\/dashboard\/admin\/hr\/rotas\/?$/, "Duty Roster"],
    [/^\/dashboard\/admin\/hr\/\d+\/edit\/?$/, "Edit Employee"],
    [/^\/dashboard\/admin\/hr\/\d+\/delete\/?$/, "Delete Employee"],
    [/^\/dashboard\/admin\/hr\/\d+\/annual-leave\/?$/, "Annual Leave"],
    [/^\/dashboard\/admin\/hr\/\d+\/attendance-history\/?$/, "Attendance History"],
    [/^\/dashboard\/admin\/hr\/\d+\/documents\/?$/, "Employee Documents"],
    [/^\/dashboard\/admin\/hr\/\d+\/training\/?$/, "Staff Training"],
    [/^\/dashboard\/admin\/hr\/\d+\/payroll\/?$/, "Payroll"],
    [/^\/dashboard\/admin\/hr\/\d+\/[^/]+\/?$/, "Employee Profile"],
    [/^\/dashboard\/admin\/hr\/\d+\/?$/, "Employee Profile"],
    [/^\/dashboard\/admin\/hr\/?$/, "Staff Management"],
    [/^\/bookings\/operations\/?$/, "Operations Overview"],
    [/^\/bookings\/events\/new\/?$/, "New Event Reservation"],
    [/^\/bookings\/events\/\d+\/edit\/?$/, "Edit Event Reservation"],
    [/^\/bookings\/events\/\d+\/payments\/?$/, "Event Payments"],
    [/^\/bookings\/events\/?$/, "Event Reservations"],
    [/^\/bookings\/payments\/room\/\d+\/edit\/?$/, "Edit Booking Payment"],
    [/^\/bookings\/payments\/event\/\d+\/edit\/?$/, "Edit Event Payment"],
    [/^\/bookings\/new\/?$/, "New Reservation"],
    [/^\/bookings\/\d+\/view\/?$/, "Reservation Details"],
    [/^\/bookings\/\d+\/edit\/?$/, "Edit Reservation"],
    [/^\/bookings\/\d+\/payments\/?$/, "Reservation Payments"],
    [/^\/bookings\/?$/, "Reservations"],
    [/^\/rooms\/new\/?$/, "Add Room"],
    [/^\/rooms\/\d+\/edit\/?$/, "Edit Room"],
    [/^\/rooms\/availability\/?$/, "Room Availability"],
    [/^\/rooms\/housekeeping\/logs\/\d+\/edit\/?$/, "Edit Housekeeping Log"],
    [/^\/rooms\/housekeeping\/?$/, "Housekeeping"],
    [/^\/rooms\/?$/, "Rooms"],
    [/^\/guests\/new\/?$/, "Add Guest"],
    [/^\/guests\/\d+\/edit\/?$/, "Edit Guest"],
    [/^\/guests\/?$/, "Guests"],
    [/^\/handovers\/new\/?$/, "New Handover"],
    [/^\/handovers\/roster\/export\/excel\/?$/, "Duty Roster Export"],
    [/^\/handovers\/roster\/\d+\/?$/, "Duty Roster Detail"],
    [/^\/handovers\/roster\/?$/, "Duty Roster"],
    [/^\/handovers\/\d+\/?$/, "Handover Detail"],
    [/^\/handovers\/?$/, "Shift Handovers"],
    [/^\/inventory\/categories\/\d+\/edit\/?$/, "Edit Inventory Category"],
    [/^\/inventory\/categories\/?$/, "Inventory Categories"],
    [/^\/inventory\/subcategories\/\d+\/edit\/?$/, "Edit Inventory Subcategory"],
    [/^\/inventory\/subcategories\/?$/, "Inventory Subcategories"],
    [/^\/inventory\/suppliers\/\d+\/edit\/?$/, "Edit Supplier"],
    [/^\/inventory\/suppliers\/?$/, "Suppliers"],
    [/^\/inventory\/items\/new\/?$/, "Add Inventory Item"],
    [/^\/inventory\/items\/\d+\/edit\/?$/, "Edit Inventory Item"],
    [/^\/inventory\/items\/\d+\/adjust\/?$/, "Adjust Stock"],
    [/^\/inventory\/items\/?$/, "Inventory Items"],
    [/^\/inventory\/transactions\/?$/, "Inventory Transactions"],
    [/^\/inventory\/pos\/checkout\/?$/, "POS Checkout"],
    [/^\/inventory\/pos\/?$/, "POS"],
    [/^\/inventory\/sales\/\d+\/edit\/?$/, "Edit POS Sale"],
    [/^\/inventory\/sales\/\d+\/?$/, "POS Sale Receipt"],
    [/^\/inventory\/sales\/?$/, "POS Sales"],
    [/^\/inventory\/reports\/?$/, "Inventory Reports"],
    [/^\/inventory\/?$/, "Inventory"],
    [/^\/receipts\/booking\/\d+\/?$/, "Booking Receipt"],
    [/^\/password-change\/?$/, "Change Password"],
    [/^\/password-reset\/?$/, "Password Reset"],
    [/^\/login\/?$/, "Login"],
    [/^\/admin\/?$/, "Django Admin"]
  ];

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

  function sidebarLinkLabel(link) {
    const label = link.querySelector("span");
    return (label ? label.textContent : link.textContent).trim();
  }

  function sidebarItemMatchesCurrent(item) {
    try {
      const target = new URL(item.url, window.location.origin);
      if (target.pathname !== window.location.pathname) {
        return false;
      }
      for (const key of target.searchParams.keys()) {
        if (window.location.search) {
          const currentParams = new URLSearchParams(window.location.search);
          if (currentParams.get(key) !== target.searchParams.get(key)) {
            return false;
          }
        } else if (target.searchParams.get(key)) {
          return false;
        }
      }
      return true;
    } catch (error) {
      return false;
    }
  }

  function bindSidebarDropdowns() {
    document.querySelectorAll(".sidebar-nav").forEach(function (nav) {
      if (nav.dataset.dropdownsEnhanced === "true") {
        return;
      }
      nav.dataset.dropdownsEnhanced = "true";

      Array.from(nav.children).forEach(function (child) {
        if (!child.matches || !child.matches("a.sidebar-link")) {
          return;
        }

        const label = sidebarLinkLabel(child);
        const children = sidebarSubmenus[label];
        if (!children || !children.length) {
          return;
        }

        const group = document.createElement("div");
        group.className = "sidebar-nav-group";
        const childIsActive = children.some(sidebarItemMatchesCurrent);
        if (child.classList.contains("active") || childIsActive) {
          group.classList.add("active", "is-open");
        }

        const parent = document.createElement("div");
        parent.className = "sidebar-nav-parent";

        const toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "sidebar-submenu-toggle";
        toggle.setAttribute("aria-label", `Toggle ${label} submenu`);
        toggle.setAttribute("aria-expanded", group.classList.contains("is-open") ? "true" : "false");
        toggle.innerHTML = "<span aria-hidden=\"true\">›</span>";

        const submenu = document.createElement("div");
        submenu.className = "sidebar-submenu";

        children.forEach(function (item) {
          const link = document.createElement("a");
          link.className = "sidebar-submenu-link";
          link.href = item.url;
          link.textContent = item.label;
          if (sidebarItemMatchesCurrent(item)) {
            link.classList.add("active");
          }
          submenu.appendChild(link);
        });

        child.insertAdjacentElement("beforebegin", group);
        parent.appendChild(child);
        parent.appendChild(toggle);
        group.appendChild(parent);
        group.appendChild(submenu);

        toggle.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          const isOpen = group.classList.toggle("is-open");
          toggle.setAttribute("aria-expanded", String(isOpen));
        });
      });
    });

    document.addEventListener("click", function (event) {
      if (event.target.closest(".sidebar-nav-group")) {
        return;
      }
      document.querySelectorAll(".sidebar-nav-group.is-open:not(.active)").forEach(function (group) {
        group.classList.remove("is-open");
        const toggle = group.querySelector(".sidebar-submenu-toggle");
        if (toggle) {
          toggle.setAttribute("aria-expanded", "false");
        }
      });
    });
  }

  function normalizeHistoryUrl(url) {
    try {
      const parsed = new URL(url, window.location.origin);
      if (parsed.origin !== window.location.origin) {
        return null;
      }
      return `${parsed.pathname}${parsed.search}`;
    } catch (error) {
      return null;
    }
  }

  function currentHistoryUrl() {
    return `${window.location.pathname}${window.location.search}`;
  }

  function readablePageName(pathname) {
    const cleanPath = pathname || "/";
    for (const rule of pageNameRules) {
      if (rule[0].test(cleanPath)) {
        return rule[1];
      }
    }

    const visibleTitle = document.querySelector(".module-title, .page-title, h1");
    if (visibleTitle && visibleTitle.textContent.trim()) {
      return visibleTitle.textContent.trim();
    }

    const parts = cleanPath.split("/").filter(Boolean);
    const lastPart = parts[parts.length - 1] || "Dashboard";
    return lastPart
      .replace(/[-_]+/g, " ")
      .replace(/\b\w/g, function (letter) {
        return letter.toUpperCase();
      });
  }

  function loadPageHistory() {
    try {
      const navigationEntry = performance.getEntriesByType("navigation")[0];
      if (navigationEntry && navigationEntry.type === "reload") {
        sessionStorage.removeItem(pageHistoryStorageKey);
      }
      const stored = JSON.parse(sessionStorage.getItem(pageHistoryStorageKey) || "null");
      if (!stored || !Array.isArray(stored.entries)) {
        return { entries: [], index: -1 };
      }
      const entries = stored.entries
        .filter(function (entry) {
          return entry && typeof entry.url === "string";
        })
        .slice(-60);
      let index = Number(stored.index);
      if (!Number.isFinite(index)) {
        index = entries.length - 1;
      }
      index = Math.min(Math.max(index, entries.length ? 0 : -1), entries.length - 1);
      return { entries: entries, index: index };
    } catch (error) {
      return { entries: [], index: -1 };
    }
  }

  function savePageHistory(state) {
    sessionStorage.setItem(pageHistoryStorageKey, JSON.stringify(state));
  }

  function bindPageHistoryNavigation() {
    const nav = document.getElementById("fgPathBar");
    const trail = document.getElementById("fgPathTrail");
    if (!nav || !trail) {
      return;
    }

    const currentUrl = currentHistoryUrl();
    const currentName = readablePageName(window.location.pathname);
    let state = loadPageHistory();
    const currentEntry = state.entries[state.index];

    if (!currentEntry || currentEntry.url !== currentUrl) {
      state.entries = state.entries.slice(0, state.index + 1);
      state.entries.push({ url: currentUrl, name: currentName });
      state.entries = state.entries.slice(-60);
      state.index = state.entries.length - 1;
    } else if (currentEntry.name !== currentName) {
      currentEntry.name = currentName;
    }

    savePageHistory(state);

    function render() {
      trail.replaceChildren();
      const entries = state.entries.slice(0, state.index + 1);
      if (!entries.length) {
        nav.hidden = true;
        return;
      }

      nav.hidden = false;
      entries.forEach(function (entry, index) {
        const item = document.createElement("li");
        item.className = "app-pathbar-item";

        if (index === entries.length - 1) {
          const current = document.createElement("span");
          current.className = "app-pathbar-current";
          current.setAttribute("aria-current", "page");
          current.textContent = entry.name || currentName;
          item.appendChild(current);
        } else {
          const link = document.createElement("a");
          link.className = "app-pathbar-link";
          link.href = normalizeHistoryUrl(entry.url) || "#";
          link.dataset.pathIndex = String(index);
          link.textContent = entry.name || "Page";
          item.appendChild(link);
        }

        trail.appendChild(item);
      });

      requestAnimationFrame(function () {
        nav.scrollLeft = nav.scrollWidth;
      });
    }

    function trimAndGoToIndex(nextIndex) {
      if (nextIndex < 0 || nextIndex >= state.entries.length || nextIndex === state.index) {
        return;
      }
      const targetUrl = normalizeHistoryUrl(state.entries[nextIndex].url);
      if (!targetUrl) {
        return;
      }
      state.index = nextIndex;
      state.entries = state.entries.slice(0, nextIndex + 1);
      savePageHistory(state);
      window.location.href = targetUrl;
    }

    trail.addEventListener("click", function (event) {
      const link = event.target.closest(".app-pathbar-link");
      if (!link) {
        return;
      }
      event.preventDefault();
      trimAndGoToIndex(Number(link.dataset.pathIndex));
    });

    render();
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
    bindSidebarDropdowns();
    bindPageHistoryNavigation();
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
