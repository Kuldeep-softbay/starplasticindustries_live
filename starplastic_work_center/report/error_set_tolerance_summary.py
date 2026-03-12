from odoo import models, fields, tools


class ErrorSetToleranceSummary(models.Model):
    _name = 'error.set.tolerance.summary'
    _description = 'Error Set Tolerance Summary'
    _auto = False

    date = fields.Date()
    workorder_no = fields.Char()
    machine_id = fields.Many2one('mrp.workcenter')

    shift_id = fields.Many2one(
        'work.center.shift',
    )

    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False
    )

    product_id = fields.Many2one('product.product', string='Item')

    production_kg_workshop = fields.Float()
    production_kg_store = fields.Float()
    difference_kg = fields.Float()
    difference_percent = fields.Float()

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
        tools.drop_view_if_exists(self.env.cr, 'error_set_tolerance_summary')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW error_set_tolerance_summary AS (
                SELECT
                    row_number() OVER () AS id,

                    wcs.date,
                    mo.name AS workorder_no,
                    wo.workcenter_id AS machine_id,
                    wcs.id AS shift_id,
                    mo.product_id AS product_id,

                    COALESCE(SUM(whe.produced_weight_kg), 0)
                        AS production_kg_workshop,

                    COALESCE(wcs.store_inward_kg, 0)
                        AS production_kg_store,

                    COALESCE(SUM(whe.produced_weight_kg), 0)
                        - COALESCE(wcs.store_inward_kg, 0)
                        AS difference_kg,

                    CASE
                        WHEN COALESCE(SUM(whe.produced_weight_kg), 0) = 0 THEN 0
                        ELSE
                            ROUND(
                                (
                                    (
                                        COALESCE(SUM(whe.produced_weight_kg), 0)
                                        - COALESCE(wcs.store_inward_kg, 0)
                                    )
                                    / NULLIF(SUM(whe.produced_weight_kg), 0)
                                )::numeric * 100,
                                2
                            )
                    END AS difference_percent,

                    wcs.error_tolerance_action AS action,
                    wcs.error_tolerance_reason_id AS reason_id,
                    wcs.error_tolerance_acknowledged_by AS action_by

                FROM work_center_shift wcs

                JOIN mrp_production mo
                    ON mo.id = wcs.production_id

                JOIN mrp_workorder wo
                    ON wo.production_id = mo.id

                LEFT JOIN work_center_hourly_entry whe
                    ON whe.shift_id = wcs.id

                WHERE COALESCE(wcs.error_tolerance_acknowledged, false) = true

                GROUP BY
                    wcs.id,
                    wcs.date,
                    mo.name,
                    wo.workcenter_id,
                    mo.product_id,
                    wcs.store_inward_kg,
                    wcs.error_tolerance_action,
                    wcs.error_tolerance_reason_id,
                    wcs.error_tolerance_acknowledged_by
            )
        """)
