from odoo import models, fields, tools


class StdCycleTimeSummary(models.Model):
    _name = 'std.cycle.time.summary'
    _description = 'Standard Cycle Time Summary'
    _auto = False

    date = fields.Date()
    lot_id = fields.Many2one('stock.lot', string="Batch Number")
    machine_id = fields.Many2one('mrp.workcenter')
    shift_id = fields.Many2one('work.center.shift')
    shift_display = fields.Char(compute='_compute_shift_display', store=False)
    product_id = fields.Many2one('product.product')
    supervisor_one_id = fields.Many2one('res.users')
    supervisor_two_id = fields.Many2one('res.users')
    set_cycle_time = fields.Float()
    std_cycle_time = fields.Float(string='Running Cycle Time')
    tolerance = fields.Float()
    reason_id = fields.Many2one('running.cavity.reason')
    action = fields.Char()
    action_by = fields.Many2one('res.users')

    def _compute_shift_display(self):
        for rec in self:
            rec.shift_display = (
                rec.shift_id.name.split('-')[-1].strip()
                if rec.shift_id and rec.shift_id.name
                else False
            )

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'std_cycle_time_summary')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW std_cycle_time_summary AS (
                SELECT
                    row_number() OVER () AS id,

                    wcs.id AS shift_id,
                    wcs.date AS date,
                    mo.lot_id,
                    wo.workcenter_id AS machine_id,
                    wcs.mold_id AS product_id,

                    wcs.supervisor_one_id,
                    wcs.supervisor_two_id,

                    rwc.cycle_time AS set_cycle_time,
                    wcs.cycle_time_sec AS std_cycle_time,
                    pt.unit_weight_tolerance AS tolerance,

                    wcs.cycle_time_reason_id AS reason_id,
                    wcs.cycle_time_action AS action,
                    wcs.cycle_time_acknowledged_by AS action_by

                FROM work_center_shift wcs
                JOIN mrp_production mo
                    ON mo.id = wcs.production_id
                JOIN mrp_workorder wo
                    ON wo.production_id = mo.id
                JOIN mrp_routing_workcenter rwc
                    ON rwc.id = wo.operation_id
                JOIN product_product pp
                    ON pp.id = wcs.mold_id
                JOIN product_template pt
                    ON pt.id = pp.product_tmpl_id

                WHERE
                    COALESCE(wcs.cycle_time_acknowledged, false) = true
                    AND COALESCE(wcs.cycle_time_sec, 0) 
                        != COALESCE(rwc.cycle_time, 0)
            )
        """)

