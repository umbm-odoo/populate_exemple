"""Spec section 3: the 2,000 outstanding confirmed orders' supply posture.

1,000 in transit to a regional warehouse / 600 awaiting production in
Belgium / 400 awaiting purchased goods, at full scale. "In transit" only
makes sense for a region actually served by a regional warehouse (UK, or
Americas/APAC from 2021) - "other Europe" is always served directly from
Belgium (spec section 6), so it can never be in the transit sub-bucket.
"""
from __future__ import annotations

from .config import OUTSTANDING_FULL_SCALE_TOTALS, OUTSTANDING_SUB_BUCKETS, REGION_WAREHOUSE, WAREHOUSE_OPENING
from .rounding import reconcile_matrix

SUB_BUCKETS = OUTSTANDING_SUB_BUCKETS
FULL_SCALE_TOTALS = OUTSTANDING_FULL_SCALE_TOTALS


def warehouse_for(region: str, year: int) -> str:
    """Fulfilling warehouse code for a destination region in a given year."""
    if region not in REGION_WAREHOUSE:
        raise ValueError(f"Unknown region {region!r}")
    code = REGION_WAREHOUSE[region]
    if code is not None and year >= WAREHOUSE_OPENING[code].year:
        return code
    return 'BE'


def outstanding_sub_buckets(awaiting_by_region: dict[str, int], year: int, scale: float) -> dict[str, dict[str, int]]:
    """Per-region counts of transit / production / purchase awaiting orders.

    :param awaiting_by_region: This year's awaiting-fulfilment order count per region.
    :param year: Order year (only 2026 has any awaiting orders in the base spec).
    :param scale: 1.0 for the full run, 0.01 for the pilot.
    """
    regions = sorted(awaiting_by_region)
    col_targets = [round(FULL_SCALE_TOTALS[b] * scale) for b in SUB_BUCKETS]
    if sum(col_targets) != sum(awaiting_by_region.values()):
        raise ValueError(
            f"Sub-bucket totals {col_targets} don't sum to the awaiting total "
            f"{sum(awaiting_by_region.values())} for {year}.",
        )

    forbidden = set()
    forced_weights = {'transit': 0.0, 'production': 0.6, 'purchase': 0.4}
    transit_possible = {region: warehouse_for(region, year) != 'BE' for region in regions}

    # A region forced out of transit still has to land somewhere, at the
    # forced 0.6/0.4 split - so it structurally can't carry its share of the
    # global column totals. The regions that *can* still use every bucket
    # must absorb that shortfall, or the columns can never reconcile: with
    # even one forced-out region, applying the plain global ratio to every
    # eligible region independently leaves transit short and
    # production/purchase over by however many units that region held.
    forced_totals = {b: 0.0 for b in SUB_BUCKETS}
    eligible_total = 0
    for region in regions:
        if transit_possible[region]:
            eligible_total += awaiting_by_region[region]
        else:
            for b in SUB_BUCKETS:
                forced_totals[b] += awaiting_by_region[region] * forced_weights[b]
    eligible_weights = (
        {b: (FULL_SCALE_TOTALS[b] * scale - forced_totals[b]) / eligible_total for b in SUB_BUCKETS}
        if eligible_total else {b: 0.0 for b in SUB_BUCKETS}
    )

    matrix = []
    for i, region in enumerate(regions):
        count = awaiting_by_region[region]
        if transit_possible[region]:
            weights = eligible_weights
        else:
            forbidden.add((i, SUB_BUCKETS.index('transit')))
            weights = forced_weights
        matrix.append([count * weights[b] for b in SUB_BUCKETS])

    row_targets = [awaiting_by_region[r] for r in regions]
    result = reconcile_matrix(matrix, row_targets, col_targets, forbidden=forbidden)
    return {
        region: dict(zip(SUB_BUCKETS, row, strict=True))
        for region, row in zip(regions, result, strict=True)
    }
