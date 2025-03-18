from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class WooCommerceSyncWizard(models.TransientModel):
    _name = 'woocommerce.sync.wizard'
    _description = 'WooCommerce Synchronization Wizard'

    sync_products = fields.Boolean(string='Sync Products', default=True)
    sync_categories = fields.Boolean(string='Sync Categories', default=True)
    sync_attributes = fields.Boolean(string='Sync Attributes', default=True)
    direction = fields.Selection([
        ('import', 'Import from WooCommerce'),
        ('export', 'Export to WooCommerce'),
        ('both', 'Bidirectional')
    ], string='Sync Direction', default='import')

    def action_sync(self):
        woo_config = self.env['woocommerce.config'].get_config()
        if not woo_config:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Sync Failed',
                    'message': 'WooCommerce configuration not found',
                    'sticky': False,
                    'type': 'danger',
                }
            }

        if self.sync_categories and self.direction in ['import', 'both']:
            self.env['woocommerce.category'].sync_categories_from_woocommerce()

        if self.sync_attributes and self.direction in ['import', 'both']:
            self.env['woocommerce.attribute'].sync_attributes_from_woocommerce()

        if self.sync_products and self.direction in ['import', 'both']:
            self.env['woocommerce.product'].sync_from_woocommerce()

        if self.direction in ['export', 'both']:
            if self.sync_products:
                products = self.env['woocommerce.product'].search([])
                for product in products:
                    product.sync_to_woocommerce()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Sync Complete',
                'message': 'WooCommerce synchronization completed',
                'sticky': False,
                'type': 'success',
            }
        }