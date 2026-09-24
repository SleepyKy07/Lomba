"""Test Phase 2 — stdlib only (python -m unittest)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tournament import (
    Tournament,
    analyze_existing,
    analyze_rest,
    build_default_master,
    build_report,
    compare_reports,
    detect_cross_event_conflicts,
    equal_model,
    monte_carlo,
    move_match,
    render_bracket,
    render_comparison,
    render_fairness,
    render_probability,
    render_schedule,
    replace_participant,
    schedule_advanced,
    schedule_matches,
    select_participants,
    set_walkover,
    swap_slots,
    total_load_across_events,
    what_if,
)


def make_t(tid="T", fmt="knockout", team_size=4, arenas=2, **kw):
    kw.setdefault("duration_min", 30)
    kw.setdefault("minimum_rest_min", 10)
    kw.setdefault("arena_count", arenas)
    return Tournament(
        id=tid, name=tid, format=fmt, team_size=team_size, **kw,
    )


class TestComparison(unittest.TestCase):
    def test_tiga_skema_6_peserta(self):
        p = ["A", "B", "C", "D", "E", "F"]
        reps = [build_report(make_t(f"F{i}", fmt), p)
                for i, fmt in enumerate(("knockout", "group", "round_robin"))]
        labels = ["knockout", "group", "round_robin"]
        table = compare_reports(reps, labels)
        self.assertEqual(table["total_matches"], [5, 6, 15])
        self.assertEqual(table["bye"], [2, 0, 0])
        out = render_comparison(labels, table)
        self.assertIn("knockout", out)
        self.assertNotIn("pemenang", out.lower())

    def test_validasi_input(self):
        r = build_report(make_t(), ["A", "B"])
        with self.assertRaises(ValueError):
            compare_reports([r], ["satu", "dua"])
        with self.assertRaises(ValueError):
            compare_reports([], [])

    def test_render_tabel_rusak_ditolak(self):
        with self.assertRaises(ValueError):
            render_comparison(["a"], {"total_matches": [1]})
        with self.assertRaises(ValueError):
            render_comparison(["a", "b"], {"total_matches": [1],
                                           "format": ["x", "y"],
                                           "participants": [1, 2],
                                           "match_diff": [0, 0],
                                           "rest_diff": [0, 0],
                                           "bye": [0, 0],
                                           "player_load_diff": [0, 0],
                                           "conflicts": [0]})


class TestWhatIf(unittest.TestCase):
    def test_23_ke_22(self):
        p = [f"K{i:02d}" for i in range(1, 24)]
        before, after = what_if(make_t(), p, {"remove": ["K23"]})
        assert before.fairness and after.fairness
        self.assertEqual(before.fairness.total_matches, 22)
        self.assertEqual(after.fairness.total_matches, 21)
        self.assertEqual(before.fairness.bye_count, 9)
        self.assertEqual(after.fairness.bye_count, 10)
        self.assertEqual(len(after.scheme.participant_ids), 22)

    def test_ganti_format_dan_arena(self):
        p = ["A", "B", "C", "D", "E", "F"]
        _, after = what_if(make_t(), p, {"format": "group", "arena_count": 3})
        self.assertEqual(after.scheme.tournament.format, "group")
        self.assertEqual(after.scheme.tournament.arena_count, 3)

    def test_invalid_ditolak(self):
        with self.assertRaises(ValueError):
            what_if(make_t(), ["A", "B"], {"apalah": 1})
        with self.assertRaises(ValueError):
            what_if(make_t(), ["A", "B"], {"remove": ["Z"]})
        with self.assertRaises(ValueError):
            what_if(make_t(), ["A"], {"remove": ["A"]})
        with self.assertRaises(ValueError):
            what_if(make_t(), ["A", "B"], {"arena_count": 0})

    def test_add_string_tunggal_dan_registry(self):
        reg = build_default_master(28)
        _, after = what_if(make_t(), ["XII-01", "XII-02"], {"add": "XII-03"})
        self.assertIn("XII-03", after.scheme.participant_ids)
        with self.assertRaises(ValueError):  # asing dari master
            what_if(make_t(), ["XII-01", "XII-02"], {"add": ["ZZZ"]}, registry=reg)
        # Tanpa registry, ID bebas diterima (mode generik A,B,C).
        _, after2 = what_if(make_t(), ["A", "B"], {"add": "C"})
        self.assertIn("C", after2.scheme.participant_ids)

    def test_ganti_num_groups(self):
        p = ["A", "B", "C", "D", "E", "F"]
        _, after = what_if(make_t("T", "group"), p, {"num_groups": 3})
        groups = {m.group for m in after.scheme.matches}
        self.assertEqual(len(groups), 3)

    def test_remove_add_sama_tak_ubah_seed(self):
        # remove+add ID yang sama = no-op: urutan + bye tetap.
        p = ["A", "B", "C", "D", "E", "F"]
        before, after = what_if(make_t(), p, {"remove": ["A"], "add": ["A"]})
        assert before.fairness and after.fairness
        self.assertEqual(after.scheme.participant_ids, p)
        self.assertEqual(after.fairness.bye_recipients,
                         before.fairness.bye_recipients)

    def test_summary_row_tanpa_analisis_ditolak(self):
        from tournament import SchemeReport
        from tournament import Scheme
        rep = SchemeReport(scheme=Scheme(tournament=make_t(),
                                        participant_ids=["A"]))
        with self.assertRaises(ValueError):
            rep.summary_row()


class TestCrossEvent(unittest.TestCase):
    def _two_groups(self):
        ta = make_t("LA", "group")
        tb = make_t("LB", "group")
        ra = build_report(ta, ["A", "B", "C"])
        rb = build_report(tb, ["B", "C", "D"])
        return ra, rb

    def test_bentrok_terdeteksi(self):
        ra, rb = self._two_groups()
        found = detect_cross_event_conflicts([ra, rb])
        # Jadwal sama (08:00) + peserta irisan B,C -> bentrok jam sama.
        self.assertTrue(any("BENTROK" in c for c in found))
        self.assertTrue(any(c.startswith("B ") or c.startswith("C ") for c in found))

    def test_beda_jam_tanpa_bentrok(self):
        ta = make_t("LA", "group", start_time="08:00", end_time="10:00")
        tb = make_t("LB", "group", start_time="13:00", end_time="17:00")
        ra = build_report(ta, ["A", "B", "C"])
        rb = build_report(tb, ["B", "C", "D"])
        self.assertEqual(detect_cross_event_conflicts([ra, rb]), [])

    def test_overlap_beda_durasi_terdeteksi(self):
        # LA 60 mnt vs LB 10 mnt: LB 08:10 overlap LA 08:00-09:00 (non-adjacent).
        ta = make_t("LA", "group", team_size=1, arenas=5, duration_min=60)
        tb = make_t("LB", "group", team_size=1, arenas=5, duration_min=10)
        ra = build_report(ta, ["X", "Y", "Z"])
        rb = build_report(tb, ["X", "Y", "Z"])
        found = detect_cross_event_conflicts([ra, rb])
        self.assertTrue(any("BENTROK" in c and "08:10" in c for c in found),
                        f"overlap non-adjacent terlewat: {found}")

    def test_satu_lomba_kosong(self):
        ra, _ = self._two_groups()
        self.assertEqual(detect_cross_event_conflicts([ra]), [])

    def test_id_sama_tetap_dibandingkan(self):
        # Dua lomba beda dengan id sama: identitas = posisi report.
        r1 = build_report(make_t("SAME", "group"), ["A", "B", "C"])
        r2 = build_report(make_t("SAME", "group"), ["A", "D", "E"])
        found = detect_cross_event_conflicts([r1, r2])
        self.assertTrue(any("BENTROK" in c for c in found))
        # Report yang sama diteruskan dua kali bukan dua lomba.
        self.assertEqual(detect_cross_event_conflicts([r1, r1]), [])

    def test_tanggal_beda_diabaikan(self):
        ta = make_t("LA", "group", date="2026-09-20")
        tb = make_t("LB", "group", date="2026-09-21")
        ra = build_report(ta, ["A", "B", "C"])
        rb = build_report(tb, ["B", "C", "D"])
        self.assertEqual(detect_cross_event_conflicts([ra, rb]), [])

    def test_total_load(self):
        ra, rb = self._two_groups()
        total = total_load_across_events([ra, rb])
        # A: 2 match x4 = 8 (satu lomba); B: 8 + 8 = 16 (dua lomba).
        self.assertEqual(total["A"], 8)
        self.assertEqual(total["B"], 16)


class TestManual(unittest.TestCase):
    def test_swap_lalu_analisis_ulang(self):
        # n=4 tanpa bye: R1 = (A,B),(C,D) -> tukar sisi-a -> (C,B),(A,D).
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        r1 = [m.id for m in rep.scheme.matches if m.round == "R1"]
        edited = swap_slots(rep.scheme, r1[0], "a", r1[1], "a")
        self.assertIn("Manual", edited.notes[-1])
        rep2 = analyze_existing(edited, rep.scheduled)
        assert rep2.fairness is not None
        # Awal (A,B),(C,D) -> sesudah (C,B),(A,D).
        slots = {(m.participant_a, m.participant_b) for m in edited.matches
                 if m.round == "R1"}
        self.assertEqual(slots, {("C", "B"), ("A", "D")})

    def test_swap_invalid_ditolak(self):
        # Grup A,B,C: (A,B),(A,C),(B,C). Tukar m0.a dengan m2.a -> (B,B).
        rep = build_report(make_t("TG", "group"), ["A", "B", "C"])
        ids = [m.id for m in rep.scheme.matches]
        with self.assertRaises(ValueError):
            swap_slots(rep.scheme, ids[0], "a", ids[2], "a")
        with self.assertRaises(ValueError):
            swap_slots(rep.scheme, "XXX", "a", ids[0], "a")
        with self.assertRaises(ValueError):
            swap_slots(rep.scheme, ids[0], "x", ids[1], "a")

    def test_move_menciptakan_conflict_terdeteksi(self):
        # Grup (A,B),(A,C),(B,C): pindah (A,C) ke jam (A,B) -> A bentrok.
        rep = build_report(make_t("TG", "group"), ["A", "B", "C"])
        m_ab = next(m.id for m in rep.scheme.matches
                    if {m.participant_a, m.participant_b} == {"A", "B"})
        m_ac = next(m.id for m in rep.scheme.matches
                    if {m.participant_a, m.participant_b} == {"A", "C"})
        t_ab = next(s.scheduled_time for s in rep.scheduled if s.match.id == m_ab)
        a_ab = next(s.arena for s in rep.scheduled if s.match.id == m_ab)
        moved = move_match(rep.scheduled, m_ac, t_ab, a_ab)
        rep2 = analyze_existing(rep.scheme, moved)
        self.assertTrue(any("A " in c or c.startswith("A") for c in rep2.conflicts),
                        f"conflict tak terdeteksi: {rep2.conflicts}")

    def test_move_validasi_dengan_tournament(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        mid = rep.scheme.matches[0].id
        with self.assertRaises(ValueError):  # arena 99 > 2
            move_match(rep.scheduled, mid, "08:00", 99, rep.scheme.tournament)
        with self.assertRaises(ValueError):  # di luar jendela
            move_match(rep.scheduled, mid, "23:00", 1, rep.scheme.tournament)
        ok = move_match(rep.scheduled, mid, "08:00", 1, rep.scheme.tournament)
        self.assertEqual(len(ok), len(rep.scheduled))

    def test_jadwal_divalidasi_saat_analisis_ulang(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        mid = rep.scheme.matches[0].id
        moved = move_match(rep.scheduled, mid, "08:00", 99)  # tanpa tournament
        rep2 = analyze_existing(rep.scheme, moved)
        self.assertTrue(rep2.sched_errors)

    def test_swap_bye_dihitung_ulang(self):
        # A (bye SF) <-> C (R1): bye harus jadi B,C, bukan A,B.
        rep = build_report(make_t(), ["A", "B", "C", "D", "E", "F"])
        edited = swap_slots(rep.scheme, "T-M01", "a", "T-M03", "a")
        rep2 = analyze_existing(edited)
        assert rep2.fairness is not None
        self.assertEqual(rep2.fairness.bye_recipients, ["B", "C"])

    def test_jadwal_rebind_ke_match_baru(self):
        rep = build_report(make_t(), ["A", "B", "C", "D", "E", "F"])
        edited = swap_slots(rep.scheme, "T-M01", "a", "T-M02", "a")
        rep2 = analyze_existing(edited, rep.scheduled)
        got = {s.match.id: (s.match.participant_a, s.match.participant_b)
               for s in rep2.scheduled}
        self.assertEqual(got["T-M01"], ("E", "D"))
        self.assertEqual(got["T-M02"], ("C", "F"))
        self.assertEqual(rep2.sched_errors, [])

    def test_replace_participant(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        edited = replace_participant(rep.scheme, "A", "Z")
        self.assertIn("Z", edited.participant_ids)
        self.assertNotIn("A", edited.participant_ids)
        rep2 = analyze_existing(edited)
        assert rep2.fairness is not None
        self.assertIn("Z", rep2.fairness.appearances)
        with self.assertRaises(ValueError):
            replace_participant(rep.scheme, "X", "Z")
        with self.assertRaises(ValueError):
            replace_participant(rep.scheme, "A", "B")

    def test_walkover(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        mid = [m.id for m in rep.scheme.matches if m.round == "R1"][0]
        edited = set_walkover(rep.scheme, mid, "A")
        rep2 = analyze_existing(edited)
        assert rep2.fairness is not None
        self.assertEqual(rep2.fairness.appearances["B"], 0)
        self.assertEqual(rep2.fairness.appearances["A"], 1)
        self.assertEqual(rep2.fairness.guaranteed["B"], 0)
        self.assertEqual(rep2.fairness.wins_to_title["B"], 0)
        self.assertTrue(any("tidak main sama sekali" in w
                            for w in rep2.fairness.warnings))
        with self.assertRaises(ValueError):
            set_walkover(rep.scheme, mid, "Z")

    def test_swap_tbd_ke_ronde_awal_ditolak(self):
        # 6-KO: pindah slot TBD (SF) ke R1 -> bracket tak terpecahkan.
        rep = build_report(make_t(), ["A", "B", "C", "D", "E", "F"])
        sf = [m.id for m in rep.scheme.matches if m.round == "SF"][0]
        r1 = [m.id for m in rep.scheme.matches if m.round == "R1"][0]
        with self.assertRaises(ValueError):
            swap_slots(rep.scheme, sf, "b", r1, "a")

    def test_replace_none_ditolak(self):
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        with self.assertRaises(ValueError):
            replace_participant(rep.scheme, "A", None)

    def test_overlap_beda_jam_terdeteksi(self):
        # Grup: A main 2x. Geser match kedua A ke 08:15 -> tabrak 08:00+30.
        rep = build_report(make_t("TG", "group"), ["A", "B", "C"])
        m_ab = next(m.id for m in rep.scheme.matches
                    if {m.participant_a, m.participant_b} == {"A", "B"})
        m_ac = next(m.id for m in rep.scheme.matches
                    if {m.participant_a, m.participant_b} == {"A", "C"})
        t_ab = next(s.scheduled_time for s in rep.scheduled if s.match.id == m_ab)
        self.assertEqual(t_ab, "08:00")
        moved = move_match(rep.scheduled, m_ac, "08:15", 1)
        rep2 = analyze_existing(rep.scheme, moved)
        self.assertTrue(any("overlap" in c for c in rep2.conflicts),
                        f"overlap terlewat: {rep2.conflicts}")

    def test_slot_asing_ditolak_jelas(self):
        from tournament import Match, analyze_scheme
        rep = build_report(make_t(), ["A", "B", "C", "D"])
        bad = list(rep.scheme.matches) + [Match(
            id="T-MX", tournament_id="T", round="R1", stage="knockout",
            participant_a="ZZZ", participant_b="A")]
        with self.assertRaises(ValueError):
            analyze_scheme(rep.scheme.tournament, ["A", "B", "C", "D"], bad)


class TestOutputConsoleSafe(unittest.TestCase):
    """Semua output render harus bisa dicetak di console Windows (cp1252).

    Regresi untuk crash UnicodeEncodeError (em-dash di warning walkover).
    """

    def test_semua_render_cp1252(self):
        texts: list[str] = []
        for fmt in ("knockout", "preliminary_knockout", "round_robin",
                    "group", "group_knockout"):
            t = make_t(f"T-{fmt}", fmt)
            rep = build_report(t, ["A", "B", "C", "D", "E", "F"])
            assert rep.fairness is not None and rep.rest is not None
            texts.append(render_bracket(rep.scheme.matches))
            texts.append(render_schedule(rep.scheduled))
            texts.append(render_fairness(rep.fairness, rep.rest, rep.conflicts))
        # Walkover + manual + advanced + probability.
        rep = build_report(make_t("TW"), ["A", "B", "C", "D"])
        mid = [m.id for m in rep.scheme.matches if m.round == "R1"][0]
        wo = set_walkover(rep.scheme, mid, "A")
        rep2 = analyze_existing(wo)
        assert rep2.fairness is not None and rep2.rest is not None
        texts.append(render_bracket(wo.matches))
        texts.append(render_fairness(rep2.fairness, rep2.rest, rep2.conflicts))
        rep3 = build_report(make_t("TA", "group"),
                            ["A", "B", "C", "D", "E", "F"], scheduler="advanced")
        assert rep3.rest is not None
        texts.append(render_schedule(rep3.scheduled))
        mc = monte_carlo(rep.scheme, equal_model(["A", "B", "C", "D"]),
                         n=50, seed=0)
        texts.append(render_probability(mc))
        table = compare_reports(
            [build_report(make_t("C1", "knockout"), ["A", "B"]),
             build_report(make_t("C2", "group"), ["A", "B", "C"])],
            ["ko", "grup"])
        texts.append(render_comparison(["ko", "grup"], table))
        for i, out in enumerate(texts):
            with self.subTest(i=i):
                out.encode("cp1252")  # raise bila ada karakter tak aman


class TestRegistryPhase2(unittest.TestCase):
    def test_end_to_end_registry(self):
        reg = build_default_master(28)
        ikut, tidak = select_participants(
            reg, [f"XII-{i:02d}" for i in range(1, 24)])
        rep = build_report(make_t("LX"), ikut)
        assert rep.fairness is not None
        self.assertEqual(len(tidak), 5)
        self.assertEqual(rep.fairness.total_matches, 22)


if __name__ == "__main__":
    unittest.main()
