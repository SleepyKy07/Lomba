"""Probability Engine (PRD §9).

Mode 1 equal: semua peserta peluang sama.
Mode 2 custom: bobot manual -> Bradley-Terry P(a>b) = sa/(sa+sb).
Mode 3 Monte Carlo: simulasi bracket berulang.

Angka adalah konsekuensi model probabilitas yang dipilih, BUKAN
prediksi kemampuan nyata peserta.

Invarian: slot TBD diisi dari antrean pemenang sesuai URUTAN KREASI
match (kontrak generator). Operasi manual yang menyisipkan/menghapus
match (bukan swap/replace/walkover) dapat menggeser asumsi ini.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from .models import (
    LOSER_PREFIX,
    ROUND_ORDER,
    Scheme,
    is_placeholder,
    parse_group_qualifier,
)


@dataclass(frozen=True)
class StrengthModel:
    weights: dict[str, float]
    default_weight: float = 1.0
    description: str = ""


def equal_model(participant_ids: list[str]) -> StrengthModel:
    """Mode 1: peluang menang sama untuk semua."""
    pids = list(dict.fromkeys(participant_ids))
    if not pids:
        raise ValueError("Model butuh minimal 1 peserta.")
    return StrengthModel(
        weights={p: 1.0 for p in pids},
        description=f"equal ({len(pids)} peserta)",
    )


def custom_model(
    weights: dict[str, float], participant_ids: list[str]
) -> StrengthModel:
    """Mode 2: bobot manual. ID tak dikenal / bobot negatif ditolak.
    Peserta tanpa bobot memakai default 1.0 (dicatat di description)."""
    pids = list(dict.fromkeys(participant_ids))
    unknown = [k for k in weights if k not in pids]
    if unknown:
        raise ValueError(f"Bobot untuk peserta tak dikenal: {unknown}.")
    for k, v in weights.items():
        if v < 0:
            raise ValueError(f"Bobot negatif untuk {k}.")
    effective = {p: weights.get(p, 1.0) for p in pids}
    if not any(v > 0 for v in effective.values()):
        raise ValueError("Minimal satu bobot efektif positif.")
    missing = [p for p in pids if p not in weights]
    desc = f"custom ({len(weights)} bobot)"
    if missing:
        desc += f"; default 1.0 untuk {', '.join(missing)}"
    return StrengthModel(
        weights=dict(weights), description=desc,
    )


def percent_model(
    percentages: dict[str, float], participant_ids: list[str]
) -> StrengthModel:
    """Mode 2 gaya PRD §9 (A=60%, B=40%): persen head-to-head yang
    jumlahnya 100. Dikonversi ke bobot Bradley-Terry (60:40)."""
    pids = list(dict.fromkeys(participant_ids))
    unknown = [k for k in percentages if k not in pids]
    if unknown:
        raise ValueError(f"Persen untuk peserta tak dikenal: {unknown}.")
    for k, v in percentages.items():
        if v < 0:
            raise ValueError(f"Persen negatif untuk {k}.")
    if abs(sum(percentages.values()) - 100.0) > 0.01:
        raise ValueError(
            f"Total persen harus 100, dapat {sum(percentages.values())}."
        )
    model = custom_model(dict(percentages), pids)
    return StrengthModel(
        weights=dict(model.weights),
        default_weight=model.default_weight,
        description=f"custom persen ({', '.join(f'{k}={v}%' for k, v in percentages.items())})",
    )


def win_probability(model: StrengthModel, a: str, b: str) -> float:
    """Peluang a mengalahkan b (Bradley-Terry)."""
    sa = model.weights.get(a, model.default_weight)
    sb = model.weights.get(b, model.default_weight)
    if sa <= 0 and sb <= 0:
        raise ValueError(f"Bobot nol untuk {a} dan {b}.")
    if sa <= 0:
        return 0.0
    if sb <= 0:
        return 1.0
    return sa / (sa + sb)


def _ko_rounds_in_order(scheme: Scheme) -> list[str]:
    # F3 dikecualikan: bukan jalur juara 1.
    labels = {
        m.round for m in scheme.matches
        if m.stage == "knockout" and m.round != "F3"
    }
    return sorted(labels, key=lambda r: (ROUND_ORDER.get(r, 1), r))


def _group_of(scheme: Scheme) -> dict[str, str]:
    """Peserta -> grup ('' untuk round robin / tanpa grup)."""
    out: dict[str, str] = {}
    for m in scheme.matches:
        if m.stage != "group":
            continue
        for slot in (m.participant_a, m.participant_b):
            if not is_placeholder(slot):
                assert slot is not None
                out.setdefault(slot, m.group)
    return out


def _simulate_group_standings(
    scheme: Scheme, model: StrengthModel, rng: random.Random
) -> dict[str, list[str]]:
    """Grup -> peringkat (kemenangan terbanyak; seri diacak)."""
    wins: dict[str, int] = {p: 0 for p in scheme.participant_ids}
    for m in scheme.matches:
        if m.stage != "group":
            continue
        a, b = m.participant_a, m.participant_b
        if is_placeholder(a) or is_placeholder(b):
            continue
        assert a is not None and b is not None
        w = a if rng.random() < win_probability(model, a, b) else b
        wins[w] += 1
    groups: dict[str, list[str]] = {}
    gmap = _group_of(scheme)
    for p in scheme.participant_ids:
        groups.setdefault(gmap.get(p, ""), []).append(p)
    standings: dict[str, list[str]] = {}
    for g, members in groups.items():
        order = list(members)
        rng.shuffle(order)
        order.sort(key=lambda p: -wins[p])
        standings[g] = order
    return standings


def _resolve(
    slot: str | None,
    queue: list[str],
    group_rank: dict[tuple[int, str], str],
    losers: dict[str, str],
) -> str:
    if slot is None:
        if not queue:
            raise ValueError("Bracket tak dapat disimulasikan: slot TBD tanpa sumber.")
        return queue.pop(0)
    pq = parse_group_qualifier(slot)
    if pq is not None:
        if pq not in group_rank:
            raise ValueError(
                f"Kualifikasi {slot!r} tak dapat ditentukan "
                "(klasemen grup belum lengkap).")
        return group_rank[pq]
    if slot.startswith(LOSER_PREFIX + " "):
        if slot not in losers:
            raise ValueError(
                f"Slot {slot!r} belum bisa diisi - ronde kalah "
                "(perebutan juara 3) belum selesai / walkover tanpa "
                "kalah tercatat.")
        return losers[slot]
    return slot


def simulate_once(
    scheme: Scheme, model: StrengthModel, rng: random.Random
) -> tuple[str, list[str]]:
    """Satu simulasi penuh -> (juara, finalis)."""
    ko_rounds = _ko_rounds_in_order(scheme)
    has_group = any(m.stage == "group" for m in scheme.matches)
    group_rank: dict[tuple[int, str], str] = {}
    finalists: list[str] = []
    if has_group:
        standings = _simulate_group_standings(scheme, model, rng)
        for g, order in standings.items():
            for i, p in enumerate(order, start=1):
                group_rank[(i, g)] = p
        if not ko_rounds:
            # Round robin: juara = teratas klasemen.
            # Grup murni multi-grup tak menentukan juara tunggal
            # (gunakan format group_knockout).
            if len(standings) == 1:
                top = next(iter(standings.values()))
                return top[0], top[:2]
            raise ValueError(
                "Fase grup murni multi-grup tak menentukan juara tunggal; "
                "gunakan format group_knockout."
            )
    if not ko_rounds:
        raise ValueError("Skema tanpa match tak dapat disimulasikan.")
    queue: list[str] = []
    losers: dict[str, str] = {}
    # Posisi 1-based per match di ronde — sinkron dengan set_walkover F3
    # dan generator (WO tidak boleh menggeser nomor Kalah {ronde}-N).
    pos_in_round: dict[str, int] = {}
    for _lbl in {m.round for m in scheme.matches if m.stage == "knockout"}:
        same = [x for x in scheme.matches
                if x.stage == "knockout" and x.round == _lbl]
        for _i, _m in enumerate(same, start=1):
            pos_in_round[_m.id] = _i
    final_round = ko_rounds[-1]
    for m in scheme.matches:
        if m.stage != "knockout":
            continue
        # F3 diproses dulu: tak pernah mengantre ke juara 1
        # (termasuk bila F3 walkover — jangan queue.append).
        if m.round == "F3":
            if m.status == "walkover":
                # F3 WO: boleh 1 slot nyata (WO lama) atau 2 (set_walkover
                # menyimpan kalah di b untuk Peringkat 4). Tak memengaruhi juara 1.
                continue
            a = _resolve(m.participant_a, queue, group_rank, losers)
            b = _resolve(m.participant_b, queue, group_rank, losers)
            if a == b:
                continue
            w = a if rng.random() < win_probability(model, a, b) else b
            loser = b if w == a else a
            seq = pos_in_round.get(m.id, 0)
            if seq >= 1:
                losers[f"Kalah {m.round}-{seq}"] = loser
            continue  # hasil F3 tak memengaruhi juara 1
        if m.status == "walkover":
            # Lolos tanpa undian: satu-satunya slot nyata langsung maju.
            # Kalah WO diisi set_walkover ke F3 (bila ronde sumber F3).
            real = [s for s in (m.participant_a, m.participant_b)
                    if not is_placeholder(s)]
            if len(real) != 1:
                raise ValueError(
                    f"Match walkover {m.id} harus punya tepat 1 slot nyata."
                )
            assert real[0] is not None
            queue.append(real[0])
            if m.round == final_round:
                finalists = [real[0]]
            continue
        a = _resolve(m.participant_a, queue, group_rank, losers)
        b = _resolve(m.participant_b, queue, group_rank, losers)
        if a == b:
            queue.append(a)  # walkover / slot sama: lolos langsung
            if m.round == final_round:
                finalists = [a]
            continue
        w = a if rng.random() < win_probability(model, a, b) else b
        loser = b if w == a else a
        seq = pos_in_round.get(m.id, 0)
        if seq >= 1:
            losers[f"Kalah {m.round}-{seq}"] = loser
        queue.append(w)
        if m.round == final_round:
            finalists = [a, b]
    if not queue:
        raise ValueError("Simulasi tak menghasilkan juara.")
    return queue[-1], finalists


@dataclass
class MonteCarloResult:
    n: int
    model_desc: str
    champion_share: dict[str, float] = field(default_factory=dict)
    finalist_share: dict[str, float] = field(default_factory=dict)
    seed: int | None = None


def monte_carlo(
    scheme: Scheme,
    model: StrengthModel,
    n: int = 10000,
    seed: int | None = None,
) -> MonteCarloResult:
    """Mode 3: simulasi berulang -> distribusi juara/finalis."""
    if n < 1:
        raise ValueError("n minimal 1.")
    if not scheme.matches:
        raise ValueError("Skema tanpa match tak dapat disimulasikan.")
    rng = random.Random(seed)
    champ: dict[str, int] = {}
    fin: dict[str, int] = {}
    for _ in range(n):
        c, f = simulate_once(scheme, model, rng)
        champ[c] = champ.get(c, 0) + 1
        for p in f:
            fin[p] = fin.get(p, 0) + 1
    return MonteCarloResult(
        n=n,
        model_desc=model.description,
        champion_share={p: v / n for p, v in sorted(champ.items())},
        finalist_share={p: v / n for p, v in sorted(fin.items())},
        seed=seed,
    )


def exact_equal_title_probability(scheme: Scheme) -> dict[str, float] | None:
    """Eksak untuk knockout murni + model equal: (1/2)^menang_yang_dibutuhkan.

    Kembali None untuk skema grup (juara grup ditentukan hasil, bukan undian).
    Peserta yang tak tampil di slot KO mana pun (ex: tersingkir walkover)
    mendapat 0.0. Asumsi bracket utuh; pasca-walkover gunakan Monte Carlo.
    """
    ko_rounds = _ko_rounds_in_order(scheme)
    if not ko_rounds:
        return None
    if any(m.stage == "group" for m in scheme.matches):
        return None
    first = ko_rounds[0]
    played_first: set[str] = set()
    played_any: set[str] = set()
    for m in scheme.matches:
        if m.stage != "knockout":
            continue
        for slot in (m.participant_a, m.participant_b):
            if not is_placeholder(slot):
                assert slot is not None
                played_any.add(slot)
                if m.round == first:
                    played_first.add(slot)
    out: dict[str, float] = {}
    for p in scheme.participant_ids:
        if p not in played_any:
            out[p] = 0.0
            continue
        entry_idx = 0 if p in played_first else 1
        out[p] = 0.5 ** (len(ko_rounds) - entry_idx)
    return out


def render_probability(result: MonteCarloResult, top: int = 8) -> str:
    """Render distribusi juara ala PRD §9 + disclaimer wajib."""
    lines = [
        "== PROBABILITY ==",
        f"Model: {result.model_desc} | simulasi: {result.n}"
        + (f" | seed {result.seed}" if result.seed is not None else ""),
    ]
    ordered = sorted(result.champion_share.items(), key=lambda kv: -kv[1])[:top]
    for p, share in ordered:
        fin = result.finalist_share.get(p, 0.0)
        lines.append(f"  {p} -> Juara: {share * 100:.1f}% | Finalis: {fin * 100:.1f}%")
    hidden = len(result.champion_share) - len(ordered)
    if hidden > 0:
        lines.append(f"  (+{hidden} peserta lainnya di bawah)")
    lines.append(
        "Hasil simulasi model di atas, BUKAN prediksi kemampuan nyata peserta."
    )
    return "\n".join(lines)
