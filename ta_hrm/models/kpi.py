from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Kpi(models.Model):
    _name = 'hr.kpi'

    name = fields.Char(string='KPI Name', required=True)
    target = fields.Float(string='Target')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    bonus = fields.Monetary(string='Bonus', currency_field='company_currency_id')
    manage_brand_id = fields.Many2one('manage.brand', string='Brand')
    company_currency_id = fields.Many2one('res.currency', string='Company Currency',
                                          related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    so_total_amount = fields.Monetary(string='Total SO Amount',
                                      compute='_compute_employee_so_amount',
                                      currency_field='company_currency_id')
    so_line_ids = fields.One2many('kpi.so.line', 'kpi_id', string='Sales Orders')
    bonus_payslip_line_id = fields.Many2one('hr.payslip.line', string='Bonus Payslip Line')
    bonus_payslip_line_details = fields.Text(string='Bonus Payslip Line Details', compute='_compute_bonus_payslip_line_details', store=False)

    @api.depends('bonus_payslip_line_id')
    def _compute_bonus_payslip_line_details(self):
        for record in self:
            if record.bonus_payslip_line_id:
                record.bonus_payslip_line_details = f"""
                    Payslip Line Details:
                    - Payslip: {record.bonus_payslip_line_id.slip_id.name}
                    - Amount: {record.bonus_payslip_line_id.amount}
                    - Code: {record.bonus_payslip_line_id.code}
                    - Salary Rule: {record.bonus_payslip_line_id.salary_rule_id.name}
                                    """.strip()
            else:
                record.bonus_payslip_line_details = "No bonus payslip line created"

    @api.depends('employee_id')
    def _compute_employee_so_amount(self):
        for record in self:
            if record.employee_id:
                # Find sales orders for the specific employee
                sales_orders = self.env['sale.order'].search([
                    ('employee_id', '=', record.employee_id.id),
                    ('state', 'in', ['sale', 'done'])
                ])
                record.so_total_amount = sum(sales_orders.mapped('amount_total'))

                # Create SO line records for display
                record.so_line_ids = [(5, 0, 0)]  # Clear existing lines
                so_lines = []
                for so in sales_orders:
                    so_lines.append((0, 0, {
                        'sale_order_id': so.id,
                        'amount_total': so.amount_total,
                        'date_order': so.date_order,
                        'name': so.name
                    }))
                record.so_line_ids = so_lines

                # self._create_bonus_payslip_line(record)

    def create_bonus_payslip_line(self):
        """
        Manual action to create bonus payslip line
        """
        self.ensure_one()

        # Validate prerequisites
        if not self.employee_id:
            raise UserError("Please select an employee first.")

        if not self.target or not self.bonus:
            raise UserError("Please set target and bonus percentage.")

        try:
            # Find or create a specific salary rule for KPI bonus
            salary_rule = self.env['hr.salary.rule'].search([
                ('code', '=', 'KPI_BONUS_RULE')
            ], limit=1)

            # Find the most recent draft or confirmed payslip for the employee
            payslip = self.env['hr.payslip'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', 'in', ['draft', 'verify'])
            ], order='date_to desc', limit=1)

            if not payslip:
                raise UserError("No draft payslip found for the employee. Please create a payslip first.")

            # Calculate bonus amount
            bonus_amount = self.target * (self.bonus / 100)

            # Create bonus payslip line
            bonus_line = self.env['hr.payslip.line'].create({
                'slip_id': payslip.id,
                'name': f'KPI Bonus - {self.name}',
                'code': 'KPI_BONUS',
                'salary_rule_id': salary_rule.id,
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'sequence': 100,
                'amount': bonus_amount,
                'total': bonus_amount,
                'contract_id': payslip.contract_id.id
            })

            # Link bonus line to KPI record
            self.bonus_payslip_line_id = bonus_line

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': f'Bonus of {bonus_amount} created successfully!',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(f"Error creating bonus payslip line: {str(e)}")


class KpiSoLine(models.Model):
    _name = 'kpi.so.line'

    kpi_id = fields.Many2one('hr.kpi', string='KPI')
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    name = fields.Char(string='SO Number')

    amount_total = fields.Monetary(
        string='Total Amount',
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='kpi_id.company_currency_id',
        readonly=True
    )
    date_order = fields.Datetime(string='Order Date')