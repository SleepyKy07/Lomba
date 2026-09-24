/** Tahap 4: banding beberapa lomba. */
(function () {
  "use strict";

  async function loadPilih() {
    var box = document.getElementById("pilih-box");
    if (!TPage.guardOrCta("Login diperlukan untuk membanding lomba.")) {
      box.innerHTML = "";
      return;
    }
    try {
      var rows = await TApi.listTournaments();
      if (!rows || !rows.length) {
        box.innerHTML = '<span class="empty">Belum ada lomba.</span>';
        return;
      }
      box.innerHTML = rows
        .map(function (t) {
          return (
            "<label><input type='checkbox' name='ids' value='" +
            TUI.esc(t.id) +
            "'> " +
            TUI.esc(t.id) +
            " — " +
            TUI.esc(t.name) +
            "</label> "
          );
        })
        .join("");
    } catch (e) {
      box.innerHTML = '<span class="empty">Gagal memuat lomba.</span>';
      if (!TUI.onAuthError(e)) TUI.showError(e, "Banding");
    }
  }

  async function onRun() {
    TUI.clearMessages();
    var ids = Array.prototype.map.call(
      document.querySelectorAll("#pilih-box input:checked"),
      function (el) {
        return el.value;
      }
    );
    if (!ids.length) {
      TUI.showError(new Error("Pilih minimal 1 lomba."), "Banding");
      return;
    }
    TPage.showEngine("Ambil data + banding…", false);
    try {
      var rows = [];
      for (var i = 0; i < ids.length; i++) {
        var r = await TApi.getTournament(ids[i]);
        if (r && r[0]) rows.push(r[0]);
      }
      var out = await TEngine.banding(rows);
      document.getElementById("hasil-card").hidden = false;
      document.getElementById("out-banding").textContent = out.comparison || "";
      TPage.showEngine("");
    } catch (e) {
      TPage.showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Banding");
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadPilih();
    document.getElementById("btn-banding").addEventListener("click", onRun);
  });
})();
