from odoo import models, fields, tools

class WorkCenterShift(models.Model):
    _inherit = 'work.center.shift'

    cycle_time_acknowledged = fields.Boolean(default=False)
    cycle_time_reason_id = fields.Many2one(
        'running.cavity.reason',
        string='Reason'
    )
    cycle_time_action = fields.Char(string='Action')
    cycle_time_acknowledged_by = fields.Many2one(
        'res.users',
        string='Action By'
    )

    
class StdCycleTimeReasonWizard(models.TransientModel):
    _name = 'std.cycle.time.reason.wizard'
    _description = 'Standard Cycle Time Reason Wizard'

    shift_id = fields.Many2one(
        'work.center.shift',
        string='Shift',
        required=True,
        readonly=True
    )
    reason_id = fields.Many2one(
        'running.cavity.reason',
        string='Reason',
        required=True
    )
    action = fields.Char(
        string='Action',
        required=True
    )

    def action_confirm(self):
        self.ensure_one()
        self.shift_id.write({
            'cycle_time_acknowledged': True,
            'cycle_time_reason_id': self.reason_id.id,
            'cycle_time_action': self.action,
            'cycle_time_acknowledged_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}


    
class StdCycleTimeHidden(models.Model):
    _name = 'std.cycle.time.hidden'
    _description = 'Hidden Std Cycle Time Lines'

    report_key = fields.Char(index=True)
    reason_id = fields.Many2one('running.cavity.reason')


class StdCycleTimeReport(models.Model):
    _name = 'std.cycle.time.report'
    _description = 'Standard Cycle Time Report'
    _auto = False

    date = fields.Date()
    lot_id = fields.Many2one('stock.lot', string="Batch Number")
    machine_id = fields.Many2one('mrp.workcenter')
    shift_id = fields.Many2one('work.center.shift')
    shift_display = fields.Char(
        compute='_compute_shift_display',
        store=False,
    )
    product_id = fields.Many2one('product.product')
    supervisor_one_id = fields.Many2one('res.users')
    supervisor_two_id = fields.Many2one('res.users')
    set_cycle_time = fields.Float(string='Set Cycle Time')
    running_cycle_time = fields.Float(string='Running Cycle Time')
    tolerance = fields.Float()
    hourly_target = fields.Float()

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
            'name': 'Acknowledge Std Cycle Time Action',
            'res_model': 'std.cycle.time.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shift_id': self.shift_id.id,
            }
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'std_cycle_time_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW std_cycle_time_report AS (
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
                    wcs.cycle_time_sec AS running_cycle_time,
                    pt.unit_weight_tolerance AS tolerance,
                    wcs.hourly_target_qty AS hourly_target

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
                    COALESCE(wcs.cycle_time_acknowledged, false) = false
                    AND COALESCE(wcs.cycle_time_sec, 0) 
                        != COALESCE(rwc.cycle_time, 0)
            )
        """)



class StdCycleTimeReasonLog(models.Model):
    _name = 'std.cycle.time.reason.log'
    _description = 'Standard Cycle Time Reason Log'

    report_key = fields.Char(required=True, index=True)
    reason_id = fields.Many2one('running.cavity.reason', required=True)
    action = fields.Char(required=True)
    hidden_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    hidden_on = fields.Datetime(default=fields.Datetime.now)






