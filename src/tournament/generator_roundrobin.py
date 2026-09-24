"""Round robin penuh — satu grup besar, semua bertemu semua (PRD §16 Alternatif C).

Total match = n*(n-1)/2. Peserta ganjil: tiap ronde satu peserta jeda
(dicatat sebagai bye jeda, bukan bye bracket).
"""
from __future__ import annotations

from .models import Match, Scheme, Tournament


def generate_round_robin(
    tournament: Tournament, participant_ids: list[str]
) -> Scheme:
    if not participant_ids:
        raise ValueError("Round robin butuh minimal 2 peserta (dapat 0).")
    participants = list(dict.fromkeys(participant_ids))
    notes: list[str] = []
    if len(participants) != len(participant_ids):
        notes.append("ID duplikat dihapus; jadwal memakai daftar unik.")
    n = len(participants)
    if n < 2:
        raise ValueError("Round robin butuh minimal 2 peserta.")

    # Circle method: tiap ronde dipasangkan, peserta ganjil dapat 1 bye jeda.
    circle = list(participants)
    has_dummy = n % 2 == 1
    if has_dummy:
        circle.append("__BYE__")
    rounds = len(circle) - 1
    matches: list[Match] = []
    mid = 0
    bye_jeda: dict[str, int] = {}
    for r in range(1, rounds + 1):
        for i in range(len(circle) // 2):
            a = circle[i]
            b = circle[-(i + 1)]
            if "__BYE__" in (a, b):
                real = b if a == "__BYE__" else a
                bye_jeda[real] = bye_jeda.get(real, 0) + 1
                continue
            mid += 1
            matches.append(
                Match(
                    id=f"{tournament.id}-RR{mid:02d}",
                    tournament_id=tournament.id,
                    round=f"R{r}",
                    stage="group",
                    participant_a=a,
                    participant_b=b,
                )
            )
        # rotasi circle (pertama tetap)
        circle = [circle[0], circle[-1], *circle[1:-1]]
    notes.append(
        f"Round robin: tiap peserta main {n - 1}x, total {len(matches)} match."
    )
    if bye_jeda:
        notes.append(
            f"Peserta ganjil: tiap peserta jeda 1 ronde "
            f"({', '.join(sorted(bye_jeda))})."
        )
    if tournament.winner_count > 1:
        notes.append(
            f"winner_count={tournament.winner_count}: juara = urutan "
            "klasemen round robin (poin, selisih gol)."
        )
    return Scheme(
        tournament=tournament, participant_ids=participants,
        matches=matches, notes=notes, bye_details=[],
    )
