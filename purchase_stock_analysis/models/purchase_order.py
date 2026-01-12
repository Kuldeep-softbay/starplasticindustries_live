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
        for move in self:
            grade = ''
            if move.product_id:
                values = move.product_id.product_template_variant_value_ids
                grade = ", ".join(values.mapped('name'))
            move.product_grade = grade

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    product_grade = fields.Char(
        compute='_compute_product_grade',
        store=False
    )

    def _compute_product_grade(self):
        for line in self:
            values = line.product_id.product_template_variant_value_ids
            line.product_grade = ", ".join(values.mapped('name'))
