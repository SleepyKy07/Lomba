"""Scheduler single lomba — greedy sadar bentrok + advanced sadar-istirahat.

- Urut match: grup/round-robin dulu, lalu knockout P/R1 -> ... -> SF -> F.
- Ronde diproses berurutan (ronde berikut tak mulai sebelum ronde sebelumnya).
- Greedy: padatkan ke batch paling awal tanpa 1 peserta 2x di jam sama.
- Advanced: pilih batch berbiaya minimum (pelanggaran rest dihukum berat).
"""
from __future__ import annotations

from .models import Match, ScheduledMatch, Tournament, is_placeholder, minutes_to_hhmm, round_sort_key


def _sched_key(m: Match) -> tuple[int, str]:
    # Penjadwalan: seluruh fase grup/round-robin satu pool (boleh paralel),
    # knockout tetap per ronde (urutan menang -> main lagi terjaga).
    if m.stage == "group":
        return (0, "GROUP")
    return round_sort_key(m.round, m.stage)


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _to_hhmm(total: int) -> str:
    return minutes_to_hhmm(total)


def _players_of(m: Match) -> set[str]:
    return {
        p
        for p in (m.participant_a, m.participant_b)
        if p is not None and not is_placeholder(p)
    }


def schedule_matches(
    tournament: Tournament, matches: list[Match]
) -> tuple[list[ScheduledMatch], list[str]]:
    ordered = sorted(matches, key=lambda m: round_sort_key(m.round, m.stage))
    start = _to_min(tournament.start_time)
    end = _to_min(tournament.end_time)
    # Kelompokkan per pool agar urutan ronde terjaga.
    pools: list[list[Match]] = []
    for m in ordered:
        if not pools or _sched_key(m) != _sched_key(pools[-1][0]):
            pools.append([m])
        else:
            pools[-1].append(m)
    scheduled: list[ScheduledMatch] = []
    batch_occupants: list[set[str]] = []  # peserta per batch
    batch_counts: list[int] = []
    for pool in pools:
        # Tiap pool mulai di batch baru (ronde berikut tak overlap waktu
        # dengan ronde sebelumnya).
        b_start = len(batch_occupants)
        for m in pool:
            players = {
                p
                for p in (m.participant_a, m.participant_b)
                if p is not None and not is_placeholder(p)
            }
            b = max(0, b_start)
            while True:
                while b >= len(batch_occupants):
                    batch_occupants.append(set())
                    batch_counts.append(0)
                if (
                    batch_counts[b] < tournament.arena_count
                    and batch_occupants[b].isdisjoint(players)
                ):
                    break
                b += 1
            t = start + b * tournament.duration_min
            if t + tournament.duration_min > end:
                return scheduled, [
                    f"Jadwal melebihi jam_selesai ({tournament.end_time}): "
                    f"match {m.id} tidak muat. Kurangi peserta / tambah arena / tambah waktu."
                ]
            batch_occupants[b] |= players
            batch_counts[b] += 1
            arena = batch_counts[b]  # 1-based dalam batch
            scheduled.append(
                ScheduledMatch(
                    match=m,
                    scheduled_time=_to_hhmm(t),
                    arena=arena,
                    start_min=t,
                )
            )
    return scheduled, []


VIOLATION_COST = 10000


def schedule_advanced(
    tournament: Tournament, matches: list[Match]
) -> tuple[list[ScheduledMatch], list[str]]:
    """Advanced scheduler (Phase 3): heuristik sadar-istirahat.

    Greedy menumpuk ke batch paling awal hingga penuh; scheduler ini
    memilih batch berbiaya minimum: pelanggaran minimum-rest dihukum
    berat, batch lebih larut berharga kecil (makespan). Batch boleh
    dikosongkan (arena menganggur) demi jeda istirahat.
    Urutan ronde tetap dijaga (pool mulai di batch baru).
    """
    ordered = sorted(matches, key=lambda m: round_sort_key(m.round, m.stage))
    start = _to_min(tournament.start_time)
    end = _to_min(tournament.end_time)
    max_batch = (end - start - tournament.duration_min) // tournament.duration_min
    pools: list[list[Match]] = []
    for m in ordered:
        if not pools or _sched_key(m) != _sched_key(pools[-1][0]):
            pools.append([m])
        else:
            pools[-1].append(m)
    scheduled: list[ScheduledMatch] = []
    occ: list[set[str]] = []  # peserta per batch (indeks = batch)
    cnt: list[int] = []
    placed: dict[str, list[int]] = {}  # peserta -> batch-batchnya

    def ensure(n: int) -> None:
        while len(occ) <= n:
            occ.append(set())
            cnt.append(0)

    for pool in pools:
        pool_start = len(occ)
        for m in pool:
            players = _players_of(m)
            best_b: int | None = None
            best_cost = 0
            for b in range(pool_start, len(occ) + 2):
                if b > max_batch:
                    break
                o = occ[b] if b < len(occ) else set()
                c = cnt[b] if b < len(occ) else 0
                if c >= tournament.arena_count or not o.isdisjoint(players):
                    continue
                viol = 0
                for p in players:
                    for bo in placed.get(p, []):
                        if abs(b - bo) * tournament.duration_min - tournament.duration_min < tournament.minimum_rest_min:
                            viol += 1
                            break
                cost = VIOLATION_COST * viol + b
                if best_b is None or cost < best_cost:
                    best_b, best_cost = b, cost
            if best_b is None:
                return scheduled, [
                    f"Jadwal (advanced) melebihi jam_selesai ({tournament.end_time}): "
                    f"match {m.id} tidak muat. Tambah arena / tambah waktu / "
                    "turunkan minimum_rest."
                ]
            ensure(best_b)
            t = start + best_b * tournament.duration_min
            occ[best_b] |= players
            cnt[best_b] += 1
            for p in players:
                placed.setdefault(p, []).append(best_b)
            scheduled.append(
                ScheduledMatch(
                    match=m,
                    scheduled_time=_to_hhmm(t),
                    arena=cnt[best_b],
                    start_min=t,
                )
            )
    return scheduled, []
