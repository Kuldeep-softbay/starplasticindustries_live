import math
from odoo import api, fields, models, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import math

class ProductTemplate(models.Model):
    _inherit = "product.product"

    batch_number = fields.Char(string='Batch Number', help="Batch number associated with the product.")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    invoice_number = fields.Char(string="Invoice Number")
    rm_add_date = fields.Date(string="Date")
    supplier_batch_number = fields.Char(string='Supplier Batch Number')
    internal_batch_number = fields.Char(
        string='Internal Batch Number',
        readonly=True,
        copy=False,
        compute='_compute_internal_batch_number',
        store=True,
    )
    mfi_value = fields.Float(string='MFI Value')
    bags_type = fields.Char(string='Bags Type')
    number_of_bags = fields.Integer(string='Number of Bags', compute='_compute_number_of_bags', store=True)
    particulars = fields.Text(string='Particulars')
    remarks = fields.Text(string='Remarks')
    party_id = fields.Many2one('job.party.work', string='Party')

    batch_number = fields.Char(string='Batch Number')
    removal_type = fields.Selection([
        ('normal', 'Normal'),
        ('other', 'Other')
    ], string='Removal Type', default='normal')

    total_product_qty = fields.Float(
    string='Total Quantity',
    compute='_compute_total_product_qty',
    readonly=True)
    actual_dispatch_date = fields.Date(
        string='Actual Despatch Date',
        help="The date when the picking was completed.")
    exp_dis_date = fields.Date(
        string="Expected Dispatch Date",
        tracking=True,
    )
    rejection_reason_id = fields.Many2one(
        'rejection.reason',
        string='Rejection Reason'
    )
    packing_memo_count = fields.Integer(
        compute='_compute_packing_memo_count'
    )

    @api.depends('move_ids_without_package.product_uom_qty', 'state')
    def _compute_number_of_bags(self):
        for picking in self:
            if picking.state != 'done':
                picking.number_of_bags = 0
                continue

            total_qty_grams = 0.0

            for move in picking.move_ids_without_package:
                total_qty_grams += move.product_uom_qty or 0.0

            BAG_SIZE_GRAMS = 25 * 1000

            picking.number_of_bags = int(
                math.ceil(total_qty_grams / BAG_SIZE_GRAMS)
            ) if total_qty_grams else 0

    def _compute_packing_memo_count(self):
        for picking in self:
            picking.packing_memo_count = self.env[
                'packing.memo'
            ].search_count([
                ('picking_id', '=', picking.id)
            ])
    
    def action_open_stock_move(self):
        self.ensure_one()

        picking = self.env['stock.picking'].search(
            [('sale_id', '=', self.sale_id.id)],
            limit=1
        )
        if not picking:
            raise ValidationError("No delivery order found for this Sale Order.")

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



    @api.depends('move_ids.product_qty')
    def _compute_total_product_qty(self):
        for picking in self:
            picking.total_product_qty = sum(picking.move_ids.mapped('product_qty'))

    @api.depends(
        'picking_type_id.code',
        'move_ids_without_package.product_id',
        'move_ids_without_package.product_id.product_tmpl_id.default_code'
    )
    def _compute_internal_batch_number(self):
        for picking in self:

            # Already generated → skip
            if picking.internal_batch_number:
                continue

            # Only Incoming Receipts
            if picking.picking_type_id.code != 'incoming':
                continue

            # Must have at least one move
            if not picking.move_ids_without_package:
                continue

            # Take first move product
            move = picking.move_ids_without_package[0]
            product = move.product_id

            if not product:
                continue

            product_code = product.product_tmpl_id.default_code

            if not product_code:
                raise UserError(
                    _("Product must have an Internal Reference (Product Code) to generate Internal Batch Number.")
                )

            # Year (last 2 digits)
            year = datetime.now().strftime('%y')

            # Prefix: R00126
            prefix = f"{product_code}{year}"

            # Find last sequence for same prefix
            last_picking = self.search(
                [('internal_batch_number', 'like', f"{prefix}%")],
                order='internal_batch_number desc',
                limit=1
            )

            if last_picking and last_picking.internal_batch_number:
                try:
                    last_seq = int(last_picking.internal_batch_number[-4:])
                    next_seq = str(last_seq + 1).zfill(4)
                except Exception:
                    next_seq = '0001'
            else:
                next_seq = '0001'

            # Final value
            picking.internal_batch_number = f"{prefix}{next_seq}"
