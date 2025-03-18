from odoo import models, fields, api
import requests
import json
import logging

_logger = logging.getLogger(__name__)


class WooCommerceProduct(models.Model):
    _name = 'woocommerce.product'
    _description = 'WooCommerce Product'

    name = fields.Char(string='Name', required=True)
    woo_id = fields.Integer(string='WooCommerce ID')
    product_id = fields.Many2one('product.product', string='Odoo Product')
    price = fields.Float(string='Price')
    regular_price = fields.Float(string='Regular Price')
    sale_price = fields.Float(string='Sale Price')
    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('private', 'Private'),
        ('publish', 'Published')
    ], string='Status', default='draft')
    description = fields.Html(string='Description')
    short_description = fields.Html(string='Short Description')
    sku = fields.Char(string='SKU')
    stock_quantity = fields.Integer(string='Stock Quantity')
    categories = fields.Many2many('woocommerce.category', string='Categories')
    images = fields.One2many('woocommerce.product.image', 'product_id', string='Images')
    permalink = fields.Char(string='Permalink')
    date_created = fields.Datetime(string='Date Created')
    date_modified = fields.Datetime(string='Date Modified')

    @api.model
    def sync_from_woocommerce(self):
        """Đồng bộ sản phẩm từ WooCommerce về Odoo"""
        woo_config = self.env['woocommerce.config'].get_config()
        if not woo_config:
            _logger.error('WooCommerce configuration not found')
            return False

        try:
            url = f"{woo_config.url}/wp-json/wc/v3/products"
            auth = (woo_config.consumer_key, woo_config.consumer_secret)
            params = {'per_page': 100}

            response = requests.get(url, params=params, auth=auth)

            if response.status_code != 200:
                _logger.error(f"Error fetching products: {response.status_code}")
                _logger.error(response.text)
                return False

            products = response.json()

            for product_data in products:
                self._create_or_update_product(product_data, woo_config)

            return True

        except Exception as e:
            _logger.error(f"Error syncing products: {str(e)}")
            return False

    def _create_or_update_product(self, product_data, woo_config):
        """Tạo hoặc cập nhật sản phẩm từ dữ liệu WooCommerce"""
        woo_product = self.search([('woo_id', '=', product_data['id'])])

        # Xử lý danh mục
        category_ids = []
        for category in product_data.get('categories', []):
            woo_category = self.env['woocommerce.category'].search([('woo_id', '=', category['id'])])
            if not woo_category:
                woo_category = self.env['woocommerce.category'].create({
                    'name': category['name'],
                    'woo_id': category['id'],
                    'slug': category.get('slug', '')
                })
            category_ids.append(woo_category.id)

        vals = {
            'name': product_data['name'],
            'woo_id': product_data['id'],
            'price': float(product_data.get('price', 0)),
            'regular_price': float(product_data.get('regular_price', 0)) if product_data.get('regular_price') else 0,
            'sale_price': float(product_data.get('sale_price', 0)) if product_data.get('sale_price') else 0,
            'status': product_data['status'],
            'description': product_data.get('description', ''),
            'short_description': product_data.get('short_description', ''),
            'sku': product_data.get('sku', ''),
            'stock_quantity': product_data.get('stock_quantity', 0),
            'permalink': product_data.get('permalink', ''),
            'date_created': product_data.get('date_created', False),
            'date_modified': product_data.get('date_modified', False),
        }

        if category_ids:
            vals['categories'] = [(6, 0, category_ids)]

        if not woo_product:
            # Tạo sản phẩm mới
            woo_product = self.create(vals)

            # Tạo sản phẩm Odoo tương ứng
            odoo_product = self.env['product.product'].create({
                'name': product_data['name'],
                'list_price': float(product_data.get('price', 0)),
                'default_code': product_data.get('sku', ''),
                'description': product_data.get('description', ''),
                'description_sale': product_data.get('short_description', ''),
                'type': 'product',
            })

            woo_product.write({'product_id': odoo_product.id})

            # Xử lý hình ảnh
            for image_data in product_data.get('images', []):
                self.env['woocommerce.product.image'].create({
                    'product_id': woo_product.id,
                    'woo_id': image_data['id'],
                    'src': image_data['src'],
                    'name': image_data.get('name', 'Image'),
                    'alt': image_data.get('alt', ''),
                })
        else:
            # Cập nhật sản phẩm hiện có
            woo_product.write(vals)

            if woo_product.product_id:
                woo_product.product_id.write({
                    'name': product_data['name'],
                    'list_price': float(product_data.get('price', 0)),
                    'default_code': product_data.get('sku', ''),
                    'description': product_data.get('description', ''),
                    'description_sale': product_data.get('short_description', ''),
                })

            # Cập nhật hình ảnh
            current_images = woo_product.images.mapped('woo_id')
            for image_data in product_data.get('images', []):
                if image_data['id'] not in current_images:
                    self.env['woocommerce.product.image'].create({
                        'product_id': woo_product.id,
                        'woo_id': image_data['id'],
                        'src': image_data['src'],
                        'name': image_data.get('name', 'Image'),
                        'alt': image_data.get('alt', ''),
                    })

        return woo_product

    def sync_to_woocommerce(self):
        """Đồng bộ sản phẩm từ Odoo lên WooCommerce"""
        self.ensure_one()
        woo_config = self.env['woocommerce.config'].get_config()
        if not woo_config:
            return False

        try:
            # Chuẩn bị dữ liệu sản phẩm
            product_data = {
                'name': self.name,
                'regular_price': str(self.regular_price),
                'description': self.description,
                'short_description': self.short_description,
                'sku': self.sku,
                'status': self.status,
            }

            # Thêm giá khuyến mãi nếu có
            if self.sale_price:
                product_data['sale_price'] = str(self.sale_price)

            # Thêm số lượng tồn kho
            if self.stock_quantity:
                product_data['stock_quantity'] = self.stock_quantity
                product_data['manage_stock'] = True

            # Thêm danh mục
            if self.categories:
                product_data['categories'] = [{'id': cat.woo_id} for cat in self.categories]

            # Xử lý API endpoint và phương thức
            if self.woo_id:
                # Cập nhật sản phẩm hiện có
                url = f"{woo_config.url}/wp-json/wc/v3/products/{self.woo_id}"
                method = requests.put
            else:
                # Tạo sản phẩm mới
                url = f"{woo_config.url}/wp-json/wc/v3/products"
                method = requests.post

            auth = (woo_config.consumer_key, woo_config.consumer_secret)
            response = method(url, json=product_data, auth=auth)

            if response.status_code not in [200, 201]:
                _logger.error(f"Error syncing product: {response.status_code}")
                _logger.error(response.text)
                return False

            result = response.json()

            # Cập nhật ID nếu là sản phẩm mới
            if not self.woo_id:
                self.write({'woo_id': result['id']})

            return True

        except Exception as e:
            _logger.error(f"Error syncing product to WooCommerce: {str(e)}")
            return False


class WooCommerceProductImage(models.Model):
    _name = 'woocommerce.product.image'
    _description = 'WooCommerce Product Image'

    product_id = fields.Many2one('woocommerce.product', string='Product', ondelete='cascade')
    woo_id = fields.Integer(string='WooCommerce ID')
    name = fields.Char(string='Name')
    src = fields.Char(string='Source URL')
    alt = fields.Char(string='Alt Text')


class WooCommerceCategory(models.Model):
    _name = 'woocommerce.category'
    _description = 'WooCommerce Category'

    name = fields.Char(string='Name', required=True)
    woo_id = fields.Integer(string='WooCommerce ID')
    slug = fields.Char(string='Slug')
    parent_id = fields.Many2one('woocommerce.category', string='Parent Category')
    description = fields.Text(string='Description')