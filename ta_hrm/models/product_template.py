from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    manage_brand_id = fields.Many2one('manage.brand', string='Brand')


class ManageBrand(models.Model):
    _name = 'manage.brand'

    name = fields.Char('Brand')