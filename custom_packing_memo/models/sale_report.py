from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class SaleReport(models.Model):
    _inherit = 'sale.report'

    product_weight = fields.Float(string="Product Weight", readonly=True)
    opening_stock = fields.Float(string="Opening Stock", compute="_compute_stock_balances")
    closing_stock = fields.Float(string="Closing Stock", compute="_compute_stock_balances")
    production_qty = fields.Float(string="Production", compute="_compute_stock_balances")
    dispatch_qty = fields.Float(string="Dispatch", compute="_compute_stock_balances")

    def _select_additional_fields(self):
        res = super()._select_additional_fields()
        res.update({"product_weight": "MAX(t.weight)"})
        return res

    @api.depends('product_id', 'date')
    def _compute_stock_balances(self):
        Move = self.env['stock.move']

        groups = {}
        for rec in self:
            rec.opening_stock = rec.closing_stock = 0.0
            rec.production_qty = rec.dispatch_qty = 0.0

            if not rec.product_id or not rec.date:
                continue

            dt = fields.Datetime.to_datetime(rec.date)
            month_start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            key = (rec.product_id.id, month_start)
            groups.setdefault(key, []).append(rec)

        if not groups:
            return

        def _sum_qty(domain):
            data = Move.read_group(domain, ['product_uom_qty'], [])
            return data[0]['product_uom_qty'] if data else 0.0


        for (product_id, month_start), recs in groups.items():
            product = self.env['product.product'].browse(product_id)
            product_weight = product.weight or 0.0
            month_end = month_start + relativedelta(months=1)

            domain_before_start = [
                ('product_id', '=', product_id),
                ('state', '=', 'done'),
                ('date', '<', month_start),
            ]
            domain_before_end = [
                ('product_id', '=', product_id),
                ('state', '=', 'done'),
                ('date', '<', month_end),
            ]

            incoming_before_start = _sum_qty(
                domain_before_start + [('location_dest_id.usage', '=', 'internal')]
            )
            outgoing_before_start = _sum_qty(
                domain_before_start + [('location_id.usage', '=', 'internal')]
            )

            incoming_before_end = _sum_qty(
                domain_before_end + [('location_dest_id.usage', '=', 'internal')]
            )
            outgoing_before_end = _sum_qty(
                domain_before_end + [('location_id.usage', '=', 'internal')]
            )

            opening_qty = incoming_before_start - outgoing_before_start
            closing_qty = incoming_before_end - outgoing_before_end

            domain_month = [
                ('product_id', '=', product_id),
                ('state', '=', 'done'),
                ('date', '>=', month_start),
                ('date', '<', month_end),
            ]

            production_qty = _sum_qty(domain_month + [
                    ('production_id', '!=', False),
                    ('location_dest_id.usage', '=', 'internal'),
                ]
            )

            dispatch_qty = _sum_qty(
                domain_month + [
                    ('location_id.usage', '=', 'internal'),
                    ('location_dest_id.usage', 'in',
                     ['customer', 'supplier', 'inventory', 'production']),
                ]
            )

            for rec in recs:
                rec.opening_stock = opening_qty
                rec.closing_stock = closing_qty
                rec.production_qty = production_qty
                rec.dispatch_qty = dispatch_qty

