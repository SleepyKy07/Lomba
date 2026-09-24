"""Cross-event conflict + beban lintas lomba (PRD §8.6).

Satu kelas dapat mengikuti beberapa lomba: deteksi bila dijadwalkan di
dua lomba pada waktu yang sama (bentrok) atau terlalu berdekatan
(jeda di bawah batas istirahat minimum).

Batasan jujur: load knockout hanya dari slot pasti (ronde TBD tak
terhitung, warisan Phase 1); pasangan lomba dengan tanggal berbeda
(diisi keduanya) tidak dibandingkan.
"""
from __future__ import annotations

from .analysis import SchemeReport
from .models import is_placeholder, minutes_to_hhmm


def _intervals(
    rep: SchemeReport, idx: int
) -> dict[str, list[tuple[int, int, int, str]]]:
    """Kelas -> [(mulai, selesai, indeks_report, id_match)]."""
    t = rep.scheme.tournament
    out: dict[str, list[tuple[int, int, int, str]]] = {}
    for s in rep.scheduled:
        end = s.start_min + t.duration_min
        for slot in (s.match.participant_a, s.match.participant_b):
            if is_placeholder(slot):
                continue
            assert slot is not None
            out.setdefault(slot, []).append((s.start_min, end, idx, s.match.id))
    return out


def detect_cross_event_conflicts(reports: list[SchemeReport]) -> list[str]:
    """Bandingkan jadwal antar lomba (identitas = posisi report, bukan id).

    Overlap diperiksa semua pasangan (aman untuk durasi berbeda);
    "terlalu dekat" diperiksa pasangan berurutan.
    """
    if len(reports) < 2:
        return []
    per_class: dict[str, list[tuple[int, int, int, str, str, str]]] = {}
    # (mulai, selesai, idx_report, id_lomba, tanggal, id_match)
    rest_min: dict[int, int] = {}
    for idx, rep in enumerate(reports):
        t = rep.scheme.tournament
        rest_min[idx] = t.minimum_rest_min
        for pid, ivs in _intervals(rep, idx).items():
            for s, e, _, m in ivs:
                per_class.setdefault(pid, []).append((s, e, idx, t.id, t.date, m))
    findings: list[str] = []
    for pid in sorted(per_class):
        ivs = sorted(per_class[pid])
        # 1. Overlap: semua pasangan (durasi boleh beda).
        seen_overlap: set[tuple[int, str, int, str]] = set()
        for i in range(len(ivs)):
            for j in range(i + 1, len(ivs)):
                s1, e1, a, t1, d1, m1 = ivs[i]
                s2, e2, b, t2, d2, m2 = ivs[j]
                if a == b:
                    continue  # konflik internal = Phase 1
                if reports[a] is reports[b]:
                    continue  # objek report yang sama diteruskan dua kali
                if d1 and d2 and d1 != d2:
                    continue  # hari berbeda
                if s2 < e1 and s1 < e2:
                    key = (a, m1, b, m2) if (a, m1) <= (b, m2) else (b, m2, a, m1)
                    if key not in seen_overlap:
                        seen_overlap.add(key)
                        findings.append(
                            f"{pid} BENTROK: {t1}/{m1} ({minutes_to_hhmm(s1)}) vs "
                            f"{t2}/{m2} ({minutes_to_hhmm(s2)})."
                        )
        # 2. Terlalu dekat: pasangan berurutan beda lomba, tanpa overlap.
        for (s1, e1, a, t1, d1, m1), (s2, e2, b, t2, d2, m2) in zip(ivs, ivs[1:]):
            if a == b:
                continue
            if reports[a] is reports[b]:
                continue
            if d1 and d2 and d1 != d2:
                continue
            if s2 >= e1:
                need = max(rest_min[a], rest_min[b])
                if s2 - e1 < need:
                    findings.append(
                        f"{pid} terlalu dekat: {t1}/{m1} -> {t2}/{m2} "
                        f"(jeda {s2 - e1} mnt < {need} mnt)."
                    )
    return findings


def total_load_across_events(reports: list[SchemeReport]) -> dict[str, int]:
    """Total player-load per kelas di semua lomba (match × team_size).

    Knockout hanya menghitung slot pasti yang terjadwal.
    """
    total: dict[str, int] = {}
    for rep in reports:
        if rep.fairness is None:
            raise ValueError("SchemeReport belum dianalisis (fairness kosong).")
        for pid, load in rep.fairness.player_load.items():
            total[pid] = total.get(pid, 0) + load
    return dict(sorted(total.items()))
