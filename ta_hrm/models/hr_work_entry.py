from odoo import models, fields, api, _

class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    cont_bonus = fields.Char(string='Cont Bonus')
    is_department_manager = fields.Boolean(string="Is Department Manager", compute='_compute_is_department_manager')
    can_edit_cont_bonus = fields.Boolean(string="Can Edit Cont Bonus", compute='_compute_can_edit_cont_bonus')

    @api.depends('employee_id')
    def _compute_is_department_manager(self):
        for work_entry in self:
            user_employee = self.env.user.employee_id
            work_entry.is_department_manager = (
                    user_employee
                    and work_entry.employee_id.department_id
                    and work_entry.employee_id.department_id.manager_id == user_employee
            )

    @api.depends('employee_id')
    def _compute_can_edit_cont_bonus(self):
        for work_entry in self:
            work_entry.can_edit_cont_bonus = work_entry.is_department_manager

    def write(self, vals):
        if 'cont_bonus' in vals and not self.env.context.get('no_sync'):
            for work_entry in self:
                if work_entry.is_department_manager:
                    department = work_entry.employee_id.department_id
                    if department:
                        work_entries_to_update = self.env['hr.work.entry'].search([
                            ('employee_id.department_id', '=', department.id),
                            ('id', '!=', work_entry.id),
                            ('date_start', '=', work_entry.date_start),
                            ('date_stop', '=', work_entry.date_stop),
                        ])
                        work_entries_to_update.sudo().with_context(no_sync=True).write(
                            {'cont_bonus': vals['cont_bonus']})
        return super(HrWorkEntry, self).write(vals)
