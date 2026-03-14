from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WCShiftTemplate(models.Model):
    _name = 'wc.shift.template'
    _description = 'Shift Template (8-hour patterns)'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(required=True)
    code = fields.Selection(
        [('F', 'A'), ('S', 'B'), ('T', 'C')],
        required=True,
        help="Short code for the shift (A/B/C)."
    )
    start_hour = fields.Integer(string='Start Hour (0-23)', required=True)
    duration_hours = fields.Integer(string='Duration (hours)', default=8, required=True)
    sequence = fields.Integer(default=10, help="Ordering in lists")

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Shift code must be unique.'),
    ]

    @api.constrains('start_hour', 'duration_hours')
    def _check_shift_hours(self):
        for rec in self:
            if rec.duration_hours != 8:
                raise ValidationError(_("Shift duration must be exactly 8 hours."))
            if rec.start_hour < 0 or rec.start_hour > 23:
                raise ValidationError(_("Start hour must be between 0 and 23."))

    @api.onchange('code')
    def _onchange_shift_code(self):
        """Set start hour based on shift code"""
        if self.code == 'F':
            self.start_hour = 6  # 6 AM - 2 PM
        elif self.code == 'S':
            self.start_hour = 14  # 2 PM - 10 PM
        elif self.code == 'T':
            self.start_hour = 22  # 10 PM - 6 AM

    @api.constrains('code', 'start_hour')
    def _check_shift_time_validity(self):
        for rec in self:
            if rec.code == 'F' and rec.start_hour != 6:
                raise ValidationError(_("FS must start at 6 AM"))
            elif rec.code == 'S' and rec.start_hour != 14:
                raise ValidationError(_("SS must start at 2 PM"))
            elif rec.code == 'T' and rec.start_hour != 22:
                raise ValidationError(_("TS must start at 10 PM"))
    @api.depends('code')
    def _compute_start_hour(self):
        """Automatically set start hour based on shift code"""
        for rec in self:
            if rec.code == 'F':
                rec.start_hour = 6  # 6 AM to 2 PM
            elif rec.code == 'S':
                rec.start_hour = 14  # 2 PM to 10 PM
            elif rec.code == 'T':
                rec.start_hour = 22  # 10 PM to 6 AM

    def get_time_keys(self):
        """Return 8 time keys for the shift."""
        self.ensure_one()
        keys = []
        start = self.start_hour
        for i in range(8):  # 8-hour shift
            hour = (start + i) % 24
            next_hour = (hour + 1) % 24
            key = f"{hour:02d}-{next_hour:02d}"
            keys.append(key)
        return keys


class WCShift(models.Model):
    _name = 'work.center.shift'
    _description = 'Work Center Shift Instance'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    entry_ids = fields.One2many(
        'work.center.hourly.entry',
        'shift_id',
        string='Hourly Entries'
    )

    total_produced_qty = fields.Float(
        string='Total Produced Qty',
        compute='_compute_total_produced_qty',
        store=True
    )
    remaining_qty = fields.Float(
        string='Remaining Qty (Nos)',
        compute='_compute_remaining_qty',
        store=True
    )

    minimum_target_nos = fields.Float(
        string='Minimum Target (Nos)',
        compute='_compute_minimum_target',
        store=True
    )

    minimum_target_kg = fields.Float(
        string='Minimum Target (KG)',
        compute='_compute_minimum_target',
        store=True
    )

    hourly_entry_ids = fields.One2many(
        'work.center.hourly.entry',
        'shift_id',
        string='Hourly Entries for Target Calculation'
    )

    channel_no = fields.Char("Ch.No")

    workorder_id = fields.Many2one(
        'mrp.workorder',
        string="Work Order"
    )

    machine_id = fields.Many2one(
        'mrp.workcenter',
        string="Machine",
        compute="_compute_machine",
        store=True
    )

    unit_weight_avg = fields.Float("Unit Weight Average")

    production_kg = fields.Float("Production Kg Total")

    production_nos = fields.Float("Production Nos")

    error_set = fields.Float("Error Set")

    error_set_unit_weight = fields.Float("Error Set Unit Weight")

    final_production_kg = fields.Float(
        compute="_compute_final_values",
        store=True
    )

    final_production_nos = fields.Float(
        compute="_compute_final_values",
        store=True
    )

    hourly_entry_id = fields.Many2one(
        'work.center.hourly.entry',
        string="Hourly Entry"
    )

    unit_weight_avg = fields.Float(
        string="Unit Weight Average",
        compute="_compute_unit_weight",
        store=True
    )

    @api.depends('hourly_entry_id')
    def _compute_unit_weight(self):
        for rec in self:
            if rec.hourly_entry_id:
                rec.unit_weight_avg = rec.hourly_entry_id.weight_gm
            else:
                rec.unit_weight_avg = 0

    @api.depends('workorder_id')
    def _compute_machine(self):
        for rec in self:
            if rec.workorder_id:
                rec.machine_id = rec.workorder_id.workcenter_id.id
            elif rec.production_id.workorder_ids:
                rec.machine_id = rec.production_id.workorder_ids[0].workcenter_id.id
            else:
                rec.machine_id = False

    @api.depends('production_kg', 'error_set', 'unit_weight_avg')
    def _compute_final_values(self):
        for rec in self:

            rec.final_production_kg = rec.production_kg - rec.error_set

            if rec.unit_weight_avg:
                rec.final_production_nos = rec.final_production_kg / rec.unit_weight_avg
            else:
                rec.final_production_nos = 0

    @api.depends(
        'hourly_target_qty',
        'cavity',
        'cycle_time_sec',
        'mold_id.weight_gm'
    )
    def _compute_minimum_target(self):
        for rec in self:

            hourly = rec.hourly_target_qty or 0.0

            unit_weight = (rec.mold_id.weight_gm or 0.0) / 1000.0

            min_nos = hourly * 0.95

            rec.minimum_target_nos = round(min_nos, 0)
            rec.minimum_target_kg = round(min_nos * unit_weight, 2)

    @api.depends('production_id', 'production_id.product_qty', 'total_produced_qty')
    def _compute_remaining_qty(self):
        for rec in self:
            if rec.production_id:
                total_produced = sum(
                    self.search([
                        ('production_id', '=', rec.production_id.id)
                    ]).mapped('total_produced_qty')
                )
                rec.remaining_qty = max(
                    rec.production_id.product_qty - total_produced, 0
                )
            else:
                rec.remaining_qty = 0


    downtime_summary_ids = fields.One2many(
        'work.center.shift.downtime.summary',
        'shift_id',
        string='Downtime Reasons Summary',
        compute='_compute_downtime_summary',
        store=True
    )

    @api.depends(
        'entry_ids.time',
        'entry_ids.reason_line_ids.reason_id',
        'entry_ids.reason_line_ids.sub_reason_id',
        'entry_ids.reason_line_ids.duration_minutes',
    )
    def _compute_downtime_summary(self):
        for shift in self:
            shift.downtime_summary_ids = [(5, 0, 0)]
            summary = {}

            for entry in shift.entry_ids:
                for line in entry.reason_line_ids:
                    key = (
                        entry.time,
                        line.reason_id.id,
                        line.sub_reason_id.id or False
                    )
                    summary[key] = summary.get(key, 0.0) + (line.duration_minutes or 0.0)

            records = []
            for (hour_slot, reason_id, sub_reason_id), total in summary.items():
                records.append((0, 0, {
                    'hour_slot': hour_slot,
                    'reason_id': reason_id,
                    'sub_reason_id': sub_reason_id,
                    'total_duration': total,
                }))

            shift.downtime_summary_ids = records

    # =========================
    # COMPUTE
    # =========================
    @api.depends('entry_ids.produced_qty_number')
    def _compute_total_produced_qty(self):
        for shift in self:
            shift.total_produced_qty = sum(
                shift.entry_ids.mapped('produced_qty_number')
            )

    name = fields.Char(compute='_compute_name', store=True, tracking=True)
    production_id = fields.Many2one(
        'mrp.production', required=True, tracking=True, ondelete='cascade'
    )
    date = fields.Date(required=True, tracking=True)
    template_id = fields.Many2one('wc.shift.template', required=True, tracking=True)

    supervisor_one_id = fields.Many2one('res.users', tracking=True)
    supervisor_two_id = fields.Many2one('res.users', tracking=True)

    mold_id = fields.Many2one(
        'product.product', string='Running Mold', tracking=True
    )
    state = fields.Selection(
        [('draft', 'Draft'), ('generated', 'Generated'), ('done', 'Done')],
        default='draft', required=True, tracking=True
    )

    cavity = fields.Integer(required=True, tracking=True)
    cycle_time_sec = fields.Float(required=True, tracking=True)

    # =========================
    # WEIGHT / PCS FIELDS
    # =========================

    unit_waight = fields.Float(
        string='Unit Weight (kg)',
        tracking=True,
        help="Weight of 1 piece in KG"
    )

    total_kg = fields.Float(
        string='Total KG',
        tracking=True
    )

    total_pcs = fields.Integer(
        string='Total Pcs',
        tracking=True
    )
   
    hourly_target_qty = fields.Float(string='Hourly Target (units/hr)', compute='_compute_hourly_target', store=True)

    code = fields.Selection(
        [('F', 'FS'), ('S', 'SS'), ('T', 'TS')],
        string='Shift Code',
        help='Code representing the shift (F, S, or T).'
    )

    # =========================
    # ONCHANGE LOGIC
    # =========================

    @api.onchange('mold_id')
    def _onchange_mold_id_set_unit_weight(self):
        """Auto fetch unit weight from product"""
        for rec in self:
            if rec.mold_id:
                # Use product weight (Odoo standard field)
                rec.unit_waight = rec.mold_id.weight or 0.0

    @api.onchange('total_kg', 'unit_waight')
    def _onchange_total_kg(self):
        """If KG is entered → calculate PCS"""
        for rec in self:
            if rec.total_kg and rec.unit_waight:
                rec.total_pcs = int(rec.total_kg / rec.unit_waight)

    @api.onchange('total_pcs', 'unit_waight')
    def _onchange_total_pcs(self):
        """If PCS is entered → calculate KG"""
        for rec in self:
            if rec.total_pcs and rec.unit_waight:
                rec.total_kg = rec.total_pcs * rec.unit_waight

    # =========================
    # DATA SAFETY
    # =========================

    @api.constrains('unit_waight')
    def _check_unit_weight(self):
        for rec in self:
            if rec.unit_waight < 0:
                raise ValidationError(_("Unit weight cannot be negative."))

    # =========================
    # OPTIONAL: NAME COMPUTE
    # =========================

    @api.depends('production_id', 'date')
    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.production_id.name or ''} - {rec.date or ''}"

    _sql_constraints = [
        ('uniq_mo_date_template', 'unique(production_id, date, template_id)',
         'A shift already exists for this MO, date, and template.')
    ]
   

    @api.depends('production_id', 'date', 'template_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.production_id:
                parts.append(rec.production_id.name)
            if rec.date:
                parts.append(rec.date.strftime('%Y-%m-%d'))
            if rec.template_id and rec.template_id.code:
                parts.append(f"Shift {rec.template_id.code}")
            rec.name = " - ".join(parts) if parts else "Shift"

    @api.depends('cavity', 'cycle_time_sec')
    def _compute_hourly_target(self):
        for rec in self:
            target = 0.0
            if rec.cavity and rec.cycle_time_sec:
                # units per hour = (3600 / cycle_time_sec) * cavity
                target = round((3600.0 / rec.cycle_time_sec) * rec.cavity, 0)
            rec.hourly_target_qty = target

    def action_done(self):
        self.write({'state': 'done'})