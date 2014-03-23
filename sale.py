# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from tools.translate import _
import netsvc
import collections

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
                            'order_id': order.id
                        }, context=context)

                        line_pool.write(cr, uid, line.id, {
                            "giftcard_id": new_card_id
                        })

        cr.commit()

        return success

    def action_wait(self, cr, uid, ids, context=None):
        success = True
        line_orm = self.pool.get('sale.order.line')

        # Split out every order line containing multiple gift cards into one line per gift card.
        for order in self.browse(cr, uid, ids, context=context):
            for line in order.order_line:
                if line.product_id and line.product_id.giftcard:
                    for i in range(0, int(line.product_uom_qty)-1):
                        success = success and line_orm.copy(cr, uid, line.id, {"product_uom_qty": 1})
                    success = success and line_orm.write(cr, uid, line.id, {"product_uom_qty": 1})

        cr.commit()

        return success and super(sale_order, self).action_wait(cr, uid, ids, context=context)

sale_order()

class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
    _columns = {
        'giftcard_id': fields.many2one('gift.card', 'Gift Card', required=False, readonly=True)
    }