from odoo import api, models, fields
from odoo.exceptions import ValidationError


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    name = fields.Char(string="Mould Name")
    workcenter_ids = fields.Many2many(
        'mrp.workcenter',
        'workcenter_id',
        string="Suitable Machines"
    )

    cavity = fields.Integer(string="Cavity", default=1, help="Number of cavities")
    standard_cycle_time = fields.Float(string="Std Cycle Time")
    cycle_time = fields.Float(string="Cycle Time")
    standard_cycle_time_hourly = fields.Float(
        string="Std Cycle Time band for hourly entery")
    standard_production_per_hour = fields.Float(
        string="Std Production per Hour",
        compute="_compute_standard_production_per_hour",
        store=True
    )
    cycle_time_tolerance = fields.Float(string="Cycle Time Tolerance (%)")
    cycle_time_manual_seconds = fields.Float(
        string="Cycle Time Manual (Seconds)"
    )

    time_cycle_manual = fields.Float(
        string="Cycle Time Manual (Minutes)",
        compute="_compute_time_cycle_manual",
        store=True
    )

    @api.depends('cavity', 'cycle_time', 'standard_cycle_time')
    def _compute_standard_production_per_hour(self):
        for rec in self:
            cycle_seconds = 0.0

            if rec.standard_cycle_time and rec.standard_cycle_time > 0:
                cycle_seconds = rec.standard_cycle_time

            elif rec.cycle_time and rec.cycle_time > 0:
                cycle_seconds = rec.cycle_time

            if cycle_seconds > 0 and rec.cavity > 0:
                rec.standard_production_per_hour = (3600.0 / cycle_seconds) * rec.cavity
            else:
                rec.standard_production_per_hour = 0.0

    @api.depends('cycle_time_manual_seconds')
    def _compute_time_cycle_manual(self):
        for rec in self:
            rec.time_cycle_manual = (
                rec.cycle_time_manual_seconds / 60.0
                if rec.cycle_time_manual_seconds > 0
                else 0.0
            )

    @api.onchange('cycle_time_manual_seconds')
    def _onchange_cycle_time_manual_seconds(self):
        self.time_cycle_manual = (
            self.cycle_time_manual_seconds / 60.0
            if self.cycle_time_manual_seconds > 0
            else 0.0
        )

    def compute_operation_duration(self, required_qty):
        self.ensure_one()

        if not self.time_cycle_manual or self.cavity < 1:
            return 0.0

        if required_qty <= self.cavity:
            return self.time_cycle_manual

        cycles = required_qty / self.cavity
        return cycles * self.time_cycle_manual

    
    @api.constrains('cavity', 'standard_cycle_time', 'cycle_time_tolerance')
    def _check_positive_values(self):
        for rec in self:
            if rec.cavity is not None and rec.cavity < 1:
                raise ValidationError("Cavity must be at least 1.")
            if rec.standard_cycle_time is not None and rec.standard_cycle_time < 0:
                raise ValidationError("Standard cycle time must be non-negative.")
            if rec.cycle_time_tolerance is not None and rec.cycle_time_tolerance < 0:
                raise ValidationError("Cycle time tolerance must be non-negative.")