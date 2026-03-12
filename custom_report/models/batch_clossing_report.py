from odoo import api, fields, models, tools

class BatchClosingReport(models.Model):
    _name = "batch.closing.report"
    _description = "Batch Closing Report"
    _auto = False
    _order = "wo_date desc"

    lot_id = fields.Many2one('stock.lot')
    wo_date = fields.Date(string="W.O Date")
    product_id = fields.Many2one('product.product', string="Item")

    black_spot = fields.Float(string="Black Spot")
    cut_pcs = fields.Float(string="Cut PCS")
    short_qty = fields.Float(string="Short Quantity")

    wo_qty = fields.Float(string="W.O Quantity")
    production_qty = fields.Float(string="Production Quantity")
    dispatch_qty = fields.Float(string="Dispatch Quantity")

    month = fields.Char(string="Month")


    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'batch_closing_report')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW batch_closing_report AS (
                SELECT
                    row_number() OVER() AS id,

                    lot.id AS lot_id,
                    mo.date_start::date AS wo_date,
                    pp.id AS product_id,

                    TO_CHAR(mo.date_start, 'YYYY-MM') AS month,

                    COALESCE(SUM(rs.scrap_qty), 0) AS black_spot,

                    0.0 AS cut_pcs,
                    0.0 AS short_qty,

                    mo.product_qty AS wo_qty,

                    COALESCE(SUM(sml.quantity), 0) AS production_qty,

                    COALESCE(SUM(
                        CASE 
                            WHEN sp.state = 'done'
                            THEN sml2.quantity
                            ELSE 0
                        END
                    ), 0) AS dispatch_qty

                FROM mrp_production mo

                /* Ensure product exists */
                INNER JOIN product_product pp
                    ON pp.id = mo.product_id

                /* Production Move */
                INNER JOIN stock_move sm
                    ON sm.production_id = mo.id
                    AND sm.state = 'done'

                /* Production Move Lines (must have lot) */
                INNER JOIN stock_move_line sml
                    ON sml.move_id = sm.id
                    AND sml.lot_id IS NOT NULL

                /* Ensure lot exists */
                INNER JOIN stock_lot lot
                    ON lot.id = sml.lot_id

                /* Dispatch Moves */
                LEFT JOIN stock_move sm2
                    ON sm2.product_id = pp.id
                    AND sm2.state = 'done'

                LEFT JOIN stock_move_line sml2
                    ON sml2.move_id = sm2.id
                    AND sml2.lot_id = lot.id

                LEFT JOIN stock_picking sp
                    ON sp.id = sm2.picking_id

                LEFT JOIN stock_scrap rs
                    ON rs.lot_id = lot.id

                WHERE mo.state = 'done'

                GROUP BY
                    lot.id,
                    mo.date_start,
                    pp.id,
                    mo.product_qty
            )
        """)

