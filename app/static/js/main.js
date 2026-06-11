/* Semantic Platform — UI behaviour.
   Vanilla JS, no dependencies. Every feature is independently guarded so a
   missing element can never break the others. */
(function () {
  "use strict";

  var root = document.documentElement;

  /* ---- Theme toggle (light / dark, persisted, respects system default) ---- */
  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function storedTheme() {
    try { return localStorage.getItem("theme"); } catch (e) { return null; }
  }
  function effectiveTheme() {
    return root.getAttribute("data-theme") || (systemPrefersDark() ? "dark" : "light");
  }
  function applyTheme(theme) {
    if (theme === "light" || theme === "dark") {
      root.setAttribute("data-theme", theme);
      try { localStorage.setItem("theme", theme); } catch (e) {}
    }
    syncToggle();
  }
  function syncToggle() {
    var btn = document.querySelector(".theme-toggle");
    if (!btn) return;
    var dark = effectiveTheme() === "dark";
    btn.setAttribute("aria-pressed", dark ? "true" : "false");
    var icon = btn.querySelector(".theme-toggle__icon");
    if (icon) icon.textContent = dark ? "☀" : "☾";
  }
  function initTheme() {
    var btn = document.querySelector(".theme-toggle");
    syncToggle();
    if (btn) {
      btn.addEventListener("click", function () {
        applyTheme(effectiveTheme() === "dark" ? "light" : "dark");
      });
    }
    // Keep the icon in sync when following the system and the OS theme changes.
    if (window.matchMedia) {
      var mq = window.matchMedia("(prefers-color-scheme: dark)");
      var onChange = function () { if (!storedTheme()) syncToggle(); };
      if (mq.addEventListener) mq.addEventListener("change", onChange);
      else if (mq.addListener) mq.addListener(onChange);
    }
  }

  /* ---- Sidebar / mobile drawer ---- */
  function initSidebar() {
    var app = document.querySelector(".app");
    var toggle = document.querySelector(".nav-toggle");
    var backdrop = document.querySelector(".sidebar-backdrop");
    if (!app || !toggle) return;

    function setOpen(open) {
      app.setAttribute("data-sidebar", open ? "open" : "expanded");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      if (backdrop) backdrop.hidden = !open;
    }
    toggle.addEventListener("click", function () {
      setOpen(app.getAttribute("data-sidebar") !== "open");
    });
    if (backdrop) backdrop.addEventListener("click", function () { setOpen(false); });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && app.getAttribute("data-sidebar") === "open") {
        setOpen(false);
        toggle.focus();
      }
    });
    // Close the drawer after following a link on mobile.
    var nav = app.querySelector(".sidebar nav");
    if (nav) {
      nav.addEventListener("click", function (e) {
        if (e.target.closest(".nav-link") && app.getAttribute("data-sidebar") === "open") {
          setOpen(false);
        }
      });
    }
  }

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }
  ready(function () {
    initTheme();
    initSidebar();
  });
})();
