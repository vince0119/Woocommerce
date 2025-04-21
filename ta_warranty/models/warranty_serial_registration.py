from odoo import models, fields, api, _
from odoo.exceptions import UserError


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

    order_id = fields.Many2one('sale.order', string='Sale Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    lot_id = fields.Many2one('stock.lot', string='Lot', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            existing = self.search([('seri', '=', vals.get('seri'))])
            if existing:
                return existing[0]
        return super(WarrantySerialRegistration, self).create(vals_list)

    def action_create_warranty_request(self):
        # Check if all selected records have the same order_id
        selected_records = self.filtered(lambda r: r.state != 'created' and r.seri)
        if not selected_records:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'message': _('No valid serial numbers selected'),
                    'type': 'warning',
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    }
                }
            }

        # Get the first record's order_id
        first_order = selected_records[0].order_id
        if not first_order:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Error'),
                    'message': _('The selected records must have a sales order assigned'),
                    'type': 'danger',
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    }
                }
            }

        # Check if all records have the same order_id
        for record in selected_records:
            if not record.order_id or record.order_id.id != first_order.id:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Error'),
                        'message': _('All selected serial numbers must belong to the same sales order'),
                        'type': 'danger',
                        'next': {
                            'type': 'ir.actions.act_window_close'
                        }
                    }
                }

        # Find all records for the same order that were not selected
        all_order_records = self.search([
            ('order_id', '=', first_order.id),
            ('state', '=', 'draft'),
            ('id', 'not in', selected_records.ids)
        ])

        # If there are unselected records from the same order, show warning dialog
        if all_order_records:
            return {
                'name': _('Missing Serial Numbers'),
                'type': 'ir.actions.act_window',
                'res_model': 'warranty.serial.missing.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_selected_ids': selected_records.ids,
                    'default_missing_ids': all_order_records.ids,
                    'default_order_id': first_order.id,
                }
            }

        # If no missing records, proceed with creating warranty request
        return self._create_warranty_request(selected_records)

    def _create_warranty_request(self, records):
        """Helper method to create warranty requests from selected records"""
        picking_serial_map = {}

        # Check each serial registration against barcodes
        for record in records:
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
