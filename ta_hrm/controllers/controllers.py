# -*- coding: utf-8 -*-
# from odoo import http


# class TaHrm(http.Controller):
#     @http.route('/ta_hrm/ta_hrm', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/ta_hrm/ta_hrm/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('ta_hrm.listing', {
#             'root': '/ta_hrm/ta_hrm',
#             'objects': http.request.env['ta_hrm.ta_hrm'].search([]),
#         })

#     @http.route('/ta_hrm/ta_hrm/objects/<model("ta_hrm.ta_hrm"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('ta_hrm.object', {
#             'object': obj
#         })

