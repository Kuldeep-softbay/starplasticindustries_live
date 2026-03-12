from odoo import models, fields, tools


class RunningCavitySummary(models.Model):
    _name = 'running.cavity.summary'
    _description = 'Running Cavity Summary'
    _auto = False

    date = fields.Date()
    lot_id = fields.Many2one('stock.lot', string="Batch Number")
    machine_id = fields.Many2one('mrp.workcenter')
    shift_id = fields.Many2one('work.center.shift')
    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False,
    )
    product_id = fields.Many2one('product.product', string='Item')
    supervisor_one_id = fields.Many2one('res.users')
    supervisor_two_id = fields.Many2one('res.users')
    running_cavity = fields.Integer()
    mould_cavity = fields.Integer()
    action = fields.Char(string='Action')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action_by = fields.Many2one('res.users')

    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                rec.shift_display = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_display = False

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'running_cavity_summary')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW running_cavity_summary AS (
                SELECT
                    row_number() OVER () AS id,
                    wcs.date,
                    mo.lot_id,
                    wo.workcenter_id AS machine_id,
                    wcs.id AS shift_id,
                    wcs.mold_id AS product_id,
                    wcs.supervisor_one_id,
                    wcs.supervisor_two_id,
                    wcs.cavity AS running_cavity,
                    rwc.cavity AS mould_cavity,
                    wcs.cavity_action AS action,
                    wcs.cavity_reason_id AS reason_id,
                    wcs.cavity_acknowledged_by AS action_by
                FROM work_center_shift wcs
                JOIN mrp_production mo ON mo.id = wcs.production_id
                JOIN mrp_workorder wo ON wo.production_id = mo.id
                JOIN mrp_routing_workcenter rwc ON rwc.id = wo.operation_id
                WHERE
                    COALESCE(wcs.cavity_acknowledged, false) = true
                    AND COALESCE(wcs.cavity, 0) != COALESCE(rwc.cavity, 0)
            )
        """)

