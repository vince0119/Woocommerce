from odoo import models, fields, api


class WarrantyRequest(models.Model):
    _name = 'warranty.request'
    _description = 'Warranty Request'
    _order = 'name desc'

    name = fields.Char(string='Warranty Request No.', required=True, readonly=True, default='New')
    sale_id = fields.Many2one('sale.order', string='Source Document', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    delivery_id = fields.Many2one('stock.picking', string='Delivery Order', readonly=True)
    line_ids = fields.One2many('warranty.request.line', 'warranty_id', string='Products')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('confirmed', 'Confirmed'),
        ('returned', 'Returned'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    return_picking_count = fields.Integer(string="Return", compute="_compute_return_picking_count")

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate sequential request number"""
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('warranty.request') or 'New'
        return super(WarrantyRequest, self).create(vals_list)

    def action_request(self):
        self.state = 'requested'

    def action_confirm(self):
        self.write({'state': 'confirmed'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_create_return_picking(self):
        valid_lines = self.line_ids.filtered(lambda l: l.warranty_type in ['warranty', 'scrap'])

        return_route = self.env['stock.route'].search([('type', '=', 'return')], limit=1)
        return_rule = self.env['stock.rule'].search([('route_id', '=', return_route.id)], limit=1)

        partner_location = self.delivery_id.location_dest_id

        return_move_lines = []
        for line in valid_lines:
            original_move = self.env['stock.move'].search([
                ('picking_id', '=', self.delivery_id.id),
                ('product_id', '=', line.product_id.id)
            ], limit=1)

            return_move_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.warranty_qty,
                'product_uom': original_move.product_uom.id or line.product_id.uom_id.id,
                'name': f"Return of {line.product_id.name}",
                'location_id': partner_location.id,
                'location_dest_id': return_rule.location_dest_id.id,
                'picking_type_id': self.delivery_id.picking_type_id.return_picking_type_id.id,
            }))

        return_picking = self.env['stock.picking'].create({
            'return_id': self.delivery_id.id,
            'partner_id': self.partner_id.id,
            'group_id': self.sale_id.procurement_group_id.id,
            'origin': f"Return to warranty {self.delivery_id.name}",
            'location_id': partner_location.id,
            'location_dest_id': return_rule.location_dest_id.id,
            'picking_type_id': self.delivery_id.picking_type_id.return_picking_type_id.id,
            'move_ids_without_package': return_move_lines,
            'warranty_request_id': self.id,
            'sale_id': self.sale_id.id
        })

        return_picking.action_confirm()
        self.write({'state': 'returned'})

        warranty_lines = valid_lines.filtered(lambda l: l.warranty_type == 'warranty')
        warranty_route = self.env['stock.route'].search([('type', '=', 'warranty')], limit=1)
        warranty_rule = self.env['stock.rule'].search([('route_id', '=', warranty_route.id)], limit=1)

        if warranty_lines and warranty_rule:
            self._create_transfer_picking(warranty_lines, warranty_rule, "Warranty")

        scrap_lines = valid_lines.filtered(lambda l: l.warranty_type == 'scrap')
        scrap_route = self.env['stock.route'].search([('type', '=', 'scrap')], limit=1)
        scrap_rule = self.env['stock.rule'].search([('route_id', '=', scrap_route.id)], limit=1)

        if scrap_lines and scrap_rule:
            self._create_transfer_picking(scrap_lines, scrap_rule, "Scrap")

        return return_picking

    def _create_transfer_picking(self, lines, rule, transfer_type):
        move_lines = []
        for line in lines:
            move_lines.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.warranty_qty,
                'product_uom': line.product_id.uom_id.id,
                'name': f"{transfer_type} transfer for {line.product_id.name}",
                'location_id': rule.location_src_id.id,
                'location_dest_id': rule.location_dest_id.id,
            }))

        origin = f"{transfer_type} of {self.delivery_id.name}"

        picking = self.env['stock.picking'].create({
            'return_id': self.delivery_id.id,
            'partner_id': self.partner_id.id,
            'group_id': self.delivery_id.group_id.id,
            'origin': origin,
            'location_id': rule.location_src_id.id,
            'location_dest_id': rule.location_dest_id.id,
            'picking_type_id': rule.picking_type_id.id,
            'move_ids_without_package': move_lines,
            'warranty_request_id': self.id,
            'sale_id': self.sale_id.id
        })
        picking.action_confirm()
        return picking

    @api.depends('delivery_id')
    def _compute_return_picking_count(self):
        for record in self:
            if record.delivery_id:
                record.return_picking_count = self.env['stock.picking'].search_count([
                    '|', '|',
                    ('origin', 'ilike', f"Return to warranty {record.delivery_id.name}"),
                    ('origin', 'ilike', f"Warranty of {record.delivery_id.name}"),
                    ('origin', 'ilike', f"Scrap of {record.delivery_id.name}")
                ])
            else:
                record.return_picking_count = 0

    def action_view_return_pickings(self):
        pass
        self.ensure_one()
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        action['domain'] = [
            '|', '|',
            ('origin', 'ilike', f"Return to warranty {self.delivery_id.name}"),
            ('origin', 'ilike', f"Warranty of {self.delivery_id.name}"),
            ('origin', 'ilike', f"Scrap of {self.delivery_id.name}")
        ]

        return action


class WarrantyRequestLine(models.Model):
    _name = 'warranty.request.line'
    _description = 'Warranty Request Line'

    warranty_id = fields.Many2one('warranty.request', string='Warranty Request', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    warranty_qty = fields.Float('Warranty Quantity', digits='Product Unit of Measure')
    warranty_type = fields.Selection([
        ('warranty', 'Warranty'),
        ('scrap', 'Scrap')
    ], string="Warranty Type")

    damage_level = fields.Selection([
        ('light', 'Light'),
        ('medium', 'Medium'),
        ('heavy', 'Heavy')
    ], string="Damage Level")
    serial_number = fields.Char(string='Serial Number')
    serial_registration_id = fields.Many2one('warranty.serial.registration', string='Serial Registration',
                                             compute='_compute_serial_registration', store=True)

    @api.depends('serial_number')
    def _compute_serial_registration(self):
        for line in self:
            if line.serial_number:
                registration = self.env['warranty.serial.registration'].search([
                    ('seri', '=', line.serial_number)
                ], limit=1)
                line.serial_registration_id = registration.id if registration else False
