from openerp.osv import fields, osv

class card(osv.osv):
    _name = "gift.card"
    _columns = {
        'value': fields.float('Card Value'),
        'partner_id': fields.many2one("res.partner", 'Customer'),
    }

card()