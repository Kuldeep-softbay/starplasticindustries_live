from odoo import api, fields, models, _
from collections import defaultdict

class SaleOrder(models.Model):
    _inherit = "sale.order"

    exp_dis_date = fields.Date(string="Expected Dispatch Date")
    exp_packing_date = fields.Date(string="Expected Packing Date")
    actual_packing_date = fields.Date(string="Actual Packing Date")
    remark = fields.Char(string="Remark")
    packing_details = fields.Html(
        string="Packing Details",
        sanitize=True
    )
    @api.onchange('partner_id')
    def _onchange_partner_id_set_packing_details(self):
        """
        When customer is selected, populate Packing Details
        from Customer Internal Notes (comment).
        """
        for order in self:
            if order.partner_id and order.partner_id.comment:
                order.packing_details = order.partner_id.comment
            else:
                order.packing_details = False

    def get_packing_memo_payload(self):
        selections = self.env.context.get('packing_memo_selections', {})
        if not selections:
            return {'details': [], 'summary': []}

        details = []

        summary_qty_map = defaultdict(float)
        summary_lot_map = {}

        for lot_id_str, qty in selections.items():
            lot = self.env['stock.lot'].browse(int(lot_id_str))
            product = lot.product_id

            # Details table → per lot
            details.append({
                'lot_name': lot.name,
                'product_display_name': product.display_name,
                'default_code': product.default_code,
                'qty': qty,
            })

            # Summary → per product
            summary_qty_map[product.id] += qty

            # Store ANY one batch number per product (first wins)
            if product.id not in summary_lot_map:
                summary_lot_map[product.id] = lot.name

        # Build summary table (ONE row per product)
        summary = []
        for product_id, total_qty in summary_qty_map.items():
            product = self.env['product.product'].browse(product_id)
            summary.append({
                'lot_name': summary_lot_map.get(product_id),  # representative batch
                'product_display_name': product.display_name,
                'default_code': product.default_code,
                'qty': total_qty,
            })

        return {
            'details': details,
            'summary': summary,
        }

    
    def write(self, vals):
        res = super().write(vals)

        if 'exp_dispatch_date' in vals:
            for order in self:
                pickings = order.picking_ids.filtered(
                    lambda p: p.state not in ('done', 'cancel')
                    and p.picking_type_code == 'outgoing'
                )
                pickings.write({
                    'exp_dispatch_date': order.exp_dispatch_date,
                })

        return res
