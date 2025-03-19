import json
import base64
import html
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class ProductImportWizard(models.TransientModel):
    _name = 'product.import.wizard'
    _description = 'Import Product from JSON'

    json_file = fields.Binary(string="Upload JSON File")

    def import_json_data(self):
        self.ensure_one()

        if not self.json_file:
            raise ValueError("No file uploaded or file is empty")

        try:
            json_data = base64.b64decode(self.json_file).decode("utf-8")
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")

        self._process_products(data)

    def _process_products(self, data):
        ProductTemplate = self.env["product.template"]
        ProductProduct = self.env["product.product"]
        ProductPublicCategory = self.env["product.public.category"]
        ProductAttribute = self.env["product.attribute"]
        ProductAttributeValue = self.env["product.attribute.value"]
        ProductTemplateAttributeLine = self.env["product.template.attribute.line"]

        # 📌 Bước 1: Tìm `product.template` theo SKU
        if not data:
            raise ValueError("JSON is empty")

        sku = data[0]["sku"]
        product_template = ProductTemplate.search([("default_code", "=", sku)], limit=1)

        if not product_template:
            product_template = ProductTemplate.create({
                "name": "Product Template for " + sku,
                "default_code": sku,
                "list_price": data[0]["price"],
            })

        # 📌 Bước 2: Xử lý `categories`
        category_ids = []
        for cat in data[0].get("categories", []):
            category_name = html.unescape(cat["name"])
            category = ProductPublicCategory.search([("name", "=", category_name)], limit=1)

            if not category:
                category = ProductPublicCategory.create({"name": category_name})

            category_ids.append(category.id)

        if category_ids:
            product_template.public_categ_ids = [(6, 0, category_ids)]

        # 📌 Bước 3: Xử lý `attributes`
        attribute_map = {}
        template_attribute_lines = {}

        for product_data in data:
            for attr in product_data.get("attributes", []):
                attr_name = html.unescape(attr["name"])
                attr_value_name = html.unescape(attr["option"])

                if attr_name not in attribute_map:
                    attribute = ProductAttribute.search([("name", "=", attr_name)], limit=1)
                    if not attribute:
                        attribute = ProductAttribute.create({"name": attr_name})
                    attribute_map[attr_name] = attribute

                attribute = attribute_map[attr_name]

                value = ProductAttributeValue.search([
                    ("name", "=", attr_value_name),
                    ("attribute_id", "=", attribute.id)
                ], limit=1)

                if not value:
                    value = ProductAttributeValue.create({
                        "name": attr_value_name,
                        "attribute_id": attribute.id
                    })

                if attribute.id not in template_attribute_lines:
                    template_attribute_lines[attribute.id] = []

                template_attribute_lines[attribute.id].append(value.id)

        # 📌 Bước 4: Gán attributes vào `product.template.attribute.line`
        for attr_id, value_ids in template_attribute_lines.items():
            line = ProductTemplateAttributeLine.search([
                ("product_tmpl_id", "=", product_template.id),
                ("attribute_id", "=", attr_id)
            ], limit=1)

            if not line:
                ProductTemplateAttributeLine.create({
                    "product_tmpl_id": product_template.id,
                    "attribute_id": attr_id,
                    "value_ids": [(6, 0, list(set(value_ids)))]
                })

        # 📌 Bước 5: Xử lý `product.product` (biến thể)
        for product_data in data:
            variant_values = []
            for attr in product_data.get("attributes", []):
                attr_name = html.unescape(attr["name"])
                attr_value_name = html.unescape(attr["option"])

                attribute = attribute_map.get(attr_name)
                if attribute:
                    value = ProductAttributeValue.search([
                        ("name", "=", attr_value_name),
                        ("attribute_id", "=", attribute.id)
                    ], limit=1)

                    if value:
                        variant_values.append(value.id)

            # 📌 Kiểm tra nếu biến thể đã tồn tại
            existing_variant = ProductProduct.search([
                ("product_tmpl_id", "=", product_template.id),
                ("product_template_variant_value_ids", "in", variant_values)
            ], limit=1)

            # 📌 Nếu chưa có biến thể, thì tạo mới
            if not existing_variant:
                ProductProduct.create({
                    "product_tmpl_id": product_template.id,
                    "default_code": product_data["sku"],
                    "list_price": product_data["price"],
                    "product_template_variant_value_ids": [(6, 0, variant_values)]
                })
            else:
                _logger.info(f"Product variant already exists for {product_data['sku']}, skipping creation.")

class ImportProductWizardView(models.TransientModel):
    _inherit = 'product.import.wizard'

    def action_import(self):
        self.import_json_data()
        return {'type': 'ir.actions.act_window_close'}