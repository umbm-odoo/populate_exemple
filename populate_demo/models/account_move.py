from odoo import fields, models


class AccountMove(models.Model):
    """Historical-date-aware invoice/bill posting and payment registration."""
    _inherit = 'account.move'

    def _populate_post(self, date):
        date = fields.Date.to_date(date)
        self.write({'invoice_date': date})
        self.action_post()
        self.with_context(skip_readonly_check=True).write({'date': date, 'invoice_date': date})

    def _populate_register_payment(self, date):
        date = fields.Date.to_date(date)
        wizard = self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=self.ids,
        ).create({'payment_date': date})
        wizard.action_create_payments()
        payments = self.payment_ids
        payments.write({'date': date})
        payments.move_id.with_context(skip_readonly_check=True).write({'date': date})
        return payments
