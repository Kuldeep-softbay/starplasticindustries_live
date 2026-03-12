from odoo import api, fields, models


class FgWorkOrderReport(models.Model):
    _name = "fg.work.order.report"
    _description = "FG Work Order Report"
    _order = "product_id"

    user_id = fields.Many2one(
        "res.users", string="User", default=lambda self: self.env.user, index=True
    )

    product_id = fields.Many2one("product.product", string="Item", required=True)
    product_template_id = fields.Many2one(
        "product.template",
        string="Product Template",
        related="product_id.product_tmpl_id",
        store=True,
    )

    price = fields.Float("Price", digits="Product Price")
    product_weight_sale = fields.Float("Product Weight for Sale")

    opening_qty = fields.Float("Opening Stock")
    production_qty = fields.Float("Production")
    dispatch_qty = fields.Float("Dispatch")
    closing_qty = fields.Float(
        "Closing Stock",
        compute="_compute_closing_qty",
        store=True,
    )

    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")

    @api.depends("opening_qty", "production_qty", "dispatch_qty")
    def _compute_closing_qty(self):
        for rec in self:
            closing = (rec.opening_qty or 0.0) + (rec.production_qty or 0.0) - (rec.dispatch_qty or 0.0)
            rec.closing_qty = closing if closing > 0.0 else 0.0



class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    stock_move_sms_validation = fields.Boolean(
        string="SMS Validation on Stock Moves",
        config_parameter="custom_report.stock_move_sms_validation",
    )
    # stock_sms_confirmation_template_id = fields.Many2one(
    #     "mail.template",
    #     string="SMS Confirmation Template",
    #     config_parameter="custom_report.stock_sms_confirmation_template_id",
    # )