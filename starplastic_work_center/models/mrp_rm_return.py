from odoo import models, fields, api
from odoo.exceptions import UserError


class MrpRmReturnLine(models.Model):
    _name = 'mrp.rm.return.line'
    _description = 'RM Return Line'

    production_id = fields.Many2one(
        'mrp.production',
        string="Manufacturing Order",
        ondelete='cascade'
    )

    date = fields.Date(
        string="Return Date",
        default=fields.Date.context_today,
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        string="Raw Material",
        required=True,
        domain="[('id', 'in', allowed_product_ids)]"
    )

    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        related='product_id.uom_id',
        store=True
    )

    allowed_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_products'
    )

    source_location_id = fields.Many2one(
        'stock.location',
        string="Source Location",
        required=True
    )

    location_id = fields.Many2one(
        'stock.location',
        string="Return Location",
        required=True
    )

    quantity = fields.Float(
        string="Quantity",
        required=True
    )

    stock_move_id = fields.Many2one(
        'stock.move',
        string="Stock Move",
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], default='draft')

    lot_id = fields.Many2one(
        'stock.lot',
        string="Lot/Serial Number",
        domain="[('product_id','=',product_id)]"
    )

    # --------------------------------------------------

    @api.depends('production_id')
    def _compute_allowed_products(self):
        for rec in self:
            if rec.production_id:
                rec.allowed_product_ids = rec.production_id.move_raw_ids.mapped('product_id')
            else:
                rec.allowed_product_ids = False

    # --------------------------------------------------
    # Create RM Return Stock Move
    # --------------------------------------------------

    def action_return_material(self):

        for rec in self:

            if rec.stock_move_id:
                continue

            if rec.quantity <= 0:
                raise UserError("Return quantity must be greater than zero.")

            move = self.env['stock.move'].create({
                'name': 'RM Return',
                'product_id': rec.product_id.id,
                'product_uom_qty': rec.quantity,
                'product_uom': rec.uom_id.id,

                # RETURN FROM PRODUCTION
                'location_id': rec.source_location_id.id,

                # RETURN TO STOCK
                'location_dest_id': rec.location_id.id,

                'raw_material_production_id': rec.production_id.id,
                'origin': rec.production_id.name,

                # important flag for reports
                'reference': 'rm_return',
            })

            move._action_confirm()

            move_line_vals = {
                'move_id': move.id,
                'product_id': rec.product_id.id,
                'product_uom_id': rec.uom_id.id,
                'qty_done': rec.quantity,
                'location_id': rec.source_location_id.id,
                'location_dest_id': rec.location_id.id,
            }

            # pass lot if product tracking enabled
            if rec.product_id.tracking != 'none':
                if not rec.lot_id:
                    raise UserError("Please select Lot/Serial Number for this product.")
                move_line_vals['lot_id'] = rec.lot_id.id

            self.env['stock.move.line'].create(move_line_vals)

            move._action_done()

            rec.stock_move_id = move.id
            rec.state = 'done'

    # --------------------------------------------------
    # Create
    # --------------------------------------------------

    @api.model
    def create(self, vals):

        record = super().create(vals)

        if record.production_id and not record.source_location_id:
            record.source_location_id = record.production_id.location_dest_id.id

        record.action_return_material()

        if record.production_id:
            record.production_id._compute_rm_return_qty()
            record.production_id._compute_pmemo()

        return record

    # --------------------------------------------------
    # Write
    # --------------------------------------------------

    def write(self, vals):

        res = super().write(vals)

        if any(field in vals for field in ['quantity', 'state']):
            for rec in self:
                if rec.production_id:
                    rec.production_id._compute_rm_return_qty()
                    rec.production_id._compute_pmemo()

        return res
