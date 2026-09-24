"""Dispatcher generator."""
from __future__ import annotations

from .generator_group import generate_group, generate_group_knockout
from .generator_knockout import (
    generate_knockout,
    generate_preliminary_knockout,
)
from .generator_roundrobin import generate_round_robin
from .models import Scheme, Tournament


def generate_scheme(
    tournament: Tournament,
    participant_ids: list[str],
    num_groups: int | None = None,
) -> Scheme:
    if tournament.format == "knockout":
        return generate_knockout(tournament, participant_ids)
    if tournament.format == "preliminary_knockout":
        return generate_preliminary_knockout(tournament, participant_ids)
    if tournament.format == "round_robin":
        return generate_round_robin(tournament, participant_ids)
    if tournament.format == "group":
        return generate_group(tournament, participant_ids, num_groups)
    if tournament.format == "group_knockout":
        return generate_group_knockout(tournament, participant_ids, num_groups)
    raise ValueError(f"Format tak dikenal: {tournament.format}")
