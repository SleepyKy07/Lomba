/** Halaman login / daftar — Supabase Auth email+password. */
(function (global) {
  "use strict";

  function nextTarget() {
    return TUI.qs("next") || "index.html";
  }

  function bindMode() {
    var mode = TUI.qs("mode") === "daftar" ? "daftar" : "masuk";
    var title = document.getElementById("auth-title");
    var submit = document.getElementById("btn-submit");
    var link = document.getElementById("auth-switch");
    var hint = document.getElementById("auth-hint");
    if (mode === "daftar") {
      if (title) title.textContent = "Daftar akun panitia";
      if (submit) submit.textContent = "Daftar";
      if (link)
        link.innerHTML =
          'Sudah punya akun? <a href="login.html">Masuk</a>';
      if (hint)
        hint.textContent =
          "Buat akun email panitia. Konfirmasi email dimatikan di proyek demo.";
    } else {
      if (title) title.textContent = "Masuk";
      if (submit) submit.textContent = "Masuk";
      if (link)
        link.innerHTML =
          'Belum punya akun? <a href="login.html?mode=daftar">Daftar</a>';
      if (hint)
        hint.textContent =
          "Wajib login: RLS menolak akses anon setelah Tahap 2.";
    }
    return mode;
  }

  async function onSubmit(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    var email = document.getElementById("fld-email").value.trim();
    var pass = document.getElementById("fld-pass").value;
    if (!email || !pass) {
      TUI.showError(new Error("Email & password wajib diisi."), "Auth");
      return;
    }
    var btn = document.getElementById("btn-submit");
    if (btn) btn.disabled = true;
    try {
      var mode = bindMode();
      if (mode === "daftar") {
        await TAuth.signUp(email, pass);
        if (!TAuth.isLoggedIn()) {
          TUI.showFlash(
            "Akun dibuat. Cek email bila diminta konfirmasi, lalu masuk."
          );
          global.location.href = "login.html?next=" +
            encodeURIComponent(nextTarget()) +
            "&msg=" +
            encodeURIComponent("Akun dibuat. Silakan masuk.");
          return;
        }
      } else {
        await TAuth.signIn(email, pass);
      }
      global.location.href =
        nextTarget() +
        (nextTarget().indexOf("?") >= 0 ? "&" : "?") +
        "msg=" +
        encodeURIComponent("Berhasil masuk.");
    } catch (e) {
      TUI.showError(e, "Auth");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (TAuth.isLoggedIn() && TUI.qs("mode") !== "daftar") {
      global.location.href = nextTarget();
      return;
    }
    bindMode();
    var form = document.getElementById("form-login");
    if (form) form.addEventListener("submit", onSubmit);
  });
})(window);
