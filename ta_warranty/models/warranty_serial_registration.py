from odoo import models, fields, api, _


class WarrantySerialRegistration(models.Model):
    _name = 'warranty.serial.registration'
    _description = 'Warranty Serial Registration'

    seri = fields.Char('Seri Number', required=True, index=True)
    user_id = fields.Many2one('res.users', string='API User')
    create_date = fields.Datetime('Date Created', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('created', 'Created')
    ], string='Status', default='draft')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            existing = self.search([('seri', '=', vals.get('seri'))])
            if existing:
                return existing[0]
        return super(WarrantySerialRegistration, self).create(vals_list)

    def action_create_warranty_request(self):
        picking_serial_map = {}

        # Check each serial registration against barcodes
        for record in self:
            if not record.seri or record.state == 'created':
                continue

            # Find matching barcode record
            barcode_record = self.env['stock.picking.barcode'].search([
                ('barcode', '=', record.seri)
            ], limit=1)

            if not barcode_record:
                continue

            # Group by picking_id to create one warranty request per delivery
            picking = barcode_record.picking_id
            if picking.id not in picking_serial_map:
                picking_serial_map[picking.id] = {
                    'picking': picking,
                    'serials': []
                }
            picking_serial_map[picking.id]['serials'].append({
                'serial': record.seri,
                'product': barcode_record.product_id,
                'registration': record
            })

        # Create warranty requests for each delivery with matched serials
        created_requests = self.env['warranty.request']
        for picking_data in picking_serial_map.values():
            picking = picking_data['picking']

            # Find related sale order
            sale_order = picking.sale_id or self.env['sale.order'].search([
                ('procurement_group_id', '=', picking.group_id.id)
            ], limit=1)

            if not sale_order:
                continue

            # Create warranty request
            warranty_vals = {
                'sale_id': sale_order.id,
                'partner_id': sale_order.partner_id.id,
                'delivery_id': picking.id,
                'line_ids': []
            }

            # Add warranty lines
            for serial_data in picking_data['serials']:
                warranty_vals['line_ids'].append((0, 0, {
                    'product_id': serial_data['product'].id,
                    'warranty_qty': 1,
                    'serial_number': serial_data['serial'],
                    'serial_registration_id': serial_data['registration'].id
                }))

            # Create the warranty request
            warranty_request = self.env['warranty.request'].create(warranty_vals)
            created_requests += warranty_request

            # Update serial registrations to 'created' state
            for serial_data in picking_data['serials']:
                serial_data['registration'].write({'state': 'created'})

        # Show notification to user
        if not created_requests:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No matching barcodes found for selected serial numbers'),
                    'type': 'warning',
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    }
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
                'params': {
                    'menu_id': self.env.ref('ta_warranty.menu_warranty_serial_registration').id,
                    'notification': {
                    'title': _('Success'),
                    'message': _('Warranty requests created successfully'),
                    'type': 'success',
                    }
                }
            }