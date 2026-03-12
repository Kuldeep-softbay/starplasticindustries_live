from odoo import models, fields, tools


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    production_delay_acknowledged = fields.Boolean(default=False)
    production_delay_reason_id = fields.Many2one(
        'running.cavity.reason',
        string='Reason'
    )
    production_delay_acknowledged_by = fields.Many2one(
        'res.users',
        string='Action By'
    )
    production_delay_action = fields.Char(
        string='Action'
    )

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    party_id = fields.Many2one("job.party.work")


class ProductionDelayReasonWizard(models.TransientModel):
    _name = 'production.delay.reason.wizard'
    _description = 'Production Delay Reason Wizard'

    workorder_id = fields.Many2one(
        'mrp.workorder',
        required=True,
        readonly=True
    )
    reason_id = fields.Many2one(
        'running.cavity.reason',
        required=True
    )
    action = fields.Char(required=True)


    # def action_confirm(self):
    #     self.ensure_one()

    #     self.env['production.delay.action.log'].create({
    #         'workorder_id': self.workorder_id.id,
    #         'reason_id': self.reason_id.id,
    #         'action': self.action,
    #     })

    #     self.workorder_id.write({
    #         'production_delay_acknowledged': True,
    #         'production_delay_reason_id': self.reason_id.id,
    #         'production_delay_acknowledged_by': self.env.user.id,
    #     })

    #     return {'type': 'ir.actions.act_window_close'}

    def action_confirm(self):

        log = self.env['production.delay.action.log'].create({
            'workorder_id': self.workorder_id.id,
            'reason_id': self.reason_id.id,
            'action': self.action,
        })

        return self.env.ref(
            'starplastic_work_center.action_report_delay_production'
        ).report_action(log)



class ProductionDelayReport(models.Model):
    _name = 'production.delay.report'
    _description = 'Production Delay Report'
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

    def action_hide(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Acknowledge Production Delay',
            'res_model': 'production.delay.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_workorder_id': self.id,
            }
        }

    # def action_report_delay(self):
    #     return self.env.ref(
    #         'starplastic_work_center.action_production_delay_pdf'
    #     ).report_action(self)

    def action_report_delay(self):
        return self.action_hide()

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'production_delay_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW production_delay_report AS (
                SELECT
                    wo.id AS id,

                    wo.date_start::date AS wo_date,
                    mp.name AS wo_no,
                    wo.workcenter_id AS machine_id,

                    NULL::integer AS party_id,

                    mp.product_id AS product_id,
                    mp.product_qty AS qty,

                    wo.planned_start_date,
                    wo.date_start AS actual_start_date,

                    -- Expected End Datetime
                    (wo.date_start +
                        (wo.duration_expected * interval '1 minute')
                    ) AS exp_delivery_date,

                    wo.date_finished::date AS production_close_date,
                    wo.date_finished AS production_end_date,

                    -- Delay in Minutes
                    ROUND(
                        EXTRACT(EPOCH FROM (
                            wo.date_finished -
                            (wo.date_start +
                                (wo.duration_expected * interval '1 minute')
                            )
                        )) / 60
                    )::integer AS production_delay

                FROM mrp_workorder wo
                JOIN mrp_production mp
                    ON mp.id = wo.production_id

                WHERE
                    wo.state = 'done'
                    AND wo.date_start IS NOT NULL
                    AND wo.date_finished IS NOT NULL
                    AND wo.duration_expected IS NOT NULL

                    -- IMPORTANT CONDITION:
                    -- Show only if finished AFTER expected time
                    AND wo.date_finished >
                        (wo.date_start +
                            (wo.duration_expected * interval '1 minute')
                        )
                    AND COALESCE(wo.production_delay_acknowledged, false) = false
            )
        """)


class ProductionDelayActionLog(models.Model):
    _name = 'production.delay.action.log'
    _description = 'Production Delay Action Log'

    report_id = fields.Integer()
    reason_id = fields.Many2one('running.cavity.reason')
    action_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    date = fields.Datetime(default=fields.Datetime.now)
    action = fields.Char()
    workorder_id = fields.Many2one('mrp.workorder', string="Work Order")

