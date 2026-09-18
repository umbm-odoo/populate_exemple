"""Spec section 3/5 quota tables and their resolution to whole-record counts.

All tables are kept at full (100,000-order) scale here; callers pass a
``scale`` factor (1.0 for the full run, 0.01 for the 1% pilot) so the same
tables drive both without duplication. Section 13 defines the pilot as an
independent 1,000-order base rather than a literal 1% slice of every cell,
so ``scale`` only touches the totals that must reconcile - the shape of the
allocation (which years/outcomes/regions get the rounding-up) is derived
fresh at whatever scale is requested.
"""
from __future__ import annotations

from .rounding import largest_remainder, reconcile_matrix

OUTCOMES = ('delivered', 'awaiting', 'cancelled', 'open')

# Spec section 3.
ANNUAL = {
    2016: {'all': 1500, 'delivered': 1300, 'awaiting': 0, 'cancelled': 200, 'open': 0},
    2017: {'all': 1900, 'delivered': 1650, 'awaiting': 0, 'cancelled': 250, 'open': 0},
    2018: {'all': 2400, 'delivered': 2100, 'awaiting': 0, 'cancelled': 300, 'open': 0},
    2019: {'all': 3000, 'delivered': 2650, 'awaiting': 0, 'cancelled': 350, 'open': 0},
    2020: {'all': 2700, 'delivered': 2300, 'awaiting': 0, 'cancelled': 400, 'open': 0},
    2021: {'all': 8000, 'delivered': 7100, 'awaiting': 0, 'cancelled': 900, 'open': 0},
    2022: {'all': 11000, 'delivered': 9850, 'awaiting': 0, 'cancelled': 1150, 'open': 0},
    2023: {'all': 12500, 'delivered': 11000, 'awaiting': 0, 'cancelled': 1500, 'open': 0},
    2024: {'all': 14500, 'delivered': 13100, 'awaiting': 0, 'cancelled': 1400, 'open': 0},
    2025: {'all': 18000, 'delivered': 16450, 'awaiting': 0, 'cancelled': 1550, 'open': 0},
    2026: {'all': 24500, 'delivered': 15500, 'awaiting': 2000, 'cancelled': 2000, 'open': 5000},
}
ANNUAL_TOTAL = {
    'all': sum(y['all'] for y in ANNUAL.values()),
    'delivered': sum(y['delivered'] for y in ANNUAL.values()),
    'awaiting': sum(y['awaiting'] for y in ANNUAL.values()),
    'cancelled': sum(y['cancelled'] for y in ANNUAL.values()),
    'open': sum(y['open'] for y in ANNUAL.values()),
}
assert ANNUAL_TOTAL == {'all': 100_000, 'delivered': 83_000, 'awaiting': 2_000, 'cancelled': 10_000, 'open': 5_000}

# Spec section 5. 2016-2020 share the same weights ("2016-2020" row).
REGION_WEIGHTS = {
    **{y: {'europe': 0.80, 'americas': 0.15, 'apac': 0.05} for y in range(2016, 2021)},
    2021: {'europe': 0.70, 'americas': 0.20, 'apac': 0.10},
    2022: {'europe': 0.66, 'americas': 0.22, 'apac': 0.12},
    2023: {'europe': 0.62, 'americas': 0.24, 'apac': 0.14},
    2024: {'europe': 0.58, 'americas': 0.26, 'apac': 0.16},
    2025: {'europe': 0.54, 'americas': 0.28, 'apac': 0.18},
    2026: {'europe': 0.50, 'americas': 0.30, 'apac': 0.20},
}
UK_SHARE_OF_EUROPE = 0.60
REGIONS = ('uk', 'other_europe', 'americas', 'apac')


def annual_outcome_quotas(scale: float) -> dict[int, dict[str, int]]:
    """Whole-record year x outcome counts at the requested scale.

    Row totals (per year) and column totals (per outcome, matching the
    scaled versions of 83,000 / 2,000 / 10,000 / 5,000) are both matched
    exactly via ``reconcile_matrix``.
    """
    years = sorted(ANNUAL)
    row_targets = [round(ANNUAL[y]['all'] * scale) for y in years]
    col_targets = [round(ANNUAL_TOTAL[outcome] * scale) for outcome in OUTCOMES]

    if sum(row_targets) != sum(col_targets):
        raise ValueError(
            f"Scale {scale} does not divide evenly: row total {sum(row_targets)} "
            f"!= column total {sum(col_targets)}.",
        )

    matrix = [[ANNUAL[y][outcome] * scale for outcome in OUTCOMES] for y in years]
    result = reconcile_matrix(matrix, row_targets, col_targets)
    return {
        y: dict(zip(OUTCOMES, row, strict=True))
        for y, row in zip(years, result, strict=True)
    }


def geographic_quotas(year: int, confirmed_count: int) -> dict[str, int]:
    """Whole-record UK / other-Europe / Americas / APAC split for one year's confirmed orders.

    Only reconciled "within one order" for this single year (spec section 5)
    - not against any fixed multi-year column total, which the spec does not
    define for geography the way it does for the outcome quotas.
    """
    weights = REGION_WEIGHTS[year]
    real_values = [
        confirmed_count * weights['europe'] * UK_SHARE_OF_EUROPE,
        confirmed_count * weights['europe'] * (1 - UK_SHARE_OF_EUROPE),
        confirmed_count * weights['americas'],
        confirmed_count * weights['apac'],
    ]
    result = largest_remainder(real_values, confirmed_count)
    return dict(zip(REGIONS, result, strict=True))
