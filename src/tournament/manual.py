"""Manual Adjustment (PRD §12): ganti lawan, pindah jadwal/arena,
ganti peserta, walkover (bye). Setiap operasi mengembalikan objek BARU
+ catatan; panggil analyze_existing() untuk analisis ulang otomatis.

Bye dihitung ulang dari struktur bracket pasca-edit (tak pernah basi).
Menghapus bye struktural (peserta bye dipaksa main play-in) =
regenerasi skema, gunakan what-if — agar bracket tetap valid.
Walkover tercatat di notes + appearances; bye_count menghitung bye
struktural bracket.
"""
from __future__ import annotations

from dataclasses import replace

from .fairness import infer_bye_details
from .models import (
    ROUND_ORDER,
    Match,
    ScheduledMatch,
    Scheme,
    Tournament,
    is_placeholder,
)

Slot = str  # "a" | "b"


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _fresh_bye(participant_ids: list[str], matches: list[Match]) -> list:
    """Hitung ulang bye dari struktur bracket pasca-edit agar laporan
    tak basi (bye = siapa yang absen di ronde pembuka, bukan data lama)."""
    return infer_bye_details(participant_ids, matches)


def _find_match(scheme: Scheme, match_id: str) -> Match:
    for m in scheme.matches:
        if m.id == match_id:
            return m
    raise ValueError(f"Match tak dikenal: {match_id}.")


def _check_slot(slot: Slot) -> None:
    if slot not in ("a", "b"):
        raise ValueError("slot harus 'a' atau 'b'.")


def _validate_no_self_match(matches: list[Match]) -> None:
    for m in matches:
        if (
            m.participant_a is not None
            and m.participant_a == m.participant_b
        ):
            raise ValueError(
                f"Match {m.id} tidak valid: satu kelas di kedua sisi."
            )


def _validate_bracket_resolvable(matches: list[Match]) -> None:
    """Setiap slot TBD knockout harus punya pemenang ronde sebelumnya
    (disiplin antrean yang sama dengan probability engine).

    Walkover tak mengonsumsi antrean (lolos langsung); placeholder juara
    grup tak mengonsumsi antrean (datang dari fase grup). F3 dilewati:
    slot 'Kalah ...' diisi dari kalah ronde, bukan antrean pemenang —
    F3 tidak boleh menambah `available` (dulu false-OK untuk F).
    """
    available = 0
    for m in matches:
        if m.stage != "knockout":
            continue
        if m.round == "F3":
            continue
        if m.status == "walkover":
            available += 1
            continue
        need = 0
        for slot in (m.participant_a, m.participant_b):
            if slot is None:
                need += 1
        if need > available:
            raise ValueError(
                f"Bracket tak valid: {m.id} butuh {need} pemenang ronde "
                f"sebelumnya, tersedia {available}. "
                "Jangan pindah slot TBD ke ronde yang lebih awal."
            )
        available = available - need + 1


def swap_slots(
    scheme: Scheme,
    match_id_a: str, slot_a: Slot,
    match_id_b: str, slot_b: Slot,
) -> Scheme:
    """Tukar dua slot peserta antar match (ganti lawan)."""
    _check_slot(slot_a)
    _check_slot(slot_b)
    ma = _find_match(scheme, match_id_a)
    mb = _find_match(scheme, match_id_b)
    va = ma.participant_a if slot_a == "a" else ma.participant_b
    vb = mb.participant_a if slot_b == "a" else mb.participant_b
    matches = []
    for m in scheme.matches:
        if m.id == match_id_a:
            m = replace(
                m,
                participant_a=vb if slot_a == "a" else m.participant_a,
                participant_b=vb if slot_a == "b" else m.participant_b,
            )
        elif m.id == match_id_b:
            m = replace(
                m,
                participant_a=va if slot_b == "a" else m.participant_a,
                participant_b=va if slot_b == "b" else m.participant_b,
            )
        matches.append(m)
    _validate_no_self_match(matches)
    _validate_bracket_resolvable(matches)
    return Scheme(
        tournament=scheme.tournament,
        participant_ids=list(scheme.participant_ids),
        matches=matches,
        notes=[*scheme.notes,
               f"Manual: tukar {match_id_a}({slot_a}) <-> {match_id_b}({slot_b})."],
        bye_details=_fresh_bye(list(scheme.participant_ids), matches),
    )


def move_match(
    scheduled: list[ScheduledMatch],
    match_id: str,
    new_time: str,
    new_arena: int,
    tournament: Tournament | None = None,
) -> list[ScheduledMatch]:
    """Pindah jam mulai ("HH:MM") dan arena suatu match terjadwal.

    Bila tournament diberikan, tujuan divalidasi terhadap jumlah arena
    dan jendela waktu lomba."""
    try:
        h, m = new_time.split(":")
        start_min = int(h) * 60 + int(m)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"new_time harus HH:MM, dapat: {new_time!r}.") from exc
    if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
        raise ValueError(f"new_time tidak valid: {new_time!r}.")
    if new_arena < 1:
        raise ValueError("new_arena minimal 1.")
    if tournament is not None:
        if new_arena > tournament.arena_count:
            raise ValueError(
                f"new_arena {new_arena} melebihi jumlah arena "
                f"({tournament.arena_count})."
            )
        start, end = _to_min(tournament.start_time), _to_min(tournament.end_time)
        if not (start <= start_min and start_min + tournament.duration_min <= end):
            raise ValueError(
                f"{new_time} di luar jendela lomba "
                f"({tournament.start_time}-{tournament.end_time})."
            )
    out = []
    found = False
    for s in scheduled:
        if s.match.id == match_id:
            out.append(replace(s, scheduled_time=new_time,
                               arena=new_arena, start_min=start_min))
            found = True
        else:
            out.append(s)
    if not found:
        raise ValueError(f"Match tak dikenal: {match_id}.")
    return out


def replace_participant(
    scheme: Scheme, old_id: str, new_id: str
) -> Scheme:
    """Ganti peserta di daftar + seluruh slot match."""
    if not isinstance(old_id, str) or not old_id:
        raise ValueError(f"Peserta lama tidak valid: {old_id!r}.")
    if not isinstance(new_id, str) or not new_id:
        raise ValueError(f"Peserta baru tidak valid: {new_id!r}.")
    if old_id not in scheme.participant_ids:
        raise ValueError(f"Peserta {old_id} tidak ada di lomba.")
    if new_id in scheme.participant_ids:
        raise ValueError(f"Peserta {new_id} sudah ada di lomba.")
    matches = []
    for m in scheme.matches:
        m = replace(
            m,
            participant_a=new_id if m.participant_a == old_id else m.participant_a,
            participant_b=new_id if m.participant_b == old_id else m.participant_b,
        )
        matches.append(m)
    _validate_no_self_match(matches)
    new_pids = [new_id if p == old_id else p for p in scheme.participant_ids]
    bye_details = [
        replace(b, participant=new_id) if b.participant == old_id else b
        for b in _fresh_bye(new_pids, matches)
    ]
    return Scheme(
        tournament=scheme.tournament,
        participant_ids=new_pids,
        matches=matches,
        notes=[*scheme.notes, f"Manual: {old_id} diganti {new_id}."],
        bye_details=bye_details,
    )


def _round_before_f3_source(matches: list[Match]) -> str | None:
    """Ronde perebutan F3 = ronde knockout sebelum F (2 match)."""
    labels = sorted(
        {m.round for m in matches
         if m.stage == "knockout" and m.round != "F3"},
        key=lambda r: (ROUND_ORDER.get(r, 1), r),
    )
    if "F" not in labels:
        return None
    idx = labels.index("F")
    return labels[idx - 1] if idx >= 1 else None


def set_walkover(scheme: Scheme, match_id: str, winner_id: str) -> Scheme:
    """Walkover (memberi bye): pemenang lolos tanpa bertanding.
    Slot lawan dikosongkan (None). Bila ronde ini perebutan juara 3 (F3),
    kalah DICATAT ke slot 'Kalah {ronde}-N' agar bracket F3 tetap terisi
    (tanpa ini, kalah WO hilang dan F3 tak bisa diisi otomatis)."""
    m = _find_match(scheme, match_id)
    if winner_id not in (m.participant_a, m.participant_b):
        raise ValueError(f"{winner_id} bukan peserta match {match_id}.")
    if is_placeholder(m.participant_a) or is_placeholder(m.participant_b):
        raise ValueError(f"Match {match_id} mengandung slot TBD.")
    loser = m.participant_b if winner_id == m.participant_a else m.participant_a
    matches = []
    for x in scheme.matches:
        if x.id != match_id:
            matches.append(x)
            continue
        if m.round == "F3":
            # F3 WO: kedua slot diisi (pemenang di a, kalah di b) agar
            # Peringkat 4 tetap tercatat di klasemen (slot kosong = identitas
            # kalah hilang). Konvensi: pemenang WO F3 selalu di participant_a.
            matches.append(replace(
                x, participant_a=winner_id, participant_b=loser,
                status="walkover",
            ))
        else:
            matches.append(replace(
                x,
                participant_a=x.participant_a if x.participant_a == winner_id else None,
                participant_b=x.participant_b if x.participant_b == winner_id else None,
                status="walkover",  # dibaca probability engine: lolos tanpa undian
            ))
    f3_note = ""
    has_f3 = any(x.round == "F3" for x in matches)
    if has_f3 and m.stage == "knockout":
        if m.round == "F3":
            f3_note = f" F3: {loser} tercatat sebagai peringkat 4 (WO)."
        else:
            pre = _round_before_f3_source(matches)
            if pre == m.round:
                same = [x for x in matches if x.round == m.round]
                seq = next((i for i, x in enumerate(same) if x.id == match_id), None)
                if seq is not None and len(same) == 2 and loser is not None:
                    key = f"Kalah {m.round}-{seq + 1}"
                    filled = []
                    for x in matches:
                        if x.round != "F3":
                            filled.append(x)
                            continue
                        if x.participant_a == key:
                            filled.append(replace(x, participant_a=loser))
                        elif x.participant_b == key:
                            filled.append(replace(x, participant_b=loser))
                        else:
                            filled.append(x)
                    matches = filled
                    f3_note = f" F3: {loser} tercatat mengisi {key}."
                else:
                    f3_note = (
                        f" F3 tidak diisi dari WO ini (ronde {m.round} bukan "
                        f"sumber F3 / tak ada 2 match)."
                    )
            else:
                f3_note = (
                    f" Limitasi: WO ronde {m.round} TIDAK mengisi F3 "
                    f"(sumber = kalah {pre}). Kalah WO non-sumber hilang "
                    f"dari bracket - F3 menunggu kalah {pre} dari skor biasa."
                )
    return Scheme(
        tournament=scheme.tournament,
        participant_ids=list(scheme.participant_ids),
        matches=matches,
        notes=[*scheme.notes,
               f"Manual: walkover {match_id}, {winner_id} lolos "
               f"(tanpa vs {loser}).{f3_note}"],
        bye_details=_fresh_bye(list(scheme.participant_ids), matches),
    )
