from datetime import timedelta

from odoo import Command, fields, models


class MrpProduction(models.Model):
    """Historical-date-aware manufacturing order completion."""
    _inherit = 'mrp.production'

    def _populate_order_components(self, date_order, date_receive):
        """Buy and receive whatever raw materials are still missing.

        Component demand is fed by ``make_to_stock`` reordering rules, not by
        the sale-triggered make-to-order chain used for the finished good, so
        nothing procures them automatically. The blueprint is responsible for
        generating those vendor receipts itself, early enough to support the
        production (spec section 9).
        """
        for production in self:
            for move in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                product = move.product_id
                qty = move.product_uom_qty
                seller = product._select_seller(quantity=qty)
                if not seller:
                    continue
                po = self.env['purchase.order'].create({
                    'partner_id': seller.partner_id.id,
                    'date_order': date_order,
                    'order_line': [(0, 0, {
                        'product_id': product.id,
                        'product_uom_qty': qty,
                        'uom_id': move.uom_id.id,
                        'price_unit': seller.price,
                        'date_planned': date_order,
                    })],
                })
                # product_uom_qty is reset to a default (e.g. supplier min_qty)
                # by a compute during create(); write it again to lock in the
                # actual demand.
                po.order_line.write({'product_uom_qty': qty})
                po._populate_confirm(date_order)
                # The receipt move is stamped with whatever product_uom_qty
                # the order line had at picking-creation time; re-sync it in
                # case it snapshotted the pre-write() default.
                po.picking_ids.move_ids.write({'product_uom_qty': qty})
                po.picking_ids._populate_validate(date_receive)
            production.action_assign()
            # We just bought/received exactly this move's own demand, but
            # reservation is a shared pool: another production waiting on the
            # same component can win part of what we just receipted before
            # our own action_assign() runs, leaving this move a unit or two
            # short and the production stuck in 'to_close' on a consumption
            # mismatch. Top the reservation back up to the full demand - the
            # stock physically exists, it just got claimed by the wrong move.
            for move in production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                shortfall = move.product_uom_qty - move.quantity
                if shortfall <= 0:
                    continue
                if move.move_line_ids:
                    move.move_line_ids[0].quantity += shortfall
                else:
                    move.move_line_ids = [Command.create({
                        'product_id': move.product_id.id,
                        'uom_id': move.uom_id.id,
                        'quantity': shortfall,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'picking_id': move.picking_id.id,
                    })]

    def _populate_produce(self, date_start, date_finished):
        date_start = fields.Datetime.to_datetime(date_start)
        date_finished = fields.Datetime.to_datetime(date_finished)
        for production in self:
            if production.state == 'draft':
                production.action_confirm()
            # Raw move quantities scale with qty_producing, so it must be set
            # before component needs are computed for purchasing - otherwise
            # we buy/receive for whatever quantity was showing beforehand.
            production.qty_producing = production.product_qty
            production._populate_order_components(
                date_order=date_start - timedelta(days=9),
                date_receive=date_start - timedelta(days=2),
            )
            production.button_mark_done()
            # force_date bypasses the "can't move a done/cancelled MO" guard;
            # writing date_start/date_finished also re-dates the raw/finished
            # moves for us (see mrp.production.write()).
            production.with_context(force_date=True).write({
                'date_start': date_start, 'date_finished': date_finished,
            })
