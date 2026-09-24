"""Cek cepat frontend Tahap 1: static serve + tidak ada secret key.

Usage: python scripts/check_phase1.py
- Serve docs/ sebentar, GET / dan /kelas.html
- Scan docs/**/* untuk pola service_role / sb_secret_
- node --check semua docs/js/*.js bila Node tersedia
"""
from __future__ import annotations

import http.server
import re
import socketserver
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FAIL: list[str] = []
OK: list[str] = []


def ok(msg: str) -> None:
    OK.append(msg)
    print(f"OK  {msg}")


def fail(msg: str) -> None:
    FAIL.append(msg)
    print(f"FAIL {msg}")


def scan_secrets() -> None:
    # Nilai key nyata, BUKAN kata "service_role" di komentar/larangan UI.
    # Catatan: docs/js/config.js BOLEH memuat anon public key (JWT role=anon)
    # untuk GitHub Pages — tetap DILARANG service_role / sb_secret di file mana pun.
    patterns = [
        (re.compile(r"sb_secret_[A-Za-z0-9]{10,}"), "sb_secret value"),
        (re.compile(r"service_role\s*[:=]\s*[\"'][^\"']{20,}[\"']"), "service_role assignment"),
        (
            re.compile(r"eyJhbGciOi[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
            "raw JWT",
        ),
    ]
    for path in DOCS.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".js", ".html", ".css", ".md", ".json", ".toml"}:
            continue
        is_config = path.name == "config.js" and path.parent.name == "js"
        text = path.read_text(encoding="utf-8", errors="replace")
        for pat, label in patterns:
            if not pat.search(text):
                continue
            if is_config and label == "raw JWT":
                # anon key = JWT publik; pastikan BUKAN role service_role
                if '"role":"service_role"' in text or "%22service_role%22" in text:
                    fail("docs/js/config.js memuat JWT service_role")
                else:
                    ok("docs/js/config.js: anon public key terisi (role != service_role)")
                continue
            fail(f"{label} di {path.relative_to(ROOT)}")
    cfg = DOCS / "js" / "config.js"
    if cfg.is_file():
        ctext = cfg.read_text(encoding="utf-8", errors="replace")
        if "YOUR_PROJECT_REF" in ctext or "YOUR_ANON_PUBLIC_KEY" in ctext:
            fail("docs/js/config.js masih placeholder — isi Supabase URL + anon key")
        elif "SUPABASE_URL" not in ctext:
            fail("docs/js/config.js tidak memuat SUPABASE_URL")
    if not any(f.startswith(("raw JWT", "sb_secret", "service_role")) for f in FAIL):
        ok("Tidak ada service_role / sb_secret terekspos di docs/")


def serve_and_get() -> None:
    handler_cls = http.server.SimpleHTTPRequestHandler

    class Quiet(handler_cls):
        def log_message(self, *args):  # noqa: D102
            pass

    def factory(*args, **kwargs):
        return Quiet(*args, directory=str(DOCS), **kwargs)

    with socketserver.TCPServer(("127.0.0.1", 0), factory) as httpd:
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        try:
            paths = (
                "/",
                "/kelas.html",
                "/login.html",
                "/lomba.html",
                "/lomba_detail.html",
                "/banding.html",
                "/lintas.html",
                "/js/api.js",
                "/js/auth.js",
                "/js/pyengine.js",
                "/js/page.js",
                "/js/lomba.js",
                "/js/lomba_detail.js",
                "/js/banding.js",
                "/js/lintas.js",
                "/js/config.js",
                "/css/styles.css",
                "/_engine/tournament/__init__.py",
                "/_engine/tournament/models.py",
                "/_engine/tournament/results.py",
                "/_engine/tournament/whatif.py",
                "/_engine/tournament/comparison.py",
                "/_engine/tournament/probability.py",
                "/_engine/tournament/cross_event.py",
                "/_engine/tournament/multi.py",
            )
            for path in paths:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}") as r:
                    body = r.read()
                    if r.status != 200 or not body:
                        fail(f"GET {path} -> {r.status}")
                    else:
                        ok(f"GET {path} ({len(body)} bytes)")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/kelas.html") as r:
                html = r.read().decode("utf-8")
            for marker in ("Master Kelas", "form-tambah", "js/api.js", "js/auth.js"):
                if marker not in html:
                    fail(f"kelas.html kurang marker: {marker}")
                else:
                    ok(f"marker {marker!r} ada")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/login.html") as r:
                login_html = r.read().decode("utf-8")
            for marker in ("form-login", "js/auth.js"):
                if marker not in login_html:
                    fail(f"login.html kurang marker: {marker}")
                else:
                    ok(f"login marker {marker!r} ada")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/lomba.html") as r:
                lomba_html = r.read().decode("utf-8")
            for marker in ("form-buat", "js/pyengine.js", "js/lomba.js"):
                if marker not in lomba_html:
                    fail(f"lomba.html kurang marker: {marker}")
                else:
                    ok(f"lomba marker {marker!r} ada")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/lomba_detail.html") as r:
                detail_html = r.read().decode("utf-8")
            for marker in (
                "pane-hasil",
                "pane-manual",
                "form-wo",
                "form-swap",
                "form-move",
                "form-replace",
                "pane-whatif",
                "pane-prob",
                "js/page.js",
                'id="skor-table"',
            ):
                if marker not in detail_html:
                    fail(f"lomba_detail.html kurang marker: {marker}")
                else:
                    ok(f"detail marker {marker!r} ada")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/banding.html") as r:
                banding_html = r.read().decode("utf-8")
            for marker in ("btn-banding", "js/banding.js", "js/pyengine.js"):
                if marker not in banding_html:
                    fail(f"banding.html kurang marker: {marker}")
                else:
                    ok(f"banding marker {marker!r} ada")
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/lintas.html") as r:
                lintas_html = r.read().decode("utf-8")
            for marker in ("btn-lintas", "btn-optimasi", "js/lintas.js"):
                if marker not in lintas_html:
                    fail(f"lintas.html kurang marker: {marker}")
                else:
                    ok(f"lintas marker {marker!r} ada")
            for page in ("index.html", "kelas.html", "login.html", "lomba.html"):
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/{page}") as r:
                    html = r.read().decode("utf-8")
                for marker in ("banding.html", "lintas.html"):
                    if marker not in html:
                        fail(f"{page} kurang nav {marker}")
                    else:
                        ok(f"nav {page} -> {marker}")
        finally:
            httpd.shutdown()
            t.join(timeout=2)


def check_js_syntax() -> None:
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        print("SKIP node --check (Node tidak tersedia)")
        return
    for js in sorted((DOCS / "js").glob("*.js")):
        r = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
        if r.returncode != 0:
            fail(f"node --check {js.name}: {r.stderr.strip()}")
        else:
            ok(f"node --check {js.name}")


def check_global_iife() -> None:
    """File yang memakai global.* harus IIFE dengan param (global) + })(window).

    Regresi: login.js dulu (function(){ tanpa param) -> 'global is not defined'
    di runtime (lolos node --check karena ReferenceError hanya saat eksekusi).
    """
    import re

    for js in sorted((DOCS / "js").glob("*.js")):
        text = js.read_text(encoding="utf-8", errors="replace")
        if "global." not in text:
            continue
        if not re.search(r"\(function\s*\(\s*global\s*\)", text):
            fail(f"{js.name} pakai global.* tapi IIFE tanpa param (global)")
        elif not re.search(r"\}\)\(\s*window\s*\);", text):
            fail(f"{js.name} IIFE param global tapi penutup bukan }})(window)")
        else:
            ok(f"{js.name} IIFE global OK")


def check_bridge_exports() -> None:
    """BRIDGE di pyengine.js harus import nama yang ada di package tournament."""
    js = (DOCS / "js" / "pyengine.js").read_text(encoding="utf-8", errors="replace")
    import re

    m = re.search(r"from tournament import \((.*?)\)", js, re.S)
    if not m:
        fail("pyengine.js: blok 'from tournament import' tidak ditemukan")
        return
    names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", m.group(1))
    init = (ROOT / "src" / "tournament" / "__init__.py").read_text(
        encoding="utf-8", errors="replace"
    )
    all_m = re.search(r"__all__\s*=\s*\[(.*?)\]", init, re.S)
    exported = (
        set(re.findall(r"[\"']([A-Za-z_][A-Za-z0-9_]*)[\"']", all_m.group(1)))
        if all_m
        else set()
    )
    missing = [n for n in names if n not in exported]
    if missing:
        fail("BRIDGE import tidak ada di __all__: " + ", ".join(missing))
    else:
        ok(f"BRIDGE import cocok __all__ ({len(names)} nama)")

    m2 = re.search(r"from tournament\.models import \((.*?)\)", js, re.S)
    if m2:
        names2 = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", m2.group(1))
        models_src = (ROOT / "src" / "tournament" / "models.py").read_text(
            encoding="utf-8", errors="replace"
        )
        miss2 = [
            n
            for n in names2
            if not re.search(rf"class {n}\b|def {n}\b|^{n}\s*=", models_src, re.M)
        ]
        if miss2:
            fail("BRIDGE models import tidak ada: " + ", ".join(miss2))
        else:
            ok(f"BRIDGE models import cocok ({len(names2)} nama)")


def check_no_python_dep_in_docs() -> None:
    # frontend tidak boleh import engine Python / STORE / sqlite di runtime JS.
    # "from tournament" di pyengine.js = bridge Pyodide (diperbolehkan).
    bad = []
    for path in DOCS.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".js", ".html"}:
            continue
        if path.name == "pyengine.js":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in ("import sqlite3", "from tournament", "STORE[", "require('sqlite3')"):
            if token in text:
                bad.append(f"{path.name}:{token}")
        if "import web" in text or "python web.py" in text:
            bad.append(f"{path.name}:web.py")
    if bad:
        fail("frontend masih rujuk Python runtime: " + ", ".join(bad))
    else:
        ok("frontend tidak import engine Python / STORE / sqlite (di luar Pyodide bridge)")


def main() -> int:
    if not DOCS.is_dir():
        fail("docs/ belum ada")
        return 1
    scan_secrets()
    check_no_python_dep_in_docs()
    check_js_syntax()
    check_global_iife()
    check_bridge_exports()
    serve_and_get()
    print()
    print(f"Total OK={len(OK)} FAIL={len(FAIL)}")
    if FAIL:
        for f in FAIL:
            print(" -", f)
        return 1
    print("PHASE1_STATIC_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
