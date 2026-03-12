from odoo import models, fields, tools


class MachineDataReport(models.Model):
    _name = "machine.data.report"
    _description = "Machine Data Report"
    _auto = False
    _order = "date desc"

    date = fields.Date(string="Date", readonly=True)
    workcenter_id = fields.Many2one("mrp.workcenter", string="Machine", readonly=True)
    product_id = fields.Many2one("product.product", string="Item", readonly=True)

    ing_sec = fields.Float(string="ING (Sec)", readonly=True)
    ing_pressure = fields.Float(string="ING P", readonly=True)

    rlp_sec = fields.Float(string="RLP (Sec)", readonly=True)
    rlp_pressure = fields.Float(string="RLP P", readonly=True)

    cooling_sec = fields.Float(string="Cooling", readonly=True)
    rm_feed = fields.Float(string="RM Feed", readonly=True)
    locking_tonnage = fields.Float(string="Locking", readonly=True)

    temp_zone_1 = fields.Float(string="T1", readonly=True)
    temp_zone_2 = fields.Float(string="T2", readonly=True)
    temp_zone_3 = fields.Float(string="T3", readonly=True)
    temp_zone_4 = fields.Float(string="T4", readonly=True)
    temp_zone_5 = fields.Float(string="T5", readonly=True)
    temp_zone_6 = fields.Float(string="T6", readonly=True)
    temp_zone_7 = fields.Float(string="T7", readonly=True)

    notes = fields.Text(string="Notes", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE VIEW machine_data_report AS (
                SELECT
                    row_number() OVER() AS id,

                    md.date,
                    md.workcenter_id,
                    md.product_id,

                    md.ing_sec,
                    md.ing_pressure,
                    md.rlp_sec,
                    md.rlp_pressure,
                    md.cooling_sec,
                    md.rm_feed,
                    md.locking_tonnage,

                    md.temp_zone_1,
                    md.temp_zone_2,
                    md.temp_zone_3,
                    md.temp_zone_4,
                    md.temp_zone_5,
                    md.temp_zone_6,
                    md.temp_zone_7,

                    md.notes

                FROM machine_data md
            )
        """)
