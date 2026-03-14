from odoo import api, fields, models, _
import re
import logging
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    batch_number = fields.Char('Batch Number')
    expected_delivery_date = fields.Date('Expected Delivery Date')
    warehouse_verified = fields.Boolean('Warehouse Verified', default=False)
    hourly_entry_count = fields.Integer(string='Hourly Entries', compute='_compute_hourly_entry_count')
    sale_order_qty = fields.Float(
        string='C.O Quantity',
        compute='_compute_customer_order',
        store=True
    )

    customer_po_number = fields.Char(
        string='C.O Number',
        compute='_compute_customer_order',
        store=True
    )

    wo_qty = fields.Float(string='WO Qty', compute='_compute_customer_order', store=True)

    unit_weight = fields.Float(string="Unit Weight")
    total_kg = fields.Float(string="Total KG")
    total_pcs = fields.Integer(
        string="Total PCS",
        compute="_compute_total_pcs",
        store=True
    )
    unit_weight_kg = fields.Float(
        string="Unit Weight (KG)",
        compute="_compute_unit_weight_kg",
        store=True)

    pmemo_ids = fields.One2many(
        'production.memo',
        'production_id',
        string='Production Memos'
    )
    rm_return_ids = fields.One2many(
        'mrp.rm.return.line',
        'production_id',
        string="RM Return"
    )

    rm_return_count = fields.Integer(
            compute="_compute_rm_return_count"
        )

    def _compute_rm_return_count(self):
        for rec in self:
            rec.rm_return_count = len(rec.rm_return_ids)

    pmemo_number = fields.Char()
    workcenter_id = fields.Many2one("mrp.workcenter")
    colour = fields.Char()
    production_qty = fields.Float()
    date = fields.Date(compute="_compute_pmemo_header", store=True)
    workcenter_id = fields.Many2one("mrp.workcenter", compute="_compute_pmemo_header", store=True)
    production_qty = fields.Float(compute="_compute_pmemo_header", store=True)
    lot_id = fields.Many2one("stock.lot", compute="_compute_pmemo_header", store=True)
    unit_weight = fields.Float(compute="_compute_pmemo_header", store=True)


    # ---- Raw Material Formulation ----
    rm_required_qty = fields.Float(compute="_compute_pmemo", store=True)
    rm_issued_qty = fields.Float(compute="_compute_pmemo", store=True)
    rm_loss_qty = fields.Float(compute="_compute_pmemo", store=True)
    rm_loss_percent = fields.Float(compute="_compute_pmemo", store=True)
    rm_to_be_made = fields.Float(compute="_compute_pmemo", store=True)

    fg_qty = fields.Float(compute="_compute_pmemo", store=True)
    fg_weight = fields.Float(compute="_compute_pmemo", store=True)
    yeild_percent = fields.Float(compute="_compute_pmemo", store=True)

    rm_type = fields.Many2one(
        "product.product",
        compute="_compute_pmemo_extra",
        store=True
    )
    cavity = fields.Integer(
        compute="_compute_pmemo_extra",
        store=True
    )

    rm_return_ids = fields.One2many(
        'mrp.rm.return.line',
        'production_id',
        string="RM Return"
    )

    rm_return_qty = fields.Float(
        string="Rm Return Qty",
        compute="_compute_rm_return_qty",
        store=True
    )

    @api.depends('rm_return_ids.quantity')
    def _compute_rm_return_qty(self):
        for rec in self:
            rec.rm_return_qty = sum(
                rec.rm_return_ids.mapped('quantity')
            )

    shift_ids = fields.One2many(
        'work.center.shift',
        'production_id',
        string="Shifts"
    )

    total_shift_produced_qty = fields.Float(
        string="Total Produced (Nos)",
        compute="_compute_total_shift_produced",
        store=True
    )

    total_kg = fields.Float(
        string="Total Production (Kg)",
        compute="_compute_total_kg",
        store=True
    )

    @api.depends('total_shift_produced_qty', 'unit_weight')
    def _compute_total_kg(self):
        for rec in self:
            rec.total_kg = rec.total_shift_produced_qty * rec.unit_weight

    @api.depends('shift_ids.total_produced_qty')
    def _compute_total_shift_produced(self):
        for rec in self:
            rec.total_shift_produced_qty = sum(
                rec.shift_ids.mapped('total_produced_qty')
            )

    @api.depends(
        "state",
        "bom_id.bom_line_ids.product_id",
        "bom_id.operation_ids.cavity",
    )
    def _compute_pmemo_extra(self):
        for rec in self:
            rec.rm_type = False
            rec.cavity = 0

            if rec.state != "done":
                continue

            raw_moves = rec.move_raw_ids.filtered(
                lambda m: m.state == "done"
            )
            if raw_moves:
                rec.rm_type = raw_moves[0].product_id

            if rec.bom_id and rec.bom_id.operation_ids:
                rec.cavity = rec.bom_id.operation_ids[0].cavity or 0

    @api.depends(
        "state",
        "date_finished",
        "qty_produced",
        "product_id",
        "lot_producing_id",
        "workorder_ids.workcenter_id",
    )
    def _compute_pmemo_header(self):
        for rec in self:
            rec.date = False
            rec.workcenter_id = False
            rec.production_qty = 0.0
            rec.lot_id = False
            rec.unit_weight = 0.0

            if rec.state != "done":
                continue

            rec.date = rec.date_finished.date() if rec.date_finished else fields.Date.today()
            rec.production_qty = rec.qty_produced
            rec.lot_id = rec.lot_producing_id
            rec.unit_weight = rec.product_id.weight or 0.0
            if rec.workorder_ids:
                rec.workcenter_id = rec.workorder_ids[0].workcenter_id

    @api.depends(
        "state",
        "product_qty",
        "bom_id",
        "move_raw_ids.move_line_ids.qty_done",
        "move_finished_ids.move_line_ids.qty_done",
        "rm_return_qty",
    )
    def _compute_pmemo(self):
        for rec in self:
            # ---- Default values ----
            rec.rm_required_qty = 0.0
            rec.rm_issued_qty = 0.0
            rec.rm_loss_qty = 0.0
            rec.rm_loss_percent = 0.0
            rec.rm_to_be_made = 0.0
            rec.fg_qty = 0.0
            rec.fg_weight = 0.0
            rec.yeild_percent = 0.0

            if rec.state != "done":
                continue

            # ---- RM REQUIRED (from BOM) ----
            if rec.bom_id and rec.bom_id.product_qty:
                factor = rec.product_qty / rec.bom_id.product_qty
                rec.rm_required_qty = sum(
                    line.product_qty * factor
                    for line in rec.bom_id.bom_line_ids
                )

            # ---- RM ISSUED & RETURNED ----
            issued = 0.0
            for move in rec.move_raw_ids.filtered(lambda m: m.state == "done"):
                for ml in move.move_line_ids:
                    if ml.location_dest_id.usage == "production":
                        issued += ml.qty_done

            rec.rm_issued_qty = issued

            # ---- RM LOSS ----
            loss = issued - rec.rm_required_qty - rec.rm_return_qty
            rec.rm_loss_qty = max(loss, 0.0)
            rec.rm_loss_percent = (
                (rec.rm_loss_qty / rec.rm_required_qty) * 100
                if rec.rm_required_qty else 0.0
            )

            rec.rm_to_be_made = (
                rec.rm_required_qty
                - rec.rm_issued_qty
                + rec.rm_return_qty
            )

            # ---- FG QTY & WEIGHT ----
            fg_qty = sum(
                ml.qty_done
                for move in rec.move_finished_ids.filtered(lambda m: m.state == "done")
                for ml in move.move_line_ids
            )
            rec.fg_qty = fg_qty
            rec.fg_weight = fg_qty * rec.unit_weight

            # ---- YIELD ----
            rec.yeild_percent = (
                (rec.fg_weight / rec.rm_issued_qty) * 100
                if rec.rm_issued_qty
                else 0.0
            )

    # --------------------------------
    # Convert Unit Weight Gram → KG
    # --------------------------------
    @api.depends('unit_weight')
    def _compute_unit_weight_kg(self):
        for rec in self:
            rec.unit_weight_kg = rec.unit_weight / 1000 if rec.unit_weight else 0.0

    @api.depends('total_kg', 'unit_weight_kg')
    def _compute_total_pcs(self):
        for rec in self:
            if rec.unit_weight_kg > 0:
                rec.total_pcs = int(rec.total_kg / rec.unit_weight_kg)
            else:
                rec.total_pcs = 0

    @api.depends('origin', 'product_id')
    def _compute_customer_order(self):
        for mo in self:
            qty = 0.0
            po_number = False
            wo_qty = 0.0

            if mo.origin:
                so = self.env['sale.order'].search([
                    ('name', '=', mo.origin)
                ], limit=1)

                if so:
                    sol = so.order_line.filtered(
                        lambda l: l.product_id == mo.product_id
                    )

                    if sol:
                        qty = sol.product_uom_qty
                        po_number = sol.co_number
                        wo_qty = sol.wo_qty

            mo.sale_order_qty = qty
            mo.customer_po_number = po_number
            mo.wo_qty = wo_qty

    def action_view_shifts(self):
        self.ensure_one()
        try:
            action = self.env.ref('starplastic_work_center.action_wc_shift').read()[0]
        except Exception as e:
            _logger.warning("Shift action not found, using inline action. Details: %s", e)
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Shifts',
                'res_model': 'work.center.shift',
                'view_mode': 'list,form',
            }
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {'default_production_id': self.id, 'search_default_production_id': self.id}
        return action

    def _compute_hourly_entry_count(self):
        if not self.ids:
            for rec in self:
                rec.hourly_entry_count = 0
            return

        groups = self.env['work.center.hourly.entry'].read_group(
            domain=[('production_id', 'in', self.ids)],
            fields=['production_id'],
            groupby=['production_id'],
        )
        counts = {}
        for g in groups:
            if g.get('production_id'):
                prod_id = g['production_id'][0]
                cnt = g.get('__count', 0)
                if cnt == 0:
                    cnt = g.get('production_id_count', 0)
                counts[prod_id] = cnt

        for rec in self:
            rec.hourly_entry_count = counts.get(rec.id, 0)

    def action_view_hourly_entries(self):
        self.ensure_one()
        try:
            action = self.env.ref('starplastic_work_center.action_work_center_hourly_entry_master').read()[0]
        except Exception as e:
            _logger.warning("Hourly entries action not found, using inline action. Details: %s", e)
            action = {
                'type': 'ir.actions.act_window',
                'name': 'Hourly Entries',
                'res_model': 'work.center.hourly.entry',
                'view_mode': 'list,form',
            }
        action['domain'] = [('production_id', '=', self.id)]
        action['context'] = {'default_production_id': self.id}
        return action

    def write(self, vals):
        res = super().write(vals)

        if "row_material_returned" in vals:
            for mo in self:
                if mo.row_material_returned > 0:
                    mo._create_rm_return_move()

        return res

    def _create_rm_return_move(self):
        self.ensure_one()

        raw_move = self.move_raw_ids.filtered(lambda m: m.state == "done")
        if not raw_move:
            return

        base_move = raw_move[0]

        move = self.env["stock.move"].create({
            "name": f"RM Return {self.name}",
            "product_id": base_move.product_id.id,
            "product_uom_qty": self.row_matterial_returned,
            "product_uom": base_move.product_uom.id,
            "location_id": base_move.location_dest_id.id,
            "location_dest_id": base_move.location_id.id,
            "production_id": self.id,
            "company_id": self.company_id.id,
        })

        self.env["stock.move.line"].create({
            "move_id": move.id,
            "product_id": move.product_id.id,
            "product_uom_id": move.product_uom.id,
            "qty_done": self.row_matterial_returned,
            "location_id": move.location_id.id,
            "location_dest_id": move.location_dest_id.id,
            "company_id": self.company_id.id,
        })

        move._action_done()



class MrpProductionRmLine(models.Model):
    _name = "mrp.production.rm.line"
    _description = "MRP Production Raw Material Line"

    production_id = fields.Many2one(
        "mrp.production",
        string="Production",
        required=True,
        ondelete="cascade",
    )
    rm_type = fields.Many2one(
        "product.product",
        string="Raw Material",
        required=True,
        domain="[('purchase_ok','=',True),('sale_ok','=',False)]"
    )
    uom_id = fields.Many2one("uom.uom", string="UoM", required=True)
    bom_qty = fields.Float(string="RM Required (BOM)")
    issued_qty = fields.Float(string="RM Issued")
    return_qty = fields.Float(string="RM Returned")
    loss_qty = fields.Float(string="RM Loss Qty")
    to_be_made_qty = fields.Float(string="RM To Be Made")
    loss_percent = fields.Float(string="RM Loss (%)")
