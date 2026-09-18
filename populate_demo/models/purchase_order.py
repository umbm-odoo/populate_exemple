import random

from odoo import fields, models

from ..planner import schedule
from ..planner.config import CURRENCY_DECIMALS, CUTOFF, VENDOR_COST_FACTORS


class PurchaseOrder(models.Model):
    """Historical-date-aware purchase confirmation, billing, and payment."""
    _inherit = 'purchase.order'

    def _populate_confirm(self, date):
        date = fields.Datetime.to_datetime(date)
        # Spec section 7: "apply vendor [cost] factors at purchase
        # confirmation". Both native procurement (direct-buy resale lines,
        # triggered by sale.order.action_confirm) and our own component
        # purchases (mrp_production.py's _populate_order_components) leave
        # price_unit at today's raw supplierinfo price - rescale it to the
        # confirmation year's vendor-cost factor before it's locked in.
        factor = VENDOR_COST_FACTORS[date.year]
        for line in self.order_line:
            line.price_unit = round(line.price_unit * factor, CURRENCY_DECIMALS)
        self.button_confirm()
        self.write({'date_order': date, 'date_approve': date})

    def _populate_bill_and_pay(self):
        """Create, post, and (mostly) pay a vendor bill for each fully
        received PO in ``self``, receipt-based (spec section 11).

        Unlike sale orders, cascaded purchase orders (component purchases,
        native direct-buy procurement) aren't represented as named rows in
        the JSON plan, so there's no ``by_name`` row to look a bill/payment
        date up from. Dates are derived here instead, straight from the
        PO's own receipt, using the same scheduling rules the planner uses
        for customer invoices (``planner.schedule``) - seeded per PO so the
        result is still fully deterministic given the run seed.
        """
        for po in self:
            receipt_dates = po.picking_ids.filtered(lambda p: p.state == 'done').mapped('date_done')
            if not receipt_dates:
                continue
            receive_date = max(receipt_dates)
            bill_date = schedule.schedule_vendor_bill(receive_date, random.Random(f'{po.id}-bill'))
            if bill_date >= CUTOFF.date():
                continue  # received too close to cutoff to have been billed yet

            po.action_create_invoice()
            bill = po.invoice_ids.filtered(lambda m: m.state == 'draft')
            if not bill:
                continue
            bill._populate_post(bill_date)

            pay_date, unpaid = schedule.schedule_vendor_payment(bill_date, random.Random(f'{po.id}-pay'))
            if not unpaid:
                bill._populate_register_payment(pay_date)
