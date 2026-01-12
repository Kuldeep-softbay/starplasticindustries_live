from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PackingMemoWizard(models.TransientModel):
    _name = 'packing.memo.wizard'
    _description = 'Packing Memo Wizard'

    sale_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True,
        readonly=True,
    )
    line_ids = fields.One2many(
        'packing.memo.wizard.line',
        'wizard_id',
        string='Products',
    )
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        readonly=True,
    )
    line_ids = fields.One2many(
        'packing.memo.wizard.line',
        'wizard_id',
        string='Products',
    )

    def action_open_stock_move(self):
        self.ensure_one()

        picking = self.env['stock.picking'].search(
            [('sale_id', '=', self.sale_id.id)],
            limit=1
        )
        if not picking:
            raise ValidationError("No delivery order found for this Sale Order.")

        self.picking_id = picking.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Detailed Operations',
            'res_model': 'stock.move',
            'view_mode': 'form',
            'views': [(self.env.ref('stock.view_stock_move_operations').id, 'form')],
            'target': 'new',
            'res_id': picking.move_ids_without_package[:1].id,
            'context': {
                'active_id': picking.id,
                'active_model': 'stock.picking',
                'from_packing_memo': True,
                'packing_memo_wizard_id': self.id,
            }
        }

class PackingMemoWizardLine(models.TransientModel):
    _name = 'packing.memo.wizard.line'
    _description = 'Packing Memo Wizard Line'

    wizard_id = fields.Many2one(
        'packing.memo.wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one(
        'product.product',
        required=True,
    )
    quantity = fields.Float(required=True)

    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch / Lot',
        domain="[('product_id', '=', product_id)]",
    )

    available_qty = fields.Float(
        string='Available',
        compute='_compute_available_qty',
        store=False,
    )
    selected_qty = fields.Float(string='Selected Qty')

    @api.depends('lot_id')
    def _compute_available_qty(self):
        Quant = self.env['stock.quant']
        for rec in self:
            if not rec.lot_id:
                rec.available_qty = 0.0
                continue

            quants = Quant.search([
                ('lot_id', '=', rec.lot_id.id),
                ('location_id.usage', '=', 'internal'),
            ])
            rec.available_qty = sum(quants.mapped('quantity'))

    @api.onchange('lot_id')
    def _onchange_lot_id(self):
        if not self.lot_id:
            self.selected_qty = 0.0
            return

        self.selected_qty = min(
            self.quantity or 0.0,
            self.available_qty or 0.0,
        )
