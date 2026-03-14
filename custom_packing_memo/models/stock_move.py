from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class StockMove(models.Model):
    _inherit = 'stock.move'

    product_grade = fields.Char(
        string='Grade',
        compute='_compute_product_grade',
        store=False
    )

    rm_formulation = fields.Char(
        string='RM Formulation',
        compute='_compute_rm_formulation',
        store=False
    )

    @api.depends('product_id')
    def _compute_product_grade(self):
        for line in self:
            if line.product_id:
                attrs = line.product_id.product_template_attribute_value_ids.mapped('name')
                line.product_grade = ", ".join(attrs)
            else:
                line.product_grade = ""

    @api.depends('picking_id')
    def _compute_rm_formulation(self):
        Production = self.env['mrp.production']

        for move in self:
            rm_formulation = False

            if move.picking_id and move.picking_id.origin:
                mo = Production.search([('name', '=', move.picking_id.origin)], limit=1)

                if mo and mo.product_id:
                    rm_formulation = mo.product_id.rm_formulation

            move.rm_formulation = rm_formulation

    def action_generate_packing_memo(self):
        self.ensure_one()

        move_lines = self.move_line_ids.filtered(
            lambda l: l.quantity > 0 and l.lot_id
        )

        if not move_lines:
            raise ValidationError(_("Nothing to generate packing memo."))

        selections = {}
        for line in move_lines:
            lot_id = str(line.lot_id.id)
            selections.setdefault(lot_id, 0.0)
            selections[lot_id] += line.quantity

        sale_order = self.picking_id.sale_id
        if not sale_order:
            raise UserError(_("No Sale Order linked."))

        return self.env.ref(
            'custom_packing_memo.action_report_packing_memo'
        ).with_context(
            packing_memo_selections=selections
        ).report_action(sale_order)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    product_grade = fields.Char(
        compute='_compute_product_grade',
        store=False
    )

    @api.depends('product_id')
    def _compute_product_grade(self):
        for line in self:
            if line.product_id:
                attrs = line.product_id.product_template_attribute_value_ids.mapped('name')
                line.product_grade = ", ".join(attrs)
            else:
                line.product_grade = ""
