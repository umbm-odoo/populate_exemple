from odoo import fields, models


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
        date = fields.Datetime.to_datetime(date)
        for picking in self:
            if picking.state != 'done':
                # Always re-attempt reservation: a picking can already show
                # 'assigned' from one of its moves while a sibling move (e.g.
                # a manufactured line whose production just finished) only
                # just became available and still needs its own action_assign.
                picking.action_assign()
            if not picking.move_ids.filtered('product_uom_qty'):
                # A redundant leg of a multi-step route (e.g. an internal
                # transfer whose source and destination collapse to the same
                # place for this particular order) with nothing to move -
                # there is no business event here, so cancel it rather than
                # validate a transfer of nothing.
                picking.move_ids._action_cancel()
                picking.action_cancel()
                continue
            for move_line in picking.move_line_ids:
                if not move_line.quantity:
                    move_line.quantity = move_line.move_id.product_uom_qty
            if not sum(picking.move_line_ids.mapped('quantity')):
                raise ValueError(
                    f"{picking.display_name}: reservation produced no move lines "
                    f"despite {sum(picking.move_ids.mapped('product_uom_qty'))} units demanded "
                    f"(moves: {picking.move_ids.mapped(lambda m: (m.product_id.display_name, m.state, m.product_uom_qty))})"
                )
            picking.button_validate()
            picking.write({'date_done': date})
            picking.move_ids.write({'date': date})
