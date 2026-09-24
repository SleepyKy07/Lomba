# Tournament Scheme & Fairness Simulator

Web app panitia OSIS: buat/bandingkan/analisis skema lomba antar kelas (fairness transparan, bukan "skor keadilan"). Sumber kebenaran requirement: **`PRD.md` (jangan diubah)**. Bahasa komunikasi: Indonesia.

**Status: SELESAI semua fase PRD §19 + hasil/klasemen (§15 Result, §5) + perebutan juara 3 (F3) + walkover isi F3 + qualify_per_group + UI redesign** — **157 test**. Terakhir: UI modern (kartu, subnav lomba, stats badge, form grid, flash alert, responsive viewport; stdlib only, tanpa asset eksternal). Review bugfix gelar-2 — (1) form kelas `name='id' required` (id kosong saat submit); (2) F3 walkover simpan kalah di slot b -> status Peringkat 4 + note bukan "Limitasi" salah konteks; (3) klasemen group murni: `-> juara grup` tanpa "lolos" (lolos hanya group_knockout); (4) `num_groups=0` error (bukan jatuh ke auto via `or` falsy); (5) `_validate_bracket_resolvable` skip F3 (F3 tak inflate `available` / false-OK); (6) whatif simpan `ng2 is not None` (0 tidak diam-diam jadi None).

Gelar-1: (1) F3 walkover tak mengantre ke juara 1 di MC + status Juara 3; (2) `build_standings` resolve slot via `advance_scheme`; (3) web ready-check pakai `is_placeholder`; banding bawa `winner_count`/`qualify_per_group`; (4) `generate_group_knockout` hitung grup dari ID unik; (5) f-string `{available}` + em-dash notes/`render_standings` cp1252-safe; (6) `is_placeholder("Kalahman")=False`.

## Perintah

```bash
python -m unittest discover -s tests   # 157 test, WAJIB jalankan setelah ubah kode
python web.py                          # http://localhost:8000 (127.0.0.1, in-memory bila --db '')
python web.py --host 0.0.0.0 --port 8000 --db tournament.db   # akses LAN + persist
# Windows: klik 2x jalankan.bat (LAN + buka browser otomatis)
python app.py / demo_phase2.py / demo_phase3.py               # demo CLI (opsional)
```

Tanpa dependensi: **stdlib only** (http.server, sqlite3, unittest). Python ≥3.10 (pakai `X | None`).

## Migrasi Tahap 1–4 — Frontend static + Supabase (GitHub Pages)

Fitur di `docs/`: **Master Kelas**, **Buat/Detail Lomba** (Pyodide), **hasil/klasemen**, **what-if**, **probabilitas**, **banding**, **lintas & optimasi multi-lomba**. Tanpa `web.py` / SQLite / `STORE` untuk hosting. **Mode publik: tanpa login** (RLS dimatikan via `0003`).

### Setup (sekali)

1. SQL Editor → `supabase/migrations/0001_init.sql` (tabel + seed).
2. SQL Editor → `supabase/migrations/0002_auth_rls.sql` (opsional, mode login).
3. SQL Editor → `supabase/migrations/0003_public_demo.sql` (**mode publik** — RLS off, tanpa login).
4. Settings → API → **Project URL** + **anon public** → isi `docs/js/config.js`.  
   **Jangan** taruh `service_role` / `sb_secret_*` di frontend.
5. Sinkron engine ke frontend (wajib sebelum serve/deploy):  
   `python scripts/sync_engine_to_docs.py`
6. GitHub Pages: Settings → Pages → Deploy from branch → `main` / folder `/docs`.

### Jalankan frontend lokal (tanpa `web.py`)

```powershell
python scripts/sync_engine_to_docs.py
python -m http.server 8080 --directory docs
```

1. `kelas.html` → kelola master kelas (langsung, tanpa login).
2. `lomba.html` → buat lomba (Pyodide generate ~detik; load pertama bisa lama).
3. `lomba_detail.html?id=L1` → BRACKET / SCHEDULE / FAIRNESS.
4. Tab detail: `&tab=hasil` skor + klasemen · `&tab=manual` walkover/swap/pindah/ganti · `&tab=whatif` · `&tab=prob`.
5. `banding.html` banding beberapa lomba · `lintas.html` bentrok antar-lomba + optimasi time-shift.

### Cek cepat

```bash
python scripts/sync_engine_to_docs.py
python scripts/check_phase1.py   # static + secret + nav/marker Tahap 4
python scripts/smoke_bridge_phase4.py   # fungsi *_json bridge di CPython
python -m unittest discover -s tests   # 157 test engine legacy
```

Tahap 4 selesai (frontend): skor/klasemen, banding, what-if, probabilitas, lintas, optimasi multi — semua via bridge Pyodide + tabel `results` Supabase.

**Manual + walkover (frontend):** tab `&tab=manual` — walkover, tukar slot, pindah jadwal, ganti peserta (engine `manual.py`). Edit struktural hapus semua results + regenerasi jadwal; pindah jadwal tidak hapus skor. Tombol WO juga ada di tab Hasil.

Belum di frontend (opsional lanjutan): simpan hasil optimasi ke `manual_scheduled`, simpan what-if sebagai lomba baru, CI sync engine otomatis.

## Struktur (baca file ini saja, jangan buka semua)

```
docs/                        # FRONTEND static GitHub Pages (Tahap 1–4) — tanpa Python server
  index.html, kelas.html     # beranda + Master Kelas
  login.html                 # redirect ke index (mode publik; auth code disimpan)
  lomba.html, lomba_detail.html # buat + detail (ringkasan/hasil/whatif/prob)
  banding.html, lintas.html  # Tahap 4: banding skema · lintas + optimasi multi
  css/styles.css
  js/config.js               # SUPABASE_URL + anon key (bukan service_role)
  js/api.js                  # Postgrest + Bearer JWT + tournaments/results CRUD + seq
  js/auth.js                 # signUp/signIn/signOut (GoTrue REST)
  js/pyengine.js             # Pyodide + bridge engine Python (Tahap 3–4)
  js/page.js                 # subnav detail + helper engine/login
  js/lomba.js, lomba_detail.js, banding.js, lintas.js, kelas.js, home.js, login.js, main.js
  _engine/tournament/        # salinan src/tournament (sync_engine_to_docs.py; jangan edit di sini)
supabase/
  config.toml
  migrations/0001_init.sql   # skema + seed
  migrations/0002_auth_rls.sql # hapus anon; RLS authenticated + owner_id
  .env.example
scripts/
  sync_engine_to_docs.py     # src/tournament -> docs/_engine/tournament
  check_phase1.py            # smoke static + secret + nav Tahap 4
  smoke_bridge_phase4.py     # eksekusi fungsi *_json bridge di CPython
  serve-frontend.ps1
web.py                     # UI web legacy (dev/LAN): STORE in-memory, Handler router, persist() via redirect();
                           #   layout modern (_CSS inline, topbar+subnav lomba, kartu/stats/form-grid)
jalankan.bat               # launcher Windows (0.0.0.0:8000)
app.py, demo_phase*.py     # demo CLI
src/tournament/
  models.py                # dataclass + KONTRAK: VALID_FORMATS, ROUND_ORDER (termasuk F3), 
                           #   QUALIFIER_PREFIX="Juara Grup", RANK_QUALIFIER_PREFIX="Peringkat",
                           #   LOSER_PREFIX="Kalah" (F3), is_placeholder(), parse_group_qualifier(),
                           #   Tournament.qualify_per_group (group_knockout: 1=juara, 2=+peringkat 2),
                           #   round_sort_key(), Match.status, Result (seri => winner None)
  registry.py              # ClassRegistry, build_default_master(28), select_participants()
  generator*.py            # generate_scheme(tournament, peserta) dispatch; 5 format
  fairness.py              # analyze_scheme, analyze_rest, detect_internal_conflict(scheduled, duration_min)
  scheduler.py             # schedule_matches (greedy), schedule_advanced
  analysis.py              # build_report(t, peserta) | analyze_existing(scheme, scheduled) -> SchemeReport
  comparison.py, whatif.py # compare_reports, what_if / apply_changes
  cross_event.py, multi.py # bentrok antar-lomba, optimize_multi_event
  probability.py           # equal/custom/percent, monte_carlo; BUKAN prediksi kemampuan
  manual.py                # swap_slots, move_match, replace_participant, set_walkover
                           #   (WO ronde sumber F3 isi Kalah {ronde}-N; WO di F3: a=pemenang, b=Peringkat 4;
                           #    non-sumber: catatan limitasi; validasi bracket skip F3)
  results.py               # record_result(..., results=...), advance_scheme, build_standings; poin 3/1/0
                           #   resolve Juara/Peringkat Grup dari klasemen bila grup lengkap
  # F3: perebutan juara 3 bila winner_count>1 — slot Kalah X-1/2; fairness & path-to-title mengecualikan F3;
  #   probability: kalah SF/R1 di-track losers (pos 1-based per ronde, sinkron WO), juara tetap dari F saja
  # group_knockout: qualify_per_group placeholder Juara/Peringkat k Grup; MC + advance resolve dari standings
  bracket.py               # render_* -> teks console (wajib ASCII/cp1252-safe)
  store.py                 # SQLiteStore legacy (web.py lokal): classes/tournaments(+results_json)/meta
tests/                     # phase1/2/3 + store + web + results + third_place + review_fixes
```

API publik re-export di `src/tournament/__init__.py`.

## Kontrak & jebakan (jangan dilanggar)

- **Console cp1252**: `render_*` **dan** `scheme.notes` / pesan error user-facing wajib ASCII (`->` bukan `→`, tanpa em-dash).
- **Skor**: knockout tidak boleh `seri` (error; pakai walkover/koreksi); fase grup/RR seri OK (`winner=None`).
- **record_result** wajib diberi `results=` sebelumnya agar slot ronde lanjutan divalidasi via `advance_scheme` (bukan skema asli yang masih TBD).
- **advance_scheme** hanya untuk TAMPILAN; skema asli tak dimutasi (fairness = desain, bukan hasil).
- Edit struktural (swap/ganti/WO/reset) **menghapus results**; pindah jadwal tidak.
- **Slot TBD**: antrean pemenang = urutan kreasi match (sama dengan probability engine).
- **web.py**: POST mutasi diakhiri `redirect()` -> `persist()`; input HTML lewat `esc()`.
- **SQLite**: wajib lock + `check_same_thread=False`; jangan tambah dependensi luar; jangan ubah `PRD.md`.
- **Fairness**: tanpa label "pemenang" subjektif; jelaskan selisih, bukan skor tunggal.
- `reset_store()` (`tests/test_web.py`) reset STORE in-memory.

## Fitur UI (`web.py`)

Beranda (stats) · master kelas · buat lomba (form grid + **panduan & tips tiap format**, sorot kartu aktif) · detail (subnav, ringkasan badge+stats, bracket/jadwal 2-kolom, fairness, klasemen, reset) · **hasil (isi/hapus skor, klasemen)** · banding · what-if · probabilitas · manual (kartu per aksi) · lintas lomba · optimasi multi-lomba. Flash alert hijau; error merah; mobile viewport.

## Lanjutan yang mungkin diminta

- **Tahap 5 (opsional)**: simpan hasil optimasi ke `manual_scheduled`; simpan what-if sebagai lomba baru; CI auto-sync engine.
- Backup/restore `tournament.db` (legacy lokal); migrasi kolom baru: `SCHEMA` (CREATE) + `ALTER` di `__init__` store + test roundtrip.
- Fitur engine: modul + re-export `__init__` + `tests/test_phaseN.py`; UI legacy: route `Handler` + halaman + `test_web.py`.
