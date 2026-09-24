/** Beranda: stats publik (tanpa login). */
(function () {
  "use strict";

  function setStat(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = String(val);
  }

  async function loadStats() {
    try {
      setStat("stat-user", "publik");

      if (!TApi.isConfigured()) {
        setStat("stat-kelas", "-");
        setStat("stat-lomba", "-");
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
          new Error("Server menolak akses. Jalankan 0003_public_demo.sql (mode publik)."),
          "Beranda"
        );
      } else {
        TUI.showError(e, "Stat beranda");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", loadStats);
})();
