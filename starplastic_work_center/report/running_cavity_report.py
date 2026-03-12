from odoo import models, fields, tools


class RunningCavityReason(models.Model):
    _name = 'running.cavity.reason'
    _description = 'Running Cavity Reason'

    name = fields.Char(string='Reason')


class WorkCenterShift(models.Model):
    _inherit = 'work.center.shift'

    cavity_acknowledged = fields.Boolean(default=False)
    cavity_reason_id = fields.Many2one(
        'running.cavity.reason',
        string='Reason'
    )
    cavity_action = fields.Char(string='Action')
    cavity_acknowledged_by = fields.Many2one(
        'res.users',
        string='Action By'
    )


class RunningCavityReasonWizard(models.TransientModel):
    _name = 'running.cavity.reason.wizard'
    _description = 'Running Cavity Reason Wizard'

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
            'cavity_acknowledged': True,
            'cavity_reason_id': self.reason_id.id,
            'cavity_action': self.action,
            'cavity_acknowledged_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}


class RunningCavityReport(models.Model):
    _name = 'running.cavity.report'
    _description = 'Running Cavity Report'
    _auto = False

    date = fields.Date()
    lot_id = fields.Many2one('stock.lot', string="Batch Number")
    machine_id = fields.Many2one('mrp.workcenter', string="Machine")
    shift_id = fields.Many2one('work.center.shift', string="Shift")
    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False,
    )
    product_id = fields.Many2one('product.product', string="Item")
    supervisor_one_id = fields.Many2one('res.users', string="Supervisor 1")
    supervisor_two_id = fields.Many2one('res.users', string="Supervisor 2")
    running_cavity = fields.Integer()
    mould_cavity = fields.Integer()

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
            'name': 'Acknowledge Cavity Action',
            'res_model': 'running.cavity.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shift_id': self.shift_id.id,
            }
        }


    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'running_cavity_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW running_cavity_report AS (
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
                    rwc.cavity AS mould_cavity
                FROM work_center_shift wcs
                JOIN mrp_production mo ON mo.id = wcs.production_id
                JOIN mrp_workorder wo ON wo.production_id = mo.id
                JOIN mrp_routing_workcenter rwc ON rwc.id = wo.operation_id
                WHERE
                    COALESCE(wcs.cavity_acknowledged, false) = false
                    AND COALESCE(wcs.cavity, 0) != COALESCE(rwc.cavity, 0)
            )
        """)


class RunningCavityActionLog(models.Model):
    _name = 'running.cavity.action.log'
    _description = 'Running Cavity Action Log'

    report_id = fields.Integer()
    reason_id = fields.Many2one('running.cavity.reason')
    action = fields.Char()
    action_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    date = fields.Datetime(default=fields.Datetime.now)
