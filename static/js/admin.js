/**
 * ANNAMALAI archive — control room interaction layer.
 * Vanilla JavaScript only. All behaviour is progressive enhancement.
 */
(function () {
  "use strict";

  const doc = document;
  const body = doc.body;
  if (!body || !body.classList.contains("admin-body")) {
    return;
  }

  const $ = (selector, context = doc) => context.querySelector(selector);
  const $$ = (selector, context = doc) => Array.from(context.querySelectorAll(selector));
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const mobileQuery = window.matchMedia("(max-width: 1024px)");
  const FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
    'select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';

  function isElement(value) {
    return value instanceof Element;
  }

  function focusables(container) {
    return $$(FOCUSABLE, container).filter(
      (element) =>
        !element.hasAttribute("hidden") &&
        element.getClientRects().length > 0 &&
        element.getAttribute("aria-hidden") !== "true"
    );
  }

  function trapFocus(event, container) {
    const items = focusables(container);
    if (!items.length) {
      event.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && doc.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && doc.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  /* -----------------------------------------------------------------------
     Sidebar
     ----------------------------------------------------------------------- */
  const sidebar = $("#admin-sidebar");
  const sidebarToggle = $("[data-sidebar-toggle]");
  const sidebarBackdrop = $(".admin-sidebar-backdrop");
  let sidebarOpen = false;
  let sidebarReturnFocus = null;

  function openSidebar() {
    if (!sidebar || !mobileQuery.matches || sidebarOpen) return;
    sidebarReturnFocus = doc.activeElement;
    sidebarOpen = true;
    sidebar.classList.add("is-open");
    sidebar.setAttribute("aria-hidden", "false");
    body.classList.add("admin-nav-open");
    if (sidebarBackdrop) sidebarBackdrop.hidden = false;
    sidebarToggle?.setAttribute("aria-expanded", "true");
    sidebarToggle?.setAttribute("aria-label", "Close control room navigation");
    window.setTimeout(() => {
      if (!sidebarOpen) return;
      const first = $(".admin-nav__link, a, button", sidebar);
      (first || sidebar).focus({ preventScroll: true });
    }, 80);
  }

  function closeSidebar(restoreFocus = true) {
    if (!sidebar || !sidebarOpen) return;
    sidebarOpen = false;
    sidebar.classList.remove("is-open");
    sidebar.setAttribute("aria-hidden", "true");
    body.classList.remove("admin-nav-open");
    sidebarToggle?.setAttribute("aria-expanded", "false");
    sidebarToggle?.setAttribute("aria-label", "Open control room navigation");
    if (sidebarBackdrop) {
      window.setTimeout(() => {
        if (!sidebarOpen) sidebarBackdrop.hidden = true;
      }, prefersReducedMotion ? 0 : 260);
    }
    if (restoreFocus) {
      const target = sidebarReturnFocus || sidebarToggle;
      if (target && doc.contains(target)) target.focus({ preventScroll: true });
    }
    sidebarReturnFocus = null;
  }

  function initSidebar() {
    if (!sidebar) return;
    sidebarToggle?.addEventListener("click", () => {
      if (sidebarOpen) closeSidebar();
      else openSidebar();
    });
    $$("[data-sidebar-close]").forEach((control) => {
      control.addEventListener("click", () => closeSidebar());
    });
    $$(".admin-nav__link", sidebar).forEach((link) => {
      link.addEventListener("click", () => {
        if (mobileQuery.matches) closeSidebar(false);
      });
    });
    const handleDesktop = (event) => {
      if (!event.matches) closeSidebar(false);
    };
    if (mobileQuery.addEventListener) {
      mobileQuery.addEventListener("change", handleDesktop);
    } else if (mobileQuery.addListener) {
      mobileQuery.addListener(handleDesktop);
    }
    if (!mobileQuery.matches) {
      sidebar.setAttribute("aria-hidden", "false");
    }
  }

  /* -----------------------------------------------------------------------
     Toasts
     ----------------------------------------------------------------------- */
  function dismissToast(toast) {
    if (!toast || toast.dataset.dismissing === "true") return;
    toast.dataset.dismissing = "true";
    toast.classList.add("is-leaving");
    window.setTimeout(() => toast.remove(), prefersReducedMotion ? 0 : 260);
  }

  function initToasts() {
    $$(".admin-toast").forEach((toast) => {
      let timer = window.setTimeout(() => dismissToast(toast), 7200);
      toast.addEventListener("mouseenter", () => window.clearTimeout(timer));
      toast.addEventListener("mouseleave", () => {
        timer = window.setTimeout(() => dismissToast(toast), 3200);
      });
    });
    doc.addEventListener("click", (event) => {
      if (!isElement(event.target)) return;
      const close = event.target.closest("[data-admin-toast-close]");
      if (close) dismissToast(close.closest(".admin-toast"));
    });
  }

  /* -----------------------------------------------------------------------
     Destructive confirmation modal
     ----------------------------------------------------------------------- */
  const confirmModal = $("#admin-confirm");
  const confirmMessage = $("#admin-confirm-message");
  const confirmAccept = $("[data-confirm-accept]", confirmModal || doc);
  let pendingForm = null;
  let pendingSubmitter = null;
  let confirmReturnFocus = null;

  function openConfirm(form, submitter) {
    if (!confirmModal) {
      if (window.confirm(form.dataset.confirm || "Continue?")) {
        form.dataset.confirmed = "true";
        form.requestSubmit(submitter || undefined);
      }
      return;
    }
    pendingForm = form;
    pendingSubmitter = submitter || null;
    confirmReturnFocus = submitter || doc.activeElement;
    if (confirmMessage) {
      confirmMessage.textContent = form.dataset.confirm || "This action cannot be undone.";
    }
    confirmModal.hidden = false;
    body.classList.add("admin-modal-open");
    window.requestAnimationFrame(() => confirmModal.classList.add("is-open"));
    window.setTimeout(() => {
      const cancel = $("[data-confirm-cancel].admin-btn, [data-confirm-cancel]", confirmModal);
      (cancel || confirmAccept || confirmModal).focus({ preventScroll: true });
    }, 50);
  }

  function closeConfirm(restoreFocus = true) {
    if (!confirmModal || confirmModal.hidden) return;
    confirmModal.classList.remove("is-open");
    confirmModal.hidden = true;
    body.classList.remove("admin-modal-open");
    pendingForm = null;
    pendingSubmitter = null;
    if (restoreFocus && confirmReturnFocus && doc.contains(confirmReturnFocus)) {
      confirmReturnFocus.focus({ preventScroll: true });
    }
    confirmReturnFocus = null;
  }

  function acceptConfirm() {
    const form = pendingForm;
    const submitter = pendingSubmitter;
    closeConfirm(false);
    if (!form) return;
    form.dataset.confirmed = "true";
    if (typeof form.requestSubmit === "function") {
      try {
        form.requestSubmit(submitter || undefined);
        return;
      } catch (error) {
        form.dataset.confirmed = "";
      }
    }
    form.submit();
  }

  function initConfirmModal() {
    doc.addEventListener(
      "submit",
      (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (form.dataset.confirmed === "true") {
          delete form.dataset.confirmed;
          return;
        }
        if (!form.hasAttribute("data-confirm")) return;
        event.preventDefault();
        openConfirm(form, event.submitter);
      },
      true
    );

    if (!confirmModal) return;

    $$("[data-confirm-cancel]").forEach((control) => {
      control.addEventListener("click", () => closeConfirm());
    });
    confirmAccept?.addEventListener("click", acceptConfirm);

    confirmModal.addEventListener("click", (event) => {
      if (event.target === confirmModal) closeConfirm();
    });

    doc.addEventListener("keydown", (event) => {
      if (confirmModal.hidden) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeConfirm();
      } else if (event.key === "Tab") {
        trapFocus(event, confirmModal);
      }
    });
  }

  /* -----------------------------------------------------------------------
     File previews and upload drop zones
     ----------------------------------------------------------------------- */
  function initFilePreviews() {
    $$('input[type="file"]').forEach((input) => {
      const upload = input.closest(".admin-upload, .admin-upload-form, .admin-upload-drop");
      const preview = upload ? $("[data-upload-preview]", upload) : null;
      const empty = upload ? $(".admin-media-preview__empty", upload) : null;
      let objectUrl = null;

      input.addEventListener("change", () => {
        const file = input.files && input.files[0];

        if (preview) {
          if (objectUrl) {
            URL.revokeObjectURL(objectUrl);
            objectUrl = null;
          }
          if (file && file.type.startsWith("image/")) {
            objectUrl = URL.createObjectURL(file);
            preview.src = objectUrl;
            preview.hidden = false;
            if (empty) empty.hidden = true;
          } else {
            preview.removeAttribute("src");
            preview.hidden = true;
            if (empty) empty.hidden = false;
          }
        }

        const selection = upload ? $("[data-upload-selection]", upload) : null;
        if (selection) {
          const count = input.files ? input.files.length : 0;
          selection.textContent =
            count === 0
              ? ""
              : `${count} FILE${count === 1 ? "" : "S"} SELECTED / ${Array.from(input.files)
                  .map((item) => item.name)
                  .join(" · ")}`;
          selection.hidden = count === 0;
        }

        if (upload && upload.classList.contains("admin-upload-drop")) {
          upload.classList.toggle("has-files", Boolean(input.files && input.files.length));
        }
      });
    });

    $$(".admin-upload-drop").forEach((drop) => {
      const input = $('input[type="file"]', drop);
      if (!input) return;
      ["dragenter", "dragover"].forEach((name) => {
        drop.addEventListener(name, (event) => {
          event.preventDefault();
          drop.classList.add("is-dragging");
        });
      });
      ["dragleave", "dragend", "drop"].forEach((name) => {
        drop.addEventListener(name, () => drop.classList.remove("is-dragging"));
      });
      drop.addEventListener("drop", (event) => {
        event.preventDefault();
        if (!event.dataTransfer || !event.dataTransfer.files.length) return;
        try {
          input.files = event.dataTransfer.files;
          input.dispatchEvent(new Event("change", { bubbles: true }));
        } catch (error) {
          /* Some browsers expose a read-only FileList. */
        }
      });
    });
  }

  /* -----------------------------------------------------------------------
     Colour pickers and live preview
     ----------------------------------------------------------------------- */
  const HEX = /^#[0-9a-f]{6}$/i;

  function initColourControls() {
    const preview = $(".admin-surface-preview");
    const swatches = $$(".admin-surface-preview__palette i");
    const mapping = {
      color_bg: { variable: "--preview-bg", index: 0 },
      color_panel: { variable: "--preview-panel", index: 1 },
      color_text: { variable: "--preview-text", index: 2 },
      color_muted: { variable: "--preview-muted", index: 3 },
      color_red: { variable: "--preview-red", index: 4 },
      color_copper: { variable: "--preview-copper", index: 5 },
      color_green: { variable: "--preview-green-deep", index: 6 },
      color_green_light: { variable: "--preview-green", index: 7 },
      color_highlight: { variable: "--preview-highlight", index: 8 },
    };

    function paint(id, value) {
      const entry = mapping[id];
      if (!entry || !HEX.test(value)) return;
      if (preview) preview.style.setProperty(entry.variable, value);
      const swatch = swatches[entry.index];
      if (swatch) swatch.style.background = value;
    }

    $$("[data-color-picker]").forEach((picker) => {
      const target = doc.getElementById(picker.dataset.target || "");
      if (!target) return;

      picker.addEventListener("input", () => {
        target.value = picker.value.toUpperCase();
        paint(target.id, picker.value);
      });

      target.addEventListener("input", () => {
        const value = target.value.trim();
        if (HEX.test(value)) {
          picker.value = value;
          paint(target.id, value);
        }
      });

      target.addEventListener("blur", () => {
        const value = target.value.trim();
        if (!HEX.test(value) && HEX.test(picker.value)) {
          target.value = picker.value.toUpperCase();
        }
      });
    });
  }

  function initLivePreview() {
    $$("[data-preview]").forEach((node) => {
      const field = doc.getElementById(node.dataset.preview || "");
      if (!field) return;
      const update = () => {
        node.textContent = field.value;
      };
      field.addEventListener("input", update);
      update();
    });
  }

  /* -----------------------------------------------------------------------
     Password visibility, strength and requirements
     ----------------------------------------------------------------------- */
  function setIcon(button, name) {
    const use = $("use", button);
    if (!use) return;
    const href = use.getAttribute("href") || use.getAttribute("xlink:href") || "";
    const base = href.split("#")[0];
    if (base) {
      use.setAttribute("href", `${base}#${name}`);
      use.setAttribute("xlink:href", `${base}#${name}`);
    }
  }

  function initPasswordToggles() {
    $$("[data-password-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        const input = doc.getElementById(button.dataset.target || "");
        if (!input) return;
        const show = input.type === "password";
        input.type = show ? "text" : "password";
        button.setAttribute("aria-pressed", String(show));
        button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        setIcon(button, show ? "eye-off" : "eye");
      });
    });
  }

  function initPasswordStrength() {
    const input = doc.getElementById("new_password");
    const panel = $("[data-password-strength]");
    const requirements = $("[data-password-requirements]");
    if (!input || !panel) return;

    const current = doc.getElementById("current_password");
    const bar = $(".admin-strength__bar", panel);
    const fill = $(".admin-strength__bar i", panel);
    const label = $(".admin-strength__label", panel);
    const rules = requirements ? $$("[data-rule]", requirements) : [];

    const tests = {
      length: () => input.value.length >= 8,
      letter: () => /[A-Za-z]/.test(input.value),
      number: () => /\d/.test(input.value),
      different: () => !current || !current.value || input.value !== current.value,
    };

    function update() {
      const value = input.value;
      panel.hidden = value.length === 0;

      let score = 0;
      if (value.length >= 8) score += 1;
      if (/[A-Za-z]/.test(value)) score += 1;
      if (/\d/.test(value)) score += 1;
      if (value.length >= 12) score += 1;
      if (/[^A-Za-z0-9]/.test(value)) score += 1;

      const levels = ["", "is-weak", "is-fair", "is-good", "is-strong", "is-strong"];
      if (fill && bar) {
        fill.style.width = `${Math.min(100, score * 20)}%`;
        bar.className = `admin-strength__bar ${levels[score] || ""}`.trim();
      }
      if (label) {
        label.textContent =
          value.length === 0
            ? "ENTER A PASSWORD"
            : score <= 2
              ? "WEAK / ADD LENGTH, LETTERS OR NUMBERS"
              : score === 3
                ? "FAIR / ADD MORE LENGTH"
                : score === 4
                  ? "GOOD / ALMOST THERE"
                  : "STRONG / READY TO SAVE";
      }

      rules.forEach((rule) => {
        const test = tests[rule.dataset.rule];
        if (!test) return;
        const met = test();
        rule.classList.toggle("is-met", met);
        rule.classList.toggle("is-unmet", !met && value.length > 0);
      });
    }

    input.addEventListener("input", update);
    current?.addEventListener("input", update);
    update();
  }

  /* -----------------------------------------------------------------------
     Easter egg placement preview
     ----------------------------------------------------------------------- */
  function initEggPreview() {
    const form = doc.getElementById("egg-form");
    const title = doc.getElementById("title");
    const section = doc.getElementById("section");
    const type = doc.getElementById("interaction_type");
    const titleNode = doc.getElementById("egg-preview-title");
    const metaNode = doc.getElementById("egg-preview-meta");
    if (!form || !titleNode || !metaNode) return;

    const update = () => {
      titleNode.textContent =
        (title && title.value.trim()) || "HIDDEN RECORD TITLE";
      const place = section ? section.options[section.selectedIndex]?.text || "" : "";
      const kind = type ? type.options[type.selectedIndex]?.text || "" : "";
      metaNode.textContent = `${place || "GLOBAL / TERMINAL"} / ${kind || "HIDDEN OBJECT"}`;
    };
    [title, section, type].forEach((field) => field?.addEventListener("input", update));
    [section, type].forEach((field) => field?.addEventListener("change", update));
    update();
  }

  /* -----------------------------------------------------------------------
     Gallery selection summary
     ----------------------------------------------------------------------- */
  function initGallerySelection() {
    const input = doc.getElementById("gallery-images");
    const selection = $("[data-upload-selection]");
    if (!input || !selection) return;
    input.addEventListener("change", () => {
      const count = input.files ? input.files.length : 0;
      selection.textContent =
        count === 0
          ? ""
          : `${count} FRAME${count === 1 ? "" : "S"} SELECTED / ${Array.from(input.files)
              .map((file) => file.name)
              .join(" · ")}`;
      selection.hidden = count === 0;
    });
  }

  /* -----------------------------------------------------------------------
     Keyboard handling for sidebar and modal
     ----------------------------------------------------------------------- */
  function initKeyboardHandling() {
    doc.addEventListener("keydown", (event) => {
      if (confirmModal && !confirmModal.hidden) return;
      if (!sidebarOpen) return;
      if (event.key === "Escape") {
        event.preventDefault();
        closeSidebar();
        return;
      }
      if (event.key === "Tab" && sidebar) {
        trapFocus(event, sidebar);
      }
    });
  }

  doc.addEventListener("DOMContentLoaded", () => {
    initSidebar();
    initToasts();
    initConfirmModal();
    initFilePreviews();
    initColourControls();
    initLivePreview();
    initPasswordToggles();
    initPasswordStrength();
    initEggPreview();
    initGallerySelection();
    initKeyboardHandling();
  });
})();
