from odoo import fields, models


class PurchaseOrder(models.Model):
    """Historical-date-aware purchase confirmation."""
    _inherit = 'purchase.order'

    def _populate_confirm(self, date):
        date = fields.Datetime.to_datetime(date)
        self.button_confirm()
        self.write({'date_order': date, 'date_approve': date})
