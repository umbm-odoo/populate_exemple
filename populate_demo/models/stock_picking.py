from odoo import models


class StockPicking(models.Model):
    """Historical-date-aware picking validation.

    ``button_validate`` stamps ``date_done`` and every ``stock.move``'s
    ``date`` with the execution time - which also drives FIFO consumption
    order. Callers are responsible for triggering pickings in true
    chronological order across the whole run so cost layers are consumed in
    the intended sequence; this method only corrects the *displayed*
    business dates after the native transition runs.
    """
    _inherit = 'stock.picking'

    def _populate_validate(self, date):
        for picking in self:
            if picking.state != 'done':
                # Always re-attempt reservation: a picking can already show
                # 'assigned' from one of its moves while a sibling move (e.g.
                # a manufactured line whose production just finished) only
                # just became available and still needs its own action_assign.
                picking.action_assign()
            for move_line in picking.move_line_ids:
                if not move_line.quantity:
                    move_line.quantity = move_line.move_id.product_uom_qty
            picking.button_validate()
            picking.write({'date_done': date})
            picking.move_ids.write({'date': date})
