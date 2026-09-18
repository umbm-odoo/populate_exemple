"""Authoring tool: build the pilot plan and write it as JSON for the blueprint to consume.

Not imported at runtime by Odoo - run this whenever the plan needs
regenerating (seed, scale, or planner logic changes), then commit the
resulting JSON alongside the blueprint that reads it.

The blueprint creates sale.order records in five separate bulk blocks (one
per outcome group, see populate/pilot.xml) so each group can be targeted by
its own populate ref later. Odoo assigns each one the next sequence number
(S00001, S00002, ...) strictly in creation order, so this script mirrors
that exact creation order when it assigns "order_name" - the blueprint's
generators look a record's own name/origin back up in ``by_name`` rather
than relying on position, but ``by_name`` still has to use the *real* names
Odoo will end up giving them.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from planner.plan import build_plan  # noqa: E402

OUTPUT_PATH = Path(__file__).parent.parent / 'populate' / 'data' / 'pilot_plan.json'
# Override with PILOT_SCALE=0.0012 for a fast ~120-order iteration cycle
# while debugging (still exercises every outcome/sub-bucket) - 0.01 is the
# real 1,000-order pilot and is what must be committed. PILOT_SEED lets a
# debugging run try a different random draw at the same scale.
SEED = int(os.environ.get('PILOT_SEED', 20260920))
SCALE = float(os.environ.get('PILOT_SCALE', 0.01))

# Creation order for the five sale.order bulk blocks - must match
# populate/pilot.xml's <create> block order exactly.
CREATION_GROUPS = [
    ('delivered_orders', 'delivered'),
    ('awaiting_orders', 'awaiting'),
    ('cancelled_before_orders', 'cancelled_before_confirm'),
    ('cancelled_after_orders', 'cancelled_after_confirm'),
    ('open_orders', 'open'),
]


def _serialise(value):
    if isinstance(value, datetime):
        return {'__type__': 'datetime', 'value': value.strftime('%Y-%m-%d %H:%M:%S')}
    if isinstance(value, date):
        return {'__type__': 'date', 'value': value.isoformat()}
    if isinstance(value, dict):
        return {k: _serialise(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialise(v) for v in value]
    return value


def _processing_sort_key(order: dict):
    """Chronological key used to order each group's *creation* sequence.

    FIFO consumption follows the id/creation order of the stock moves that
    confirming a sale order cascades into (see planner/README notes in
    plan.py), not any date field written after the fact. Bulk-processing an
    entire ref in one pass therefore stays close to true chronological order
    as long as the records were *created* in that order to begin with -
    which this sort gives us without needing to split the blueprint into
    per-year batches.
    """
    return order.get('confirm_date') or order['quotation_date']


def main():
    orders = build_plan(SCALE, SEED)

    subsets: dict[str, list[dict]] = {}
    by_name: dict[str, dict] = {}
    sequence = 0

    for subset_name, outcome in CREATION_GROUPS:
        group = sorted((o for o in orders if o['outcome'] == outcome), key=_processing_sort_key)
        subsets[subset_name] = group
        for order in group:
            sequence += 1
            order['order_name'] = f'S{sequence:05d}'
            by_name[order['order_name']] = order

    # CRM leads: created in three separate blocks so each can be targeted by
    # its own ref for _populate_win / _populate_lose / (open: untouched).
    subsets['won_leads'] = [
        o for o in orders if o['linked'] and o['outcome'] in ('delivered', 'awaiting', 'cancelled_after_confirm')
    ]
    subsets['lost_leads'] = [o for o in orders if o['linked'] and o['outcome'] == 'cancelled_before_confirm']
    subsets['open_leads'] = [o for o in orders if o['linked'] and o['outcome'] == 'open']

    all_lines = []
    for order in orders:
        for seq, line in enumerate(order['lines'], start=1):
            all_lines.append({
                'order_name': order['order_name'],
                'product_xmlid': line['product_xmlid'],
                'qty': line['qty'],
                'sequence': seq,
            })
    subsets['all_lines'] = all_lines

    payload = {
        'seed': SEED,
        'scale': SCALE,
        'by_name': _serialise(by_name),
        'subsets': _serialise(subsets),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open('w') as f:
        json.dump(payload, f, indent=1)

    print(f"Wrote {len(orders)} orders ({sum(len(v) for v in subsets.values())} subset rows) to {OUTPUT_PATH}")
    for name, group in subsets.items():
        print(f"  {name}: {len(group)}")


if __name__ == '__main__':
    main()
