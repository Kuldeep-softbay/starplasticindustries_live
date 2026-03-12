from odoo import models, fields

class MachineData(models.Model):
    _name = "machine.data"
    _description = "Machine Data Entry"

    name = fields.Char("Item RM & Color")

    workorder_id = fields.Many2one("mrp.workorder")
    production_id = fields.Many2one("mrp.production")

    workcenter_id = fields.Many2one("mrp.workcenter")
    machine_type = fields.Selection(
        related="workcenter_id.machine_type",
        store=True
    )

    product_id = fields.Many2one("product.product")
    date = fields.Date(default=fields.Date.today)

    # -------- Injaction Machine --------
    ing_sec = fields.Float("ING (Sec)")
    ing_pressure = fields.Float("ING Pressure")

    rlp_sec = fields.Float("RLP (Sec)")
    rlp_pressure = fields.Float("RLP Pressure")

    cooling_sec = fields.Float("Cooling (Sec)")
    rm_feed = fields.Float("RM Feed")
    locking_tonnage = fields.Float("Locking Tonnage")

    temp_zone_1 = fields.Float("Temp Zone 1")
    temp_zone_2 = fields.Float("Temp Zone 2")
    temp_zone_3 = fields.Float("Temp Zone 3")
    temp_zone_4 = fields.Float("Temp Zone 4")
    temp_zone_5 = fields.Float("Temp Zone 5")
    temp_zone_6 = fields.Float("Temp Zone 6")
    temp_zone_7 = fields.Float("Temp Zone 7")

    # -------- Blow Mould Machine --------
    die_core_left = fields.Float("Die Core Left")
    die_core_right = fields.Float("Die Core Right")

    shooting_sec = fields.Float("Shooting (sec)")
    blow_pin_delay = fields.Float("Blow Pin Delay")
    blow_delay = fields.Float("Blow Delay")

    blowing_sec = fields.Float("Blowing (sec)")
    exhaust_cooling = fields.Float("Exhaust Cooling")

    eject_time = fields.Float("Eject Time")

    m_close_p = fields.Float("M Close P")
    m_close_f = fields.Float("M Close F")

    tube_time = fields.Float("Tube Time")

    cutter_mode = fields.Selection([
        ('normal', 'Normal'),
        ('auto', 'Auto')
    ])

    cut_delay = fields.Float("Cut Delay")
    cut_time = fields.Float("Cut Time")

    temp_1 = fields.Float("Temp 1")
    temp_2 = fields.Float("Temp 2")
    temp_3 = fields.Float("Temp 3")
    temp_4 = fields.Float("Temp 4")
    temp_5 = fields.Float("Temp 5")
    temp_6 = fields.Float("Temp 6")
    temp_7 = fields.Float("Temp 7")
    temp_8 = fields.Float("Temp 8")

    notes = fields.Text()

class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    def action_open_machine_data(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Machine Data",
            "res_model": "machine.data",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {
                "default_workorder_id": self.id,
                "default_production_id": self.production_id.id,
                "default_workcenter_id": self.workcenter_id.id,
                "default_product_id": self.product_id.id,
            },
        }
