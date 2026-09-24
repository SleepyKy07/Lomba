"""Test Phase 3 — stdlib only (python -m unittest)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tournament import (
    Tournament,
    analyze_existing,
    build_report,
    custom_model,
    detect_cross_event_conflicts,
    equal_model,
    exact_equal_title_probability,
    monte_carlo,
    optimize_multi_event,
    percent_model,
    render_probability,
    schedule_advanced,
    schedule_matches,
    set_walkover,
    simulate_once,
    win_probability,
)
import random


def make_t(tid="T", fmt="knockout", team_size=1, arenas=2, **kw):
    kw.setdefault("duration_min", 30)
    kw.setdefault("minimum_rest_min", 10)
    kw.setdefault("arena_count", arenas)
    return Tournament(id=tid, name=tid, format=fmt, team_size=team_size, **kw)


class TestProbability(unittest.TestCase):
    def test_equal_model(self):
        m = equal_model(["A", "B"])
        self.assertEqual(win_probability(m, "A", "B"), 0.5)
        with self.assertRaises(ValueError):
            equal_model([])

    def test_custom_validasi(self):
        with self.assertRaises(ValueError):
            custom_model({"Z": 1.0}, ["A", "B"])
        with self.assertRaises(ValueError):
            custom_model({"A": -1.0}, ["A", "B"])
        m = custom_model({"A": 3.0}, ["A", "B"])
        self.assertAlmostEqual(win_probability(m, "A", "B"), 0.75)
        self.assertIn("default", m.description)

    def test_2_peserta_eksak_vs_montecarlo(self):
        rep = build_report(make_t(), ["A", "B"])
        m = custom_model({"A": 3.0}, ["A", "B"])
        mc = monte_carlo(rep.scheme, m, n=20000, seed=1)
        self.assertAlmostEqual(mc.champion_share["A"], 0.75, delta=0.02)
        self.assertAlmostEqual(
            mc.champion_share["A"] + mc.champion_share["B"], 1.0)

    def test_exact_equal_6_knockout(self):
        rep = build_report(make_t(), ["A", "B", "C", "D", "E", "F"])
        exact = exact_equal_title_probability(rep.scheme)
        assert exact is not None
        self.assertAlmostEqual(exact["A"], 0.25)  # bye: 2 menang
        self.assertAlmostEqual(exact["C"], 0.125)  # 3 menang
        mc = monte_carlo(rep.scheme, equal_model(rep.scheme.participant_ids),
                         n=20000, seed=3)
        for p in ("A", "C"):
            self.assertAlmostEqual(mc.champion_share[p], exact[p], delta=0.02)

    def test_seed_reproducibel(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        m = equal_model(["A", "B", "C", "D"])
        r1 = monte_carlo(rep.scheme, m, n=1000, seed=9)
        r2 = monte_carlo(rep.scheme, m, n=1000, seed=9)
        self.assertEqual(r1.champion_share, r2.champion_share)

    def test_group_kuat_menang(self):
        rep = build_report(make_t("G", "group"), ["A", "B", "C"])
        m = custom_model({"A": 9.0, "B": 1.0, "C": 1.0}, ["A", "B", "C"])
        mc = monte_carlo(rep.scheme, m, n=5000, seed=5)
        self.assertGreater(mc.champion_share["A"], 0.5)

    def test_grup_murni_multi_ditolak(self):
        rep = build_report(make_t("G", "group"),
                           ["A", "B", "C", "D", "E", "F"])
        with self.assertRaises(ValueError):
            simulate_once(rep.scheme, equal_model(["A", "B", "C", "D", "E", "F"]),
                           random.Random(0))

    def test_exact_none_untuk_grup(self):
        rep = build_report(make_t("G", "round_robin"), ["A", "B", "C"])
        self.assertIsNone(exact_equal_title_probability(rep.scheme))

    def test_render_disclaimer(self):
        rep = build_report(make_t(), ["A", "B"])
        mc = monte_carlo(rep.scheme, equal_model(["A", "B"]), n=10, seed=0)
        out = render_probability(mc)
        self.assertIn("BUKAN prediksi", out)

    def test_render_truncasi_bertanda(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        mc = monte_carlo(rep.scheme, equal_model(["A", "B", "C", "D"]),
                         n=100, seed=0)
        out = render_probability(mc, top=1)
        self.assertIn("peserta lainnya", out)

    def test_n_invalid(self):
        rep = build_report(make_t(), ["A", "B"])
        with self.assertRaises(ValueError):
            monte_carlo(rep.scheme, equal_model(["A", "B"]), n=0)

    def test_walkover_bisa_disimulasi(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        mid = [m.id for m in rep.scheme.matches if m.round == "R1"][0]
        edited = set_walkover(rep.scheme, mid, "A")
        wo = next(m for m in edited.matches if m.id == mid)
        self.assertEqual(wo.status, "walkover")
        mc = monte_carlo(edited, equal_model(["A", "B", "C", "D"]),
                         n=2000, seed=0)
        self.assertAlmostEqual(sum(mc.champion_share.values()), 1.0)
        # A lolos gratis R1 -> peluang juara naik di atas equal murni.
        self.assertGreater(mc.champion_share["A"], 0.3)

    def test_exact_walkover_nol_untuk_tersingkir(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        mid = [m.id for m in rep.scheme.matches if m.round == "R1"][0]
        edited = set_walkover(rep.scheme, mid, "A")
        exact = exact_equal_title_probability(edited)
        assert exact is not None
        self.assertEqual(exact["B"], 0.0)

    def test_custom_nol_semua_ditolak(self):
        with self.assertRaises(ValueError):
            custom_model({"A": 0.0, "B": 0.0}, ["A", "B"])

    def test_percent_model_prd(self):
        m = percent_model({"A": 60.0, "B": 40.0}, ["A", "B"])
        self.assertAlmostEqual(win_probability(m, "A", "B"), 0.6)
        with self.assertRaises(ValueError):
            percent_model({"A": 50.0, "B": 40.0}, ["A", "B"])
        with self.assertRaises(ValueError):
            percent_model({"A": 60.0, "Z": 40.0}, ["A", "B"])


class TestAdvancedScheduler(unittest.TestCase):
    def test_hilangkan_violation_grup6(self):
        t = make_t("TG", "group", team_size=4)
        p = ["A", "B", "C", "D", "E", "F"]
        greedy = build_report(t, p, scheduler="greedy")
        adv = build_report(t, p, scheduler="advanced")
        assert greedy.rest is not None and adv.rest is not None
        self.assertGreater(len(greedy.rest.violations), 0)
        self.assertEqual(len(adv.rest.violations), 0)
        self.assertEqual(len(adv.scheduled), len(greedy.scheduled))

    def test_tanpa_conflict_dan_ronde_terjaga(self):
        t = make_t("TG", "group", team_size=4)
        rep = build_report(t, ["A", "B", "C", "D", "E", "F"], scheduler="advanced")
        self.assertEqual(rep.conflicts, [])
        self.assertEqual(rep.sched_errors, [])

    def test_knockout_tetap_muat(self):
        t = make_t("T", "knockout")
        p = [f"K{i:02d}" for i in range(1, 24)]
        rep = build_report(t, p, scheduler="advanced")
        self.assertEqual(rep.sched_errors, [])
        self.assertEqual(len(rep.scheduled), 22)

    def test_scheduler_invalid_ditolak(self):
        with self.assertRaises(ValueError):
            build_report(make_t(), ["A", "B"], scheduler="acme")

    def test_overflow_jujur(self):
        t = make_t("T", "knockout", arenas=1, start_time="08:00", end_time="09:00")
        scheduled, err = schedule_advanced(
            t, build_report(make_t(), ["A", "B", "C", "D"]).scheme.matches)
        self.assertTrue(err)
        self.assertLess(len(scheduled), 4)


class TestMulti(unittest.TestCase):
    def test_hilangkan_bentrok(self):
        ta = make_t("LA", "group", team_size=4)
        tb = make_t("LB", "group", team_size=4)
        specs = [(ta, ["A", "B", "C", "D", "E", "F"]),
                 (tb, ["E", "F", "G", "H", "I", "J"])]
        before_n = sum("BENTROK" in c for c in detect_cross_event_conflicts(
            [build_report(t, p) for t, p in specs]))
        self.assertGreater(before_n, 0)
        after, notes = optimize_multi_event(specs)
        found = detect_cross_event_conflicts(after)
        self.assertEqual(sum("BENTROK" in c for c in found), 0)
        self.assertTrue(notes)

    def test_jendela_sempit_jujur(self):
        ta = make_t("LA", "group", team_size=4, start_time="08:00", end_time="10:00")
        tb = make_t("LB", "group", team_size=4, start_time="08:00", end_time="10:00")
        specs = [(ta, ["A", "B", "C"]), (tb, ["A", "B", "C"])]
        after, notes = optimize_multi_event(specs, max_shift_batches=1)
        # Grup 3 peserta butuh 3 batch; shift 1 tak cukup -> sisa jujur.
        found = detect_cross_event_conflicts(after)
        self.assertTrue(sum("BENTROK" in c for c in found) > 0 or notes)

    def test_kosong_ditolak(self):
        with self.assertRaises(ValueError):
            optimize_multi_event([])

    def test_input_invalid_ditolak(self):
        ta = make_t("LA", "group")
        with self.assertRaises(ValueError):
            optimize_multi_event([(ta, ["A", "B", "C"])], max_shift_batches=-1)
        with self.assertRaises(ValueError):
            optimize_multi_event([(ta,)])

    def test_lomba_pertama_tak_digeser(self):
        ta = make_t("LA", "group", team_size=4)
        tb = make_t("LB", "group", team_size=4)
        specs = [(ta, ["A", "B", "C", "D", "E", "F"]),
                 (tb, ["E", "F", "G", "H", "I", "J"])]
        base0 = build_report(ta, specs[0][1])
        after, _ = optimize_multi_event(specs)
        self.assertEqual(
            [s.start_min for s in after[0].scheduled],
            [s.start_min for s in base0.scheduled])

    def test_shift_negatif_ditolak(self):
        from tournament import shift_report
        rep = build_report(make_t(), ["A", "B"])
        with self.assertRaises(ValueError):
            shift_report(rep, -1)


if __name__ == "__main__":
    unittest.main()
