from odoo import models


class SaleOrder(models.Model):
    """Historical-date-aware sale confirmation.

    ``action_confirm`` resets ``date_order`` to the execution date. Replay
    the native confirmation, then restore the scenario's confirmation date.
    """
    _inherit = 'sale.order'

    def _populate_confirm(self, date):
        self.action_confirm()
        self.write({'date_order': date})

    def _populate_cancel(self):
        """Cancel a confirmed order and any dependent demand it already triggered.

        ``action_cancel`` on the sale order does not reliably cascade to a
        manufacturing order already created for it (unlike purchase orders
        and pickings, which do cancel via the stock rule's
        ``propagate_cancel``) - cancel those explicitly so no live MO is left
        behind for an order that is supposed to have no outstanding demand.
        """
        self.action_cancel()
        for order in self:
            stray_mos = self.env['mrp.production'].search([
                ('origin', 'like', order.name),
                ('state', 'not in', ('done', 'cancel')),
            ])
            stray_mos.action_cancel()
