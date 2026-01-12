from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    primary_contact_person = fields.Char(string="Contact Person")
    primary_contact_no = fields.Char(string="Contact No")
    primary_email = fields.Char(string="Email")

    secondary_contact_person = fields.Char(string="Contact Person")
    secondary_contact_no = fields.Char(string="Contact No")
    secondary_email = fields.Char(string="Email")

    packing_method = fields.Char(string="Packing Method")
    packing_details_qty = fields.Text(string="Details of Packing with Quantity")
    transport_details = fields.Text(string="Transport Details")

    product_details_ids = fields.Many2many(
        'product.product',
        string="Product Name & Details"
    )
