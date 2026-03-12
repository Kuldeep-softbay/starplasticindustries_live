# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time

# ==========================================================
# REPORT MODEL
# ==========================================================
class RmGradeWiseStockReport(models.Model):
    _name = 'rm.grade.wise.stock.report'
    _description = 'RM Grade Wise Stock Report'
    _order = 'date, id'

    computation_key = fields.Char(index=True)

    date = fields.Date()
    particulars = fields.Char()

    product_id = fields.Many2one('product.product', string='Product')
    rm_type = fields.Many2one('product.template', string='RM Type')

    batch = fields.Char(string='Internal Batch No')

    rm_grade_name = fields.Char(string='RM Grade')

    vendor_id = fields.Many2one('res.partner', string='Vendor')
    invoice_no = fields.Char()

    received_qty = fields.Float()
    issue_qty = fields.Float()
    balance_qty = fields.Float()
    pmemo_no = fields.Char()


# ==========================================================
# WIZARD
# ==========================================================
class RmGradeWiseStockWizard(models.TransientModel):
    _name = 'rm.grade.wise.stock.wizard'
    _description = 'RM Grade Wise Stock Wizard'

    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)

    party_id = fields.Many2one('job.party.work', string='Party')

    rm_type = fields.Many2one(
        'product.template',
        string='RM Type',
        domain="[('purchase_ok','=',True),('sale_ok','=',False)]"
    )

    rm_grade = fields.Many2one(
        'product.template.attribute.value',
        string='RM Grade',
        domain="[('id','in',available_grade_ids)]",
        context={'rm_grade_only': True}
    )

    available_grade_ids = fields.Many2many(
        'product.template.attribute.value',
        compute='_compute_available_grades',
        store=False
    )

    @api.depends('rm_type')
    def _compute_available_grades(self):
        for wizard in self:
            if not wizard.rm_type:
                wizard.available_grade_ids = [(6, 0, [])]
                continue
            values = wizard.rm_type.product_variant_ids.mapped(
                'product_template_variant_value_ids'
            )
            wizard.available_grade_ids = [(6, 0, values.ids)]


    # ------------------------------------------------------
    # DATETIME HELPERS
    # ------------------------------------------------------
    def _datetime_from(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_from, time.min)
        )

    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_to, time.max)
        )

    def _get_grade_name(self, product):
        if not product:
            return ''
        return ", ".join(
            product.product_template_variant_value_ids.mapped('name')
        )

    # ------------------------------------------------------
    # DOMAIN
    # ------------------------------------------------------
    def _base_domain(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self._datetime_from()),
            ('date', '<=', self._datetime_to()),
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),
            '|',
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
        ]

        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))

        if self.rm_type:
            domain.append(('product_id.product_tmpl_id', '=', self.rm_type.id))

        if self.rm_grade:
            domain.append((
                'product_id.product_template_variant_value_ids',
                'in',
                self.rm_grade.id
            ))

        return domain

    # ------------------------------------------------------
    # OPENING BALANCE
    # ------------------------------------------------------
    def _compute_opening_balance(self):
        opening = 0.0
        Move = self.env['stock.move']

        moves = Move.search([
            ('state', '=', 'done'),
            ('date', '<', self._datetime_from()),
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),
            '|',
            ('location_id.usage', '=', 'internal'),
            ('location_dest_id.usage', '=', 'internal'),
        ])

        for mv in moves:
            qty = mv.product_uom_qty
            if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                opening += qty
            elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                opening -= qty

        return opening

    # ------------------------------------------------------
    # MAIN ACTION
    # ------------------------------------------------------
    def action_show_report(self):
        self.ensure_one()

        Report = self.env['rm.grade.wise.stock.report']
        Move = self.env['stock.move']

        # Remove previous report records
        Report.search([
            ('computation_key', 'like', f"{self.env.uid}-")
        ]).unlink()

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"
        balance = self._compute_opening_balance()

        moves = Move.search(self._base_domain(), order='date,id')

        for mv in moves:

            received = 0.0
            issued = 0.0

            qty = sum(mv.move_line_ids.mapped('qty_done')) or mv.product_uom_qty

            src = mv.location_id
            dest = mv.location_dest_id

            # --------------------------------------------------
            # PURCHASE RECEIPT
            # --------------------------------------------------
            if src.usage == 'supplier' and dest.usage == 'internal':
                received = qty

            # --------------------------------------------------
            # MANUFACTURING MOVES
            # --------------------------------------------------
            elif mv.raw_material_production_id:

                # Issue → Stock → Production
                if dest.usage == 'production':
                    issued = qty

                # Return → Production → Stock
                elif src.usage == 'production' and dest.usage == 'internal':
                    received = qty

            # --------------------------------------------------
            # DELIVERY
            # --------------------------------------------------
            elif src.usage == 'internal' and dest.usage == 'customer':
                issued = qty

            # --------------------------------------------------
            # BALANCE UPDATE
            # --------------------------------------------------
            balance += (received - issued)

            # -------- PARTICULARS --------
            if mv.raw_material_production_id:
                particulars = 'Production'
            elif mv.production_id:
                particulars = 'Production'
            elif mv.picking_id:
                particulars = mv.picking_id.name
            else:
                particulars = mv.reference or ''

            lot_name = mv.move_line_ids[:1].lot_id.name if mv.move_line_ids else False

            main_product = False

            if mv.raw_material_production_id:
                main_product = mv.raw_material_production_id.product_id
            elif mv.production_id:
                main_product = mv.production_id.product_id
            elif hasattr(mv, 'party_id') and mv.party_id:
                main_product = mv.party_id.product_id

            product_id_value = main_product.id if main_product and main_product.exists() else False

            Report.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'particulars': particulars,
                'product_id': product_id_value,
                'batch': lot_name or '',
                'rm_grade_name': self._get_grade_name(main_product) if main_product else '',
                'vendor_id': mv.picking_id.partner_id.id if mv.picking_id else False,
                'invoice_no': mv.picking_id.invoice_number if mv.picking_id else '',
                'received_qty': received,
                'issue_qty': issued,
                'balance_qty': balance,
                'pmemo_no': mv.picking_id.name if mv.picking_id else '',
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Grade Wise Stock Report'),
            'res_model': 'rm.grade.wise.stock.report',
            'view_mode': 'list',
            'domain': [('computation_key', '=', computation_key)],
            'target': 'current',
        }
