from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PackingMemo(models.Model):
    _name = 'packing.memo'
    _description = 'Packing Memo'
    _order = 'id desc'

    name = fields.Char(default='New', copy=False)
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        required=True
    )
    sale_id = fields.Many2one(
        'sale.order',
        string='Sale Order',
        required=True
    )
    line_ids = fields.One2many(
        'packing.memo.line',
        'memo_id',
        string='Products'
    )

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'packing.memo'
            ) or 'New'
        return super().create(vals)


class PackingMemoLine(models.Model):
    _name = 'packing.memo.line'
    _description = 'Packing Memo Line'

    memo_id = fields.Many2one(
        'packing.memo',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        required=True
    )
    quantity = fields.Float(required=True)

class StockMove(models.Model):
    _inherit = 'stock.move'

    def action_open_packing_memo_wizard(self):
        self.ensure_one()

        if not self.picking_id or not self.picking_id.sale_id:
            raise UserError(_("Packing Memo can be created only for Sale Orders."))

        return {
            'name': _('Generate Packing Memo'),
            'type': 'ir.actions.act_window',
            'res_model': 'packing.memo.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sale_id': self.picking_id.sale_id.id,
                'default_move_id': self.id,
                'default_picking_id': self.picking_id.id,
            }
        }
