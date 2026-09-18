from odoo import fields, models


class SaleOrder(models.Model):
    """Historical-date-aware sale confirmation.

    ``action_confirm`` resets ``date_order`` to the execution date. Replay
    the native confirmation, then restore the scenario's confirmation date.
    """
    _inherit = 'sale.order'

    def _populate_confirm(self, date):
        # Populate's cross-boundary safety check forbids passing a real
        # datetime through an <arg>/eval dependency, so blueprints hand us
        # an ISO string here - convert it back before using it.
        date = fields.Datetime.to_datetime(date)
        self.action_confirm()
        self.write({'date_order': date})

    def _populate_cancel(self):
        """Cancel a confirmed order and any dependent demand it already triggered.

        ``action_cancel`` on the sale order cancels the delivery picking but
        leaves any manufacturing order or draft purchase order already
        created for it (buy/manufacture route procurement) untouched -
        cancel those explicitly so no live MO/PO is left behind for an order
        that is supposed to have no outstanding demand.
        """
        self.action_cancel()
        for order in self:
            stray_mos = self.env['mrp.production'].search([
                ('origin', 'like', order.name),
                ('state', 'not in', ('done', 'cancel')),
            ])
            stray_mos.action_cancel()
            stray_pos = self.env['purchase.order'].search([
                ('origin', 'like', order.name),
                ('state', 'not in', ('done', 'cancel')),
            ])
            stray_pos.button_cancel()
