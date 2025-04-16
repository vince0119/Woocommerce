# -*- coding: utf-8 -*-
{
    'name': "Tada Warranty",
    'category': 'Tadas',
    'depends': ['base', 'sale_management', 'stock'],

    'data': [
        'security/warranty_security.xml',
        'security/ir.model.access.csv',

        'views/warranty_views.xml',
        'views/stock_route_views.xml',
        'views/res_users_views.xml',
        'views/warranty_serial_registration_views.xml',

        'data/sequence.xml',
        
        'wizard/warranty_serial_missing_wizard.xml',
    ],
}
