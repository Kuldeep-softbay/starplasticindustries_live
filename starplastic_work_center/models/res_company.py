from odoo import models, fields

class ResCompany(models.Model):
    _inherit = 'res.company'

    work_order_footer_image = fields.Binary(string="W.O Footer")
    # work_order_header_format_no = fields.Text(string="W.O Header Format No")
    # work_order_header_effective_date = fields.Date(string="W.O Header Effective Date")
    # work_order_header_review_date = fields.Date(string="W.O Header Review Date")
    production_memo_header_image = fields.Binary(string="Production Memo Header")
    production_memo_footer_image = fields.Binary(string="Production Memo Footer")
    machine_status_memo_header_image = fields.Binary(string="Machine Status Memo Header")
    machine_status_memo_footer_image = fields.Binary(string="Machine Status Memo Footer")
    delayed_production_report_header_image = fields.Binary(string="Delayed Production Report Header")
    delayed_production_report_footer_image = fields.Binary(string="Delayed Production Report Footer")
    rm_stock_book_report_header_image = fields.Binary(string="RM Stock Book Report Header")
    rm_stock_book_report_footer_image = fields.Binary(string="RM Stock Book Report Footer")
    rm_grade_report_header_image = fields.Binary(string="RM Grade Report Header")
    rm_grade_report_footer_image = fields.Binary(string="RM Grade Report Footer")
    rm_stock_sheet_report_header_image = fields.Binary(string="FG Stock Sheet Report Header")
    rm_stock_sheet_report_footer_image = fields.Binary(string="FG Stock Sheet Report Footer")
    delay_report_header = fields.Binary(string="Delay Report Header")
    production_completion_header = fields.Binary(
            string="Production Completion Memo Header"
        )
    production_delay_header = fields.Binary(string="Production Delay Header")