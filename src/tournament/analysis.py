"""Pipeline analisis: satu pintu generate + analisis ulang.

Dipakai comparison, what-if, dan manual adjustment agar angka selalu
konsisten (setiap perubahan → analisis dijalankan ulang, PRD §12).

Kontrak analyze_existing():
- scheduled yang diteruskan di-REBIND ke match skema via match ID,
  sehingga rest/conflict selalu dari susunan pasca-edit.
- Bila ID tak sinkron (match hilang/baru), jadwal dibuat ulang penuh
  dan dicatat di sched_errors.
- Jadwal yang diteruskan/divalidasi terhadap arena + jendela waktu lomba.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace

from .fairness import (
    FairnessReport,
    RestReport,
    analyze_rest,
    analyze_scheme,
    detect_internal_conflict,
)
from .generator import generate_scheme
from .models import ScheduledMatch, Scheme, Tournament
from .scheduler import schedule_advanced, schedule_matches

SCHEDULERS = ("greedy", "advanced")


def _run_scheduler(
    name: str, tournament: Tournament, matches: list
) -> tuple[list[ScheduledMatch], list[str]]:
    if name == "greedy":
        return schedule_matches(tournament, matches)
    if name == "advanced":
        return schedule_advanced(tournament, matches)
    raise ValueError(f"scheduler harus salah satu {list(SCHEDULERS)}.")


@dataclass
class SchemeReport:
    scheme: Scheme
    scheduled: list[ScheduledMatch] = field(default_factory=list)
    sched_errors: list[str] = field(default_factory=list)
    fairness: FairnessReport | None = None
    rest: RestReport | None = None
    conflicts: list[str] = field(default_factory=list)

    def summary_row(self) -> dict[str, str | int]:
        """Baris metrik untuk tabel perbandingan (PRD §11)."""
        if self.fairness is None or self.rest is None:
            raise ValueError("SchemeReport belum dianalisis (fairness/rest kosong).")
        return {
            "format": self.scheme.tournament.format,
            "participants": len(self.scheme.participant_ids),
            "total_matches": self.fairness.total_matches,
            "match_diff": self.fairness.match_diff,
            "rest_diff": self.rest.rest_diff if self.rest.rest_diff is not None else "-",
            "bye": self.fairness.bye_count,
            "player_load_diff": self.fairness.player_load_diff,
            "conflicts": len(self.conflicts),
        }


def _validate_scheduled(
    tournament: Tournament, scheduled: list[ScheduledMatch]
) -> list[str]:
    """Validasi jadwal terhadap arena + jendela waktu lomba."""
    errors: list[str] = []
    start, end = _to_min(tournament.start_time), _to_min(tournament.end_time)
    for s in scheduled:
        if s.arena < 1 or s.arena > tournament.arena_count:
            errors.append(
                f"{s.match.id}: arena {s.arena} di luar 1-{tournament.arena_count}."
            )
        if not (start <= s.start_min and s.start_min + tournament.duration_min <= end):
            errors.append(
                f"{s.match.id}: jam {s.scheduled_time} di luar jendela "
                f"({tournament.start_time}-{tournament.end_time})."
            )
    return errors


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _rebind(
    scheme: Scheme, scheduled: list[ScheduledMatch]
) -> tuple[list[ScheduledMatch], list[str]]:
    """Ikat ulang jadwal ke objek Match skema via match ID."""
    by_id = {m.id: m for m in scheme.matches}
    sched_ids = [s.match.id for s in scheduled]
    if set(sched_ids) != set(by_id):
        fresh, errors = schedule_matches(scheme.tournament, scheme.matches)
        return fresh, [
            "Struktur match berubah: jadwal dibuat ulang penuh.",
            *errors,
        ]
    return [replace(s, match=by_id[s.match.id]) for s in scheduled], []


def analyze_existing(
    scheme: Scheme,
    scheduled: list[ScheduledMatch] | None = None,
    scheduler: str = "greedy",
) -> SchemeReport:
    """Analisis ulang skema yang sudah ada (hasil edit manual).

    scheduled yang diteruskan di-rebind + divalidasi; bila None,
    dijadwalkan dengan scheduler pilihan ("greedy" | "advanced")."""
    t = scheme.tournament
    if scheduled is None:
        scheduled, errors = _run_scheduler(scheduler, t, scheme.matches)
    else:
        scheduled, errors = _rebind(scheme, scheduled)
        errors += _validate_scheduled(t, scheduled)
    fairness = analyze_scheme(t, scheme.participant_ids, scheme.matches,
                              scheme.bye_details)
    rest = analyze_rest(t, scheduled)
    conflicts = detect_internal_conflict(scheduled, t.duration_min)
    return SchemeReport(
        scheme=scheme, scheduled=scheduled, sched_errors=errors,
        fairness=fairness, rest=rest, conflicts=conflicts,
    )


def build_report(
    tournament: Tournament,
    participant_ids: list[str],
    num_groups: int | None = None,
    scheduler: str = "greedy",
) -> SchemeReport:
    """Generate skema + jadwal + analisis dalam satu panggilan."""
    scheme = generate_scheme(tournament, participant_ids, num_groups)
    return analyze_existing(scheme, None, scheduler)
