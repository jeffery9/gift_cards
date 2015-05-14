# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 NovaPoint Group LLC (<http://www.novapointgroup.com>)
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

from openerp.osv import osv, fields
from openerp.tools.translate import _

class account_invoice(osv.osv):
    
    _inherit = 'account.invoice'
    _columns = {
        'gift_card': fields.boolean('Gift Card', readonly=True)
    }
    _defaults = {
        'gift_card': False
    }

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):
        """Refunds the invoice, crediting and debiting gift cards as necessary."""
        order_orm = self.pool.get("sale.order")
        giftcard_orm = self.pool.get("gift.card")
        voucher_orm = self.pool.get("account.voucher")

        if not hasattr(ids, "__iter__"):
            ids = [ids]

        result = super(account_invoice, self).refund(
            cr, uid, ids, date=date, period_id=period_id,
            description=description, journal_id=journal_id, context=context
        )

        # Don't proceed to refunding gift cards if the superclass' refund attempt failed.
        if not result:
            return result

        for invoice in self.browse(cr, uid, ids):
            # Refund all gift cards used to pay for this invoice.
            for voucher in voucher_orm.read(voucher_orm.search(cr, uid, [
                ('move_id', '=', invoice.move_id), ('giftcard_id', '!=', False)
            ])):
                giftcard = giftcard_orm.browse(cr, uid, voucher['giftcard_id'])
                giftcard_orm.write(cr, uid, voucher['giftcard_id'], {
                    "balance": giftcard.balance + voucher['amount']
                })

        return result

account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

