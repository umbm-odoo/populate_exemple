"""Section 4: picking a specific customer/supplier for a given slot.

"Select customers by destination bucket first, then by eligible customer
within that bucket. Customer counts do not determine transaction shares."
Selection is uniform-with-replacement among the eligible pool (repeat
orders from the same customer are expected and fine) using the run's seeded
Random so results are reproducible.
"""
from __future__ import annotations

import random

from .config import CORPORATE_SHARE, PRIMARY_SUPPLIER_SHARE
from .eligibility import Party


def eligible_pool(parties: dict[str, Party], *, bucket: str | None, year: int) -> list[Party]:
    pool = [p for p in parties.values() if p.eligible_from.year <= year]
    if bucket is not None:
        pool = [p for p in pool if p.bucket == bucket]
    pool.sort(key=lambda p: p.xmlid)  # stable order before any RNG draw
    return pool


def pick_customer(customers: dict[str, Party], *, bucket: str | None, year: int, rng: random.Random) -> Party:
    """Pick a customer, biasing toward the 20% corporate share only where both
    individuals and companies are actually eligible (spec's own caveat) -
    otherwise whichever type exists is used exclusively (true before 2021,
    when every Phase 1 customer happens to be a company).

    ``bucket=None`` picks from every eligible customer regardless of
    destination region - used for CRM-only records with no shipping
    destination of their own (unconverted leads, opportunities lost before
    ever reaching a quotation).
    """
    pool = eligible_pool(customers, bucket=bucket, year=year)
    if not pool:
        raise ValueError(f"No eligible customer for bucket={bucket!r} year={year}.")

    companies = [p for p in pool if p.is_company]
    individuals = [p for p in pool if not p.is_company]
    if companies and individuals:
        sub_pool = companies if rng.random() < CORPORATE_SHARE else individuals
    else:
        sub_pool = companies or individuals
    return rng.choice(sub_pool)


def pick_supplier(
    suppliers: dict[str, Party],
    supplierinfo_for_product: list[dict],
    *,
    year: int,
    rng: random.Random,
) -> dict:
    """Pick a supplierinfo entry (dict with partner_xmlid/price/delay) for a component/resale product.

    70% primary (sequence 1) / 30% among the eligible alternatives (spec
    section 7), never a Phase 2 supplier before its eligibility date.
    """
    eligible = [
        si for si in supplierinfo_for_product
        if suppliers[si['partner_xmlid']].eligible_from.year <= year
    ]
    if not eligible:
        raise ValueError(f"No eligible supplier for product before {year}.")

    eligible.sort(key=lambda si: si['sequence'])
    primary, alternatives = eligible[0], eligible[1:]

    if not alternatives or rng.random() < PRIMARY_SUPPLIER_SHARE:
        return primary
    return rng.choice(alternatives)
