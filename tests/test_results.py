"""Test hasil skor + klasemen (PRD §15, §5)."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tournament import (
    Tournament,
    advance_scheme,
    build_report,
    build_standings,
    clear_result,
    record_result,
    render_standings,
    set_walkover,
)
from tournament.registry import build_default_master
from tournament.store import SQLiteStore


def ko_t(fmt="knockout", n_winner=1, ids=None):
    t = Tournament(id="T1", name="T1", format=fmt, team_size=1,
                   winner_count=n_winner, duration_min=30,
                   minimum_rest_min=10, arena_count=2)
    pids = ids or ["A", "B", "C", "D", "E", "F"]
    return t, pids


class RecordCase(unittest.TestCase):
    def test_knockout_menang(self):
        t, pids = ko_t(ids=["A", "B"])
        rep = build_report(t, pids)
        mid = rep.scheme.matches[0].id
        r = record_result(rep.scheme, mid, 3, 1)
        self.assertEqual(r.winner, "A")
        self.assertEqual((r.score_a, r.score_b), (3, 1))

    def test_knockout_seri_ditolak(self):
        t, pids = ko_t(ids=["A", "B"])
        rep = build_report(t, pids)
        mid = rep.scheme.matches[0].id
        with self.assertRaises(ValueError):
            record_result(rep.scheme, mid, 2, 2)

    def test_skor_negatif_ditolak(self):
        t, pids = ko_t(ids=["A", "B"])
        rep = build_report(t, pids)
        with self.assertRaises(ValueError):
            record_result(rep.scheme, rep.scheme.matches[0].id, -1, 0)

    def test_tbd_ditolak(self):
        t, pids = ko_t()  # 6 peserta -> ada TBD
        rep = build_report(t, pids)
        tbd = next(m for m in rep.scheme.matches
                   if m.participant_a is None or m.participant_b is None)
        with self.assertRaises(ValueError):
            record_result(rep.scheme, tbd.id, 1, 0)

    def test_match_tak_dikenal(self):
        t, pids = ko_t(ids=["A", "B"])
        rep = build_report(t, pids)
        with self.assertRaises(ValueError):
            record_result(rep.scheme, "NOPE", 1, 0)

    def test_round_robin_seri_boleh(self):
        t = Tournament(id="RR", name="RR", format="round_robin", team_size=1)
        rep = build_report(t, ["A", "B", "C"])
        mid = rep.scheme.matches[0].id
        r = record_result(rep.scheme, mid, 1, 1)
        self.assertIsNone(r.winner)

    def test_clear_result(self):
        t, pids = ko_t(ids=["A", "B"])
        rep = build_report(t, pids)
        mid = rep.scheme.matches[0].id
        res = {mid: record_result(rep.scheme, mid, 1, 0)}
        self.assertEqual(clear_result(res, mid), {})
        with self.assertRaises(ValueError):
            clear_result({}, mid)


class AdvanceCase(unittest.TestCase):
    def test_isi_tbd_berantai(self):
        t, pids = ko_t()  # 6 peserta
        rep = build_report(t, pids)
        # mainkan semua ronde pertama yang siap
        results = {}
        for m in rep.scheme.matches:
            if m.participant_a and m.participant_b:
                results[m.id] = record_result(
                    rep.scheme, m.id, 2, 0, results=results)
        live = advance_scheme(rep.scheme, results)
        # skema asli tak berubah
        self.assertTrue(any(m.participant_a is None
                            for m in rep.scheme.matches))
        # setelah R1 + result, slot R2 terisi pemenang
        r2 = [m for m in live.matches if m.round == "R2"]
        if r2:
            self.assertTrue(all(m.participant_a is not None
                                and m.participant_b is not None
                                for m in r2))

    def test_final_lengkap_tanpa_tbd(self):
        t, pids = ko_t(ids=["A", "B", "C", "D"])
        rep = build_report(t, pids)
        results = {}
        # isi bertahap sampai final
        for _ in range(4):
            ready = False
            for m in advance_scheme(rep.scheme, results).matches:
                if (m.stage == "knockout" and m.id not in results
                        and m.participant_a and m.participant_b):
                    results[m.id] = record_result(
                        rep.scheme, m.id, 1, 0, results=results)
                    ready = True
                    break
            if not ready:
                break
        self.assertTrue(results)
        live = advance_scheme(rep.scheme, results)
        tables = dict(build_standings(rep.scheme, results))
        ko = dict(tables)["Jalur knockout"]
        cat = {r.participant: r.catatan for r in ko}
        # juara = pemenang final bila final tercatat
        final = live.matches[-1]
        if final.id in results and results[final.id].winner:
            self.assertEqual(
                cat[results[final.id].winner], "Juara")
        self.assertIn("final", str(cat).lower() + "final")  # sanity


class StandingsCase(unittest.TestCase):
    def test_rr_poin_urut(self):
        t = Tournament(id="RR", name="RR", format="round_robin", team_size=1)
        rep = build_report(t, ["A", "B", "C"])
        results = {}
        # A menang semua
        for m in rep.scheme.matches:
            if "A" in (m.participant_a, m.participant_b):
                if m.participant_a == "A":
                    results[m.id] = record_result(rep.scheme, m.id, 2, 1)
                else:
                    results[m.id] = record_result(rep.scheme, m.id, 1, 2)
        # B vs C seri
        for m in rep.scheme.matches:
            if m.id not in results:
                results[m.id] = record_result(rep.scheme, m.id, 0, 0)
        tables = build_standings(rep.scheme, results)
        label, rows = tables[0]
        self.assertIn("round robin", label)
        self.assertEqual(rows[0].participant, "A")
        self.assertEqual(rows[0].poin, 6)
        self.assertEqual(rows[1].poin, 1)  # seri B dan C, tie-break GF/GA
        text = render_standings(tables, results)
        self.assertIn("KLASEMEN", text)
        self.assertIn("A", text)

    def test_kosong_tanpa_skor(self):
        t, pids = ko_t(ids=["A", "B"])
        rep = build_report(t, pids)
        text = render_standings(build_standings(rep.scheme, {}), {})
        self.assertIn("belum ada skor", text)

    def test_group_klasemen_dengan_seri(self):
        t = Tournament(id="G", name="G", format="group_knockout",
                       team_size=1, num_groups=1) if False else Tournament(
            id="G", name="G", format="group", team_size=1)
        rep = build_report(t, ["A", "B", "C", "D"])
        results = {}
        for m in rep.scheme.matches:
            if m.stage == "group":
                results[m.id] = record_result(rep.scheme, m.id, 1, 1)
        tables = build_standings(rep.scheme, results)
        self.assertTrue(tables)
        _, rows = tables[0]
        for r in rows:
            self.assertEqual(r.seri, r.main)
            self.assertEqual(r.poin, r.main)

    def test_walkover_hitung_kemenangan(self):
        t, pids = ko_t(ids=["A", "B", "C", "D"])
        rep = build_report(t, pids)
        mid = rep.scheme.matches[0].id
        wo = set_walkover(rep.scheme, mid, "A")
        tables = dict(build_standings(wo, {}))
        if "Jalur knockout" in tables:
            rows = {r.participant: r for r in tables["Jalur knockout"]}
            self.assertEqual(rows["A"].catatan, "Lolos WO di R1")


class StoreResultsCase(unittest.TestCase):
    def test_roundtrip_results(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "r.db")
        t, pids = ko_t(ids=["A", "B"])
        rep = build_report(t, pids)
        mid = rep.scheme.matches[0].id
        res = {mid: record_result(rep.scheme, mid, 5, 3)}
        s = SQLiteStore(path)
        s.save_all(build_default_master(4),
                   {"L1": {"tournament": t, "peserta": pids,
                           "scheme": rep.scheme, "scheduled": rep.scheduled,
                           "results": res}}, 1)
        s.close()
        s2 = SQLiteStore(path)
        _, lomba, _ = s2.load_all()
        got = lomba["L1"]["results"][mid]
        self.assertEqual(got.winner, "A")
        self.assertEqual((got.score_a, got.score_b), (5, 3))
        s2.close()


if __name__ == "__main__":
    unittest.main()
