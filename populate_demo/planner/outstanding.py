"""Spec section 3: the 2,000 outstanding confirmed orders' supply posture.

1,000 in transit to a regional warehouse / 600 awaiting production in
Belgium / 400 awaiting purchased goods, at full scale. "In transit" only
makes sense for a region actually served by a regional warehouse (UK, or
Americas/APAC from 2021) - "other Europe" is always served directly from
Belgium (spec section 6), so it can never be in the transit sub-bucket.
"""
from __future__ import annotations

from .rounding import reconcile_matrix

SUB_BUCKETS = ('transit', 'production', 'purchase')
FULL_SCALE_TOTALS = {'transit': 1000, 'production': 600, 'purchase': 400}


def warehouse_for(region: str, year: int) -> str:
    """Fulfilling warehouse code for a destination region in a given year."""
    if region == 'uk':
        return 'UK'
    if region == 'other_europe':
        return 'BE'
    if region == 'americas':
        return 'US' if year >= 2021 else 'BE'
    if region == 'apac':
        return 'SG' if year >= 2021 else 'BE'
    raise ValueError(f"Unknown region {region!r}")


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
    matrix = []
    for i, region in enumerate(regions):
        count = awaiting_by_region[region]
        transit_possible = warehouse_for(region, year) != 'BE'
        if not transit_possible:
            forbidden.add((i, SUB_BUCKETS.index('transit')))
            weights = {'transit': 0.0, 'production': 0.6, 'purchase': 0.4}
        else:
            total_weight = sum(FULL_SCALE_TOTALS.values())
            weights = {b: FULL_SCALE_TOTALS[b] / total_weight for b in SUB_BUCKETS}
        matrix.append([count * weights[b] for b in SUB_BUCKETS])

    row_targets = [awaiting_by_region[r] for r in regions]
    result = reconcile_matrix(matrix, row_targets, col_targets, forbidden=forbidden)
    return {
        region: dict(zip(SUB_BUCKETS, row, strict=True))
        for region, row in zip(regions, result, strict=True)
    }
