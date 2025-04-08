from odoo import _, fields, models


class StockPickingBarcode(models.Model):
    _name = "stock.picking.barcode"
    _description = "Barcode Scanned for Stock Picking"

    picking_id = fields.Many2one(
        "stock.picking", string="Stock Picking", required=True
    )
    product_id = fields.Many2one(
        "product.product", string="Product", required=True
    )
    barcode = fields.Char(required=True)
    scanned_at = fields.Datetime(default=fields.Datetime.now)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    barcode_line_ids = fields.One2many(
        "stock.picking.barcode", "picking_id", string="Scanned Barcodes", readonly=True
    )

