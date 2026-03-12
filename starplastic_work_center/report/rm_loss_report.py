from odoo import models, fields, tools


class RMLossReport(models.Model):
    _name = "rm.loss.report"
    _description = "RM Loss Report"
    _auto = False
    _rec_name = "pmemo_number"

    date = fields.Date(string="Date")
    product_id = fields.Many2one("product.product", string="Item")
    rm_type = fields.Many2one("product.product", string="RM Type")
    colour = fields.Char(string="Color")
    pmemo_number = fields.Char(string="P-Memo No")
    lot_id = fields.Many2one("stock.lot", string="Batch No")
    loss_kg = fields.Float(string="Loss (Kg)")
    loss_percent = fields.Float(string="Loss (%)")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW rm_loss_report AS (
                SELECT
                    row_number() OVER () AS id,
                    mo.date_finished::date AS date,
                    mo.product_id AS product_id,
                    mo.rm_type AS rm_type,
                    mo.colour AS colour,
                    mo.pmemo_number AS pmemo_number,
                    mo.lot_id AS lot_id,
                    mo.rm_loss_qty AS loss_kg,
                    mo.rm_loss_percent AS loss_percent
                FROM mrp_production mo
                WHERE
                    mo.state = 'done'
                    AND mo.rm_loss_qty > 0
            )
        """)
