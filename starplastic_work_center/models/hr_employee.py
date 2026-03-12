from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    type = fields.Char(string="Employee Type")