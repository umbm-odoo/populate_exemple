"""Spec section 4: customer/supplier eligibility and destination buckets.

Builds the "persistent external-ID-to-eligibility mapping" the spec asks
for, from the master-data snapshot (``planner/data/snapshot.json``, see
``export_snapshot.py``). Eligibility dates are generation controls only -
they are never written to any Odoo field.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .config import (
    AMERICAS_CODES,
    APAC_CODES,
    EUROPE_CODES,
    PHASE1_ELIGIBLE_FROM,
    PHASE2_COHORT_SIZES,
    PHASE2_SUPPLIER_ELIGIBLE_FROM,
    UK_CODE,
)

SNAPSHOT_PATH = Path(__file__).parent / 'data' / 'snapshot.json'


def bucket_for_country(country_code: str | None) -> str | None:
    """Return 'uk' / 'other_europe' / 'americas' / 'apac', or None if the
    country is outside the three destination regions (spec section 5: such
    customers are preserved but excluded from generated sales)."""
    if country_code == UK_CODE:
        return 'uk'
    if country_code in EUROPE_CODES:
        return 'other_europe'
    if country_code in AMERICAS_CODES:
        return 'americas'
    if country_code in APAC_CODES:
        return 'apac'
    return None


@dataclass(frozen=True)
class Party:
    xmlid: str
    name: str
    country_code: str | None
    is_company: bool
    phase: int
    eligible_from: date
    bucket: str | None  # None for suppliers (spec: supplier countries may remain global)


_IMPORT_PREFIX = '__import__.'


def _strip_import_prefix(value):
    """Drop the '__import__.' module prefix; xmlids from other modules (e.g.
    'crm.stage_lead1', a leftover default we filter out separately) are left
    alone since they're never meant to be re-qualified the same way."""
    if isinstance(value, str) and value.startswith(_IMPORT_PREFIX):
        return value[len(_IMPORT_PREFIX):]
    if isinstance(value, list):
        return [_strip_import_prefix(v) for v in value]
    return value


_XMLID_FIELDS = ('xmlid', 'product_xmlid', 'partner_xmlid', 'user_xmlid', 'member_xmlids',
                 'finished_xmlid', 'component_xmlid')


def load_snapshot() -> dict:
    with SNAPSHOT_PATH.open() as f:
        raw = json.load(f)
    for records in raw.values():
        for record in records:
            for field in _XMLID_FIELDS:
                if field in record:
                    record[field] = _strip_import_prefix(record[field])
    return raw


def _assign_phase2_cohorts(phase2_customers: list[dict]) -> dict[str, date]:
    """Deterministically slice Phase 2 customers into onboarding cohorts."""
    ordered = sorted(phase2_customers, key=lambda c: c['xmlid'])
    total = sum(PHASE2_COHORT_SIZES.values())
    if len(ordered) != total:
        raise ValueError(f"Expected {total} Phase 2 customers, snapshot has {len(ordered)}.")

    eligible_from = {}
    index = 0
    for year in sorted(PHASE2_COHORT_SIZES):
        size = PHASE2_COHORT_SIZES[year]
        for customer in ordered[index:index + size]:
            eligible_from[customer['xmlid']] = date(year, 1, 1)
        index += size
    return eligible_from


def build_customers(snapshot: dict) -> dict[str, Party]:
    phase1 = [c for c in snapshot['customers'] if c['phase'] == 1]
    phase2 = [c for c in snapshot['customers'] if c['phase'] == 2]
    cohort_dates = _assign_phase2_cohorts(phase2)

    parties = {}
    for c in phase1:
        parties[c['xmlid']] = Party(
            xmlid=c['xmlid'], name=c['name'], country_code=c['country_code'],
            is_company=c['is_company'], phase=1, eligible_from=PHASE1_ELIGIBLE_FROM,
            bucket=bucket_for_country(c['country_code']),
        )
    for c in phase2:
        parties[c['xmlid']] = Party(
            xmlid=c['xmlid'], name=c['name'], country_code=c['country_code'],
            is_company=c['is_company'], phase=2, eligible_from=cohort_dates[c['xmlid']],
            bucket=bucket_for_country(c['country_code']),
        )
    return parties


def build_suppliers(snapshot: dict) -> dict[str, Party]:
    parties = {}
    for s in snapshot['suppliers']:
        eligible_from = PHASE1_ELIGIBLE_FROM if s['phase'] == 1 else PHASE2_SUPPLIER_ELIGIBLE_FROM
        parties[s['xmlid']] = Party(
            xmlid=s['xmlid'], name=s['name'], country_code=s['country_code'],
            is_company=s['is_company'], phase=s['phase'], eligible_from=eligible_from,
            bucket=None,
        )
    return parties
