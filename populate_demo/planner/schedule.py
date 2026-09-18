"""Section 10: the historical date contract for one order's full lifecycle.

Every date is derived from the one before it, in the order the spec's table
gives them - never sampled independently - so the chain stays causally
consistent by construction.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from .config import (
    CUSTOMER_NET_DAYS,
    CUTOFF,
    DIRECT_TRANSIT_DAYS,
    EU_DELIVERY_DAYS,
    FULL_SETTLEMENT_DAYS,
    INVOICE_AFTER_DELIVERY_DAYS,
    LATE_1_30_SHARE,
    LATE_DELIVERY_EXTRA_DAYS,
    LATE_DELIVERY_SHARE,
    ON_TIME_SHARE_2026,
    PRODUCTION_LEAD_DAYS,
    PURCHASE_CONFIRM_DELAY_DAYS,
    PURCHASE_LEAD_DAYS,
    REGIONAL_DELIVERY_DAYS,
    REGIONAL_TRANSIT_DAYS,
    UNPAID_SHARE,
    VENDOR_BILL_AFTER_RECEIPT_DAYS,
    VENDOR_NET_DAYS,
)


def _at(d: date, hour: int, minute: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute)


def add_days(dt: datetime, low: int, high: int, rng: random.Random) -> datetime:
    return dt + timedelta(days=rng.randint(low, high))


@dataclass
class OrderSchedule:
    quotation_date: datetime
    lead_date: datetime | None = None
    confirm_date: datetime | None = None
    lost_date: datetime | None = None
    po_request_date: datetime | None = None
    po_confirm_date: datetime | None = None
    po_receive_date: datetime | None = None
    mo_start_date: datetime | None = None
    mo_finish_date: datetime | None = None
    dispatch_date: datetime | None = None
    transit_receive_date: datetime | None = None
    delivery_promised_date: datetime | None = None
    delivery_actual_date: datetime | None = None
    invoice_date: date | None = None
    payment_date: date | None = None
    unpaid: bool = False


def schedule_lead(quotation_date: datetime, rng: random.Random) -> datetime:
    return add_days(quotation_date, -14, -1, rng)


def schedule_confirm(quotation_date: datetime, rng: random.Random) -> datetime:
    return add_days(quotation_date, 1, 10, rng)


def schedule_line_procurement(confirm_date: datetime, *, is_manufactured: bool, rng: random.Random) -> dict:
    """One line's own procurement/production dates and the date its goods become available in BE/Stock."""
    out: dict[str, datetime] = {}
    if is_manufactured:
        out['mo_start_date'] = confirm_date
        out['mo_finish_date'] = add_days(out['mo_start_date'], *PRODUCTION_LEAD_DAYS, rng)
        out['goods_available_date'] = out['mo_finish_date']
    else:
        out['po_request_date'] = confirm_date
        out['po_confirm_date'] = add_days(out['po_request_date'], *PURCHASE_CONFIRM_DELAY_DAYS, rng)
        out['po_receive_date'] = add_days(out['po_confirm_date'], *PURCHASE_LEAD_DAYS, rng)
        out['goods_available_date'] = out['po_receive_date']
    return out


def schedule_logistics(goods_available: datetime, *, region: str, warehouse: str, rng: random.Random) -> dict:
    """Shared dispatch/transit/delivery dates once every line's goods are available in BE/Stock.

    ``warehouse`` is 'BE' for the home market and for pre-2021 direct
    international sales (see ``outstanding.warehouse_for``).
    """
    out: dict[str, datetime] = {}
    if warehouse == 'BE':
        out['delivery_promised_date'] = add_days(goods_available, *EU_DELIVERY_DAYS, rng) \
            if region in ('uk', 'other_europe') \
            else add_days(goods_available, *DIRECT_TRANSIT_DAYS[region], rng)
    else:
        out['dispatch_date'] = goods_available
        out['transit_receive_date'] = add_days(out['dispatch_date'], *REGIONAL_TRANSIT_DAYS[region], rng)
        delivery_days = EU_DELIVERY_DAYS if region == 'uk' else REGIONAL_DELIVERY_DAYS
        out['delivery_promised_date'] = add_days(out['transit_receive_date'], *delivery_days, rng)
    return out


def apply_delivery_delay(promised: datetime, rng: random.Random) -> datetime:
    if rng.random() < LATE_DELIVERY_SHARE:
        return add_days(promised, *LATE_DELIVERY_EXTRA_DAYS, rng)
    return promised


def schedule_invoice(delivery_actual: datetime, rng: random.Random) -> date:
    return add_days(delivery_actual, *INVOICE_AFTER_DELIVERY_DAYS, rng).date()


def schedule_payment(invoice_date: date, rng: random.Random, *, net_days: int = CUSTOMER_NET_DAYS) -> tuple[date | None, bool]:
    """Returns (payment_date, unpaid). ``payment_date`` is None only when ``unpaid``.

    Shared by customer payments (``net_days=CUSTOMER_NET_DAYS``, the default)
    and vendor payments (``net_days=VENDOR_NET_DAYS``) - spec section 11's
    85%/10%/5% on-time/late/unpaid settlement split for 2026 documents isn't
    stated separately per side, only the net terms differ.
    """
    due_date = invoice_date + timedelta(days=net_days)
    is_2026_document = invoice_date.year == 2026

    if not is_2026_document:
        # Full settlement within 90 days for anything issued before 2026.
        pay_day_offset = rng.randint(0, FULL_SETTLEMENT_DAYS)
        return invoice_date + timedelta(days=pay_day_offset), False

    roll = rng.random()
    if roll < ON_TIME_SHARE_2026:
        pay_date = invoice_date + timedelta(days=rng.randint(0, net_days))
    elif roll < ON_TIME_SHARE_2026 + LATE_1_30_SHARE:
        pay_date = due_date + timedelta(days=rng.randint(1, 30))
    else:
        return None, True

    if pay_date >= CUTOFF.date():
        return None, True  # sampled payment falls after cutoff: unpaid at cutoff
    return pay_date, False


def schedule_vendor_bill(po_receive_date: datetime, rng: random.Random) -> date:
    """Vendor bill date: receipt date or up to 5 days later (spec section 10)."""
    return add_days(po_receive_date, *VENDOR_BILL_AFTER_RECEIPT_DAYS, rng).date()


def schedule_vendor_payment(bill_date: date, rng: random.Random) -> tuple[date | None, bool]:
    return schedule_payment(bill_date, rng, net_days=VENDOR_NET_DAYS)
