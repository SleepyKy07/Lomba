"""Persistensi SQLite (stdlib) — satu file, tanpa install.

Menyimpan: master kelas, definisi lomba + peserta, override skema manual
(match/notes/bye) + override jadwal. Analisis selalu dihitung ulang
dari data tersimpan (single source of truth = input, bukan output).
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading

from .models import (
    ByeDetail,
    ClassInfo,
    Match,
    Result,
    ScheduledMatch,
    Scheme,
    Tournament,
)
from .registry import ClassRegistry

SCHEMA = """
CREATE TABLE IF NOT EXISTS classes (
    id TEXT PRIMARY KEY, name TEXT NOT NULL,
    tingkat TEXT NOT NULL DEFAULT '', jurusan TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS tournaments (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, format TEXT NOT NULL,
    team_size INTEGER NOT NULL, winner_count INTEGER NOT NULL,
    duration_min INTEGER NOT NULL, minimum_rest_min INTEGER NOT NULL,
    arena_count INTEGER NOT NULL, date TEXT NOT NULL DEFAULT '',
    start_time TEXT NOT NULL, end_time TEXT NOT NULL,
    participant_ids TEXT NOT NULL,
    manual_scheme TEXT, manual_scheduled TEXT, results_json TEXT,
    qualify_per_group INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def scheme_to_json(scheme: Scheme) -> str:
    return json.dumps(scheme.to_dict(), ensure_ascii=False)


def scheme_from_json(data: str, tournament: Tournament) -> Scheme:
    d = json.loads(data)
    return Scheme(
        tournament=tournament,
        participant_ids=d["participant_ids"],
        matches=[Match(
            id=m["id"], tournament_id=tournament.id, round=m["round"],
            stage=m["stage"], participant_a=m["participant_a"],
            participant_b=m["participant_b"], group=m.get("group", ""),
            status=m.get("status", "scheduled")) for m in d["matches"]],
        notes=d.get("notes", []),
        bye_details=[ByeDetail(
            participant=b["participant"], entry_round=b["entry_round"],
            skipped_rounds=b.get("skipped_rounds", []),
            wins_needed=b["wins_needed"]) for b in d.get("bye_details", [])],
    )


def scheduled_to_json(scheduled: list[ScheduledMatch]) -> str:
    return json.dumps([{
        "match": {"id": s.match.id, "round": s.match.round,
                  "stage": s.match.stage,
                  "participant_a": s.match.participant_a,
                  "participant_b": s.match.participant_b,
                  "group": s.match.group, "status": s.match.status},
        "scheduled_time": s.scheduled_time, "arena": s.arena,
        "start_min": s.start_min} for s in scheduled], ensure_ascii=False)


def scheduled_from_json(data: str, tournament: Tournament) -> list[ScheduledMatch]:
    out = []
    for s in json.loads(data):
        m = s["match"]
        out.append(ScheduledMatch(
            match=Match(id=m["id"], tournament_id=tournament.id, round=m["round"],
                        stage=m["stage"], participant_a=m["participant_a"],
                        participant_b=m["participant_b"], group=m.get("group", ""),
                        status=m.get("status", "scheduled")),
            scheduled_time=s["scheduled_time"], arena=s["arena"],
            start_min=s["start_min"]))
    return out


class SQLiteStore:
    def __init__(self, path: str):
        fresh = not os.path.exists(path)
        self.path = path
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.executescript(SCHEMA)
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(tournaments)")}
        if "results_json" not in cols:
            self.db.execute(
                "ALTER TABLE tournaments ADD COLUMN results_json TEXT")
        if "qualify_per_group" not in cols:
            self.db.execute(
                "ALTER TABLE tournaments ADD COLUMN qualify_per_group "
                "INTEGER NOT NULL DEFAULT 1")
        self.db.commit()
        if fresh:
            self._seed_default()

    def _seed_default(self) -> None:
        for i in range(1, 29):
            cid = f"XII-{i:02d}"
            self.db.execute(
                "INSERT INTO classes (id, name, tingkat) VALUES (?, ?, ?)",
                (cid, cid, "XII"))
        self.db.execute("INSERT INTO meta (key, value) VALUES ('seq', '0')")
        self.db.commit()

    # ----- tulis -----

    def save_all(self, registry: ClassRegistry, lomba: dict, seq: int) -> None:
        with self.lock:
            cur = self.db.cursor()
            cur.execute("DELETE FROM classes")
            for c in registry.list_all():
                cur.execute(
                    "INSERT INTO classes (id, name, tingkat, jurusan)"
                    " VALUES (?, ?, ?, ?)",
                    (c.id, c.name, c.tingkat, c.jurusan))
            cur.execute("DELETE FROM tournaments")
            for lid, rec in lomba.items():
                t = rec["tournament"]
                results = rec.get("results") or {}
                results_json = json.dumps(
                    {k: {"winner": v.winner, "score_a": v.score_a,
                         "score_b": v.score_b}
                     for k, v in results.items()}, ensure_ascii=False)
                cur.execute(
                    "INSERT INTO tournaments (id, name, format, team_size,"
                    " winner_count, duration_min, minimum_rest_min, arena_count,"
                    " date, start_time, end_time, participant_ids,"
                    " manual_scheme, manual_scheduled, results_json,"
                    " qualify_per_group)"
                    " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (lid, t.name, t.format, t.team_size, t.winner_count,
                     t.duration_min, t.minimum_rest_min, t.arena_count, t.date,
                     t.start_time, t.end_time, json.dumps(rec["peserta"]),
                     scheme_to_json(rec["scheme"]) if rec["scheme"] else None,
                     scheduled_to_json(rec["scheduled"])
                     if rec["scheduled"] else None,
                     results_json, t.qualify_per_group))
            cur.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES ('seq', ?)",
                (str(seq),))
            self.db.commit()

    # ----- baca -----

    def load_all(self) -> tuple[ClassRegistry, dict, int]:
        with self.lock:
            reg = ClassRegistry()
            for cid, name, tingkat, jurusan in self.db.execute(
                    "SELECT id, name, tingkat, jurusan FROM classes ORDER BY id"):
                reg.add(ClassInfo(id=cid, name=name, tingkat=tingkat,
                                  jurusan=jurusan))
            lomba: dict = {}
            for row in self.db.execute(
                    "SELECT id, name, format, team_size, winner_count,"
                    " duration_min, minimum_rest_min, arena_count, date,"
                    " start_time, end_time, participant_ids, manual_scheme,"
                    " manual_scheduled, results_json, qualify_per_group"
                    " FROM tournaments ORDER BY id"):
                (lid, name, fmt, team_size, winner_count, duration_min,
                 minimum_rest_min, arena_count, date, start_time, end_time,
                 pids_json, scheme_json, sched_json, results_json,
                 qualify_per_group) = row
                t = Tournament(id=lid, name=name, format=fmt, team_size=team_size,
                               winner_count=winner_count,
                               duration_min=duration_min,
                               minimum_rest_min=minimum_rest_min,
                               arena_count=arena_count, date=date,
                               start_time=start_time, end_time=end_time,
                               qualify_per_group=qualify_per_group or 1)
                scheme = (scheme_from_json(scheme_json, t)
                          if scheme_json else None)
                sched = (scheduled_from_json(sched_json, t)
                         if sched_json else None)
                results = {
                    mid: Result(match_id=mid, winner=v.get("winner"),
                                score_a=int(v.get("score_a", 0)),
                                score_b=int(v.get("score_b", 0)))
                    for mid, v in json.loads(results_json or "{}").items()}
                lomba[lid] = {"tournament": t,
                              "peserta": json.loads(pids_json),
                              "scheme": scheme, "scheduled": sched,
                              "results": results}
            seq = int(self.db.execute(
                "SELECT value FROM meta WHERE key='seq'").fetchone()[0])
            return reg, lomba, seq

    def close(self) -> None:
        self.db.close()
