import re
from helpers.shortuuid import uuid
from openerp.osv import fields, osv

class card(osv.osv):
    '''Represents a gift card issued to a customer.'''

    _name = "gift.card"
    _rec_name = "number"
    _columns = {
        'number': fields.char('Card Number', size=19, readonly=True),
        'value': fields.float('Card Value')
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

card()
