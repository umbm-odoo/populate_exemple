"""Spec section 8: CRM linkage and opportunity outcome quotas.

Every stratum in the spec's CRM numbers works out to exactly 70% linkage
(1,400/2,000 confirmed-then-cancelled, 5,600/8,000 quotation-cancellations,
58,100/83,000 completed, 1,400/2,000 awaiting - all exactly 0.7). That 70%
is a *global* target across all years, so splitting each year's count by
70% independently (which nearly-but-not-exactly divides most years) would
drift from the exact global total by the time eleven years of rounding
accumulate. Each split is instead resolved with ``reconcile_matrix``: rows
are years (whose totals are already fixed by ``quotas.annual_outcome_quotas``),
columns are the two-way split, and the column totals are pinned to the
spec's exact global numbers.
"""
from __future__ import annotations

from .rounding import reconcile_matrix

LINK_RATE = 0.70

# Spec section 3: how the 10,000 cancellations split (global, not per-year).
CANCEL_BEFORE_CONFIRM_SHARE = 0.80  # 8,000 / 10,000
CANCEL_AFTER_CONFIRM_SHARE = 0.20  # 2,000 / 10,000

# Spec section 8: additional CRM volumes at full (100,000-order) scale.
FULL_SCALE_EXTRA = {
    'lost_no_quote': 40_000,
    'open_no_quote': 6_000,
    'unconverted_leads': 4_000,
}


def _two_way_split(per_year_totals: dict[int, int], share_a: float) -> dict[int, tuple[int, int]]:
    """Split each year's total into (a, b) so sum(a) matches round(grand_total * share_a) exactly."""
    years = sorted(per_year_totals)
    grand_total = sum(per_year_totals.values())
    target_a = round(grand_total * share_a)
    target_b = grand_total - target_a

    matrix = [[per_year_totals[y] * share_a, per_year_totals[y] * (1 - share_a)] for y in years]
    row_targets = [per_year_totals[y] for y in years]
    result = reconcile_matrix(matrix, row_targets, [target_a, target_b])
    return {y: (row[0], row[1]) for y, row in zip(years, result, strict=True)}


def linked_counts_per_year(annual_outcomes: dict[int, dict[str, int]]) -> dict[int, dict[str, int]]:
    """CRM-linked / unlinked order counts per year, for each outcome.

    ``cancelled`` is first split into "before confirmation" (a lost
    quotation if linked) and "after confirmation" (a won opportunity, later
    cancelled, if linked), since those follow different CRM outcomes.
    """
    years = sorted(annual_outcomes)

    cancel_before_after = _two_way_split(
        {y: annual_outcomes[y]['cancelled'] for y in years}, CANCEL_BEFORE_CONFIRM_SHARE,
    )

    delivered_split = _two_way_split({y: annual_outcomes[y]['delivered'] for y in years}, LINK_RATE)
    awaiting_split = _two_way_split({y: annual_outcomes[y]['awaiting'] for y in years}, LINK_RATE)
    open_split = _two_way_split({y: annual_outcomes[y]['open'] for y in years}, LINK_RATE)
    cancel_before_totals = {y: cancel_before_after[y][0] for y in years}
    cancel_after_totals = {y: cancel_before_after[y][1] for y in years}
    cancel_before_split = _two_way_split(cancel_before_totals, LINK_RATE)
    cancel_after_split = _two_way_split(cancel_after_totals, LINK_RATE)

    return {
        y: {
            'delivered_linked': delivered_split[y][0],
            'delivered_unlinked': delivered_split[y][1],
            'awaiting_linked': awaiting_split[y][0],
            'awaiting_unlinked': awaiting_split[y][1],
            'cancelled_before_confirm_total': cancel_before_totals[y],
            'cancelled_before_confirm_linked': cancel_before_split[y][0],
            'cancelled_before_confirm_unlinked': cancel_before_split[y][1],
            'cancelled_after_confirm_total': cancel_after_totals[y],
            'cancelled_after_confirm_linked': cancel_after_split[y][0],
            'cancelled_after_confirm_unlinked': cancel_after_split[y][1],
            'open_linked': open_split[y][0],
            'open_unlinked': open_split[y][1],
        }
        for y in years
    }


def extra_crm_volumes(scale: float) -> dict[str, int]:
    """Unlinked CRM records (lost/open opportunities and leads with no quotation)."""
    result = {}
    for key, full_value in FULL_SCALE_EXTRA.items():
        scaled = full_value * scale
        rounded = round(scaled)
        if abs(rounded - scaled) > 1e-6:
            raise ValueError(f"Scale {scale} does not divide {key} ({full_value}) evenly.")
        result[key] = rounded
    return result
