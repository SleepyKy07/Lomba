"""Scenario Comparison (PRD §11): beberapa skema berdampingan.

Tanpa label "pemenang" subjektif — panitia memilih dari data transparan.
"""
from __future__ import annotations

from .analysis import SchemeReport

METRICS: list[tuple[str, str]] = [
    ("format", "Format"),
    ("participants", "Peserta"),
    ("total_matches", "Total pertandingan"),
    ("match_diff", "Match difference"),
    ("rest_diff", "Rest difference (mnt)"),
    ("bye", "Bye"),
    ("player_load_diff", "Player-load difference"),
    ("conflicts", "Conflict"),
]


def compare_reports(reports: list[SchemeReport], labels: list[str]) -> dict[str, list]:
    """Kembalikan {nama_metrik: [nilai per skema]}."""
    if len(reports) != len(labels):
        raise ValueError("Jumlah reports dan labels harus sama.")
    if not reports:
        raise ValueError("Minimal 1 skema untuk dibandingkan.")
    rows = {key: [] for key, _ in METRICS}
    for rep in reports:
        row = rep.summary_row()
        for key, _ in METRICS:
            rows[key].append(row[key])
    return rows


def render_comparison(labels: list[str], table: dict[str, list]) -> str:
    """Render tabel perbandingan gaya PRD §11."""
    name_of = dict(METRICS)
    missing = [k for k, _ in METRICS if k not in table]
    if missing:
        raise ValueError(f"Tabel perbandingan kurang metrik: {missing}.")
    bad = [k for k, _ in METRICS if len(table[k]) != len(labels)]
    if bad:
        raise ValueError(f"Jumlah nilai tak sesuai labels: {bad}.")
    head = "| Metrik | " + " | ".join(labels) + " |"
    sep = "| --- | " + " | ".join(["---:"] * len(labels)) + " |"
    lines = ["== COMPARISON ==", head, sep]
    for key, _ in METRICS:
        vals = " | ".join(str(v) for v in table[key])
        lines.append(f"| {name_of[key]} | {vals} |")
    lines.append("Panitia memilih berdasarkan kebutuhan kegiatan (tanpa skor tunggal).")
    return "\n".join(lines)
