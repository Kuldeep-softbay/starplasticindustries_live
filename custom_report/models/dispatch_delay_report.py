from odoo import models, fields

class DispatchDelayReasonWizard(models.TransientModel):
    _name = 'dispatch.delay.reason.wizard'
    _description = 'Dispatch Delay Reason Wizard'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        required=True,
        readonly=True
    )

    delay_reason_id = fields.Many2one(
        'dispatch.delay.reason',
        string='Delay Reason',
        required=True
    )

    def action_confirm(self):
        self.ensure_one()
        self.picking_id.write({
            'delay_acknowledged': True,
            'delay_reason_id': self.delay_reason_id.id,
            'delay_acknowledged_by': self.env.user.id,
        })
        return {'type': 'ir.actions.act_window_close'}


class DispatchDelayReport(models.Model):
    _name = 'dispatch.delay.report'
    _description = 'Dispatch Delay Report'
    _auto = False
    _order = 'exp_dispatch_date'

    packing_slip_no = fields.Char(string='Packing Slip No')
    partner_id = fields.Many2one('res.partner', string='Customer Name')
    exp_dispatch_date = fields.Date(string='Exp Dispatch Date')
    dispatch_date = fields.Date(string='Dispatch Date')
    remark = fields.Text(string='Remark')
    total_qty = fields.Float(string='Total Quantity')

    action_state = fields.Selection(
        [('show', 'Show'), ('hide', 'Hide')],
        string='Action State'
    )

    def init(self):
        self.env.cr.execute("""
            DROP VIEW IF EXISTS dispatch_delay_report CASCADE;
        """)
        self.env.cr.execute("""
            CREATE VIEW dispatch_delay_report AS (
                SELECT
                    sp.id AS id,
                    sp.name AS packing_slip_no,
                    sp.partner_id AS partner_id,
                    sp.exp_dis_date::date AS exp_dispatch_date,
                    sp.actual_dispatch_date::date AS dispatch_date,
                    sp.remarks AS remark,
                    COALESCE(SUM(sml.quantity), 0) AS total_qty
                FROM stock_picking sp
                LEFT JOIN stock_move_line sml
                    ON sml.picking_id = sp.id
                WHERE
                    sp.exp_dis_date IS NOT NULL
                    AND sp.state = 'done'
                    AND sp.actual_dispatch_date IS NOT NULL
                    AND sp.actual_dispatch_date::date > sp.exp_dis_date::date
                    AND COALESCE(sp.delay_acknowledged, false) = false
                GROUP BY
                    sp.id,
                    sp.name,
                    sp.partner_id,
                    sp.exp_dis_date,
                    sp.actual_dispatch_date,
                    sp.remarks
            )
        """)

    def action_hide(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Acknowledge Dispatch Delay',
            'res_model': 'dispatch.delay.reason.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            }
        }



