from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    employee_id = fields.Many2one('hr.employee', string='Employee', require=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    commission_amount = fields.Monetary(
        string="Commission",
        currency_field='currency_id',
        compute='_compute_commission_amount',
        store=True
    )

    @api.depends('product_id', 'product_uom_qty', 'order_id.user_id')
    def _compute_commission_amount(self):
        for line in self:
            total_commission = 0.0
            user = line.order_id.user_id
            plans = self.env['sale.commission.plan'].search([('user_ids', 'in', user.id)])
            for plan in plans:
                for target in plan.target_ids:
                    if target.target_mode == 'quantity':
                        total_commission += target.compute_commission(line)
            line.commission_amount = total_commission