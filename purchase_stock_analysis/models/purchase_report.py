from odoo import models, fields, tools


class PurchaseMonthlyReport(models.Model):
    _name = 'purchase.monthly.report'
    _description = 'Purchase Monthly Stock Report'
    _auto = False
    _rec_name = 'product_tmpl_id'

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product',
        readonly=True
    )

    opening_stock = fields.Float(readonly=True)
    purchase_qty = fields.Float(readonly=True)
    issue_qty = fields.Float(readonly=True)
    closing_stock = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW purchase_monthly_report AS (
                SELECT
                    row_number() OVER () AS id,
                    MIN(pt.id) AS product_tmpl_id,

                    /* OPENING STOCK (before current month) */
                    SUM(
                        CASE
                            WHEN sm.date < date_trunc('month', CURRENT_DATE)
                            THEN
                                CASE
                                    WHEN dest.usage = 'internal' THEN sm.product_uom_qty
                                    WHEN src.usage = 'internal' THEN -sm.product_uom_qty
                                    ELSE 0
                                END
                            ELSE 0
                        END
                    ) AS opening_stock,

                    /* PURCHASE QTY (current month) */
                    SUM(
                        CASE
                            WHEN src.usage = 'supplier'
                             AND dest.usage = 'internal'
                             AND sm.date >= date_trunc('month', CURRENT_DATE)
                             AND sm.date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
                            THEN sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS purchase_qty,

                    /* ISSUE QTY (current month) */
                    SUM(
                        CASE
                            WHEN src.usage = 'internal'
                             AND dest.usage != 'internal'
                             AND sm.date >= date_trunc('month', CURRENT_DATE)
                             AND sm.date < date_trunc('month', CURRENT_DATE) + INTERVAL '1 month'
                            THEN sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS issue_qty,

                    /* CLOSING STOCK (till date) */
                    SUM(
                        CASE
                            WHEN dest.usage = 'internal' THEN sm.product_uom_qty
                            WHEN src.usage = 'internal' THEN -sm.product_uom_qty
                            ELSE 0
                        END
                    ) AS closing_stock

                FROM stock_move sm
                JOIN product_product pp ON sm.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN stock_location src ON sm.location_id = src.id
                JOIN stock_location dest ON sm.location_dest_id = dest.id

                WHERE sm.state = 'done'
                  AND pt.purchase_ok = TRUE
                  AND pt.active = TRUE

                GROUP BY pt.name
            )
        """)
