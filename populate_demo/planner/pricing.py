"""Spec section 7: historical commercial amounts via year-specific factors.

"Use year-specific price factors instead of applying current prices to old
transactions ... Apply selling factors at quotation date and vendor factors
at purchase confirmation. Lock the resulting line prices into downstream
invoices and bills. Round unit prices to currency precision."

Selling prices are resolved entirely here, in the planner, against the
known 2026 catalogue baseline (``config.PRODUCT_2026_LIST_PRICE``) - so
every sale order line's price is locked into the plan before Odoo ever
sees it. Vendor prices can't be: the actual seller/price is only known at
purchase-confirmation time in Odoo (``product._select_seller()``, native
procurement, 70/30 supplier choice), so the vendor-cost factor is applied
Odoo-side, in ``models/purchase_order.py``, against this same table.
"""
from __future__ import annotations

from .config import CURRENCY_DECIMALS, PRODUCT_2026_LIST_PRICE, SELLING_PRICE_FACTORS


def selling_price(product_xmlid: str, year: int) -> float:
    base = PRODUCT_2026_LIST_PRICE[product_xmlid]
    factor = SELLING_PRICE_FACTORS[year]
    return round(base * factor, CURRENCY_DECIMALS)
