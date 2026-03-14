from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    product_grade = fields.Char(
        string='Grade',
        compute='_compute_product_grade',
        store=False
    )

    @api.depends('product_id')
    def _compute_product_grade(self):
        for line in self:
            if line.product_id:
                attrs = line.product_id.product_template_attribute_value_ids.mapped('name')
                line.product_grade = ", ".join(attrs)
            else:
                line.product_grade = ""

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_grade = fields.Char(
        compute='_compute_product_grade',
        store=False
    )

    @api.depends('product_id')
    def _compute_product_grade(self):
        for line in self:
            if line.product_id:
                attrs = line.product_id.product_template_attribute_value_ids.mapped('name')
                line.product_grade = ", ".join(attrs)
            else:
                line.product_grade = ""
