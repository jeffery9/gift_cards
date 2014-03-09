# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 RyePDX LLC (http://ryepdx.com/)
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################
{
    'name': 'Gift Cards',
    'version': '0.01',
    'category': 'Generic Modules/Others',
    'description': "Allows salespeople to issue and use gift cards.",
    'author': 'RyePDX LLC',
    'website': ' http://ryepdx.com',
    'depends': ['sale'],
    'data': [
        'gift_view.xml',
        'account_voucher_view.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True,
    'active': True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
