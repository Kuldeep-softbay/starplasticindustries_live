from odoo import models, api
from collections import defaultdict

class ReportPackingMemo(models.AbstractModel):
    _name = 'report.custom_packing_memo.report_packing_memo'
    _description = 'Packing Memo Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        sale = self.env['sale.order'].browse(docids)
        selections = self.env.context.get('packing_memo_selections')

        if selections:
            details, summary = self._from_wizard(selections)
        else:
            payload = sale.get_packing_memo_payload()
            details = payload['details']
            summary = payload['summary']

        return {
            'doc_ids': docids,
            'doc_model': 'sale.order',
            'docs': sale,
            'details': details,
            'summary': summary,
        }

    def _from_wizard(self, selections):
        details = []
        summary_map = {}

        lots = self.env['stock.lot'].browse(
            [int(x) for x in selections]
        )

        for lot in lots:
            qty = selections[str(lot.id)]
            product = lot.product_id

            details.append({
                # 'batch_number': lot.name,
                'product_display_name': product.display_name,
                'default_code': product.default_code or '',
                'qty': qty,
            })

            key = (product.id, lot.name)
            summary_map[key] = summary_map.get(key, 0.0) + qty

        summary = []
        for (product_id, batch), qty in summary_map.items():
            product = self.env['product.product'].browse(product_id)
            summary.append({
                # 'batch_number': batch,
                'product_display_name': product.display_name,
                'default_code': product.default_code or '',
                'qty': qty,
            })

        return details, summary
