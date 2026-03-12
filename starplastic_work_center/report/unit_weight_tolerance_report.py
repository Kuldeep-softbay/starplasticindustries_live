from odoo import models, fields, tools

class WorkCenterShift(models.Model):
    _inherit = 'work.center.shift'

    unit_weight_acknowledged = fields.Boolean(default=False)
    unit_weight_reason_id = fields.Many2one(
        'running.cavity.reason',
        string='Reason'
    )
    unit_weight_action = fields.Char(string='Action')
    unit_weight_acknowledged_by = fields.Many2one(
        'res.users',
        string='Action By'
    )

class UnitWeightToleranceWizard(models.TransientModel):
    _name = 'unit.weight.tolerance.wizard'
    _description = 'Unit Weight Tolerance Wizard'

    shift_id = fields.Many2one(
        'work.center.shift',
        required=True,
        readonly=True
    )
    reason_id = fields.Many2one(
        'running.cavity.reason',
        required=True
    )
    action = fields.Char(required=True)

    def action_confirm(self):
        self.ensure_one()
        self.shift_id.write({
            'unit_weight_acknowledged': True,
            'unit_weight_reason_id': self.reason_id.id,
            'unit_weight_action': self.action,
            'unit_weight_acknowledged_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}

class UnitWeightToleranceReport(models.Model):
    _name = 'unit.weight.tolerance.report'
    _description = 'Unit Weight Tolerance Report'
    _auto = False

    date = fields.Date(string='Date')
    lot_id = fields.Many2one('stock.lot', string='Batch Number')
    machine_id = fields.Many2one('mrp.workcenter', string='Machine')
    shift_id = fields.Many2one('work.center.shift', string='Shift')
    shift_display = fields.Char(compute='_compute_shift_display', store=False)
    product_id = fields.Many2one('product.product', string='Item')
    supervisor_one_id = fields.Many2one('res.users', string='Supervisor 1')
    supervisor_two_id = fields.Many2one('res.users', string='Supervisor 2')
    time_slot = fields.Char(string='Time Slot')
    actual_weight = fields.Float(string='Actual Weight')
    std_weight = fields.Float(string='Std Weight')
    tolerance = fields.Float(string='Tolerance (+/-)')


    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                rec.shift_display = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_display = False

    def action_hide(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Acknowledge Unit Weight Tolerance',
            'res_model': 'unit.weight.tolerance.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shift_id': self.shift_id.id,
            }
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'unit_weight_tolerance_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW unit_weight_tolerance_report AS (
                SELECT
                    row_number() OVER () AS id,

                    DATE(whe.create_date) AS date,
                    mo.lot_id,
                    wo.workcenter_id AS machine_id,
                    whe.shift_id AS shift_id,
                    mo.product_id AS product_id,

                    ws.supervisor_one_id,
                    ws.supervisor_two_id,

                    whe.time AS time_slot,
                    whe.unit_weight AS actual_weight,

                    pt.weight AS std_weight,

                    (whe.unit_weight - pt.weight) AS tolerance

                FROM work_center_hourly_entry whe

                JOIN mrp_production mo
                    ON mo.id = whe.production_id

                JOIN mrp_workorder wo
                    ON wo.production_id = mo.id

                JOIN work_center_shift ws
                    ON ws.id = whe.shift_id

                JOIN product_product pp
                    ON pp.id = mo.product_id

                JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id

                LEFT JOIN stock_move_line sml
                    ON sml.production_id = mo.id
                    AND sml.product_id = mo.product_id

                WHERE
                    COALESCE(ws.unit_weight_acknowledged, false) = false

                    -- IMPORTANT CONDITION
                    AND whe.unit_weight IS NOT NULL
                    AND pt.weight IS NOT NULL
                    AND whe.unit_weight <> pt.weight
                )
            """)


class UnitWeightToleranceActionLog(models.Model):
    _name = 'unit.weight.tolerance.action.log'
    _description = 'Unit Weight Tolerance Action Log'

    report_id = fields.Integer()
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action = fields.Char()
    action_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user
    )
    date = fields.Datetime(default=fields.Datetime.now)

