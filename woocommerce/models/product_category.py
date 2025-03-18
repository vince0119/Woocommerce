from odoo import models, fields, api


class ProductCategory(models.Model):
    _inherit = 'product.category'

    woo_category_ids = fields.One2many('woocommerce.category', 'odoo_category_id', string='WooCommerce Categories')