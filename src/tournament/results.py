"""Hasil pertandingan + klasemen (PRD §15 Result, §5 menyusun klasemen).

- record_result: skor per match (seri hanya di fase grup/round robin;
  knockout wajib pemenang — seri = salah input, pakai walkover/skor ulang).
- advance_scheme: tampilan bracket live — isi slot TBD dari antrean pemenang
  (disiplin sama dengan probability engine) + 'Juara Grup X' dari klasemen
  grup yang sudah lengkap. Struktur skema asli TIDAK dimutasi (fairness
  tetap mengukur desain skema, bukan hasil).
- build_standings: klasemen per grup / round robin / jalur knockout.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from .models import (
    LOSER_PREFIX,
    Match,
    Result,
    Scheme,
    is_placeholder,
    parse_group_qualifier,
    round_sort_key,
)

Results = dict[str, Result]  # match_id -> Result


@dataclass(frozen=True)
class StandRow:
    participant: str
    main: int = 0
    menang: int = 0
    seri: int = 0
    kalah: int = 0
    gf: int = 0
    ga: int = 0
    poin: int = 0
    catatan: str = ""


def _find_match(scheme: Scheme, match_id: str) -> Match:
    for m in scheme.matches:
        if m.id == match_id:
            return m
    raise ValueError(f"Match tak dikenal: {match_id}.")


def record_result(
    scheme: Scheme, match_id: str, score_a: int, score_b: int,
    results: Results | None = None,
) -> Result:
    """Catat/ubah skor satu match. Mengembalikan Result siap simpan.

    `results` (hasil sebelumnya) dipakai agar slot ronde lanjutan yang
    belum terisi di skema asli dicek lewat advance_scheme() — pemenang
    R1 baru bisa mencatat skor R2.
    """
    target = advance_scheme(scheme, results) if results is not None else scheme
    m = _find_match(target, match_id)
    if m.status == "walkover":
        raise ValueError(
            f"{match_id} walkover - tidak menerima skor; hapus WO bila keliru.")
    if is_placeholder(m.participant_a) or is_placeholder(m.participant_b):
        raise ValueError(
            f"{match_id} belum siap (ada slot TBD) - mainkan ronde sebelumnya dulu.")
    try:
        sa, sb = int(score_a), int(score_b)
    except (TypeError, ValueError) as exc:
        raise ValueError("Skor harus bilangan bulat.") from exc
    if sa < 0 or sb < 0:
        raise ValueError("Skor tidak boleh negatif.")
    if sa == sb and m.stage == "knockout":
        raise ValueError(
            f"{match_id} knockout: skor seri tidak boleh. "
            "Koreksi skor atau gunakan walkover.")
    winner: str | None = None
    if sa > sb:
        winner = m.participant_a
    elif sb > sa:
        winner = m.participant_b
    return Result(match_id=match_id, winner=winner, score_a=sa, score_b=sb)


def clear_result(results: Results, match_id: str) -> Results:
    if match_id not in results:
        raise ValueError(f"Belum ada hasil untuk {match_id}.")
    out = dict(results)
    out.pop(match_id)
    return out


def _group_complete(scheme: Scheme, group: str, results: Results) -> bool:
    for m in scheme.matches:
        if m.stage == "group" and m.group == group and m.id not in results:
            return False
    return True


def _stand_rows(
    members: list[str], matches: list[Match], results: Results
) -> list[StandRow]:
    acc: dict[str, StandRow] = {p: StandRow(participant=p) for p in members}
    for m in matches:
        res = results.get(m.id)
        if m.status == "walkover":
            real = [s for s in (m.participant_a, m.participant_b)
                    if s is not None and not is_placeholder(s)]
            if len(real) == 1 and real[0] in acc:
                r = acc[real[0]]
                acc[real[0]] = replace(
                    r, main=r.main + 1, menang=r.menang + 1,
                    poin=r.poin + 3, catatan="WO")
            continue
        if res is None:
            continue
        for pid, gf, ga in (
            (m.participant_a, res.score_a, res.score_b),
            (m.participant_b, res.score_b, res.score_a),
        ):
            if pid is None or pid not in acc:
                continue
            r = acc[pid]
            menang, seri, kalah, poin = r.menang, r.seri, r.kalah, r.poin
            if res.winner is None:
                seri, poin = r.seri + 1, r.poin + 1
            elif res.winner == pid:
                menang, poin = r.menang + 1, r.poin + 3
            else:
                kalah = r.kalah + 1
            acc[pid] = replace(
                r, main=r.main + 1, menang=menang, seri=seri, kalah=kalah,
                gf=r.gf + gf, ga=r.ga + ga, poin=poin)
    rows = list(acc.values())
    rows.sort(key=lambda r: (-r.poin, -(r.gf - r.ga), -r.gf, r.participant))
    return rows


def _ko_status(scheme: Scheme, results: Results) -> dict[str, str]:
    """Status jalur knockout per peserta berdasar hasil yang sudah ada."""
    status: dict[str, str] = {p: "Belum main" for p in scheme.participant_ids}
    for b in scheme.bye_details:
        if b.participant in status and status[b.participant] == "Belum main":
            status[b.participant] = f"Bye masuk {b.entry_round}"
    ko = [m for m in scheme.matches
          if m.stage == "knockout" and m.round != "F3"]
    ko.sort(key=lambda m: round_sort_key(m.round, m.stage))
    final = ko[-1] if ko else None
    for m in ko:
        if m.status == "walkover":
            real = [s for s in (m.participant_a, m.participant_b)
                    if s is not None and not is_placeholder(s)]
            if len(real) == 1:
                status[real[0]] = f"Lolos WO di {m.round}"
            continue
        res = results.get(m.id)
        if res is None:
            for s in (m.participant_a, m.participant_b):
                if (s is not None and not is_placeholder(s)
                        and status.get(s) == "Belum main"):
                    status[s] = f"Di {m.round}"
            continue
        if res.winner is None:
            continue
        loser = (m.participant_b if res.winner == m.participant_a
                 else m.participant_a)
        if final is not None and m.id == final.id:
            status[res.winner] = "Juara"
            if loser is not None:
                status[loser] = "Juara 2"
        else:
            if loser is not None:
                status[loser] = f"Gugur di {m.round}"
            status[res.winner] = f"Lolos dari {m.round}"
    # Perebutan juara 3 (F3): juara = Juara 3, kalah = peringkat 4.
    for m in scheme.matches:
        if m.round != "F3":
            continue
        if m.status == "walkover":
            real = [s for s in (m.participant_a, m.participant_b)
                    if s is not None and not is_placeholder(s)]
            if len(real) == 2:
                # Konvensi set_walkover F3: pemenang di a, kalah di b.
                if m.participant_a in status:
                    status[m.participant_a] = "Juara 3"
                if (m.participant_b in status
                        and status.get(m.participant_b) != "Juara"):
                    status[m.participant_b] = "Peringkat 4"
            elif len(real) == 1 and real[0] in status:
                status[real[0]] = "Juara 3"
            continue
        res = results.get(m.id)
        if res is None or res.winner is None:
            continue
        loser = (m.participant_b if res.winner == m.participant_a
                 else m.participant_a)
        if res.winner in status:
            status[res.winner] = "Juara 3"
        if loser is not None and loser in status and status[loser] != "Juara":
            status[loser] = "Peringkat 4"
    return status


def _group_members(scheme: Scheme) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for m in scheme.matches:
        if m.stage != "group":
            continue
        for s in (m.participant_a, m.participant_b):
            if s is not None and not is_placeholder(s):
                if s not in groups.setdefault(m.group, []):
                    groups[m.group].append(s)
    # peserta tanpa match grup (mis. bye jeda RR) tetap masuk
    if scheme.tournament.format == "round_robin" and groups:
        only = next(iter(groups))
        for p in scheme.participant_ids:
            if p not in groups[only]:
                groups[only].append(p)
    return groups


def build_standings(
    scheme: Scheme, results: Results
) -> list[tuple[str, list[standRow]]]:
    """Klasemen siap render: [(label_tabel, baris), ...].

    Slot KO di-resolve via advance_scheme (tampilan) agar skor ronde
    lanjutan terhitung; skema asli tidak dimutasi.
    """
    scheme = advance_scheme(scheme, results) if results else scheme
    out: list[tuple[str, list[StandRow]]] = []
    is_rr = scheme.tournament.format == "round_robin"
    groups = _group_members(scheme)

    if is_rr and groups:
        g = next(iter(groups))
        gmatches = [m for m in scheme.matches if m.stage == "group"]
        out.append(("Klasemen round robin",
                    _stand_rows(groups[g], gmatches, results)))
    else:
        for g in sorted(groups):
            gmatches = [m for m in scheme.matches
                        if m.stage == "group" and m.group == g]
            rows = _stand_rows(groups[g], gmatches, results)
            if (_group_complete(scheme, g, results) and rows
                    and gmatches):
                q = scheme.tournament.qualify_per_group
                is_ko = scheme.tournament.format == "group_knockout"
                top_n = q if is_ko else 1
                marked: list[StandRow] = []
                for i, r in enumerate(rows):
                    if i < top_n:
                        kind = "juara grup" if i == 0 else f"peringkat {i + 1}"
                        # "lolos" hanya bila memang ada knockout lanjutan;
                        # format group murni juara = peringkat akhir.
                        label = f" -> lolos ({kind})" if is_ko else f" -> {kind}"
                        marked.append(replace(
                            r,
                            catatan=(r.catatan + " | ").strip(" |") + label))
                    else:
                        marked.append(r)
                out.append((f"Klasemen grup {g}", marked))
            else:
                out.append((f"Klasemen grup {g}", rows))

    if any(m.stage == "knockout" for m in scheme.matches):
        st = _ko_status(scheme, results)
        rows = []
        for p in scheme.participant_ids:
            main = menang = seri = kalah = gf = ga = poin = 0
            for m in scheme.matches:
                res = results.get(m.id)
                if m.status == "walkover":
                    real = [s for s in (m.participant_a, m.participant_b)
                            if s is not None and not is_placeholder(s)]
                    if m.round == "F3" and len(real) == 2:
                        # Pemenang WO F3 di slot a (konvensi set_walkover).
                        if p == m.participant_a:
                            main += 1
                            menang += 1
                            poin += 3
                    elif real == [p]:
                        main += 1
                        menang += 1
                        poin += 3
                    continue
                if res is None or p not in (m.participant_a, m.participant_b):
                    continue
                main += 1
                if p == m.participant_a:
                    gf, ga = gf + res.score_a, ga + res.score_b
                else:
                    gf, ga = gf + res.score_b, ga + res.score_a
                if res.winner is None:
                    seri += 1
                    poin += 1
                elif res.winner == p:
                    menang += 1
                    poin += 3
                else:
                    kalah += 1
            rows.append(StandRow(participant=p, main=main, menang=menang,
                                 seri=seri, kalah=kalah, gf=gf, ga=ga,
                                 poin=poin, catatan=st.get(p, "")))
        rank = {"Juara": 0, "Juara 2": 1, "Juara 3": 2, "Peringkat 4": 3}
        rows.sort(key=lambda r: (rank.get(r.catatan, 4), -r.poin,
                                 r.participant))
        out.append(("Jalur knockout", rows))
    return out or [("Klasemen", [])]


def advance_scheme(scheme: Scheme, results: Results) -> Scheme:
    """Salinan skema dengan slot TBD terisi dari hasil (untuk tampilan).

    Maju hanya sejauh hasil tersedia; 'Juara Grup X' diisi bila grupnya
    sudah lengkap (juara = baris teratas klasemen, tie-break sama dengan
    build_standings). Skema asli tidak diubah.
    """
    group_rank: dict[tuple[int, str], str] = {}
    for g, members in _group_members(scheme).items():
        if not g or not _group_complete(scheme, g, results):
            continue
        gmatches = [m for m in scheme.matches
                    if m.stage == "group" and m.group == g]
        rows = _stand_rows(members, gmatches, results)
        for i, r in enumerate(rows, start=1):
            group_rank[(i, g)] = r.participant

    def resolve(slot: str | None, queue: list[str]) -> str | None:
        if slot is None:
            return queue.pop(0) if queue else None
        pq = parse_group_qualifier(slot)
        if pq is not None:
            # 'Juara Grup X' / 'Peringkat 2 Grup X' -> klasemen bila lengkap
            return group_rank.get(pq, slot)
        return slot

    def resolve_ready(slot: str | None) -> str | None:
        """Isi slot yang TIDAK butuh antrean pemenang (grup/kalah sudah
        diketahui) — dipakai juga saat antrean tertahan (stopped)."""
        if slot is None:
            return None
        pq = parse_group_qualifier(slot)
        if pq is not None:
            return group_rank.get(pq, slot)
        if slot.startswith(LOSER_PREFIX + " "):
            return losers.get(slot, slot)
        return slot

    queue: list[str] = []
    losers: dict[str, str] = {}
    # Posisi 1-based per match di ronde (sinkron dengan set_walkover F3
    # dan penomoran generator Kalah {ronde}-1/2 — WO tidak boleh geser).
    pos_in_round: dict[str, int] = {}
    for _lbl in {m.round for m in scheme.matches if m.stage == "knockout"}:
        same = [x for x in scheme.matches
                if x.stage == "knockout" and x.round == _lbl]
        for _i, _m in enumerate(same, start=1):
            pos_in_round[_m.id] = _i
    new_matches: list[Match] = []
    stopped = False
    for m in scheme.matches:
        if m.stage != "knockout":
            new_matches.append(m)
            continue
        # F3 (juara 3): slot 'Kalah ...' — independen antrean pemenang.
        if m.round == "F3":
            a = m.participant_a
            b = m.participant_b
            if a is not None and a.startswith(LOSER_PREFIX + " "):
                a = losers.get(a, a)
            if b is not None and b.startswith(LOSER_PREFIX + " "):
                b = losers.get(b, b)
            new_matches.append(replace(m, participant_a=a, participant_b=b))
            continue  # tidak stop, tidak menambah antrean juara 1
        if stopped:
            # Antrean pemenang tertahan; grup/kalah yang sudah pasti tetap
            # diisi agar bracket group_knockout tampil penuh.
            a = resolve_ready(m.participant_a)
            b = resolve_ready(m.participant_b)
            new_matches.append(replace(m, participant_a=a, participant_b=b))
            continue
        if m.status == "walkover":
            real = [s for s in (m.participant_a, m.participant_b)
                    if s is not None and not is_placeholder(s)]
            if len(real) == 1:
                queue.append(real[0])
            new_matches.append(m)
            continue
        a = resolve(m.participant_a, queue)
        b = resolve(m.participant_b, queue)
        res = results.get(m.id)
        new_matches.append(replace(m, participant_a=a, participant_b=b))
        real_a = a is not None and not is_placeholder(a)
        real_b = b is not None and not is_placeholder(b)
        if real_a and real_b and res is not None and res.winner is not None:
            loser = b if res.winner == a else a
            seq = pos_in_round.get(m.id, 0)
            if loser is not None and seq >= 1:
                losers[f"Kalah {m.round}-{seq}"] = loser
            queue.append(res.winner)
        elif a is None or b is None:
            if not queue:
                stopped = True
        elif real_a and real_b:
            # dua peserta siap tapi belum ada skor — ronde berikut tertahan
            stopped = True
        # placeholder belum terisi (grup/Kalah belum lengkap): jangan stop
    return Scheme(
        tournament=scheme.tournament,
        participant_ids=list(scheme.participant_ids),
        matches=new_matches,
        notes=list(scheme.notes),
        bye_details=list(scheme.bye_details),
    )


def render_standings(
    tables: list[tuple[str, list[StandRow]]], results: Results
) -> str:
    lines = ["== KLASEMEN =="]
    if not results:
        lines.append("(belum ada skor - isi di halaman Hasil)")
        return "\n".join(lines)
    lines.append(f"Skor tercatat: {len(results)}")
    for label, rows in tables:
        lines.append(f"-- {label} --")
        if not rows:
            lines.append("  (kosong)")
            continue
        lines.append(
            "  #  Peserta         M  M  S  K  GF  GA  Poin  Status")
        for i, r in enumerate(rows, 1):
            lines.append(
                f"  {i:<2}{r.participant:<16}{r.main:>2}{r.menang:>3}"
                f"{r.seri:>3}{r.kalah:>3}{r.gf:>4}{r.ga:>4}{r.poin:>6}"
                f"  {r.catatan}")
    return "\n".join(lines)
