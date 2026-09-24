"""UI Web Phase 1 (PRD §5, §14): untuk panitia non-programmer.

Stdlib only (http.server) — tanpa install, jalan offline.
In-memory (database = tahap berikut, PRD §19).

Cara jalan:  python web.py [--port 8000]  -> buka http://localhost:8000
"""
from __future__ import annotations

import argparse
import html
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tournament import (  # noqa: E402
    VALID_FORMATS,
    ClassInfo,
    Tournament,
    analyze_existing,
    apply_changes,
    advance_scheme,
    build_default_master,
    build_report,
    build_standings,
    clear_result,
    compare_reports,
    custom_model,
    detect_cross_event_conflicts,
    equal_model,
    generate_scheme,
    is_placeholder,
    monte_carlo,
    move_match,
    optimize_multi_event,
    percent_model,
    record_result,
    render_bracket,
    render_comparison,
    render_fairness,
    render_probability,
    render_schedule,
    render_standings,
    replace_participant,
    select_participants,
    set_walkover,
    swap_slots,
    total_load_across_events,
    what_if,
)

STORE = {"registry": build_default_master(28), "seq": 0, "lomba": {}, "msg": "",
         "store": None}


def persist() -> None:
    if STORE["store"] is not None:
        STORE["store"].save_all(STORE["registry"], STORE["lomba"], STORE["seq"])


def reset_store(n_kelas: int = 28) -> None:
    STORE.update(registry=build_default_master(n_kelas), seq=0, lomba={}, msg="")


def esc(s: object) -> str:
    return html.escape(str(s), quote=True)


_CSS = """
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
  background:#f0f2f5;color:#0f172a;line-height:1.5;font-size:15px}
a{color:#1d4ed8;text-decoration:none}
a:hover{text-decoration:underline}
.topbar{background:linear-gradient(135deg,#0f172a 0%,#1e3a8a 100%);color:#fff;
  padding:.65rem 1.25rem;display:flex;flex-wrap:wrap;align-items:center;gap:.35rem 1rem;
  box-shadow:0 2px 8px rgba(15,23,42,.25)}
.brand{font-weight:700;font-size:1rem;letter-spacing:.02em;color:#fff;white-space:nowrap}
.brand:hover{text-decoration:none;opacity:.9}
.topnav{display:flex;flex-wrap:wrap;gap:.15rem}
.topnav a{color:#cbd5e1;padding:.35rem .7rem;border-radius:6px;font-size:.9rem}
.topnav a:hover{background:rgba(255,255,255,.12);color:#fff;text-decoration:none}
main{max-width:1100px;margin:1.25rem auto;padding:0 1rem 2.5rem}
.page-title{margin:.25rem 0 1rem;font-size:1.55rem;font-weight:700;color:#0f172a}
.flash{background:#ecfdf5;border:1px solid #6ee7b7;color:#065f46;
  padding:.7rem 1rem;border-radius:8px;margin-bottom:1rem;font-weight:600}
.err{background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;
  padding:.7rem 1rem;border-radius:8px;margin-bottom:1rem}
.card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;
  padding:1.1rem 1.25rem;margin-bottom:1.1rem;box-shadow:0 1px 2px rgba(15,23,42,.05)}
.card h2,.card h3{margin:.15rem 0 .75rem;font-size:1.05rem;font-weight:700;color:#0f172a}
.meta{display:flex;flex-wrap:wrap;gap:.4rem .75rem;margin-bottom:.75rem}
.badge{display:inline-block;background:#e0e7ff;color:#3730a3;border-radius:999px;
  padding:.15rem .65rem;font-size:.8rem;font-weight:600}
.badge.alt{background:#f1f5f9;color:#334155}
.badge.ok{background:#d1fae5;color:#065f46}
.badge.warn{background:#fef3c7;color:#92400e}
.subnav{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:1rem}
.subnav a{background:#fff;border:1px solid #e2e8f0;color:#1e293b;
  padding:.4rem .8rem;border-radius:8px;font-size:.88rem;font-weight:600}
.subnav a:hover{background:#eff6ff;border-color:#93c5fd;text-decoration:none}
.subnav a.primary{background:#1d4ed8;border-color:#1d4ed8;color:#fff}
.subnav a.primary:hover{background:#1e40af}
table{border-collapse:collapse;width:100%;background:#fff;font-size:.92rem}
th,td{border:1px solid #e2e8f0;padding:.5rem .7rem;text-align:left;vertical-align:top}
th{background:#f8fafc;font-weight:700;color:#334155;white-space:nowrap}
tr:nth-child(even) td{background:#f8fafc}
pre{background:#0f172a;color:#e2e8f0;padding:.9rem 1rem;border-radius:10px;
  overflow:auto;font-size:.85rem;line-height:1.45;margin:.5rem 0 0}
label{display:inline-block;font-weight:600;color:#334155;margin:.35rem 0 .15rem}
input[type=text],input:not([type]),input[type=number],select,textarea{
  border:1px solid #cbd5e1;border-radius:8px;padding:.45rem .65rem;font:inherit;
  background:#fff;color:#0f172a;max-width:100%}
input:focus,select:focus,textarea:focus{outline:2px solid #93c5fd;border-color:#3b82f6}
button,.btn{display:inline-block;background:#1d4ed8;color:#fff;border:none;
  border-radius:8px;padding:.5rem .95rem;font:inherit;font-weight:600;cursor:pointer}
button:hover,.btn:hover{background:#1e40af;text-decoration:none}
button.ghost,button.danger{background:#fff;color:#b91c1c;border:1px solid #fca5a5}
button.ghost:hover,button.danger:hover{background:#fef2f2}
.form-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:.65rem .9rem}
.form-grid .full{grid-column:1/-1}
.checks{display:flex;flex-wrap:wrap;gap:.35rem .85rem;max-height:220px;overflow:auto;
  border:1px solid #e2e8f0;border-radius:8px;padding:.65rem;background:#f8fafc}
.checks label{margin:0;font-weight:500;display:flex;align-items:center;gap:.35rem}
.actions{display:flex;flex-wrap:wrap;gap:.65rem;align-items:center;margin-top:.85rem}
.empty{color:#64748b;font-style:italic;padding:.5rem 0}
.hint{color:#64748b;font-size:.88rem;margin:.25rem 0 .75rem}
.grid2{display:grid;grid-template-columns:1fr;gap:1.1rem}
@media(min-width:800px){.grid2{grid-template-columns:1fr 1fr}}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.75rem}
.stat{background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:.75rem;text-align:center}
.stat b{display:block;font-size:1.35rem;color:#1d4ed8}
.stat span{font-size:.8rem;color:#64748b}
table.form-table td{border:none;padding:.35rem .4rem}
table.form-table tr:nth-child(even) td{background:transparent}
td.actions-cell,th.actions-cell{white-space:nowrap}
.tip-live{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;
  padding:.75rem .9rem;margin:.75rem 0;font-size:.92rem}
.tip-live b{color:#1d4ed8}
.tip-live ul{margin:.4rem 0 0;padding-left:1.15rem}
.tip-live li{margin:.2rem 0}
.fmt-grid{display:grid;grid-template-columns:1fr;gap:.75rem}
@media(min-width:800px){.fmt-grid{grid-template-columns:1fr 1fr}}
.fmt-card{border:1px solid #e2e8f0;border-radius:10px;padding:.85rem 1rem;background:#f8fafc}
.fmt-card.active{border-color:#3b82f6;background:#eff6ff;box-shadow:0 0 0 2px #bfdbfe}
.fmt-card h3{margin:0 0 .35rem;font-size:.95rem;color:#0f172a}
.fmt-card h3 code{font-size:.85rem;background:#e2e8f0;border-radius:4px;padding:.05rem .35rem}
.fmt-card p{margin:.25rem 0;font-size:.88rem;color:#334155}
.fmt-card .tips{margin:.45rem 0 0;padding-left:1.1rem;font-size:.85rem;color:#475569}
.fmt-card .tips li{margin:.15rem 0}
.fmt-card .when{display:inline-block;font-size:.78rem;font-weight:700;color:#065f46;
  background:#d1fae5;border-radius:999px;padding:.1rem .5rem;margin-bottom:.35rem}
"""


def page(title: str, body: str, code_hint: str = "") -> str:
    msg = STORE["msg"]
    STORE["msg"] = ""
    flash = f"<div class='flash'>{esc(msg)}</div>" if msg else ""
    err = f"<div class='err'>{esc(code_hint)}</div>" if code_hint else ""
    return (
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)} · Tournament Simulator</title>"
        f"<style>{_CSS}</style></head><body>"
        "<header class='topbar'>"
        "<a class='brand' href='/'>Tournament Simulator</a>"
        "<nav class='topnav'>"
        "<a href='/'>Beranda</a>"
        "<a href='/kelas'>Kelas</a>"
        "<a href='/lomba/baru'>Lomba baru</a>"
        "<a href='/banding'>Banding</a>"
        "<a href='/lintas'>Lintas</a>"
        "<a href='/optimasi'>Optimasi</a>"
        "</nav></header>"
        f"<main><h1 class='page-title'>{esc(title)}</h1>{flash}{err}{body}</main>"
        "</body></html>"
    )


def lomba_nav(lid: str) -> str:
    base = f"/lomba/{esc(lid)}"
    return (
        f"<nav class='subnav'>"
        f"<a href='{base}'>Detail</a>"
        f"<a class='primary' href='{base}/hasil'>Hasil & skor</a>"
        f"<a href='{base}/banding'>Banding format</a>"
        f"<a href='{base}/whatif'>What-if</a>"
        f"<a href='{base}/probabilitas'>Probabilitas</a>"
        f"<a href='{base}/manual'>Manual</a>"
        f"</nav>"
    )


def send(handler: BaseHTTPRequestHandler, body: str, code: int = 200) -> None:
    data = body.encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)


def redirect(handler: BaseHTTPRequestHandler, url: str) -> None:
    persist()  # write-through: semua mutasi POST diakhiri redirect
    handler.send_response(303)
    handler.send_header("Location", url)
    handler.end_headers()


def form(handler: BaseHTTPRequestHandler) -> dict[str, list[str]]:
    n = int(handler.headers.get("Content-Length", 0) or 0)
    return urllib.parse.parse_qs(handler.rfile.read(n).decode("utf-8"))


def one(d: dict[str, list[str]], key: str, default: str = "") -> str:
    v = d.get(key, [default])
    return v[0] if v else default


def get_lomba(lid: str) -> dict:
    try:
        return STORE["lomba"][lid]
    except KeyError as exc:
        raise ValueError(f"Lomba tak dikenal: {lid}.") from exc


def report_of(rec: dict):
    if rec["scheme"] is not None:
        return analyze_existing(rec["scheme"], rec["scheduled"])
    if rec["scheduled"] is not None:
        # Jadwal manual di atas skema generated: bangun skema lalu rebind.
        scheme = generate_scheme(rec["tournament"], rec["peserta"])
        return analyze_existing(scheme, rec["scheduled"])
    return build_report(rec["tournament"], rec["peserta"])


def new_lomba_id() -> str:
    STORE["seq"] += 1
    return f"L{STORE['seq']}"


# ---------- halaman ----------

def home() -> str:
    n_lomba = len(STORE["lomba"])
    n_kelas = STORE["registry"].count()
    total_peserta = sum(len(r["peserta"]) for r in STORE["lomba"].values())
    rows = "".join(
        f"<tr><td><a href='/lomba/{esc(lid)}'><b>{esc(r['tournament'].name)}</b></a></td>"
        f"<td><code>{esc(lid)}</code></td>"
        f"<td><span class='badge alt'>{esc(r['tournament'].format)}</span></td>"
        f"<td>{len(r['peserta'])}</td>"
        f"<td>{r['tournament'].team_size}v{r['tournament'].team_size}</td>"
        f"<td><a href='/lomba/{esc(lid)}'>Buka</a></td></tr>"
        for lid, r in STORE["lomba"].items()
    ) or "<tr><td colspan='6' class='empty'>Belum ada lomba. Mulai dari Lomba baru.</td></tr>"
    return page("Tournament Simulator",
                "<div class='stats'>"
                f"<div class='stat'><b>{n_lomba}</b><span>Lomba</span></div>"
                f"<div class='stat'><b>{n_kelas}</b><span>Kelas di master</span></div>"
                f"<div class='stat'><b>{total_peserta}</b><span>Kesempatan ikut (peserta)</span></div>"
                "</div>"
                "<div class='card'><h2>Daftar lomba</h2>"
                f"<table><tr><th>Nama</th><th>ID</th><th>Format</th><th>Peserta</th>"
                f"<th>Tim</th><th></th></tr>{rows}</table>"
                "<div class='actions'><a class='btn' href='/lomba/baru'>+ Lomba baru</a>"
                "<a href='/kelas'>Kelola kelas</a></div></div>")


def kelas_list() -> str:
    rows = "".join(
        f"<tr><td><code>{esc(c.id)}</code></td><td>{esc(c.name)}</td>"
        f"<td>{esc(c.tingkat)}</td>"
        f"<td class='actions-cell'><form method='post' action='/kelas/hapus' style='display:inline'>"
        f"<input type='hidden' name='id' value='{esc(c.id)}'>"
        "<button class='danger'>Hapus</button></form></td></tr>"
        for c in STORE["registry"].list_all()
    ) or "<tr><td colspan='4' class='empty'>Belum ada kelas.</td></tr>"
    return page(f"Master Kelas ({STORE['registry'].count()})",
                "<div class='card'><h2>Daftar kelas</h2>"
                "<table><tr><th>ID</th><th>Nama</th><th>Tingkat</th><th></th></tr>"
                f"{rows}</table></div>"
                "<div class='card'><h2>Tambah kelas</h2>"
                "<form method='post' action='/kelas/tambah'><div class='form-grid'>"
                "<label>ID <input name='id' required placeholder='XII-01'></label>"
                "<label>Nama <input name='nama' placeholder='Kelas A'></label>"
                "<label>Tingkat <input name='tingkat' value='XII'></label>"
                "</div><div class='actions'><button>Tambah</button></div></form></div>")


# Panduan format untuk panitia (PRD F-04) — ditampilkan di Lomba baru.
_FORMAT_GUIDE: dict[str, dict[str, str | list[str]]] = {
    "knockout": {
        "title": "Gugur murni",
        "when": "Cepat, sedikit match, satu-satu kalah langsung keluar",
        "about": (
            "Semua peserta masuk bracket langsung. Kalah satu laga = selesai. "
            "Bila jumlah peserta bukan pangkat 2, sistem memberi bye "
            "(langkung ronde awal) supaya ronde berikutnya penuh."
        ),
        "tips": [
            "Paling cocok kalau jam terbatas dan hanya butuh 1 juara.",
            "Cek Bye Analysis: peserta yang dapat bye main lebih sedikit di awal.",
            "Jalur juara bisa beda panjang bila ada bye - bandingkan path-to-title.",
            "Knockout tidak boleh seri: pakai walkover bila perlu.",
        ],
    },
    "preliminary_knockout": {
        "title": "Play-in + bracket utama",
        "when": "Peserta tidak pas 2^n, tapi tetap mau format gugur",
        "about": (
            "Ronde awal (P) hanya untuk peserta berlebih. Pemenang play-in "
            "masuk bracket knockout utama seperti biasa. Sisa yang langsung "
            "masuk R1 mendapat keuntungan (tidak main di P)."
        ),
        "tips": [
            "Pakai bila 6-10 peserta dan tidak mau ribet grup.",
            "Fairness: yang ikut P punya 1 laga tambahan - cek match difference.",
            "Lebih singkat dari round robin penuh, lebih adil dari KO polos.",
            "Sama seperti KO: siapkan aturan ser/walkover.",
        ],
    },
    "round_robin": {
        "title": "Liga (semua vs semua)",
        "when": "Prioritas keadilan penuh, jam cukup longgar",
        "about": (
            "Setiap peserta main melawan semua peserta lain tepat satu kali. "
            "Klasemen dari poin (menang 3, seri 1, kalah 0). Tidak ada bye; "
            "tidak ada knockout di akhir."
        ),
        "tips": [
            "Match = n x (n-1) / 2 - 10 kelas = 45 laga, pastikan arena & jam muat.",
            "Seri diperbolehkan (fase ini), beda dengan knockout.",
            "Paling transparan: semua bertemu, load paling merata.",
            "Cocok final pool / hari penuh; kurang cocok bila waktunya mepet.",
        ],
    },
    "group": {
        "title": "Fase grup saja",
        "when": "Ingin klasemen per grup tanpa lanjutan KO",
        "about": (
            "Peserta dibagi ke beberapa grup. Di dalam grup main round robin. "
            "Tidak ada babak knockout - juara grup = peringkat teratas klasemen "
            "grup (atau juara agregat bila digabung)."
        ),
        "tips": [
            "Jumlah grup bisa diatur (field Grup di what-if); kosong = auto.",
            "Cocok penyisihan saja, atau lomba yang juaranya dari poin grup.",
            "Klasemen menampilkan juara / peringkat grup (tanpa label 'lolos').",
            "Rest analysis tetap penting: satu kelas bisa main 2x berturut di grup kecil.",
        ],
    },
    "group_knockout": {
        "title": "Grup + babak gugur",
        "when": "Standar OSIS: grup dulu, juara lanjut KO",
        "about": (
            "Fase grup (RR di tiap grup), lalu lolos masuk bracket knockout "
            "sampai final. Slot bracket diisi 'Juara Grup X' / 'Peringkat k "
            "Grup X' sampai klasemen grup lengkap."
        ),
        "tips": [
            "Lolos/grup: 1 = hanya juara grup, 2 = juara + peringkat 2.",
            "Juara > 1 aktifkan F3 (perebutan juara 3) otomatis di knockout.",
            "Cocok 6-16 peserta: grup adil, KO hemat waktu di akhir.",
            "Setelah semua skor grup masuk, klasemen resolve otomatis ke bracket.",
        ],
    },
}


def format_guide_html() -> str:
    cards = []
    for fmt in VALID_FORMATS:
        g = _FORMAT_GUIDE.get(fmt)
        if not g:
            continue
        tips = "".join(f"<li>{esc(t)}</li>" for t in g["tips"])
        cards.append(
            f"<div class='fmt-card' data-fmt='{esc(fmt)}' id='fmt-{esc(fmt)}'>"
            f"<span class='when'>{esc(str(g['when']))}</span>"
            f"<h3><code>{esc(fmt)}</code> &middot; {esc(str(g['title']))}</h3>"
            f"<p>{esc(str(g['about']))}</p>"
            f"<ul class='tips'>{tips}</ul></div>"
        )
    return (
        "<div class='card' id='panduan-format'><h2>Panduan tiap format</h2>"
        "<p class='hint'>Klik/pilih Format di atas - kartu yang cocok akan tersorot. "
        "Semua fitur fairness (bye, rest, load, path) tetap dihitung.</p>"
        f"<div class='fmt-grid'>{''.join(cards)}</div></div>"
    )


def _format_live_tip(fmt: str) -> str:
    g = _FORMAT_GUIDE.get(fmt)
    if not g:
        return ""
    tips = "".join(f"<li>{esc(t)}</li>" for t in g["tips"])
    return (
        f"<div class='tip-live' id='tip-live'>"
        f"<b>{esc(fmt)}</b> - {esc(str(g['title']))}<br>"
        f"{esc(str(g['about']))}"
        f"<ul>{tips}</ul></div>"
    )


def lomba_baru() -> str:
    boxes = "".join(
        f"<label><input type='checkbox' name='peserta' value='{esc(c.id)}' checked> "
        f"{esc(c.id)}</label> "
        for c in STORE["registry"].list_all()
    )
    opts = "".join(f"<option>{esc(f)}</option>" for f in VALID_FORMATS)
    default_fmt = VALID_FORMATS[0]
    return page("Lomba baru",
                "<div class='card'><h2>Parameter lomba</h2>"
                "<form method='post' action='/lomba/buat'>"
                "<div class='form-grid'>"
                "<label class='full'>Nama lomba "
                "<input name='nama' value='Lomba 1' required></label>"
                f"<label>Format <select name='format' id='format-select'>{opts}</select></label>"
                "<label>Team size <input name='team_size' value='4' size='3'></label>"
                "<label>Jumlah juara <input name='winner_count' value='1' size='3'></label>"
                "<label>Lolos/grup <input name='qualify_per_group' value='1' size='3'></label>"
                "<label>Durasi (mnt) <input name='duration_min' value='30' size='4'></label>"
                "<label>Rest min (mnt) <input name='minimum_rest_min' value='10' size='4'></label>"
                "<label>Arena <input name='arena_count' value='2' size='3'></label>"
                "<label>Mulai <input name='start_time' value='08:00' size='6'></label>"
                "<label>Selesai <input name='end_time' value='17:00' size='6'></label>"
                "</div>"
                "<p class='hint'>group_knockout: lolos/grup 1 = juara, 2 = +peringkat 2. "
                "winner_count &gt; 1 menambah F3 (juara 3) di format knockout lanjutan.</p>"
                + _format_live_tip(default_fmt)
                + "<h3>Peserta (centang yang ikut)</h3>"
                f"<div class='checks'>{boxes}</div>"
                "<div class='actions'><button>Buat lomba</button></div>"
                "</form></div>"
                + format_guide_html()
                + """
<script>
(function(){
  var sel = document.getElementById('format-select');
  var tip = document.getElementById('tip-live');
  if (!sel) return;
  function refresh(){
    var v = sel.value;
    document.querySelectorAll('.fmt-card').forEach(function(el){
      el.classList.toggle('active', el.getAttribute('data-fmt') === v);
    });
    if (tip) tip.style.outline = '2px solid #93c5fd';
    location.hash = ''; /* jangan pindah halaman */
    var card = document.getElementById('fmt-' + v);
    if (card && tip) {
      /* sinkron teks live tip dari kartu aktif */
      var h = card.querySelector('h3');
      var p = card.querySelector('p');
      var ul = card.querySelector('ul');
      if (h && p && ul) {
        tip.innerHTML = '<b>' + v + '</b> - ' + h.textContent.split('\\u00b7').pop().trim()
          + '<br>' + p.innerHTML + '<ul>' + ul.innerHTML + '</ul>';
      }
    }
  }
  sel.addEventListener('change', refresh);
  refresh();
})();
</script>""")


def lomba_detail(lid: str) -> str:
    rec = get_lomba(lid)
    rep = report_of(rec)
    assert rep.fairness is not None and rep.rest is not None
    t = rec["tournament"]
    results = rec.get("results") or {}
    shown = advance_scheme(rep.scheme, results) if results else rep.scheme
    sched_err = "".join(
        f"<div class='err'>{esc(e)}</div>" for e in rep.sched_errors)
    f = rep.fairness
    stats = (
        "<div class='stats'>"
        f"<div class='stat'><b>{f.total_matches}</b><span>Total match</span></div>"
        f"<div class='stat'><b>{f.match_diff}</b><span>Match difference</span></div>"
        f"<div class='stat'><b>{f.bye_count}</b><span>Bye</span></div>"
        f"<div class='stat'><b>{f.player_load_diff}</b><span>Player-load diff</span></div>"
        f"<div class='stat'><b>{f.path_diff}</b><span>Path difference</span></div>"
        f"<div class='stat'><b>{len(results)}</b><span>Skor tercatat</span></div>"
        "</div>"
    )
    return page(f"{t.name} ({lid})",
                lomba_nav(lid)
                + sched_err
                + "<div class='card'><h2>Ringkasan</h2>"
                + "<div class='meta'>"
                + f"<span class='badge'>{esc(t.format)}</span>"
                + f"<span class='badge alt'>{len(rec['peserta'])} peserta</span>"
                + f"<span class='badge alt'>arena {t.arena_count}</span>"
                + f"<span class='badge alt'>{esc(t.start_time)}-{esc(t.end_time)}</span>"
                + f"<span class='badge alt'>{t.team_size}v{t.team_size}</span>"
                + f"<span class='badge alt'>{t.winner_count} juara</span>"
                + "</div>"
                + stats
                + "</div>"
                + "<div class='grid2'>"
                + "<div class='card'><h2>Bracket</h2>"
                + f"<pre>{esc(render_bracket(shown.matches))}</pre></div>"
                + "<div class='card'><h2>Jadwal</h2>"
                + f"<pre>{esc(render_schedule(rep.scheduled))}</pre></div>"
                + "</div>"
                + "<div class='card'><h2>Fairness (transparan)</h2>"
                + f"<pre>{esc(render_fairness(f, rep.rest, rep.conflicts))}</pre></div>"
                + "<div class='card'><h2>Klasemen</h2>"
                + f"<pre>{esc(render_standings(build_standings(rep.scheme, results), results))}</pre>"
                + "</div>"
                + "<div class='card'><h2>Reset</h2>"
                + "<p class='hint'>Menghapus edit manual &amp; skor; skema digenerate ulang.</p>"
                + "<form method='post' action='/lomba/reset'>"
                + f"<input type='hidden' name='id' value='{esc(lid)}'>"
                + "<button class='danger'>Reset ke hasil generate</button></form></div>")


def lomba_banding(lid: str) -> str:
    rec = get_lomba(lid)
    labels, reps, gagal = [], [], []
    for fmt in VALID_FORMATS:
        try:
            src = rec["tournament"]
            tt = Tournament(id=src.id, name=src.name,
                            format=fmt, team_size=src.team_size,
                            winner_count=src.winner_count,
                            duration_min=src.duration_min,
                            minimum_rest_min=src.minimum_rest_min,
                            arena_count=src.arena_count,
                            date=src.date,
                            start_time=src.start_time,
                            end_time=src.end_time,
                            qualify_per_group=src.qualify_per_group)
            reps.append(build_report(tt, rec["peserta"]))
            labels.append(fmt)
        except ValueError as e:
            gagal.append(f"{fmt}: {e}")
    table = compare_reports(reps, labels)
    note = "".join(f"<div class='err'>{esc(g)}</div>" for g in gagal)
    return page(f"Banding format ({lid})",
                lomba_nav(lid) + note
                + "<div class='card'><h2>Perbandingan semua format</h2>"
                f"<pre>{esc(render_comparison(labels, table))}</pre></div>")


def lomba_whatif(lid: str) -> str:
    rec = get_lomba(lid)
    return page(f"What-if ({lid})",
                lomba_nav(lid)
                + "<div class='card'><h2>Ubah kondisi (simulasi)</h2>"
                "<p class='hint'>Kosongkan field yang tidak diubah. ID kelas dipisah koma.</p>"
                f"<form method='post' action='/lomba/{esc(lid)}/whatif/hitung'>"
                "<div class='form-grid'>"
                "<label class='full'>Hapus peserta (koma) "
                "<input name='remove' placeholder='XII-06,XII-07'></label>"
                "<label class='full'>Tambah peserta (koma) "
                "<input name='add' placeholder='XII-27'></label>"
                "<label>Format <select name='format'><option value=''>-tetap-</option>"
                + "".join(f"<option>{esc(f)}</option>" for f in VALID_FORMATS)
                + "</select></label>"
                "<label>Arena <input name='arena_count' size='3'></label>"
                "<label>Durasi <input name='duration_min' size='4'></label>"
                "<label>Rest <input name='minimum_rest_min' size='4'></label>"
                "<label>Juara <input name='winner_count' size='3'></label>"
                "<label>Team <input name='team_size' size='3'></label>"
                "<label>Grup <input name='num_groups' size='3'></label>"
                "<label>Lolos/grup <input name='qualify_per_group' size='3'></label>"
                "</div><div class='actions'><button>Hitung what-if</button></div>"
                "</form></div>")


def lomba_prob(lid: str) -> str:
    return page(f"Probabilitas ({lid})",
                lomba_nav(lid)
                + "<div class='card'><h2>Simulasi kemungkinan</h2>"
                "<p class='hint'>Bukan prediksi kemampuan nyata — hanya model probabilitas pilihanmu.</p>"
                f"<form method='post' action='/lomba/{esc(lid)}/probabilitas/hitung'>"
                "<div class='form-grid'>"
                "<label>Model <select name='mode'>"
                "<option value='equal'>equal</option>"
                "<option value='custom'>custom bobot</option>"
                "<option value='persen'>custom persen</option></select></label>"
                "<label>Simulasi (n) <input name='n' value='2000' size='7'></label>"
                "<label>Seed <input name='seed' value='7' size='6'></label>"
                "<label class='full'>Bobot/persen per baris (ID=nilai)<br>"
                "<textarea name='bobot' rows='6' cols='40' "
                "placeholder='XII-01=1.5'></textarea></label>"
                "</div><div class='actions'><button>Hitung probabilitas</button></div>"
                "</form></div>")


def lomba_hasil(lid: str) -> str:
    rec = get_lomba(lid)
    rep = report_of(rec)
    results = rec.get("results") or {}
    shown = advance_scheme(rep.scheme, results) if results else rep.scheme
    forms = []
    for m in shown.matches:
        ready = (m.status != "walkover"
                 and m.participant_a is not None and m.participant_b is not None
                 and not is_placeholder(m.participant_a)
                 and not is_placeholder(m.participant_b))
        res = results.get(m.id)
        sa = res.score_a if res else ""
        sb = res.score_b if res else ""
        ronde = esc(m.round)
        if m.status == "walkover":
            forms.append(
                f"<tr><td><code>{esc(m.id)}</code></td>"
                f"<td><span class='badge warn'>{ronde}</span></td>"
                f"<td>{esc(str(m.participant_a))} vs {esc(str(m.participant_b))}</td>"
                f"<td colspan='3' class='empty'>walkover - tanpa skor</td></tr>")
        elif not ready:
            forms.append(
                f"<tr><td><code>{esc(m.id)}</code></td>"
                f"<td><span class='badge alt'>{ronde}</span></td>"
                f"<td>{esc(str(m.participant_a))} vs {esc(str(m.participant_b))}</td>"
                f"<td colspan='3' class='empty'>menunggu ronde sebelumnya</td></tr>")
        else:
            forms.append(
                f"<tr><td><code>{esc(m.id)}</code></td>"
                f"<td><span class='badge'>{ronde}</span></td>"
                f"<td>{esc(m.participant_a or '')} vs {esc(m.participant_b or '')}</td>"
                f"<td><input name='sa_{esc(m.id)}' value='{esc(sa)}' size='3' "
                f"aria-label='skor A'> - "
                f"<input name='sb_{esc(m.id)}' value='{esc(sb)}' size='3' "
                f"aria-label='skor B'></td>"
                f"<td class='actions-cell'><button name='match_id' "
                f"value='{esc(m.id)}'>Simpan</button>"
                + (
                    f" <button class='ghost' formaction='/lomba/{esc(lid)}/skor/hapus' "
                    f"name='match_id' value='{esc(m.id)}'>Hapus</button>"
                    if res else "")
                + "</td></tr>")
    tables = render_standings(build_standings(rep.scheme, results), results)
    return page(
        f"Hasil & klasemen ({lid})",
        lomba_nav(lid)
        + "<div class='card'><h2>Isi skor</h2>"
        + f"<form method='post' action='/lomba/{esc(lid)}/skor'>"
        + "<table><tr><th>ID</th><th>Ronde</th><th>Peserta</th>"
        "<th>Skor A-B</th><th>Aksi</th></tr>"
        + "".join(forms)
        + "</table>"
        "<div class='actions'>"
        "<button name='match_id' value='__all__'>Simpan semua skor terisi</button>"
        "</div></form></div>"
        "<div class='card'><h2>Klasemen</h2>"
        f"<pre>{esc(tables)}</pre></div>")


def lomba_manual(lid: str) -> str:
    rec = get_lomba(lid)
    rep = report_of(rec)
    mids = " ".join(m.id for m in rep.scheme.matches)
    return page(f"Manual ({lid})",
                lomba_nav(lid)
                + "<p class='hint'>ID match: " + esc(mids) + "</p>"
                + "<div class='grid2'>"
                + "<div class='card'><h2>Tukar lawan</h2>"
                + "<form method='post' action='/lomba/{0}/manual/swap'>".format(esc(lid))
                + "<div class='form-grid'>"
                "<label>Match A <input name='a' size='10'></label>"
                "<label>Slot A <input name='sa' value='a' size='2'></label>"
                "<label>Match B <input name='b' size='10'></label>"
                "<label>Slot B <input name='sb' value='a' size='2'></label>"
                "</div><div class='actions'><button>Tukar</button></div></form></div>"
                + "<div class='card'><h2>Pindah jadwal</h2>"
                + "<form method='post' action='/lomba/{0}/manual/pindah'>".format(esc(lid))
                + "<div class='form-grid'>"
                "<label>Match <input name='mid' size='10'></label>"
                "<label>Jam <input name='jam' value='08:00' size='6'></label>"
                "<label>Arena <input name='arena' value='1' size='3'></label>"
                "</div><div class='actions'><button>Pindah</button></div></form></div>"
                + "<div class='card'><h2>Ganti peserta</h2>"
                + "<form method='post' action='/lomba/{0}/manual/ganti'>".format(esc(lid))
                + "<div class='form-grid'>"
                "<label>Lama <input name='old' size='10'></label>"
                "<label>Baru <input name='new' size='10'></label>"
                "</div><div class='actions'><button>Ganti</button></div></form></div>"
                + "<div class='card'><h2>Walkover</h2>"
                + "<form method='post' action='/lomba/{0}/manual/wo'>".format(esc(lid))
                + "<div class='form-grid'>"
                "<label>Match <input name='mid' size='10'></label>"
                "<label>Pemenang <input name='w' size='10'></label>"
                "</div><div class='actions'><button>Terapkan WO</button></div></form></div>"
                + "</div>")


def pilih_lomba(action: str, title: str) -> str:
    boxes = "".join(
        f"<label><input type='checkbox' name='ids' value='{esc(lid)}'> "
        f"<code>{esc(lid)}</code> {esc(r['tournament'].name)} "
        f"({esc(r['tournament'].format)})</label>"
        for lid, r in STORE["lomba"].items()
    ) or "<span class='empty'>Belum ada lomba.</span>"
    extra = ""
    if action == "/optimasi/jalan":
        extra = ("<label>Max shift batch "
                 "<input name='max_shift_batches' value='12' size='4'></label>")
    return page(title,
                "<div class='card'>"
                f"<form method='post' action='{action}'>"
                "<div class='checks'>" + boxes + "</div>"
                + (f"<div class='form-grid' style='margin-top:.75rem'>{extra}</div>"
                   if extra else "")
                + "<div class='actions'><button>Jalankan</button></div>"
                "</form></div>")


def parse_bobot(text: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in text.replace(",", "\n").splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = float(v.strip())
    return out


def int_or(d: dict[str, list[str]], key: str):
    v = one(d, key).strip()
    return int(v) if v else None


# ---------- router ----------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # sunyi
        pass

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        p = url.path.rstrip("/") or "/"
        try:
            if p == "/":
                send(self, home())
            elif p == "/kelas":
                send(self, kelas_list())
            elif p == "/lomba/baru":
                send(self, lomba_baru())
            elif p == "/banding":
                send(self, pilih_lomba("/banding/jalan", "Banding skema"))
            elif p == "/lintas":
                send(self, pilih_lomba("/lintas/jalan", "Lintas lomba"))
            elif p == "/optimasi":
                send(self, pilih_lomba("/optimasi/jalan", "Optimasi multi-lomba"))
            elif p.startswith("/lomba/"):
                parts = p.split("/")[2:]
                lid = parts[0]
                if len(parts) == 1:
                    send(self, lomba_detail(lid))
                elif parts[1] == "banding":
                    send(self, lomba_banding(lid))
                elif parts[1] == "whatif":
                    send(self, lomba_whatif(lid))
                elif parts[1] == "probabilitas":
                    send(self, lomba_prob(lid))
                elif parts[1] == "manual":
                    send(self, lomba_manual(lid))
                elif parts[1] == "hasil":
                    send(self, lomba_hasil(lid))
                else:
                    send(self, page("404",
                                    "<div class='card'>Halaman tak dikenal.</div>"), 404)
            else:
                send(self, page("404", "<div class='card'>Halaman tak dikenal.</div>"), 404)
        except ValueError as e:
            send(self, page("Error",
                            f"<div class='card'><p>{esc(e)}</p>"
                            "<p><a href='/'>Beranda</a></p></div>"), 404)
        except Exception as e:  # jangan bocorkan stack ke panitia
            send(self, page("Error",
                            f"<div class='card'>Terjadi kesalahan: {esc(e)}</div>"), 500)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        p = url.path.rstrip("/") or "/"
        d = form(self)
        try:
            if p == "/kelas/tambah":
                cid, nama = one(d, "id").strip(), one(d, "nama").strip() or one(d, "id").strip()
                STORE["registry"].add(ClassInfo(id=cid, name=nama,
                                                tingkat=one(d, "tingkat").strip()))
                STORE["msg"] = f"Kelas {cid} ditambah."
                redirect(self, "/kelas")
            elif p == "/kelas/hapus":
                cid = one(d, "id")
                reg = STORE["registry"]
                kept = [c for c in reg.list_all() if c.id != cid]
                if len(kept) == reg.count():
                    raise ValueError(f"Kelas tak dikenal: {cid}.")
                reg._classes = {c.id: c for c in kept}
                STORE["msg"] = f"Kelas {cid} dihapus."
                redirect(self, "/kelas")
            elif p == "/lomba/buat":
                ikut, _ = select_participants(
                    STORE["registry"], d.get("peserta", []))
                t = Tournament(
                    id=new_lomba_id(), name=one(d, "nama") or "Lomba",
                    format=one(d, "format") or "knockout",
                    team_size=int(one(d, "team_size") or 4),
                    winner_count=int(one(d, "winner_count") or 1),
                    duration_min=int(one(d, "duration_min") or 30),
                    minimum_rest_min=int(one(d, "minimum_rest_min") or 10),
                    arena_count=int(one(d, "arena_count") or 2),
                    qualify_per_group=int(one(d, "qualify_per_group") or 1),
                    start_time=one(d, "start_time") or "08:00",
                    end_time=one(d, "end_time") or "17:00")
                lid = t.id
                STORE["lomba"][lid] = {"tournament": t, "peserta": ikut,
                                       "scheme": None, "scheduled": None,
                                       "results": {}}
                redirect(self, f"/lomba/{lid}")
            elif p == "/lomba/reset":
                rec = get_lomba(one(d, "id"))
                rec["scheme"] = rec["scheduled"] = None
                rec["results"] = {}
                STORE["msg"] = "Skema & skor dikembalikan ke hasil generate."
                redirect(self, f"/lomba/{one(d, 'id')}")
            elif p == "/banding/jalan":
                reps = [report_of(get_lomba(lid)) for lid in d.get("ids", [])]
                table = compare_reports(reps, d.get("ids", []))
                send(self, page("Banding",
                                "<div class='card'><h2>Hasil banding</h2>"
                                f"<pre>{esc(render_comparison(d.get('ids', []), table))}"
                                "</pre></div>"))
            elif p == "/lintas/jalan":
                reps = [report_of(get_lomba(lid)) for lid in d.get("ids", [])]
                found = detect_cross_event_conflicts(reps)
                total = total_load_across_events(reps)
                body = "".join(f"<div class='err'>{esc(c)}</div>" for c in found) \
                    or "<div class='flash'>Tanpa temuan bentrok.</div>"
                body += "<div class='card'><h2>Total load antar lomba</h2><pre>" + esc(
                    "\n".join(f"{k}: {v}" for k, v in total.items())) + "</pre></div>"
                send(self, page("Lintas lomba", body))
            elif p == "/optimasi/jalan":
                specs = [(get_lomba(lid)["tournament"], get_lomba(lid)["peserta"])
                         for lid in d.get("ids", [])]
                after, notes = optimize_multi_event(
                    specs, max_shift_batches=int(one(d, "max_shift_batches") or 12))
                body = "".join(f"<p>* {esc(n)}</p>" for n in notes)
                left = detect_cross_event_conflicts(after)
                body += "".join(f"<div class='err'>{esc(c)}</div>" for c in left) \
                    or "<div class='flash'>0 BENTROK tersisa.</div>"
                send(self, page("Optimasi", body))
            elif p.startswith("/lomba/"):
                parts = p.split("/")[2:]
                lid, rec = parts[0], get_lomba(parts[0])
                if parts[1] == "whatif" and parts[2] == "hitung":
                    ch: dict = {}
                    if one(d, "remove").strip():
                        ch["remove"] = [x.strip() for x in one(d, "remove").split(",")]
                    if one(d, "add").strip():
                        ch["add"] = [x.strip() for x in one(d, "add").split(",")]
                    for k in ("format", "team_size", "winner_count", "duration_min",
                              "minimum_rest_min", "arena_count", "start_time",
                              "end_time", "qualify_per_group"):
                        v = one(d, k).strip()
                        if v and k == "format":
                            ch[k] = v
                        elif v:
                            ch[k] = int(v)
                    ng = int_or(d, "num_groups")
                    if ng is not None:
                        ch["num_groups"] = ng
                    before, after = what_if(rec["tournament"], rec["peserta"], ch,
                                            None, STORE["registry"])
                    assert before.fairness and after.fairness
                    table = compare_reports([before, after], ["sebelum", "sesudah"])
                    send(self, page(f"What-if ({lid})",
                                    lomba_nav(lid)
                                    + "<div class='card'><h2>Perbandingan sebelum vs sesudah</h2>"
                                    + f"<pre>{esc(render_comparison(['sebelum', 'sesudah'], table))}"
                                    "</pre>"
                                    "<form method='post' "
                                    f"action='/lomba/{esc(lid)}/whatif/simpan'>"
                                    + "".join(
                                        f"<input type='hidden' name='{esc(k)}' "
                                        f"value='{esc(','.join(map(str, v)) if isinstance(v, list) else v)}'>"
                                        for k, v in {**ch, **(
                                            {"num_groups": ng} if ng is not None else {})}.items())
                                    + "<div class='actions'>"
                                    "<button>Simpan sebagai lomba baru</button></div>"
                                    "</form></div>"))
                elif parts[1] == "whatif" and parts[2] == "simpan":
                    ch2: dict = {}
                    for k in ("format", "team_size", "winner_count", "duration_min",
                              "minimum_rest_min", "arena_count", "start_time",
                              "end_time", "num_groups", "qualify_per_group"):
                        v = one(d, k).strip()
                        if v:
                            ch2[k] = v if k in ("format", "start_time", "end_time") else int(v)
                    for k in ("remove", "add"):
                        if one(d, k).strip():
                            ch2[k] = [x.strip() for x in one(d, k).split(",") if x.strip()]
                    ng2 = ch2.pop("num_groups", None)
                    nt, npes = apply_changes(rec["tournament"], rec["peserta"], ch2,
                                             STORE["registry"])
                    nid = new_lomba_id()
                    nt = Tournament(**{**nt.__dict__, "id": nid,
                                       "name": rec["tournament"].name + " (what-if)"})
                    STORE["lomba"][nid] = {"tournament": nt, "peserta": npes,
                                           "scheme": generate_scheme(nt, npes, ng2)
                                           if ng2 is not None else None,
                                           "scheduled": None,
                                           "results": {}}
                    STORE["msg"] = f"What-if disimpan sebagai {nid}."
                    redirect(self, f"/lomba/{nid}")
                elif parts[1] == "probabilitas" and parts[2] == "hitung":
                    rep = report_of(rec)
                    mode = one(d, "mode")
                    bobot = parse_bobot(one(d, "bobot"))
                    n = min(int(one(d, "n") or 2000), 50000)
                    seed = int_or(d, "seed")
                    if mode == "equal":
                        model = equal_model(rep.scheme.participant_ids)
                    elif mode == "persen":
                        model = percent_model(bobot, rep.scheme.participant_ids)
                    else:
                        model = custom_model(bobot, rep.scheme.participant_ids)
                    mc = monte_carlo(rep.scheme, model, n=n, seed=seed)
                    send(self, page(f"Probabilitas ({lid})",
                                    lomba_nav(lid)
                                    + "<div class='card'><h2>Hasil simulasi</h2>"
                                    + f"<pre>{esc(render_probability(mc))}</pre></div>"))
                elif parts[1] == "skor" and (len(parts) > 2) and parts[2] == "hapus":
                    mid = one(d, "match_id")
                    rec["results"] = clear_result(rec.get("results") or {}, mid)
                    STORE["msg"] = f"Skor {mid} dihapus."
                    redirect(self, f"/lomba/{lid}/hasil")
                elif parts[1] == "skor":
                    rep = report_of(rec)
                    mid = one(d, "match_id")
                    results = dict(rec.get("results") or {})
                    if mid == "__all__":
                        n = 0
                        for m in rep.scheme.matches:
                            sa = one(d, f"sa_{m.id}").strip()
                            sb = one(d, f"sb_{m.id}").strip()
                            if not sa and not sb:
                                continue
                            results[m.id] = record_result(
                                rep.scheme, m.id, int(sa or 0), int(sb or 0),
                                results=results)
                            n += 1
                        rec["results"] = results
                        STORE["msg"] = f"{n} skor disimpan."
                    else:
                        results[mid] = record_result(
                            rep.scheme, mid,
                            int(one(d, f"sa_{mid}") or 0),
                            int(one(d, f"sb_{mid}") or 0),
                            results=results)
                        rec["results"] = results
                        STORE["msg"] = f"Skor {mid} disimpan."
                    redirect(self, f"/lomba/{lid}/hasil")
                elif parts[1] == "manual":
                    rep = report_of(rec)
                    op = parts[2]
                    if op == "swap":
                        rec["scheme"] = swap_slots(
                            rep.scheme, one(d, "a"), one(d, "sa") or "a",
                            one(d, "b"), one(d, "sb") or "a")
                        rec["scheduled"] = None
                        rec["results"] = {}
                    elif op == "pindah":
                        base = rep.scheduled
                        rec["scheduled"] = move_match(
                            base, one(d, "mid"), one(d, "jam"),
                            int(one(d, "arena") or 1), rec["tournament"])
                        if rec["scheme"] is None:
                            rec["scheme"] = rep.scheme
                    elif op == "ganti":
                        rec["scheme"] = replace_participant(
                            rep.scheme, one(d, "old"), one(d, "new"))
                        rec["scheduled"] = None
                        rec["peserta"] = rec["scheme"].participant_ids
                        rec["results"] = {}
                    elif op == "wo":
                        rec["scheme"] = set_walkover(
                            rep.scheme, one(d, "mid"), one(d, "w"))
                        rec["scheduled"] = None
                        rec["results"] = {}
                    STORE["msg"] = "Edit manual diterapkan + analisis ulang."
                    redirect(self, f"/lomba/{lid}")
                else:
                    send(self, page("404",
                                    "<div class='card'>Aksi tak dikenal.</div>"), 404)
            else:
                send(self, page("404",
                                "<div class='card'>Halaman tak dikenal.</div>"), 404)
        except ValueError as e:
            send(self, page("Error",
                            f"<div class='card'><p>{esc(e)}</p>"
                            "<p><a href='/'>Beranda</a></p></div>"), 400)
        except Exception as e:
            send(self, page("Error",
                            f"<div class='card'>Terjadi kesalahan: {esc(e)}</div>"), 500)


def lan_ips() -> list[str]:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return [ip] if not ip.startswith("127.") else []
    except OSError:
        return []


def run(port: int = 8000, db: str | None = None,
        host: str = "127.0.0.1") -> ThreadingHTTPServer:
    if db is not None:
        from tournament.store import SQLiteStore
        STORE["store"] = SQLiteStore(db)
        reg, lomba, seq = STORE["store"].load_all()
        STORE.update(registry=reg, lomba=lomba, seq=seq)
    return ThreadingHTTPServer((host, port), Handler)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", default="127.0.0.1",
                    help="127.0.0.1 (hanya mesin ini, default) atau "
                         "0.0.0.0 (akses dari perangkat lain di LAN).")
    ap.add_argument("--db", default="tournament.db",
                    help="File SQLite (default tournament.db di folder kerja). "
                         "Kosongkan (--db '') untuk mode in-memory.")
    args = ap.parse_args()
    srv = run(args.port, args.db or None, args.host)
    print(f"Buka http://localhost:{args.port}")
    if args.host == "0.0.0.0":
        for ip in lan_ips():
            print(f"Perangkat lain: http://{ip}:{args.port}")
        print("Tips: izinkan Python di Windows Firewall bila diminta.")
    elif args.host == "127.0.0.1":
        print("(Hanya mesin ini. Untuk akses LAN: --host 0.0.0.0)")
    if args.db:
        print(f"Database: {args.db}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if STORE["store"] is not None:
            persist()
            STORE["store"].close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

