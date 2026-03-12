from odoo import http
from odoo.http import request
from datetime import datetime


class PowerMatrixController(http.Controller):

    @http.route('/power/matrix/data', type='json', auth='user')
    def get_power_matrix_data(self):

        Workcenter = request.env['mrp.workcenter']
        Workorder = request.env['mrp.workorder']
        Consumption = request.env['mrp.power.consumption']

        workcenters = Workcenter.search([], order="id")
        consumptions = Consumption.search([], order='consumption_date')

        wc_names = workcenters.mapped('name')

        rows = []

        for rec in consumptions:

            machine_minutes_list = []
            total_ideal = 0

            for wc in workcenters:

                # Get workorders of same date & workcenter
                workorders = Workorder.search([
                    ('workcenter_id', '=', wc.id),
                    ('date_finished', '!=', False),
                ])

                minutes = 0

                for wo in workorders:
                    if wo.date_finished.date() == rec.consumption_date:
                        minutes += wo.duration or 0

                machine_minutes_list.append(minutes)

                # Ideal calculation (minutes / 60 * max_power)
                ideal = (minutes / 60.0) * (wc.max_power or 0)
                total_ideal += ideal

            actual = rec.meter_reading or 0
            difference = actual - total_ideal

            row = {
                "date": rec.consumption_date.strftime('%d/%m/%Y') if rec.consumption_date else "",
                "machines": machine_minutes_list,
                "load1": rec.additional_load1 or 0,
                "remark1": rec.remark_load1 or "",
                "load2": rec.additional_load2 or 0,
                "remark2": rec.remark_load2 or "",
                "ideal": total_ideal or 0,
                "actual": actual,
                "meter": actual,
                "difference": difference,
            }

            rows.append(row)

        return {
            "rows": rows,
            "workcenters": wc_names,
        }