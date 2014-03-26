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
        'gift_card' : fields.boolean('Gift Card', readonly=True)
    }
    _defaults = {
        'gift_card' : False
    }

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):
        order_orm = self.pool.get("sale.order")
        giftcard_orm = self.pool.get("gift.card")
        voucher_orm = self.pool.get("account.voucher")
        results = []

        if not hasattr(ids, "__iter__"):
            ids = [ids]

        # Doing this one at a time so we can associate refund invoices with their originals.
        for id in ids:

            invoice = self.browse(cr, uid, id, context=context)

            # TODO: Make this more flexible? What if they only paid a very
            # little bit with this invoice and just want to cancel *this*
            # invoice but leave everything else intact? The tricky bit, of
            # course, is picking *which* cards to debit and communicating
            # to the user which cards were debited.

            # Now debit any gift cards that were bought with this invoice.
            order = order_orm.browse(cr, uid, order_orm.search(cr, uid, [('invoice_ids', 'in', id)]))
            giftcards = sorted(order.giftcard_ids, lambda x, y: x.balance - y.balance)
            new_balances = []
            balances = [{"id":card.id, "balance": card.balance} for card in giftcards]

            # Remove, at most, the amount paid for these cards.
            debit_total = min(
                invoice.amount_total, sum([card.sale_order_line_id.price_unit for card in giftcards])
            )

            # Verify that there is enough left on the cards bought with this invoice to cover
            # the amount being refunded. For example, if someone bought a $5 gift card, and the
            # invoice being refunded paid for $1 on that gift card, then we need to make sure
            # there's at least $1 left on that card for us to *remove* from it before we give
            # them back their dollar. Otherwise we're in a situation where we're giving them
            # back money they've already spent!
            for i in range(0, len(balances)):
                debit = min(balances[i]["balance"], debit_total)
                debit_total -= debit
                new_balances.append([{"id": balances[i]["id"], "balance": (balances[i]["balance"] - debit)}])

                if debit_total <= 0:
                    break

            if debit_total > 0:
                raise osv.except_osv(_("Error"), _("This invoice was used to buy gift cards which were, in turn, " +
                                         "used on other invoices. Refund enough invoices on the gift cards to cover " +
                                         "the refund of this invoice and try again."))

            if debit_total < 0:
                # This should *never* happen, but we're catching it here for completeness.
                osv.except_osv(_("Error"), _("Ended up with a negative debit after refunding gift cards!"))

            if debit_total == 0:
                # This is the normal case. If we've reached this point, go ahead and commit
                # the debits to the database.
                result = super(account_invoice, self).refund(
                    cr, uid, [ids], date=date, period_id=period_id,
                    description=description, journal_id=journal_id, context=context
                )

                if result:
                    # Refund all gift cards used to pay for this invoice.
                    for voucher in voucher_orm.search_read(cr, uid, [
                        ('move_id', '=', invoice.move_id), ('giftcard_id', '!=', False)
                    ]):
                        giftcard = giftcard_orm.browse(cr, uid, voucher['giftcard_id'])
                        giftcard_orm.write(cr, uid, voucher['giftcard_id'], {
                            "balance": giftcard.balance + voucher['amount']
                        })

                    # Write all debits to purchased gift cards.
                    for card in new_balances:
                        giftcard_orm.write(cr, uid, card["id"], {"balance": card["balance"]})

                # Append result to our list of results, no matter what.
                results.append(result[0])

            cr.commit()

        return results

account_invoice()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

