from odoo import models, fields, tools


class UnitWeightToleranceSummary(models.Model):
    _name = 'unit.weight.tolerance.summary'
    _description = 'Unit Weight Tolerance Summary'
    _auto = False

    date = fields.Date(string='Date')
    lot_id = fields.Many2one('stock.lot', string='Batch No')
    machine_id = fields.Many2one('mrp.workcenter', string='Machine')
    shift_id = fields.Many2one('work.center.shift', string='Shift')
    shift_desplay = fields.Char(
        compute='_compute_shift_display',
        store=False,
    )
    product_id = fields.Many2one('product.product', string='Item')

    supervisor_one_id = fields.Many2one('res.users', string='Supervisor 1')
    supervisor_two_id = fields.Many2one('res.users', string='Supervisor 2')
    time = fields.Char(string='Time')

    actual_weight = fields.Float(string='Actual Weight')
    std_weight = fields.Float(string='Std Weight')
    tolerance = fields.Float(string='Tolerance (+/-)')

    action = fields.Char(string='Action')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action_by = fields.Many2one('res.users', string='Action By')

    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                rec.shift_desplay = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_desplay = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'unit_weight_tolerance_summary')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW unit_weight_tolerance_summary AS (
                SELECT
                    row_number() OVER () AS id,

                    DATE(whe.create_date) AS date,
                    mo.lot_id AS lot_id,

                    wo.workcenter_id AS machine_id,
                    whe.shift_id AS shift_id,
                    mo.product_id AS product_id,

                    ws.supervisor_one_id,
                    ws.supervisor_two_id,

                    whe.time AS time,
                    whe.unit_weight AS actual_weight,

                    pt.weight AS std_weight,
                    (whe.unit_weight - pt.weight) AS tolerance,

                    ws.unit_weight_reason_id AS reason_id,
                    ws.unit_weight_action AS action,
                    ws.unit_weight_acknowledged_by AS action_by

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
                    COALESCE(ws.unit_weight_acknowledged, false) = true
                    AND whe.unit_weight IS NOT NULL
                    AND pt.weight IS NOT NULL
                    AND ABS(whe.unit_weight - pt.weight) > 0.0001
            )
        """)
