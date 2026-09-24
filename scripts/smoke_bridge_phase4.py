"""Smoke bridge Tahap 4: fungsi *_json di pyengine.js dieksekusi di CPython.

Usage: python scripts/smoke_bridge_phase4.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tournament import (  # noqa: E402
    Tournament,
    advance_scheme,
    analyze_existing,
    build_report,
    build_standings,
    clear_result,
    compare_reports,
    custom_model,
    detect_cross_event_conflicts,
    equal_model,
    exact_equal_title_probability,
    monte_carlo,
    optimize_multi_event,
    percent_model,
    record_result,
    render_bracket,
    render_comparison,
    render_fairness,
    render_probability,
    render_schedule,
    render_standings,
    total_load_across_events,
    what_if,
)
from tournament.models import ByeDetail, Match, Result, Scheme, ScheduledMatch, is_placeholder  # noqa: E402


def scheduled_from_list(t, arr):
    out = []
    for s in arr or []:
        m = s["match"]
        out.append(
            ScheduledMatch(
                match=Match(
                    id=m["id"],
                    tournament_id=t.id,
                    round=m["round"],
                    stage=m["stage"],
                    participant_a=m.get("participant_a"),
                    participant_b=m.get("participant_b"),
                    group=m.get("group") or "",
                    status=m.get("status") or "scheduled",
                ),
                scheduled_time=s["scheduled_time"],
                arena=int(s["arena"]),
                start_min=int(s.get("start_min") or 0),
            )
        )
    return out


def scheduled_to_list(scheduled):
    return [
        {
            "match": {
                "id": s.match.id,
                "round": s.match.round,
                "stage": s.match.stage,
                "participant_a": s.match.participant_a,
                "participant_b": s.match.participant_b,
                "group": s.match.group,
                "status": s.match.status,
            },
            "scheduled_time": s.scheduled_time,
            "arena": s.arena,
            "start_min": s.start_min,
        }
        for s in scheduled
    ]


def scheme_from_dict(d, t):
    matches = [
        Match(
            id=m["id"],
            tournament_id=t.id,
            round=m["round"],
            stage=m["stage"],
            participant_a=m.get("participant_a"),
            participant_b=m.get("participant_b"),
            group=m.get("group") or "",
            status=m.get("status") or "scheduled",
        )
        for m in d.get("matches") or []
    ]
    byes = [
        ByeDetail(
            participant=b["participant"],
            entry_round=b["entry_round"],
            skipped_rounds=list(b.get("skipped_rounds") or []),
            wins_needed=int(b["wins_needed"]),
        )
        for b in d.get("bye_details") or []
    ]
    return Scheme(
        tournament=t,
        participant_ids=list(d.get("participant_ids") or []),
        matches=matches,
        notes=list(d.get("notes") or []),
        bye_details=byes,
    )


def tournament_from_row(row):
    return Tournament(
        id=row["id"],
        name=row["name"],
        format=row["format"],
        team_size=int(row.get("team_size") or 4),
        winner_count=int(row.get("winner_count") or 1),
        duration_min=int(row.get("duration_min") or 30),
        minimum_rest_min=int(row.get("minimum_rest_min") or 10),
        arena_count=int(row.get("arena_count") or 2),
        date=row.get("date") or "",
        start_time=row.get("start_time") or "08:00",
        end_time=row.get("end_time") or "17:00",
        qualify_per_group=int(row.get("qualify_per_group") or 1),
    )


def results_from_list(arr):
    out = {}
    for r in arr or []:
        mid = r.get("match_id") or r.get("id")
        if not mid:
            continue
        out[mid] = Result(
            match_id=mid,
            winner=r.get("winner"),
            score_a=int(r.get("score_a") or 0),
            score_b=int(r.get("score_b") or 0),
        )
    return out


def results_to_list(results, tid):
    return [
        {
            "tournament_id": tid,
            "match_id": mid,
            "winner": res.winner,
            "score_a": res.score_a,
            "score_b": res.score_b,
        }
        for mid, res in (results or {}).items()
    ]


def report_dict(rep):
    return {
        "scheme": rep.scheme.to_dict(),
        "scheduled": scheduled_to_list(rep.scheduled),
        "notes": list(rep.scheme.notes),
        "sched_errors": list(rep.sched_errors),
        "bracket": render_bracket(rep.scheme.matches),
        "schedule": render_schedule(rep.scheduled),
        "fairness": render_fairness(rep.fairness, rep.rest, rep.conflicts),
        "summary": rep.summary_row(),
        "conflicts": list(rep.conflicts),
    }


def extract_bridge(js_path: Path) -> str:
    text = js_path.read_text(encoding="utf-8")
    m = re.search(r'var BRIDGE = \[(.*?)\]\.join\("\\n"\);', text, re.S)
    if not m:
        raise SystemExit("BRIDGE block not found")
    raw = m.group(1)
    lines = re.findall(r'"((?:\\.|[^"\\])*)"', raw)
    joined = "\n".join(lines)
    joined = joined.encode("utf-8").decode("unicode_escape")
    return joined


def main() -> int:
    js = ROOT / "docs" / "js" / "pyengine.js"
    bridge_src = extract_bridge(js)
    g: dict = {}
    # execute package first (path already in sys.path)
    exec(bridge_src, g)

    pids = ["XII-01", "XII-02", "XII-03", "XII-04"]
    row = {
        "id": "L1",
        "name": "Smoke",
        "format": "knockout",
        "team_size": 4,
        "winner_count": 1,
        "duration_min": 30,
        "minimum_rest_min": 10,
        "arena_count": 2,
        "qualify_per_group": 1,
        "date": "2026-01-01",
        "start_time": "08:00",
        "end_time": "17:00",
        "participant_ids": pids,
    }

    rep_json = g["create_report_json"](row)
    rep = json.loads(rep_json)
    assert rep["scheme"]["matches"], "bracket kosong"
    assert rep["bracket"].startswith("=="), "render_bracket"
    print("OK create_report_json")

    scheme_d = rep["scheme"]
    scheduled = rep["scheduled"]
    ana = json.loads(g["analyze_saved_json"](row, scheme_d, scheduled))
    assert ana["summary"]["total_matches"] >= 3
    print("OK analyze_saved_json")

    # skor R1 knockout (dua match pertama biasanya R1)
    t = tournament_from_row(row)
    scheme = scheme_from_dict(scheme_d, t)
    r1 = [m for m in scheme.matches if m.stage == "knockout" and m.participant_a and m.participant_b and not is_placeholder(m.participant_a) and not is_placeholder(m.participant_b)]
    assert r1, "tidak ada match R1 siap"
    mid = r1[0].id
    sa, sb = 3, 1
    rec = json.loads(g["record_score_json"](row, scheme_d, [], mid, sa, sb))
    assert rec["ok"], rec
    results = rec["results"]
    assert results[0]["match_id"] == mid and results[0]["score_a"] == 3
    print("OK record_score_json")

    st = json.loads(g["standings_json"](row, scheme_d, results))
    assert "KLASEMEN" in st["standings"] or st["standings"].strip()
    assert any(m["id"] == mid for m in st["matches"])
    print("OK standings_json")

    cl = json.loads(g["clear_score_json"](row, scheme_d, results, mid))
    assert cl["ok"] and cl["score_count"] == 0
    print("OK clear_score_json")

    # score ulang untuk whatif/prob
    results = json.loads(g["record_score_json"](row, scheme_d, [], mid, 3, 1))["results"]

    wi = json.loads(
        g["whatif_json"](row, scheme_d, {"add": ["XII-05", "XII-06"]}, None)
    )
    assert "comparison" in wi and wi["after"]["participants"] == 6
    print("OK whatif_json")

    pb = json.loads(g["probability_json"](row, scheme_d, "equal", {}, 50, 42))
    assert "PROBABILITY" in pb["render"] or pb["render"].strip()
    assert pb["exact"] is not None
    print("OK probability_json")

    row2 = dict(row, id="L2", participant_ids=["XII-01", "XII-02", "XII-07", "XII-08"])
    band = json.loads(g["banding_json"]([row, row2]))
    assert band["labels"] == ["L1", "L2"]
    assert "COMPARISON" in band["comparison"] or band["comparison"].strip()
    print("OK banding_json")

    lt = json.loads(g["lintas_json"]([row, row2]))
    assert "total_load" in lt and "findings" in lt
    print("OK lintas_json")

    opt = json.loads(g["optimasi_json"]([row, row2], 4))
    assert opt["labels"] == ["L1", "L2"]
    assert len(opt["summaries"]) == 2
    print("OK optimasi_json")

    # --- manual: walkover / swap / move / replace ---
    ready = [
        m
        for m in scheme.matches
        if m.stage == "knockout"
        and m.participant_a
        and m.participant_b
        and not is_placeholder(m.participant_a)
        and not is_placeholder(m.participant_b)
    ]
    mid_wo = ready[0].id
    winner_wo = ready[0].participant_a
    wo = json.loads(
        g["manual_json"](
            "walkover",
            row,
            scheme_d,
            scheduled,
            {"match_id": mid_wo, "winner_id": winner_wo},
        )
    )
    assert wo["ok"], wo
    assert wo["clear_results"] is True
    wo_m = next(m for m in wo["scheme"]["matches"] if m["id"] == mid_wo)
    assert wo_m["status"] == "walkover"
    assert any(n.startswith("Manual: walkover") for n in wo["report"]["notes"])
    print("OK manual_json walkover")

    ready2 = [
        m
        for m in scheme.matches
        if m.stage == "knockout"
        and m.participant_a
        and m.participant_b
        and not is_placeholder(m.participant_a)
        and not is_placeholder(m.participant_b)
    ]
    sw = json.loads(
        g["manual_json"](
            "swap",
            row,
            scheme_d,
            scheduled,
            {
                "match_id_a": ready2[0].id,
                "slot_a": "a",
                "match_id_b": ready2[1].id,
                "slot_b": "a",
            },
        )
    )
    assert sw["ok"], sw
    assert sw["clear_results"] is True
    assert any(n.startswith("Manual: tukar") for n in sw["report"]["notes"])
    print("OK manual_json swap")

    mid_mv = scheduled[0]["match"]["id"]
    mv = json.loads(
        g["manual_json"](
            "move",
            row,
            scheme_d,
            scheduled,
            {"match_id": mid_mv, "new_time": "09:30", "new_arena": 1},
        )
    )
    assert mv["ok"], mv
    assert mv["clear_results"] is False
    moved = next(s for s in mv["scheduled"] if s["match"]["id"] == mid_mv)
    assert moved["scheduled_time"] == "09:30"
    print("OK manual_json move")

    old_p = scheme.participant_ids[0]
    new_p = "XII-99"
    rp = json.loads(
        g["manual_json"](
            "replace",
            row,
            scheme_d,
            scheduled,
            {"old_id": old_p, "new_id": new_p},
        )
    )
    assert rp["ok"], rp
    assert new_p in rp["participant_ids"] and old_p not in rp["participant_ids"]
    assert any(n.startswith("Manual:") and new_p in n for n in rp["report"]["notes"])
    print("OK manual_json replace")

    bad = json.loads(
        g["manual_json"](
            "walkover",
            row,
            scheme_d,
            scheduled,
            {"match_id": mid_wo, "winner_id": "TIDAK-ADA"},
        )
    )
    assert not bad["ok"] and bad["error"]
    print("OK manual_json error path")

    # BRIDGE import names present
    for name in (
        "create_report_json",
        "standings_json",
        "whatif_json",
        "probability_json",
        "banding_json",
        "lintas_json",
        "optimasi_json",
        "manual_json",
    ):
        assert name in g, name

    # unused imports in smoke module still validated via bridge
    _ = (
        advance_scheme,
        analyze_existing,
        build_report,
        build_standings,
        clear_result,
        compare_reports,
        custom_model,
        detect_cross_event_conflicts,
        equal_model,
        exact_equal_title_probability,
        monte_carlo,
        optimize_multi_event,
        percent_model,
        record_result,
        render_comparison,
        total_load_across_events,
        what_if,
    )

    print("BRIDGE_PHASE4_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
