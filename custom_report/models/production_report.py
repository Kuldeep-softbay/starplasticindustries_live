# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductionReportLine(models.Model):
    _name = 'production.report.line'
    _description = 'Production Report Line'
    _order = 'date, id'

    computation_key = fields.Char(index=True)

    date = fields.Date(string='Date')
    particulars = fields.Char(string='Particulars')

    product_id = fields.Many2one('product.product', string='Item Name')
    lot_id = fields.Many2one('stock.lot', string='Batch No')

    total_production = fields.Float(string='Total Production')
    total_dispatch = fields.Float(string='Total Dispatch')
    total_reject = fields.Float(string='Rejection')
    balance = fields.Float(string='Stock')


class ProductionReportWizard(models.TransientModel):
    _name = 'production.report.wizard'
    _description = 'Production Report Wizard'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True
    )

    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch Number',
        domain="[('product_id', '=', product_id)]"
    )

    def action_show_report(self):
        self.ensure_one()

        Report = self.env['production.report.line']
        StockMove = self.env['stock.move']
        Scrap = self.env['stock.scrap']

        computation_key = f"{self.env.uid}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"

        if not self.lot_id:
            raise UserError(_("Please select a Batch / Lot"))

        product = self.product_id
        lot = self.lot_id

        # 🔹 Production (finished goods)
        production_moves = StockMove.search([
            ('state', '=', 'done'),
            ('product_id', '=', product.id),
            ('move_line_ids.lot_id', '=', lot.id),
            ('location_dest_id.usage', '=', 'internal'),
        ])

        production_qty = sum(
            production_moves.mapped('move_line_ids').filtered(
                lambda ml: ml.lot_id == lot
            ).mapped('qty_done')
        )

        # 🔹 Dispatch
        dispatch_moves = StockMove.search([
            ('state', '=', 'done'),
            ('product_id', '=', product.id),
            ('move_line_ids.lot_id', '=', lot.id),
            ('location_dest_id.usage', '=', 'customer'),
        ])

        dispatch_qty = sum(
            dispatch_moves.mapped('move_line_ids').filtered(
                lambda ml: ml.lot_id == lot
            ).mapped('qty_done')
        )

        # 🔹 Rejection
        scrap_moves = Scrap.search([
            ('state', '=', 'done'),
            ('product_id', '=', product.id),
            ('lot_id', '=', lot.id),
        ])

        reject_qty = sum(scrap_moves.mapped('scrap_qty'))

        balance = production_qty - dispatch_qty - reject_qty

        Report.create({
            'computation_key': computation_key,
            'date': fields.Date.context_today(self),
            'particulars': 'Batch Wise Production',
            'product_id': product.id,
            'lot_id': lot.id,
            'total_production': production_qty,
            'total_dispatch': dispatch_qty,
            'total_reject': reject_qty,
            'balance': balance,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Report'),
            'res_model': 'production.report.line',
            'view_mode': 'list,form',
            'domain': [('computation_key', '=', computation_key)],
            'target': 'current',
        }
