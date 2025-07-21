from odoo import models, fields, api

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    count_flag = fields.Integer(string='Count Flag', default=0)
    in_out_amt = fields.Float(string='In/Out Amt', default=0.0)
    in_out_unit_price = fields.Float(string='Unit Price', default=0.0)
    quant_in_out = fields.Float(string='Quantity', default=0.0)

    @api.depends('x_quant_in_out')
    def _compute_quant_in_out(self):
        qty_out = self.env.context.get('stock_card_qty_out', False)
        for rec in self:
            record = rec.move_id
            value = 0

            picking = record.picking_id
            valuation_ids = False
            if picking:
                #     # valuation_ids = self.env['stock.valuation.layer'].search(picking.action_view_stock_valuation_layers()['domain'])
                valuation_ids = rec.move_id.stock_valuation_layer_ids

            if not valuation_ids and picking:
                purchase = picking._get_subcontracting_source_purchase()
                list_valuation_ids = self.env['stock.valuation.layer']
                if purchase:
                    for p in purchase.picking_ids:
                        valuation_ids = self.env['stock.valuation.layer'].search(
                            p.action_view_stock_valuation_layers()['domain'])
                        list_valuation_ids |= valuation_ids
                    valuation_ids = list_valuation_ids
                else:
                    valuation_domain = rec.picking_id.action_view_stock_valuation_layers()
                    re_valuation_ids = self.env['stock.valuation.layer'].search(valuation_domain['domain'])
                    for v in re_valuation_ids:
                        if v.product_id == rec.product_id and v.quantity == abs(rec.x_quant_in_out):
                            valuation_ids |= v

            if not valuation_ids:
                mrp = self.env['mrp.production'].search([('name', '=', record.group_id.name)])
                if mrp:
                    valuation_ids = self.env['stock.valuation.layer'].search(
                        mrp.action_view_stock_valuation_layers()['domain'])

            if not valuation_ids:
                valuation_ids = record.stock_valuation_layer_ids

            if valuation_ids:
                filtered_valuation_ids = []
                filtered_valuation_ids_quantity = []
                has_zero_quantity = False

                for valuation in valuation_ids:
                    if valuation.product_id == record.product_id:
                        filtered_valuation_ids_quantity.append(valuation.value)
                        has_zero_quantity = True
                    if valuation.product_id == record.product_id and valuation.quantity != 0:
                        filtered_valuation_ids.append(valuation.value / valuation.quantity)
                        has_zero_quantity = False

                if has_zero_quantity:
                    value = sum(filtered_valuation_ids_quantity)
                else:
                    value = (sum(filtered_valuation_ids) / len(filtered_valuation_ids)) * rec.qty_done

            if (rec.picking_code in ['internal',
                                     False] or rec.picking_type_id.id == 22) and "SBC" not in rec.reference and not valuation_ids:
                valuation_ids = self.env['stock.valuation.layer'].search([
                    ('product_id', '=', record.product_id.id),
                    ('create_date', '<=', rec.date)
                ], order='create_date desc', limit=1)

                if valuation_ids and valuation_ids.quantity != 0:
                    value = (
                                        valuation_ids.value / valuation_ids.quantity) * rec.qty_done if valuation_ids.quantity != 0 else 0

            value = round(abs(value) + 0.0049, 2)
            # # rec['x_in_out_amt'] = rec.move_id.stock_valuation_layer_ids.value\
            rec['x_in_out_amt'] = value * -1 if qty_out else value
