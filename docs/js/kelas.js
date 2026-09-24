/** Fitur Master Kelas — wajib login (Tahap 2 RLS). */
(function (global) {
  "use strict";

  var tbody;
  var locked = false;

  function setCount(n) {
    var el = document.getElementById("kelas-count");
    if (el) el.textContent = String(n);
  }

  function setMutateEnabled(on) {
    var form = document.getElementById("form-tambah");
    var wrap = document.getElementById("mutate-card");
    if (form) {
      form.querySelectorAll("input, button").forEach(function (el) {
        el.disabled = !on;
      });
    }
    if (wrap) wrap.hidden = !on;
    locked = !on;
  }

  function showLoginCta(msg) {
    setMutateEnabled(false);
    var cta = document.getElementById("login-cta");
    if (!cta) return;
    cta.hidden = false;
    cta.innerHTML =
      TUI.esc(msg || "Login diperlukan untuk tambah/hapus kelas.") +
      ' <a class="btn" href="login.html?next=kelas.html">Masuk</a>';
  }

  function renderRows(rows) {
    setCount(rows.length);
    if (!rows || !rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="empty">Belum ada kelas.</td></tr>';
      return;
    }
    var canMutate = TAuth.isLoggedIn();
    var html = rows
      .map(function (c) {
        var del = canMutate
          ? '<button type="button" class="danger" data-del="' +
            TUI.esc(c.id) +
            '">Hapus</button>'
          : "";
        return (
          "<tr>" +
          "<td><code>" +
          TUI.esc(c.id) +
          "</code></td>" +
          "<td>" +
          TUI.esc(c.name) +
          "</td>" +
          "<td>" +
          TUI.esc(c.tingkat) +
          "</td>" +
          '<td class="actions-cell">' +
          del +
          "</td>" +
          "</tr>"
        );
      })
      .join("");
    tbody.innerHTML = html;
  }

  async function refresh() {
    TUI.clearMessages();
    try {
      var rows = await TApi.listClasses();
      renderRows(rows || []);
    } catch (e) {
      if (e && (e.status === 401 || e.status === 403)) {
        tbody.innerHTML =
          '<tr><td colspan="4" class="empty">Butuh login untuk melihat kelas.</td></tr>';
        setCount(0);
        showLoginCta("RLS menolak akses anon. Masuk dulu.");
        return;
      }
      TUI.showError(e, "Muat kelas");
      tbody.innerHTML =
        '<tr><td colspan="4" class="empty">Gagal memuat. Cek konfigurasi &amp; RLS.</td></tr>';
      setCount(0);
    }
  }

  async function onAdd(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    if (!TUI.guardAuth("kelas.html")) return;
    var id = document.getElementById("fld-id").value.trim();
    var nama = document.getElementById("fld-nama").value.trim();
    var tingkat = document.getElementById("fld-tingkat").value.trim();
    if (!id) {
      TUI.showError(new Error("ID wajib diisi."), "Tambah");
      return;
    }
    try {
      await TApi.addClass({ id: id, name: nama || id, tingkat: tingkat });
      document.getElementById("fld-id").value = "";
      document.getElementById("fld-nama").value = "";
      TUI.showFlash("Kelas " + id + " ditambah.");
      await refresh();
    } catch (e) {
      if (!TUI.onAuthError(e)) TUI.showError(e, "Tambah kelas");
      if (e && (e.status === 401 || e.status === 403)) {
        showLoginCta("Sesi tidak valid. Masuk ulang.");
      }
    }
  }

  async function onDelete(id) {
    if (!TUI.guardAuth("kelas.html")) return;
    if (!global.confirm("Hapus kelas " + id + "?")) return;
    TUI.clearMessages();
    try {
      await TApi.deleteClass(id);
      TUI.showFlash("Kelas " + id + " dihapus.");
      await refresh();
    } catch (e) {
      if (!TUI.onAuthError(e)) TUI.showError(e, "Hapus kelas");
      if (e && (e.status === 401 || e.status === 403)) {
        showLoginCta("Sesi tidak valid. Masuk ulang.");
      }
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    tbody = document.querySelector("#kelas-table tbody");
    var form = document.getElementById("form-tambah");
    if (form) form.addEventListener("submit", onAdd);
    if (tbody) {
      tbody.addEventListener("click", function (ev) {
        var btn = ev.target.closest("button[data-del]");
        if (btn) onDelete(btn.getAttribute("data-del"));
      });
    }
    if (TAuth.isLoggedIn()) {
      setMutateEnabled(true);
    } else {
      showLoginCta("Tambah/hapus kelas setelah login.");
    }
    refresh();
  });
})(window);
