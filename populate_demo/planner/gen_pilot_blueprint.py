"""Authoring tool: generate populate/pilot.xml from pilot_plan.json.

Not imported at runtime. Run after dump_plan.py whenever the plan changes.
"""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

# Odoo's own core populate blueprints (sale/stock/account/project) never let
# mail.thread's per-write tracking/follower-notification machinery run at
# bulk scale - every <create> block for a tracked model carries this same
# context. Our blocks additionally replay real action_confirm/button_validate
# workflows (needed for FIFO/valuation correctness), which touches tracked
# state fields far more often than a plain create, so the same flag matters
# even more here - it was the single biggest cost once order volume grew.
BULK_CONTEXT = "{'tracking_disable': True, 'mail_auto_subscribe_no_notify': True}"

PLAN_PATH = Path(__file__).parent.parent / 'populate' / 'data' / 'pilot_plan.json'
OUTPUT_PATH = Path(__file__).parent.parent / 'populate' / 'pilot.xml'


def ref(bare_xmlid_expr: str) -> str:
    """Python expression resolving a bare-xmlid *expression* (not a literal) via env.ref()."""
    return f"env.ref('__import__.' + {bare_xmlid_expr}).id"


def ind(text: str, level: int = 3) -> str:
    return textwrap.indent(text, '    ' * level)


def exclude_origins(names: list[str]) -> str:
    """Domain fragment excluding any picking/production whose ``origin``
    *contains* one of these order names.

    Odoo batches same-day/same-warehouse internal transfers for multiple
    orders into one shared picking, so ``origin`` can come back comma-joined
    ("S00416,S00419"). An exact ``('origin', 'not in', names)`` misses that
    entirely - it neither excludes a combined origin it should (the excluded
    name is a substring, not the whole field) nor safely matches one it
    shouldn't. ``not ilike`` per name, AND'ed together, checks containment
    instead of equality and covers both directions correctly.
    """
    return ', '.join(f"('origin', 'not ilike', {name!r})" for name in names)


def main():
    with PLAN_PATH.open() as f:
        plan = json.load(f)
    subsets = plan['subsets']

    production_only_names = [o['order_name'] for o in subsets['awaiting_orders'] if o['sub_bucket'] == 'production']
    purchase_only_names = [o['order_name'] for o in subsets['awaiting_orders'] if o['sub_bucket'] == 'purchase']
    unpaid_names = [o['order_name'] for o in subsets['delivered_orders'] if o.get('unpaid')]

    blocks: list[str] = []

    # === CRM leads =============================================================
    for subset in ('won_leads', 'lost_leads', 'open_leads'):
        fields = "\n".join([
            f'<value name="_row" generator="oxp.subset_row" subset="{subset}"/>',
            "<field name=\"name\" eval=\"'Opportunity ' + _row['order_name']\"/>",
            "<field name=\"type\" eval=\"'opportunity'\"/>",
            f'<field name="partner_id" eval="{ref("_row[\'customer_xmlid\']")}"/>',
            f'<field name="team_id" eval="{ref("_row[\'team\']")}"/>',
            f'<field name="user_id" eval="{ref("_row[\'user\']")}"/>',
            f'<field name="source_id" eval="{ref("_row[\'source\']")}"/>',
            f'<field name="medium_id" eval="{ref("_row[\'medium\']")}"/>',
            f'<field name="stage_id" eval="{ref("\'bi_crm_new\'")}"/>',
            f'<field name="campaign_id" eval="{ref("_row[\'campaign\']")} if _row.get(\'campaign\') else False"/>',
        ])
        blocks.append(f'<create model="crm.lead" count="{len(subsets[subset])}" id="{subset}">\n{ind(fields)}\n</create>')

    # === Extra order-unlinked CRM volumes (spec section 8) =====================
    # No sale order behind any of these - "name" can't reuse an order_name.
    for subset, name_prefix, lead_type in (
        ('crm_lost_no_quote', 'Prospect', 'opportunity'),
        ('crm_open_no_quote', 'Prospect', 'opportunity'),
        ('crm_unconverted_leads', 'Lead', 'lead'),
    ):
        fields = "\n".join([
            f'<value name="_row" generator="oxp.subset_row" subset="{subset}"/>',
            f"<field name=\"name\" eval=\"'{name_prefix} ' + str(_row['id'])\"/>",
            f"<field name=\"type\" eval=\"'{lead_type}'\"/>",
            f'<field name="partner_id" eval="{ref("_row[\'customer_xmlid\']")}"/>',
            f'<field name="team_id" eval="{ref("_row[\'team\']")}"/>',
            f'<field name="user_id" eval="{ref("_row[\'user\']")}"/>',
            f'<field name="source_id" eval="{ref("_row[\'source\']")}"/>',
            f'<field name="medium_id" eval="{ref("_row[\'medium\']")}"/>',
        ] + ([f'<field name="stage_id" eval="{ref("\'bi_crm_new\'")}"/>'] if lead_type == 'opportunity' else []))
        blocks.append(f'<create model="crm.lead" count="{len(subsets[subset])}" id="{subset}">\n{ind(fields)}\n</create>')

    blocks.append(
        '<function model="crm.lead" name="_populate_lose" ref="crm_lost_no_quote" batched="False">\n'
        + ind(
            '<value name="_row" generator="oxp.subset_row" subset="crm_lost_no_quote"/>\n'
            f'<arg name="lost_reason_id" eval="{ref("_row[\'lost_reason\']")}"/>\n'
            "<arg name=\"date\" eval=\"_row['close_date']\"/>",
        ) + '\n</function>',
    )

    # === Sale orders (5 outcome groups) ========================================
    for subset in ('delivered_orders', 'awaiting_orders', 'cancelled_before_orders', 'cancelled_after_orders', 'open_orders'):
        lead_name_expr = "'Opportunity ' + _row['order_name']"
        fields = "\n".join([
            f'<value name="_row" generator="oxp.subset_row" subset="{subset}"/>',
            f'<field name="partner_id" eval="{ref("_row[\'customer_xmlid\']")}"/>',
            "<field name=\"warehouse_id\" eval=\"env.ref('stock.warehouse0').id if _row['warehouse_code'] == 'BE' "
            "else env.ref('__import__.bi_wh_' + _row['warehouse_code'].lower()).id\"/>",
            "<field name=\"date_order\" eval=\"_row['quotation_date']\"/>",
            f'<field name="team_id" eval="{ref("_row[\'team\']")}"/>',
            f'<field name="user_id" eval="{ref("_row[\'user\']")}"/>',
            "<field name=\"opportunity_id\" eval=\""
            f"env['crm.lead'].search([('name','=',{lead_name_expr})], limit=1).id if _row['linked'] else False\"/>",
            f'<field name="source_id" eval="{ref("_row[\'source\']")} if _row[\'linked\'] else False"/>',
            f'<field name="medium_id" eval="{ref("_row[\'medium\']")} if _row[\'linked\'] else False"/>',
            f'<field name="campaign_id" eval="{ref("_row[\'campaign\']")} if _row.get(\'campaign\') else False"/>',
        ])
        blocks.append(f'<create model="sale.order" count="{len(subsets[subset])}" id="{subset}">\n{ind(fields)}\n</create>')

    # === Sale order lines ========================================================
    fields = "\n".join([
        '<value name="_row" generator="oxp.subset_row" subset="all_lines"/>',
        "<field name=\"order_id\" generator=\"relation.one\" domain=\"[('name', '=', _row['order_name'])]\"/>",
        f'<field name="product_id" eval="{ref("_row[\'product_xmlid\']")}"/>',
        "<field name=\"product_uom_qty\" eval=\"_row['qty']\"/>",
        "<field name=\"sequence\" eval=\"_row['sequence']\"/>",
        "<field name=\"price_unit\" eval=\"_row['price_unit']\"/>",
        "<field name=\"discount\" eval=\"_row['discount'] * 100\"/>",
    ])
    blocks.append(f'<create model="sale.order.line" count="{len(subsets["all_lines"])}" id="order_lines">\n{ind(fields)}\n</create>')

    # === Non-FIFO-sensitive processing (cancellations, lost/won CRM) ===========
    blocks.append('<function model="sale.order" name="action_cancel" ref="cancelled_before_orders" batched="True"/>')

    blocks.append(
        '<function model="crm.lead" name="_populate_lose" ref="lost_leads" batched="False">\n'
        + ind(
            '<value name="_row" generator="oxp.subset_row" subset="lost_leads"/>\n'
            f'<arg name="lost_reason_id" eval="{ref("_row[\'lost_reason\']")}"/>\n'
            "<arg name=\"date\" eval=\"_row['lost_date']\"/>",
        ) + '\n</function>',
    )

    blocks.append(
        '<function model="sale.order" name="_populate_confirm" ref="cancelled_after_orders" batched="False">\n'
        + ind(
            '<value name="_row" generator="oxp.subset_row" subset="cancelled_after_orders"/>\n'
            "<arg name=\"date\" eval=\"_row['confirm_date']\"/>",
        ) + '\n</function>',
    )
    blocks.append(
        '<function model="crm.lead" name="_populate_win" ref="won_leads" batched="False">\n'
        + ind(
            '<value name="_row" generator="oxp.subset_row" subset="won_leads"/>\n'
            "<arg name=\"date\" eval=\"_row['confirm_date']\"/>",
        ) + '\n</function>',
    )
    blocks.append('<function model="sale.order" name="_populate_cancel" ref="cancelled_after_orders" batched="True"/>')

    # === Delivered orders: the FIFO-sensitive chain, processed in one pass per
    # step so record creation order (already sorted chronologically by
    # dump_plan.py) drives valuation order. ======================================
    blocks.append(
        '<function model="sale.order" name="_populate_confirm" ref="delivered_orders" batched="False">\n'
        + ind(
            '<value name="_row" generator="oxp.subset_row" subset="delivered_orders"/>\n'
            "<arg name=\"date\" eval=\"_row['confirm_date']\"/>",
        ) + '\n</function>',
    )
    def fulfillment_pass_blocks():
        """PO confirm -> produce -> incoming -> dispatch -> transit receive ->
        outgoing, all domain-scoped (not ref-scoped) so re-running the same
        sequence a second time is a harmless no-op for anything already
        done. Needed because Odoo batches many orders' transit moves into
        shared aggregate pickings per warehouse/day - one order's dispatch
        leg can still be genuinely unready (waiting on production) during
        the first pass and only become dispatchable once a *sibling* order
        in the same batch catches up, so a single top-to-bottom pass isn't
        always enough to fully drain the chain.
        """
        return [
            '<function model="purchase.order" name="_populate_confirm" domain="[(\'state\', \'=\', \'draft\')]" batched="False">\n'
            + ind(
                '<value name="_row" generator="oxp.by_name_row"/>\n'
                "<arg name=\"date\" eval=\"_row['po_confirm_date']\"/>",
            ) + '\n</function>',

            '<function model="mrp.production" name="_populate_produce" domain="[(\'state\', \'not in\', (\'done\', \'cancel\'))]" batched="False">\n'
            + ind(
                '<value name="_row" generator="oxp.by_name_row"/>\n'
                "<arg name=\"date_start\" eval=\"_row['mo_start_date']\"/>\n"
                "<arg name=\"date_finished\" eval=\"_row['mo_finish_date']\"/>",
            ) + '\n</function>',

            "<function model=\"stock.picking\" name=\"_populate_validate\"\n"
            "          domain=\"[('state', 'not in', ('done', 'cancel')), ('picking_type_id.code', '=', 'incoming')]\" batched=\"False\">\n"
            + ind(
                '<value name="_row" generator="oxp.by_name_row"/>\n'
                "<arg name=\"date\" eval=\"_row['po_receive_date']\"/>",
            ) + '\n</function>',

            "<function model=\"stock.picking\" name=\"_populate_validate\"\n"
            "          domain=\"[('state', 'not in', ('done', 'cancel', 'waiting')), ('picking_type_id.code', '=', 'internal')]\" batched=\"False\">\n"
            + ind(
                '<value name="_row" generator="oxp.by_name_row"/>\n'
                "<arg name=\"date\" eval=\"_row['dispatch_date']\"/>",
            ) + '\n</function>',

            "<function model=\"stock.picking\" name=\"_populate_validate\"\n"
            "          domain=\"[('state', 'not in', ('done', 'cancel', 'waiting')), ('picking_type_id.code', '=', 'internal')]\" batched=\"False\">\n"
            + ind(
                '<value name="_row" generator="oxp.by_name_row"/>\n'
                "<arg name=\"date\" eval=\"_row['transit_receive_date']\"/>",
            ) + '\n</function>',

            "<function model=\"stock.picking\" name=\"_populate_validate\"\n"
            "          domain=\"[('state', 'not in', ('done', 'cancel')), ('picking_type_id.code', '=', 'outgoing')]\" batched=\"False\">\n"
            + ind(
                '<value name="_row" generator="oxp.by_name_row"/>\n'
                "<arg name=\"date\" eval=\"_row['delivery_actual_date']\"/>",
            ) + '\n</function>',
        ]

    # Two passes: the second one drains any transit leg left 'waiting' by a
    # sibling order's slower chain during the first pass (see docstring
    # above). A third pass would find nothing left to do.
    blocks.extend(fulfillment_pass_blocks())
    blocks.extend(fulfillment_pass_blocks())
    blocks.append('<function model="sale.order" name="_create_invoices" ref="delivered_orders" batched="False"/>')
    blocks.append(
        '<function model="account.move" name="_populate_post"\n'
        "          domain=\"[('state', '=', 'draft'), ('move_type', '=', 'out_invoice')]\" batched=\"False\">\n"
        + ind(
            '<value name="_row" generator="oxp.by_name_row"/>\n'
            "<arg name=\"date\" eval=\"_row['invoice_date']\"/>",
        ) + '\n</function>',
    )
    unpaid_exclusion = repr(unpaid_names)
    blocks.append(
        '<function model="account.move" name="_populate_register_payment"\n'
        "          domain=\"[('state', '=', 'posted'), ('payment_state', 'not in', ('paid', 'in_payment', 'reversed')), "
        f"('move_type', '=', 'out_invoice'), ('invoice_origin', 'not in', {unpaid_exclusion})]\" batched=\"False\">\n"
        + ind(
            '<value name="_row" generator="oxp.by_name_row"/>\n'
            "<arg name=\"date\" eval=\"_row['payment_date']\"/>",
        ) + '\n</function>',
    )

    # === Awaiting (outstanding) orders: confirm, then stop each one exactly
    # where its sub_bucket says it should. ======================================
    blocks.append(
        '<function model="sale.order" name="_populate_confirm" ref="awaiting_orders" batched="False">\n'
        + ind(
            '<value name="_row" generator="oxp.subset_row" subset="awaiting_orders"/>\n'
            "<arg name=\"date\" eval=\"_row['confirm_date']\"/>",
        ) + '\n</function>',
    )
    blocks.append(
        '<function model="purchase.order" name="_populate_confirm" domain="[(\'state\', \'=\', \'draft\')]" batched="False">\n'
        + ind(
            '<value name="_row" generator="oxp.by_name_row"/>\n'
            "<arg name=\"date\" eval=\"_row['po_confirm_date']\"/>",
        ) + '\n</function>',
    )
    # Component/production must not advance for orders whose whole point is to
    # still be "awaiting production" - exclude their MOs by origin.
    prod_exclusion = exclude_origins(production_only_names)
    blocks.append(
        "<function model=\"mrp.production\" name=\"_populate_produce\"\n"
        f"          domain=\"[('state', 'not in', ('done', 'cancel')), {prod_exclusion}]\" batched=\"False\">\n"
        + ind(
            '<value name="_row" generator="oxp.by_name_row"/>\n'
            "<arg name=\"date_start\" eval=\"_row['mo_start_date']\"/>\n"
            "<arg name=\"date_finished\" eval=\"_row['mo_finish_date']\"/>",
        ) + '\n</function>',
    )
    # Purchased-goods-awaited orders must not have their PO received yet.
    purchase_exclusion = exclude_origins(purchase_only_names)
    blocks.append(
        "<function model=\"stock.picking\" name=\"_populate_validate\"\n"
        "          domain=\"[('state', 'not in', ('done', 'cancel')), ('picking_type_id.code', '=', 'incoming'), "
        f"{purchase_exclusion}]\" batched=\"False\">\n"
        + ind(
            '<value name="_row" generator="oxp.by_name_row"/>\n'
            "<arg name=\"date\" eval=\"_row['po_receive_date']\"/>",
        ) + '\n</function>',
    )
    # Only the 'transit' sub-bucket dispatches - 'production'/'purchase'
    # orders can still end up with a fully-reserved (non-'waiting') dispatch
    # move once their components are otherwise resolved elsewhere in the
    # batch, so they need the same explicit origin exclusion, not just the
    # 'waiting' state filter.
    dispatch_exclusion = exclude_origins(production_only_names + purchase_only_names)
    blocks.append(
        "<function model=\"stock.picking\" name=\"_populate_validate\"\n"
        f"          domain=\"[('state', 'not in', ('done', 'cancel', 'waiting')), ('picking_type_id.code', '=', 'internal'), {dispatch_exclusion}]\" batched=\"False\">\n"
        + ind(
            '<value name="_row" generator="oxp.by_name_row"/>\n'
            "<arg name=\"date\" eval=\"_row['dispatch_date']\"/>",
        ) + '\n</function>',
    )

    # === Vendor bills and payments (spec section 11) ===========================
    # Every fully-received, not-yet-invoiced PO by this point - both direct-buy
    # resale purchases and component purchases from every order group above.
    blocks.append(
        '<function model="purchase.order" name="_populate_bill_and_pay"\n'
        "          domain=\"[('state', '=', 'purchase'), ('invoice_status', '=', 'to invoice')]\" batched=\"False\"/>",
    )

    blocks = [
        re.sub(r'(<(?:create|function)\s+model="[^"]+")', rf'\1 context="{BULK_CONTEXT}"', b, count=1)
        for b in blocks
    ]

    body = "\n\n".join(ind(b, 3) for b in blocks)
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="blueprint_pilot" model="populate.blueprint">
        <field name="name">Wingardium Odoosa BI - 1% pilot (1,000 orders)</field>
        <field name="definition_xml" type="xml">
{body}
        </field>
    </record>
</odoo>
"""
    OUTPUT_PATH.write_text(xml)
    print(f"Wrote {len(blocks)} blocks to {OUTPUT_PATH}")


if __name__ == '__main__':
    main()
