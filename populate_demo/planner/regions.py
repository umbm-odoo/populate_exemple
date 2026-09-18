"""Combine the annual outcome quotas with the geographic split (section 5).

Confirmed orders (delivered + awaiting) get an exact per-year region quota.
Cancelled and open orders use "the same year's weights as a sampling
default" (spec section 5) rather than an independently-reconciled quota, so
they're allocated with the same largest-remainder shape but are explicitly
not pinned to any cross-year column total.
"""
from __future__ import annotations

from .quotas import REGIONS, geographic_quotas
from .rounding import reconcile_matrix


def region_counts_per_year(annual_outcomes: dict[int, dict[str, int]]) -> dict[int, dict[str, dict[str, int]]]:
    """For each year, region counts for 'confirmed' (delivered+awaiting), 'cancelled', and 'open'."""
    result = {}
    for year, outcomes in annual_outcomes.items():
        confirmed = outcomes['delivered'] + outcomes['awaiting']
        result[year] = {
            'confirmed': geographic_quotas(year, confirmed) if confirmed else dict.fromkeys(
                ('uk', 'other_europe', 'americas', 'apac'), 0,
            ),
            'cancelled': geographic_quotas(year, outcomes['cancelled']) if outcomes['cancelled'] else dict.fromkeys(
                ('uk', 'other_europe', 'americas', 'apac'), 0,
            ),
            'open': geographic_quotas(year, outcomes['open']) if outcomes['open'] else dict.fromkeys(
                ('uk', 'other_europe', 'americas', 'apac'), 0,
            ),
        }
    return result


def split_regions_two_way(
    region_counts: dict[str, int],
    target_a: int,
    target_b: int,
    label_a: str = 'a',
    label_b: str = 'b',
) -> dict[str, dict[str, int]]:
    """Split each region's count into two labelled parts matching known global totals.

    Used both for delivered-vs-awaiting (2026's "confirmed" bucket) and for
    cancelled-before-vs-after-confirmation, which are otherwise only known as
    year-level totals (``crm.linked_counts_per_year``) with no region
    breakdown of their own.
    """
    total = target_a + target_b
    if total == 0:
        return {region: {label_a: 0, label_b: 0} for region in region_counts}
    if target_b == 0:
        return {region: {label_a: count, label_b: 0} for region, count in region_counts.items()}

    regions = sorted(region_counts)
    matrix = [
        [region_counts[r] * target_a / total, region_counts[r] * target_b / total]
        for r in regions
    ]
    row_targets = [region_counts[r] for r in regions]
    result = reconcile_matrix(matrix, row_targets, [target_a, target_b])
    return {
        region: {label_a: row[0], label_b: row[1]}
        for region, row in zip(regions, result, strict=True)
    }
