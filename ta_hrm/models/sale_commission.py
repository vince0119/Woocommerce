from odoo import api, fields, models


class SaleCommission(models.Model):
    _inherit = 'sale.commission.plan'

    target_mode = fields.Selection([
        ('revenue', 'By Revenue'),
        ('quantity', 'By Product Quantity'),
    ], string="Target Mode", required=True, default='revenue')

class SaleCommissionPlanTarget(models.Model):
    _inherit = "sale.commission.plan.target"

    min_qty = fields.Integer(string="Target Quantity")

    @api.depends('plan_id.target_mode', 'amount', 'min_qty')
    def _compute_commission(self):
        """Override commission calculation based on target_mode."""
        for target in self:
            if target.plan_id.target_mode == 'quantity':
                # For 'thưởng thương hiệu', use min_qty instead of amount
                target.commission = target.min_qty * target.commission_percentage / 100
            else:
                # For 'thưởng doanh số', use default amount
                super(SaleCommissionPlanTarget, target)._compute_commission()