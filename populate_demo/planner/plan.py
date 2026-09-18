"""Assembles the full per-order plan: every field an order needs, resolved.

Orchestrates every other planner module in the sequence spec section 13
describes: quotas -> demand/event schedules -> per-order records. Produces
plain dicts (JSON-serialisable) rather than Odoo records, so the whole
allocation can be inspected and unit-tested without touching a database.
"""
from __future__ import annotations

import random
from datetime import datetime

from . import attribution, basket, seasonal as cal, crm, outstanding, parties, quotas, regions, schedule
from .config import CUTOFF, OPEN_QUOTATION_WINDOW_DAYS, OUTSTANDING_WINDOW_DAYS, SCENARIO_START
from .eligibility import build_customers, build_suppliers, load_snapshot


def _line_is_manufactured(product_xmlid: str) -> bool:
    return product_xmlid in ('prod_wand_holly', 'prod_wand_elder', 'prod_felix', 'prod_polyjuice')


def _schedule_delivered_or_outstanding(
    order: dict, *, region: str, warehouse: str, year: int, rng: random.Random, must_complete: bool,
    suppliers: dict, supplierinfo_by_product: dict,
) -> None:
    """Fill in confirm -> (procurement) -> (logistics) -> delivery -> invoice -> payment.

    :param must_complete: True for 'delivered' orders, whose whole chain must
        land before the scenario cutoff (resampling the quotation date if
        it doesn't - spec: "sample only feasible timelines ... rather than
        clipping"). False for outstanding orders, whose chain is
        deliberately cut short at ``order['sub_bucket']``.
    """
    max_attempts = 200
    for _attempt in range(max_attempts):
        confirm_date = schedule.schedule_confirm(order['quotation_date'], rng)
        if confirm_date >= CUTOFF:
            order['quotation_date'] = _resample_quotation(order, year, rng)
            continue

        line_procurement = []
        for line in order['lines']:
            is_manufactured = _line_is_manufactured(line['product_xmlid'])
            procurement = schedule.schedule_line_procurement(confirm_date, is_manufactured=is_manufactured, rng=rng)
            if not is_manufactured:
                # Spec section 7: 70% primary / 30% eligible alternative supplier.
                seller = parties.pick_supplier(
                    suppliers, supplierinfo_by_product[line['product_xmlid']], year=year, rng=rng,
                )
                procurement['supplier_xmlid'] = seller['partner_xmlid']
                procurement['price'] = seller['price']
            line_procurement.append(procurement)
        goods_available = max(p['goods_available_date'] for p in line_procurement)

        if not must_complete and order['sub_bucket'] in ('purchase', 'production'):
            # Awaiting purchased goods / production: whatever each line has
            # already completed (a manufactured line might finish while a
            # purchased sibling line is still on order) must still fall
            # before the cutoff; the overall order simply never reaches
            # dispatch/delivery.
            completed_dates = [d for p in line_procurement for d in p.values() if isinstance(d, datetime)]
            if any(d >= CUTOFF for d in completed_dates):
                order['quotation_date'] = _resample_quotation(order, year, rng)
                continue
            order['confirm_date'] = confirm_date
            order['lines_procurement'] = line_procurement
            _aggregate_procurement_dates(order, line_procurement)
            return

        logistics = schedule.schedule_logistics(goods_available, region=region, warehouse=warehouse, rng=rng)

        if not must_complete and order['sub_bucket'] == 'transit':
            # In transit: dispatch completed, regional receipt/delivery not yet.
            dispatch_date = logistics.get('dispatch_date')
            if dispatch_date is not None and dispatch_date >= CUTOFF:
                order['quotation_date'] = _resample_quotation(order, year, rng)
                continue
            order['confirm_date'] = confirm_date
            order['lines_procurement'] = line_procurement
            order['dispatch_date'] = dispatch_date
            _aggregate_procurement_dates(order, line_procurement)
            return

        delivery_actual = schedule.apply_delivery_delay(logistics['delivery_promised_date'], rng)
        invoice_date = schedule.schedule_invoice(delivery_actual, rng)
        payment_date, unpaid = schedule.schedule_payment(invoice_date, rng)

        events_ok = (
            delivery_actual < CUTOFF
            and datetime.combine(invoice_date, datetime.min.time()) < CUTOFF
            and (payment_date is None or datetime.combine(payment_date, datetime.min.time()) < CUTOFF or unpaid)
        )
        if events_ok:
            order['confirm_date'] = confirm_date
            order['lines_procurement'] = line_procurement
            order.update(logistics)
            order['delivery_actual_date'] = delivery_actual
            order['invoice_date'] = invoice_date
            order['payment_date'] = payment_date
            order['unpaid'] = unpaid
            _aggregate_procurement_dates(order, line_procurement)
            return

        # Resample the quotation date (same family/year) and try the whole chain again.
        order['quotation_date'] = _resample_quotation(order, year, rng)
    raise RuntimeError(f"Could not schedule order within cutoff after {max_attempts} attempts.")


def _aggregate_procurement_dates(order: dict, line_procurement: list[dict]) -> None:
    """Roll multiple lines' independently-sampled procurement dates into one
    per-order date per step, so the blueprint can act on "this order's
    purchase order(s)" / "this order's MO(s)" with a single date rather than
    needing to know which specific line a cascaded PO or MO came from.

    All lines needing the same step are treated as arriving together, using
    the slowest (max) line for each date - consistent with
    ``schedule_logistics`` already waiting for the max of
    ``goods_available_date`` before dispatch/delivery.
    """
    po_confirms = [p['po_confirm_date'] for p in line_procurement if 'po_confirm_date' in p]
    po_receives = [p['po_receive_date'] for p in line_procurement if 'po_receive_date' in p]
    mo_finishes = [p['mo_finish_date'] for p in line_procurement if 'mo_finish_date' in p]
    if po_confirms:
        order['po_confirm_date'] = max(po_confirms)
    if po_receives:
        order['po_receive_date'] = max(po_receives)
    if mo_finishes:
        order['mo_start_date'] = order['confirm_date']
        order['mo_finish_date'] = max(mo_finishes)


def _resample_quotation(order: dict, year: int, rng: random.Random) -> datetime:
    max_date = CUTOFF.date() if year == 2026 else None
    return cal.sample_date_in_year(year, order['lead_family'], rng, max_date=max_date)


def build_plan(scale: float, seed: int) -> list[dict]:
    rng = random.Random(seed)
    snapshot = load_snapshot()
    customers = build_customers(snapshot)
    suppliers = build_suppliers(snapshot)
    supplierinfo_by_product: dict[str, list[dict]] = {}
    for si in snapshot['supplierinfo']:
        supplierinfo_by_product.setdefault(si['product_xmlid'], []).append(si)

    annual = quotas.annual_outcome_quotas(scale)
    region_by_year = regions.region_counts_per_year(annual)
    # Computed once across every year, not per year: each split's column
    # targets are pinned to the exact multi-year grand total (e.g. 581
    # linked-delivered orders overall), so splitting year by year here would
    # silently reintroduce the same cross-year rounding drift that
    # `reconcile_matrix` exists to avoid (see quotas.py / crm.py).
    crm_by_year = crm.linked_counts_per_year(annual)

    orders: list[dict] = []
    order_seq = 0

    for year in sorted(annual):
        outcomes = annual[year]
        confirmed_split = regions.split_regions_two_way(
            region_by_year[year]['confirmed'], outcomes['delivered'], outcomes['awaiting'],
            'delivered', 'awaiting',
        )
        crm_year = crm_by_year[year]
        cancelled_split = regions.split_regions_two_way(
            region_by_year[year]['cancelled'],
            crm_year['cancelled_before_confirm_total'], crm_year['cancelled_after_confirm_total'],
            'before_confirm', 'after_confirm',
        )

        # ---- delivered ----
        delivered_by_region = {r: confirmed_split[r]['delivered'] for r in confirmed_split}
        delivered_linked_split = regions.split_regions_two_way(
            delivered_by_region, crm_year['delivered_linked'], crm_year['delivered_unlinked'], 'linked', 'unlinked',
        )
        for region, counts in delivered_linked_split.items():
            for linked in (True, False):
                for _ in range(counts['linked' if linked else 'unlinked']):
                    order_seq += 1
                    orders.append(_new_order(
                        order_seq, year, 'delivered', region, linked, rng, customers,
                    ))

        # ---- awaiting (outstanding) ----
        awaiting_by_region = {r: confirmed_split[r]['awaiting'] for r in confirmed_split}
        if sum(awaiting_by_region.values()):
            awaiting_linked_split = regions.split_regions_two_way(
                awaiting_by_region, crm_year['awaiting_linked'], crm_year['awaiting_unlinked'], 'linked', 'unlinked',
            )
            sub_buckets = outstanding.outstanding_sub_buckets(awaiting_by_region, year, scale)
            for region in awaiting_by_region:
                remaining_linked = awaiting_linked_split[region]['linked']
                remaining_unlinked = awaiting_linked_split[region]['unlinked']
                for sub_bucket, count in sub_buckets[region].items():
                    for _ in range(count):
                        linked = remaining_linked > 0 and (remaining_unlinked == 0 or rng.random() < 0.5)
                        if linked:
                            remaining_linked -= 1
                        else:
                            remaining_unlinked -= 1
                        order_seq += 1
                        orders.append(_new_order(
                            order_seq, year, 'awaiting', region, linked, rng, customers, sub_bucket=sub_bucket,
                        ))

        # ---- cancelled (before/after confirmation) ----
        for outcome_key, total_key, linked_key, unlinked_key in (
            ('cancelled_before_confirm', 'before_confirm', 'cancelled_before_confirm_linked', 'cancelled_before_confirm_unlinked'),
            ('cancelled_after_confirm', 'after_confirm', 'cancelled_after_confirm_linked', 'cancelled_after_confirm_unlinked'),
        ):
            by_region = {r: cancelled_split[r][total_key] for r in cancelled_split}
            linked_split = regions.split_regions_two_way(
                by_region, crm_year[linked_key], crm_year[unlinked_key], 'linked', 'unlinked',
            )
            for region, counts in linked_split.items():
                for linked in (True, False):
                    for _ in range(counts['linked' if linked else 'unlinked']):
                        order_seq += 1
                        orders.append(_new_order(
                            order_seq, year, outcome_key, region, linked, rng, customers,
                        ))

        # ---- open quotations ----
        open_by_region = region_by_year[year]['open']
        if sum(open_by_region.values()):
            open_linked_split = regions.split_regions_two_way(
                open_by_region, crm_year['open_linked'], crm_year['open_unlinked'], 'linked', 'unlinked',
            )
            for region, counts in open_linked_split.items():
                for linked in (True, False):
                    for _ in range(counts['linked' if linked else 'unlinked']):
                        order_seq += 1
                        orders.append(_new_order(
                            order_seq, year, 'open', region, linked, rng, customers,
                        ))

    # ---- schedule dates and finish assembly for every order ----
    for order in orders:
        year = order['year']
        region = order['region']
        warehouse_wh = outstanding.warehouse_for(region, year)
        order['warehouse_code'] = warehouse_wh
        if order['outcome'] == 'open':
            pass  # quotation date only, already sampled within the last-60-day window
        elif order['outcome'] == 'cancelled_before_confirm':
            order['lost_reason'] = attribution.pick_lost_reason(rng)
            for _attempt in range(200):
                lost_date = schedule.add_days(order['quotation_date'], 1, 30, rng)
                if lost_date < CUTOFF:
                    order['lost_date'] = lost_date
                    break
                order['quotation_date'] = _resample_quotation(order, year, rng)
            else:
                raise RuntimeError(f"Order {order['id']}: could not schedule lost_date before cutoff.")
        elif order['outcome'] == 'cancelled_after_confirm':
            for _attempt in range(200):
                confirm_date = schedule.schedule_confirm(order['quotation_date'], rng)
                cancel_date = schedule.add_days(confirm_date, 1, 10, rng)
                if confirm_date < CUTOFF and cancel_date < CUTOFF:
                    order['confirm_date'] = confirm_date
                    order['cancel_date'] = cancel_date
                    break
                order['quotation_date'] = _resample_quotation(order, year, rng)
            else:
                raise RuntimeError(f"Order {order['id']}: could not schedule cancellation before cutoff.")
        elif order['outcome'] == 'awaiting':
            _schedule_delivered_or_outstanding(
                order, region=region, warehouse=warehouse_wh, year=year, rng=rng, must_complete=False,
                suppliers=suppliers, supplierinfo_by_product=supplierinfo_by_product,
            )
        elif order['outcome'] == 'delivered':
            _schedule_delivered_or_outstanding(
                order, region=region, warehouse=warehouse_wh, year=year, rng=rng, must_complete=True,
                suppliers=suppliers, supplierinfo_by_product=supplierinfo_by_product,
            )

        if order['linked']:
            order['lead_date'] = schedule.schedule_lead(order['quotation_date'], rng)

    return orders


def _uniform_recent_date(rng: random.Random, window_days: int) -> datetime:
    window_start = CUTOFF - schedule.timedelta(days=window_days)
    return window_start + schedule.timedelta(days=rng.randint(0, window_days - 1))


SUPPLY_ONLY_FAMILIES = {
    'purchase': ('brooms', 'consumables'),
    'production': ('wands', 'potions'),
}


def _new_order(seq, year, outcome, region, linked, rng, customers, sub_bucket=None):
    allowed_families = SUPPLY_ONLY_FAMILIES.get(sub_bucket)
    lead_family = rng.choice(allowed_families) if allowed_families else cal.sample_family(rng)

    if outcome == 'open':
        # Spec: open quotations stay within the last 60 days of the scenario.
        quotation_date = _uniform_recent_date(rng, OPEN_QUOTATION_WINDOW_DAYS)
    elif outcome == 'awaiting':
        # Spec: outstanding confirmed orders stay within the last 45 days.
        quotation_date = _uniform_recent_date(rng, OUTSTANDING_WINDOW_DAYS)
    else:
        max_date = CUTOFF.date() if year == 2026 else None
        quotation_date = cal.sample_date_in_year(year, lead_family, rng, max_date=max_date)

    customer = parties.pick_customer(customers, bucket=region, year=year, rng=rng)

    line_count = basket.sample_line_count(rng)
    lines = basket.build_basket(
        lead_family=lead_family, line_count=line_count, is_company=customer.is_company,
        order_date=quotation_date.date(), rng=rng, allowed_families=allowed_families,
    )

    team, user = attribution.pick_rep(rng)
    order = {
        'id': seq,
        'year': year,
        'outcome': outcome,
        'region': region,
        'sub_bucket': sub_bucket,
        'customer_xmlid': customer.xmlid,
        'is_company': customer.is_company,
        'quotation_date': quotation_date,
        'lead_family': lead_family,
        'lines': lines,
        'discount': basket.discount_for(customer.is_company),
        'team': team,
        'user': user,
        'linked': linked,
    }
    if linked:
        source, medium = attribution.pick_source(year, rng)
        order['source'] = source
        order['medium'] = medium
    return order
