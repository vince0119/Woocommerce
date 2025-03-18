from odoo import models, fields, api
import requests
import logging
import os
from datetime import datetime

_logger = logging.getLogger(__name__)


class WooCommerceCategory(models.Model):
    _name = 'woocommerce.category'
    _description = 'WooCommerce Category'

    name = fields.Char(string='Name', required=True)
    woo_id = fields.Integer(string='WooCommerce ID')
    slug = fields.Char(string='Slug')
    parent_id = fields.Many2one('woocommerce.category', string='Parent Category')
    description = fields.Text(string='Description')
    odoo_category_id = fields.Many2one('product.category', string='Odoo Category')

    @api.model
    def sync_categories_from_woocommerce(self):
        """Synchronize categories from WooCommerce to Odoo"""
        woo_config = self.env['woocommerce.config'].get_config()
        if not woo_config:
            _logger.error('WooCommerce configuration not found')
            return False

        # Setup logging
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'woo_category_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)

        _logger.info("Starting WooCommerce category synchronization")

        success_count = 0
        fail_count = 0

        try:
            url = f"{woo_config.url}/wp-json/wc/v3/products/categories"
            auth = (woo_config.consumer_key, woo_config.consumer_secret)
            params = {'per_page': 100}

            response = requests.get(url, params=params, auth=auth)

            if response.status_code != 200:
                _logger.error(f"Error fetching categories: {response.status_code}")
                _logger.error(response.text)
                return False

            categories = response.json()

            # First pass: create all categories without parent relationships
            for category_data in categories:
                try:
                    woo_category = self.search([('woo_id', '=', category_data['id'])])

                    vals = {
                        'name': category_data['name'],
                        'woo_id': category_data['id'],
                        'slug': category_data.get('slug', ''),
                        'description': category_data.get('description', ''),
                    }

                    if not woo_category:
                        woo_category = self.create(vals)
                        _logger.info(f"Created category: {category_data['name']} (ID: {category_data['id']})")
                    else:
                        woo_category.write(vals)
                        _logger.info(f"Updated category: {category_data['name']} (ID: {category_data['id']})")

                    # Create corresponding Odoo category if it doesn't exist
                    odoo_category = self.env['product.category'].search([('name', '=', category_data['name'])], limit=1)
                    if not odoo_category:
                        odoo_category = self.env['product.category'].create({
                            'name': category_data['name'],
                        })
                        _logger.info(f"Created Odoo category: {category_data['name']}")

                    # Link WooCommerce category to Odoo category
                    woo_category.write({'odoo_category_id': odoo_category.id})

                    success_count += 1
                except Exception as e:
                    _logger.error(f"Error creating/updating category {category_data.get('name', 'Unknown')}: {str(e)}")
                    fail_count += 1

            # Second pass: update parent relationships
            for category_data in categories:
                if category_data.get('parent', 0) > 0:
                    try:
                        woo_category = self.search([('woo_id', '=', category_data['id'])])
                        parent_category = self.search([('woo_id', '=', category_data['parent'])])

                        if woo_category and parent_category:
                            woo_category.write({'parent_id': parent_category.id})

                            # Update Odoo category parent as well
                            if woo_category.odoo_category_id and parent_category.odoo_category_id:
                                woo_category.odoo_category_id.write({'parent_id': parent_category.odoo_category_id.id})
                                _logger.info(f"Updated parent relationship for category: {woo_category.name}")
                    except Exception as e:
                        _logger.error(
                            f"Error updating parent for category {category_data.get('name', 'Unknown')}: {str(e)}")

            _logger.info(f"Category synchronization completed. Success: {success_count}, Failed: {fail_count}")
            _logger.removeHandler(file_handler)
            file_handler.close()
            return True

        except Exception as e:
            _logger.error(f"Error syncing categories: {str(e)}")
            _logger.removeHandler(file_handler)
            file_handler.close()
            return False