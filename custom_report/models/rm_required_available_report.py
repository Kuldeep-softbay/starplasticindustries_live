# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, time
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    party_id = fields.Many2one(
        'job.party.work',
        string='Party',
        index=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves:
            if not move.party_id:
                if move.picking_id and hasattr(move.picking_id, 'party_id'):
                    move.party_id = move.picking_id.party_id.id
                elif move.raw_material_production_id and hasattr(
                    move.raw_material_production_id, 'party_id'
                ):
                    move.party_id = move.raw_material_production_id.party_id.id
        return moves

class RmRequiredAvailableReport(models.Model):
    _name = 'rm.required.available.report'
    _description = 'RM Required and Available Report'
    _order = 'product_id'

    computation_key = fields.Char(index=True)

    product_id = fields.Many2one(
        'product.product',
        string='Raw Material',
        readonly=True
    )

    rm_required_qty = fields.Float(string='RM Required', readonly=True)
    rm_available_qty = fields.Float(string='RM Available', readonly=True)
    difference_qty = fields.Float(string='Difference', readonly=True)

    location_id = fields.Many2one('stock.location', string='Location', readonly=True)


class RmRequiredAvailableWizard(models.TransientModel):
    _name = 'rm.required.available.wizard'
    _description = 'RM Required and Available Wizard'

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=fields.Date.context_today
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.context_today
    )

    party_id = fields.Many2one(
        'job.party.work',
        string='Party',
        required=False
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product'
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage','=','internal')]"
    )

    # -----------------------------------------------------
    # DATE HELPERS
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
        domain = [
            ('state', '=', 'done'),
            ('date', '>=', self._datetime_from()),
            ('date', '<=', self._datetime_to()),
        ]

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        if self.party_id:
            domain.append(('party_id', '=', self.party_id.id))

        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

        return domain

    def _compute_opening_balance(self, tmpl_id):
        Move = self.env['stock.move']
        opening = 0.0

        domain = [
            ('state', '=', 'done'),
            ('date', '<', self._datetime_from()),
            ('product_id.product_tmpl_id', '=', tmpl_id),
        ]

        if self.location_id:
            domain.extend([
                '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id),
            ])

        for mv in Move.search(domain):
            qty = mv.product_uom_qty
            if mv.location_dest_id.usage == 'internal':
                opening += qty
            if mv.location_id.usage == 'internal':
                opening -= qty

        return opening

    def action_show_report(self):
        self.ensure_one()

        Move = self.env['stock.move']
        Report = self.env['rm.required.available.report']

        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        # Clean previous results
        Report.search([('computation_key', '=', computation_key)]).unlink()

        moves = Move.search(self._base_domain())

        rm_totals = {}

        for mv in moves:
            tmpl = mv.product_id.product_tmpl_id

            if not (tmpl.purchase_ok and not tmpl.sale_ok):
                continue

            tmpl_id = tmpl.id

            if tmpl_id not in rm_totals:
                rm_totals[tmpl_id] = {
                    'product_id': mv.product_id.id,
                    'required': 0.0,
                    'available': self._compute_opening_balance(tmpl_id),
                }

            qty = mv.product_uom_qty

            if mv.location_dest_id.usage == 'internal':
                rm_totals[tmpl_id]['available'] += qty

            if mv.location_id.usage == 'internal':
                rm_totals[tmpl_id]['required'] += qty
                rm_totals[tmpl_id]['available'] -= qty

        for tmpl_id, data in rm_totals.items():
            Report.create({
                'computation_key': computation_key,
                'product_id': data['product_id'],
                'rm_required_qty': data['required'],
                'rm_available_qty': data['available'],
                'difference_qty': data['required'] - data['available'],
                'location_id': self.location_id.id if self.location_id else False,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('RM Required and Available Report'),
            'res_model': 'rm.required.available.report',
            'view_mode': 'list',
            'domain': [('computation_key', '=', computation_key)],
        }
