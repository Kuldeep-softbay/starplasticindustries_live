from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    co_number = fields.Char(
        string='C.O Number',
        help='Customer Order Number for this line'
    )
