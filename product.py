from openerp.osv import fields, osv
from openerp.tools.translate import _

class product_product(osv.osv):
    _inherit = "product.product"
    _columns = {
        'giftcard': fields.boolean('Gift Card', help="Create a gift card when this product is sold?")
    }
product_product()