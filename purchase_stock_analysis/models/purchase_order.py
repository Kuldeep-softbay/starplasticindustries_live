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

class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_grade_value(self):
        """Helper method to fetch Grade attribute value"""
        self.ensure_one()
        for line in self.product_tmpl_id.attribute_line_ids:
            if line.attribute_id.name == "Grade":
                return ", ".join(line.value_ids.mapped("name"))
        return False

    def name_get(self):
        result = []
        for product in self:
            name = product.name
            grade = product._get_grade_value()

            if grade:
                name = f"{name} [{grade}]"

            result.append((product.id, name))
        return result

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        products = self.search([('name', operator, name)] + args, limit=limit)
        return products.name_get()
