/** Beranda: stats + indikator login. */
(function () {
  "use strict";

  function setStat(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = String(val);
  }

  async function loadStats() {
    try {
      var u = TAuth.isLoggedIn() ? TAuth.getUser() : null;
      setStat("stat-user", u && u.email ? u.email : "belum masuk");

      if (!TApi.isConfigured()) {
        setStat("stat-kelas", "-");
        setStat("stat-lomba", "-");
        return;
      }
      if (!TAuth.isLoggedIn()) {
        setStat("stat-kelas", "login?");
        setStat("stat-lomba", "login?");
        return;
      }

      var classes = await TApi.listClasses();
      setStat("stat-kelas", (classes || []).length);

      try {
        var lomba = await TApi.listTournaments();
        setStat("stat-lomba", (lomba || []).length);
      } catch (e2) {
        setStat("stat-lomba", "-");
        console.warn("Stat lomba:", e2);
      }
    } catch (e) {
      setStat("stat-kelas", "-");
      if (e && (e.status === 401 || e.status === 403)) {
        TUI.showError(
          new Error("Belum login / RLS menolak. Buka Masuk."),
          "Beranda"
        );
      } else {
        TUI.showError(e, "Stat beranda");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", loadStats);
})();
