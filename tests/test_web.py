"""Test UI web — stdlib only (server thread + urllib)."""
import os
import sys
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import web
from web import Handler, reset_store


class WebCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = web.run(0)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.thread.join()

    def setUp(self):
        reset_store(6)

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def get(self, path):
        with urllib.request.urlopen(self.url(path)) as r:
            return r.status, r.read().decode("utf-8")

    def post(self, path, data):
        body = urllib.parse.urlencode(data, doseq=True).encode()
        req = urllib.request.Request(self.url(path), data=body)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")

    def buat_lomba(self, n=6, fmt="knockout"):
        ids = [f"XII-{i:02d}" for i in range(1, n + 1)]
        code, _ = self.post("/lomba/buat", {
            "nama": "Uji", "format": fmt, "team_size": "1",
            "winner_count": "1", "duration_min": "30",
            "minimum_rest_min": "10", "arena_count": "2",
            "start_time": "08:00", "end_time": "17:00",
            "peserta": ids})
        self.assertEqual(code, 200)
        return "L1"

    def test_home(self):
        code, body = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn("Tournament", body)

    def test_kelas_tambah_hapus_escape(self):
        code, _ = self.post("/kelas/tambah",
                            {"id": "X-<script>", "nama": "<b>", "tingkat": "X"})
        self.assertEqual(code, 200)
        _, body = self.get("/kelas")
        self.assertNotIn("<script>", body)
        self.assertIn("&lt;script&gt;", body)
        code, _ = self.post("/kelas/hapus", {"id": "X-<script>"})
        self.assertEqual(code, 200)

    def test_buat_dan_detail_lomba(self):
        lid = self.buat_lomba()
        code, body = self.get(f"/lomba/{lid}")
        self.assertEqual(code, 200)
        for marker in ("BRACKET", "SCHEDULE", "FAIRNESS"):
            self.assertIn(marker, body)

    def test_buat_tanpa_peserta_400(self):
        code, _ = self.post("/lomba/buat", {"nama": "X", "format": "knockout"})
        self.assertEqual(code, 400)

    def test_banding(self):
        lid = self.buat_lomba()
        code, body = self.get(f"/lomba/{lid}/banding")
        self.assertEqual(code, 200)
        self.assertIn("COMPARISON", body)
        code, body = self.post("/banding/jalan", {"ids": [lid]})
        self.assertEqual(code, 200)
        self.assertIn("COMPARISON", body)

    def test_whatif_hitung_simpan(self):
        lid = self.buat_lomba()
        code, body = self.post(f"/lomba/{lid}/whatif/hitung", {"remove": "XII-06"})
        self.assertEqual(code, 200)
        self.assertIn("COMPARISON", body)
        code, body = self.post(f"/lomba/{lid}/whatif/simpan", {"remove": "XII-06"})
        self.assertEqual(code, 200)
        self.assertIn("L2", body)

    def test_probabilitas(self):
        lid = self.buat_lomba()
        code, body = self.post(f"/lomba/{lid}/probabilitas/hitung",
                               {"mode": "equal", "bobot": "", "n": "100", "seed": "1"})
        self.assertEqual(code, 200)
        self.assertIn("PROBABILITY", body)
        self.assertIn("BUKAN prediksi", body)

    def test_manual_swap(self):
        lid = self.buat_lomba(n=4)
        code, _ = self.post(f"/lomba/{lid}/manual/swap",
                            {"a": "L1-M01", "sa": "a", "b": "L1-M02", "sb": "a"})
        self.assertEqual(code, 200)
        _, body = self.get(f"/lomba/{lid}")
        self.assertIn("Manual", body)

    def test_skor_dan_klasemen(self):
        lid = self.buat_lomba(n=4)
        code, body = self.get(f"/lomba/{lid}/hasil")
        self.assertEqual(code, 200)
        self.assertIn("KLASEMEN", body)
        code, _ = self.post(f"/lomba/{lid}/skor",
                            {"match_id": "L1-M01", "sa_L1-M01": "2",
                             "sb_L1-M01": "1"})
        self.assertEqual(code, 200)
        code, body = self.get(f"/lomba/{lid}/hasil")
        self.assertIn("Skor tercatat: 1", body)
        code, body = self.get(f"/lomba/{lid}")
        self.assertIn("KLASEMEN", body)
        code, _ = self.post(f"/lomba/{lid}/skor/hapus",
                            {"match_id": "L1-M01"})
        self.assertEqual(code, 200)
        _, body = self.get(f"/lomba/{lid}/hasil")
        self.assertIn("belum ada skor", body)

    def test_skor_seri_knockout_400(self):
        lid = self.buat_lomba(n=4)
        code, body = self.post(f"/lomba/{lid}/skor",
                               {"match_id": "L1-M01", "sa_L1-M01": "1",
                                "sb_L1-M01": "1"})
        self.assertEqual(code, 400)
        self.assertIn("seri", body)

    def test_lintas_dan_optimasi(self):
        a = self.buat_lomba()
        code, _ = self.post("/lomba/buat", {
            "nama": "Uji2", "format": "knockout", "team_size": "1",
            "peserta": [f"XII-{i:02d}" for i in range(5, 7)]})
        self.assertEqual(code, 200)
        code, body = self.post("/lintas/jalan", {"ids": ["L1", "L2"]})
        self.assertEqual(code, 200)
        code, body = self.post("/optimasi/jalan",
                               {"ids": ["L1", "L2"], "max_shift_batches": "12"})
        self.assertEqual(code, 200)

    def test_404(self):
        try:
            self.get("/lomba/XXX")
            self.fail("harus 404")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 404)


if __name__ == "__main__":
    unittest.main()
