from odoo import fields, models, api

class CommissionSummary(models.Model):
    _name = 'commission.summary'
    _description = 'Commission Summary'

    user_id = fields.Many2one('res.users', string='User')
    plan_id = fields.Many2one('sale.commission.plan', string='Commission')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    target_amount = fields.Float(string='Target')
    achieve = fields.Float(string='Achieved')
    commission = fields.Float(string='Commission')
    target_mode = fields.Selection([
        ('revenue', 'By Revenue'),
        ('quantity', 'By Product Quantity'),
    ], string='Target Mode')

class SaleCommissionPlan(models.Model):
    _inherit = 'sale.commission.plan'

    def action_approve(self):
        res = super(SaleCommissionPlan, self).action_approve()
        self._create_commission_summary()
        return res

    def _create_commission_summary(self):
        """Tạo commission summary khi plan được approved"""
        CommissionSummary = self.env['commission.summary']

        for plan in self:
            plan_users = self.env['sale.commission.plan.user'].search([
                ('plan_id', '=', plan.id)
            ])

            for plan_user in plan_users:
                # Lấy thông tin từ plan_user
                user_id = plan_user.user_id
                date_from = plan_user.date_from
                date_to = plan_user.date_to

                # Xác định target amount dựa theo target_mode
                target = self._calculate_target(plan)

                # Tính toán achieved amount
                achieve = self._calculate_achieved(plan, user_id, date_to)

                # Tính toán commission amount
                commission = self._calculate_commission(plan, achieve, target)

                # Tạo bản ghi commission summary
                CommissionSummary.create({
                    'user_id': user_id.id,
                    'plan_id': plan.id,
                    'date_to': date_to,
                    'date_from': date_from,
                    'target_amount': target,
                    'achieve': achieve,
                    'commission': commission,
                    'target_mode': plan.target_mode,
                })

    def _calculate_target(self, plan):
        plan_target = self.env['sale.commission.plan.target'].search([
            ('plan_id', '=', plan.id),
        ], limit=1)

        if plan.target_mode == 'quantity':
            return plan_target.min_qty
        else:
            return plan_target.amount if plan_target and hasattr(plan_target, 'amount') else 0.0

    def _calculate_achieved(self, plan, user_id, date_to):
        CommissionReport = self.env['sale.commission.report']

        domain = [
            ('user_id', '=', user_id.id),
            ('date_to', '<=', date_to),
        ]

        if plan.target_mode == 'revenue':
            report = CommissionReport.search(domain)
            return sum(report.mapped('target_amount'))
        elif plan.target_mode == 'quantity':
            reports = CommissionReport.search(domain)
            return sum(reports.mapped('product_qty'))

        return 0.0

    def _calculate_commission(self, plan, achieve, target):
        commission_amount = plan.commission_amount if hasattr(plan, 'commission_amount') else 0.0

        if plan.target_mode == 'quantity':
            # Theo yêu cầu của bạn: commission = commission_amount * min_qty
            plan_target = self.env['sale.commission.plan.target'].search([
                ('plan_id', '=', plan.id),
                # Thêm điều kiện nếu có
            ], limit=1)

            if plan_target and plan_target.min_qty > 0 and achieve >= plan_target.min_qty:
                return commission_amount * plan_target.min_qty
        else:  # mode='revenue'
            # Áp dụng logic tính commission cho revenue
            # Ví dụ: Nếu đạt target doanh thu thì được hưởng commission
            if target > 0 and achieve >= target:
                return commission_amount

        return 0.0