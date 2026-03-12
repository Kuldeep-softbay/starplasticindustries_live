from odoo import models, fields, tools


class WorkCenterShift(models.Model):
    _inherit = 'work.center.shift'

    error_tolerance_acknowledged = fields.Boolean(default=False)
    error_tolerance_reason_id = fields.Many2one(
        'running.cavity.reason',
        string='Reason'
    )
    error_tolerance_action = fields.Char(string='Action')
    error_tolerance_acknowledged_by = fields.Many2one(
        'res.users',
        string='Action By'
    )
    store_inward_kg = fields.Float(
        string="Production KG Inward by Store"
    )

class ErrorSetToleranceReasonWizard(models.TransientModel):
    _name = 'error.set.tolerance.reason.wizard'
    _description = 'Error Set Tolerance Reason Wizard'

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
            'error_tolerance_acknowledged': True,
            'error_tolerance_reason_id': self.reason_id.id,
            'error_tolerance_action': self.action,
            'error_tolerance_acknowledged_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}


class ErrorSetToleranceReport(models.Model):
    _name = 'error.set.tolerance.report'
    _description = 'Error Set Tolerance Report'
    _auto = False

    date = fields.Date()
    workorder_no = fields.Char(string="W.O Number")
    product_id = fields.Many2one('product.product', string="Item")
    workcenter_id = fields.Many2one('mrp.workcenter', string="Machine")

    shift_id = fields.Many2one(
        'work.center.shift'
    )

    shift_display = fields.Char(
        compute="_compute_shift_display",
        store=False
    )

    production_kg_workshop = fields.Float(string="Production KG @ Workshop")
    production_kg_store = fields.Float(string="Production KG Inward by Store")
    difference_kg = fields.Float(string="Difference KG")
    difference_percent = fields.Float(string="Difference %")

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
            'name': 'Acknowledge Error Set Tolerance Action',
            'res_model': 'error.set.tolerance.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shift_id': self.shift_id.id,
            }
    }


    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'error_set_tolerance_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW error_set_tolerance_report AS (
                SELECT
                    row_number() OVER () AS id,

                    wcs.date,
                    mo.name AS workorder_no,
                    mo.product_id AS product_id,
                    wo.workcenter_id AS workcenter_id,
                    wcs.id AS shift_id,

                    /* Workshop Production */
                    COALESCE(SUM(whe.produced_weight_kg), 0)
                        AS production_kg_workshop,

                    /* Store Inward */
                    COALESCE(wcs.store_inward_kg, 0)
                        AS production_kg_store,

                    /* Difference KG */
                    (
                        COALESCE(SUM(whe.produced_weight_kg), 0)
                        - COALESCE(wcs.store_inward_kg, 0)
                    ) AS difference_kg,

                    /* Correct Difference Percentage */
                    CASE
                        WHEN COALESCE(SUM(whe.produced_weight_kg), 0) = 0 THEN 0
                        ELSE
                            ROUND(
                                (
                                    (
                                        COALESCE(SUM(whe.produced_weight_kg), 0)::numeric
                                        - COALESCE(wcs.store_inward_kg, 0)::numeric
                                    )
                                    /
                                    NULLIF(
                                        COALESCE(SUM(whe.produced_weight_kg), 0)::numeric,
                                        0
                                    )
                                ) * 100,
                                2
                            )
                    END AS difference_percent

                FROM work_center_shift wcs

                JOIN mrp_production mo
                    ON mo.id = wcs.production_id

                JOIN mrp_workorder wo
                    ON wo.production_id = mo.id

                LEFT JOIN work_center_hourly_entry whe
                    ON whe.shift_id = wcs.id

                WHERE COALESCE(wcs.error_tolerance_acknowledged, false) = false

                GROUP BY
                    wcs.id,
                    wcs.date,
                    mo.name,
                    mo.product_id,
                    wo.workcenter_id,
                    wcs.store_inward_kg
            )
        """)

class ErrorSetToleranceActionLog(models.Model):
    _name = 'error.set.tolerance.action.log'
    _description = 'Error Set Tolerance Action Log'

    report_id = fields.Integer()
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action = fields.Char()
    action_by = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user
    )
    date = fields.Datetime(default=fields.Datetime.now)
