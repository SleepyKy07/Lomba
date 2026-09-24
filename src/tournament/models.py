"""Data Model — sesuai PRD §15 + §7.

Kontrak bersama agar label ronde/placeholder tidak tersebar (temuan review):
- ROUND_ORDER: urutan kanonis ronde (dipakai generator, fairness, scheduler, render).
- QUALIFIER_PREFIX: prefix slot lolos grup ("Juara Grup X").
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Prefix slot kualifikasi grup yang belum diketahui pemenangnya.
QUALIFIER_PREFIX = "Juara Grup"

# Prefix peringkat grup selain juara ("Peringkat 2 Grup A" — qualify_per_group>1).
RANK_QUALIFIER_PREFIX = "Peringkat"

# Prefix slot kalah ronde sebelumnya (perebutan juara 3, "Kalah SF-1").
LOSER_PREFIX = "Kalah"

# Urutan kanonis ronde. "P" = preliminary (eksplisit, F-04).
# Ronde grup GA/GB/... diurutkan lewat kunci khusus (lihat round_sort_key).
# F3 = perebutan juara 3 (setelah F; bukan jalur juara 1 — fairness/prob
# mengecualikan F3 dari path-to-title).
ROUND_ORDER: dict[str, int] = {
    "P": 1,
    "R1": 1,
    "R2": 2,
    "R3": 3,
    "R4": 4,
    "SF": 5,
    "F": 6,
    "F3": 7,
}

VALID_FORMATS = (
    "knockout",
    "preliminary_knockout",
    "round_robin",
    "group",
    "group_knockout",
)


def is_placeholder(slot: str | None) -> bool:
    """True untuk slot TBD: None, 'Juara Grup X', 'Peringkat k Grup X',
    atau 'Kalah ...' (F3).

    Prefix 'Kalah' / 'Peringkat' wajib diikuti spasi agar ID kelas
    seperti 'Kalahman' tidak salah dianggap placeholder.
    """
    if slot is None:
        return True
    return (
        slot.startswith(QUALIFIER_PREFIX)
        or slot.startswith(LOSER_PREFIX + " ")
        or slot.startswith(RANK_QUALIFIER_PREFIX + " ")
    )


def parse_group_qualifier(slot: str | None) -> tuple[int, str] | None:
    """'Juara Grup A' -> (1, A); 'Peringkat 2 Grup A' -> (2, A); else None."""
    if slot is None:
        return None
    if slot.startswith(QUALIFIER_PREFIX):
        g = slot[len(QUALIFIER_PREFIX):].strip()
        return (1, g) if g else None
    if slot.startswith(RANK_QUALIFIER_PREFIX + " "):
        rest = slot[len(RANK_QUALIFIER_PREFIX) + 1:]
        rank_s, _, tail = rest.partition(" ")
        if tail.startswith("Grup "):
            g = tail[len("Grup "):].strip()
            try:
                rank = int(rank_s)
            except ValueError:
                return None
            return (rank, g) if g and rank >= 1 else None
    return None


def round_sort_key(round_label: str, stage: str) -> tuple[int, str]:
    """Kunci urut ronde lintas stage. Grup selalu sebelum knockout."""
    if stage == "group":
        return (0, round_label)
    return (ROUND_ORDER.get(round_label, 1), round_label)


def _check_hhmm(value: str, field_name: str) -> int:
    try:
        h, m = value.split(":")
        total = int(h) * 60 + int(m)
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{field_name} harus format HH:MM, dapat: {value!r}.") from exc
    if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
        raise ValueError(f"{field_name} tidak valid: {value!r}.")
    return total


def minutes_to_hhmm(total: int) -> str:
    """Menit sejak 00:00 -> 'HH:MM'. Helper bersama (scheduler, cross-event)."""
    return f"{total // 60:02d}:{total % 60:02d}"


@dataclass(frozen=True)
class ClassInfo:
    # PRD §7 minta tingkat/jurusan; §15 minimal id/name.
    # Dibuat opsional agar kompatibel dengan keduanya.
    id: str
    name: str
    tingkat: str = ""
    jurusan: str = ""


@dataclass(frozen=True)
class Tournament:
    id: str
    name: str
    format: str  # lihat VALID_FORMATS
    team_size: int  # pemain per tim; >=1 (1v1..4v4 + kelompok, PRD §2)
    winner_count: int = 1
    duration_min: int = 30
    minimum_rest_min: int = 10
    arena_count: int = 2
    date: str = ""
    start_time: str = "08:00"  # "HH:MM"
    end_time: str = "17:00"
    # group_knockout: berapa peserta per grup lolos (1=juara, 2=+peringkat 2).
    qualify_per_group: int = 1

    def __post_init__(self) -> None:
        if self.format not in VALID_FORMATS:
            raise ValueError(f"format harus salah satu {list(VALID_FORMATS)}.")
        if self.team_size < 1:
            raise ValueError("team_size minimal 1.")
        if self.winner_count < 1:
            raise ValueError("winner_count minimal 1.")
        if self.arena_count < 1:
            raise ValueError("arena_count minimal 1.")
        if self.duration_min <= 0:
            raise ValueError("duration_min harus > 0.")
        if self.minimum_rest_min < 0:
            raise ValueError("minimum_rest_min tidak boleh negatif.")
        if self.qualify_per_group < 1:
            raise ValueError("qualify_per_group minimal 1.")
        start = _check_hhmm(self.start_time, "start_time")
        end = _check_hhmm(self.end_time, "end_time")
        if start >= end:
            raise ValueError("start_time harus sebelum end_time.")


@dataclass(frozen=True)
class Match:
    id: str
    tournament_id: str
    round: str  # "P", "R1", "SF", "F", "GA", ...
    stage: str  # "knockout" | "group"
    participant_a: str | None  # class id, None = slot TBD
    participant_b: str | None
    group: str = ""  # "A", "B" untuk fase grup
    status: str = "scheduled"  # PRD §15; "walkover" = lolos tanpa bertanding


@dataclass
class ScheduledMatch:
    match: Match
    scheduled_time: str  # "HH:MM"
    arena: int  # 1-based dalam batch waktu
    start_min: int = 0  # menit sejak 00:00, untuk hitung rest


@dataclass(frozen=True)
class Result:
    match_id: str
    winner: str | None = None
    score_a: int = 0
    score_b: int = 0


@dataclass(frozen=True)
class FairnessMetric:
    tournament_id: str
    metric_name: str
    value: str


@dataclass(frozen=True)
class ByeDetail:
    """Satu penerima bye (PRD §8.4): siapa, masuk di ronde apa,
    ronde apa saja yang dilewati, dan dampak jalur juaranya."""

    participant: str
    entry_round: str
    skipped_rounds: list[str]
    wins_needed: int


@dataclass
class Scheme:
    """Satu alternatif skema untuk satu set peserta (PRD §11)."""

    tournament: Tournament
    participant_ids: list[str]
    matches: list[Match] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    bye_details: list[ByeDetail] = field(default_factory=list)

    def summary_row(self) -> dict[str, str | int | float]:
        """Baris ringkas terstruktur untuk tabel perbandingan Phase 2 (PRD §11).
        Phase 1 hanya menyediakan datanya, tanpa UI perbandingan."""
        return {
            "tournament_id": self.tournament.id,
            "format": self.tournament.format,
            "participants": len(self.participant_ids),
            "total_matches": len(self.matches),
            "byes": len(self.bye_details),
        }

    def to_dict(self) -> dict:
        return {
            "tournament": {
                "id": self.tournament.id,
                "name": self.tournament.name,
                "format": self.tournament.format,
                "team_size": self.tournament.team_size,
                "winner_count": self.tournament.winner_count,
                "duration_min": self.tournament.duration_min,
                "minimum_rest_min": self.tournament.minimum_rest_min,
                "arena_count": self.tournament.arena_count,
                "date": self.tournament.date,
                "start_time": self.tournament.start_time,
                "end_time": self.tournament.end_time,
                "qualify_per_group": self.tournament.qualify_per_group,
            },
            "participant_ids": list(self.participant_ids),
            "matches": [
                {
                    "id": m.id,
                    "round": m.round,
                    "stage": m.stage,
                    "participant_a": m.participant_a,
                    "participant_b": m.participant_b,
                    "group": m.group,
                    "status": m.status,
                }
                for m in self.matches
            ],
            "notes": list(self.notes),
            "bye_details": [
                {
                    "participant": b.participant,
                    "entry_round": b.entry_round,
                    "skipped_rounds": list(b.skipped_rounds),
                    "wins_needed": b.wins_needed,
                }
                for b in self.bye_details
            ],
        }
