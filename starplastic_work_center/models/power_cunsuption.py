from odoo import models, fields, api


class PowerConsumptionEntry(models.Model):
    _name = 'mrp.power.consumption'
    _description = 'Power Consumption Entry'
    _order = 'consumption_date desc'

    consumption_date = fields.Date(
        string="Consumption Date",
        required=True,
        default=fields.Date.today
    )

    location_id = fields.Many2one(
        'stock.location',
        string="Location",
        required=True
    )

    meter_reading = fields.Float(
        string="24 Hr KWH Meter Reading"
    )

    additional_load1 = fields.Float(
        string="Additional Load 1"
    )

    remark_load1 = fields.Text(
        string="Remarks for Additional Load 1"
    )

    additional_load2 = fields.Float(
        string="Additional Load 2"
    )

    remark_load2 = fields.Text(
        string="Remarks for Additional Load 2"
    )
