"""Section 8: sales team/rep assignment and marketing attribution."""
from __future__ import annotations

import random

# Matches the workbook's utm.medium per utm.source (spec: "Match medium to source").
SOURCE_MEDIUM = {
    'bi_source_prophet': 'bi_medium_print',
    'bi_source_owl': 'bi_medium_email',
    'bi_source_referral': 'bi_medium_referral',
    'bi_source_web': 'bi_medium_web',
}
SOURCE_WEIGHTS_BEFORE_2021 = {'bi_source_prophet': 0.45, 'bi_source_owl': 0.25, 'bi_source_referral': 0.20, 'bi_source_web': 0.10}
SOURCE_WEIGHTS_FROM_2021 = {'bi_source_prophet': 0.20, 'bi_source_owl': 0.25, 'bi_source_referral': 0.20, 'bi_source_web': 0.35}

TEAMS = {
    'team_gryffindor': ('user_g_1', 'user_g_2', 'user_g_3'),
    'team_hufflepuff': ('user_h_1', 'user_h_2', 'user_h_3'),
    'team_ravenclaw': ('user_r_1', 'user_r_2', 'user_r_3'),
    'team_slytherin': ('user_s_1', 'user_s_2', 'user_s_3'),
}
ALL_REPS = [(team, user) for team, users in TEAMS.items() for user in users]


def pick_rep(rng: random.Random) -> tuple[str, str]:
    """Returns (team_xmlid, user_xmlid)."""
    return rng.choice(ALL_REPS)


LOST_REASON_WEIGHTS = {
    'bi_loss_price': 0.40,
    'bi_loss_timing': 0.25,
    'bi_loss_competitor': 0.25,
    'bi_loss_no_need': 0.10,
}


def pick_lost_reason(rng: random.Random) -> str:
    reasons = list(LOST_REASON_WEIGHTS)
    return rng.choices(reasons, weights=list(LOST_REASON_WEIGHTS.values()), k=1)[0]


def pick_source(year: int, rng: random.Random) -> tuple[str, str]:
    """Returns (source_xmlid, medium_xmlid)."""
    weights = SOURCE_WEIGHTS_BEFORE_2021 if year < 2021 else SOURCE_WEIGHTS_FROM_2021
    sources = list(weights)
    source = rng.choices(sources, weights=list(weights.values()), k=1)[0]
    return source, SOURCE_MEDIUM[source]
