from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_insert = fields.Char("Product Insert")
    default_code = fields.Char("Product Code")
    raw_material = fields.Char("Raw Material")
    mould_name = fields.Char("Mould Name")
    difference = fields.Float("Difference")
    is_product = fields.Boolean(string="Is Product?")

    product_counting_type = fields.Selection([
        ('kg', 'Kg'),
        ('nos', 'Nos'),
    ], string="Product Counting Type")

    unit_weight_tolerance = fields.Float("Unit Weight Tolerance (+/-)")
    process = fields.Selection([
        ('blow', 'Blow molding'),
        ('injaction', 'Injaction molding'),
        ('blow_injection', 'Blow Injaction molding'),
        ('other', 'Other'),
    ], string="Process")

    rm_formulation = fields.Text("RM Formulation")
    packing_method = fields.Char("Packing Method")
    batch_number = fields.Char("Batch Number")
    
    weight_gm = fields.Float(
        string="Weight (gm)",
        digits=(16, 2)
    )

    weight_gm_uom = fields.Char(
        string="",
        default="gm",
        readonly=True
    )

    weight = fields.Float(
    compute="_compute_weight_from_gm",
    store=True,
    digits=(16, 4)
    )

    attribute_values_display = fields.Char(
        string="Attributes",
        compute="_compute_attribute_values_display",
        store=False
    )

    @api.depends('attribute_line_ids.value_ids')
    def _compute_attribute_values_display(self):
        for product in self:
            values = []
            for line in product.attribute_line_ids:
                values.extend(line.value_ids.mapped('name'))
            product.attribute_values_display = ", ".join(values)


    @api.depends('weight_gm')
    def _compute_weight_from_gm(self):
        for rec in self:
            rec.weight = (rec.weight_gm or 0.0) / 1000.0

    @api.onchange('weight_gm')
    def _onchange_weight_gm(self):
        self.weight = (self.weight_gm or 0.0) / 1000.0
