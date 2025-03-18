# -*- coding: utf-8 -*-
# from odoo import http


# class Woocommerce(http.Controller):
#     @http.route('/woocommerce/woocommerce', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/woocommerce/woocommerce/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('woocommerce.listing', {
#             'root': '/woocommerce/woocommerce',
#             'objects': http.request.env['woocommerce.woocommerce'].search([]),
#         })

#     @http.route('/woocommerce/woocommerce/objects/<model("woocommerce.woocommerce"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('woocommerce.object', {
#             'object': obj
#         })

