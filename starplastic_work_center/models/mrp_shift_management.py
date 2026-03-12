from odoo import api, fields, models

class WorkCenterShiftSlot(models.Model):
    _name = 'work.center.shift.slot'
    _description = 'Work Center Shift Slot'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id'


    shift_id = fields.Many2one('work.center.shift', string='Shift', required=True, ondelete='cascade')
    name = fields.Char('Slot', required=True, help='E.g., 08-09')
    sequence = fields.Integer('Sequence', default=10)
    start_time = fields.Float('Start (h)', help='Optional; decimal hours 8.0 = 08:00')
    end_time = fields.Float('End (h)', help='Optional; decimal hours 9.0 = 09:00')