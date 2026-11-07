/**
 * ANNAMALAI archive — public interaction layer.
 * Vanilla JavaScript only. Every control maps to a real DOM element or record.
 */
(function () {
  "use strict";

  const doc = document;
  const body = doc.body;
  if (!body || !body.classList.contains("archive-body")) {
    return;
  }

  const root = doc.documentElement;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const animationsEnabled = body.dataset.animations === "true" && !prefersReducedMotion;
  const siteTimeZone = body.dataset.timezone || "Asia/Kolkata";
  const MODE_KEY = "archive-focus-mode";

  const $ = (selector, context = doc) => context.querySelector(selector);
  const $$ = (selector, context = doc) => Array.from(context.querySelectorAll(selector));
  const pad = (value) => String(value).padStart(2, "0");
  const isElement = (value) => value instanceof Element;
  const scrollBehavior = () => (animationsEnabled ? "smooth" : "auto");

  function clockTime(date = new Date()) {
    try {
      return new Intl.DateTimeFormat("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
        timeZone: siteTimeZone,
      }).format(date);
    } catch (error) {
      return date.toLocaleTimeString("en-GB", { hour12: false });
    }
  }

  const FOCUSABLE =
    'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
    'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

  function visibleFocusables(container) {
    return $$(FOCUSABLE, container).filter(
      (element) =>
        !element.hasAttribute("hidden") && element.getClientRects().length > 0
    );
  }

  function trapFocus(event, container) {
    const items = visibleFocusables(container);
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
     Overlay manager — one accessible layer at a time
     ----------------------------------------------------------------------- */
  let activeOverlay = null;
  let overlayReturnFocus = null;
  const closingOverlays = new WeakSet();

  function openOverlay(layer, focusTarget) {
    if (!layer) return;

    if (activeOverlay && activeOverlay !== layer) {
      activeOverlay.hidden = true;
      activeOverlay.classList.remove("is-open", "is-closing");
    }
    if (!activeOverlay) {
      overlayReturnFocus = doc.activeElement;
    }

    layer.hidden = false;
    layer.classList.remove("is-closing");
    layer.classList.add("is-open");
    activeOverlay = layer;
    body.classList.add("overlay-open");

    const dialog =
      $(".secret-dialog, .terminal-window, .lightbox", layer) || layer;
    const target = focusTarget || dialog;
    window.setTimeout(() => {
      if (activeOverlay === layer && isElement(target)) {
        target.focus({ preventScroll: true });
      }
    }, 40);
  }

  function closeOverlay(layer = activeOverlay) {
    if (!layer || layer.hidden || closingOverlays.has(layer)) return;

    closingOverlays.add(layer);
    layer.classList.add("is-closing");

    const finish = () => {
      layer.hidden = true;
      layer.classList.remove("is-open", "is-closing");
      closingOverlays.delete(layer);
      if (activeOverlay === layer) {
        activeOverlay = null;
      }
      if (!activeOverlay) {
        body.classList.remove("overlay-open");
        const previous = overlayReturnFocus;
        overlayReturnFocus = null;
        if (previous && doc.contains(previous)) {
          previous.focus({ preventScroll: true });
        }
      }
    };

    window.setTimeout(finish, prefersReducedMotion ? 0 : 250);
  }

  doc.addEventListener("click", (event) => {
    if (!isElement(event.target)) return;
    const closer = event.target.closest("[data-overlay-close]");
    if (!closer) return;
    const layer = closer.closest(".overlay-layer");
    if (layer) {
      event.preventDefault();
      closeOverlay(layer);
    }
  });

  /* -----------------------------------------------------------------------
     Boot sequence
     ----------------------------------------------------------------------- */
  function initBoot() {
    const boot = $("#boot-screen");
    if (!boot) return;

    let seen = false;
    try {
      seen = window.sessionStorage.getItem("archive-boot-seen") === "1";
    } catch (error) {
      seen = false;
    }

    if (!animationsEnabled || seen) {
      boot.classList.add("is-skipped");
      window.setTimeout(() => boot.remove(), 50);
      return;
    }

    try {
      window.sessionStorage.setItem("archive-boot-seen", "1");
    } catch (error) {
      /* Private mode may deny storage. */
    }

    const bar = $("#boot-progress-bar");
    const percent = $("#boot-percent");
    let progress = 0;

    const timer = window.setInterval(() => {
      progress = Math.min(100, progress + 9 + Math.floor(Math.random() * 13));
      if (bar) bar.style.width = `${progress}%`;
      if (percent) percent.textContent = `${pad(progress)}%`;
      if (progress >= 100) window.clearInterval(timer);
    }, 180);

    window.setTimeout(() => {
      progress = 100;
      if (bar) bar.style.width = "100%";
      if (percent) percent.textContent = "100%";
      window.clearInterval(timer);
      boot.classList.add("is-leaving");
    }, 1850);

    window.setTimeout(() => {
      boot.classList.add("is-skipped");
      boot.remove();
    }, 2700);
  }

  /* -----------------------------------------------------------------------
     Navigation, progress, active section
     ----------------------------------------------------------------------- */
  const nav = $("#archive-nav");
  const navProgress = $("#nav-progress-bar");
  const navLinks = $$("[data-nav-link]");
  const navSections = $$("[data-archive-section]").filter(
    (section) => navLinks.some((link) => link.dataset.navLink === section.id)
  );
  const mobileMenu = $("#mobile-menu");
  const navToggle = $("[data-nav-toggle]");
  let menuOpen = false;
  let menuTimer = null;
  let menuReturnFocus = null;
  let lastScrollY = window.scrollY;
  let scrollFrame = 0;

  function updateScrollUI() {
    const y = window.scrollY;
    const height = Math.max(1, doc.documentElement.scrollHeight - window.innerHeight);
    const ratio = Math.min(1, Math.max(0, y / height));

    if (navProgress) {
      navProgress.style.width = `${(ratio * 100).toFixed(2)}%`;
    }

    if (nav) {
      nav.classList.toggle("is-scrolled", y > 24);
      if (!menuOpen && !activeOverlay) {
        if (y > lastScrollY + 6 && y > 480) {
          nav.classList.add("is-hidden");
        } else if (y < lastScrollY - 6 || y < 140) {
          nav.classList.remove("is-hidden");
        }
      }
    }

    let current = "home";
    for (const section of navSections) {
      if (section.offsetTop - 140 <= y) {
        current = section.id;
      }
    }
    for (const link of navLinks) {
      const active = link.dataset.navLink === current;
      link.classList.toggle("is-active", active);
      if (active) {
        link.setAttribute("aria-current", "location");
      } else {
        link.removeAttribute("aria-current");
      }
    }

    lastScrollY = y;
  }

  function requestScrollUpdate() {
    if (scrollFrame) return;
    scrollFrame = window.requestAnimationFrame(() => {
      scrollFrame = 0;
      updateScrollUI();
    });
  }

  function openMenu() {
    if (!mobileMenu || menuOpen) return;
    window.clearTimeout(menuTimer);
    menuReturnFocus = doc.activeElement;
    mobileMenu.hidden = false;
    menuOpen = true;
    body.classList.add("menu-open");
    nav?.classList.remove("is-hidden");
    navToggle?.setAttribute("aria-expanded", "true");
    navToggle?.setAttribute("aria-label", "Close navigation menu");
    window.requestAnimationFrame(() => mobileMenu.classList.add("is-open"));
    window.setTimeout(() => {
      const firstLink = $("[data-mobile-nav-link]", mobileMenu);
      (firstLink || mobileMenu).focus({ preventScroll: true });
    }, 90);
  }

  function closeMenu(restoreFocus = true) {
    if (!mobileMenu || !menuOpen) return;
    menuOpen = false;
    body.classList.remove("menu-open");
    navToggle?.setAttribute("aria-expanded", "false");
    navToggle?.setAttribute("aria-label", "Open navigation menu");
    mobileMenu.classList.remove("is-open");
    menuTimer = window.setTimeout(() => {
      if (!menuOpen) mobileMenu.hidden = true;
    }, prefersReducedMotion ? 0 : 280);
    if (restoreFocus && navToggle) {
      navToggle.focus({ preventScroll: true });
    }
  }

  function initNavigation() {
    navToggle?.addEventListener("click", () => {
      if (menuOpen) closeMenu();
      else openMenu();
    });

    $$("[data-nav-close]").forEach((control) => {
      control.addEventListener("click", () => closeMenu());
    });

    $$("[data-mobile-nav-link]").forEach((link) => {
      link.addEventListener("click", () => closeMenu(false));
    });

    navLinks.forEach((link) => {
      link.addEventListener("click", () => {
        nav?.classList.remove("is-hidden");
      });
    });

    const desktopQuery = window.matchMedia("(min-width: 1025px)");
    const handleDesktop = (event) => {
      if (event.matches) closeMenu(false);
    };
    if (desktopQuery.addEventListener) {
      desktopQuery.addEventListener("change", handleDesktop);
    } else if (desktopQuery.addListener) {
      desktopQuery.addListener(handleDesktop);
    }

    window.addEventListener("scroll", requestScrollUpdate, { passive: true });
    window.addEventListener("resize", requestScrollUpdate);
    window.addEventListener("load", requestScrollUpdate);
    window.addEventListener("hashchange", () => {
      nav?.classList.remove("is-hidden");
      requestScrollUpdate();
    });
    updateScrollUI();
  }

  /* -----------------------------------------------------------------------
     Focus mode
     ----------------------------------------------------------------------- */
  function applyFocusMode(green, persist = true) {
    root.classList.toggle("green-mode", green);
    $$("[data-mode-toggle]").forEach((button) => {
      button.setAttribute("aria-pressed", String(green));
      const label = green ? "Disable green focus mode" : "Enable green focus mode";
      button.setAttribute("aria-label", label);
      button.setAttribute("title", label);
    });
    if (persist) {
      try {
        window.localStorage.setItem(MODE_KEY, green ? "green" : "red");
      } catch (error) {
        /* Storage can be unavailable in strict privacy modes. */
      }
    }
  }

  function initFocusMode() {
    applyFocusMode(root.classList.contains("green-mode"), false);
    $$("[data-mode-toggle]").forEach((button) => {
      button.addEventListener("click", () => {
        applyFocusMode(!root.classList.contains("green-mode"));
      });
    });
  }

  /* -----------------------------------------------------------------------
     Toasts
     ----------------------------------------------------------------------- */
  function dismissToast(toast) {
    if (!toast || toast.dataset.dismissing === "true") return;
    toast.dataset.dismissing = "true";
    const remove = () => toast.remove();
    if (prefersReducedMotion || typeof toast.animate !== "function") {
      remove();
      return;
    }
    const animation = toast.animate(
      [
        { opacity: 1, transform: "translateX(0)", maxHeight: `${toast.offsetHeight}px` },
        { opacity: 0, transform: "translateX(18px)", maxHeight: "0px", margin: "0", padding: "0" },
      ],
      { duration: 260, easing: "ease", fill: "forwards" }
    );
    animation.addEventListener("finish", remove, { once: true });
    window.setTimeout(remove, 500);
  }

  function initToasts() {
    $$(".archive-toast").forEach((toast) => {
      window.setTimeout(() => dismissToast(toast), 7000);
    });
    doc.addEventListener("click", (event) => {
      if (!isElement(event.target)) return;
      const close = event.target.closest("[data-toast-close]");
      if (close) dismissToast(close.closest(".archive-toast"));
    });
  }

  /* -----------------------------------------------------------------------
     Hidden records / artifact modal
     ----------------------------------------------------------------------- */
  function initSecretRecords() {
    const layer = $("#secret-modal");
    if (!layer) return;
    const label = $("#secret-label");
    const title = $("#secret-title");
    const message = $("#secret-message");
    const fragmentBox = $("#secret-fragment");
    const fragmentCode = $("#secret-fragment-code");
    const fragmentSlot = $("#secret-fragment-slot");
    const fragmentCommand = $("#secret-fragment-command");

    doc.addEventListener("click", (event) => {
      if (!isElement(event.target)) return;
      const trigger = event.target.closest("[data-secret-trigger]");
      if (!trigger) return;
      event.preventDefault();

      if (label) label.textContent = trigger.dataset.eggLabel || "HIDDEN RECORD";
      if (title) title.textContent = trigger.dataset.eggTitle || "ARCHIVE ANOMALY";
      if (message) {
        message.textContent =
          trigger.dataset.eggMessage || "This record has no readable content.";
      }

      const code = String(trigger.dataset.eggFragment || "").trim().toUpperCase();
      const slot = String(trigger.dataset.eggSlot || "").trim();
      if (fragmentBox && code && slot) {
        fragmentBox.hidden = false;
        if (fragmentCode) fragmentCode.textContent = code;
        if (fragmentSlot) {
          fragmentSlot.textContent = `${pad(Number(slot) || 0)} / ${pad(fragments.length)}`;
        }
        if (fragmentCommand) fragmentCommand.textContent = code;
      } else if (fragmentBox) {
        fragmentBox.hidden = true;
      }

      openOverlay(layer, $(".secret-dialog", layer));
    });
  }

  /* -----------------------------------------------------------------------
     Secret terminal
     ----------------------------------------------------------------------- */
  const terminalLayer = $("#terminal-modal");
  const terminalOutput = $("#terminal-output");
  const terminalForm = $("#terminal-form");
  const terminalInput = $("#terminal-input");
  const mmClock = $("#miss-minutes");
  const mmLine = $("#miss-minutes-line");
  let archiveSnapshot = null;
  let terminalStarted = false;
  let terminalLoading = false;
  let controlOpening = false;
  const terminalHistory = [];
  let historyIndex = -1;

  /* -----------------------------------------------------------------------
     Tempad access fragments / sealed control door
     ----------------------------------------------------------------------- */
  const ACCESS_KEY = "annamalai-archive-access";
  const accessConfig = $("[data-access-config]");
  const controlGate = $("[data-control-gate]");
  const controlUnlocked = $("[data-control-unlocked]");
  const controlShell = $("[data-control-shell]");
  const fragmentCountNode = $("[data-fragment-count]");
  const fragmentTotalNode = $("[data-fragment-total]");
  const fragmentBarNode = $("[data-fragment-bar]");
  const accessStatusNode = $("[data-control-access-status]");
  const sectionStatusNode = $("#control-section-status");
  const tempadFragmentsNode = $("#tempad-fragments");

  const fragmentMap = new Map();
  if (accessConfig) {
    $$("[data-access-fragment]", accessConfig).forEach((node) => {
      const slot = Number(node.dataset.slot);
      const code = String(node.dataset.code || "").trim().toUpperCase();
      if (!Number.isInteger(slot) || slot < 1 || slot > 4 || !code) return;
      if (fragmentMap.has(slot)) return;
      if (Array.from(fragmentMap.values()).some((fragment) => fragment.code === code)) {
        return;
      }
      fragmentMap.set(slot, {
        slot,
        code,
        section: String(node.dataset.section || "archive").trim(),
        title: String(node.dataset.title || "Hidden record").trim(),
      });
    });
  }
  const fragments = Array.from(fragmentMap.values()).sort((a, b) => a.slot - b.slot);
  const fragmentCodes = new Set(fragments.map((fragment) => fragment.code));

  function readAccessState() {
    const state = { found: new Set(), unlocked: false };
    try {
      const stored = JSON.parse(window.localStorage.getItem(ACCESS_KEY) || "null");
      if (stored && typeof stored === "object") {
        const storedCodes = Array.isArray(stored.fragments) ? stored.fragments : [];
        storedCodes.forEach((value) => {
          const code = String(value || "").trim().toUpperCase();
          if (fragmentCodes.has(code)) state.found.add(code);
        });
        state.unlocked = stored.unlocked === true;
      }
    } catch (error) {
      state.found = new Set();
      state.unlocked = false;
    }
    if (fragmentCodes.size && state.found.size === fragmentCodes.size) {
      state.unlocked = true;
    }
    return state;
  }

  const accessState = readAccessState();

  function persistAccessState() {
    try {
      window.localStorage.setItem(
        ACCESS_KEY,
        JSON.stringify({
          fragments: Array.from(accessState.found),
          unlocked: accessState.unlocked,
        })
      );
    } catch (error) {
      /* Private browsing can disable storage; the puzzle still works per visit. */
    }
  }

  function foundFragments() {
    return fragments.filter((fragment) => accessState.found.has(fragment.code));
  }

  function missingFragments() {
    return fragments.filter((fragment) => !accessState.found.has(fragment.code));
  }

  function renderAccessState() {
    const found = foundFragments();
    const total = fragments.length;

    $$("[data-fragment-slot]").forEach((node) => {
      const slot = Number(node.dataset.fragmentSlot);
      const fragment = fragmentMap.get(slot);
      const codeNode = $("[data-fragment-code]", node);
      const hintNode = $("[data-fragment-hint]", node);
      const recovered = Boolean(fragment && accessState.found.has(fragment.code));
      node.classList.toggle("is-unassigned", !fragment);
      node.classList.toggle("is-found", recovered);
      if (!fragment) {
        if (codeNode) codeNode.textContent = "— — — —";
        if (hintNode) hintNode.textContent = "UNASSIGNED";
        return;
      }
      if (codeNode) {
        codeNode.textContent = recovered ? fragment.code : "• • • • •";
      }
      if (hintNode) {
        hintNode.textContent = recovered
          ? "RECOVERED / LOGGED"
          : `${fragment.section.toUpperCase()} / HIDDEN`;
      }
    });

    if (fragmentCountNode) fragmentCountNode.textContent = pad(found.length);
    if (fragmentTotalNode) fragmentTotalNode.textContent = pad(total);
    if (fragmentBarNode) {
      const progress = total ? Math.round((found.length / total) * 100) : 0;
      fragmentBarNode.style.width = `${progress}%`;
    }
    if (controlGate) {
      controlGate.classList.toggle("is-complete", total > 0 && found.length === total);
    }
    if (accessStatusNode) {
      if (accessState.unlocked) {
        accessStatusNode.textContent = "FIREWALL OPEN";
      } else if (total && found.length === total) {
        accessStatusNode.textContent = "KEY COMPLETE / OPENING";
      } else {
        accessStatusNode.textContent = "FIREWALL SEALED";
      }
    }
    if (tempadFragmentsNode) {
      tempadFragmentsNode.textContent = `FRAGMENTS ${pad(found.length)} / ${pad(total)}`;
    }
    if (terminalInput) {
      terminalInput.placeholder = accessState.unlocked
        ? "type open control"
        : total && found.length === total
          ? "type open control"
          : "type help — or unlock a fragment";
    }
    const emptyNode = $("[data-fragment-empty]");
    if (emptyNode) emptyNode.hidden = total > 0;
  }

  function syncControlVisibility({ scroll = false, focus = false } = {}) {
    if (!controlGate || !controlUnlocked) return;
    const open = accessState.unlocked;
    if (sectionStatusNode) {
      sectionStatusNode.textContent = open ? "CONSOLE / ONLINE" : "CONSOLE / SEALED";
    }
    controlGate.hidden = open;
    controlUnlocked.hidden = !open;
    if (!open) {
      controlUnlocked.classList.remove("is-online");
      return;
    }
    controlUnlocked.classList.add("is-online");
    if (scroll) {
      const section = doc.getElementById("control");
      scrollToElement(section);
      if (focus) {
        window.setTimeout(
          () => controlShell?.focus({ preventScroll: true }),
          animationsEnabled ? 720 : 80
        );
      }
    }
    if (window.ScrollTrigger) {
      window.setTimeout(() => window.ScrollTrigger.refresh(), 220);
    }
  }

  function unlockControl({ scroll = true, focus = true } = {}) {
    accessState.unlocked = true;
    persistAccessState();
    renderAccessState();
    if (activeOverlay === terminalLayer) {
      closeOverlay(terminalLayer);
      window.setTimeout(
        () => syncControlVisibility({ scroll, focus }),
        prefersReducedMotion ? 0 : 280
      );
    } else {
      syncControlVisibility({ scroll, focus });
    }
  }

  function relockControl() {
    accessState.found.clear();
    accessState.unlocked = false;
    controlOpening = false;
    persistAccessState();
    renderAccessState();
    syncControlVisibility();
    if (activeOverlay === terminalLayer) {
      closeOverlay(terminalLayer);
    }
    window.setTimeout(
      () => scrollToElement(doc.getElementById("control")),
      prefersReducedMotion ? 0 : 300
    );
  }

  function acceptFragment(value) {
    const code = String(value || "").trim().toUpperCase();
    if (!code) return { status: "empty" };
    const fragment = fragments.find((candidate) => candidate.code === code);
    if (!fragment) return { status: "invalid", code };
    if (accessState.found.has(code)) {
      return { status: "already", fragment };
    }
    accessState.found.add(code);
    persistAccessState();
    renderAccessState();
    return { status: "accepted", fragment, remaining: missingFragments().length };
  }

  function reportFragmentProgress(prefix = "PROGRESS") {
    const found = foundFragments().length;
    appendTerminalLine(
      `${prefix} / ${pad(found)} OF ${pad(fragments.length)} FRAGMENTS RECOVERED`,
      found === fragments.length ? "term-green" : "term-block"
    );
  }

  function openControlFromTerminal() {
    if (accessState.unlocked) {
      appendTerminalLine("CONTROL LINK ALREADY OPEN. Returning to the console...", "term-green");
      setMissMinutes("Back to the control room? Try not to break anything I have to clock.", "success");
      unlockControl({ scroll: true });
      return;
    }
    if (!fragments.length) {
      appendTerminalLine("NO FRAGMENTS PUBLISHED. Requesting emergency access...", "term-red");
      appendTerminalLine("EMERGENCY BYPASS ACCEPTED / CONTROL DOOR OPEN", "term-green");
      accessState.unlocked = true;
      persistAccessState();
      renderAccessState();
      setMissMinutes("No key, no lock. Fine. I will allow it this once.", "success");
      terminalLayer?.classList.add("is-granted");
      window.setTimeout(() => {
        terminalLayer?.classList.remove("is-granted");
        unlockControl({ scroll: true });
      }, prefersReducedMotion ? 0 : 900);
      return;
    }
    const missing = missingFragments();
    if (!missing.length) {
      appendTerminalLine("ACCESS KEY COMPLETE. Opening the control door...", "term-green");
      accessState.unlocked = true;
      persistAccessState();
      renderAccessState();
      setMissMinutes("Every piece accounted for. Opening the control room, sugar.", "success");
      terminalLayer?.classList.add("is-granted");
      window.setTimeout(() => {
        terminalLayer?.classList.remove("is-granted");
        unlockControl({ scroll: true });
      }, prefersReducedMotion ? 0 : 900);
      return;
    }
    appendTerminalLine("ACCESS DENIED / TEMPORAL FIREWALL SEALED", "term-red");
    reportFragmentProgress("CURRENT KEY");
    const next = missing[0];
    appendTerminalLine(
      `NEXT FRAGMENT / SLOT 0${next.slot} / ${next.section.toUpperCase()} / ${next.title}`,
      "term-amber"
    );
    appendTerminalLine(
      "Type UNLOCK <fragment> to submit a code. Type HINT if you need a pointer.",
      "term-muted"
    );
    setMissMinutes("Not yet, sugar. The door needs every piece, not almost every piece.", "warning");
  }

  function appendTerminalLine(text, className) {
    if (!terminalOutput) return null;
    const line = doc.createElement("span");
    line.className = `terminal-line${className ? ` ${className}` : ""}`;
    line.textContent = text;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
    return line;
  }

  function appendTerminalCommand(command) {
    if (!terminalOutput) return;
    const line = doc.createElement("span");
    line.className = "terminal-line";
    const prompt = doc.createElement("span");
    prompt.className = "term-muted";
    prompt.textContent = "tempad@archive:~$ ";
    const value = doc.createElement("span");
    value.className = "term-cmd";
    value.textContent = command;
    line.append(prompt, value);
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  function loadArchiveSnapshot() {
    if (terminalLoading || archiveSnapshot) return;
    terminalLoading = true;
    appendTerminalLine("> establishing encrypted channel...", "term-muted");

    fetch("/api/archive", {
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json" },
    })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((payload) => {
        archiveSnapshot = payload;
        appendTerminalLine("CONNECTION ACCEPTED / ARCHIVE A-001", "term-green");
        if (payload.handshake) {
          appendTerminalLine(payload.handshake, "term-block");
        }
        appendTerminalLine(
          "Type HELP to list commands. This session is read-only.",
          "term-muted"
        );
      })
      .catch(() => {
        appendTerminalLine(
          "CONNECTION FAILED. The archive is not reachable from this terminal.",
          "term-red"
        );
        appendTerminalLine("Local commands such as HELP and CLEAR still work.", "term-muted");
      })
      .finally(() => {
        terminalLoading = false;
      });
  }

  function terminalSnapshot() {
    if (!archiveSnapshot) {
      appendTerminalLine(
        "SNAPSHOT NOT READY. Wait for the channel, then try again.",
        "term-red"
      );
      return null;
    }
    return archiveSnapshot;
  }

  const terminalCommands = {
    help() {
      appendTerminalLine("TEMPAD COMMANDS", "term-green");
      appendTerminalLine("  ABOUT / WHOAMI ... identity record", "term-block");
      appendTerminalLine("  PROJECTS ........ project index", "term-block");
      appendTerminalLine("  TIMELINE ........ achievement coordinates", "term-block");
      appendTerminalLine("  TEAMS ........... organizations on record", "term-block");
      appendTerminalLine("  PEOPLE .......... collaborators", "term-block");
      appendTerminalLine("  GALLERY ......... visual archive status", "term-block");
      appendTerminalLine("  STATS ........... live record counts", "term-block");
      appendTerminalLine("  EGG ............. terminal handshake", "term-block");
      appendTerminalLine("  CONTACT ......... open the signal channel", "term-block");
      appendTerminalLine(" ");
      appendTerminalLine("TEMPORAL FIREWALL", "term-amber");
      appendTerminalLine("  FRAGMENTS ....... recovered access fragments", "term-block");
      appendTerminalLine("  UNLOCK <code> ... submit one fragment", "term-block");
      appendTerminalLine("  SCAN ............ show every fragment location", "term-block");
      appendTerminalLine("  HINT ............ point at the next missing fragment", "term-block");
      appendTerminalLine("  OPEN CONTROL .... open the sealed console", "term-block");
      appendTerminalLine("  RELOCK .......... re-seal the console and reset the key", "term-block");
      appendTerminalLine(" ");
      appendTerminalLine("DATE / LS / CLEAR / EXIT / MISS", "term-muted");
      appendTerminalLine("CTRL + SHIFT + A opens this Tempad anywhere.", "term-muted");
    },

    fragments() {
      if (!fragments.length) {
        appendTerminalLine("NO ACCESS FRAGMENTS ARE PUBLISHED.", "term-red");
        appendTerminalLine(
          "The control console accepts OPEN CONTROL as an emergency request.",
          "term-muted"
        );
        return;
      }
      appendTerminalLine("ACCESS FRAGMENT LEDGER", "term-green");
      fragments.forEach((fragment) => {
        const recovered = accessState.found.has(fragment.code);
        appendTerminalLine(
          `  SLOT 0${fragment.slot} / ${recovered ? fragment.code : "— — — — —"} / ${recovered ? "RECOVERED" : fragment.section.toUpperCase() + " / HIDDEN"}`,
          recovered ? "term-block" : "term-muted"
        );
      });
      reportFragmentProgress();
      if (!missingFragments().length) {
        appendTerminalLine(
          "KEY COMPLETE. Type OPEN CONTROL or wait for the Tempad to open it.",
          "term-green"
        );
      }
    },

    unlock(args) {
      const raw = args.join(" ").trim();
      if (!raw) {
        appendTerminalLine("USAGE / UNLOCK <fragment>", "term-amber");
        appendTerminalLine(
          "Open hidden records in the archive, read the access fragment, then type its code here.",
          "term-muted"
        );
        reportFragmentProgress();
        return;
      }
      if (!fragments.length) {
        appendTerminalLine("NO FRAGMENT LOCKS ARE PUBLISHED.", "term-red");
        appendTerminalLine("Type OPEN CONTROL to request emergency access.", "term-muted");
        return;
      }

      const parts = raw.split(/\s+/);
      let acceptedNow = 0;
      parts.forEach((part) => {
        const result = acceptFragment(part);
        if (result.status === "accepted") {
          acceptedNow += 1;
          appendTerminalLine(
            `FRAGMENT 0${result.fragment.slot} ACCEPTED / ${result.fragment.code}`,
            "term-green"
          );
        } else if (result.status === "already") {
          appendTerminalLine(
            `FRAGMENT 0${result.fragment.slot} ALREADY LOGGED / ${result.fragment.code}`,
            "term-muted"
          );
        } else if (result.status === "invalid") {
          appendTerminalLine(`FRAGMENT REJECTED / ${result.code}`, "term-red");
          appendTerminalLine(
            "That code is not recognised. Check the hidden record and try again.",
            "term-muted"
          );
        }
      });

      if (!acceptedNow && !parts.length) return;
      const remaining = missingFragments();
      reportFragmentProgress();
      if (!remaining.length) {
        appendTerminalLine("ACCESS KEY COMPLETE / 04 OF 04", "term-green");
        appendTerminalLine("TEMPORAL FIREWALL DISENGAGED. OPENING ARCHIVE CONTROL...", "term-green");
        setMissMinutes(
          "Well, would you look at that. Every piece accounted for. Access granted, sugar.",
          "success"
        );
        if (!controlOpening) {
          controlOpening = true;
          terminalLayer?.classList.add("is-granted");
          window.setTimeout(() => {
            terminalLayer?.classList.remove("is-granted");
            unlockControl({ scroll: true });
          }, prefersReducedMotion ? 0 : 1300);
        }
      } else if (acceptedNow) {
        appendTerminalLine(
          `NEXT TARGET / SLOT 0${remaining[0].slot} / ${remaining[0].section.toUpperCase()}`,
          "term-amber"
        );
        setMissMinutes(
          acceptedNow > 1
            ? "Two pieces at once. Aren't you efficient. Keep going, sugar."
            : "Well now, that's one more piece of the puzzle. The firewall felt that.",
          "success"
        );
      }
    },

    scan() {
      if (!fragments.length) {
        appendTerminalLine("SCAN COMPLETE / NO ACCESS FRAGMENTS PUBLISHED", "term-red");
        appendTerminalLine("OPEN CONTROL accepts an emergency request.", "term-muted");
        return;
      }
      appendTerminalLine("TEMPORAL SCAN / ACCESS FRAGMENT LOCATIONS", "term-green");
      fragments.forEach((fragment) => {
        const recovered = accessState.found.has(fragment.code);
        appendTerminalLine(
          `  SLOT 0${fragment.slot} / ${fragment.section.toUpperCase()} / ${fragment.title}`,
          recovered ? "term-muted" : "term-block"
        );
        appendTerminalLine(
          `    ${recovered ? `RECOVERED / ${fragment.code}` : "SIGNAL UNRECOVERED / OPEN THE HIDDEN RECORD"}`,
          recovered ? "term-green" : "term-amber"
        );
      });
      reportFragmentProgress("SCAN");
      setMissMinutes("Sweeping the timeline now. Mind the static, sugar.");
    },

    hint() {
      if (accessState.unlocked) {
        appendTerminalLine("THE CONTROL DOOR IS ALREADY OPEN.", "term-green");
        appendTerminalLine("Type OPEN CONTROL to return to the console.", "term-muted");
        return;
      }
      if (!fragments.length) {
        appendTerminalLine("NO FRAGMENTS TO HUNT. TYPE OPEN CONTROL.", "term-amber");
        return;
      }
      const missing = missingFragments();
      if (!missing.length) {
        appendTerminalLine("NO MISSING FRAGMENTS. TYPE OPEN CONTROL.", "term-green");
        return;
      }
      const next = missing[0];
      appendTerminalLine(
        `HINT / SLOT 0${next.slot} IS HIDDEN IN THE ${next.section.toUpperCase()} SECTION.`,
        "term-amber"
      );
      appendTerminalLine(`LOOK FOR / ${next.title}`, "term-block");
      appendTerminalLine(
        "Open that floating hidden-record node, read the fragment, then type UNLOCK <code>.",
        "term-muted"
      );
      setMissMinutes("Fine, I'll point. But you still have to do the walking.");
    },

    open(args) {
      const target = (args[0] || "").toLowerCase();
      if (target === "control" || target === "console" || target === "archive") {
        openControlFromTerminal();
        return;
      }
      appendTerminalLine("USAGE / OPEN CONTROL", "term-amber");
      appendTerminalLine(
        "That is the only door this terminal is allowed to open.",
        "term-muted"
      );
    },

    control() {
      openControlFromTerminal();
    },

    relock() {
      appendTerminalLine("RE-SEALING TEMPORAL FIREWALL...", "term-amber");
      appendTerminalLine("RECOVERED FRAGMENTS CLEARED / CONTROL DOOR SEALED", "term-red");
      setMissMinutes("Suit yourself. I'll put the firewall right back up.", "warning");
      controlOpening = false;
      relockControl();
    },

    miss() {
      const lines = [
        "I'm a clock, sugar. I know exactly how much time you're wasting.",
        "The archive remembers everything. Even the pages you thought you closed.",
        "If the timeline looks broken, try turning it off and on again. That's not official advice.",
        "Twelve ticks, two hands, and a front-row seat to every bad decision in history.",
      ];
      setMissMinutes(lines[Math.floor(Math.random() * lines.length)]);
      appendTerminalLine(
        "MISS MINUTES / \"I'm a clock, sugar. I'm always on time.\"",
        "term-amber"
      );
    },

    about() {
      const data = terminalSnapshot();
      if (!data) return;
      appendTerminalLine(`IDENTITY / ${data.identity.name || "ANNAMALAI"}`, "term-green");
      if (data.identity.role) appendTerminalLine(data.identity.role, "term-block");
      if (data.identity.tagline) appendTerminalLine(data.identity.tagline, "term-muted");
    },

    projects() {
      const data = terminalSnapshot();
      if (!data) return;
      if (!data.projects.length) {
        appendTerminalLine("NO PROJECT OBJECTS REGISTERED.", "term-muted");
        return;
      }
      data.projects.forEach((project, index) => {
        appendTerminalLine(
          `${pad(index + 1)}  ${project.title}${project.featured ? "  [FEATURED]" : ""}`,
          "term-green"
        );
        if (project.tagline) appendTerminalLine(`    ${project.tagline}`, "term-block");
        if (project.tech && project.tech.length) {
          appendTerminalLine(`    ${project.tech.join(" / ")}`, "term-muted");
        }
        if (project.url) appendTerminalLine(`    ${project.url}`, "term-muted");
      });
    },

    timeline() {
      const data = terminalSnapshot();
      if (!data) return;
      if (!data.achievements.length) {
        appendTerminalLine("NO TIMELINE COORDINATES LOADED.", "term-muted");
        return;
      }
      data.achievements.forEach((achievement, index) => {
        const suffix = [achievement.position, achievement.year]
          .filter(Boolean)
          .join(" / ");
        appendTerminalLine(
          `${pad(index + 1)}  ${achievement.title}${suffix ? ` — ${suffix}` : ""}`,
          "term-block"
        );
      });
    },

    teams() {
      const data = terminalSnapshot();
      if (!data) return;
      if (!data.organizations.length) {
        appendTerminalLine("NO ORGANIZATION RECORDS.", "term-muted");
        return;
      }
      data.organizations.forEach((organization, index) => {
        appendTerminalLine(
          `${pad(index + 1)}  ${organization.name}${organization.role ? ` / ${organization.role}` : ""}`,
          "term-block"
        );
      });
    },

    people() {
      const data = terminalSnapshot();
      if (!data) return;
      if (!data.collaborators.length) {
        appendTerminalLine("NO CONTACTS IN THE CONSTELLATION.", "term-muted");
        return;
      }
      data.collaborators.forEach((person, index) => {
        appendTerminalLine(`${pad(index + 1)}  ${person.name}`, "term-block");
        if (person.website) appendTerminalLine(`    ${person.website}`, "term-muted");
      });
    },

    gallery() {
      const data = terminalSnapshot();
      if (!data) return;
      appendTerminalLine(
        `VISUAL ARCHIVE / ${pad(data.gallery.image_count)} FRAMES INDEXED`,
        "term-green"
      );
      appendTerminalLine(
        data.gallery.categories.length
          ? `CHANNELS: ${data.gallery.categories.join(" / ")}`
          : "NO CHANNELS CONFIGURED.",
        "term-muted"
      );
    },

    stats() {
      const data = terminalSnapshot();
      if (!data) return;
      const stats = data.stats;
      appendTerminalLine("LIVE RECORD COUNTS", "term-green");
      appendTerminalLine(`  PROJECTS ........ ${pad(stats.projects)}`, "term-block");
      appendTerminalLine(`  ACHIEVEMENTS .... ${pad(stats.achievements)}`, "term-block");
      appendTerminalLine(`  ORGANIZATIONS ... ${pad(stats.organizations)}`, "term-block");
      appendTerminalLine(`  COLLABORATORS ... ${pad(stats.collaborators)}`, "term-block");
      appendTerminalLine(`  GALLERY FRAMES .. ${pad(stats.gallery_images)}`, "term-block");
      appendTerminalLine(
        `  ACCESS FRAGMENTS  ${pad(foundFragments().length)} / ${pad(fragments.length)}`,
        "term-muted"
      );
    },

    egg() {
      const data = terminalSnapshot();
      if (!data) return;
      appendTerminalLine("TERMINAL HANDSHAKE", "term-green");
      appendTerminalLine(
        data.handshake || "The handshake record is currently sealed.",
        "term-block"
      );
    },

    contact() {
      appendTerminalLine(
        "SIGNAL CHANNEL: scroll to section 08 or use the CONTACT form in the public archive.",
        "term-block"
      );
      appendTerminalLine("Stored privately. No third-party transport.", "term-muted");
    },

    whoami() {
      appendTerminalLine("VISITOR / FREQUENCY 07 / PUBLIC ACCESS", "term-green");
      appendTerminalLine(
        "The archive does not profile its visitors. Curiosity is the only credential.",
        "term-muted"
      );
    },

    date() {
      appendTerminalLine(`${clockTime()} / ${siteTimeZone}`, "term-block");
    },

    ls() {
      appendTerminalLine(
        "about/  achievements/  teams/  projects/  people/  gallery/  contact/  .hidden/",
        "term-block"
      );
    },

    clear() {
      if (terminalOutput) terminalOutput.replaceChildren();
    },

    exit() {
      appendTerminalLine("CLOSING CHANNEL...", "term-muted");
      window.setTimeout(() => closeOverlay(terminalLayer), 220);
    },

    sudo() {
      appendTerminalLine("Nice try. This archive only accepts curiosity.", "term-red");
      setMissMinutes("Oh, honey. No.", "warning");
    },
  };

  const terminalAliases = {
    h: "help",
    "?": "help",
    identity: "about",
    id: "about",
    project: "projects",
    orgs: "teams",
    organizations: "teams",
    collaborators: "people",
    frames: "gallery",
    secret: "egg",
    cls: "clear",
    close: "exit",
    quit: "exit",
    time: "date",
    dir: "ls",
    cat: "ls",
    codes: "fragments",
    code: "fragments",
    keys: "fragments",
    key: "fragments",
    access: "fragments",
    fragments: "fragments",
    opencontrol: "control",
    console: "control",
    archive: "control",
    seal: "relock",
    lock: "relock",
    minutes: "miss",
    mm: "miss",
  };

  const terminalQuips = {
    help: "Help's on the board, sugar. I only watch the clock.",
    about: "That's the person the archive belongs to. Try not to reorganise their timeline.",
    projects: "Objects. Projects. Same difference on this side of the archive.",
    timeline: "Every mark is a moment somebody decided to keep.",
    teams: "Teams are just timelines that decided to travel together.",
    people: "People are the only coordinates that really matter.",
    gallery: "Empty frames still count. They're just waiting for a memory.",
    stats: "Numbers are honest. Most of the time.",
    egg: "A handshake from the archive. It remembers you already.",
    contact: "Send a signal. Somebody out there is listening.",
    whoami: "A curious visitor. My favourite kind, most days.",
    date: "Time. My whole personality, really.",
    ls: "Everything looks tidier in a list, doesn't it?",
  };

  function runTerminalCommand(raw) {
    if (!terminalOutput) return;
    const input = String(raw || "").trim();
    if (!input) return;

    const [command, ...args] = input.split(/\s+/);
    const key = command.toLowerCase();
    if (key === "clear" || terminalAliases[key] === "clear") {
      terminalOutput.replaceChildren();
      return;
    }

    appendTerminalCommand(input);
    if (terminalHistory[terminalHistory.length - 1] !== input) {
      terminalHistory.push(input);
      if (terminalHistory.length > 40) terminalHistory.shift();
    }
    historyIndex = terminalHistory.length;

    const resolved = terminalCommands[key] ? key : terminalAliases[key];
    const handler = resolved ? terminalCommands[resolved] : null;
    if (!handler) {
      appendTerminalLine(
        `command not found: ${command}. Type HELP for available commands.`,
        "term-red"
      );
      setMissMinutes("That's not a command, sweetheart. Try HELP before you break something.", "warning");
      return;
    }
    if (terminalQuips[resolved]) {
      setMissMinutes(terminalQuips[resolved]);
    }
    handler(args);
  }

  function openTerminal() {
    if (!terminalLayer) return;
    if (!terminalStarted) {
      terminalStarted = true;
      appendTerminalLine("ANNAMALAI ARCHIVE // TEMPAD OS v7.2", "term-green");
      appendTerminalLine("TEMPORAL LINK: ESTABLISHED / PUBLIC FREQUENCY 07", "term-muted");
      if (fragments.length) {
        appendTerminalLine(
          `TEMPORAL FIREWALL: SEALED / ${pad(foundFragments().length)} OF ${pad(fragments.length)} FRAGMENTS RECOVERED`,
          "term-amber"
        );
        appendTerminalLine(
          foundFragments().length === fragments.length
            ? "ACCESS KEY COMPLETE / TYPE OPEN CONTROL"
            : "TYPE HELP, SCAN OR HINT / OR OPEN A HIDDEN RECORD TO FIND A CODE",
          "term-block"
        );
      } else {
        appendTerminalLine(
          "TEMPORAL FIREWALL: NO FRAGMENTS PUBLISHED / OPEN CONTROL ACCEPTS AN EMERGENCY REQUEST",
          "term-amber"
        );
      }
      appendTerminalLine(" ");
      loadArchiveSnapshot();
    }
    renderAccessState();
    const found = foundFragments().length;
    if (accessState.unlocked) {
      setMissMinutes(
        "There you are. The control room is already humming. Try not to press anything that unravels time."
      );
    } else if (!fragments.length) {
      setMissMinutes(
        "No key, no lock. If you ask nicely, the terminal might let you in anyway."
      );
    } else if (found === fragments.length) {
      setMissMinutes(
        "Every piece is accounted for, sugar. Type OPEN CONTROL and let's see what you do with it."
      );
    } else if (found) {
      setMissMinutes(
        `Back again? You've got ${found} of ${fragments.length} pieces. The timeline rewards persistence.`
      );
    } else {
      setMissMinutes(
        "Well, hello there. Four little pieces are hiding in the archive. Find them and bring them here."
      );
    }
    openOverlay(terminalLayer, terminalInput);
    window.setTimeout(() => terminalInput?.focus({ preventScroll: true }), 90);
  }

  function initTerminal() {
    if (!terminalLayer || !terminalForm || !terminalInput) return;

    $$("[data-terminal-open]").forEach((button) => {
      button.addEventListener("click", openTerminal);
    });

    $$("[data-terminal-run]").forEach((button) => {
      button.addEventListener("click", () => {
        openTerminal();
        const command = button.dataset.terminalRun || "help";
        window.setTimeout(() => runTerminalCommand(command), 180);
      });
    });

    $$("[data-secret-terminal]").forEach((button) => {
      button.addEventListener("click", openTerminal);
    });

    terminalForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const command = terminalInput.value;
      terminalInput.value = "";
      runTerminalCommand(command);
    });

    $$("[data-terminal-command]", terminalLayer).forEach((button) => {
      button.addEventListener("click", () => {
        runTerminalCommand(button.dataset.terminalCommand || "help");
        terminalInput.focus({ preventScroll: true });
      });
    });

    terminalInput.addEventListener("keydown", (event) => {
      if (event.key === "ArrowUp") {
        event.preventDefault();
        if (!terminalHistory.length) return;
        historyIndex = Math.max(0, historyIndex - 1);
        terminalInput.value = terminalHistory[historyIndex] || "";
        terminalInput.setSelectionRange(
          terminalInput.value.length,
          terminalInput.value.length
        );
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        if (!terminalHistory.length) return;
        historyIndex = Math.min(terminalHistory.length, historyIndex + 1);
        terminalInput.value = terminalHistory[historyIndex] || "";
      }
    });

    doc.addEventListener("keydown", (event) => {
      if (
        (event.ctrlKey || event.metaKey) &&
        event.shiftKey &&
        event.key.toLowerCase() === "a"
      ) {
        event.preventDefault();
        openTerminal();
      }
    });
  }

  /* -----------------------------------------------------------------------
     Gallery filters
     ----------------------------------------------------------------------- */
  const galleryFilters = $$("[data-gallery-filter]");
  const galleryItems = $$("[data-gallery-item]");
  let activeGalleryFilter = "all";

  function applyGalleryFilter(slug) {
    activeGalleryFilter = slug || "all";
    galleryFilters.forEach((button) => {
      const active = button.dataset.galleryFilter === activeGalleryFilter;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    galleryItems.forEach((item) => {
      const hidden =
        activeGalleryFilter !== "all" &&
        item.dataset.galleryCategory !== activeGalleryFilter;
      item.classList.toggle("is-filtered-out", hidden);
    });
  }

  function initGallery() {
    if (!galleryFilters.length) return;
    galleryFilters.forEach((button) => {
      button.addEventListener("click", () => {
        applyGalleryFilter(button.dataset.galleryFilter || "all");
      });
    });
  }

  /* -----------------------------------------------------------------------
     Fullscreen lightbox
     ----------------------------------------------------------------------- */
  const lightboxLayer = $("#lightbox");
  const lightboxImage = $("#lightbox-image");
  const lightboxCounter = $("#lightbox-counter");
  const lightboxCategory = $("#lightbox-category");
  const lightboxIndex = $("#lightbox-index");
  const lightboxTitle = $("#lightbox-title");
  const lightboxDescription = $("#lightbox-description");
  const lightboxPrev = $("#lightbox-prev");
  const lightboxNext = $("#lightbox-next");
  let visibleLightboxItems = [];
  let lightboxPosition = 0;

  function currentLightboxItems() {
    return galleryItems.filter(
      (item) => !item.classList.contains("is-filtered-out")
    );
  }

  function renderLightbox() {
    if (!lightboxLayer || !visibleLightboxItems.length) return;
    lightboxPosition =
      ((lightboxPosition % visibleLightboxItems.length) +
        visibleLightboxItems.length) %
      visibleLightboxItems.length;

    const item = visibleLightboxItems[lightboxPosition];
    const image = $("img", item);
    const caption = (item.dataset.caption || "").trim();
    const category = (item.dataset.category || "VISUAL ARCHIVE").trim();
    const description = (item.dataset.description || "").trim();
    const source = item.dataset.fullSrc || image?.currentSrc || image?.src || "";

    if (lightboxImage) {
      lightboxImage.src = source;
      lightboxImage.alt = caption
        ? `${caption} — ${category} photograph`
        : `${category} photograph`;
      lightboxImage.loading = "eager";
    }
    if (lightboxCounter) {
      lightboxCounter.textContent = `${pad(lightboxPosition + 1)} / ${pad(
        visibleLightboxItems.length
      )}`;
    }
    if (lightboxCategory) lightboxCategory.textContent = category;
    if (lightboxIndex) {
      lightboxIndex.textContent = `FRAME ${String(lightboxPosition + 1).padStart(
        3,
        "0"
      )}`;
    }
    if (lightboxTitle) lightboxTitle.textContent = caption || "Untitled frame";
    if (lightboxDescription) lightboxDescription.textContent = description;

    const single = visibleLightboxItems.length < 2;
    if (lightboxPrev) lightboxPrev.disabled = single;
    if (lightboxNext) lightboxNext.disabled = single;
  }

  function stepLightbox(direction) {
    if (visibleLightboxItems.length < 2) return;
    lightboxPosition += direction;
    renderLightbox();
  }

  function openLightbox(item) {
    if (!lightboxLayer) return;
    visibleLightboxItems = currentLightboxItems();
    lightboxPosition = Math.max(0, visibleLightboxItems.indexOf(item));
    renderLightbox();
    openOverlay(lightboxLayer, $(".lightbox", lightboxLayer));
  }

  function initLightbox() {
    if (!lightboxLayer || !galleryItems.length) return;

    galleryItems.forEach((item) => {
      item.addEventListener("click", () => openLightbox(item));
    });

    lightboxPrev?.addEventListener("click", () => stepLightbox(-1));
    lightboxNext?.addEventListener("click", () => stepLightbox(1));

    doc.addEventListener("keydown", (event) => {
      if (activeOverlay !== lightboxLayer) return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        stepLightbox(-1);
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        stepLightbox(1);
      }
    });
  }

  /* -----------------------------------------------------------------------
     Archive control system
     ----------------------------------------------------------------------- */
  function scrollToElement(element) {
    if (!element) return;
    element.scrollIntoView({ behavior: scrollBehavior(), block: "start" });
  }

  function initClocks() {
    const clocks = [
      ["#gate-clock", "TEMPAD GATE"],
      ["#control-clock", "ARCHIVE CONTROL SYSTEM"],
      ["#tempad-time", "TEMPAD LOCAL TIME"],
      ["#footer-clock", "ARCHIVE LOCAL TIME"],
    ]
      .map(([selector, label]) => {
        const element = $(selector);
        if (element) {
          element.setAttribute("title", `${label} / ${siteTimeZone}`);
          element.setAttribute("datetime", new Date().toISOString());
        }
        return element;
      })
      .filter(Boolean);

    if (!clocks.length) return;

    const updateClocks = () => {
      const now = new Date();
      const time = clockTime(now);
      clocks.forEach((clock) => {
        clock.textContent = time;
        clock.setAttribute("datetime", now.toISOString());
      });
    };

    updateClocks();
    window.setInterval(updateClocks, 1000);
  }

  function setMissMinutes(line, tone = "") {
    if (!mmLine) return;
    mmLine.textContent = line;
    const dialogue = mmLine.closest(".tempad-dialogue");
    if (dialogue) {
      dialogue.classList.remove("is-speaking");
      void dialogue.offsetWidth;
      dialogue.classList.add("is-speaking");
    }
    if (mmClock && (tone === "success" || tone === "warning")) {
      mmClock.classList.remove("is-alert");
      void mmClock.offsetWidth;
      mmClock.classList.add("is-alert");
      window.setTimeout(() => mmClock.classList.remove("is-alert"), 1400);
    }
  }

  function initMissMinutes() {
    if (!mmClock) return;
    const hourHand = $("[data-mm-hour]", mmClock);
    const minuteHand = $("[data-mm-minute]", mmClock);
    const secondHand = $("[data-mm-second]", mmClock);
    const pupils = $$("[data-mm-pupil]", mmClock);
    let pointerFrame = null;

    const timeParts = (date) => {
      try {
        const parts = new Intl.DateTimeFormat("en-GB", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: siteTimeZone,
        }).formatToParts(date);
        const result = {};
        parts.forEach((part) => {
          if (part.type !== "literal") result[part.type] = part.value;
        });
        return result;
      } catch (error) {
        return {
          hour: pad(date.getHours()),
          minute: pad(date.getMinutes()),
          second: pad(date.getSeconds()),
        };
      }
    };

    const updateHands = () => {
      const now = new Date();
      const parts = timeParts(now);
      const hours = (Number(parts.hour) || 0) % 12;
      const minutes = Number(parts.minute) || 0;
      const seconds = Number(parts.second) || 0;
      if (hourHand) {
        hourHand.style.transform = `rotate(${(hours + minutes / 60) * 30}deg)`;
      }
      if (minuteHand) {
        minuteHand.style.transform = `rotate(${(minutes + seconds / 60) * 6}deg)`;
      }
      if (secondHand) {
        secondHand.style.transform = `rotate(${seconds * 6}deg)`;
      }
    };

    updateHands();
    window.setInterval(updateHands, 1000);

    if (!pupils.length || !("PointerEvent" in window)) return;
    doc.addEventListener(
      "pointermove",
      (event) => {
        if (activeOverlay !== terminalLayer || pointerFrame) return;
        pointerFrame = window.requestAnimationFrame(() => {
          pointerFrame = null;
          pupils.forEach((pupil) => {
            const eye = pupil.parentElement;
            if (!eye) return;
            const rect = eye.getBoundingClientRect();
            if (!rect.width) return;
            const dx = Math.max(
              -2.4,
              Math.min(2.4, (event.clientX - (rect.left + rect.width / 2)) / 22)
            );
            const dy = Math.max(
              -2.4,
              Math.min(2.4, (event.clientY - (rect.top + rect.height / 2)) / 22)
            );
            pupil.style.transform = `translate(${dx}px, ${dy}px)`;
          });
        });
      },
      { passive: true }
    );
  }

  function initControlSystem() {
    const achievementNodes = $$("[data-control-achievement]");
    const titleNode = $("#control-achievement-title");
    const positionNode = $("#control-achievement-position");
    const indexNode = $("#control-achievement-index");
    const dots = $$("[data-timeline-dots] span");
    const previous = $("[data-timeline-prev]");
    const next = $("[data-timeline-next]");
    let achievementIndex = 0;
    let achievementTimer = null;

    const renderAchievement = () => {
      if (!achievementNodes.length) return;
      achievementIndex =
        ((achievementIndex % achievementNodes.length) + achievementNodes.length) %
        achievementNodes.length;
      const item = achievementNodes[achievementIndex];
      const position = (item.dataset.position || "").trim();
      const year = (item.dataset.year || "").trim();
      const suffix = [position, year].filter(Boolean).join(" / ");

      if (titleNode) {
        titleNode.textContent = item.dataset.title || "UNRECORDED COORDINATE";
      }
      if (positionNode) {
        positionNode.textContent = suffix || "COORDINATE / UNRECORDED";
      }
      if (indexNode) {
        indexNode.textContent = `${pad(achievementIndex + 1)} / ${pad(
          achievementNodes.length
        )}`;
      }
      dots.forEach((dot, index) => {
        dot.classList.toggle("is-active", index === achievementIndex);
      });
    };

    const scheduleAchievements = () => {
      if (achievementTimer) window.clearInterval(achievementTimer);
      if (achievementNodes.length < 2 || prefersReducedMotion) return;
      achievementTimer = window.setInterval(() => {
        if (doc.hidden) return;
        achievementIndex += 1;
        renderAchievement();
      }, 5200);
    };

    if (achievementNodes.length) {
      renderAchievement();
      scheduleAchievements();
    }

    previous?.addEventListener("click", () => {
      achievementIndex -= 1;
      renderAchievement();
      scheduleAchievements();
    });

    next?.addEventListener("click", () => {
      achievementIndex += 1;
      renderAchievement();
      scheduleAchievements();
    });

    $$("[data-project-jump]").forEach((button) => {
      button.addEventListener("click", () => {
        const target = doc.getElementById(button.dataset.projectJump || "");
        if (!target) return;
        scrollToElement(target);
        if (animationsEnabled && typeof target.animate === "function") {
          target.animate(
            [
              { boxShadow: "0 0 0 1px rgba(177, 231, 190, 0.9)" },
              { boxShadow: "0 0 0 14px rgba(177, 231, 190, 0)" },
            ],
            { duration: 1800, easing: "ease-out" }
          );
        }
      });
    });

    $$("[data-gallery-jump]").forEach((button) => {
      button.addEventListener("click", () => {
        const slug = button.dataset.galleryJump || "all";
        scrollToElement(doc.getElementById("gallery"));
        const filter = galleryFilters.find(
          (candidate) =>
            candidate.dataset.galleryFilter === slug &&
            candidate.dataset.galleryFilter !== "all"
        );
        window.setTimeout(
          () => applyGalleryFilter(filter ? slug : "all"),
          animationsEnabled ? 420 : 0
        );
      });
    });

    $$("[data-scroll-home]").forEach((button) => {
      button.addEventListener("click", () => {
        window.scrollTo({ top: 0, behavior: scrollBehavior() });
        const home = doc.getElementById("home");
        if (home) home.focus({ preventScroll: true });
      });
    });

    const recalibrate = $("[data-recalibrate]");
    const integrity = $("#control-integrity");
    const calibration = $("#control-last-calibration");
    recalibrate?.addEventListener("click", async () => {
      if (recalibrate.disabled) return;
      recalibrate.disabled = true;
      if (integrity) integrity.textContent = "SYNCING";
      try {
        const response = await fetch("/healthz", {
          credentials: "same-origin",
          cache: "no-store",
          headers: { Accept: "application/json" },
        });
        const payload = await response.json();
        if (!response.ok || payload.status !== "online") {
          throw new Error("Archive fault");
        }
        if (integrity) integrity.textContent = "100.0%";
        if (calibration) calibration.textContent = `SYNC / ${clockTime()}`;
      } catch (error) {
        if (integrity) integrity.textContent = "FAULT";
        if (calibration) {
          calibration.textContent = `SYNC / ${clockTime()} / OFFLINE`;
        }
      } finally {
        window.setTimeout(() => {
          recalibrate.disabled = false;
        }, 700);
      }
    });

    renderAccessState();
    syncControlVisibility();
  }

  /* -----------------------------------------------------------------------
     Reveals, hero entrance and timeline line
     ----------------------------------------------------------------------- */
  function startHeroAnimation() {
    if (!animationsEnabled || !window.gsap) return;
    const title = $("[data-hero-title]");
    if (!title) return;

    const run = () => {
      const timeline = window.gsap.timeline({
        defaults: { ease: "power3.out" },
      });
      timeline
        .from(
          "[data-hero-title] .hero__name-text",
          { yPercent: 115, opacity: 0, duration: 1.1 },
          0
        )
        .from(
          "[data-hero-title] .hero__name-echo",
          { opacity: 0, xPercent: 6, duration: 1.2 },
          0.15
        )
        .from(
          "[data-hero-object]",
          { opacity: 0, scale: 0.92, duration: 1.3 },
          0.15
        )
        .from(
          "[data-hero-reveal]",
          { opacity: 0, y: 22, duration: 0.85, stagger: 0.1 },
          0.1
        );
    };

    if ($("#boot-screen")) {
      window.setTimeout(run, 2050);
    } else {
      run();
    }
  }

  function markTimelineVisible() {
    $$(".timeline-shell").forEach((shell) => shell.classList.add("is-visible"));
  }

  function initReveals() {
    if (!animationsEnabled) {
      markTimelineVisible();
      return;
    }

    let gsapReady = false;
    try {
      gsapReady = Boolean(window.gsap && window.ScrollTrigger);
      if (gsapReady) {
        window.gsap.registerPlugin(window.ScrollTrigger);
      }
    } catch (error) {
      gsapReady = false;
    }

    if (gsapReady) {
      const revealElements = $$("[data-reveal]");
      revealElements.forEach((element) => {
        window.gsap.fromTo(
          element,
          { autoAlpha: 0, y: 26 },
          {
            autoAlpha: 1,
            y: 0,
            duration: 0.9,
            ease: "power3.out",
            scrollTrigger: {
              trigger: element,
              start: "top 88%",
              once: true,
            },
          }
        );
      });

      startHeroAnimation();
      window.addEventListener("load", () => window.ScrollTrigger.refresh());
    } else {
      const revealElements = $$("[data-reveal]");
      if ("IntersectionObserver" in window) {
        revealElements.forEach((element) => element.classList.add("will-reveal"));
        const revealObserver = new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (!entry.isIntersecting) return;
              entry.target.classList.add("reveal-done");
              revealObserver.unobserve(entry.target);
            });
          },
          { rootMargin: "0px 0px -10% 0px", threshold: 0.01 }
        );
        revealElements.forEach((element) => revealObserver.observe(element));
      } else {
        revealElements.forEach((element) => element.classList.add("reveal-done"));
      }
    }

    const timelineShells = $$(".timeline-shell");
    if (!timelineShells.length) return;
    if ("IntersectionObserver" in window) {
      const timelineObserver = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return;
            entry.target.classList.add("is-visible");
            timelineObserver.unobserve(entry.target);
          });
        },
        { rootMargin: "0px 0px -14% 0px", threshold: 0.01 }
      );
      timelineShells.forEach((shell) => timelineObserver.observe(shell));
    } else {
      markTimelineVisible();
    }
  }

  /* -----------------------------------------------------------------------
     Global keyboard handling for menu, overlays and lightbox
     ----------------------------------------------------------------------- */
  function initKeyboardHandling() {
    doc.addEventListener("keydown", (event) => {
      if (menuOpen) {
        if (event.key === "Escape") {
          event.preventDefault();
          closeMenu();
          return;
        }
        if (event.key === "Tab" && mobileMenu) {
          const panel = $(".mobile-menu__panel", mobileMenu);
          if (panel) trapFocus(event, panel);
        }
        return;
      }

      if (!activeOverlay) return;

      if (event.key === "Escape") {
        event.preventDefault();
        closeOverlay(activeOverlay);
        return;
      }

      if (event.key === "Tab") {
        trapFocus(event, activeOverlay);
      }
    });
  }

  /* -----------------------------------------------------------------------
     Boot all systems
     ----------------------------------------------------------------------- */
  document.addEventListener("DOMContentLoaded", () => {
    initBoot();
    initNavigation();
    initFocusMode();
    initToasts();
    initSecretRecords();
    initTerminal();
    initGallery();
    initLightbox();
    initClocks();
    initMissMinutes();
    initControlSystem();
    initKeyboardHandling();
    initReveals();
  });
})();
