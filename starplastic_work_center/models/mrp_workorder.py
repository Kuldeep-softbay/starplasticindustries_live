from odoo import api, models, fields
from odoo.exceptions import ValidationError
import re

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    
    workcenter_id = fields.Many2one(
        'mrp.workcenter',
        string="Suitable Machine"
    )
    batch_number = fields.Char('Batch Number')
    expected_delivery_date = fields.Datetime('Expected Delivery Date')
    actual_delivery_date = fields.Datetime('Actual Delivery Date')
    remark = fields.Text('Remark')
    produced_quantity = fields.Float('Produced Quantity')
    remaining_quantity = fields.Float('Remaining Quantity')
    planned_start_date = fields.Datetime('Planned Start Date')
    planned_end_date = fields.Datetime('Planned End Date')
    creation_date = fields.Datetime('W.O Date')
    customer_order_quantity = fields.Float(
        string='CO Quantity',
        compute='_compute_customer_order_qty',
        store=True
    )
    customer_po_number = fields.Char(
        string='C.O Number',
        related='production_id.customer_po_number',
        store=True,
        readonly=True
    )
    @api.depends(
        "qty_production",
        "operation_id",
        "operation_id.time_cycle_manual",
        "operation_id.cavity",
    )
    def _compute_duration_expected(self):
        for wo in self:
            duration = 0.0

            operation = wo.operation_id
            qty = wo.qty_production or wo.production_id.product_qty

            if operation and operation.time_cycle_manual:
                duration = operation.compute_operation_duration(qty)

            wo.duration_expected = duration

    @api.depends('production_id.origin', 'product_id')
    def _compute_customer_order_qty(self):
        for wo in self:
            qty = 0.0

            if wo.production_id and wo.production_id.origin:
                match = re.search(r'\bS\d+\b', wo.production_id.origin)
                if match:
                    so_name = match.group(0)

                    so = self.env['sale.order'].search(
                        [('name', '=', so_name)],
                        limit=1
                    )

                    if so:
                        solines = so.order_line.filtered(
                            lambda l: l.product_id == wo.product_id
                        )
                        qty = sum(solines.mapped('product_uom_qty'))

            wo.customer_order_quantity = qty

    @api.model
    def create(self, vals):
        """Assign creation_date automatically on record creation."""
        if not vals.get('creation_date'):
            vals['creation_date'] = fields.Datetime.now()
        return super(MrpWorkorder, self).create(vals)


class JobPartyWork(models.Model):
    _name = 'job.party.work'
    _description = 'Job Party Work'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char('Job Party Name')
    work_type = fields.Selection([
        ('inward', 'Inward'),
        ('outword', 'Outword')
    ], string='Type')
    remark = fields.Text('Remark')

    party_ids = fields.One2many(
        'stock.picking',
        'party_id',
        string='Job Party Pickings'
    )
