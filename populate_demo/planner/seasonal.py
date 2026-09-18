"""Section 7: product family mix and the repeating back-to-school calendar.

Family is sampled first from the flat statistical weights, then the
quotation date is sampled within the year from a daily-weight curve that
depends on the family's calendar group (spec: "sample the lead product
family first, then choose quotation dates with the following daily
weights"). November 2020 gets a distinct, separate Chocogrenouilles spike
(section 7) that multiplies quantity rather than date density, applied
later during basket assembly.
"""
from __future__ import annotations

import calendar as _calendar
import random
from datetime import date, datetime, timedelta

from .config import BASE_FAMILY_WEIGHTS, CALENDAR_GROUP, DEFAULT_HOUR, FAMILIES, FAMILY_PRODUCTS, SEASONAL_WINDOWS


def sample_family(rng: random.Random) -> str:
    families = list(BASE_FAMILY_WEIGHTS)
    weights = list(BASE_FAMILY_WEIGHTS.values())
    return rng.choices(families, weights=weights, k=1)[0]


def _multiplier_for_day(d: date, curve_group: str) -> float:
    for (m1, d1), (m2, d2), multipliers in SEASONAL_WINDOWS:
        start = date(d.year, m1, d1)
        end = date(d.year, m2, d2)
        if start <= d <= end:
            return multipliers[curve_group]
    return 1.0


def sample_date_in_year(year: int, family: str, rng: random.Random, *, max_date: date | None = None) -> datetime:
    """Sample a quotation datetime within ``year`` weighted by the family's seasonal curve.

    :param max_date: Optional inclusive cap (e.g. the scenario cutoff for 2026).
    """
    curve_group = CALENDAR_GROUP[family]
    day_count = 366 if _calendar.isleap(year) else 365
    start = date(year, 1, 1)
    days = [start + timedelta(n) for n in range(day_count)]
    if max_date is not None:
        days = [d for d in days if d <= max_date]
    weights = [_multiplier_for_day(d, curve_group) for d in days]
    picked = rng.choices(days, weights=weights, k=1)[0]
    return datetime(picked.year, picked.month, picked.day, DEFAULT_HOUR)
