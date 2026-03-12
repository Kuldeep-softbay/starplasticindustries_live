from odoo import models, fields, tools


class ProductionDelaySummary(models.Model):
    _name = 'production.delay.summary'
    _description = 'Production Delay Summary'
    _auto = False

    wo_date = fields.Date(string='W.O Date')
    wo_no = fields.Char(string='W.O No')

    machine_id = fields.Many2one('mrp.workcenter', string='Machine')
    product_id = fields.Many2one('product.product', string='Item')
    party_id = fields.Many2one('job.party.work', string='Party')

    qty = fields.Float(string='Qty')

    planned_start_date = fields.Datetime(string='Planned Start Date')
    actual_start_date = fields.Datetime(string='Actual Start Date')

    exp_delivery_date = fields.Date(string='Exp. Delivery Date')
    production_close_date = fields.Date(string='Production Close Date')
    production_end_date = fields.Datetime(string='Production End Date')

    production_delay = fields.Integer(string='Production Delay (Min)')

    action = fields.Char(string='Action')
    reason_id = fields.Many2one('running.cavity.reason', string='Reason')
    action_by = fields.Many2one('res.users', string='Action By')

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'production_delay_summary')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW production_delay_summary AS (
                SELECT
                    wo.id AS id,

                    wo.date_start::date AS wo_date,
                    mp.party_id AS party_id,
                    mp.name AS wo_no,
                    wo.workcenter_id AS machine_id,
                    mp.product_id AS product_id,
                    mp.product_qty AS qty,
                    wo.planned_start_date,
                    wo.date_start AS actual_start_date,

                    -- Expected End Date
                    (
                        wo.date_start +
                        (wo.duration_expected * interval '1 minute')
                    )::date AS exp_delivery_date,

                    wo.date_finished::date AS production_close_date,
                    wo.date_finished AS production_end_date,

                    -- Delay in Minutes
                    ROUND(
                        EXTRACT(EPOCH FROM (
                            wo.date_finished -
                            (
                                wo.date_start +
                                (wo.duration_expected * interval '1 minute')
                            )
                        )) / 60
                    )::integer AS production_delay,

                    wo.production_delay_reason_id AS reason_id,
                    wo.production_delay_acknowledged_by AS action_by,
                    ''::varchar AS action
                FROM mrp_workorder wo
                JOIN mrp_production mp
                    ON mp.id = wo.production_id

                WHERE
                    wo.state = 'done'
                    AND wo.date_start IS NOT NULL
                    AND wo.date_finished IS NOT NULL
                    AND wo.duration_expected IS NOT NULL

                    -- IMPORTANT: Only real delays
                    AND wo.date_finished >
                        (
                            wo.date_start +
                            (wo.duration_expected * interval '1 minute')
                        )

                    AND COALESCE(wo.production_delay_acknowledged, false) = true
            )
        """)
