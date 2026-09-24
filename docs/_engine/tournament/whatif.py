"""What-If Analysis (PRD §10): ubah kondisi tanpa membuat lomba baru.

Parameter yang dapat diubah: peserta (tambah/kurang/ganti),
format, jumlah arena, durasi, waktu istirahat, jumlah juara, team size.
Sistem menghitung ulang format/bracket/bye/jadwal/fairness.
"""
from __future__ import annotations

from dataclasses import replace

from .analysis import SchemeReport, build_report
from .models import Tournament

ALLOWED_KEYS = {
    "add", "remove", "format", "team_size", "winner_count",
    "duration_min", "minimum_rest_min", "arena_count",
    "date", "start_time", "end_time", "num_groups",
    "qualify_per_group",
}


def _as_list(value: object, key: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    try:
        return list(value)  # type: ignore[arg-type]
    except TypeError as exc:
        raise ValueError(f"Parameter what-if {key!r} harus list ID.") from exc


def apply_changes(
    tournament: Tournament,
    participant_ids: list[str],
    changes: dict,
    registry=None,
) -> tuple[Tournament, list[str]]:
    """Terapkan perubahan → (tournament baru, peserta baru). Validasi penuh
    lewat konstruktor Tournament + dedup peserta. Bila registry diberikan,
    ID tambahan divalidasi ke master kelas."""
    unknown = set(changes) - ALLOWED_KEYS
    if unknown:
        raise ValueError(f"Parameter what-if tak dikenal: {sorted(unknown)}.")
    if "num_groups" in changes:
        raise ValueError(
            "num_groups diatur via argumen what_if(), bukan changes."
        )
    participants = list(dict.fromkeys(participant_ids))
    removed = set(_as_list(changes.get("remove"), "remove"))
    for cid in removed:
        if cid not in participants:
            raise ValueError(f"Peserta {cid} tidak ada di lomba.")
    added = _as_list(changes.get("add"), "add")
    if registry is not None:
        for cid in added:
            registry.get(cid)  # validasi ke master (ValueError bila asing)
    # Urutan seed dijaga: posisi semula dipertahankan; hanya ID yang
    # benar-benar baru (tak ada di daftar awal) ditambah di akhir.
    # remove+add ID yang sama = no-op (bye tak berpindah).
    original = set(participants)
    staying = [p for p in participants if p not in removed or p in added]
    newcomers = [c for c in dict.fromkeys(added) if c not in original]
    participants = staying + newcomers
    if not participants:
        raise ValueError("What-if menyisakan 0 peserta.")
    t_kwargs = {
        "format": changes.get("format", tournament.format),
        "team_size": changes.get("team_size", tournament.team_size),
        "winner_count": changes.get("winner_count", tournament.winner_count),
        "duration_min": changes.get("duration_min", tournament.duration_min),
        "minimum_rest_min": changes.get(
            "minimum_rest_min", tournament.minimum_rest_min),
        "arena_count": changes.get("arena_count", tournament.arena_count),
        "date": changes.get("date", tournament.date),
        "start_time": changes.get("start_time", tournament.start_time),
        "end_time": changes.get("end_time", tournament.end_time),
        "qualify_per_group": changes.get(
            "qualify_per_group", tournament.qualify_per_group),
    }
    # replace() memanggil __init__ + __post_init__ sehingga validasi penuh.
    new_t = replace(tournament, **t_kwargs)  # type: ignore[arg-type]
    return new_t, participants


def what_if(
    tournament: Tournament,
    participant_ids: list[str],
    changes: dict,
    num_groups: int | None = None,
    registry=None,
) -> tuple[SchemeReport, SchemeReport]:
    """Kembalikan (before, after) sebagai SchemeReport siap banding.

    changes["num_groups"] (opsional) hanya berlaku untuk skema sesudah.
    """
    before = build_report(tournament, participant_ids, num_groups)
    changes = dict(changes)
    after_groups = changes.pop("num_groups", num_groups)
    new_t, new_p = apply_changes(tournament, participant_ids, changes, registry)
    after = build_report(new_t, new_p, after_groups)
    return before, after
