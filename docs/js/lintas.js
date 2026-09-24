/** Tahap 4: deteksi bentrok lintas lomba + optimasi multi-lomba. */
(function () {
  "use strict";

  async function loadRows() {
    var box = document.getElementById("pilih-box");
    if (!TPage.guardOrCta("Login diperlukan untuk fitur lintas lomba.")) {
      box.innerHTML = "";
      return [];
    }
    try {
      var list = await TApi.listTournaments();
      if (!list || !list.length) {
        box.innerHTML = '<span class="empty">Belum ada lomba.</span>';
        return [];
      }
      box.innerHTML = list
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
      var full = [];
      for (var i = 0; i < list.length; i++) {
        var rows = await TApi.getTournament(list[i].id);
        if (rows && rows[0]) full.push(rows[0]);
      }
      return full;
    } catch (e) {
      box.innerHTML = '<span class="empty">Gagal memuat lomba.</span>';
      if (!TUI.onAuthError(e)) TUI.showError(e, "Lintas");
      return [];
    }
  }

  function selectedIds() {
    return Array.prototype.map.call(
      document.querySelectorAll("#pilih-box input:checked"),
      function (el) {
        return el.value;
      }
    );
  }

  function filterSelected(all) {
    var ids = selectedIds();
    return all.filter(function (r) {
      return ids.indexOf(r.id) >= 0;
    });
  }

  function renderFindings(host, findings) {
    if (!findings || !findings.length) {
      host.innerHTML =
        '<div class="flash">Tidak ada bentrok lintas lomba terdeteksi.</div>';
      return;
    }
    host.innerHTML = findings
      .map(function (f) {
        return "<div class='err'>" + TUI.esc(f) + "</div>";
      })
      .join("");
  }

  async function onLintas(all) {
    TUI.clearMessages();
    var rows = filterSelected(all);
    if (rows.length < 2) {
      TUI.showError(new Error("Pilih minimal 2 lomba."), "Lintas");
      return;
    }
    TPage.showEngine("Deteksi bentrok lintas lomba…", false);
    try {
      var out = await TEngine.lintas(rows);
      document.getElementById("hasil-lintas").hidden = false;
      renderFindings(document.getElementById("out-lintas"), out.findings);
      document.getElementById("out-load").textContent =
        out.total_load || "(kosong)";
      TPage.showEngine("");
    } catch (e) {
      TPage.showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Lintas");
    }
  }

  async function onOptimasi(all) {
    TUI.clearMessages();
    var rows = filterSelected(all);
    if (rows.length < 1) {
      TUI.showError(new Error("Pilih minimal 1 lomba."), "Optimasi");
      return;
    }
    var maxB = parseInt(document.getElementById("opt-max").value, 10);
    if (isNaN(maxB) || maxB < 0) maxB = 12;
    TPage.showEngine("Optimasi multi-lomba (bisa ~detik)…", false);
    try {
      var out = await TEngine.optimasi(rows, maxB);
      document.getElementById("hasil-opt").hidden = false;
      var notesHost = document.getElementById("out-opt-notes");
      notesHost.innerHTML =
        "<ul>" +
        (out.notes || [])
          .map(function (n) {
            return "<li>" + TUI.esc(n) + "</li>";
          })
          .join("") +
        "</ul>";
      renderFindings(document.getElementById("out-opt-left"), out.left);
      document.getElementById("out-opt-summ").textContent = (
        out.summaries || []
      )
        .map(function (s, i) {
          return (
            (out.labels && out.labels[i] ? out.labels[i] : "#" + i) +
            ": " +
            JSON.stringify(s)
          );
        })
        .join("\n");
      TPage.showEngine("");
      TUI.showFlash(
        "Optimasi selesai (preview — jadwal hasil tidak disimpan ke Supabase otomatis)."
      );
    } catch (e) {
      TPage.showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Optimasi");
    }
  }

  document.addEventListener("DOMContentLoaded", async function () {
    var all = await loadRows();
    document.getElementById("btn-lintas").addEventListener("click", function () {
      onLintas(all);
    });
    document
      .getElementById("btn-optimasi")
      .addEventListener("click", function () {
        onOptimasi(all);
      });
  });
})();
