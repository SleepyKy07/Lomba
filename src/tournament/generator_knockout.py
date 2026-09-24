"""Knockout generator.

Aturan (transparan, PRD §8.3-8.4):
- next_pow2(n), byes = next_pow2 - n
- Bye ke seed awal sesuai urutan input, lalu DISEBAR merata di bagan
  (bye tidak saling bertemu selama masih bisa dihindari).
- Ronde pembuka ("R1", atau "P" untuk format preliminary) hanya untuk
  peserta non-bye. Total match menuju 1 juara = n - 1.
- Slot pemenang yang belum diketahui memakai None (TBD).
"""
from __future__ import annotations

import math

from .models import ByeDetail, Match, Scheme, Tournament


def next_pow2(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def _interleave(bye: list[str | None], winners: list[str | None]) -> list[str | None]:
    """Sebar bye merata: selingi bye dan pemenang play-in agar dua
    penerima bye tidak satu match selama masih bisa dihindari."""
    out: list[str | None] = []
    bi = ti = 0
    take_bye = True
    while bi < len(bye) or ti < len(winners):
        if (take_bye and bi < len(bye)) or ti >= len(winners):
            out.append(bye[bi])
            bi += 1
        else:
            out.append(winners[ti])
            ti += 1
        take_bye = not take_bye
    return out


def generate_knockout(
    tournament: Tournament,
    participant_ids: list[str],
    first_round_label: str = "R1",
) -> Scheme:
    if not participant_ids:
        raise ValueError("Knockout butuh minimal 2 peserta (dapat 0).")
    participants = list(dict.fromkeys(participant_ids))  # dedup, jaga urutan
    notes: list[str] = []
    if len(participants) != len(participant_ids):
        notes.append("ID duplikat dihapus; bracket memakai daftar unik.")
    n = len(participants)
    if n < 2:
        raise ValueError("Knockout butuh minimal 2 peserta.")
    if n == 2:
        # Satu final langsung, tanpa play-in.
        m = Match(
            id=f"{tournament.id}-M01",
            tournament_id=tournament.id,
            round="F",
            stage="knockout",
            participant_a=participants[0],
            participant_b=participants[1],
        )
        scheme_notes = [*notes]
        if tournament.winner_count > 1:
            scheme_notes.append(
                "winner_count>1: perebutan juara 3 tidak mungkin "
                "(hanya 2 peserta; bracket di atas untuk juara 1)."
            )
        return Scheme(
            tournament=tournament, participant_ids=participants,
            matches=[m], notes=scheme_notes, bye_details=[],
        )

    size = next_pow2(n)
    bye_count = size - n

    bye_recipients = participants[:bye_count] if bye_count else []
    playin = participants[bye_count:]

    matches: list[Match] = []
    mid = 0

    def new_id() -> str:
        nonlocal mid
        mid += 1
        return f"{tournament.id}-M{mid:02d}"

    # Ronde pembuka antar non-bye.
    r1_winner_slots: list[str | None] = []
    for i in range(0, len(playin), 2):
        a = playin[i]
        b = playin[i + 1] if i + 1 < len(playin) else None
        if b is None:  # mustahil via matematika next_pow2, dijaga saja
            r1_winner_slots.append(a)
            notes.append(f"{a} lolos tanpa lawan di {first_round_label}.")
            continue
        matches.append(
            Match(
                id=new_id(), tournament_id=tournament.id, round=first_round_label,
                stage="knockout", participant_a=a, participant_b=b,
            )
        )
        r1_winner_slots.append(None)

    advancing: list[str | None] = _interleave(list(bye_recipients), r1_winner_slots)
    round_no = 2
    total_rounds = int(math.log2(size))
    subsequent_labels: list[str] = []
    while len(advancing) > 1:
        if len(advancing) == 2:
            label = "F"
        elif len(advancing) == 4 and total_rounds >= 2:
            label = "SF"
        else:
            label = f"R{round_no}"
        subsequent_labels.append(label)
        nxt: list[str | None] = []
        for i in range(0, len(advancing), 2):
            a = advancing[i]
            b = advancing[i + 1]
            if b is None and a is not None and len(advancing) % 2 == 1:
                nxt.append(a)
                continue
            matches.append(
                Match(
                    id=new_id(), tournament_id=tournament.id, round=label,
                    stage="knockout", participant_a=a, participant_b=b,
                )
            )
            nxt.append(None)
        advancing = nxt
        round_no += 1

    ko_rounds = [first_round_label, *subsequent_labels]
    entry_round = subsequent_labels[0] if subsequent_labels else first_round_label
    wins_needed = len(ko_rounds) - 1
    bye_details = [
        ByeDetail(
            participant=p, entry_round=entry_round,
            skipped_rounds=[first_round_label], wins_needed=wins_needed,
        )
        for p in bye_recipients
    ]
    if bye_count:
        full_path = wins_needed + 1
        notes.append(
            f"{bye_count} bye ({', '.join(bye_recipients)}): lewati "
            f"{first_round_label}, masuk di {entry_round}; butuh {wins_needed} "
            f"menang vs {full_path} bagi non-bye."
        )
    if tournament.winner_count > 1:
        _add_third_place(matches, ko_rounds, new_id, notes)
    return Scheme(
        tournament=tournament, participant_ids=participants,
        matches=matches, notes=notes, bye_details=bye_details,
    )


def _add_third_place(
    matches: list[Match], ko_rounds: list[str], new_id, notes: list[str]
) -> None:
    """Perebutan juara 3 (F3): kalah ronde sebelum final vs kalah finalis.

    Slot memakai placeholder 'Kalah {ronde}-1/2' (is_placeholder=True);
    diisi oleh results.advance_scheme / probability engine dari kalah SF/R1.
    Disisipkan SEBELUM F agar urutan tampilan/jalur tahu-kalah mendahului
    final. Jalur juara 1 tidak melewati F3 (fairness/prob mengecualikan F3).
    """
    if "F" not in ko_rounds:
        return
    f_idx = ko_rounds.index("F")
    if f_idx < 1:
        # n=2: hanya final — tak ada kalah semifinal/ronde awal.
        notes.append(
            "winner_count>1: perebutan juara 3 tidak mungkin (hanya 2 peserta)."
        )
        return
    pre = ko_rounds[f_idx - 1]
    pre_ms = [m for m in matches if m.round == pre]
    if len(pre_ms) != 2:
        notes.append(
            f"winner_count>1: perebutan juara 3 dilewati "
            f"(ronde {pre} punya {len(pre_ms)} match, butuh 2)."
        )
        return
    try:
        idx_f = next(i for i, m in enumerate(matches) if m.round == "F")
    except StopIteration:
        return
    f3 = Match(
        id=new_id(), tournament_id=matches[0].tournament_id,
        round="F3", stage="knockout",
        participant_a=f"Kalah {pre}-1",
        participant_b=f"Kalah {pre}-2",
    )
    matches.insert(idx_f, f3)
    notes.append(
        f"Perebutan juara 3 (F3): kalah {pre}-1 vs kalah {pre}-2 "
        "(slot terisi setelah ronde itu selesai)."
    )


def generate_preliminary_knockout(
    tournament: Tournament, participant_ids: list[str]
) -> Scheme:
    """Knockout dengan ronde pembuka eksplisit 'P' (preliminary, F-04).

    Sama dengan knockout standar, hanya label ronde 1 = 'P' agar
    transparan di bracket/jadwal/analisis."""
    scheme = generate_knockout(tournament, participant_ids, first_round_label="P")
    scheme.notes.append("Ronde P = preliminary (play-in menuju bracket utama).")
    return scheme
