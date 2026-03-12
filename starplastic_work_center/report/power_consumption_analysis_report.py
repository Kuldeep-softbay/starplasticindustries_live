from odoo import models, fields, tools

class PowerConsumptionAnalysis(models.Model):
    _name = 'mrp.power.consumption.analysis'
    _description = 'Power Consumption Analysis'
    _auto = False

    consumption_date = fields.Date()
    location_id = fields.Many2one('stock.location')
    workcenter_id = fields.Many2one('mrp.workcenter')

    machine_minutes = fields.Float()
    meter_reading = fields.Float(string="Meter Rd Kwh")
    additional_load1 = fields.Float(string="Load 1 Unit")
    remark_load1 = fields.Text(string="Remarks Load 1")
    additional_load2 = fields.Float(string="Load 2 Unit")
    remark_load2 = fields.Text(string="Remarks Load 2")
    difference = fields.Float(string="Difference")
    ideal_meter_reading = fields.Float(string="Ideal Unit Used")
    actual_power_consumption = fields.Float(string="Actual Unit Used")

    def init(self):
        tools.drop_view_if_exists(self._cr, 'mrp_power_consumption_analysis')

        self._cr.execute("""
            CREATE OR REPLACE VIEW mrp_power_consumption_analysis AS (
                SELECT
                    row_number() OVER() AS id,

                    pc.consumption_date,
                    pc.location_id,

                    wc.id as workcenter_id,

                    -- Machine Minutes per Workcenter
                    COALESCE(SUM(wo.duration), 0) as machine_minutes,

                    -- Global Values (not per machine)
                    MAX(pc.additional_load1) as additional_load1,
                    MAX(pc.additional_load2) as additional_load2,
                    MAX(pc.meter_reading) as meter_reading,
                    MAX(pc.meter_reading) as actual_power_consumption,

                    -- Ideal Power (per machine)
                    (
                        (COALESCE(SUM(wo.duration), 0) / 60.0)
                        * COALESCE(wc.max_power, 0)
                    ) as ideal_meter_reading,

                    (
                        MAX(pc.meter_reading)
                        -
                        (
                            (COALESCE(SUM(wo.duration), 0) / 60.0)
                            * COALESCE(wc.max_power, 0)
                        )
                    ) as difference

                FROM mrp_power_consumption pc

                CROSS JOIN mrp_workcenter wc

                LEFT JOIN mrp_workorder wo
                    ON wo.workcenter_id = wc.id
                    AND wo.date_finished::date = pc.consumption_date

                GROUP BY
                    pc.consumption_date,
                    pc.location_id,
                    wc.id,
                    wc.max_power
            )
        """)
