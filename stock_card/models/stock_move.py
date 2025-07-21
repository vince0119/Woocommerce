from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    in_out_amt = fields.Float(string='Amount Total', default=0.0)
    in_out_unit_price = fields.Float(string='Unit Price', default=0.0)
    quant_in_out = fields.Float(string='Quantity', default=0.0)