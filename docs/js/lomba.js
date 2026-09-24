/** Tahap 3: daftar + buat lomba (generate via Pyodide, simpan ke Supabase). */
(function () {
  "use strict";

  var pesertaLoaded = false;

  function showLoginCta(msg) {
    var cta = document.getElementById("login-cta");
    var card = document.getElementById("buat-card");
    if (card) card.hidden = true;
    if (!cta) return;
    cta.hidden = false;
    cta.innerHTML =
      TUI.esc(msg) +
      ' <a class="btn" href="login.html?next=lomba.html">Masuk</a>';
  }

  function setEngineStatus(msg, isErr) {
    var el = document.getElementById("engine-status");
    if (!el) return;
    if (!msg) {
      el.hidden = true;
      return;
    }
    el.hidden = false;
    el.textContent = msg;
    if (isErr) {
      el.style.background = "#fef2f2";
      el.style.borderColor = "#fca5a5";
      el.style.color = "#991b1b";
    } else {
      el.style.background = "#eff6ff";
      el.style.borderColor = "#bfdbfe";
      el.style.color = "#1e40af";
    }
  }

  async function loadPeserta() {
    var box = document.getElementById("peserta-box");
    try {
      var rows = await TApi.listClasses();
      if (!rows || !rows.length) {
        box.innerHTML =
          '<span class="empty">Belum ada kelas — tambah di Master Kelas dulu.</span>';
        return;
      }
      box.innerHTML = rows
        .map(function (c) {
          return (
            "<label><input type='checkbox' name='peserta' value='" +
            TUI.esc(c.id) +
            "' checked> " +
            TUI.esc(c.id) +
            "</label> "
          );
        })
        .join("");
      pesertaLoaded = true;
    } catch (e) {
      box.innerHTML = '<span class="empty">Gagal memuat kelas (login / RLS).</span>';
      if (!TUI.onAuthError(e)) TUI.showError(e, "Peserta");
    }
  }

  async function loadList() {
    var el = document.getElementById("lomba-list");
    try {
      var rows = await TApi.listTournaments();
      if (!rows || !rows.length) {
        el.innerHTML = '<div class="empty">Belum ada lomba.</div>';
        return;
      }
      el.innerHTML =
        "<table><tr><th>ID</th><th>Nama</th><th>Format</th><th>Peserta</th></tr>" +
        rows
          .map(function (t) {
            var n =
              t.participant_ids && t.participant_ids.length
                ? t.participant_ids.length
                : 0;
            return (
              "<tr><td><a href='lomba_detail.html?id=" +
              encodeURIComponent(t.id) +
              "'><code>" +
              TUI.esc(t.id) +
              "</code></a></td><td>" +
              TUI.esc(t.name) +
              "</td><td>" +
              TUI.esc(t.format) +
              "</td><td>" +
              n +
              "</td></tr>"
            );
          })
          .join("") +
        "</table>";
    } catch (e) {
      if (e && (e.status === 401 || e.status === 403)) {
        el.innerHTML = '<div class="empty">Butuh login untuk melihat lomba.</div>';
        showLoginCta("RLS menolak akses anon.");
        return;
      }
      el.innerHTML = '<div class="empty">Gagal memuat lomba.</div>';
      if (!TUI.onAuthError(e)) TUI.showError(e, "Daftar lomba");
    }
  }

  function intVal(id, fallback) {
    var v = document.getElementById(id).value;
    if (v === "" || v == null) return fallback;
    var n = parseInt(v, 10);
    return isNaN(n) ? fallback : n;
  }

  async function onCreate(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    if (!TUI.guardAuth("lomba.html")) return;

    var ids = Array.prototype.map
      .call(document.querySelectorAll("#peserta-box input:checked"), function (el) {
        return el.value;
      });
    ids = ids.filter(function (v, i, a) {
      return a.indexOf(v) === i;
    });
    if (!ids.length) {
      TUI.showError(new Error("Pilih minimal 1 peserta."), "Buat lomba");
      return;
    }

    var ngRaw = document.getElementById("fld-groups").value;
    var numGroups = ngRaw === "" ? null : intVal("fld-groups", null);

    var btn = document.getElementById("btn-buat");
    btn.disabled = true;
    setEngineStatus("Menyiapkan engine Python (Pyodide)… pertama kali bisa ~10–30 dtk.", false);
    try {
      var lid = await TApi.nextLombaId();
      var row = {
        id: lid,
        name: document.getElementById("fld-nama").value.trim() || "Lomba",
        format: document.getElementById("fld-format").value,
        team_size: intVal("fld-team", 4),
        winner_count: intVal("fld-winners", 1),
        duration_min: intVal("fld-dur", 30),
        minimum_rest_min: intVal("fld-rest", 10),
        arena_count: intVal("fld-arena", 2),
        qualify_per_group: intVal("fld-qualify", 1),
        start_time: document.getElementById("fld-start").value || "08:00",
        end_time: document.getElementById("fld-end").value || "17:00",
        date: document.getElementById("fld-date").value || "",
        participant_ids: ids,
        num_groups: numGroups,
      };

      setEngineStatus("Generate bracket + jadwal + fairness…", false);
      var report = await TEngine.createReport(row);

      var saveRow = {
        id: row.id,
        name: row.name,
        format: row.format,
        team_size: row.team_size,
        winner_count: row.winner_count,
        duration_min: row.duration_min,
        minimum_rest_min: row.minimum_rest_min,
        arena_count: row.arena_count,
        qualify_per_group: row.qualify_per_group,
        start_time: row.start_time,
        end_time: row.end_time,
        date: row.date,
        participant_ids: row.participant_ids,
        manual_scheme: report.scheme,
        manual_scheduled: report.scheduled,
      };
      if (global.TAuth && TAuth.getUser()) {
        saveRow.owner_id = TAuth.getUser().id;
      }

      setEngineStatus("Menyimpan ke Supabase…", false);
      await TApi.createTournament(saveRow);
      setEngineStatus("");
      global.location.href =
        "lomba_detail.html?id=" +
        encodeURIComponent(lid) +
        "&msg=" +
        encodeURIComponent("Lomba " + lid + " dibuat + skema di-generate.");
    } catch (e) {
      setEngineStatus("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Buat lomba");
      btn.disabled = false;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (TAuth.isLoggedIn()) {
      var card = document.getElementById("buat-card");
      if (card) card.hidden = false;
    } else {
      showLoginCta("Login diperlukan untuk melihat & membuat lomba.");
    }
    var form = document.getElementById("form-buat");
    if (form) form.addEventListener("submit", onCreate);
    loadPeserta();
    loadList();
    // hangatkan engine di latar (opsional, non-blocking)
    if (TAuth.isLoggedIn() && TEngine.ensureReady) {
      TEngine.ensureReady().then(
        function () {
          setEngineStatus("Engine Python siap.");
          setTimeout(function () {
            setEngineStatus("");
          }, 2000);
        },
        function () {
          /* biarkan; error muncul saat buat lomba */
        }
      );
    }
  });
})();
