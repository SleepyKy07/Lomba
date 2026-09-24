"""Test persistensi SQLite — stdlib only."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from tournament import (
    ClassInfo,
    Tournament,
    analyze_existing,
    build_report,
    move_match,
    set_walkover,
    swap_slots,
)
from tournament.registry import build_default_master
from tournament.store import SQLiteStore


def make_t(tid="L1", fmt="knockout"):
    return Tournament(id=tid, name=tid, format=fmt, team_size=4,
                      duration_min=30, minimum_rest_min=10, arena_count=2)


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "uji.db")

    def tearDown(self):
        self.tmp.cleanup()

    def test_fresh_seed_28(self):
        s = SQLiteStore(self.path)
        reg, lomba, seq = s.load_all()
        self.assertEqual(reg.count(), 28)
        self.assertEqual(lomba, {})
        self.assertEqual(seq, 0)
        s.close()

    def test_roundtrip_lengkap(self):
        s = SQLiteStore(self.path)
        reg = build_default_master(6)
        reg.add(ClassInfo(id="X-1", name="X-1", tingkat="X", jurusan="IPA"))
        t = make_t()
        rep = build_report(t, ["XII-01", "XII-02", "XII-03", "XII-04"])
        r1 = [m.id for m in rep.scheme.matches if m.round == "R1"]
        edited = swap_slots(rep.scheme, r1[0], "a", r1[1], "a")
        moved = move_match(rep.scheduled, r1[0], "09:00", 1, t)
        lomba = {"L1": {"tournament": t,
                        "peserta": ["XII-01", "XII-02", "XII-03", "XII-04"],
                        "scheme": edited, "scheduled": moved}}
        s.save_all(reg, lomba, 3)
        s.close()

        s2 = SQLiteStore(self.path)
        reg2, lomba2, seq2 = s2.load_all()
        self.assertEqual(reg2.count(), 7)
        self.assertEqual(reg2.get("X-1").jurusan, "IPA")
        self.assertEqual(seq2, 3)
        r = lomba2["L1"]
        self.assertEqual(r["tournament"].format, "knockout")
        self.assertEqual(r["peserta"], ["XII-01", "XII-02", "XII-03", "XII-04"])
        self.assertIn("Manual", r["scheme"].notes[-1])
        got = {m.id: (m.participant_a, m.participant_b)
               for m in r["scheme"].matches}
        want = {m.id: (m.participant_a, m.participant_b)
                for m in edited.matches}
        self.assertEqual(got, want)
        self.assertEqual(
            [(x.scheduled_time, x.arena) for x in r["scheduled"]],
            [(x.scheduled_time, x.arena) for x in moved])
        # Laporan dari data tersimpan tetap valid.
        rep2 = analyze_existing(r["scheme"], r["scheduled"])
        assert rep2.fairness is not None
        self.assertEqual(rep2.fairness.total_matches, 3)
        s2.close()

    def test_walkover_dan_status_tersimpan(self):
        s = SQLiteStore(self.path)
        t = make_t()
        rep = build_report(t, ["A", "B", "C", "D"])
        mid = [m.id for m in rep.scheme.matches if m.round == "R1"][0]
        ed = set_walkover(rep.scheme, mid, "A")
        s.save_all(build_default_master(4),
                   {"L1": {"tournament": t, "peserta": ["A", "B", "C", "D"],
                           "scheme": ed, "scheduled": None}}, 1)
        s.close()
        s2 = SQLiteStore(self.path)
        _, lomba2, _ = s2.load_all()
        wo = next(m for m in lomba2["L1"]["scheme"].matches if m.id == mid)
        self.assertEqual(wo.status, "walkover")
        self.assertEqual(
            len(lomba2["L1"]["scheme"].bye_details),
            len(ed.bye_details))
        s2.close()

    def test_kosong_tetap_kosong_tanpa_reseed(self):
        s = SQLiteStore(self.path)
        from tournament.registry import ClassRegistry
        s.save_all(ClassRegistry(), {}, 0)
        s.close()
        s2 = SQLiteStore(self.path)
        reg2, _, _ = s2.load_all()
        self.assertEqual(reg2.count(), 0)
        s2.close()


if __name__ == "__main__":
    unittest.main()
