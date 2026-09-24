/** Detail lomba: ringkasan / hasil / manual+WO / what-if / probabilitas. */
(function (global) {
  "use strict";

  var TABS = ["ringkasan", "hasil", "manual", "whatif", "prob"];
  var currentId = null;
  var currentRow = null;
  var currentScheme = null;
  var currentScheduled = [];
  var currentResults = [];
  var currentReport = null;
  var currentTab = "ringkasan";
  var classesCache = null;

  function showEngine(msg, isErr) {
    TPage.showEngine(msg, isErr);
  }

  function showLoginCta(msg) {
    TPage.showLoginCta(msg, "lomba_detail.html?id=" + (currentId || ""));
  }

  function parseTab() {
    var t = TUI.qs("tab") || "ringkasan";
    if (TABS.indexOf(t) < 0) t = "ringkasan";
    currentTab = t;
    return t;
  }

  function showOnly(tab) {
    TABS.forEach(function (name) {
      var el = document.getElementById("pane-" + name);
      if (el) el.hidden = name !== tab;
    });
    TPage.lombaSubnav(tab);
  }

  function schemeMatches(scheme) {
    return (scheme && scheme.matches) || [];
  }

  function readyMatches(scheme) {
    return schemeMatches(scheme).filter(function (m) {
      return (
        m.status !== "walkover" &&
        m.participant_a &&
        m.participant_b &&
        m.participant_a.indexOf("Juara") !== 0 &&
        m.participant_a.indexOf("Peringkat") !== 0 &&
        m.participant_a.indexOf("Kalah") !== 0 &&
        m.participant_b.indexOf("Juara") !== 0 &&
        m.participant_b.indexOf("Peringkat") !== 0 &&
        m.participant_b.indexOf("Kalah") !== 0 &&
        m.participant_a !== null &&
        m.participant_b !== null
      );
    });
  }

  function isRealId(pid) {
    if (!pid) return false;
    if (pid === "TBD") return false;
    return (
      pid.indexOf("Juara") !== 0 &&
      pid.indexOf("Peringkat") !== 0 &&
      pid.indexOf("Kalah") !== 0
    );
  }

  function renderSummary(report, row) {
    document.getElementById("lomba-title").textContent =
      row.id + " — " + row.name;
    var pids = row.participant_ids || [];
    document.getElementById("lomba-badges").innerHTML = [
      '<span class="badge">' + TUI.esc(row.format) + "</span>",
      '<span class="badge alt">' + pids.length + " peserta</span>",
      '<span class="badge alt">' + row.team_size + "v" + row.team_size + "</span>",
      '<span class="badge alt">juara ' + row.winner_count + "</span>",
    ].join(" ");
    var s = report.summary || {};
    document.getElementById("lomba-stats").innerHTML =
      '<div class="stat"><b>' +
      (s.total_matches != null ? s.total_matches : "-") +
      "</b><span>Total match</span></div>" +
      '<div class="stat"><b>' +
      (s.match_diff != null ? s.match_diff : "-") +
      "</b><span>Match diff</span></div>" +
      '<div class="stat"><b>' +
      (s.bye != null ? s.bye : "-") +
      "</b><span>Bye</span></div>" +
      '<div class="stat"><b>' +
      (s.player_load_diff != null ? s.player_load_diff : "-") +
      "</b><span>Load diff</span></div>" +
      '<div class="stat"><b>' +
      (s.conflicts != null ? s.conflicts : "-") +
      "</b><span>Konflik</span></div>";

    document.getElementById("card-bracket").hidden = false;
    document.getElementById("card-schedule").hidden = false;
    document.getElementById("card-fairness").hidden = false;
    document.getElementById("card-notes").hidden = false;
    document.getElementById("out-bracket").textContent = report.bracket || "";
    document.getElementById("out-schedule").textContent = report.schedule || "";
    document.getElementById("out-fairness").textContent = report.fairness || "";
    document.getElementById("out-notes").innerHTML = (report.notes || [])
      .map(function (n) {
        return "<li>" + TUI.esc(n) + "</li>";
      })
      .join("");
    document.getElementById("out-sched-err").innerHTML = (
      report.sched_errors || []
    )
      .map(function (e) {
        return '<div class="err">' + TUI.esc(e) + "</div>";
      })
      .join("");
  }

  function renderManualPane() {
    if (!currentScheme) return;
    var matches = schemeMatches(currentScheme);
    var idHost = document.getElementById("manual-ids");
    if (idHost) {
      idHost.textContent =
        "ID match: " + matches.map(function (m) { return m.id; }).join(" ");
    }

    function fillSelect(id, list, keepValue) {
      var el = document.getElementById(id);
      if (!el) return;
      var prev = keepValue ? el.value : "";
      el.innerHTML = list
        .map(function (opt) {
          return (
            "<option value=\"" +
            TUI.esc(opt.value) +
            "\">" +
            TUI.esc(opt.label) +
            "</option>"
          );
        })
        .join("");
      if (keepValue && prev) el.value = prev;
    }

    var ready = readyMatches(currentScheme).filter(function (m) {
      return isRealId(m.participant_a) && isRealId(m.participant_b);
    });

    fillSelect(
      "wo-match",
      ready.map(function (m) {
        return {
          value: m.id,
          label: m.id + " — " + m.participant_a + " vs " + m.participant_b,
        };
      }),
      true
    );
    fillSelect(
      "sw-a",
      ready.map(function (m) {
        return { value: m.id, label: m.id };
      }),
      true
    );
    fillSelect(
      "sw-b",
      ready.map(function (m) {
        return { value: m.id, label: m.id };
      }),
      true
    );
    fillSelect(
      "mv-match",
      matches.map(function (m) {
        return { value: m.id, label: m.id + " (" + m.round + ")" };
      }),
      true
    );

    var woM = document.getElementById("wo-match");
    var woW = document.getElementById("wo-winner");
    if (woM && woW) {
      var selected = matches.find(function (m) {
        return m.id === woM.value;
      });
      var opts = ['<option value="">(pilih…)</option>'];
      if (selected) {
        if (isRealId(selected.participant_a)) {
          opts.push(
            '<option value="' +
              TUI.esc(selected.participant_a) +
              '">' +
              TUI.esc(selected.participant_a) +
              " (slot a)</option>"
          );
        }
        if (isRealId(selected.participant_b)) {
          opts.push(
            '<option value="' +
              TUI.esc(selected.participant_b) +
              '">' +
              TUI.esc(selected.participant_b) +
              " (slot b)</option>"
          );
        }
      }
      woW.innerHTML = opts.join("");
    }

    var pids = (currentScheme.participant_ids || []).filter(isRealId);
    fillSelect(
      "rp-old",
      pids.map(function (p) {
        return { value: p, label: p };
      }),
      true
    );

    var rpNew = document.getElementById("rp-new");
    if (rpNew) {
      var used = pids;
      classesCache = classesCache || [];
      var candidates = used
        .map(function (p) {
          return { value: p, label: p + " (di lomba)" };
        })
        .concat(
          classesCache
            .filter(function (c) {
              return used.indexOf(c.id) < 0;
            })
            .map(function (c) {
              return { value: c.id, label: c.id + " (Master)" };
            })
        );
      var prev = rpNew.value;
      rpNew.innerHTML =
        '<option value="">(pilih…)</option>' +
        candidates
          .map(function (opt) {
            return (
              '<option value="' +
              TUI.esc(opt.value) +
              '">' +
              TUI.esc(opt.label) +
              "</option>"
            );
          })
          .join("");
      if (prev) rpNew.value = prev;
    }

    var logCard = document.getElementById("manual-log-card");
    var log = document.getElementById("manual-log");
    var notes = (currentReport && currentReport.notes) || [];
    var manualNotes = notes.filter(function (n) {
      return n.indexOf("Manual:") === 0;
    });
    if (logCard && log) {
      if (manualNotes.length) {
        logCard.hidden = false;
        log.innerHTML = manualNotes
          .map(function (n) {
            return "<li>" + TUI.esc(n) + "</li>";
          })
          .join("");
      } else {
        logCard.hidden = true;
      }
    }
  }

  function renderStandingsView(data) {
    document.getElementById("out-standings").textContent =
      data.standings || "(kosong)";
    var tbody = document.querySelector("#skor-table tbody");
    var rows = data.matches || [];
    if (!rows.length) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="empty">Belum ada match.</td></tr>';
      return;
    }
    tbody.innerHTML = rows
      .map(function (m) {
        var label =
          (m.participant_a || "TBD") + " vs " + (m.participant_b || "TBD");
        if (m.status === "walkover") {
          return (
            "<tr><td><code>" +
            TUI.esc(m.id) +
            "</code></td><td><span class='badge warn'>" +
            TUI.esc(m.round) +
            "</span></td><td>" +
            TUI.esc(label) +
            "</td><td colspan='2' class='empty'>walkover - tanpa skor</td></tr>"
          );
        }
        if (!m.ready) {
          return (
            "<tr><td><code>" +
            TUI.esc(m.id) +
            "</code></td><td><span class='badge alt'>" +
            TUI.esc(m.round) +
            "</span></td><td>" +
            TUI.esc(label) +
            "</td><td colspan='2' class='empty'>menunggu ronde sebelumnya</td></tr>"
          );
        }
        var sa = m.score_a == null ? "" : m.score_a;
        var sb = m.score_b == null ? "" : m.score_b;
        return (
          "<tr><td><code>" +
          TUI.esc(m.id) +
          "</code></td><td><span class='badge'>" +
          TUI.esc(m.round) +
          "</span></td><td>" +
          TUI.esc(label) +
          "</td><td>" +
          '<input data-sa="' +
          TUI.esc(m.id) +
          '" value="' +
          TUI.esc(sa) +
          '" size="3" aria-label="skor A"> - ' +
          '<input data-sb="' +
          TUI.esc(m.id) +
          '" value="' +
          TUI.esc(sb) +
          '" size="3" aria-label="skor B">' +
          "</td><td class='actions-cell'>" +
          '<button type="button" class="btn" data-save="' +
          TUI.esc(m.id) +
          '">Simpan</button> ' +
          (m.has_result
            ? '<button type="button" class="ghost" data-del="' +
              TUI.esc(m.id) +
              '">Hapus</button> '
            : "") +
          (isRealId(m.participant_a) && isRealId(m.participant_b)
            ? '<button type="button" class="ghost" data-wo="' +
              TUI.esc(m.id) +
              "|" +
              TUI.esc(m.participant_a) +
              '">WO ' +
              TUI.esc(m.participant_a) +
              "</button> " +
              '<button type="button" class="ghost" data-wo="' +
              TUI.esc(m.id) +
              "|" +
              TUI.esc(m.participant_b) +
              '">WO ' +
              TUI.esc(m.participant_b) +
              "</button>"
            : "") +
          "</td></tr>"
        );
      })
      .join("");
  }

  async function ensureClasses() {
    if (classesCache) return classesCache;
    try {
      classesCache = (await TApi.listClasses()) || [];
    } catch (e) {
      classesCache = [];
    }
    return classesCache;
  }

  async function refreshHasil() {
    if (!currentRow || !currentScheme) return;
    showEngine("Hitung klasemen…", false);
    try {
      currentResults = (await TApi.listResults(currentId)) || [];
      var data = await TEngine.standings(
        currentRow,
        currentScheme,
        currentResults
      );
      renderStandingsView(data);
      showEngine("");
    } catch (e) {
      showEngine("Gagal klasemen: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Hasil");
    }
  }

  async function applyManual(out, flashMsg) {
    if (out.clear_results) {
      try {
        await TApi.deleteResultsForTournament(currentId);
      } catch (e) {
        if (e && e.status !== 404) throw e;
      }
      currentResults = [];
    }
    var patch = {
      manual_scheme: out.scheme,
      manual_scheduled: out.scheduled || [],
    };
    if (out.participant_ids) {
      patch.participant_ids = out.participant_ids;
      currentRow.participant_ids = out.participant_ids;
    }
    await TApi.updateTournament(currentId, patch);
    currentScheme = out.scheme;
    currentScheduled = out.scheduled || [];
    currentReport = out.report || currentReport;
    if (currentReport) {
      renderSummary(currentReport, currentRow);
      renderManualPane();
    }
    if (out.clear_results) {
      TUI.showFlash(
        flashMsg + " Semua skor dihapus (edit struktural)."
      );
    } else {
      TUI.showFlash(flashMsg);
    }
  }

  async function runWalkover(matchId, winnerId) {
    if (
      !global.confirm(
        "Walkover " + matchId + ": " + winnerId + " lolos? Semua skor dihapus."
      )
    ) {
      return;
    }
    TUI.clearMessages();
    showEngine("Terapkan walkover…", false);
    try {
      var out = await TEngine.walkover(
        currentRow,
        currentScheme,
        currentScheduled,
        matchId,
        winnerId
      );
      if (!out.ok) {
        showEngine(out.error || "Walkover ditolak.", true);
        TUI.showError(new Error(out.error || "Walkover ditolak."), "Walkover");
        return;
      }
      showEngine("");
      await applyManual(out, "Walkover " + matchId + ": " + winnerId + " lolos.");
      if (currentTab === "hasil") await refreshHasil();
      if (currentTab === "manual") renderManualPane();
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Walkover");
    }
  }

  async function saveScore(matchId) {
    var saEl = document.querySelector('[data-sa="' + matchId + '"]');
    var sbEl = document.querySelector('[data-sb="' + matchId + '"]');
    if (!saEl || !sbEl) return;
    TUI.clearMessages();
    showEngine("Simpan skor " + matchId + "…", false);
    try {
      var out = await TEngine.recordScore(
        currentRow,
        currentScheme,
        currentResults,
        matchId,
        saEl.value,
        sbEl.value
      );
      if (!out.ok) {
        showEngine(out.error || "Skor ditolak.", true);
        TUI.showError(new Error(out.error || "Skor ditolak."), "Skor");
        return;
      }
      await TApi.upsertResults(currentId, out.results);
      currentResults = out.results;
      TUI.showFlash("Skor " + matchId + " disimpan.");
      await refreshHasil();
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Simpan skor");
    }
  }

  async function deleteScore(matchId) {
    if (!global.confirm("Hapus skor " + matchId + "?")) return;
    try {
      var out = await TEngine.clearScore(
        currentRow,
        currentScheme,
        currentResults,
        matchId
      );
      if (!out.ok) {
        TUI.showError(new Error(out.error || "Gagal hapus"), "Hapus skor");
        return;
      }
      await TApi.deleteResult(currentId, matchId);
      currentResults = out.results || [];
      TUI.showFlash("Skor " + matchId + " dihapus.");
      await refreshHasil();
    } catch (e) {
      if (!TUI.onAuthError(e)) TUI.showError(e, "Hapus skor");
    }
  }

  async function onWalkoverForm(ev) {
    ev.preventDefault();
    var mid = document.getElementById("wo-match").value;
    var w = document.getElementById("wo-winner").value;
    if (!mid || !w) {
      TUI.showError(new Error("Pilih match dan pemenang."), "Walkover");
      return;
    }
    await runWalkover(mid, w);
  }

  async function onSwap(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    var a = document.getElementById("sw-a").value;
    var sa = document.getElementById("sw-sa").value;
    var b = document.getElementById("sw-b").value;
    var sb = document.getElementById("sw-sb").value;
    if (!a || !b) {
      TUI.showError(new Error("Pilih kedua match."), "Swap");
      return;
    }
    if (
      !global.confirm(
        "Tukar " + a + "(" + sa + ") <-> " + b + "(" + sb + ")? Semua skor dihapus."
      )
    ) {
      return;
    }
    showEngine("Tukar slot…", false);
    try {
      var out = await TEngine.swap(
        currentRow,
        currentScheme,
        currentScheduled,
        a,
        sa,
        b,
        sb
      );
      if (!out.ok) {
        showEngine(out.error || "Swap ditolak.", true);
        TUI.showError(new Error(out.error || "Swap ditolak."), "Swap");
        return;
      }
      showEngine("");
      await applyManual(
        out,
        "Tukar " + a + "(" + sa + ") <-> " + b + "(" + sb + ") diterapkan."
      );
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Swap");
    }
  }

  async function onMove(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    var mid = document.getElementById("mv-match").value;
    var time = document.getElementById("mv-time").value;
    var arena = document.getElementById("mv-arena").value;
    if (!mid || !time) {
      TUI.showError(new Error("Pilih match dan jam."), "Pindah jadwal");
      return;
    }
    showEngine("Pindah jadwal…", false);
    try {
      var out = await TEngine.move(
        currentRow,
        currentScheme,
        currentScheduled,
        mid,
        time,
        arena
      );
      if (!out.ok) {
        showEngine(out.error || "Pindah ditolak.", true);
        TUI.showError(new Error(out.error || "Pindah ditolak."), "Pindah jadwal");
        return;
      }
      showEngine("");
      await applyManual(
        out,
        mid + " dipindah ke " + time + " arena " + arena + "."
      );
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Pindah jadwal");
    }
  }

  async function onReplace(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    var oldId = document.getElementById("rp-old").value;
    var newId = document.getElementById("rp-new").value;
    if (!oldId || !newId || oldId === newId) {
      TUI.showError(
        new Error("Pilih peserta lama dan baru (berbeda)."),
        "Ganti peserta"
      );
      return;
    }
    if (
      !global.confirm(
        "Ganti " + oldId + " -> " + newId + "? Semua skor dihapus."
      )
    ) {
      return;
    }
    showEngine("Ganti peserta…", false);
    try {
      var out = await TEngine.replaceParticipant(
        currentRow,
        currentScheme,
        currentScheduled,
        oldId,
        newId
      );
      if (!out.ok) {
        showEngine(out.error || "Ganti ditolak.", true);
        TUI.showError(new Error(out.error || "Ganti ditolak."), "Ganti peserta");
        return;
      }
      showEngine("");
      await applyManual(out, oldId + " diganti " + newId + ".");
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Ganti peserta");
    }
  }

  async function onWhatif(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    showEngine("Hitung what-if…", false);
    try {
      var changes = {};
      var remove = document.getElementById("wi-remove").value.trim();
      var add = document.getElementById("wi-add").value.trim();
      if (remove) {
        changes.remove = remove
          .split(",")
          .map(function (s) {
            return s.trim();
          })
          .filter(Boolean);
      }
      if (add) {
        changes.add = add
          .split(",")
          .map(function (s) {
            return s.trim();
          })
          .filter(Boolean);
      }
      var fmt = document.getElementById("wi-format").value;
      if (fmt) changes.format = fmt;
      [
        "team_size",
        "winner_count",
        "duration_min",
        "minimum_rest_min",
        "arena_count",
        "qualify_per_group",
      ].forEach(function (k) {
        var v = document.getElementById("wi-" + k).value;
        if (v !== "") changes[k] = parseInt(v, 10);
      });
      var st = document.getElementById("wi-start_time").value;
      var en = document.getElementById("wi-end_time").value;
      if (st) changes.start_time = st;
      if (en) changes.end_time = en;
      var ng = document.getElementById("wi-num_groups").value;
      var out = await TEngine.whatif(
        currentRow,
        currentScheme,
        changes,
        ng === "" ? null : ng
      );
      document.getElementById("out-whatif").textContent = out.comparison || "";
      document.getElementById("whatif-notes").innerHTML = (out.notes || [])
        .map(function (n) {
          return "<li>" + TUI.esc(n) + "</li>";
        })
        .join("");
      showEngine("");
      TUI.showFlash("What-if selesai (belum disimpan sebagai lomba baru).");
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "What-if");
    }
  }

  async function onProb(ev) {
    ev.preventDefault();
    TUI.clearMessages();
    showEngine("Monte Carlo… (n besar bisa lambat di HP)", false);
    try {
      var mode = document.getElementById("pb-mode").value;
      var n = document.getElementById("pb-n").value || 2000;
      var seed = document.getElementById("pb-seed").value;
      var bobot = {};
      var bobotRaw = document.getElementById("pb-bobot").value.trim();
      if (bobotRaw) {
        bobotRaw.split(",").forEach(function (pair) {
          var bits = pair.split("=");
          if (bits.length === 2) {
            bobot[bits[0].trim()] = parseFloat(bits[1]);
          }
        });
      }
      var out = await TEngine.probability(
        currentRow,
        currentScheme,
        mode,
        bobot,
        n,
        seed
      );
      document.getElementById("out-prob").textContent = out.render || "";
      showEngine("");
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (!TUI.onAuthError(e)) TUI.showError(e, "Probabilitas");
    }
  }

  async function onDelete() {
    if (!currentId) return;
    if (!global.confirm("Hapus lomba " + currentId + " beserta results?")) return;
    try {
      await TApi.deleteResultsForTournament(currentId).catch(function () {});
      await TApi.deleteTournament(currentId);
      global.location.href =
        "lomba.html?msg=" + encodeURIComponent("Lomba " + currentId + " dihapus.");
    } catch (e) {
      if (!TUI.onAuthError(e)) TUI.showError(e, "Hapus lomba");
    }
  }

  function bindEvents() {
    var skorTable = document.getElementById("skor-table");
    if (skorTable && !skorTable._bound) {
      skorTable._bound = true;
      skorTable.addEventListener("click", function (ev) {
        var save = ev.target.closest("button[data-save]");
        if (save) saveScore(save.getAttribute("data-save"));
        var del = ev.target.closest("button[data-del]");
        if (del) deleteScore(del.getAttribute("data-del"));
        var wo = ev.target.closest("button[data-wo]");
        if (wo) {
          var bits = wo.getAttribute("data-wo").split("|");
          runWalkover(bits[0], bits[1]);
        }
      });
    }
    var pairs = [
      ["form-whatif", onWhatif],
      ["form-prob", onProb],
      ["form-wo", onWalkoverForm],
      ["form-swap", onSwap],
      ["form-move", onMove],
      ["form-replace", onReplace],
    ];
    pairs.forEach(function (p) {
      var el = document.getElementById(p[0]);
      if (el && !el._bound) {
        el._bound = true;
        el.addEventListener("submit", p[1]);
      }
    });
    var woMatch = document.getElementById("wo-match");
    if (woMatch && !woMatch._bound) {
      woMatch._bound = true;
      woMatch.addEventListener("change", renderManualPane);
    }
  }

  async function load() {
    currentId = TUI.qs("id");
    if (!currentId) {
      TUI.showError(new Error("Parameter id lomba hilang."), "Detail");
      return;
    }
    var tab = parseTab();
    if (!TAuth.isLoggedIn()) {
      showLoginCta("Login diperlukan untuk membuka lomba.");
      return;
    }
    try {
      var rows = await TApi.getTournament(currentId);
      if (!rows || !rows.length) {
        TUI.showError(new Error("Lomba tidak ditemukan."), "Detail");
        return;
      }
      currentRow = rows[0];
      currentScheme = currentRow.manual_scheme || {};
      currentScheduled = currentRow.manual_scheduled || [];
      document.getElementById("meta-card").hidden = false;
      document.getElementById("btn-hapus").onclick = onDelete;

      showEngine("Menjalankan engine Python (Pyodide)…", false);
      var report = await TEngine.analyzeSaved(
        currentRow,
        currentScheme,
        currentScheduled
      );
      currentScheme = report.scheme || currentScheme;
      currentScheduled = report.scheduled || currentScheduled;
      currentReport = report;
      showEngine("");
      renderSummary(report, currentRow);
      showOnly(tab);
      bindEvents();
      await ensureClasses();

      if (tab === "hasil") {
        await refreshHasil();
      }
      if (tab === "manual") {
        renderManualPane();
      }
    } catch (e) {
      showEngine("Gagal: " + (e.message || e), true);
      if (e && (e.status === 401 || e.status === 403)) {
        showLoginCta("RLS menolak akses.");
        return;
      }
      if (!TUI.onAuthError(e)) TUI.showError(e, "Detail lomba");
    }
  }

  document.addEventListener("DOMContentLoaded", load);
})(window);
