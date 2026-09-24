"""Test perebutan juara 3 (F3) — winner_count > 1."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tournament import (
    LOSER_PREFIX,
    Tournament,
    advance_scheme,
    build_report,
    build_standings,
    equal_model,
    exact_equal_title_probability,
    generate_scheme,
    is_placeholder,
    monte_carlo,
    record_result,
    render_bracket,
    set_walkover,
)


def ko(t_id="T1", n=4, wc=2, fmt="knockout"):
    t = Tournament(id=t_id, name=t_id, format=fmt, team_size=1,
                   winner_count=wc, duration_min=30, minimum_rest_min=10,
                   arena_count=2)
    pids = [f"P{i}" for i in range(1, n + 1)]
    return t, pids


class GeneratorF3Case(unittest.TestCase):
    def test_f3_ada_saat_winner_count_gt1(self):
        t, pids = ko(n=4, wc=3)
        s = generate_scheme(t, pids)
        f3 = [m for m in s.matches if m.round == "F3"]
        self.assertEqual(len(f3), 1)
        self.assertTrue(f3[0].participant_a.startswith(LOSER_PREFIX))
        self.assertTrue(f3[0].participant_b.startswith(LOSER_PREFIX))
        # F3 sebelum F di daftar match
        ids = [m.round for m in s.matches]
        self.assertLess(ids.index("F3"), ids.index("F"))
        self.assertTrue(any("Perebutan juara 3" in n for n in s.notes))

    def test_tanpa_f3_winner_count_1(self):
        t, pids = ko(n=4, wc=1)
        s = generate_scheme(t, pids)
        self.assertFalse(any(m.round == "F3" for m in s.matches))

    def test_n2_tanpa_f3(self):
        t, pids = ko(n=2, wc=2)
        s = generate_scheme(t, pids)
        self.assertFalse(any(m.round == "F3" for m in s.matches))
        self.assertTrue(any("tidak mungkin" in n for n in s.notes))

    def test_n6_punya_f3_kalah_sf(self):
        t, pids = ko(n=6, wc=2)
        s = generate_scheme(t, pids)
        f3 = next(m for m in s.matches if m.round == "F3")
        self.assertEqual(f3.participant_a, "Kalah SF-1")
        self.assertEqual(f3.participant_b, "Kalah SF-2")

    def test_placeholder_dan_fairness_tidak_boom(self):
        t, pids = ko(n=6, wc=2)
        rep = build_report(t, pids)
        self.assertIsNotNone(rep.fairness)
        # path-to-title tidak dihitung dari F3 (juara 1 tetap via F)
        self.assertTrue(all(v <= 3 for v in rep.fairness.wins_to_title.values()))
        # render aman
        text = render_bracket(rep.scheme.matches)
        self.assertIn("F3", text)
        self.assertIn(LOSER_PREFIX, text)

    def test_exact_equal_abaikan_f3(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        probs = exact_equal_title_probability(s)
        self.assertIsNotNone(probs)
        # 4 peserta bracket utuh: juara = (1/2)^2 = 0.25 (bukan termasuk F3)
        for p, v in probs.items():
            self.assertAlmostEqual(v, 0.25)


class AdvanceF3Case(unittest.TestCase):
    def test_isi_f3_dari_kalah_r1(self):
        t, pids = ko(n=4, wc=2)
        rep = build_report(t, pids)
        # menangkan semua match yang siap (R1 dulu)
        results = {}
        for m in rep.scheme.matches:
            if (m.round != "F3" and m.participant_a and m.participant_b
                    and not is_placeholder(m.participant_a)
                    and not is_placeholder(m.participant_b)):
                try:
                    results[m.id] = record_result(
                        rep.scheme, m.id, 2, 0, results=results)
                except ValueError:
                    break
        # isi R1 saja dulu (2 match) agar F3 terisi kalah R1
        r1 = [m for m in rep.scheme.matches if m.round == "R1"]
        results = {}
        for m in r1:
            results[m.id] = record_result(rep.scheme, m.id, 2, 0,
                                          results=results)
        live = advance_scheme(rep.scheme, results)
        f3 = next(m for m in live.matches if m.round == "F3")
        self.assertFalse(is_placeholder(f3.participant_a))
        self.assertFalse(is_placeholder(f3.participant_b))
        self.assertNotEqual(f3.participant_a, f3.participant_b)
        # kalah R1 = yang skornya kalah
        losers = set()
        for m in r1:
            r = results[m.id]
            losers.add(m.participant_b if r.winner == m.participant_a
                       else m.participant_a)
        self.assertEqual({f3.participant_a, f3.participant_b}, losers)

    def test_f3_dengan_hasil_status_juara3(self):
        t, pids = ko(n=4, wc=3)
        rep = build_report(t, pids)
        results = {}
        # mainkan sampai F3 + F
        for _ in range(5):
            for m in advance_scheme(rep.scheme, results).matches:
                if (m.id in results or m.round == "F3"
                        or not m.participant_a or not m.participant_b):
                    continue
                if is_placeholder(m.participant_a) or is_placeholder(
                        m.participant_b):
                    continue
                try:
                    results[m.id] = record_result(
                        rep.scheme, m.id, 1, 0, results=results)
                except ValueError:
                    pass
        tables = dict(build_standings(rep.scheme, results))
        cat = {r.participant: r.catatan
               for r in tables.get("Jalur knockout", [])}
        if any(m.round == "F3" and m.id in results for m in rep.scheme.matches):
            f3 = next(m for m in rep.scheme.matches if m.round == "F3")
            r = results.get(f3.id)
            if r and r.winner:
                self.assertEqual(cat.get(r.winner), "Juara 3")


class MonteCarloF3Case(unittest.TestCase):
    def test_mc_jalan_dengan_f3(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        mc = monte_carlo(s, equal_model(pids), n=50, seed=1)
        self.assertEqual(mc.n, 50)
        total = sum(mc.champion_share.values())
        self.assertAlmostEqual(total, 1.0, places=6)
        # tiap peserta punya peluang non-negatif; F3 tak menambah juara aneh
        for p in pids:
            self.assertGreaterEqual(mc.champion_share.get(p, 0), 0)


class WalkoverF3Case(unittest.TestCase):
    """Item 1: WO di ronde sumber F3 harus mencatat kalah ke slot Kalah."""

    def test_wo_r1_isi_slot_kalah_r1(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        self.assertEqual(len(r1), 2)
        wo = set_walkover(s, r1[0].id, r1[0].participant_a)
        f3 = next(m for m in wo.matches if m.round == "F3")
        loser = r1[0].participant_b
        # slot pertama F3 terisi loser WO (pos 1 = Kalah R1-1)
        if f3.participant_a == loser or f3.participant_b == loser:
            pass
        else:
            self.fail(f"F3 tidak terisi loser WO: {f3.participant_a!r} "
                      f"/ {f3.participant_b!r}")
        # slot satunya masih placeholder Kalah R1-2
        other = (f3.participant_b if f3.participant_a == loser
                 else f3.participant_a)
        self.assertEqual(other, "Kalah R1-2")
        self.assertTrue(any("F3:" in n and loser in n for n in wo.notes))
        # skor match kedua melengkapi F3
        results = {r1[1].id: record_result(s, r1[1].id, 1, 0)}
        live = advance_scheme(wo, results)
        f3l = next(m for m in live.matches if m.round == "F3")
        self.assertFalse(is_placeholder(f3l.participant_a))
        self.assertFalse(is_placeholder(f3l.participant_b))
        self.assertNotEqual(f3l.participant_a, f3l.participant_b)

    def test_kedua_r1_walkover_f3_penuh(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        wo = set_walkover(s, r1[0].id, r1[0].participant_a)
        wo = set_walkover(wo, r1[1].id, r1[1].participant_a)
        f3 = next(m for m in wo.matches if m.round == "F3")
        self.assertFalse(is_placeholder(f3.participant_a))
        self.assertFalse(is_placeholder(f3.participant_b))
        self.assertEqual(
            {f3.participant_a, f3.participant_b},
            {r1[0].participant_b, r1[1].participant_b},
        )

    def test_wo_bukan_ronde_sumber_catatan_limitasi(self):
        t, pids = ko(n=8, wc=2)
        s = generate_scheme(t, pids)
        # pre-F = SF; WO di R1 bukan sumber F3
        r1 = next(m for m in s.matches if m.round == "R1")
        wo = set_walkover(s, r1.id, r1.participant_a)
        f3 = next(m for m in wo.matches if m.round == "F3")
        self.assertTrue(is_placeholder(f3.participant_a))
        self.assertTrue(is_placeholder(f3.participant_b))
        self.assertTrue(any("Limitasi" in n or "TIDAK mengisi F3"
                            for n in wo.notes))

    def test_mc_setelah_wo_sumber_f3(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        wo = set_walkover(s, r1[0].id, r1[0].participant_a)
        mc = monte_carlo(wo, equal_model(pids), n=40, seed=2)
        total = sum(mc.champion_share.values())
        self.assertAlmostEqual(total, 1.0, places=6)


class QualifyPerGroupCase(unittest.TestCase):
    """Item 2: qualify_per_group — juara + runner-up lolos."""

    def _t(self, q=2, fmt="group_knockout", wc=1):
        return Tournament(id="Q", name="Q", format=fmt, team_size=1,
                          winner_count=wc, duration_min=30,
                          minimum_rest_min=10, arena_count=2,
                          qualify_per_group=q)

    def test_placeholder_peringkat_2(self):
        pids = [f"P{i}" for i in range(1, 9)]  # 8 -> 2 grup x 4
        s = generate_scheme(self._t(q=2), pids, num_groups=2)
        ko_ms = [m for m in s.matches if m.stage == "knockout"]
        slots = {m.participant_a for m in ko_ms} | {m.participant_b for m in ko_ms}
        self.assertIn("Juara Grup A", slots)
        self.assertIn("Peringkat 2 Grup A", slots)
        self.assertIn("Juara Grup B", slots)
        self.assertIn("Peringkat 2 Grup B", slots)
        self.assertTrue(all(is_placeholder(x) for x in slots if x and "Grup" in x))
        self.assertTrue(any("Kualifikasi: 2 per grup" in n for n in s.notes))

    def test_q1_default_tanpa_peringkat_2(self):
        pids = [f"P{i}" for i in range(1, 7)]
        s = generate_scheme(self._t(q=1), pids, num_groups=2)
        slots = {m.participant_a for m in s.matches if m.stage == "knockout"} \
            | {m.participant_b for m in s.matches if m.stage == "knockout"}
        self.assertFalse(any(x and x.startswith("Peringkat") for x in slots))

    def test_q_melebihi_ukuran_grup_error(self):
        pids = [f"P{i}" for i in range(1, 7)]  # 2 grup x 3
        with self.assertRaises(ValueError):
            generate_scheme(self._t(q=4), pids, num_groups=2)

    def test_q_kurang_1_error(self):
        with self.assertRaises(ValueError):
            self._t(q=0)

    def test_advance_isi_dari_klasemen(self):
        pids = ["A", "B", "C", "D", "E", "F", "G", "H"]
        s = generate_scheme(self._t(q=2), pids, num_groups=2)
        results = {}
        # menangkan semua match grup: pemenang = participant_a
        for m in s.matches:
            if m.stage == "group":
                results[m.id] = record_result(s, m.id, 2, 0, results=results)
        live = advance_scheme(s, results)
        # ronde KO pertama (4 qualifier) terisi dari klasemen
        first_ko = [m for m in live.matches
                    if m.stage == "knockout" and m.round == "R1"]
        if not first_ko:
            first_ko = [m for m in live.matches if m.stage == "knockout"]
            # 4 qualifier -> F langsung? next_pow2(4)=4 -> R1 + F
            rounds = {m.round for m in live.matches if m.stage == "knockout"}
            first_label = sorted(rounds, key=lambda r: (r != "R1", r))[0]
            first_ko = [m for m in live.matches
                        if m.stage == "knockout" and m.round == first_label]
        self.assertTrue(first_ko)
        for m in first_ko:
            for slot in (m.participant_a, m.participant_b):
                self.assertFalse(
                    is_placeholder(slot) and slot is not None
                    and "Grup" in (slot or ""),
                    f"placeholder grup {slot!r} di {m.id} belum terisi")
                # slot TBD antrean pemenang (None) boleh ada di ronde lanjut
                if slot is not None and "Grup" in slot:
                    self.fail(f"sisa placeholder {slot!r}")
        # tak ada lagi 'Juara/Peringkat Grup' di ronde KO pertama
        for m in first_ko:
            for slot in (m.participant_a, m.participant_b):
                if slot is not None:
                    self.assertNotIn("Grup", slot)

    def test_mc_group_knockout_q2(self):
        pids = [f"P{i}" for i in range(1, 9)]
        s = generate_scheme(self._t(q=2), pids, num_groups=2)
        mc = monte_carlo(s, equal_model(pids), n=30, seed=3)
        total = sum(mc.champion_share.values())
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_parse_group_qualifier(self):
        from tournament import parse_group_qualifier
        self.assertEqual(parse_group_qualifier("Juara Grup A"), (1, "A"))
        self.assertEqual(parse_group_qualifier("Peringkat 2 Grup B"), (2, "B"))
        self.assertEqual(parse_group_qualifier("Peringkat 3 Grup C"), (3, "C"))
        self.assertIsNone(parse_group_qualifier("Kalah SF-1"))
        self.assertIsNone(parse_group_qualifier("XII-01"))
        self.assertIsNone(parse_group_qualifier(None))

    def test_is_placeholder_peringkat(self):
        self.assertTrue(is_placeholder("Peringkat 2 Grup A"))
        self.assertTrue(is_placeholder("Juara Grup A"))
        self.assertTrue(is_placeholder("Kalah SF-1"))
        self.assertFalse(is_placeholder("XII-01"))

    def test_whatif_qualify_per_group(self):
        from tournament import what_if
        pids = [f"P{i}" for i in range(1, 9)]
        t = self._t(q=1)
        before, after = what_if(t, pids, {"qualify_per_group": 2},
                                num_groups=2)
        self.assertEqual(after.scheme.tournament.qualify_per_group, 2)
        self.assertNotEqual(
            {m.participant_a for m in after.scheme.matches},
            {m.participant_a for m in before.scheme.matches},
        )

    def test_store_roundtrip_qualify(self):
        import tempfile
        from tournament.registry import build_default_master
        from tournament.store import SQLiteStore
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "q.db")
        t = self._t(q=2)
        pids = [f"P{i}" for i in range(1, 9)]
        s = generate_scheme(t, pids, num_groups=2)
        st = SQLiteStore(path)
        st.save_all(build_default_master(4),
                    {"L1": {"tournament": t, "peserta": pids,
                            "scheme": s, "scheduled": None}}, 1)
        st.close()
        st2 = SQLiteStore(path)
        _, lomba, _ = st2.load_all()
        self.assertEqual(lomba["L1"]["tournament"].qualify_per_group, 2)
        st2.close()

    def test_web_buat_qualify(self):
        import urllib.parse
        import urllib.request
        # lewat unit: pastikan field form ada
        import web as web_mod
        html = web_mod.lomba_baru()
        self.assertIn("qualify_per_group", html)
        self.assertIn("Lolos/grup", html)


if __name__ == "__main__":
    unittest.main()
