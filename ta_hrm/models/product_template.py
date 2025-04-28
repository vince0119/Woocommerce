from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    manage_brand_id = fields.Many2one('manage.brand', string='Brand')

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        if 'manage_brand_id' in vals:
            for product in self.product_variant_ids:
                product.manage_brand_id = vals['manage_brand_id']
        return res

class ProductProduct(models.Model):
    _inherit = 'product.product'

    manage_brand_id = fields.Many2one('manage.brand', string='Brand',
        related='product_tmpl_id.manage_brand_id', store=True)

class ManageBrand(models.Model):
    _name = 'manage.brand'

    name = fields.Char('Brand')