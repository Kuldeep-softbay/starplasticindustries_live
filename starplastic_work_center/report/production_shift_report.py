from odoo import models, fields, tools


class MrpProductionSlip(models.Model):
    _name = "mrp.production.slip"
    _description = "Production Slip Report"
    _auto = False
    _order = "date desc"

    # Basic Info
    date = fields.Date(string="Date", readonly=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine", readonly=True)
    time_slot = fields.Char(string="Time", readonly=True)
    log_time = fields.Datetime(string="Log Time", readonly=True)
    product_id = fields.Many2one("product.product", string="Product", readonly=True)
    shift_id = fields.Many2one("work.center.shift", string="Shift", readonly=True)
    production_id = fields.Many2one("mrp.production", string="MO", readonly=True)

    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False,
    )

    def _compute_shift_display(self):
        for rec in self:
            if rec.shift_id and rec.shift_id.name:
                rec.shift_display = rec.shift_id.name.split('-')[-1].strip()
            else:
                rec.shift_display = False

    cavity = fields.Char(string="Cavity", readonly=True)

    operator_one_id = fields.Many2one("res.users", string="Operator 1", readonly=True)
    operator_two_id = fields.Many2one("res.users", string="Operator 2", readonly=True)
    supervisor_one_id = fields.Many2one("res.users", string="Supervisor 1", readonly=True)
    supervisor_two_id = fields.Many2one("res.users", string="Supervisor 2", readonly=True)

    unit_weight = fields.Float(string="Unit Weight", readonly=True)
    runing_cavity = fields.Float(string="Running Cavity", readonly=True)

    # Production Data
    std_cycle_time = fields.Float(string="Std Cycle Time", readonly=True)
    actual_cycle_time = fields.Float(string="Actual Cycle Time", readonly=True)
    qc_check = fields.Boolean(string="QC Check", readonly=True)

    production_qty = fields.Float(string="Production Qty", readonly=True)
    production_kg = fields.Float(string="Production (Kg)", readonly=True)
    rejection_qty = fields.Float(string="Rejection Qty", readonly=True)
    rejection_kg = fields.Float(string="Rejection (Kg)", readonly=True)
    rejection_reason = fields.Char(string="Rejection Reason", readonly=True)

    # Downtime
    shut_down_time = fields.Float(string="Shutdown Time", readonly=True)
    reason_id = fields.Many2one("wc.downtime.reason", string="Reason", readonly=True)
    sub_reason_id = fields.Many2one("wc.downtime.subreason", string="Sub Reason", readonly=True)
    explanation = fields.Char(string="Explanation", readonly=True)

    efficiency = fields.Float(string="Efficiency", readonly=True)
    product_efficiency = fields.Float(string="Product Efficiency", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE VIEW mrp_production_slip AS (
                SELECT
                    row_number() OVER() AS id,

                    DATE(whe.create_date) AS date,
                    wo.workcenter_id,
                    whe.time AS time_slot,
                    whe.create_date AS log_time,
                    whe.production_id,
                    mo.product_id,
                    whe.shift_id,

                    mo.origin AS mould_no,
                    wo.name AS cavity,

                    whe.operator_one_id,
                    whe.operator_two_id,
                    ws.supervisor_one_id,
                    ws.supervisor_two_id,

                    whe.unit_weight,
                    mo.cavity AS runing_cavity,

                    wo.duration_expected AS std_cycle_time,
                    whe.actual_cycle_time,
                    whe.qc_check,

                    whe.produced_qty_number AS production_qty,
                    whe.produced_weight_kg AS production_kg,
                    whe.reject_qty_number AS rejection_qty,
                    whe.reject_weight_kg AS rejection_kg,
                    whe.rejection_reason,

                    COALESCE(SUM(rl.duration_minutes), 0) AS shut_down_time,
                    MAX(rl.reason_id) AS reason_id,
                    MAX(rl.sub_reason_id) AS sub_reason_id,

                    NULL::text AS explanation,

                    /* Worker Efficiency */
                    CASE
                        WHEN wo.duration_expected IS NOT NULL
                             AND wo.duration_expected != 0
                             AND mo.cavity IS NOT NULL
                             AND mo.cavity != 0
                        THEN
                            (
                                whe.produced_qty_number /
                                NULLIF((3600.0 / wo.duration_expected) * mo.cavity, 0)
                            )
                            -
                            (COALESCE(SUM(rl.duration_minutes), 0) / 60.0)
                        ELSE 0
                    END AS efficiency,

                    /* Product Efficiency */
                    CASE
                        WHEN wo.duration_expected IS NOT NULL
                             AND wo.duration_expected != 0
                             AND mo.cavity IS NOT NULL
                             AND mo.cavity != 0
                        THEN
                            (
                                whe.produced_qty_number /
                                NULLIF((3600.0 / wo.duration_expected) * mo.cavity, 0)
                            )
                            -
                            (
                                COALESCE(
                                    SUM(
                                        CASE
                                            WHEN r.affect_product_efficiency = TRUE
                                            THEN rl.duration_minutes
                                            ELSE 0
                                        END
                                    ), 0
                                ) / 60.0
                            )
                        ELSE 0
                    END AS product_efficiency

                FROM work_center_hourly_entry whe

                LEFT JOIN mrp_production mo
                    ON mo.id = whe.production_id

                LEFT JOIN mrp_workorder wo
                    ON wo.production_id = mo.id

                LEFT JOIN work_center_shift ws
                    ON ws.id = whe.shift_id

                LEFT JOIN work_center_hourly_entry_reason_line rl
                    ON rl.hourly_entry_id = whe.id

                LEFT JOIN wc_downtime_reason r
                    ON r.id = rl.reason_id

                GROUP BY
                    whe.id,
                    wo.workcenter_id,
                    whe.time,
                    whe.create_date,
                    whe.production_id,
                    mo.product_id,
                    whe.shift_id,
                    mo.origin,
                    wo.name,
                    whe.operator_one_id,
                    whe.operator_two_id,
                    ws.supervisor_one_id,
                    ws.supervisor_two_id,
                    whe.unit_weight,
                    mo.cavity,
                    wo.duration_expected,
                    whe.actual_cycle_time,
                    whe.qc_check,
                    whe.produced_qty_number,
                    whe.produced_weight_kg,
                    whe.reject_qty_number,
                    whe.reject_weight_kg,
                    whe.rejection_reason
            )
        """)
