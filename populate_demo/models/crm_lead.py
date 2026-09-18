from odoo import fields, models


class CrmLead(models.Model):
    """Historical-date-aware CRM transitions for the BI talk blueprint.

    Native ``action_set_won``/``action_set_lost`` stamp ``date_closed`` (and
    other tracked fields) with the execution date. The populate blueprint
    needs the closure to land on the scenario's historical date instead, so
    these wrappers replay the native action then correct the date it leaves
    behind - never writing the final state directly.
    """
    _inherit = 'crm.lead'

    def _populate_win(self, date):
        date = fields.Datetime.to_datetime(date)
        self.action_set_won()
        self.write({'date_closed': date})

    def _populate_lose(self, lost_reason_id, date):
        date = fields.Datetime.to_datetime(date)
        self.action_set_lost(lost_reason_id=lost_reason_id)
        self.write({'date_closed': date})
