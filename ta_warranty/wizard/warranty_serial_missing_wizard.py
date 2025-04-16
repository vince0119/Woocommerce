from odoo import models, fields, api, _


class WarrantySerialMissingWizard(models.TransientModel):
    _name = 'warranty.serial.missing.wizard'
    _description = 'Missing Serial Numbers Wizard'

    order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    selected_ids = fields.Many2many('warranty.serial.registration', 'selected_serials_rel',
                                    string='Selected Serials', readonly=True)
    missing_line_ids = fields.One2many('warranty.serial.missing.line', 'wizard_id',
                                       string='Missing Serials')

    @api.model
    def default_get(self, fields_list):
        res = super(WarrantySerialMissingWizard, self).default_get(fields_list)
        if self._context.get('default_missing_ids'):
            missing_ids = self._context.get('default_missing_ids')
            missing_serials = self.env['warranty.serial.registration'].browse(missing_ids)
            missing_lines = [(0, 0, {
                'serial_id': serial.id,
                'seri': serial.seri,
                'product_id': serial.product_id.id,
                'selected': False
            }) for serial in missing_serials]
            res.update({'missing_line_ids': missing_lines})
        return res

    def action_skip(self):
        """Continue with only selected serials"""
        return self.env['warranty.serial.registration'].browse(self.selected_ids.ids)._create_warranty_request(
            self.selected_ids)

    def action_process(self):
        """Process with selected and additional serials"""
        selected_missing = self.missing_line_ids.filtered(lambda l: l.selected).mapped('serial_id')
        all_records = self.selected_ids | selected_missing
        return self.env['warranty.serial.registration'].browse(all_records.ids)._create_warranty_request(all_records)


class WarrantySerialMissingLine(models.TransientModel):
    _name = 'warranty.serial.missing.line'
    _description = 'Missing Serial Line'

    wizard_id = fields.Many2one('warranty.serial.missing.wizard', string='Wizard')
    serial_id = fields.Many2one('warranty.serial.registration', string='Serial Registration')
    seri = fields.Char('Serial Number', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    selected = fields.Boolean('Include', default=False)