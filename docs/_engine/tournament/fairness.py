"""Fairness Engine — PRD §8 (tanpa probability/comparison).

Semua angka dijelaskan asalnya (PRD §4.1), bukan skor tunggal.
Deteksi bye generik: berdasarkan ronde knockout pertama yang ada
(bukan hardcode "R1"), sehingga aman untuk label "P"/"F".
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import (
    ROUND_ORDER,
    ByeDetail,
    Match,
    ScheduledMatch,
    Tournament,
    is_placeholder,
    minutes_to_hhmm,
)


@dataclass
class FairnessReport:
    tournament_id: str
    total_matches: int
    bye_recipients: list[str]
    bye_count: int
    bye_details: list[ByeDetail]
    # appearances = slot terjadwal berisi nama pasti (TBD dikecualikan).
    appearances: dict[str, int]
    min_match: int
    max_match: int
    avg_match: float
    match_diff: int
    # Potensi: jaminan main (gugur langsung) vs maksimal (juara).
    guaranteed: dict[str, int]
    max_possible: dict[str, int]
    potential_diff: int
    # Jalur menuju semifinal / final / juara (PRD §8.3).
    wins_to_semifinal: dict[str, int]
    wins_to_final: dict[str, int]
    wins_to_title: dict[str, int]
    path_diff: int
    # Player load = match × team_size (PRD §8.2) dari appearances.
    player_load: dict[str, int]
    player_load_diff: int
    warnings: list[str]


def _appearances(participant_ids: list[str], matches: list[Match]) -> dict[str, int]:
    app = {p: 0 for p in participant_ids}
    for m in matches:
        for slot in (m.participant_a, m.participant_b):
            if is_placeholder(slot):
                continue
            if slot in app:
                app[slot] += 1
            else:
                app[slot] = 1
    return app


def _ko_rounds_in_order(matches: list[Match]) -> list[str]:
    # F3 (juara 3) dikecualikan: bukan jalur juara 1 (PRD path-to-title).
    labels = {
        m.round for m in matches
        if m.stage == "knockout" and m.round != "F3"
    }
    return sorted(labels, key=lambda r: (ROUND_ORDER.get(r, 1), r))


def _first_round_of(slot: str, matches: list[Match], ko_rounds: list[str]) -> str | None:
    for r in ko_rounds:
        for m in matches:
            if m.stage == "knockout" and m.round == r and slot in (
                m.participant_a, m.participant_b,
            ):
                return r
    return None


def _validate_slots(participant_ids: list[str], matches: list[Match]) -> None:
    """Slot nyata harus terdaftar di participant_ids (fail-fast dengan
    pesan jelas, bukan KeyError belakangan di render)."""
    known = set(participant_ids)
    stray = set()
    for m in matches:
        for slot in (m.participant_a, m.participant_b):
            if slot is not None and not is_placeholder(slot) and slot not in known:
                stray.add(slot)
    if stray:
        raise ValueError(
            f"Slot tak terdaftar di peserta: {sorted(stray)}. "
            "Perbaiki participant_ids atau slot match."
        )


def infer_bye_details(
    participant_ids: list[str], matches: list[Match]
) -> list[ByeDetail]:
    """Inferens bye dari struktur bracket: slot yang absen di ronde
    knockout pertama berarti melewatinya (= bye). Berlaku untuk nama
    nyata maupun placeholder 'Juara Grup X'."""
    _validate_slots(participant_ids, matches)
    ko_rounds = _ko_rounds_in_order(matches)
    if not ko_rounds:
        return []
    first = ko_rounds[0]
    played_first = set()
    for m in matches:
        if m.stage == "knockout" and m.round == first:
            if m.participant_a is not None:
                played_first.add(m.participant_a)
            if m.participant_b is not None:
                played_first.add(m.participant_b)
    # Semua slot yang muncul di KO (nyata + placeholder).
    slots: list[str] = list(dict.fromkeys(participant_ids))
    for m in matches:
        for slot in (m.participant_a, m.participant_b):
            if slot is not None and slot not in slots:
                slots.append(slot)
    details: list[ByeDetail] = []
    for slot in slots:
        if slot in played_first:
            continue
        entry = _first_round_of(slot, matches, ko_rounds)
        if entry is None:
            continue  # tak pernah tampil di KO (ex: peserta grup murni di group_knockout)
        idx = ko_rounds.index(entry)
        details.append(
            ByeDetail(
                participant=slot, entry_round=entry,
                skipped_rounds=ko_rounds[:idx],
                wins_needed=len(ko_rounds) - idx,
            )
        )
    return details


def championship_paths(
    participant_ids: list[str],
    matches: list[Match],
    bye_entry: dict[str, str],
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """(wins_to_sf, wins_to_final, wins_to_title) per peserta nyata.

    Peserta grup-murni di skema group_knockout tidak tampil di KO:
    jalurnya = kedalaman KO (dengan syarat lolos grup — lihat notes skema).
    """
    ko_rounds = _ko_rounds_in_order(matches)
    r = len(ko_rounds)
    if r == 0:
        z = {p: 0 for p in participant_ids}
        return dict(z), dict(z), dict(z)
    played_anywhere: set[str] = set()
    for m in matches:
        for slot in (m.participant_a, m.participant_b):
            if slot is not None and not is_placeholder(slot):
                played_anywhere.add(slot)
    sf_idx = r - 2  # semifinal = ronde kedua dari akhir (ada bila r >= 3)
    final_idx = r - 1
    to_sf, to_f, to_t = {}, {}, {}
    for p in participant_ids:
        if p in bye_entry:
            entry_idx = ko_rounds.index(bye_entry[p])
        elif _first_round_of(p, matches, ko_rounds) is not None:
            entry_idx = ko_rounds.index(
                _first_round_of(p, matches, ko_rounds)  # type: ignore[arg-type]
            )
        elif p in played_anywhere:
            entry_idx = 0  # tak tampil di KO (peserta grup di group_knockout)
            # Jalur penuh KO masih harus ditempuh setelah lolos grup.
            to_sf[p] = max(0, sf_idx) if r >= 3 else 0
            to_f[p] = final_idx
            to_t[p] = r
            continue
        else:
            # Tak tampil di slot mana pun (ex: tersingkir walkover): jalur 0.
            to_sf[p] = to_f[p] = to_t[p] = 0
            continue
        to_t[p] = r - entry_idx
        to_f[p] = max(0, final_idx - entry_idx)
        to_sf[p] = max(0, sf_idx - entry_idx) if r >= 3 else 0
    return to_sf, to_f, to_t


def analyze_scheme(
    tournament: Tournament,
    participant_ids: list[str],
    matches: list[Match],
    bye_details: list[ByeDetail] | None = None,
) -> FairnessReport:
    participants = list(dict.fromkeys(participant_ids))
    _validate_slots(participants, matches)
    app = _appearances(participants, matches)
    vals = list(app.values()) or [0]
    ko_rounds = _ko_rounds_in_order(matches)

    # Sumber kebenaran bye: generator bila disediakan, else inferens.
    details = list(bye_details) if bye_details is not None else infer_bye_details(
        participants, matches
    )
    # Placeholder kualifikasi (Juara/Peringkat Grup) bukan bye kelas nyata.
    real_details = [d for d in details if not is_placeholder(d.participant)]
    placeholder_byes = [d for d in details if is_placeholder(d.participant)]
    byes = [d.participant for d in real_details]

    bye_entry = {d.participant: d.entry_round for d in details}
    to_sf, to_f, to_t = championship_paths(participants, matches, bye_entry)
    path_vals = list(to_t.values()) or [0]

    has_ko = bool(ko_rounds)
    has_group = any(m.stage == "group" for m in matches)
    ko_depth = len(ko_rounds)
    played_ko = set()
    for m in matches:
        if m.stage != "knockout":
            continue
        for slot in (m.participant_a, m.participant_b):
            if slot is not None and not is_placeholder(slot):
                played_ko.add(slot)
    guaranteed: dict[str, int] = {}
    max_possible: dict[str, int] = {}
    for p in participants:
        if has_ko and not has_group:
            if p in played_ko:
                guaranteed[p] = 1  # main ≥1x (R1/P atau ronde masuk bye)
                max_possible[p] = to_t[p]
            else:  # ex: tersingkir via walkover tanpa main
                guaranteed[p] = 0
                max_possible[p] = 0
        elif has_ko and has_group:
            guaranteed[p] = app[p]  # fase grup pasti
            max_possible[p] = app[p] + ko_depth  # + full KO bila lolos grup -> juara
        else:
            guaranteed[p] = app[p]  # deterministik (grup / round robin)
            max_possible[p] = app[p]

    load = {p: c * tournament.team_size for p, c in app.items()}
    load_vals = list(load.values()) or [0]

    warnings: list[str] = []
    if min(vals) == 0:
        zero = sorted(p for p, c in app.items() if c == 0)
        warnings.append(
            f"{', '.join(zero)} tidak main sama sekali (0x) - cek walkover."
        )
    if max(vals) - min(vals) >= 2:
        warnings.append(
            f"Match difference {max(vals) - min(vals)} >= 2: ketimpangan jumlah main."
        )
    if real_details:
        wmin = min(to_t[p] for p in byes)
        wmax = max(to_t[p] for p in participants if p not in byes)
        skipped = ", ".join(sorted({r for d in real_details for r in d.skipped_rounds}))
        entries = ", ".join(sorted({d.entry_round for d in real_details}))
        warnings.append(
            f"{len(byes)} bye ({', '.join(byes)}): lewati {skipped}, "
            f"masuk di {entries}; butuh {wmin} menang vs {wmax} bagi non-bye."
        )
    if placeholder_byes:
        warnings.append(
            f"{len(placeholder_byes)} bye antar slot kualifikasi grup "
            f"({', '.join(d.participant for d in placeholder_byes)}): "
            "jumlah grup bukan power-of-2."
        )
    if max(path_vals) - min(path_vals) >= 1:
        warnings.append("Championship path tidak merata akibat bye.")
    if has_ko and has_group:
        warnings.append(
            "Jalur juara peserta grup = lolos grup + "
            f"{ko_depth} menang di knockout."
        )

    g_vals = list(guaranteed.values()) or [0]
    m_vals = list(max_possible.values()) or [0]
    return FairnessReport(
        tournament_id=tournament.id,
        total_matches=len(matches),
        bye_recipients=byes,
        bye_count=len(byes),
        bye_details=details,
        appearances=app,
        min_match=min(vals),
        max_match=max(vals),
        avg_match=round(sum(vals) / len(vals), 2) if vals else 0.0,
        match_diff=max(vals) - min(vals),
        guaranteed=guaranteed,
        max_possible=max_possible,
        potential_diff=max(m_vals) - min(g_vals),
        wins_to_semifinal=to_sf,
        wins_to_final=to_f,
        wins_to_title=to_t,
        path_diff=max(path_vals) - min(path_vals),
        player_load=load,
        player_load_diff=max(load_vals) - min(load_vals),
        warnings=warnings,
    )


@dataclass
class RestReport:
    min_rest: int | None
    max_rest: int | None
    avg_rest: float | None
    rest_diff: int | None
    violations: list[str]
    rest_per_class: dict[str, list[int]]


def analyze_rest(
    tournament: Tournament, scheduled: list[ScheduledMatch]
) -> RestReport:
    """Jeda antar match berurutan per kelas (menit). Hanya dari slot pasti;
    ronde TBD tidak terhitung (dicatat di output)."""
    by_class: dict[str, list[int]] = {}
    for s in scheduled:
        for slot in (s.match.participant_a, s.match.participant_b):
            if is_placeholder(slot):
                continue
            assert slot is not None
            by_class.setdefault(slot, []).append(s.start_min)

    gaps: list[int] = []
    per_class: dict[str, list[int]] = {}
    violations: list[str] = []
    for pid, times in by_class.items():
        times.sort()
        pid_gaps = [b - a - tournament.duration_min for a, b in zip(times, times[1:])]
        per_class[pid] = pid_gaps
        gaps.extend(pid_gaps)
        for gap in pid_gaps:
            if gap < tournament.minimum_rest_min:
                violations.append(
                    f"{pid} istirahat {gap} mnt < minimum {tournament.minimum_rest_min} mnt."
                )

    if not gaps:
        return RestReport(None, None, None, None, violations, per_class)
    return RestReport(
        min_rest=min(gaps),
        max_rest=max(gaps),
        avg_rest=round(sum(gaps) / len(gaps), 1),
        rest_diff=max(gaps) - min(gaps),
        violations=violations,
        rest_per_class=per_class,
    )


def detect_internal_conflict(
    scheduled: list[ScheduledMatch], duration_min: int | None = None
) -> list[str]:
    """Satu kelas di dua pertandingan yang tabrakan waktu.

    Tanpa duration_min: hanya jam mulai yang sama (kompatibel lama).
    Dengan duration_min: semua pasangan interval yang overlap
    (menangkap juga 08:15 vs 08:00+30 mnt).
    """
    by_class: dict[str, list[tuple[int, str]]] = {}
    for s in scheduled:
        for slot in (s.match.participant_a, s.match.participant_b):
            if is_placeholder(slot):
                continue
            assert slot is not None
            by_class.setdefault(slot, []).append((s.start_min, s.match.id))
    out: list[str] = []
    for pid in sorted(by_class):
        ivs = sorted(by_class[pid])
        seen_same: dict[int, list[str]] = {}
        for start, mid in ivs:
            seen_same.setdefault(start, []).append(mid)
        for start in sorted(seen_same):
            if len(seen_same[start]) > 1:
                out.append(f"{pid} bentrok di {seen_same[start]} (jam sama)")
        if duration_min is not None:
            ends = [(s, s + duration_min, m) for s, m in ivs]
            seen_pair: set[tuple[str, str]] = set()
            for i in range(len(ends)):
                for j in range(i + 1, len(ends)):
                    s1, e1, m1 = ends[i]
                    s2, e2, m2 = ends[j]
                    if s1 == s2:
                        continue  # sudah dilaporkan sebagai jam sama
                    if s2 < e1 and s1 < e2:
                        key = (m1, m2) if m1 <= m2 else (m2, m1)
                        if key not in seen_pair:
                            seen_pair.add(key)
                            out.append(
                                f"{pid} overlap: {m1} ({minutes_to_hhmm(s1)}) vs "
                                f"{m2} ({minutes_to_hhmm(s2)})"
                            )
    return out
