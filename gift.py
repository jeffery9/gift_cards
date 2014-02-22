import re
from helpers.shortuuid import uuid
from openerp.osv import fields, osv

class card(osv.osv):
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
        ('number_unique', 'unique(number)', 'Card number collision! Try again.')
    ]

card()
