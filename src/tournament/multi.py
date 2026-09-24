"""Multi-lomba optimization (Phase 3): koordinasi jadwal antar lomba.

Strategi: time-shift. Lomba pertama dijadwalkan apa adanya; setiap
lomba berikut digeser maju per kelipatan durasinya hingga BENTROK
antar-lomba hilang (atau temuan minimal), selama masih muat di jendela
waktu. Pergeseran utuh menjaga urutan ronde + jeda internal.
"""
from __future__ import annotations

from dataclasses import replace

from .analysis import SchemeReport, analyze_existing, build_report
from .cross_event import detect_cross_event_conflicts
from .models import minutes_to_hhmm


def shift_report(report: SchemeReport, batches: int) -> SchemeReport:
    """Geser seluruh jadwal report maju N batch (N x durasi lomba itu)."""
    if batches < 0:
        raise ValueError("batches minimal 0.")
    t = report.scheme.tournament
    shifted = [
        replace(
            s,
            start_min=s.start_min + batches * t.duration_min,
            scheduled_time=minutes_to_hhmm(s.start_min + batches * t.duration_min),
        )
        for s in report.scheduled
    ]
    return analyze_existing(report.scheme, shifted)


def _bentrok_count(findings: list[str]) -> int:
    return sum(1 for f in findings if "BENTROK" in f)


def optimize_multi_event(
    specs: list[tuple],
    scheduler: str = "greedy",
    max_shift_batches: int = 12,
) -> tuple[list[SchemeReport], list[str]]:
    """specs = [(tournament, participant_ids[, num_groups])].

    Lomba pertama tak pernah digeser (hasil tergantung urutan specs).
    Seleksi kandidat: BENTROK minimum, lalu total temuan minimum.
    Kembalikan (reports_final, notes). Jujur bila sisa temuan tak
    terhindarkan (jendela waktu habis).
    """
    if not specs:
        raise ValueError("Minimal 1 lomba.")
    if max_shift_batches < 0:
        raise ValueError("max_shift_batches minimal 0.")
    reports: list[SchemeReport] = []
    notes: list[str] = []
    for pos, spec in enumerate(specs):
        if len(spec) < 2 or len(spec) > 3:
            raise ValueError(
                f"Spec #{pos} harus (tournament, participant_ids[, num_groups])."
            )
        tournament, pids = spec[0], spec[1]
        ng = spec[2] if len(spec) > 2 else None
        base = build_report(tournament, list(pids), ng, scheduler)
        if base.sched_errors:
            notes.append(f"{tournament.id}: jadwal dasar sudah overflow.")
            reports.append(base)
            continue
        if not reports:
            reports.append(base)
            continue
        best: SchemeReport | None = None
        best_key: tuple[int, int] | None = None
        best_findings: list[str] = []
        best_k = 0
        for k in range(max_shift_batches + 1):
            cand = base if k == 0 else shift_report(base, k)
            if cand.sched_errors:
                break  # makin jauh makin tak muat
            findings = detect_cross_event_conflicts([*reports, cand])
            key = (_bentrok_count(findings), len(findings))
            if best_key is None or key < best_key:
                best, best_key, best_findings, best_k = cand, key, findings, k
            if key == (0, 0):
                break
        assert best is not None and best_key is not None
        if best_k > 0:
            notes.append(
                f"{tournament.id} digeser +{best_k} batch "
                f"({base.scheme.tournament.duration_min} mnt/batch) "
                "demi menghindari bentrok lintas lomba."
            )
        if best_key[0] > 0:
            notes.append(
                f"{tournament.id}: sisa {best_key[0]} BENTROK "
                "tak terhindarkan dalam jendela waktu."
            )
        reports.append(best)
    return reports, notes


def k_shift_of(base: SchemeReport, cand: SchemeReport) -> int:
    """Selisih batch antara kandidat dan jadwal dasar (asumsi shift utuh)."""
    if not base.scheduled or not cand.scheduled:
        return 0
    dur = base.scheme.tournament.duration_min
    return round((cand.scheduled[0].start_min - base.scheduled[0].start_min) / dur)
