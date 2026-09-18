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

from .config import ANNUAL, ANNUAL_TOTAL, OUTCOMES, REGION_WEIGHTS, REGIONS, UK_SHARE_OF_EUROPE
from .rounding import largest_remainder, reconcile_matrix


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
