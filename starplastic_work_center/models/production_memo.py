from odoo import api, fields, models
from odoo.exceptions import UserError


class ProductionMemo(models.Model):
    _name = 'production.memo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Production Memo'

    production_id = fields.Many2one(
        'mrp.production',
        required=True,
        tracking=True
    )
