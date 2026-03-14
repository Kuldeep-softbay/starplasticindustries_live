from odoo import models, fields, api


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    co_number = fields.Char(
        string='C.O Number',
        help='Customer Order Number for this line'
    )
    wo_qty = fields.Float(
        string='WO Qty',
        help='Work Order Quantity for this line'
    )

    product_attribute = fields.Char(
        string="Attribute",
        compute="_compute_product_attribute",
        store=True
    )

    @api.depends('product_id')
    def _compute_product_attribute(self):
        for line in self:
            if line.product_id:
                attrs = line.product_id.product_template_attribute_value_ids.mapped('name')
                line.product_attribute = ", ".join(attrs)
            else:
                line.product_attribute = ""
