"""Demo CLI Phase 1 — tanpa dependensi eksternal.

Skenario PRD: master 28 kelas, subset 23/6 peserta (kasus nyata §16),
format knockout / preliminary / round_robin / group, lalu cetak
bracket/schedule/fairness (§13).

Cara jalan:  python app.py [--peserta 6|23] [--format knockout|...]
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from tournament import (  # noqa: E402
    VALID_FORMATS,
    Tournament,
    analyze_rest,
    analyze_scheme,
    build_default_master,
    detect_internal_conflict,
    generate_scheme,
    render_bracket,
    render_fairness,
    render_schedule,
    schedule_matches,
    select_participants,
)


def run_demo(peserta_n: int, fmt: str) -> int:
    registry = build_default_master(28)
    semua = [c.id for c in registry.list_all()]
    peserta, tidak_ikut = select_participants(registry, semua[:peserta_n])
    t = Tournament(
        id="T1",
        name=f"Demo {fmt} {peserta_n} peserta",
        format=fmt,  # type: ignore[arg-type]
        team_size=4,
        winner_count=1,
        duration_min=30,
        minimum_rest_min=10,
        arena_count=2,
        start_time="08:00",
        end_time="17:00",
    )
    print(f"Lomba: {t.name} | format={fmt} 4v4 | peserta={peserta_n} dari 28 kelas")
    print(f"  Tidak ikut ({len(tidak_ikut)}): "
          f"{', '.join(tidak_ikut[:5])}{'...' if len(tidak_ikut) > 5 else ''}")
    scheme = generate_scheme(t, peserta)
    for note in scheme.notes:
        print(f"  * {note}")
    print()
    print(render_bracket(scheme.matches))
    print()
    scheduled, sched_err = schedule_matches(t, scheme.matches)
    for e in sched_err:
        print(f"  ! {e}")
    if sched_err:
        print(f"  ! Jadwal parsial ({len(scheduled)}/{len(scheme.matches)} "
              "match); analisis rest di bawah hanya dari slot terjadwal.")
    print(render_schedule(scheduled))
    print()
    fair = analyze_scheme(t, scheme.participant_ids, scheme.matches,
                          scheme.bye_details)
    rest = analyze_rest(t, scheduled)
    conflicts = detect_internal_conflict(scheduled)
    print(render_fairness(fair, rest, conflicts))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--peserta", type=int, default=6)
    ap.add_argument("--format", default="knockout", choices=list(VALID_FORMATS))
    args = ap.parse_args()
    return run_demo(args.peserta, args.format)


if __name__ == "__main__":
    raise SystemExit(main())
