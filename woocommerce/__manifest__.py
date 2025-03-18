# -*- coding: utf-8 -*-
{
    'name': "woocommerce",
    'category': 'Tadas',
    'version': '0.1',

    'depends': ['base', 'product', 'sale', 'stock'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',

        'views/woocommerce_views.xml',
        'views/woocommerce_menus.xml',
        'views/woocommerce_attribute_views.xml',

        'wizards/woocommerce_sync_wizard_views.xml',
    ],
}

