"""Custom Populate generators driving the pilot blueprint from a precomputed plan.

The plan (``populate/data/pilot_plan.json``) is built entirely in plain
Python (see ``planner/``) so every quota, date, and business rule can be
unit-tested without touching Odoo. These generators just hand that
already-resolved data to Populate's ``<create>``/``<function>`` blocks, one
row at a time, as a plain dict - the blueprint XML then pulls individual
fields out of that row with ordinary ``eval`` expressions
(``_row['customer_xmlid']`` etc.) instead of needing one generator class per
field.

Two read patterns are needed:

- ``oxp.subset_row``: for ``<create>`` blocks. Rows are generated fresh in
  the same order they'll be consumed (record 0, 1, 2, ...), so a plain
  per-generator counter into the named subset list is enough.
- ``oxp.by_name_row``: for ``<function>`` blocks acting on records Populate
  didn't create directly (a cascaded purchase order, picking, MO, or
  invoice). These must be looked up by the *record's own* identifying field
  (name / origin / invoice_origin) rather than by position, because a
  domain- or ref-scoped batch doesn't necessarily line up positionally with
  any one plan subset.
"""
from __future__ import annotations

import json
from pathlib import Path

from odoo.addons.populate.generators.generator import Generator

PLAN_PATH = Path(__file__).parent / 'populate' / 'data' / 'pilot_plan.json'

_ORDER_NAME_FIELD = {
    # sale.order and crm.lead are always targeted by their own populate ref
    # (delivered_orders, won_leads, ...) with no further domain, so
    # SubsetRow's positional order already matches - only records Populate
    # didn't create directly (cascaded from confirming a sale order) need
    # this name-based lookup.
    'purchase.order': 'origin',
    'stock.picking': 'origin',
    'mrp.production': 'origin',
    'account.move': 'invoice_origin',
}

_plan_cache: dict | None = None


def _deserialise(value):
    """Unwrap the ``{'__type__': ..., 'value': ...}`` markers back to plain
    ISO strings (not real ``date``/``datetime`` objects).

    Populate's cross-boundary safety check (``check_eval_args``) only allows
    ``None``/``bool``/``int``/``float``/``str``/``bytes``/recordsets through
    an ``eval`` dependency or a ``<function>`` argument - a raw
    ``datetime.date``/``datetime.datetime`` is rejected, dict-nested or not.
    Every model method that receives one of these strings as an argument is
    responsible for parsing it back (see ``models/*.py``)."""
    if isinstance(value, dict) and set(value) == {'__type__', 'value'}:
        return value['value']
    if isinstance(value, dict):
        return {k: _deserialise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deserialise(v) for v in value]
    return value


def get_plan() -> dict:
    global _plan_cache
    if _plan_cache is None:
        with PLAN_PATH.open() as f:
            raw = json.load(f)
        _plan_cache = _deserialise(raw)
    return _plan_cache


class SubsetRow(Generator):
    """Yield successive rows of a named plan subset, in file order.

    Only valid for ``<create>`` blocks whose ``count`` matches the subset's
    length exactly - one row per generated record, in lockstep.
    """
    name = 'oxp.subset_row'
    allowed_on = ('value',)

    def __init__(self, subset: str, **kwargs):
        super().__init__(**kwargs)
        self.rows = get_plan()['subsets'][subset]
        self.counter = 0

    @classmethod
    def convert_to_kwargs(cls, attrs):
        kwargs = super().convert_to_kwargs(attrs)
        kwargs['subset'] = attrs['subset']
        return kwargs

    def _next(self, known_vals):
        row = self.rows[self.counter]
        self.counter += 1
        return row


class ByNameRow(Generator):
    """Yield the plan row matching each target record's own name/origin field.

    Used by ``<function>`` blocks so a domain- or ref-scoped batch of
    cascaded documents (a PO, picking, MO, or invoice) can still recover
    "which order was this created for", regardless of where it falls
    positionally within the batch.
    """
    name = 'oxp.by_name_row'
    allowed_on = ('value',)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        by_name = get_plan()['by_name']
        records = self.job._get_target_records()
        self.rows = [by_name[self._order_name(record)] for record in records]
        self.counter = 0

    @staticmethod
    def _order_name(record):
        """A vendor receipt's own ``origin`` is the purchase order's name
        (e.g. ``P00028``), not the sale order it was ultimately bought for -
        Odoo stamps incoming pickings with the PO they fulfil, so the sale
        order name has to be read one hop further, off the linked PO."""
        if record._name == 'stock.picking' and record.purchase_id:
            name_field, source = 'origin', record.purchase_id
        else:
            name_field, source = _ORDER_NAME_FIELD[record._name], record
        return getattr(source, name_field).split(',')[0].strip()

    def _next(self, known_vals):
        row = self.rows[self.counter]
        self.counter += 1
        return row
