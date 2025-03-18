from odoo import models, fields, api
import requests
import logging

_logger = logging.getLogger(__name__)


class WooCommerceConfig(models.Model):
    _name = 'woocommerce.config'
    _description = 'WooCommerce Configuration'

    name = fields.Char(string='Name', required=True, default='WooCommerce Config')
    url = fields.Char(string='URL', required=True, help='WooCommerce store URL')
    consumer_key = fields.Char(string='Consumer Key', required=True)
    consumer_secret = fields.Char(string='Consumer Secret', required=True)
    is_active = fields.Boolean(string='Active', default=True)

    @api.model
    def get_config(self):
        """Lấy cấu hình WooCommerce đang hoạt động"""
        config = self.search([('is_active', '=', True)], limit=1)
        return config

    def test_connection(self):
        """Kiểm tra kết nối tới WooCommerce API"""
        self.ensure_one()
        try:
            url = f"{self.url}/wp-json/wc/v3/products"
            auth = (self.consumer_key, self.consumer_secret)
            params = {'per_page': 1}

            response = requests.get(url, params=params, auth=auth)

            if response.status_code == 200:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Successful',
                        'message': 'Successfully connected to WooCommerce API',
                        'sticky': False,
                        'type': 'success',
                    }
                }
            else:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Connection Failed',
                        'message': f"Error: {response.status_code} - {response.text}",
                        'sticky': False,
                        'type': 'danger',
                    }
                }

        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Connection Failed',
                    'message': f"Error: {str(e)}",
                    'sticky': False,
                    'type': 'danger',
                }
            }