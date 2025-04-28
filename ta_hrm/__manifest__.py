# -*- coding: utf-8 -*-
{
    'name': "Tada HRM",
    'category': 'Tadas',
    'depends': ['base', 'hr','hr_attendance', 'hr_recruitment', 'hr_payroll', 'hr_holidays', 'sale_management', 'sale_commission'],

    'data': [
        'security/ir.model.access.csv',

        'views/sale_order_views.xml',
        'views/kpi_views.xml',
        'views/product_template_views.xml',
        'views/brand_views.xml',
        'views/hr_work_entry_views.xml',
    ],
}
