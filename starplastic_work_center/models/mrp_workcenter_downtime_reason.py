from odoo import fields, models

class WcDowntimeReason(models.Model):
    _name = 'wc.downtime.reason'
    _description = 'Downtime Reason'

    name = fields.Char(required=True, string='Reason')


class WcDowntimeSubreason(models.Model):
    _name = 'wc.downtime.subreason'
    _description = 'Downtime Sub Reason'

    name = fields.Char(required=True, string='Sub Reason')
    reason_id = fields.Many2one('wc.downtime.reason', string='Reason', required=True)


class WorkCenterShiftDowntimeSummary(models.Model):
    _name = 'work.center.shift.downtime.summary'
    _description = 'Downtime Summary'
    _order = 'hour_slot, reason_id'

    shift_id = fields.Many2one(
        'work.center.shift',
        string='Shift',
        ondelete='cascade',
        required=True
    )

    hour_slot = fields.Selection(
        selection=lambda self: self.env['work.center.hourly.entry']._selection_hour_slots(),
        string='Hour Slot',
        readonly=True
    )

    reason_id = fields.Many2one(
        'wc.downtime.reason',
        string='Reason',
        readonly=True
    )

    sub_reason_id = fields.Many2one(
        'wc.downtime.subreason',
        string='Sub Reason',
        readonly=True
    )

    total_duration = fields.Float(
        string='Total Duration (min)',
        readonly=True
    )

