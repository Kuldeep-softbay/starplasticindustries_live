from odoo import models, fields

class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    machine_no = fields.Char(string="Machine No")
    name = fields.Char(string="Machine Name")
    machine_type = fields.Selection([
        ('blow_molding', 'Blow Molding'),
        ('injection', 'Injection Molding'),
        ('blow_injection', 'Blow Injection molding'),
        ('other', 'Other'),
    ], string="Machine Type")

    capacity_ton = fields.Float(string="Capacity (TON)")
    location_id = fields.Many2one('stock.location', string="Location")
    remark = fields.Text(string="Remark")
    max_power = fields.Float(string="Max Power Consumption (Unit/hour)")
    outgoing_job = fields.Boolean(string="Outgoing Job?")
    company_name = fields.Char(string="Company Name")
    machine_shift = fields.Selection([
        ('day', 'Day Night'),
        ('3shift', '3 Shift'),
    ], string="Machine Shift")
