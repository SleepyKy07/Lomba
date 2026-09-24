"""Test Phase 1 — stdlib only (python -m unittest)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tournament import (
    ClassInfo,
    ClassRegistry,
    Tournament,
    analyze_rest,
    analyze_scheme,
    build_default_master,
    detect_internal_conflict,
    generate_scheme,
    infer_bye_details,
    render_bracket,
    render_fairness,
    render_schedule,
    schedule_matches,
    select_participants,
)


def make_t(fmt="knockout", team_size=4, arenas=2, **kw):
    return Tournament(
        id="T", name="t", format=fmt, team_size=team_size,
        duration_min=30, minimum_rest_min=10, arena_count=arenas, **kw,
    )


class TestKnockout(unittest.TestCase):
    def test_6_peserta_5_match_2_bye(self):
        p = ["A", "B", "C", "D", "E", "F"]
        s = generate_scheme(make_t("knockout"), p)
        self.assertEqual(len(s.matches), 5)  # n-1 menuju 1 juara
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertEqual(f.bye_count, 2)
        self.assertEqual(f.bye_recipients, ["A", "B"])
        self.assertEqual(f.wins_to_title["A"], 2)
        self.assertEqual(f.wins_to_title["C"], 3)
        self.assertGreater(f.path_diff, 0)

    def test_bye_disebar_tidak_saling_bunuh(self):
        # 6 peserta: SF harus bye-vs-TBD, bukan bye-vs-bye.
        s = generate_scheme(make_t("knockout"), ["A", "B", "C", "D", "E", "F"])
        sf = [m for m in s.matches if m.round == "SF"]
        self.assertEqual(len(sf), 2)
        byes = {"A", "B"}
        for m in sf:
            di_m = {m.participant_a, m.participant_b} & byes
            self.assertLessEqual(len(di_m), 1, f"bye-vs-bye di {m.id}")

    def test_bye_detail_entry_round(self):
        s = generate_scheme(make_t("knockout"), ["A", "B", "C", "D", "E", "F"])
        det = {d.participant: d for d in s.bye_details}
        self.assertEqual(set(det), {"A", "B"})
        self.assertEqual(det["A"].entry_round, "SF")
        self.assertEqual(det["A"].skipped_rounds, ["R1"])
        self.assertEqual(det["A"].wins_needed, 2)

    def test_23_peserta_9_bye(self):
        p = [f"K{i:02d}" for i in range(1, 24)]
        s = generate_scheme(make_t("knockout"), p)
        self.assertEqual(len(s.matches), 22)
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertEqual(f.bye_count, 9)  # next_pow2(23)=32

    def test_2_peserta_final_langsung(self):
        s = generate_scheme(make_t("knockout"), ["A", "B"])
        self.assertEqual(len(s.matches), 1)
        self.assertEqual(s.matches[0].round, "F")
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertEqual(f.bye_count, 0)

    def test_inferensi_tanpa_bye_details_generator(self):
        # Fairness tetap menemukan bye meski generator tak memberi data.
        s = generate_scheme(make_t("knockout"), ["A", "B", "C", "D", "E", "F"])
        det = infer_bye_details(s.participant_ids, s.matches)
        self.assertEqual([d.participant for d in det], ["A", "B"])
        self.assertEqual(det[0].entry_round, "SF")

    def test_jaminan_vs_maksimal(self):
        s = generate_scheme(make_t("knockout"), ["A", "B", "C", "D", "E", "F"])
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertTrue(all(v == 1 for v in f.guaranteed.values()))
        self.assertEqual(f.max_possible["A"], 2)
        self.assertEqual(f.max_possible["C"], 3)

    def test_path_sf_final(self):
        s = generate_scheme(make_t("knockout"), ["A", "B", "C", "D", "E", "F"])
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertEqual(f.wins_to_semifinal["A"], 0)  # langsung di SF
        self.assertEqual(f.wins_to_semifinal["C"], 1)
        self.assertEqual(f.wins_to_final["A"], 1)
        self.assertEqual(f.wins_to_final["C"], 2)


class TestPreliminary(unittest.TestCase):
    def test_label_p_terdeteksi_bye(self):
        s = generate_scheme(make_t("preliminary_knockout"),
                            ["A", "B", "C", "D", "E", "F"])
        rounds = {m.round for m in s.matches}
        self.assertIn("P", rounds)
        self.assertNotIn("R1", rounds)
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertEqual(f.bye_count, 2)
        self.assertEqual(f.bye_recipients, ["A", "B"])


class TestRoundRobin(unittest.TestCase):
    def test_6_peserta_15_match(self):
        p = ["A", "B", "C", "D", "E", "F"]
        s = generate_scheme(make_t("round_robin"), p)
        self.assertEqual(len(s.matches), 15)  # 6*5/2
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        for v in f.appearances.values():
            self.assertEqual(v, 5)
        self.assertEqual(f.match_diff, 0)
        self.assertEqual(f.bye_count, 0)

    def test_ganjil_ada_jeda(self):
        s = generate_scheme(make_t("round_robin"), ["A", "B", "C", "D", "E"])
        self.assertEqual(len(s.matches), 10)  # 5*4/2
        self.assertTrue(any("jeda" in n for n in s.notes))


class TestGroup(unittest.TestCase):
    def test_6_peserta_2_grup_masing2_main_2x(self):
        p = ["A", "B", "C", "D", "E", "F"]
        s = generate_scheme(make_t("group"), p)
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertEqual(len(s.matches), 6)  # 2 grup x 3 match
        for v in f.appearances.values():
            self.assertEqual(v, 2)
        self.assertEqual(f.match_diff, 0)
        self.assertEqual(f.bye_count, 0)

    def test_id_berurutan_per_grup(self):
        s = generate_scheme(make_t("group"), ["A", "B", "C", "D", "E", "F"])
        ga = sorted(m.id for m in s.matches if m.group == "A")
        gb = sorted(m.id for m in s.matches if m.group == "B")
        self.assertEqual(ga, ["T-GA01", "T-GA02", "T-GA03"])
        self.assertEqual(gb, ["T-GB01", "T-GB02", "T-GB03"])

    def test_group_knockout_ada_lanjutan(self):
        p = ["A", "B", "C", "D", "E", "F"]
        s = generate_scheme(make_t("group_knockout"), p)
        stages = {m.stage for m in s.matches}
        self.assertIn("group", stages)
        self.assertIn("knockout", stages)
        # ID KO penomoran sendiri, bukan hasil replace string.
        ko_ids = sorted(m.id for m in s.matches if m.stage == "knockout")
        for i in ko_ids:
            self.assertTrue(i.startswith("T-K"))

    def test_group_knockout_23_bye_antar_juara_grup(self):
        # 23 peserta -> 6 grup -> KO 6 qualifier -> 2 bye placeholder.
        p = [f"K{i:02d}" for i in range(1, 24)]
        s = generate_scheme(make_t("group_knockout"), p)
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        self.assertEqual(f.bye_count, 0)  # tak ada bye nama nyata
        ph = [d for d in f.bye_details if d.participant.startswith("Juara Grup")]
        self.assertEqual(len(ph), 2)
        self.assertTrue(any(
            ("antar juara grup" in w) or ("antar slot kualifikasi grup" in w)
            for w in f.warnings))

    def test_group_knockout_fairness_jujur(self):
        s = generate_scheme(make_t("group_knockout"), ["A", "B", "C", "D"])
        f = analyze_scheme(s.tournament, s.participant_ids, s.matches,
                           s.bye_details)
        # 4 peserta -> 1 grup -> KO 1 qualifier... tampil semua di grup.
        self.assertEqual(f.appearances["A"], 3)


class TestSchedulerFairness(unittest.TestCase):
    def test_schedule_23_muats_satu_hari_2_arena(self):
        p = [f"K{i:02d}" for i in range(1, 24)]
        t = make_t("knockout", arenas=2)
        s = generate_scheme(t, p)
        scheduled, err = schedule_matches(t, s.matches)
        self.assertEqual(err, [])
        self.assertEqual(len(scheduled), 22)
        rest = analyze_rest(t, scheduled)
        self.assertIsNone(rest.min_rest)  # ronde lanjut TBD
        self.assertEqual(detect_internal_conflict(scheduled), [])

    def test_schedule_group_rest_terhitung_tanpa_bentrok(self):
        p = ["A", "B", "C", "D", "E", "F"]
        t = make_t("group", arenas=2)
        s = generate_scheme(t, p)
        scheduled, err = schedule_matches(t, s.matches)
        self.assertEqual(err, [])
        rest = analyze_rest(t, scheduled)
        self.assertIsNotNone(rest.min_rest)
        self.assertEqual(detect_internal_conflict(scheduled), [])
        self.assertGreaterEqual(rest.min_rest, 0)

    def test_schedule_overflow_dilaporkan(self):
        p = [f"K{i:02d}" for i in range(1, 24)]
        t = make_t("knockout", arenas=1, start_time="08:00", end_time="09:00")
        s = generate_scheme(t, p)
        scheduled, err = schedule_matches(t, s.matches)
        self.assertTrue(err)
        self.assertLess(len(scheduled), len(s.matches))

    def test_player_load_4v4(self):
        p = ["A", "B", "C", "D", "E", "F"]
        t = make_t("group", team_size=4)
        s = generate_scheme(t, p)
        f = analyze_scheme(t, s.participant_ids, s.matches, s.bye_details)
        self.assertEqual(f.player_load["A"], 2 * 4)

    def test_render_tidak_crash(self):
        s = generate_scheme(make_t("knockout"), ["A", "B", "C", "D", "E", "F"])
        t = s.tournament
        scheduled, _ = schedule_matches(t, s.matches)
        f = analyze_scheme(t, s.participant_ids, s.matches, s.bye_details)
        r = analyze_rest(t, scheduled)
        c = detect_internal_conflict(scheduled)
        for out in (render_bracket(s.matches), render_schedule(scheduled),
                    render_fairness(f, r, c)):
            self.assertTrue(out)


class TestRegistry(unittest.TestCase):
    def test_master_28_dan_subset_23(self):
        reg = build_default_master(28)
        self.assertEqual(reg.count(), 28)
        ikut, tidak = select_participants(
            reg, [f"XII-{i:02d}" for i in range(1, 24)])
        self.assertEqual(len(ikut), 23)
        self.assertEqual(len(tidak), 5)

    def test_id_tak_dikenal_ditolak(self):
        reg = build_default_master(5)
        with self.assertRaises(ValueError):
            select_participants(reg, ["XII-99"])
        with self.assertRaises(ValueError):
            select_participants(reg, [])
        with self.assertRaises(ValueError):
            reg.add(ClassInfo(id="XII-01", name="duplikat"))


class TestValidasi(unittest.TestCase):
    def test_tournament_invalid(self):
        with self.assertRaises(ValueError):
            Tournament(id="T", name="t", format="catur", team_size=1)
        with self.assertRaises(ValueError):
            Tournament(id="T", name="t", format="knockout", team_size=0)
        with self.assertRaises(ValueError):
            Tournament(id="T", name="t", format="knockout", team_size=1,
                       winner_count=0)
        with self.assertRaises(ValueError):
            Tournament(id="T", name="t", format="knockout", team_size=1,
                       start_time="17:00", end_time="08:00")
        with self.assertRaises(ValueError):
            Tournament(id="T", name="t", format="knockout", team_size=1,
                       start_time="pagi", end_time="17:00")

    def test_kelompok_besar_didukung(self):
        t = Tournament(id="T", name="t", format="group", team_size=6)
        s = generate_scheme(t, ["A", "B", "C"])
        self.assertEqual(len(s.matches), 3)

    def test_peserta_kosong_ditolak(self):
        with self.assertRaises(ValueError):
            generate_scheme(make_t("knockout"), [])
        with self.assertRaises(ValueError):
            generate_scheme(make_t("round_robin"), [])


if __name__ == "__main__":
    unittest.main()
