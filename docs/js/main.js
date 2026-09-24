/** util UI bersama: escape, flash, error, nav aktif, auth topbar */
(function (global) {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function qs(name) {
    return new URLSearchParams(global.location.search).get(name);
  }

  function showFlash(msg) {
    if (!msg) return;
    var el = document.getElementById("flash");
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
  }

  function showError(err, where) {
    var el = document.getElementById("err");
    if (!el) {
      if (global.console && console.error) console.error(where || "error", err);
      return;
    }
    var msg = err && err.message ? err.message : String(err);
    el.textContent = (where ? where + ": " : "") + msg;
    el.hidden = false;
    if (global.console && console.error) {
      console.error(where || "error", err);
    }
  }

  function clearMessages() {
    var f = document.getElementById("flash");
    var e = document.getElementById("err");
    if (f) {
      f.hidden = true;
      f.textContent = "";
    }
    if (e) {
      e.hidden = true;
      e.textContent = "";
    }
  }

  function markActiveNav() {
    var path = global.location.pathname.split("/").pop() || "index.html";
    if (path === "" || path === "/") path = "index.html";
    document.querySelectorAll(".topnav a").forEach(function (a) {
      var href = (a.getAttribute("href") || "").split("/").pop();
      if (href === path || (path === "index.html" && href === "index.html")) {
        a.classList.add("active");
      }
    });
  }

  function ensureConfigBanner() {
    if (global.TApi && !global.TApi.isConfigured()) {
      var el = document.getElementById("cfg-banner");
      if (el) el.hidden = false;
    }
  }

  function bootFlash() {
    showFlash(qs("msg"));
  }

  function renderAuthSlot() {
    var slot = document.getElementById("auth-slot");
    if (!slot) return;
    slot.hidden = true;
    slot.innerHTML = "";
  }

  function guardAuth(redirectNext) {
    return true;
  }

  function onAuthError(err) {
    if (err && (err.status === 401 || err.status === 403)) {
      showError(
        new Error("Server menolak akses. Cek RLS / jalankan 0003_public_demo.sql."),
        "Auth"
      );
      return true;
    }
    return false;
  }

  global.TUI = {
    esc: esc,
    qs: qs,
    showFlash: showFlash,
    showError: showError,
    clearMessages: clearMessages,
    markActiveNav: markActiveNav,
    ensureConfigBanner: ensureConfigBanner,
    bootFlash: bootFlash,
    renderAuthSlot: renderAuthSlot,
    guardAuth: guardAuth,
    onAuthError: onAuthError,
  };

  document.addEventListener("DOMContentLoaded", function () {
    markActiveNav();
    ensureConfigBanner();
    bootFlash();
    renderAuthSlot();
  });
})(window);
