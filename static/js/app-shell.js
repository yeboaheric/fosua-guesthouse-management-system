(function () {
  const root = document.documentElement;
  const themeStorageKey = "fg-theme";
  const sidebarStorageKey = "fg-sidebar-state";
  const pageHistoryStorageKey = "fg-page-history";
  const sidebarSubmenus = {
    Reservations: [
      { label: "All Reservations", url: "/bookings/", icon: "calendar-range" },
      { label: "New Reservation", url: "/bookings/new/", icon: "calendar-plus" },
      { label: "Event Reservations", url: "/bookings/events/", icon: "party-popper" },
      { label: "Operations Overview", url: "/bookings/operations/", icon: "activity" }
    ],
    Rooms: [
      { label: "Rooms List", url: "/rooms/", icon: "bed-double" },
      { label: "Add Room", url: "/rooms/new/", icon: "plus-circle" },
      { label: "Availability", url: "/rooms/availability/", icon: "door-open" }
    ],
    Payments: [],
    Finance: [
      { label: "Finance Overview", url: "/dashboard/finance/", icon: "badge-dollar-sign" },
      { label: "Expenses", url: "/dashboard/finance/#expenses", icon: "receipt-text" },
      { label: "Profit & Loss", url: "/dashboard/finance/#profit-loss", icon: "trending-up" },
      { label: "Balance Sheet", url: "/dashboard/finance/#balance-sheet", icon: "scale" }
    ],
    Services: [
      { label: "Event Reservations", url: "/dashboard/services/", icon: "concierge-bell" },
      { label: "Event Ledger", url: "/bookings/events/", icon: "list-checks" },
      { label: "New Event", url: "/bookings/events/new/", icon: "calendar-plus" }
    ],
    Housekeeping: [
      { label: "Add Item", url: "/rooms/housekeeping/?mode=item", icon: "plus-circle" },
      { label: "Add Log Entry", url: "/rooms/housekeeping/?mode=log", icon: "clipboard-pen" },
      { label: "Daily Report", url: "/rooms/housekeeping/?report=daily", icon: "calendar-days" },
      { label: "Monthly Report", url: "/rooms/housekeeping/?report=monthly", icon: "calendar" }
    ],
    "Shift Handovers": [
      { label: "Handovers", url: "/handovers/", icon: "clipboard-list" },
      { label: "New Handover", url: "/handovers/new/", icon: "clipboard-plus" },
      { label: "Duty Roster", url: "/handovers/roster/", icon: "calendar-clock" }
    ],
    Inventory: [
      { label: "Inventory Dashboard", url: "/inventory/", icon: "layout-dashboard" },
      { label: "Items", url: "/inventory/items/", icon: "package" },
      { label: "Categories", url: "/inventory/categories/", icon: "folder" },
      { label: "Subcategories", url: "/inventory/subcategories/", icon: "folder-tree" },
      { label: "Suppliers", url: "/inventory/suppliers/", icon: "truck" },
      { label: "Transactions", url: "/inventory/transactions/", icon: "repeat-2" },
      { label: "POS Sales", url: "/inventory/sales/", icon: "shopping-cart" },
      { label: "Reports", url: "/inventory/reports/", icon: "bar-chart-3" }
    ],
    POS: [
      { label: "POS Terminal", url: "/inventory/pos/", icon: "receipt" },
      { label: "Sales History", url: "/inventory/sales/", icon: "history" },
      { label: "POS Reports", url: "/inventory/reports/", icon: "bar-chart-3" }
    ],
    "Staff Management": [
      { label: "Employees", url: "/dashboard/admin/hr/", icon: "users" },
      { label: "Add Employee", url: "/dashboard/admin/hr/new/", icon: "user-plus" },
      { label: "Duty Roster", url: "/dashboard/admin/hr/rotas/", icon: "calendar-clock" }
    ],
    Reports: [
      { label: "Daily", url: "/dashboard/admin/reports/?period=daily", icon: "calendar-days" },
      { label: "Weekly", url: "/dashboard/admin/reports/?period=weekly", icon: "calendar-range" },
      { label: "Monthly", url: "/dashboard/admin/reports/?period=monthly", icon: "calendar" },
      { label: "Yearly", url: "/dashboard/admin/reports/?period=yearly", icon: "calendar-clock" }
    ],
    Analytics: [
      { label: "Daily", url: "/dashboard/analytics/?period=daily", icon: "line-chart" },
      { label: "Weekly", url: "/dashboard/analytics/?period=weekly", icon: "bar-chart-3" },
      { label: "Monthly", url: "/dashboard/analytics/?period=monthly", icon: "pie-chart" },
      { label: "Yearly", url: "/dashboard/analytics/?period=yearly", icon: "chart-column" }
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
      if (target.hash && target.hash !== window.location.hash) {
        return false;
      }
      if (!target.hash && window.location.hash) {
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

  function sidebarItemPathMatchesCurrent(item) {
    try {
      const target = new URL(item.url, window.location.origin);
      if (target.pathname === window.location.pathname) {
        return true;
      }
      const targetPath = target.pathname.endsWith("/") ? target.pathname : `${target.pathname}/`;
      return window.location.pathname.startsWith(targetPath) && targetPath !== "/";
    } catch (error) {
      return false;
    }
  }

  function bestSidebarItemMatch(items) {
    const exact = items.find(sidebarItemMatchesCurrent);
    if (exact) {
      return exact;
    }

    return items
      .filter(sidebarItemPathMatchesCurrent)
      .sort(function (first, second) {
        return new URL(second.url, window.location.origin).pathname.length - new URL(first.url, window.location.origin).pathname.length;
      })[0];
  }

  function moduleLabelForPath(pathname) {
    const path = pathname || window.location.pathname;
    if (/^\/rooms\/housekeeping\/?/.test(path)) return "Housekeeping";
    if (/^\/inventory\/pos\/?/.test(path)) return "POS";
    if (/^\/inventory\/sales\/?/.test(path)) return "POS";
    if (/^\/inventory\/(items|categories|subcategories|suppliers|transactions|reports)\/?/.test(path) || path === "/inventory/") return "Inventory";
    if (/^\/dashboard\/services\/?/.test(path) || /^\/bookings\/events\/?/.test(path)) return "Services";
    if (/^\/dashboard\/admin\/reports\/?/.test(path)) return "Reports";
    if (/^\/dashboard\/analytics\/?/.test(path)) return "Analytics";
    if (/^\/dashboard\/finance\/?/.test(path)) return "Finance";
    if (/^\/dashboard\/admin\/hr\/?/.test(path)) return "Staff Management";
    if (/^\/handovers\/?/.test(path)) return "Shift Handovers";
    if (/^\/rooms\/?/.test(path)) return "Rooms";
    if (/^\/bookings\/?/.test(path) && !/^\/bookings\/operations\/?/.test(path)) return "Reservations";
    return null;
  }

  function moduleRootUrl(label) {
    const roots = {
      Reservations: "/bookings/",
      Rooms: "/rooms/",
      Finance: "/dashboard/finance/",
      Services: "/dashboard/services/",
      Housekeeping: "/rooms/housekeeping/",
      "Shift Handovers": "/handovers/",
      Inventory: "/inventory/",
      POS: "/inventory/pos/",
      "Staff Management": "/dashboard/admin/hr/",
      Reports: "/dashboard/admin/reports/",
      Analytics: "/dashboard/analytics/"
    };
    return roots[label] || null;
  }

  function bindSidebarDropdowns() {
    function setGroupOpen(group, open) {
      group.classList.toggle("is-open", open);
      const toggle = group.querySelector(".sidebar-submenu-toggle");
      if (toggle) {
        toggle.setAttribute("aria-expanded", String(open));
      }
    }

    function closeSiblingGroups(group) {
      const nav = group.closest(".sidebar-nav");
      if (!nav) {
        return;
      }
      nav.querySelectorAll(".sidebar-nav-group.is-open").forEach(function (sibling) {
        if (sibling !== group) {
          setGroupOpen(sibling, false);
        }
      });
    }

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
        const activeChild = bestSidebarItemMatch(children);
        const childIsActive = Boolean(activeChild);
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
          if (item.icon) {
            const icon = document.createElement("i");
            icon.setAttribute("data-lucide", item.icon);
            icon.setAttribute("aria-hidden", "true");
            link.appendChild(icon);
          }
          const text = document.createElement("span");
          text.textContent = item.label;
          link.appendChild(text);
          if (activeChild && activeChild.url === item.url) {
            link.classList.add("active");
          }
          submenu.appendChild(link);
        });

        child.insertAdjacentElement("beforebegin", group);
        parent.appendChild(child);
        parent.appendChild(toggle);
        group.appendChild(parent);
        group.appendChild(submenu);

        group.addEventListener("mouseenter", function () {
          closeSiblingGroups(group);
          setGroupOpen(group, true);
        });

        group.addEventListener("mouseleave", function () {
          if (!group.classList.contains("active")) {
            setGroupOpen(group, false);
          }
        });

        toggle.addEventListener("click", function (event) {
          event.preventDefault();
          event.stopPropagation();
          const shouldOpen = !group.classList.contains("is-open");
          if (shouldOpen) {
            closeSiblingGroups(group);
          }
          setGroupOpen(group, shouldOpen);
        });
      });
    });

    document.addEventListener("click", function (event) {
      if (event.target.closest(".sidebar-nav-group")) {
        return;
      }
      document.querySelectorAll(".sidebar-nav-group.is-open:not(.active)").forEach(function (group) {
        setGroupOpen(group, false);
      });
    });
  }

  function activeModuleGroup() {
    const desktopGroups = Array.from(document.querySelectorAll(".app-sidebar .sidebar-nav-group"));
    const preferredLabel = moduleLabelForPath(window.location.pathname);
    if (preferredLabel) {
      const preferredGroup = desktopGroups.find(function (group) {
        return sidebarLinkLabel(group.querySelector(".sidebar-link")) === preferredLabel;
      });
      if (preferredGroup) {
        return preferredGroup;
      }
    }

    const matchingGroups = desktopGroups
      .map(function (group) {
        const label = sidebarLinkLabel(group.querySelector(".sidebar-link"));
        const children = sidebarSubmenus[label] || [];
        const activeChild = bestSidebarItemMatch(children);
        return { group, activeChild };
      })
      .filter(function (match) {
        return Boolean(match.activeChild);
      })
      .sort(function (first, second) {
        const firstPath = new URL(first.activeChild.url, window.location.origin).pathname;
        const secondPath = new URL(second.activeChild.url, window.location.origin).pathname;
        return secondPath.length - firstPath.length;
      });

    if (matchingGroups.length) {
      return matchingGroups[0].group;
    }

    return desktopGroups.find(function (group) {
      return group.classList.contains("active");
    });
  }

  function parsedNavigationTarget(url) {
    try {
      const parsed = new URL(url, window.location.href);
      if (parsed.origin !== window.location.origin) {
        return null;
      }
      return parsed;
    } catch (error) {
      return null;
    }
  }

  function actionMatchesModuleItem(actionUrl, itemUrl) {
    const actionTarget = parsedNavigationTarget(actionUrl);
    const itemTarget = parsedNavigationTarget(itemUrl);
    if (!actionTarget || !itemTarget || actionTarget.pathname !== itemTarget.pathname) {
      return false;
    }

    if (itemTarget.hash && actionTarget.hash !== itemTarget.hash) {
      return false;
    }

    if (actionTarget.searchParams.has("mode") && !itemTarget.searchParams.has("mode")) {
      return false;
    }

    for (const entry of itemTarget.searchParams.entries()) {
      const [key, value] = entry;
      if (actionTarget.searchParams.get(key) !== value) {
        return false;
      }
    }

    return true;
  }

  function existingModuleAction(actionRow, item) {
    return Array.from(actionRow.querySelectorAll("a[href]")).find(function (link) {
      return actionMatchesModuleItem(link.getAttribute("href"), item.url);
    });
  }

  function bindModuleTabs() {
    const content = document.getElementById("fgPageContent");
    if (!content || content.dataset.moduleTabsEnhanced === "true") {
      return;
    }

    const group = activeModuleGroup();
    if (!group) {
      return;
    }

    const label = sidebarLinkLabel(group.querySelector(".sidebar-link"));
    const children = sidebarSubmenus[label];
    if (!children || !children.length) {
      return;
    }
    const activeChild = bestSidebarItemMatch(children);

    const hero = content.querySelector(".module-hero");
    if (!hero) {
      return;
    }

    content.dataset.moduleTabsEnhanced = "true";
    let actionRow = hero.querySelector(".module-action-row");
    if (!actionRow) {
      actionRow = document.createElement("div");
      actionRow.className = "module-action-row";
      hero.appendChild(actionRow);
    }

    const nav = document.createElement("nav");
    nav.className = "module-page-tabs module-page-tabs--actions";
    nav.setAttribute("aria-label", `${label} section navigation`);

    children.forEach(function (item) {
      const existingAction = existingModuleAction(actionRow, item);
      if (existingAction) {
        if (activeChild && activeChild.url === item.url) {
          existingAction.classList.add("module-linked-action-active");
          existingAction.setAttribute("aria-current", "page");
        }
        return;
      }

      const link = document.createElement("a");
      link.className = "module-page-tab";
      link.href = item.url;
      if (item.icon) {
        const icon = document.createElement("i");
        icon.setAttribute("data-lucide", item.icon);
        icon.setAttribute("aria-hidden", "true");
        link.appendChild(icon);
      }
      const text = document.createElement("span");
      text.textContent = item.label;
      link.appendChild(text);
      if (activeChild && activeChild.url === item.url) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
      nav.appendChild(link);
    });

    if (nav.children.length) {
      actionRow.appendChild(nav);
    }
  }

  function normalizeHistoryUrl(url) {
    try {
      const parsed = new URL(url, window.location.origin);
      if (parsed.origin !== window.location.origin) {
        return null;
      }
      return `${parsed.pathname}${parsed.search}${parsed.hash}`;
    } catch (error) {
      return null;
    }
  }

  function currentHistoryUrl() {
    return `${window.location.pathname}${window.location.search}${window.location.hash}`;
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
        return { entries: [], index: -1, scopeKey: null };
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
      return { entries: entries, index: index, scopeKey: typeof stored.scopeKey === "string" ? stored.scopeKey : null };
    } catch (error) {
      return { entries: [], index: -1, scopeKey: null };
    }
  }

  function savePageHistory(state) {
    sessionStorage.setItem(pageHistoryStorageKey, JSON.stringify(state));
  }

  function equivalentTrailUrl(firstUrl, secondUrl) {
    return normalizeHistoryUrl(firstUrl) === normalizeHistoryUrl(secondUrl);
  }

  function scopedPathItemName(url, scope, fallbackName) {
    const normalizedUrl = normalizeHistoryUrl(url);
    if (scope && equivalentTrailUrl(normalizedUrl, scope.rootUrl)) {
      return scope.name;
    }

    const children = scope ? sidebarSubmenus[scope.name] || [] : [];
    const matchingChild = children.find(function (item) {
      return actionMatchesModuleItem(normalizedUrl, item.url);
    });
    if (matchingChild) {
      return matchingChild.label;
    }

    try {
      return readablePageName(new URL(url, window.location.origin).pathname);
    } catch (error) {
      return fallbackName || "Page";
    }
  }

  function currentPathScope(currentUrl, currentName) {
    const label = moduleLabelForPath(window.location.pathname);
    const rootUrl = label ? moduleRootUrl(label) : null;
    if (label && rootUrl) {
      return {
        key: label,
        name: label,
        rootUrl: rootUrl,
        standalone: false
      };
    }

    return {
      key: currentUrl,
      name: currentName,
      rootUrl: currentUrl,
      standalone: true
    };
  }

  function bindPageHistoryNavigation() {
    const nav = document.getElementById("fgPathBar");
    const trail = document.getElementById("fgPathTrail");
    if (!nav || !trail) {
      return;
    }

    const currentUrl = currentHistoryUrl();
    const currentName = readablePageName(window.location.pathname);
    const currentScope = currentPathScope(currentUrl, currentName);
    const currentEntryName = scopedPathItemName(currentUrl, currentScope, currentName);
    let state = loadPageHistory();

    if (state.scopeKey !== currentScope.key) {
      state = { entries: [], index: -1, scopeKey: currentScope.key };
    }

    if (!currentScope.standalone && !state.entries.length) {
      state.entries.push({
        url: currentScope.rootUrl,
        name: currentScope.name
      });
      state.index = 0;
    }

    const currentEntry = state.entries[state.index];

    if (currentScope.standalone) {
      state.entries = [{ url: currentUrl, name: currentEntryName }];
      state.index = 0;
      state.scopeKey = currentScope.key;
    } else if (equivalentTrailUrl(currentUrl, currentScope.rootUrl)) {
      state.entries = [{ url: currentScope.rootUrl, name: currentScope.name }];
      state.index = 0;
      state.scopeKey = currentScope.key;
    } else if (!currentEntry || !equivalentTrailUrl(currentEntry.url, currentUrl)) {
      state.entries = state.entries.slice(0, state.index + 1);
      const existingIndex = state.entries.findIndex(function (entry) {
        return equivalentTrailUrl(entry.url, currentUrl);
      });
      if (existingIndex >= 0) {
        state.entries = state.entries.slice(0, existingIndex + 1);
        state.index = existingIndex;
      } else {
        state.entries.push({ url: currentUrl, name: currentEntryName });
        state.index = state.entries.length - 1;
      }
      state.entries = state.entries.slice(-60);
    } else if (currentEntry.name !== currentEntryName) {
      currentEntry.name = currentEntryName;
    }

    state.scopeKey = currentScope.key;

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
    bindModuleTabs();
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
