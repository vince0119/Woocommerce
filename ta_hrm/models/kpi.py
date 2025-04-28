from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Kpi(models.Model):
    _name = 'hr.kpi'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='KPI Name', required=True)
    target = fields.Float(string='Target')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    bonus = fields.Float(string='Bonus %')
    bonus_amount = fields.Monetary(string='Bonus Amount', currency_field='company_currency_id', compute='_compute_bonus_amount', store=True)
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
    bonus_payslip_line_details = fields.Text(string='Bonus Payslip Line Details', compute='_compute_bonus_payslip_line_details')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('canceled', 'Canceled')
    ], string='Status', default='draft')

    bonus_type = fields.Selection([
        ('sales_amount', 'Sales Amount Bonus'),
        ('brand', 'Brand Bonus')
    ], string='Bonus Type', default='sales_amount', required=True)
    product_id = fields.Many2one('product.product', string='Product')
    brand_bonus = fields.Float(string='Brand Bonus (%)')
    brand_total_amount = fields.Monetary(string='Brand Total Amount', currency_field='company_currency_id')
    brand_bonus_amount = fields.Monetary(string='Brand Bonus Amount', currency_field='company_currency_id')

    @api.depends('target', 'bonus', 'so_total_amount')
    def _compute_bonus_amount(self):
        for record in self:
            if record.target and record.bonus:
                achievement_percentage = (record.so_total_amount / record.target) * 100 if record.target else 0
                record.bonus_amount = (
                        record.so_total_amount * record.bonus / 100) if achievement_percentage >= 100 else 0
            else:
                record.bonus_amount = 0

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
            record.so_total_amount = 0
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

    def create_bonus_payslip_line(self):
        if not self.employee_id:
            raise UserError(_("Please select an employee first."))

        if not self.target or not self.bonus:
            raise UserError(_("Please set target and bonus percentage."))

        try:
            # Find or create a specific salary rule for KPI bonus
            salary_rule = self.env['hr.salary.rule'].search([
                ('code', '=', 'KPI_BONUS_RULE')
            ], limit=1)

            if not salary_rule:
                struct = self.env['hr.payroll.structure'].search([('name', '=', 'Regular Pay')], limit=1)
                category = self.env['hr.salary.rule.category'].search([('code', '=', 'ALW')], limit=1)

                # Create the salary rule if it doesn't exist
                salary_rule = self.env['hr.salary.rule'].create({
                    'name': 'KPI_BONUS_RULE',
                    'code': 'KPI_BONUS_RULE',
                    'category_id': category.id,
                    'sequence': 100,
                    'struct_id': struct.id,
                    'condition_select': 'none',
                    'amount_select': 'fix',
                    'amount_fix': 0.0,
                })

            # Find the most recent draft or confirmed payslip for the employee
            payslip = self.env['hr.payslip'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', 'in', ['draft', 'verify'])
            ], order='date_to desc', limit=1)

            if not payslip:
                raise UserError(_("No draft payslip found for the employee. Please create a payslip first."))

            # Create bonus payslip line
            bonus_line = self.env['hr.payslip.line'].create({
                'slip_id': payslip.id,
                'name': f'KPI Bonus - {self.name}',
                'code': 'KPI_BONUS',
                'salary_rule_id': salary_rule.id,
                'category_id': self.env.ref('hr_payroll.COMP').id,
                'sequence': 100,
                'amount': self.bonus_amount,
                'total': self.bonus_amount,
                'contract_id': payslip.contract_id.id
            })

            # Link bonus line to KPI record
            self.bonus_payslip_line_id = bonus_line

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': _('Bonus of %s created successfully!') % self.bonus_amount,
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_("Error creating bonus payslip line: %s") % str(e))


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
