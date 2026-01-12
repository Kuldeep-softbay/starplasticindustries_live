# -*- coding: utf-8 -*-
from odoo import fields, models, _
from datetime import datetime, time
import math


# =========================================================
# REPORT MODEL
# =========================================================
class RmStockSheetReport(models.Model):
    _name = 'rm.stock.sheet.report'
    _description = 'RM Stock Sheet Report'
    _order = 'rm_type, grade, internal_batch'

    computation_key = fields.Char(index=True)

    date = fields.Date(string='Date')
    party_id = fields.Many2one('job.party.work', string='Party')
    location_id = fields.Many2one('stock.location', string='Location')

    rm_type = fields.Many2one('product.template', string='RM Type', index=True)
    grade = fields.Char(string='Grade', index=True)

    mfi = fields.Char(string='MFI')
    batch = fields.Char(string='Supplier Batch No')
    internal_batch = fields.Char(string='Internal Batch No')

    bag_qty = fields.Float(string='Bag')
    kgs = fields.Float(string='Kgs')
    total_kgs = fields.Float(string='Total Kg')
    product_tmpl_id = fields.Many2one('product.template', string='RM Type', related='rm_type', store=True)


# =========================================================
# WIZARD
# =========================================================
class RmStockSheetWizard(models.TransientModel):
    _name = 'rm.stock.sheet.wizard'
    _description = 'RM Stock Sheet Wizard'

    date = fields.Date(required=True, default=fields.Date.context_today)
    party_id = fields.Many2one('job.party.work')
    rm_type = fields.Many2one(
        'product.template',
        domain="[('purchase_ok','=',True),('sale_ok','=',False)]"
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage','=','internal')]"
    )

    # ---------------------------------------------------------
    # HELPERS
    # ---------------------------------------------------------
    def _datetime_to(self):
        return fields.Datetime.to_datetime(
            datetime.combine(self.date, time.max)
        )

    def _get_grade(self, product):
        return ", ".join(
            product.product_template_variant_value_ids.mapped('name')
        )

    # ---------------------------------------------------------
    # MAIN ACTION
    # ---------------------------------------------------------
    def action_show_report(self):
        self.ensure_one()

        Report = self.env['rm.stock.sheet.report']
        MoveLine = self.env['stock.move.line']

        main_stock = self.env.ref('stock.stock_location_stock')

        computation_key = f"{self.env.uid}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}"

        Report.search([('computation_key', '=', computation_key)]).unlink()

        domain = [
            ('state', '=', 'done'),
            ('date', '<=', self._datetime_to()),
            '|',
            ('location_id', '=', main_stock.id),
            ('location_dest_id', '=', main_stock.id),
        ]

        if self.rm_type:
            domain.append(('product_id.product_tmpl_id', '=', self.rm_type.id))

        if self.party_id:
            domain.append(('move_id.party_id', '=', self.party_id.id))

        move_lines = MoveLine.search(domain)

        aggregated = {}

        for ml in move_lines:
            product = ml.product_id
            tmpl = product.product_tmpl_id
            picking = ml.move_id.picking_id

            if not (tmpl.purchase_ok and not tmpl.sale_ok):
                continue

            qty = ml.qty_done
            if not qty:
                continue

            # -------------------------------
            # NET STOCK CALCULATION
            # -------------------------------
            if ml.location_dest_id.id == main_stock.id:
                delta = qty
            elif ml.location_id.id == main_stock.id:
                delta = -qty
            else:
                continue

            mfi = ''
            batch = ''

            if picking:
                mfi_val = getattr(picking, 'mfi_value', None)
                batch_val = getattr(picking, 'supplier_batch_number', None)

                mfi = str(mfi_val).strip() if mfi_val not in (None, False) else ''
                batch = str(batch_val).strip() if batch_val not in (None, False) else ''

            grade = self._get_grade(product)
            internal_batch = ml.lot_id.name if ml.lot_id else ''

            key = (tmpl.id, grade, internal_batch)

            if key not in aggregated:
                aggregated[key] = {
                    'rm_type': tmpl,
                    'grade': grade,
                    'mfi': mfi,
                    'batch': batch,
                    'internal_batch': internal_batch,
                    'party': ml.move_id.party_id,
                    'kgs': 0.0,
                }

            aggregated[key]['kgs'] += delta

        # -------------------------------
        # CREATE FINAL RECORDS
        # -------------------------------
        BAG_CAPACITY = 25.0

        for data in aggregated.values():
            if data['kgs'] <= 0:
                continue

            bags = math.ceil(data['kgs'] / BAG_CAPACITY)

            Report.create({
                'computation_key': computation_key,
                'date': self.date,
                'party_id': data['party'].id if data['party'] else False,
                'location_id': main_stock.id,
                'rm_type': data['rm_type'].id,
                'grade': data['grade'],
                'mfi': data['mfi'],
                'batch': data['batch'],
                'internal_batch': data['internal_batch'],
                'bag_qty': bags,
                'kgs': data['kgs'],
                'total_kgs': data['kgs'],
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Stock Sheet Report'),
            'res_model': 'rm.stock.sheet.report',
            'view_mode': 'list',
            'domain': [('computation_key', '=', computation_key)],
            'target': 'current',
        }
