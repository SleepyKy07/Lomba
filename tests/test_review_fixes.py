"""Regresi review bugfix — F3 WO, ready-check, banding, dup grup, f-string."""
import os
import sys
import unittest
from dataclasses import replace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tournament import (
    Tournament,
    advance_scheme,
    build_report,
    build_standings,
    equal_model,
    generate_scheme,
    is_placeholder,
    monte_carlo,
    record_result,
    set_walkover,
)
from tournament.generator_group import auto_group_count, generate_group_knockout
from tournament.manual import _validate_bracket_resolvable
from tournament.probability import simulate_once


def ko(n=4, wc=2, fmt="knockout", q=1):
    t = Tournament(id="T", name="T", format=fmt, team_size=1,
                   winner_count=wc, duration_min=30, minimum_rest_min=10,
                   arena_count=2, qualify_per_group=q)
    pids = [f"P{i}" for i in range(1, n + 1)]
    return t, pids


class F3WalkoverQueueCase(unittest.TestCase):
    """F3 walkover tidak boleh mengantre ke juara 1 di MC."""

    def test_f3_wo_tidak_pollute_queue(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        s = set_walkover(s, r1[0].id, r1[0].participant_a)
        s = set_walkover(s, r1[1].id, r1[1].participant_a)
        f3 = next(m for m in s.matches if m.round == "F3")
        s = set_walkover(s, f3.id, f3.participant_a)
        self.assertEqual(
            next(m for m in s.matches if m.round == "F3").status,
            "walkover")
        # F3 WO tak menambah slot nyata ke antrean juara: MC tetap valid
        import random
        rng = random.Random(0)
        model = equal_model(pids)
        for _ in range(30):
            champ, fins = simulate_once(s, model, rng)
            self.assertIn(champ, pids)
            self.assertNotEqual(len(fins), 0)
        mc = monte_carlo(s, model, n=40, seed=5)
        self.assertAlmostEqual(sum(mc.champion_share.values()), 1.0, places=6)

    def test_f3_wo_juara3_status(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        s = set_walkover(s, r1[0].id, r1[0].participant_a)
        s = set_walkover(s, r1[1].id, r1[1].participant_a)
        f3 = next(m for m in s.matches if m.round == "F3")
        winner = f3.participant_a
        s = set_walkover(s, f3.id, winner)
        tables = dict(build_standings(s, {}))
        cat = {r.participant: r.catatan
               for r in tables.get("Jalur knockout", [])}
        self.assertEqual(cat.get(winner), "Juara 3")

    def test_advance_f3_wo_tidak_masuk_antrean(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        s = set_walkover(s, r1[0].id, r1[0].participant_a)
        s = set_walkover(s, r1[1].id, r1[1].participant_a)
        f3 = next(m for m in s.matches if m.round == "F3")
        f3_wo_winner = f3.participant_a
        s = set_walkover(s, f3.id, f3_wo_winner)
        live = advance_scheme(s, {})
        f3l = next(m for m in live.matches if m.round == "F3")
        self.assertEqual(f3l.status, "walkover")
        self.assertFalse(is_placeholder(f3l.participant_a))
        fin = next(m for m in live.matches if m.round == "F")
        # F diisi pemenang R1 WO — pemenang F3 WO TIDAK boleh masuk F
        r1_winners = {m.participant_a for m in live.matches if m.round == "R1"}
        self.assertEqual(
            {fin.participant_a, fin.participant_b}, r1_winners)
        self.assertNotIn(f3_wo_winner,
                         {fin.participant_a, fin.participant_b} - r1_winners)


class WebReadyCase(unittest.TestCase):
    def test_f3_placeholder_tidak_ready(self):
        import web as web_mod
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        f3 = next(m for m in s.matches if m.round == "F3")
        # logika ready di web: pakai is_placeholder, bukan substring "Juara Grup"
        ready = (f3.status != "walkover"
                 and f3.participant_a is not None
                 and f3.participant_b is not None
                 and not is_placeholder(f3.participant_a)
                 and not is_placeholder(f3.participant_b))
        self.assertFalse(ready)
        # page lomba_hasil tidak menampilkan form skor utk placeholder
        web_mod.reset_store(6)
        web_mod.STORE["lomba"]["L1"] = {
            "tournament": t, "peserta": pids, "scheme": s,
            "scheduled": None, "results": {}}
        html = web_mod.lomba_hasil("L1")
        self.assertIn("menunggu ronde sebelumnya", html)
        self.assertNotIn(f"value='sa_{f3.id}'", html)

    def test_banding_pakai_winner_count(self):
        import web as web_mod
        web_mod.reset_store(6)
        t = Tournament(id="L1", name="X", format="knockout", team_size=1,
                       winner_count=3, duration_min=30, minimum_rest_min=10,
                       arena_count=2, qualify_per_group=2)
        pids = [f"P{i}" for i in range(1, 9)]
        web_mod.STORE["lomba"]["L1"] = {
            "tournament": t, "peserta": pids, "scheme": None,
            "scheduled": None, "results": {}}
        html = web_mod.lomba_banding("L1")
        self.assertEqual(html.count("COMPARISON"), 1)
        # knockout dengan winner_count=3 punya F3 di skema banding
        # (cek lewat build_report internal — cukup pastikan tak error)
        self.assertNotIn("Error", html)


class GroupDupCountCase(unittest.TestCase):
    def test_dup_tidak_ubah_jumlah_grup(self):
        # 4 unik + 1 dup: auto(4)=1, auto(5)=2 — dulu split pakai len mentah
        pids = ["A", "B", "C", "D", "A"]
        t = Tournament(id="G", name="G", format="group_knockout",
                       team_size=1, duration_min=30, minimum_rest_min=10,
                       arena_count=2, qualify_per_group=1)
        s = generate_group_knockout(t, pids)
        groups_in_matches = {m.group for m in s.matches if m.stage == "group"}
        ko_slots = {m.participant_a for m in s.matches if m.stage == "knockout"} \
            | {m.participant_b for m in s.matches if m.stage == "knockout"}
        # hanya 1 grup (unik=4 -> auto=1): tak ada "Juara Grup B"
        self.assertEqual(groups_in_matches, {"A"})
        self.assertNotIn("Juara Grup B", ko_slots)
        self.assertEqual(auto_group_count(4), 1)
        self.assertEqual(auto_group_count(5), 2)

    def test_generate_group_unique_count(self):
        pids = ["A", "B", "C", "D", "A"]
        t = Tournament(id="G", name="G", format="group", team_size=1,
                       duration_min=30, minimum_rest_min=10, arena_count=2)
        from tournament import generate_group
        g = generate_group(t, pids)
        self.assertEqual(len(g.participant_ids), 4)


class ValidateBracketMessageCase(unittest.TestCase):
    def test_fstring_available_terisi(self):
        from tournament.models import Match
        # match knockout butuh 1 pemenang, available=0 -> pesan harus angka
        bad = [Match(id="T-M01", tournament_id="T", round="F",
                     stage="knockout", participant_a=None,
                     participant_b="A")]
        with self.assertRaises(ValueError) as ctx:
            _validate_bracket_resolvable(bad)
        msg = str(ctx.exception)
        self.assertNotIn("{available}", msg)
        self.assertIn("tersedia 0", msg)


class IsPlaceholderCase(unittest.TestCase):
    def test_kalahman_bukan_placeholder(self):
        self.assertFalse(is_placeholder("Kalahman"))
        self.assertFalse(is_placeholder("PeringkatX"))
        self.assertTrue(is_placeholder("Kalah SF-1"))
        self.assertTrue(is_placeholder("Peringkat 2 Grup A"))


class StandingsAdvanceCase(unittest.TestCase):
    def test_ko_skor_terhitung_tanpa_advance_manual(self):
        t, pids = ko(n=4, wc=1)
        rep = build_report(t, pids)
        results = {}
        # mainkan R1 + F
        for _ in range(3):
            for m in advance_scheme(rep.scheme, results).matches:
                if (m.stage == "knockout" and m.id not in results
                        and m.participant_a and m.participant_b
                        and not is_placeholder(m.participant_a)
                        and not is_placeholder(m.participant_b)):
                    try:
                        results[m.id] = record_result(
                            rep.scheme, m.id, 1, 0, results=results)
                    except ValueError:
                        pass
        tables = dict(build_standings(rep.scheme, results))
        rows = {r.participant: r for r in tables["Jalur knockout"]}
        # juara punya main >= 1 dari KO + catatan Juara bila F selesai
        final = next(m for m in rep.scheme.matches if m.round == "F")
        if final.id in results and results[final.id].winner:
            w = results[final.id].winner
            self.assertEqual(rows[w].catatan, "Juara")
            # main dihitung dari advance (skor F masuk)
            self.assertGreaterEqual(rows[w].main, 1)


class RenderStandingsSafeCase(unittest.TestCase):
    def test_render_standings_cp1252(self):
        t, pids = ko(n=2, wc=1)
        rep = build_report(t, pids)
        from tournament import render_standings
        out = render_standings(build_standings(rep.scheme, {}), {})
        out.encode("cp1252")  # raise bila em-dash tersisa


class KelasFormAttrCase(unittest.TestCase):
    def test_tambah_form_punya_name_id_pisah_required(self):
        import re
        import web as web_mod
        web_mod.reset_store(4)
        html = web_mod.kelas_list()
        # Dulu name='id required' membuat field id kosong saat submit.
        self.assertIn("name='id' required", html)
        self.assertNotIn("name='id required'", html)
        attrs = re.findall(r"name='[^']*'", html)
        self.assertIn("name='id'", attrs)


class F3WalkoverPeringkat4Case(unittest.TestCase):
    def test_f3_wo_pertahankan_kalah_peringkat4(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        s = set_walkover(s, r1[0].id, r1[0].participant_a)
        s = set_walkover(s, r1[1].id, r1[1].participant_a)
        f3 = next(m for m in s.matches if m.round == "F3")
        winner, loser = f3.participant_a, f3.participant_b
        s = set_walkover(s, f3.id, winner)
        f3b = next(m for m in s.matches if m.round == "F3")
        # Konvensi: pemenang di a, kalah di b (bukan dihapus).
        self.assertEqual(f3b.participant_a, winner)
        self.assertEqual(f3b.participant_b, loser)
        self.assertEqual(f3b.status, "walkover")
        tables = dict(build_standings(s, {}))
        cat = {r.participant: r.catatan
               for r in tables.get("Jalur knockout", [])}
        self.assertEqual(cat.get(winner), "Juara 3")
        self.assertEqual(cat.get(loser), "Peringkat 4")
        # MC tetap valid (F3 WO tak mengantre juara 1).
        mc = monte_carlo(s, equal_model(pids), n=40, seed=5)
        self.assertAlmostEqual(sum(mc.champion_share.values()), 1.0, places=6)

    def test_f3_wo_note_bukan_limitasi_salah(self):
        t, pids = ko(n=4, wc=2)
        s = generate_scheme(t, pids)
        r1 = [m for m in s.matches if m.round == "R1"]
        s = set_walkover(s, r1[0].id, r1[0].participant_a)
        s = set_walkover(s, r1[1].id, r1[1].participant_a)
        f3 = next(m for m in s.matches if m.round == "F3")
        s = set_walkover(s, f3.id, f3.participant_a)
        # Dulu note "Limitasi: WO ronde F3 TIDAK mengisi F3" (salah konteks).
        self.assertTrue(any("peringkat 4 (WO)" in n for n in s.notes))
        self.assertFalse(any("Limitasi: WO ronde F3" in n for n in s.notes))


class PureGroupStandingsCase(unittest.TestCase):
    def test_group_murni_tanpa_kata_lolos(self):
        t = Tournament(id="G", name="G", format="group", team_size=1,
                       duration_min=30, minimum_rest_min=10, arena_count=2)
        rep = build_report(t, list("ABCD"))
        results = {}
        for m in rep.scheme.matches:
            if m.stage == "group":
                results[m.id] = record_result(rep.scheme, m.id, 1, 0,
                                              results=results)
        tables = dict(build_standings(rep.scheme, results))
        rows = tables.get("Klasemen grup A", [])
        top = next(r for r in rows if r.participant == "A")
        self.assertIn("juara grup", top.catatan)
        self.assertNotIn("lolos", top.catatan)

    def test_group_knockout_tetap_lolos(self):
        t = Tournament(id="Q", name="Q", format="group_knockout",
                       team_size=1, duration_min=30, minimum_rest_min=10,
                       arena_count=2, qualify_per_group=2)
        pids = [f"P{i}" for i in range(1, 9)]
        rep = build_report(t, pids, 2)
        results = {}
        for m in rep.scheme.matches:
            if m.stage == "group":
                results[m.id] = record_result(rep.scheme, m.id, 1, 0,
                                              results=results)
        tables = dict(build_standings(rep.scheme, results))
        rows = tables.get("Klasemen grup A", [])
        top = next(r for r in rows if r.catatan)
        self.assertIn("lolos", top.catatan)


class NumGroupsZeroCase(unittest.TestCase):
    def test_generate_group_num_groups_0_error(self):
        from tournament import generate_group
        t = Tournament(id="G", name="G", format="group", team_size=1,
                       duration_min=30, minimum_rest_min=10, arena_count=2)
        with self.assertRaises(ValueError):
            generate_group(t, list("ABCD"), 0)

    def test_generate_group_knockout_num_groups_0_error(self):
        t = Tournament(id="G", name="G", format="group_knockout",
                       team_size=1, duration_min=30, minimum_rest_min=10,
                       arena_count=2)
        with self.assertRaises(ValueError):
            generate_group_knockout(t, list("ABCD"), 0)


class F3ValidatorAvailableCase(unittest.TestCase):
    def test_f3_tidak_inflate_available(self):
        # F3 punya need=0 (Kalah placeholder) — dulu available += 1
        # (false-OK untuk F bila antrean pemenang kurang).
        from tournament.models import Match
        # R1 x1 menghasilkan 1 pemenang; F3 di tengah; F butuh 2.
        # Tanpa F3: available setelah R1 = 1, F butuh 2 -> harus gagal.
        matches = [
            Match(id="T-M01", tournament_id="T", round="R1",
                  stage="knockout", participant_a="A", participant_b="B"),
            Match(id="T-M03", tournament_id="T", round="F3",
                  stage="knockout", participant_a="Kalah R1-1",
                  participant_b="Kalah R1-2"),
            Match(id="T-M02", tournament_id="T", round="F",
                  stage="knockout", participant_a=None, participant_b=None),
        ]
        with self.assertRaises(ValueError) as ctx:
            _validate_bracket_resolvable(matches)
        self.assertIn("tersedia", str(ctx.exception))
        # Bracket valid tetap lolos (2 R1 -> F butuh 2).
        ok = [
            Match(id="T-M01", tournament_id="T", round="R1",
                  stage="knockout", participant_a="A", participant_b="B"),
            Match(id="T-M02", tournament_id="T", round="R1",
                  stage="knockout", participant_a="C", participant_b="D"),
            Match(id="T-M04", tournament_id="T", round="F3",
                  stage="knockout", participant_a="Kalah R1-1",
                  participant_b="Kalah R1-2"),
            Match(id="T-M03", tournament_id="T", round="F",
                  stage="knockout", participant_a=None, participant_b=None),
        ]
        _validate_bracket_resolvable(ok)  # tidak raise


if __name__ == "__main__":
    unittest.main()
