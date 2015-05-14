# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 RyePDX LLC (<http://ryepdx.com>)
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

from openerp import netsvc
from openerp.osv import osv, fields
from openerp.tools.translate import _

class account_voucher(osv.osv):
    '''
    This represents payment lines in an account journal and on an invoice.
    This particular variation of the account.voucher model adds a reference
    to a giftcard to payment lines, allowing us to keep track of how gift
    cards have been used, as well as which gift card was used on any given
    payment line.

    '''
    
    _inherit = 'account.voucher'
    
    _columns = {
        'origin': fields.char('Origin', size=16, help='Mentions the reference of Sale/Purchase document'),
        'giftcard_id': fields.many2one('gift.card', 'Gift Card', { 'required': False }) 
    }

    def check_card_transaction(self, vouchers):
        '''
        Makes sure the giftcards used on the passed-in payment lines have enough
        on them to actually cover the charges they are supposed to cover.
        Raises an error if they don't.

        '''
        
        # We want to grab all the vouchers with gift cards and make an index
        # of their gift cards' balances, keyed off the gift card numbers, to
        # facilitate checking those balances against the charges against them.
        vouchers_with_giftcards = [
            voucher for voucher in vouchers if voucher.giftcard_id
        ]
        giftcards = dict([(voucher.giftcard_id.number, voucher.giftcard_id.balance)
            for voucher in vouchers_with_giftcards
        ])

        # Doing the balance checks we prepped for above.
        # Raises an exception if a gift card doesn't have enough of a balance.
        # This is the only way to bubble error messages up to the user in OERP.
        for voucher in vouchers_with_giftcards:
            gcard = voucher.giftcard_id
            if hasattr(gcard, "active") and not gcard.active:
                raise osv.except_osv(_('Error'), _('Gift card (%s) is not active!') % gcard.number)

            giftcards[gcard.number] -= voucher.amount
            if giftcards[gcard.number] < 0:
                raise osv.except_osv(_('Error'), _("Gift card has insufficient funds!"))
        return True

    def authorize_card(self, cr, uid, ids, context=None):
        '''
        Subtracts the invoice line charges from the gift card balances after
        first checking to make sure that each gift card has enough on it to
        actually cover the charges being attempted against it.
        
        '''

        # Make sure the requested charges can actually be made
        # against the given gift cards.
        vouchers = [self.browse(cr, uid, res_id, context) for res_id in ids]
        self.check_card_transaction(vouchers)
        giftcard_orm = self.pool.get('gift.card')

        # Subtract charges from gift cards.
        for voucher in filter(lambda voucher: voucher.giftcard_id, vouchers):
            if (voucher.giftcard_id.balance - voucher.amount) < 0:
                raise Exception(
                    'Insufficient funds on gift card %s to pay voucher %s' % (str(voucher.giftcard_id), str(voucher))
                )
            giftcard_orm.write(cr, uid, [voucher.giftcard_id.id], {
                'balance': voucher.giftcard_id.balance - voucher.amount
            })

        # Mark the payment lines as processed/validated.
        #wf_service = netsvc.LocalService("workflow")

        #for res_id in ids:
        #    wf_service.trg_validate(uid, 'account.voucher', res_id, 'proforma_voucher', cr)

        return True


    def cancel_voucher(self, cr, uid, ids, context=None):
        '''
        Handles increasing the balance of the gift card used to pay for a voucher
        when the voucher it was used to pay for is canceled.
        '''
        giftcard_orm = self.pool.get('gift.card')

        # Make sure the vouchers can be cancelled. This line will throw an exception if they can't.
        super(account_voucher, self).cancel_voucher(cr, uid, ids, context=context)

        # Increase the balances of any associated gift cards by the amounts being refunded.
        for voucher in self.browse(cr, uid, ids, context=context):
            if voucher.giftcard_id:
                giftcard_orm.write(cr, uid, [voucher.giftcard_id.id], {
                    'balance': voucher.giftcard_id.balance + voucher.amount
                })
        return True


    def proforma_voucher(self, cr, uid, ids, context=None):
        '''
        Called when a payment is added to an invoice.
        '''
        self.authorize_card(cr, uid, ids, context=context)
        return super(account_voucher, self).proforma_voucher(cr, uid, ids, context=context)
    
account_voucher()
