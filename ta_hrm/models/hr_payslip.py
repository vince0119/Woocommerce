from datetime import timedelta
from collections import defaultdict
from odoo import models, fields, api

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def is_porter_manager(self):
        employee = self.employee_id
        department = employee.department_id
        return bool(department and department.name == "Porter" and department.manager_id == employee)

    def compute_kpi_bonus(self):
        kpi_total_amount = 0
        employee = self.employee_id
        department = employee.department_id
        if not department:
            return 0

        date_employee_work = defaultdict(set)
        date_cont_bonus = {}

        # Lấy tất cả work entries của nhân viên trong khoảng thời gian payslip
        work_entries = self.env['hr.work.entry'].search([
            ('date_start', '>=', self.date_from),
            ('date_stop', '<=', self.date_to),
            ('employee_id.department_id', '=', department.id),
        ])

        for entry in work_entries:
            work_date = entry.date_start.date()  # lấy ngày
            if entry.cont_bonus:
                if work_date not in date_cont_bonus:
                    try:
                        date_cont_bonus[work_date] = int(entry.cont_bonus)
                    except ValueError:
                        date_cont_bonus[work_date] = 0
                date_employee_work[work_date].add(entry.employee_id.id)

        # Tính KPI cho employee này
        for work_date, employee_ids in date_employee_work.items():
            if employee.id in employee_ids:
                total_cont_bonus = date_cont_bonus.get(work_date, 0)
                total_money = total_cont_bonus * 3_000_000
                if employee_ids:
                    kpi_per_employee = total_money / len(employee_ids)
                    kpi_total_amount += kpi_per_employee

        return round(kpi_total_amount)