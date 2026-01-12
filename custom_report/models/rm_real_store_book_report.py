# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


# =========================================================
# REPORT MODEL
# =========================================================
class RmRealStoreBookReport(models.Model):
    _name = 'rm.real.store.book.report'
    _description = 'RM Red Stock Book Report'
    _order = 'date, id'

    computation_key = fields.Char(index=True)

    date = fields.Date(string='Date')
    particulars = fields.Char(string='Particulars')
    product_id = fields.Many2one('product.product', string='Product')
    batch = fields.Char(string='Batch')
    grade = fields.Char(string='Grade')
    vendor_id = fields.Many2one('res.partner', string='Vendor / Supplier')
    invoice_no = fields.Char(string='Invoice No')
    received_qty = fields.Float(string='Received')
    pmemo_no = fields.Char(string='P. Memo No')
    production_qty = fields.Float(string='Production')
    balance_qty = fields.Float(string='Balance')
    party_id = fields.Many2one('job.party.work', string='Party Name')
    location_id = fields.Many2one('stock.location', string='Location')
    raw_type = fields.Char(string='Raw Type')


# =========================================================
# WIZARD
# =========================================================
class RmRealStoreBookWizard(models.TransientModel):
    _name = 'rm.real.store.book.wizard'
    _description = 'RM Red Stock Book Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    raw_type = fields.Char(string='Raw Type')

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage', '=', 'internal')]",
    )
    particulars = fields.Char(string='Particular')

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain="[('purchase_ok','=',True),('sale_ok','=',False)]"
    )

    party_id = fields.Many2one(
        'job.party.work',
        string='Party Name'
    )

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------
    def _datetime_from(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_from, time.min)
        )

    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date_to, time.max)
        )

    def _base_domain(self):
        """Moves inside selected period"""
        self.ensure_one()

        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self._datetime_from()),
            ('date', '<=', self._datetime_to()),
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        if self.party_id:
            # use the custom party field on moves
            domain.append(('party_id', '=', self.party_id.id))

        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

        return domain

    def _opening_domain(self):
        """Moves strictly before date_from"""
        self.ensure_one()

        domain = [
            ('state', '=', 'done'),
            ('date', '<', self._datetime_from()),
            ('product_id.product_tmpl_id.purchase_ok', '=', True),
            ('product_id.product_tmpl_id.sale_ok', '=', False),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        if self.party_id:
            # use the custom party field on moves
            domain.append(('party_id', '=', self.party_id.id))

        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

        return domain

    def _compute_opening_balance(self):
        """Opening balance before date_from"""
        Move = self.env['stock.move']
        moves = Move.search(self._opening_domain())

        _logger.info(
            "RM Red Stock Book opening balance moves: %s",
            len(moves)
        )

        opening = 0.0
        for mv in moves:
            qty = mv.product_uom_qty

            if self.location_id:
                if mv.location_dest_id == self.location_id:
                    opening += qty
                elif mv.location_id == self.location_id:
                    opening -= qty
            else:
                if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                    opening += qty
                elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                    opening -= qty

        return opening

    def _get_grade_name(self, product):
        return ", ".join(
            product.product_template_variant_value_ids.mapped('name')
        )

    # -----------------------------------------------------
    # Main Action
    # -----------------------------------------------------
    def action_show_report(self):
        self.ensure_one()

        Report = self.env['rm.real.store.book.report']
        Move = self.env['stock.move']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"
        opening_balance = self._compute_opening_balance()

        moves = Move.search(self._base_domain(), order='date, id')

        _logger.info(
            "RM Red Stock Book Report moves: %s",
            len(moves)
        )

        balance = opening_balance

        for mv in moves:
            qty = mv.product_uom_qty
            received = 0.0
            production = 0.0

            if self.location_id:
                if mv.location_dest_id == self.location_id:
                    received = qty
                elif mv.location_id == self.location_id:
                    production = qty
            else:
                if mv.location_dest_id.usage == 'internal' and mv.location_id.usage != 'internal':
                    received = qty
                elif mv.location_id.usage == 'internal' and mv.location_dest_id.usage != 'internal':
                    production = qty

            balance += (received - production)

            Report.create({
                'computation_key': computation_key,
                'date': mv.date.date(),
                'particulars': mv.picking_id.origin if mv.picking_id else ' ',
                'product_id': mv.product_id.id,
                'batch': mv.picking_id.internal_batch_number if mv.picking_id else '',
                'grade': self._get_grade_name(mv.product_id),
                'vendor_id': mv.partner_id.id
                             if mv.partner_id else
                             (mv.picking_id.partner_id.id if mv.picking_id else False),
                'invoice_no': mv.picking_id.invoice_number if mv.picking_id else '',
                'received_qty': received,
                'pmemo_no': mv.reference or (mv.picking_id.name if mv.picking_id else ''),
                'production_qty': production,
                'balance_qty': balance,
                'location_id': self.location_id.id if self.location_id else False,
                'raw_type': self.raw_type,
                'party_id': self.party_id.id if self.party_id else False,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Red Stock Book Report'),
            'res_model': 'rm.real.store.book.report',
            'view_mode': 'list,search',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }
