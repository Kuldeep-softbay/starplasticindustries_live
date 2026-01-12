from odoo import models, fields


class RejectionReason(models.Model):
    _name = 'rejection.reason'
    _description = 'Rejection Reason'

    name = fields.Char(string='Reason', required=True)
    active = fields.Boolean(string='Active', default=True)
