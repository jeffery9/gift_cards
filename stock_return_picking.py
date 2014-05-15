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
import time

from openerp.osv import osv, fields
from openerp.tools.translate import _

# The trick here is that refunded gift cards need to be zeroed out on *other*
# types of refunds as well. And other types of refunds need to refund only the
# *remaining balance* of the gift card.
def refund_amount(sale_order, move, quantity):
    """
    Calculates the amount that should be refunded, given a particular sale order and move line.

    """
    # Simplest case: the move line's order line has a gift card associated with it.
    if move.sale_line_id and move.sale_line_id.giftcard_id:
        return move.sale_line_id.giftcard_id.balance

    # Otherwise, find the first order line with a matching product ID and use that.
    for line in sale_order.order_line:
        # Gift cards are non-refundable.
        if line.product_id and line.product_id.id == move.product_id.id and not line.giftcard_id:
            return ((line.price_subtotal / line.product_uom_qty or 1) * quantity)

    # Nothing matched? Then just refund nothing.
    return 0.00

class stock_return_picking(osv.TransientModel):
    _inherit = 'stock.return.picking'
    _columns = {
        'invoice_state': fields.selection(
            [('2binvoiced', 'To be refunded/invoiced'), ('none', 'No invoicing'),
             ('cc_refund','Credit Card Refund'), ('gc_refund', 'Gift Card Refund')], 'Invoicing', required=True),
        'giftcard_id': fields.many2one('gift.card', 'Gift Card for Refund', {'required': False})
    }

    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        if context is None:
            context = {}
        res = super(stock_return_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        pick_obj = self.pool.get('stock.picking')
        voucher_orm = self.pool.get('account.voucher')
        pick = pick_obj.browse(cr, uid, record_id, context=context)

        # Refund to gift card on a voucher if a gift card was used, by default.
        if pick:
            if 'invoice_state' in fields:
                voucher_ids = voucher_orm.read(cr, uid, voucher_orm.search(cr, uid, [
                    ('rel_sale_order_id', '=', pick.sale_id.id), ('state', '=', 'posted'),
                    ('type', '=', 'receipt'), ('giftcard_id', '!=', False)
                ], order="id desc", context=context), context=context)

                if voucher_ids:
                    res['invoice_state'] = 'gc_refund'
                    res['giftcard_id'] = voucher_ids[0].giftcard_id
        return res

    # TODO: Find out if cc_api's implementation is as completely broken as it seems.
    def create_returns(self, cr, uid, ids, context=None):
        """
         Creates return picking. Also refunds and zeroes out gift cards as necessary.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}

        record_id = context and context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        data_obj = self.pool.get('stock.return.picking.memory')
        voucher_obj = self.pool.get('account.voucher')
        giftcard_orm = self.pool.get("gift.card")
        pick = pick_obj.browse(cr, uid, record_id, context=context)

        # TODO: Is this correct? Shouldn't we be operating over all the IDs?
        data = self.read(cr, uid, ids[0], context=context)
        res = super(stock_return_picking, self).create_returns(cr, uid, ids, context=context)

        move_lines = data['product_return_moves']

        amount = 0.00

        # ...for every line in the delivery order...
        for move in move_lines:

            # ...get the line and delivery order we're supposed to refund.
            return_line = data_obj.browse(cr, uid, move, context=context)
            move = move_obj.browse(cr, uid, return_line.move_id.id, context=context)

            # Compute the amount we'll be refunding.
            if pick.sale_id:
                amount = refund_amount(pick.sale_id, move, return_line.quantity)

            # Is there an amount we need to refund, and did the user select 'gift card refund'?
            if amount and data['invoice_state'] == 'gc_refund':
                # Refund the selected gift card.
                giftcard = giftcard_orm.browse(cr, uid, data['giftcard_id'], context=context)
                giftcard_orm.write(cr, uid, data['giftcard_id'], {'balance': giftcard.balance + amount})

                # Grab all the vouchers with gift cards to be moved over to the new delivery order...?
                voucher_ids = voucher_obj.search(cr, uid, [
                    ('rel_sale_order_id', '=', pick.sale_id.id), ('state', '=', 'posted'),
                    ('type', '=', 'receipt'), ('giftcard_id', '!=', False)], order="id desc", context=context)

                if voucher_ids:
                    domain = res.get('domain') and eval(res['domain'])
                    new_pick_id = False
                    if domain and len(domain) and len(domain[0]) == 3:
                        new_pick_id = domain[0][2][0]
                    if new_pick_id:
                        self.pool.get('stock.picking').write(cr, uid, new_pick_id, {'voucher_id':voucher_ids[0]}, context=context)

        cr.commit()

        return res

stock_return_picking()

class stock_picking(osv.osv):
    
    _inherit = "stock.picking"
    _columns = {
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable"),
            ("credit_card", "Credit Card"),
            ("cc_refund", "Credit Card Refund"),
            ('gc_refund', 'Gift Card Refund')
        ], "Invoice Control", select=True, required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'giftcard_id': fields.many2one('gift.card', 'Gift Card for Refund', {'required': False})
    }

    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        if context is None:
            context = {}
        res = super(stock_picking, self).default_get(cr, uid, fields, context=context)
        record_id = context and context.get('active_id', False) or False
        voucher_orm = self.pool.get('account.voucher')
        pick = self.browse(cr, uid, record_id, context=context)

        # Refund to gift card on a voucher if a gift card was used, by default.
        if pick:
            if 'invoice_state' in fields:
                voucher_ids = voucher_orm.read(cr, uid, voucher_orm.search(cr, uid, [
                    ('rel_sale_order_id', '=', pick.sale_id.id), ('state', '=', 'posted'),
                    ('type', '=', 'receipt'), ('giftcard_id', '!=', False)
                ], order="id desc", context=context), context=context)

                if voucher_ids:
                    res['invoice_state'] = 'gc_refund'
                    res['giftcard_id'] = voucher_ids[0].giftcard_id
        return res

    def do_partial(self, cr, uid, ids, partial_data, context=None):
        """
        Refunds and zeroes out gift cards as necessary upon receipt of a gift card return.
        s
        """
        res = super(stock_picking, self).do_partial(cr, uid, ids, partial_data, context=context)
        if not res:
            return res

        giftcard_orm = self.pool.get("gift.card")

        for pick in self.browse(cr, uid, ids, context=context):
            # We only need to take action on incoming/returned stock.
            if pick.type == "out":
                continue

            # Not exactly sure what this does yet. Just aping the cc_api code. (TODO: Figure out why cc_api does this.)
            if (pick.type == 'in' and pick.invoice_state == 'gc_refund' and pick.voucher_id and
                pick.state == 'assigned' and not pick.backorder_id.id
            ):
                continue

            amount = 0.00
            lines = pick.move_lines

            if pick.backorder_id.id and pick.state=='assigned':
                lines = pick.backorder_id.move_lines

            for move in lines:
                # For every line in the sale order, grab the amount spent on that line (or the amount
                # left in the gift cards for that line) and tally it up for refunding to the gift card.
                if pick.sale_id:
                    partial_data = partial_data.get('move%s'%(move.id), {})
                    amount += refund_amount(pick.sale_id, move, partial_data.get('product_qty',0.0))

            # If there's some amount to refund, then refund it.
            if amount and pick.giftcard_id:
                giftcard_orm.write(cr, uid, pick.giftcard_id, {"balance": pick.giftcard_id.balance + amount})

        return res
stock_picking()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

   