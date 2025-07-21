from odoo import models, fields, api


class StockCardLine(models.Model):
    _name = 'stock.card.line'

    active = fields.Boolean(string='Active', default=True)
    category_id = fields.Many2one('product.category', string='Category')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    location_id = fields.Many2one('stock.location', string='Location')
    name = fields.Char(string='Name')
    notes = fields.Text(string='Notes')
    product_id = fields.Many2one('product.product', string='Product')
    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    qty_end = fields.Float(string='Qty End')
    qty_in = fields.Float(string='Qty In')
    qty_out = fields.Float(string='Qty Out')
    qty_start = fields.Float(string='Qty Start')
    qty_variation = fields.Float(string='Qty Variation')
    sequence = fields.Integer(string='Sequence', default=1)
    standard_cost = fields.Float(string='Standard Cost')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
    ], string='State', default='draft')
    stock_card_id = fields.Many2one('stock.card', string='Stock Card')
    uom_id = fields.Many2one('uom.uom', string='UoM')
    val_end = fields.Float(string='Val End')
    val_in = fields.Float(string='Val In')
    val_out = fields.Float(string='Val Out')
    val_start = fields.Float(string='Val Start')
    val_variation = fields.Float(string='Val Variation')