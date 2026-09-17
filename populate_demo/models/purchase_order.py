from odoo import models


class PurchaseOrder(models.Model):
    """Historical-date-aware purchase confirmation."""
    _inherit = 'purchase.order'

    def _populate_confirm(self, date):
        self.button_confirm()
        self.write({'date_order': date, 'date_approve': date})
