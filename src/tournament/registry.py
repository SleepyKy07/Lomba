"""Master Kelas + Pemilihan Peserta (PRD F-01, F-03).

Satu-satunya sumber daftar kelas. Pemilihan peserta memvalidasi ID
dan melaporkan yang tidak ikut (PRD §4.3).
"""
from __future__ import annotations

from .models import ClassInfo


class ClassRegistry:
    def __init__(self) -> None:
        self._classes: dict[str, ClassInfo] = {}

    def add(self, info: ClassInfo) -> None:
        if info.id in self._classes:
            raise ValueError(f"Kelas duplikat: {info.id}.")
        self._classes[info.id] = info

    def get(self, class_id: str) -> ClassInfo:
        try:
            return self._classes[class_id]
        except KeyError as exc:
            raise ValueError(f"Kelas tak dikenal: {class_id}.") from exc

    def list_all(self) -> list[ClassInfo]:
        return list(self._classes.values())

    def count(self) -> int:
        return len(self._classes)


def build_default_master(n: int = 28) -> ClassRegistry:
    """Master bawaan ±28 kelas (nama generik; panitia dapat mengganti)."""
    reg = ClassRegistry()
    for i in range(1, n + 1):
        cid = f"XII-{i:02d}"
        reg.add(ClassInfo(id=cid, name=cid, tingkat="XII"))
    return reg


def select_participants(
    registry: ClassRegistry, ids: list[str]
) -> tuple[list[str], list[str]]:
    """Kembalikan (ikut, tidak_ikut). ID tak dikenal / kosong = error."""
    if not ids:
        raise ValueError("Pilih minimal 1 peserta.")
    ikut = list(dict.fromkeys(ids))
    for cid in ikut:
        registry.get(cid)  # validasi
    tidak_ikut = [c.id for c in registry.list_all() if c.id not in ikut]
    return ikut, tidak_ikut
