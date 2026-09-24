"""Demo Phase 3 — tanpa dependensi eksternal.

1. Probability equal + exact (6 peserta knockout)
2. Probability custom + Monte Carlo (A difavoritkan)
3. Advanced scheduler vs greedy (grup 6, rest violation)
4. Multi-lomba optimization (2 lomba bentrok -> digeser)

Cara jalan:  python demo_phase3.py
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
    custom_model,
    detect_cross_event_conflicts,
    equal_model,
    exact_equal_title_probability,
    monte_carlo,
    optimize_multi_event,
    render_probability,
    select_participants,
)


def section(title: str) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}\n")


def main() -> int:
    reg = build_default_master(28)
    semua = [c.id for c in reg.list_all()]
    p6, _ = select_participants(reg, semua[:6])

    section("1. EQUAL PROBABILITY (6 knockout)")
    t = Tournament(id="TP", name="prob", format="knockout", team_size=1)
    rep = build_report(t, p6)
    model = equal_model(p6)
    exact = exact_equal_title_probability(rep.scheme)
    print("Eksak (equal): " + ", ".join(
        f"{p}={v * 100:.1f}%" for p, v in sorted(exact.items())))
    mc = monte_carlo(rep.scheme, model, n=10000, seed=7)
    print(render_probability(mc))

    section("2. CUSTOM PROBABILITY (XII-01 difavoritkan)")
    model2 = custom_model({"XII-01": 4.0}, p6)
    print(f"Model: {model2.description}")
    mc2 = monte_carlo(rep.scheme, model2, n=10000, seed=7)
    print(render_probability(mc2))

    section("3. ADVANCED SCHEDULER vs GREEDY (grup 6)")
    tg = Tournament(id="TG", name="grup", format="group", team_size=4)
    g_greedy = build_report(tg, p6, scheduler="greedy")
    g_adv = build_report(tg, p6, scheduler="advanced")
    assert g_greedy.rest is not None and g_adv.rest is not None
    print(f"Greedy:   {len(g_greedy.scheduled)} match, "
          f"violations={len(g_greedy.rest.violations)}, "
          f"selesai {g_greedy.scheduled[-1].scheduled_time}")
    print(f"Advanced: {len(g_adv.scheduled)} match, "
          f"violations={len(g_adv.rest.violations)}, "
          f"selesai {g_adv.scheduled[-1].scheduled_time}")

    section("4. MULTI-LOMBA OPTIMIZATION")
    pa, _ = select_participants(reg, semua[:6])
    pb, _ = select_participants(reg, semua[4:10])
    ta = Tournament(id="LA", name="futsal", format="group", team_size=4)
    tb = Tournament(id="LB", name="basket", format="group", team_size=4)
    before = [build_report(ta, pa), build_report(tb, pb)]
    n_before = sum("BENTROK" in c for c in detect_cross_event_conflicts(before))
    print(f"Sebelum optimasi: {n_before} BENTROK")
    after, notes = optimize_multi_event([(ta, pa), (tb, pb)])
    n_after = sum("BENTROK" in c for c in detect_cross_event_conflicts(after))
    for n in notes:
        print(f"  * {n}")
    print(f"Sesudah optimasi: {n_after} BENTROK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
