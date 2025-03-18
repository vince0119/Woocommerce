from odoo import models, fields, api


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    woo_attribute_ids = fields.One2many('woocommerce.attribute', 'odoo_attribute_id', string='WooCommerce Attributes')
