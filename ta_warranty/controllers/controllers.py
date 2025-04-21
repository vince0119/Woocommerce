from odoo import http
from odoo.fields import Datetime
from odoo.http import request, Response
import json


class ApiController(http.Controller):

    @http.route('/api/warranty/register', auth='public', type='http', methods=['POST'], csrf=False)
    def register_warranty(self, **kw):
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            seri = data.get('seri', False)
            token = data.get('token', False)

            # Validate input
            if not seri or not token:
                response = {"success": False, "message": "Missing seri or token"}
                return Response(json.dumps(response), content_type='application/json', status=400)

            # Find user by token
            api_user = request.env['res.users'].sudo().search([('token_seri', '=', token)], limit=1)
            if not api_user:
                response = {"success": False, "message": "Token not found"}
                return Response(json.dumps(response), content_type='application/json', status=401)

            matching_barcode = request.env['stock.picking.barcode'].sudo().search([('barcode', '=', seri)], limit=1)
            if not matching_barcode:
                response = {"success": False, "message": "Serial number does not match any valid barcode"}
                return Response(json.dumps(response), content_type='application/json', status=400)

            lot_id = False
            if matching_barcode.picking_id:
                move_lines = request.env['stock.move.line'].sudo().search([
                    ('picking_id', '=', matching_barcode.picking_id.id),
                    ('product_id', '=', matching_barcode.product_id.id)
                ])
                if move_lines:
                    # Lấy lot_id từ move_line đầu tiên phù hợp
                    lot_id = move_lines[0].lot_id.id if move_lines[0].lot_id else False

            sale_order = matching_barcode.picking_id.sale_id
            existing = request.env['warranty.serial.registration'].sudo().search([('seri', '=', seri)], limit=1)
            is_duplicate = bool(existing)

            serial_reg = request.env['warranty.serial.registration'].sudo().create({
                'seri': seri,
                'user_id': api_user.id,
                'create_date': Datetime.now(),
                'order_id': sale_order.id if sale_order else False,
                'product_id': matching_barcode.product_id.id,
                'lot_id': lot_id
            })

            response = {
                "success": True,
                "message": "Serial registered successfully" if not is_duplicate else "Serial was already registered",
                "is_duplicate": is_duplicate
            }
            return Response(json.dumps(response), content_type='application/json')

        except Exception as e:
            response = {"success": False, "message": f"Error: {str(e)}"}
            return Response(json.dumps(response), content_type='application/json', status=500)