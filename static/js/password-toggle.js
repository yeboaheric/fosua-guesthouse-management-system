(function () {
  "use strict";

  function renderIcon(button, visible) {
    button.innerHTML = '<i data-lucide="' + (visible ? "eye" : "eye-off") + '" aria-hidden="true"></i>';
    if (window.lucide) window.lucide.createIcons({ nodes: [button] });
  }

  function enhancePasswordFields() {
    document.querySelectorAll('input[type="password"]').forEach(function (input) {
      if (input.dataset.passwordToggleReady === "true") return;
      input.dataset.passwordToggleReady = "true";

      var wrapper = document.createElement("span");
      wrapper.className = "password-input-wrap";
      input.parentNode.insertBefore(wrapper, input);
      wrapper.appendChild(input);

      var button = document.createElement("button");
      button.type = "button";
      button.className = "password-visibility-toggle";
      button.setAttribute("aria-label", "Show password");
      button.setAttribute("aria-pressed", "false");
      renderIcon(button, false);
      button.addEventListener("click", function () {
        var isVisible = input.type === "text";
        var nextVisible = !isVisible;
        input.type = nextVisible ? "text" : "password";
        button.setAttribute("aria-label", nextVisible ? "Hide password" : "Show password");
        button.setAttribute("aria-pressed", String(nextVisible));
        renderIcon(button, nextVisible);
        input.focus({ preventScroll: true });
      });
      wrapper.appendChild(button);
    });
    if (window.lucide) window.lucide.createIcons();
  }

  function watchPasswordFields() {
    if (!window.MutationObserver) return;
    var observer = new MutationObserver(function (mutations) {
      var shouldEnhance = mutations.some(function (mutation) {
        return Array.prototype.some.call(mutation.addedNodes, function (node) {
          if (node.nodeType !== 1) return false;
          return (node.matches && node.matches('input[type="password"]'))
            || (node.querySelector && node.querySelector('input[type="password"]'));
        });
      });
      if (shouldEnhance) enhancePasswordFields();
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  document.addEventListener("submit", function (event) {
    var form = event.target.closest("form[data-confirm]");
    if (form && form.dataset.confirmHandled === "true") return;
    if (form && !window.confirm(form.dataset.confirm)) event.preventDefault();
  });

  document.addEventListener("click", function (event) {
    var confirmButton = event.target.closest("button[data-confirm]");
    if (confirmButton && !window.confirm(confirmButton.dataset.confirm)) {
      event.preventDefault();
      return;
    }
    if (event.target.closest("[data-print]")) window.print();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      enhancePasswordFields();
      watchPasswordFields();
    });
  } else {
    enhancePasswordFields();
    watchPasswordFields();
  }
})();
