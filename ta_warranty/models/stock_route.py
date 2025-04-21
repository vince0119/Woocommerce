from odoo import models, fields, api


class StockRoute(models.Model):
    _inherit = 'stock.route'

    type = fields.Selection([
        ('warranty', 'Warranty'),
        ('scrap', 'Scrap'),
        ('return', 'Return'),
        ('delivery', 'Delivery'),
        ('refund', 'Refund')], string="Route Type")


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    warranty_request_id = fields.Many2one('warranty.request', string="Warranty Request")

    def unlink(self):
        warranty_requests = self.mapped('warranty_request_id')
        res = super(StockPicking, self).unlink()

        for warranty in warranty_requests:
            remaining_pickings = self.env['stock.picking'].search_count([
                ('warranty_request_id', '=', warranty.id)
            ])
            if remaining_pickings == 0:
                warranty.write({'state': 'confirmed'})

        return res