from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_template(osv.osv):
    _inherit = "product.template"
    _columns = {
        'giftcard': fields.boolean('Gift Card', help="Create a gift card when this product is sold?")
    }
product_template()
