# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from tools.translate import _
import netsvc
import collections
from datetime import datetime
class sale_order(osv.osv):
    def _has_giftcards(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = bool(order.giftcard_ids)
        return res

    _inherit = "sale.order"
    _columns = {
        'giftcard_ids': fields.one2many('gift.card', 'order_id', 'Gift Cards', readonly=True),
        'has_giftcards': fields.function(_has_giftcards, type="boolean", method=True, readonly=True)
    }

    def action_done(self, cr, uid, ids, context=None):
        """
        Creates gift cards for each relevant order line upon payment of this sale order's invoice.

        """
        super(sale_order, self).action_done(cr, uid, ids, context=context)

        success = True
        card_pool = self.pool.get('gift.card')
        line_pool = self.pool.get('sale.order.line')

        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                if line.product_id and line.product_id.giftcard:
                    for i in range(0, int(line.product_uom_qty)):
                        new_card_id = card_pool.create(cr, uid, {
                            "balance": line.price_unit,
                            'sale_order_line_id': line.id,
                            'order_id': order.id,
                            'partner_id': order.partner_id.id,
                            'date_purchase': str(datetime.today().date()),
                            'init_amount':line.price_unit
                        }, context=context)

                        line_pool.write(cr, uid, line.id, {
                            "giftcard_id": new_card_id
                        })

        return success

    def action_wait(self, cr, uid, ids, context=None):
        """
        Creates a separate order line for every gift card in this order.
        Called when the sale is confirmed.

        """
        success = True
        line_orm = self.pool.get('sale.order.line')

        # Split out every order line containing multiple gift cards into one line per gift card.
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                if line.product_id and line.product_id.giftcard:
                    for i in range(0, int(line.product_uom_qty)-1):
                        success = success and line_orm.copy(cr, uid, line.id, {"product_uom_qty": 1})
                    success = success and line_orm.write(cr, uid, line.id, {"product_uom_qty": 1})

        return success and super(sale_order, self).action_wait(cr, uid, ids, context=context)

sale_order()

class sale_order_line(osv.osv):
    def _refund_value(self, cr, uid, ids, field_name, arg, context):
        if not hasattr(ids, "__iter__"):
            ids = [ids]

        values = {}
        for line in self.browse(cr, uid, ids):
            values[line.id] = 0 if line.giftcard_id else (line.price_subtotal / (line.product_uom_qty or 1))

        return values

    _inherit = "sale.order.line"
    _columns = {
        'giftcard_id': fields.many2one('gift.card', 'Gift Card', required=False, readonly=True),
        'refund_value': fields.function(_refund_value, type="float", method=True)
    }
