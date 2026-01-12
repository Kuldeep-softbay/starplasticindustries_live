from odoo import models, fields, tools

class SalesMonthlyReport(models.Model):
    _name = "sales.monthly.report"
    _description = "Sales Monthly Stock Report"
    _auto = False
    _rec_name = "product_id"

    product_id = fields.Many2one("product.product", readonly=True)
    price = fields.Float(readonly=True)
    weight = fields.Float(readonly=True)

    opening_stock = fields.Float(readonly=True)
    production_qty = fields.Float(readonly=True)
    dispatch_qty = fields.Float(readonly=True)
    closing_stock = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW sales_monthly_report AS (
                SELECT
                    MIN(sm.id) AS id,
                    sm.product_id,
                    pt.weight AS weight,

                    -- Sale price (take latest / max safely)
                    (
                        SELECT MAX(sol.price_unit)
                        FROM sale_order_line sol
                        JOIN sale_order so ON so.id = sol.order_id
                        WHERE sol.product_id = sm.product_id
                        AND so.state IN ('sale','done')
                    ) AS price,

                    -- Opening Stock
                    SUM(
                        CASE
                            WHEN sm.date < DATE_TRUNC('month', CURRENT_DATE)
                            AND dest.usage = 'internal'
                            THEN sm.product_uom_qty
                            WHEN sm.date < DATE_TRUNC('month', CURRENT_DATE)
                            AND src.usage = 'internal'
                            THEN -sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS opening_stock,

                    -- Production / Incoming
                    SUM(
                        CASE
                            WHEN sm.date >= DATE_TRUNC('month', CURRENT_DATE)
                            AND dest.usage = 'internal'
                            THEN sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS production_qty,

                    -- Dispatch / Sales
                    SUM(
                        CASE
                            WHEN sm.date >= DATE_TRUNC('month', CURRENT_DATE)
                            AND src.usage = 'internal'
                            THEN sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS dispatch_qty,

                    -- Closing Stock
                    SUM(
                        CASE
                            WHEN dest.usage = 'internal'
                            THEN sm.product_uom_qty
                            WHEN src.usage = 'internal'
                            THEN -sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS closing_stock

                FROM stock_move sm
                JOIN stock_location src ON src.id = sm.location_id
                JOIN stock_location dest ON dest.id = sm.location_dest_id
                JOIN product_product pp ON pp.id = sm.product_id
                JOIN product_template pt ON pt.id = pp.product_tmpl_id

                WHERE sm.state = 'done'

                GROUP BY sm.product_id, pt.weight
            )
        """)
