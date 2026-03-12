from odoo import api, fields, models, _
from datetime import datetime


class FgStoreReport(models.Model):
    _name = 'fg.store.report'
    _description = 'FG Stock Report'
    _order = 'date, id'

    computation_key = fields.Char(string='Computation Key', index=True)

    date = fields.Date(string='Date')
    partner_id = fields.Many2one('res.partner', string='Party')
    batch_number = fields.Char(string='Batch Number')
    pmemo = fields.Char(string='Pmemo')
    invoice_number = fields.Char(string='Invoice Number')
    unit_weight = fields.Float(string='Unit Weight')
    received_qty = fields.Float(string='Received')
    issued_qty = fields.Float(string='Issued')
    balance_qty = fields.Float(string='Balance')

    product_id = fields.Many2one('product.product', string='Item Name')
    stock_type = fields.Selection(
        [
            ('fg', 'Finished Goods'),
            ('rm', 'Raw Material'),
            ('cons', 'Consumable'),
        ],
        string='Stock Type',
    )


class FgStoreReportWizard(models.TransientModel):
    _name = 'fg.store.report.wizard'
    _description = 'FG Stock Report Wizard'

    date_from = fields.Date(string='Date From', required=True,
                            default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(string='Date To', required=True,
                          default=lambda self: fields.Date.context_today(self))
    partner_id = fields.Many2one('res.partner', string='Party')
    product_id = fields.Many2one('product.product', string='Item Name',
                                domain="[('purchase_ok','=',False),('sale_ok','=',True)]")
    stock_type = fields.Selection(
        [
            ('fg', 'Finished Goods'),
            ('rm', 'Raw Material'),
            ('cons', 'Consumable'),
        ],
        string='Stock Type',
    )

    def _build_domain(self):
        """Build domain for stock moves or your custom table."""
        self.ensure_one()
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.partner_id:
            domain.append(('move_id.partner_id', '=', self.partner_id.id))

        # stock_type is custom, adapt as needed
        return domain

    def action_show_report(self):
        self.ensure_one()

        report_env = self.env['fg.store.report']
        computation_key = f"{self.env.uid}-{fields.Datetime.now()}"

        domain = self._build_domain()
        domain.append(('state', '=', 'done'))

        move_lines = self.env['stock.move.line'].search(domain, order='date, id')

        lot_received_map = {}
        issued_lines = []

        for ml in move_lines:
            qty = ml.qty_done
            if not qty:
                continue

            move = ml.move_id
            product = ml.product_id
            lot = ml.lot_id
            picking = move.picking_id

            # ---------- RECEIPT ----------
            if ml.location_dest_id.usage == 'internal' and ml.location_id.usage != 'internal':
                lot_key = lot.id or 0

                data = lot_received_map.setdefault(lot_key, {
                    'date': ml.date.date(),
                    'partner_id': move.partner_id.id if move.partner_id else False,
                    'batch_number': lot.name if lot else '',
                    'pmemo': move.reference or '',
                    'invoice_number': picking.invoice_number if picking else '',
                    'unit_weight': product.weight or 0.0,
                    'product_id': product.id,
                    'received_qty': 0.0,
                })

                data['received_qty'] += qty

            # ---------- ISSUE ----------
            elif ml.location_id.usage == 'internal' and ml.location_dest_id.usage != 'internal':
                dispatch_date = (
                    picking.actual_dispatch_date
                    if picking and picking.actual_dispatch_date
                    else ml.date.date()
                )

                issued_lines.append({
                    'date': dispatch_date,
                    'partner_id': move.partner_id.id if move.partner_id else False,
                    'batch_number': lot.name if lot else '',
                    'pmemo': move.reference or '',
                    'invoice_number': picking.invoice_number if picking else '',
                    'unit_weight': product.weight or 0.0,
                    'product_id': product.id,
                    'issued_qty': qty,
                })

        # Sort for correct running balance
        received_vals = sorted(lot_received_map.values(), key=lambda x: x['date'])
        issued_vals = sorted(issued_lines, key=lambda x: x['date'])

        balance = 0.0

        # ----- RECEIVED -----
        for vals in received_vals:
            balance += vals['received_qty']
            vals.update({
                'computation_key': computation_key,
                'issued_qty': 0.0,
                'balance_qty': balance,
                'stock_type': self.stock_type,
            })
            report_env.create(vals)

        # ----- ISSUED -----
        for vals in issued_vals:
            balance -= vals['issued_qty']
            vals.update({
                'computation_key': computation_key,
                'received_qty': 0.0,
                'balance_qty': balance,
                'stock_type': self.stock_type,
            })
            report_env.create(vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('FG Stock Report'),
            'res_model': 'fg.store.report',
            'view_mode': 'list',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }

