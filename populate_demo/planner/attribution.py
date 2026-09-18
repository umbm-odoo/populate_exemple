"""Section 8: sales team/rep assignment and marketing attribution."""
from __future__ import annotations

import random

from .config import LOST_REASON_WEIGHTS, SOURCE_MEDIUM, SOURCE_WEIGHTS_BEFORE_2021, SOURCE_WEIGHTS_FROM_2021, TEAMS

ALL_REPS = [(team, user) for team, users in TEAMS.items() for user in users]


def pick_rep(rng: random.Random) -> tuple[str, str]:
    """Returns (team_xmlid, user_xmlid)."""
    return rng.choice(ALL_REPS)


def pick_lost_reason(rng: random.Random) -> str:
    reasons = list(LOST_REASON_WEIGHTS)
    return rng.choices(reasons, weights=list(LOST_REASON_WEIGHTS.values()), k=1)[0]


def pick_source(year: int, rng: random.Random) -> tuple[str, str]:
    """Returns (source_xmlid, medium_xmlid)."""
    weights = SOURCE_WEIGHTS_BEFORE_2021 if year < 2021 else SOURCE_WEIGHTS_FROM_2021
    sources = list(weights)
    source = rng.choices(sources, weights=list(weights.values()), k=1)[0]
    return source, SOURCE_MEDIUM[source]
