from odoo import models, fields, tools


class MrpMachineEfficiencySummary(models.Model):
    _name = "mrp.machine.efficiency.summary"
    _description = "Machine Efficiency Summary"
    _auto = False

    machine_id = fields.Many2one("mrp.workcenter", string="Machine", readonly=True)

    no_machine_mould_change = fields.Float(readonly=True)
    mould_change_problem = fields.Float(readonly=True)
    water_problem = fields.Float(readonly=True)
    interior_quality_problem = fields.Float(readonly=True)
    no_raw_material = fields.Float(readonly=True)
    no_operator = fields.Float(readonly=True)
    no_power = fields.Float(readonly=True)
    other_problem = fields.Float(readonly=True)
    mould_change = fields.Float(readonly=True)
    barrel_clean = fields.Float(readonly=True)
    hand_processing_problem = fields.Float(readonly=True)
    insert_change = fields.Float(readonly=True)
    mould_service = fields.Float(readonly=True)
    machine_service = fields.Float(readonly=True)
    rm = fields.Float(readonly=True)
    mould_production_setting = fields.Float(readonly=True)
    no_production_plan = fields.Float(readonly=True)

    total_downtime = fields.Float(readonly=True)
    production_minutes = fields.Float(readonly=True)
    working_minutes = fields.Float(readonly=True)
    efficiency = fields.Float(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE VIEW mrp_machine_efficiency_summary AS (
                SELECT
                    row_number() OVER() AS id,
                    wc.id AS machine_id,

                    SUM(CASE WHEN dt.description = 'NO MACHINE MOULD CHANGE'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS no_machine_mould_change,

                    SUM(CASE WHEN dt.description = 'MOULD CHANGE PROBLEM'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS mould_change_problem,

                    SUM(CASE WHEN dt.description = 'WATER PROBLEM'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS water_problem,

                    SUM(CASE WHEN dt.description = 'INTERIOR QUALITY PROBLEM'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS interior_quality_problem,

                    SUM(CASE WHEN dt.description = 'NO RAW MATERIAL'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS no_raw_material,

                    SUM(CASE WHEN dt.description = 'NO OPERATOR'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS no_operator,

                    SUM(CASE WHEN dt.description = 'NO POWER'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS no_power,

                    SUM(CASE WHEN dt.description = 'OTHER PROBLEM'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS other_problem,

                    SUM(CASE WHEN dt.description = 'MOULD CHANGE'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS mould_change,

                    SUM(CASE WHEN dt.description = 'BARREL CLEAN'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS barrel_clean,

                    SUM(CASE WHEN dt.description = 'HAND PROCESSING PROBLEM'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS hand_processing_problem,

                    SUM(CASE WHEN dt.description = 'INSERT CHANGE'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS insert_change,

                    SUM(CASE WHEN dt.description = 'MOULD SERVICE'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS mould_service,

                    SUM(CASE WHEN dt.description = 'MACHINE SERVICE'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS machine_service,

                    SUM(CASE WHEN dt.description = 'RM'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS rm,

                    SUM(CASE WHEN dt.description = 'MOULD PRODUCTION SETTING'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS mould_production_setting,

                    SUM(CASE WHEN dt.description = 'NO PRODUCTION PLAN'
                        THEN EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60 ELSE 0 END) AS no_production_plan,

                    SUM(EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60) AS total_downtime,

                    SUM(wo.duration) AS production_minutes,

                    1440 - SUM(EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60) AS working_minutes,

                    CASE
                        WHEN (1440 - SUM(EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60)) = 0
                        THEN 0
                        ELSE
                            (SUM(wo.duration) /
                            (1440 - SUM(EXTRACT(EPOCH FROM (dt.date_end - dt.date_start))/60))) * 100
                    END AS efficiency

                FROM mrp_workcenter wc
                LEFT JOIN mrp_workcenter_productivity dt
                    ON dt.workcenter_id = wc.id
                LEFT JOIN mrp_workorder wo
                    ON wo.workcenter_id = wc.id AND wo.state = 'done'
                GROUP BY wc.id
            )
        """)
