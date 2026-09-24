"""Demo Phase 2 — tanpa dependensi eksternal.

Menampilkan 5 fitur PRD Phase 2:
1. Scenario comparison (3 skema, 6 peserta)
2. What-if (23 -> 22 peserta)
3. Cross-event conflict (2 lomba, kelas sama)
4. Player-load lintas lomba
5. Manual adjustment (tukar lawan + analisis ulang)

Cara jalan:  python demo_phase2.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tournament import (  # noqa: E402
    Tournament,
    analyze_existing,
    build_default_master,
    build_report,
    compare_reports,
    detect_cross_event_conflicts,
    render_comparison,
    render_fairness,
    select_participants,
    swap_slots,
    total_load_across_events,
    what_if,
)


def section(title: str) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}\n")


def main() -> int:
    reg = build_default_master(28)
    semua = [c.id for c in reg.list_all()]

    # 1. Scenario comparison: 6 peserta, 3 format.
    section("1. SCENARIO COMPARISON (6 peserta)")
    p6, _ = select_participants(reg, semua[:6])
    reps, labels = [], []
    for fmt in ("knockout", "group", "round_robin"):
        t = Tournament(id="T6", name=f"demo-{fmt}", format=fmt, team_size=4)
        reps.append(build_report(t, p6))
        labels.append(fmt)
    table = compare_reports(reps, labels)
    print(render_comparison(labels, table))

    # 2. What-if: 23 -> 22 peserta (1 keluar).
    section("2. WHAT-IF (23 -> 22 peserta, knockout)")
    p23, _ = select_participants(reg, semua[:23])
    t23 = Tournament(id="T23", name="voli", format="knockout", team_size=4)
    before, after = what_if(t23, p23, {"remove": ["XII-23"]})
    assert before.fairness is not None and after.fairness is not None
    print(f"Sebelum: {before.fairness.total_matches} match, "
          f"{before.fairness.bye_count} bye")
    print(f"Sesudah: {after.fairness.total_matches} match, "
          f"{after.fairness.bye_count} bye")
    print("What-if menghitung ulang bracket/bye/jadwal/fairness otomatis.")

    # 3-4. Cross-event: 2 lomba jam sama dengan peserta irisan.
    section("3-4. CROSS-EVENT CONFLICT + TOTAL LOAD")
    pa, _ = select_participants(reg, semua[:6])
    pb, _ = select_participants(reg, semua[4:10])  # irisan XII-05, XII-06
    ta = Tournament(id="LA", name="futsal", format="group", team_size=4)
    tb = Tournament(id="LB", name="basket", format="group", team_size=4)
    ra, rb = build_report(ta, pa), build_report(tb, pb)
    for c in detect_cross_event_conflicts([ra, rb]):
        print(f"  ! {c}")
    print("Total load lintas lomba (5 besar):")
    for pid, load in sorted(total_load_across_events([ra, rb]).items(),
                            key=lambda kv: -kv[1])[:5]:
        print(f"  {pid}: {load}")

    # 5. Manual adjustment: tukar lawan lalu analisis ulang.
    section("5. MANUAL ADJUSTMENT (tukar lawan)")
    t = Tournament(id="TM", name="manual", format="knockout", team_size=1)
    rep = build_report(t, ["A", "B", "C", "D", "E", "F"])
    assert rep.fairness is not None
    r1 = [m.id for m in rep.scheme.matches if m.round == "R1"]
    edited = swap_slots(rep.scheme, r1[0], "a", r1[1], "a")
    rep2 = analyze_existing(edited, rep.scheduled)
    assert rep2.fairness is not None and rep2.rest is not None
    print(f"  * {edited.notes[-1]}")
    print(render_fairness(rep2.fairness, rep2.rest, rep2.conflicts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
