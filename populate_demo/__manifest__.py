{
    'name': 'Populate Demo',
    'summary': 'Wingardium Odoosa BI talk - historical transactional blueprint',
    'category': 'Hidden/Tools',
    'author': 'Odoo PS',
    'license': 'LGPL-3',
    'depends': [
        'populate',
        'sale_stock',
        'sale_mrp',
        'purchase_stock',
        'mrp_account',
        'crm',
        'sale_crm',
        'account_budget',
    ],
    'data': [
        'populate/fixture.xml',
        'populate/pilot.xml',
    ],
}
