import re, time
from helpers.shortuuid import uuid
from openerp.osv import fields, osv
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT

class card(osv.osv):
    """Represents a gift card in the system."""
    _name = "gift.card"
    _rec_name = "number"
    _columns = {
        'number': fields.char('Card Number', size=19),
        'balance': fields.float('Balance'),#, readonly=True),
        'voucher_ids': fields.one2many('account.voucher', 'giftcard_id', 'Vouchers', readonly=True),
        'sale_order_line_id': fields.many2one('sale.order.line', 'Order Line', readonly=True),
        'order_id': fields.many2one('sale.order', 'Sale Order', readonly=True),
        'email_recipient': fields.char('Recipient Email', size=128),
        'email_date': fields.date('Email After'),
        'email_sent': fields.boolean('Email Sent?', readonly=1),
        'note': fields.text('Certificate Note')
    }
    _defaults = {
        # Creates a random string of 16 characters,
        # with a space between every group of 4.
        'number': lambda *args: ' '.join(
            re.findall('....', uuid().upper()[0:16])
        )
    }
    _sql_constraints = [
        # This constraint is highly unlikely to be violated, given the fact
        # that `number` is based off a UUID. If it gets repeatedly violated,
        # beware! There is probably some sort of dark magic afoot. Or else you
        # just have way too many damn gift cards in your database.
        ('number_unique', 'unique(number)', 'Card number collision! Try again.')
    ]

    def undelivered_cards(self, cr, uid, context=None):
        cards = self.browse(cr, uid, self.search(cr, uid, [
            ('email_sent', '=', False), ('email_date', '<=', time.strftime(DEFAULT_SERVER_DATE_FORMAT))
        ]))

        return [{'id': c.id,
                 'code': c.number,
                 'balance': c.balance,
                 'recipient': c.email_recipient,
                 'note': c.note
                } for c in cards]

    def mark_delivered(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'email_sent': True})

card()
