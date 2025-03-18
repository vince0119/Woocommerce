from odoo import models, fields, api
import requests
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


class WooCommerceAttribute(models.Model):
    _name = 'woocommerce.attribute'
    _description = 'WooCommerce Attribute'

    name = fields.Char(string='Name', required=True)
    woo_id = fields.Integer(string='WooCommerce ID')
    slug = fields.Char(string='Slug')
    type = fields.Selection([
        ('select', 'Select'),
        ('text', 'Text'),
        ('color', 'Color'),
        ('button', 'Button')
    ], string='Type', default='select')
    order_by = fields.Selection([
        ('menu_order', 'Custom ordering'),
        ('name', 'Name'),
        ('name_num', 'Name (numeric)'),
        ('id', 'Term ID')
    ], string='Order by', default='menu_order')
    has_archives = fields.Boolean(string='Has Archives')
    odoo_attribute_id = fields.Many2one('product.attribute', string='Odoo Attribute')
    value_ids = fields.One2many('woocommerce.attribute.value', 'attribute_id', string='Values')

    @api.model
    def sync_attributes_from_woocommerce(self):
        """Synchronize attributes from WooCommerce to Odoo"""
        woo_config = self.env['woocommerce.config'].get_config()
        if not woo_config:
            _logger.error('WooCommerce configuration not found')
            return False

        # Setup logging
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'woo_attribute_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)

        _logger.info("Starting WooCommerce attribute synchronization")

        success_count = 0
        fail_count = 0

        try:
            url = f"{woo_config.url}/wp-json/wc/v3/products/attributes"
            auth = (woo_config.consumer_key, woo_config.consumer_secret)

            response = requests.get(url, auth=auth)

            if response.status_code != 200:
                _logger.error(f"Error fetching attributes: {response.status_code}")
                _logger.error(response.text)
                return False

            attributes = response.json()

            for attribute_data in attributes:
                try:
                    woo_attribute = self.search([('woo_id', '=', attribute_data['id'])])

                    vals = {
                        'name': attribute_data['name'],
                        'woo_id': attribute_data['id'],
                        'slug': attribute_data.get('slug', ''),
                        'type': attribute_data.get('type', 'select'),
                        'order_by': attribute_data.get('order_by', 'menu_order'),
                        'has_archives': attribute_data.get('has_archives', False),
                    }

                    if not woo_attribute:
                        woo_attribute = self.create(vals)
                        _logger.info(f"Created attribute: {attribute_data['name']} (ID: {attribute_data['id']})")
                    else:
                        woo_attribute.write(vals)
                        _logger.info(f"Updated attribute: {attribute_data['name']} (ID: {attribute_data['id']})")

                    # Create corresponding Odoo attribute if it doesn't exist
                    odoo_attribute = self.env['product.attribute'].search([('name', '=', attribute_data['name'])],
                                                                          limit=1)
                    if not odoo_attribute:
                        odoo_attribute = self.env['product.attribute'].create({
                            'name': attribute_data['name'],
                            'create_variant': 'always',
                        })
                        _logger.info(f"Created Odoo attribute: {attribute_data['name']}")

                    # Link WooCommerce attribute to Odoo attribute
                    woo_attribute.write({'odoo_attribute_id': odoo_attribute.id})

                    # Sync attribute values
                    self.sync_attribute_values(woo_attribute, woo_config)

                    success_count += 1
                except Exception as e:
                    _logger.error(
                        f"Error creating/updating attribute {attribute_data.get('name', 'Unknown')}: {str(e)}")
                    fail_count += 1

            _logger.info(f"Attribute synchronization completed. Success: {success_count}, Failed: {fail_count}")
            _logger.removeHandler(file_handler)
            file_handler.close()
            return True

        except Exception as e:
            _logger.error(f"Error syncing attributes: {str(e)}")
            _logger.removeHandler(file_handler)
            file_handler.close()
            return False

    def sync_attribute_values(self, woo_attribute, woo_config):
        """Synchronize attribute values for a specific attribute"""
        try:
            url = f"{woo_config.url}/wp-json/wc/v3/products/attributes/{woo_attribute.woo_id}/terms"
            auth = (woo_config.consumer_key, woo_config.consumer_secret)

            response = requests.get(url, auth=auth)

            if response.status_code != 200:
                _logger.error(f"Error fetching attribute values: {response.status_code}")
                _logger.error(response.text)
                return False

            values = response.json()

            for value_data in values:
                woo_value = self.env['woocommerce.attribute.value'].search([
                    ('woo_id', '=', value_data['id']),
                    ('attribute_id', '=', woo_attribute.id)
                ])

                vals = {
                    'name': value_data['name'],
                    'woo_id': value_data['id'],
                    'slug': value_data.get('slug', ''),
                    'attribute_id': woo_attribute.id,
                }

                if not woo_value:
                    woo_value = self.env['woocommerce.attribute.value'].create(vals)
                    _logger.info(f"Created attribute value: {value_data['name']} (ID: {value_data['id']})")
                else:
                    woo_value.write(vals)
                    _logger.info(f"Updated attribute value: {value_data['name']} (ID: {value_data['id']})")

                # Create corresponding Odoo attribute value if it doesn't exist
                if woo_attribute.odoo_attribute_id:
                    odoo_value = self.env['product.attribute.value'].search([
                        ('name', '=', value_data['name']),
                        ('attribute_id', '=', woo_attribute.odoo_attribute_id.id)
                    ], limit=1)

                    if not odoo_value:
                        odoo_value = self.env['product.attribute.value'].create({
                            'name': value_data['name'],
                            'attribute_id': woo_attribute.odoo_attribute_id.id,
                        })
                        _logger.info(f"Created Odoo attribute value: {value_data['name']}")

                    # Link WooCommerce value to Odoo value
                    woo_value.write({'odoo_value_id': odoo_value.id})

            return True

        except Exception as e:
            _logger.error(f"Error syncing attribute values for {woo_attribute.name}: {str(e)}")
            return False


class WooCommerceAttributeValue(models.Model):
    _name = 'woocommerce.attribute.value'
    _description = 'WooCommerce Attribute Value'

    name = fields.Char(string='Name', required=True)
    woo_id = fields.Integer(string='WooCommerce ID')
    slug = fields.Char(string='Slug')
    attribute_id = fields.Many2one('woocommerce.attribute', string='Attribute', ondelete='cascade')
    odoo_value_id = fields.Many2one('product.attribute.value', string='Odoo Value')