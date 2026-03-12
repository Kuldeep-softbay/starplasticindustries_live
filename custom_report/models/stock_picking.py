from odoo import api, fields, models, _
from datetime import datetime

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    total_qty = fields.Float(
        string='Total Qty',
        compute='_compute_total_qty',
        store=True,
    )
    exp_dispatch_date = fields.Datetime(
        string='Exp Dispatch Date',
        related='scheduled_date',
        store=True,
        readonly=True,
    )
    packing_slip_no = fields.Char(
        string='Packing Slip No',
        related='name',
        store=True,
        readonly=True,
    )
    customer_name = fields.Many2one(
        'res.partner',
        string='Customer Name',
        related='partner_id',
        store=True,
        readonly=True,
    )
    dispatch_date = fields.Date(
        string='Dispatch Date',
        compute='_compute_dispatch_date',
        store=True
    )
    actual_dispatch_date = fields.Date(
        string='Actual Despatch Date',
        help="The date when the picking was completed.")
   
    @api.depends('move_ids.product_uom_qty', 'move_line_ids.qty_done')
    def _compute_total_qty(self):
        for pick in self:
            qty = 0.0
            if pick.move_line_ids:
                qty = sum(pick.move_line_ids.mapped('qty_done'))
            else:
                qty = sum(pick.move_ids.mapped('product_uom_qty'))
            pick.total_qty = float(qty or 0.0)

    @api.depends('state', 'date_done')
    def _compute_dispatch_date(self):
        for rec in self:
            rec.dispatch_date = (
                rec.date_done.date()
                if rec.state == 'done' and rec.date_done else False
            )