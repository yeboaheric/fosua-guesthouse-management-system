(function () {
  "use strict";

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
      button.innerHTML = '<i data-lucide="eye" aria-hidden="true"></i>';
      button.addEventListener("click", function () {
        var isVisible = input.type === "text";
        input.type = isVisible ? "password" : "text";
        button.setAttribute("aria-label", isVisible ? "Show password" : "Hide password");
        button.setAttribute("aria-pressed", String(!isVisible));
        button.innerHTML = '<i data-lucide="' + (isVisible ? "eye" : "eye-off") + '" aria-hidden="true"></i>';
        if (window.lucide) window.lucide.createIcons({ nodes: [button] });
        input.focus({ preventScroll: true });
      });
      wrapper.appendChild(button);
    });
    if (window.lucide) window.lucide.createIcons();
  }

  document.addEventListener("submit", function (event) {
    var form = event.target.closest("form[data-confirm]");
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
    document.addEventListener("DOMContentLoaded", enhancePasswordFields);
  } else {
    enhancePasswordFields();
  }
})();
