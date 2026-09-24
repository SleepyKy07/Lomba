"""Group stage generator (group + group+knockout dasar)."""
from __future__ import annotations

from .generator_knockout import generate_knockout
from .models import ByeDetail, Match, Scheme, Tournament


def auto_group_count(n: int) -> int:
    """Target ukuran grup 3-4 (PRD contoh 6 peserta -> 2 grup isi 3)."""
    if n <= 4:
        return 1
    if n <= 6:
        return 2
    # Umum: ~4 peserta per grup.
    g = max(2, round(n / 4))
    # Jangan sampai ada grup isi < 3 kecuali terpaksa.
    while g > 1 and n // g < 3:
        g -= 1
    return g


def split_groups(participant_ids: list[str], num_groups: int) -> dict[str, list[str]]:
    """Bagi interleave (1,3,5.. / 2,4,6..) agar tiap grup campuran urutan seed.

    Bukan pengacakan kekuatan — urutan input dianggap urutan seed.
    """
    groups: dict[str, list[str]] = {}
    for i, pid in enumerate(participant_ids):
        g = chr(ord("A") + (i % num_groups))
        groups.setdefault(g, []).append(pid)
    return dict(sorted(groups.items()))


def round_robin_pairs(members: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for i in range(len(members)):
        for j in range(i + 1, len(members)):
            pairs.append((members[i], members[j]))
    return pairs


def generate_group(
    tournament: Tournament,
    participant_ids: list[str],
    num_groups: int | None = None,
) -> Scheme:
    if not participant_ids:
        raise ValueError("Group stage butuh minimal 2 peserta (dapat 0).")
    participants = list(dict.fromkeys(participant_ids))
    notes: list[str] = []
    if len(participants) != len(participant_ids):
        notes.append("ID duplikat dihapus; grup memakai daftar unik.")
    n = len(participants)
    if n < 2:
        raise ValueError("Group stage butuh minimal 2 peserta.")
    # num_groups=0 harus error, bukan jatuh ke auto (falsy `or`).
    g = auto_group_count(n) if num_groups is None else num_groups
    if g < 1 or g > n:
        raise ValueError("num_groups tidak valid.")

    groups = split_groups(participants, g)
    matches: list[Match] = []
    for gname, members in groups.items():
        seq = 0
        for a, b in round_robin_pairs(members):
            seq += 1
            matches.append(
                Match(
                    id=f"{tournament.id}-G{gname}{seq:02d}",
                    tournament_id=tournament.id,
                    round=f"G{gname}",
                    stage="group",
                    participant_a=a,
                    participant_b=b,
                    group=gname,
                )
            )
    notes.extend(
        f"Grup {gname}: {', '.join(m)} (masing-masing main {len(m) - 1}x)"
        for gname, m in groups.items()
    )
    if tournament.winner_count > 1:
        notes.append(
            f"winner_count={tournament.winner_count}: peringkat grup "
            "= klasemen (poin, selisih gol) dari hasil - lihat Klasemen."
        )
    return Scheme(
        tournament=tournament, participant_ids=participants,
        matches=matches, notes=notes, bye_details=[],
    )


def generate_group_knockout(
    tournament: Tournament,
    participant_ids: list[str],
    num_groups: int | None = None,
) -> Scheme:
    """Fase grup (round robin) + lolos tiap grup lanjut knockout.

    Kualifikasi = tournament.qualify_per_group per grup
    (1 = juara grup, 2 = juara + peringkat 2, dst). Slot placeholder:
    'Juara Grup X' / 'Peringkat k Grup X' diisi dari klasemen grup
    (results.advance_scheme / probability) setelah grup lengkap.
    Jumlah grup bukan power-of-2: bracket knockout memberi bye (transparan).
    """
    q = tournament.qualify_per_group
    if q < 1:
        raise ValueError("qualify_per_group minimal 1.")
    group_scheme = generate_group(tournament, participant_ids, num_groups)
    # Hitung grup dari daftar UNIK hasil generate_group — bukan
    # len(participant_ids) mentah (duplikat bisa mengubah auto_group_count).
    g_n = (auto_group_count(len(group_scheme.participant_ids))
           if num_groups is None else num_groups)
    groups = split_groups(group_scheme.participant_ids, g_n)
    max_size = max((len(m) for m in groups.values()), default=0)
    if q > max_size:
        raise ValueError(
            f"qualify_per_group={q} melebihi ukuran grup terbesar "
            f"({max_size}); peringkat {q} tidak akan pernah ada.")
    qualifiers: list[str] = []
    for g in sorted(groups):
        for rank in range(1, q + 1):
            if rank == 1:
                qualifiers.append(f"Juara Grup {g}")
            else:
                qualifiers.append(f"Peringkat {rank} Grup {g}")
    kual_note = (
        f"Kualifikasi: {q} per grup (peringkat 1"
        + (f"-{q} dari klasemen" if q > 1 else " = juara grup")
        + ")."
    )
    if len(qualifiers) < 2:
        # Tak cukup slot knockout (mis. 1 grup x q=1): juara = klasemen.
        return Scheme(
            tournament=tournament,
            participant_ids=group_scheme.participant_ids,
            matches=list(group_scheme.matches),
            notes=[*group_scheme.notes, kual_note,
                   "Tak cukup lolos utk knockout: peringkat akhir = klasemen."],
            bye_details=[],
        )
    ko_tournament = Tournament(
        id=tournament.id, name=tournament.name, format="knockout",
        team_size=tournament.team_size, winner_count=tournament.winner_count,
        duration_min=tournament.duration_min,
        minimum_rest_min=tournament.minimum_rest_min,
        arena_count=tournament.arena_count, date=tournament.date,
        start_time=tournament.start_time, end_time=tournament.end_time,
        qualify_per_group=tournament.qualify_per_group,
    )
    ko = generate_knockout(ko_tournament, qualifiers)
    # ID knockout dilabeli K dengan penomoran sendiri (tanpa string-replace).
    ko_matches = []
    for i, m in enumerate(ko.matches, start=1):
        ko_matches.append(
            Match(
                id=f"{tournament.id}-K{i:02d}",
                tournament_id=m.tournament_id, round=m.round, stage="knockout",
                participant_a=m.participant_a, participant_b=m.participant_b,
                status=m.status,
            )
        )
    ko_byes: list[ByeDetail] = list(ko.bye_details)
    return Scheme(
        tournament=tournament,
        participant_ids=group_scheme.participant_ids,
        matches=[*group_scheme.matches, *ko_matches],
        notes=[*group_scheme.notes, kual_note, *ko.notes],
        bye_details=ko_byes,
    )
