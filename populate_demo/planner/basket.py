"""Section 7: basket assembly - line count, product mix, quantities, discount.

Baskets cannot repeat a product, so the family/product mix is only a
statistical target, not an exact per-line quota (spec's own wording).
"""
from __future__ import annotations

import random
from datetime import date

from .config import (
    BASE_FAMILY_WEIGHTS,
    CHOCOGRENOUILLES_MULTIPLIER,
    CHOCOGRENOUILLES_PRODUCT,
    CHOCOGRENOUILLES_WINDOW,
    CORPORATE_DISCOUNT,
    CORPORATE_QTY_RANGE,
    FAMILY_PRODUCTS,
    INDIVIDUAL_DISCOUNT,
    INDIVIDUAL_QTY_RANGE,
    LINE_COUNT_WEIGHTS,
)


def sample_line_count(rng: random.Random) -> int:
    counts = list(LINE_COUNT_WEIGHTS)
    weights = list(LINE_COUNT_WEIGHTS.values())
    return rng.choices(counts, weights=weights, k=1)[0]


def _pick_product(family: str, used_products: set[str], rng: random.Random) -> str | None:
    """Equal chance between a family's two products; None if both are already used."""
    candidates = [p for p in FAMILY_PRODUCTS[family] if p not in used_products]
    if not candidates:
        return None
    return rng.choice(candidates)


def build_basket(
    *, lead_family: str, line_count: int, is_company: bool, order_date: date, rng: random.Random,
    allowed_families: tuple[str, ...] | None = None,
) -> list[dict]:
    """Return a list of {product_xmlid, family, qty} lines, distinct products, lead family first.

    :param allowed_families: Restrict every line to these families - used for
        outstanding orders awaiting a single supply type (a purely
        "awaiting purchased goods" order shouldn't also carry a manufactured
        line that's free to finish on its own).
    """
    qty_ranges = CORPORATE_QTY_RANGE if is_company else INDIVIDUAL_QTY_RANGE
    lines: list[dict] = []
    used_products: set[str] = set()

    candidate_families = list(allowed_families) if allowed_families else list(BASE_FAMILY_WEIGHTS)
    families_in_order = [lead_family]
    remaining_weights = [BASE_FAMILY_WEIGHTS[f] for f in candidate_families]
    while len(families_in_order) < line_count:
        family = rng.choices(candidate_families, weights=remaining_weights, k=1)[0]
        families_in_order.append(family)

    for family in families_in_order:
        product = _pick_product(family, used_products, rng)
        if product is None:
            # Every product in this family is already in the basket - fall
            # back to any (allowed) family with a free product instead of
            # repeating one.
            other_families = [f for f in candidate_families if f != family]
            rng.shuffle(other_families)
            for other in other_families:
                product = _pick_product(other, used_products, rng)
                if product is not None:
                    family = other
                    break
        if product is None:
            break  # basket already covers every distinct product allowed here

        low, high = qty_ranges[family]
        qty = rng.randint(low, high)
        used_products.add(product)
        lines.append({'product_xmlid': product, 'family': family, 'qty': qty})

    if CHOCOGRENOUILLES_WINDOW[0] <= order_date <= CHOCOGRENOUILLES_WINDOW[1]:
        for line in lines:
            if line['product_xmlid'] == CHOCOGRENOUILLES_PRODUCT:
                line['qty'] *= CHOCOGRENOUILLES_MULTIPLIER

    return lines


def discount_for(is_company: bool) -> float:
    return CORPORATE_DISCOUNT if is_company else INDIVIDUAL_DISCOUNT


def has_chocogrenouilles_spike(lines: list[dict], order_date: date) -> bool:
    return (
        CHOCOGRENOUILLES_WINDOW[0] <= order_date <= CHOCOGRENOUILLES_WINDOW[1]
        and any(line['product_xmlid'] == CHOCOGRENOUILLES_PRODUCT for line in lines)
    )
