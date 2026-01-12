from odoo import api, fields, models, _
from datetime import datetime, time


class FgWorkOrderReportWizard(models.TransientModel):
    _name = "fg.work.order.report.wizard"
    _description = "FG Work Order Report Wizard"

    from_date = fields.Date(
        string="From Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    to_date = fields.Date(
        string="To Date",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    def action_show_report(self):
        self.ensure_one()
        if self.to_date < self.from_date:
            raise ValueError(_("To Date must be after From Date"))

        # Clear previous lines only for this user
        self.env["fg.work.order.report"].search(
            [("user_id", "=", self.env.user.id)]
        ).unlink()

        from_dt = datetime.combine(self.from_date, time.min)
        to_dt = datetime.combine(self.to_date, time.max)

        Move = self.env["stock.move"]

        # ---------------------------------------------------------
        # 1) Period moves
        # ---------------------------------------------------------
        period_domain = [
            ("state", "=", "done"),
            ("date", ">=", from_dt),
            ("date", "<=", to_dt),
            ("product_id.sale_ok", "=", True),   # ONLY SALE PRODUCTS
        ]
        period_moves = Move.search(period_domain)

        production_by_product = {}
        dispatch_by_product = {}

        for move in period_moves:
            product = move.product_id
            qty = move.product_uom_qty

            src_usage = move.location_id.usage
            dest_usage = move.location_dest_id.usage
            picking_code = move.picking_type_id.code or ""

            is_production = (
                picking_code in ("mrp_operation", "mrp", "manufacturing")
                or (src_usage == "production" and dest_usage == "internal")
            )

            is_dispatch = (
                picking_code == "outgoing"
                or (src_usage == "internal" and dest_usage in ("customer", "inventory"))
            )

            if is_production:
                production_by_product[product.id] = production_by_product.get(product.id, 0.0) + qty
            elif is_dispatch:
                dispatch_by_product[product.id] = dispatch_by_product.get(product.id, 0.0) + qty

        product_ids = set(production_by_product.keys()) | set(dispatch_by_product.keys())

        # ---------------------------------------------------------
        # 2) Opening stock (only sale products)
        # ---------------------------------------------------------
        opening_by_product = {}
        Product = self.env["product.product"]

        if product_ids:
            products = Product.search([
                ("id", "in", list(product_ids)),
                ("sale_ok", "=", True)
            ])

            products_at_date = products.with_context(
                to_date=fields.Datetime.to_string(from_dt),
                company_id=self.env.company.id,
            )
            products_at_date._compute_quantities()

            for prod in products_at_date:
                opening_by_product[prod.id] = prod.qty_available or 0.0

        # ---------------------------------------------------------
        # 3) Create report lines (only sale products)
        # ---------------------------------------------------------
        all_products = Product.search([
            ("id", "in", list(product_ids)),
            ("sale_ok", "=", True)
        ])

        for product in all_products:
            opening = opening_by_product.get(product.id, 0.0)
            prod = production_by_product.get(product.id, 0.0)
            disp = dispatch_by_product.get(product.id, 0.0)

            self.env["fg.work.order.report"].create({
                "user_id": self.env.user.id,
                "product_id": product.id,
                "price": product.lst_price,
                "product_weight_sale": product.weight or 0.0,
                "opening_qty": opening,
                "production_qty": prod,
                "dispatch_qty": disp,
                "from_date": self.from_date,
                "to_date": self.to_date,
            })

        return {
            "type": "ir.actions.act_window",
            "name": _("FG Work Order Report"),
            "res_model": "fg.work.order.report",
            "view_mode": "list,pivot",
            "target": "current",
            "domain": [("user_id", "=", self.env.user.id)],
            "context": {"search_default_group_by_product": 1},
        }
