"""Salin engine Python -> docs/_engine/tournament untuk Pyodide (Tahap 3).

Usage: python scripts/sync_engine_to_docs.py
Jalankan ulang setiap ubah src/tournament/*.py sebelum deploy Pages.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "tournament"
DST = ROOT / "docs" / "_engine" / "tournament"

# store.py: sqlite opsional — tetap disalin agar package utuh bila dibutuhkan.
SKIP: set[str] = set()


def main() -> int:
    if not SRC.is_dir():
        print(f"FAIL missing {SRC}")
        return 1
    if DST.exists():
        shutil.rmtree(DST)
    DST.mkdir(parents=True)
    n = 0
    for f in sorted(SRC.glob("*.py")):
        if f.name in SKIP:
            continue
        shutil.copy2(f, DST / f.name)
        n += 1
        print(f"OK  {f.name}")
    # penanda agar folder tidak kosong di git
    (DST / ".gitkeep").write_text("synced by scripts/sync_engine_to_docs.py\n", encoding="utf-8")
    print(f"SYNC_OK {n} files -> {DST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
