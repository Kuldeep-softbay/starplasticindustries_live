from odoo import api, fields, models

class JobPartyWork(models.Model):
    _name = 'job.party.work'
    _description = 'Job Party Work'
    _rec_name = 'name'

    name = fields.Char('Job Party Name', required=True)
    work_type = fields.Selection([
        ('inward', 'Inward'),
        ('outword', 'Outword')
    ], string='Type')
    remark = fields.Text('Remark')

    party_ids = fields.One2many(
        'stock.picking',
        'party_id',
        string='Job Party Pickings'
    )
