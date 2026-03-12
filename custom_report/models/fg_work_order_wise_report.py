from odoo import api, fields, models, _
from datetime import datetime


class FgWorkOrderWiseLine(models.Model):
    _name = 'fg.work.order.wise.line'
    _description = 'FG Work Order Wise Report Line'
    _order = 'lot_id, id'

    computation_key = fields.Char(index=True)

    party_id = fields.Many2one('job.party.work', string='Party')
    product_id = fields.Many2one('product.product', string='Item')

    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch. No',
        domain="[('product_id', '=', product_id)]"
    )

    actual_stock = fields.Float(string='Actual Stock')
    stock_available_for_packing = fields.Float(string='Stock Available for Packing')
    unit_weight = fields.Float(string='Unit Weight')
    date = fields.Date(default=fields.Date.context_today)
    location_id = fields.Many2one('stock.location', string='Location')



class FgWorkOrderWiseWizard(models.TransientModel):
    _name = 'fg.work.order.wise.wizard'
    _description = 'FG Work Order Wise Wizard'

    party_id = fields.Many2one('job.party.work', string='Party')
    product_id = fields.Many2one('product.product', string='Item',
                                domain="[('purchase_ok','=',False),('sale_ok','=',True)]")

    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch. No',
        domain=lambda self: self._get_lot_domain()
    )

    def _get_lot_domain(self):
        domain = []
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        domain.append(('quant_ids.quantity', '>', 0))
        domain.append(('quant_ids.location_id.usage', '=', 'internal'))
        return domain

    location_id = fields.Many2one(
        'stock.location',
        string='Location',
        domain="[('usage','=','internal')]"
    )

    def _compute_product_stock(self, product):
        """Return (actual_stock, available_for_packing, unit_weight) for a product.
        Simple heuristic; change to your business rules if needed.
        """
        if not product:
            return 0.0, 0.0, 0.0
        actual = float(product.qty_available or 0.0)
        outgoing = float(getattr(product, 'outgoing_qty', 0.0) or 0.0)
        available_for_packing = actual - outgoing
        if available_for_packing < 0:
            available_for_packing = 0.0
        unit_weight = float(getattr(product, 'product_weight_sale', None) or getattr(product, 'weight', 0.0) or 0.0)
        return actual, available_for_packing, unit_weight

    def _compute_lot_stock(self, product, lot, location):
        Quant = self.env['stock.quant']
        domain = [
            ('product_id', '=', product.id),
            ('lot_id', '=', lot.id),
            ('quantity', '>', 0),
        ]
        if location:
            domain.append(('location_id', 'child_of', location.id))

        quants = Quant.search(domain)
        actual = sum(quants.mapped('quantity'))
        return actual

    def action_show_report(self):
        self.ensure_one()
        ReportLine = self.env['fg.work.order.wise.line']
        WorkOrder = self.env['mrp.workorder']

        computation_key = f"{self.env.uid}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        domain = []

        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))

        # if self.lot_id:
        #     domain.append(('lot_id', '=', self.lot_id.id))

        workorders = WorkOrder.search(domain, order='id desc')
        if not workorders:
            return

        for wo in workorders:
            product = wo.product_id
            actual, avail, unit_weight = self._compute_product_stock(product)

            party_id = False
            mo = wo.production_id
            lot = wo.production_id.lot_producing_id
            if not lot:
                continue

            actual = self._compute_lot_stock(product, lot, self.location_id)

            # Zero stock batch skip
            if actual <= 0:
                continue
            if self.party_id:
                party_id = self.party_id.id
            elif mo and hasattr(mo, 'sale_order_id') and mo.sale_order_id:
                party_id = mo.sale_order_id.party_id.id

            ReportLine.create({
                'computation_key': computation_key,
                'party_id': party_id,
                'product_id': product.id,
                'lot_id': lot.id,
                'actual_stock': actual,
                'stock_available_for_packing': avail,
                'unit_weight': unit_weight,
                'location_id': self.location_id.id if self.location_id else False,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': _('FG Work Order Wise Report'),
            'res_model': 'fg.work.order.wise.line',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('computation_key', '=', computation_key)],
        }