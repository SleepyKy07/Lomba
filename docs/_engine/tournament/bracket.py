"""Render teks Phase 1 (output minimal PRD §13)."""
from __future__ import annotations

from .fairness import FairnessReport, RestReport
from .models import Match, ScheduledMatch


def _label(pid: str | None) -> str:
    return pid if pid else "TBD"


def _wo(m: Match) -> str:
    return " [walkover]" if m.status == "walkover" else ""


def render_bracket(matches: list[Match]) -> str:
    order = ["G", "P", "R1", "R2", "R3", "R4", "SF", "F3", "F"]
    bucket: dict[str, list[Match]] = {}
    for m in matches:
        key = "G" if m.stage == "group" else m.round
        bucket.setdefault(key, []).append(m)
    lines = ["== BRACKET =="]
    for key in order:
        ms = bucket.get(key, [])
        if not ms:
            continue
        lines.append(f"-- {key} ({len(ms)} match) --")
        for m in ms:
            extra = f" [{m.group}]" if m.group else ""
            lines.append(
                f"  {m.id}: {_label(m.participant_a)} vs {_label(m.participant_b)}"
                f"  (ronde {m.round}{extra}){_wo(m)}"
            )
    for key in sorted(bucket):
        if key in order:
            continue
        lines.append(f"-- {key} ({len(bucket[key])} match) --")
        for m in bucket[key]:
            lines.append(
                f"  {m.id}: {_label(m.participant_a)} vs {_label(m.participant_b)}"
                f"{_wo(m)}"
            )
    return "\n".join(lines)


def render_schedule(scheduled: list[ScheduledMatch]) -> str:
    lines = ["== SCHEDULE =="]
    for s in sorted(scheduled, key=lambda x: (x.start_min, x.arena)):
        m = s.match
        lines.append(
            f"{s.scheduled_time} | Arena {s.arena} | {m.id} "
            f"({_label(m.participant_a)} vs {_label(m.participant_b)}) [{m.round}]{_wo(m)}"
        )
    return "\n".join(lines)


def _minmax(d: dict[str, int]) -> str:
    vals = list(d.values()) or [0]
    return f"{min(vals)}-{max(vals)}"


def render_fairness(f: FairnessReport, r: RestReport, conflicts: list[str]) -> str:
    lines = [
        "== FAIRNESS ==",
        f"Total pertandingan: {f.total_matches}",
        f"Bye ({f.bye_count}): {', '.join(f.bye_recipients) if f.bye_recipients else '-'}",
    ]
    for d in f.bye_details:
        lines.append(
            f"  bye {d.participant}: masuk {d.entry_round}, "
            f"lewati {', '.join(d.skipped_rounds)}; butuh {d.wins_needed} menang"
        )
    lines.extend([
        f"Match terjadwal: min {f.min_match}, max {f.max_match}, avg {f.avg_match}, "
        f"difference {f.match_diff}",
        f"Jaminan main (gugur langsung): {_minmax(f.guaranteed)}x | "
        f"Maksimal (juara): {_minmax(f.max_possible)}x | "
        f"potential diff {f.potential_diff}",
        f"Player-load diff: {f.player_load_diff} "
        f"(rumus: match x team_size; max {max(f.player_load.values()) if f.player_load else 0})",
        f"Path-to-title: butuh menang {_minmax(f.wins_to_title)} (diff {f.path_diff})",
        f"  ke semifinal: {_minmax(f.wins_to_semifinal)} | "
        f"ke final: {_minmax(f.wins_to_final)}",
        f"  detail juara: {dict(sorted(f.wins_to_title.items()))}",
    ])
    if r.min_rest is None:
        lines.append("Rest: - (tiap kelas hanya 1 slot pasti; ronde TBD tak terhitung)")
    else:
        lines.append(
            f"Rest: min {r.min_rest} mnt, max {r.max_rest} mnt, avg {r.avg_rest} mnt, "
            f"difference {r.rest_diff} mnt"
        )
    if r.violations:
        lines.append("Rest violation:")
        lines.extend(f"  ! {v}" for v in r.violations)
    if conflicts:
        lines.append("Conflict:")
        lines.extend(f"  ! {c}" for c in conflicts)
    else:
        lines.append("Conflict: 0")
    if f.warnings:
        lines.append("Warning:")
        lines.extend(f"  ! {w}" for w in f.warnings)
    lines.append("Appearances (match per kelas):")
    for pid in sorted(f.appearances):
        lines.append(
            f"  {pid}: {f.appearances[pid]}x terjadwal "
            f"(jaminan {f.guaranteed[pid]}x, maks {f.max_possible[pid]}x), "
            f"load {f.player_load[pid]}"
        )
    return "\n".join(lines)
