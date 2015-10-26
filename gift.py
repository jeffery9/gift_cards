import re, time
from helpers.shortuuid import uuid
from openerp.osv import fields, osv
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT

class config(osv.osv):
    def _name(self, cr, uid, ids, field_name, arg, context=None):
        return dict([(config.id, {'name': config.company_id.name})
                     for config in self.browse(cr, uid, ids, context=context)])

    _name = "gift.card.config"
    _columns = {
        'name': fields.char('Name', size=128),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'gift_card_journal_id': fields.many2one('account.journal', 'Gift Card Journal', required=True),
        'liability_account_id': fields.many2one('account.account', 'Liability Account', required=True),
        'redemption_account_id': fields.many2one('account.account', 'Redemption Account', required=True)
    }
    _sql_constraints = [
        ('company_unique', 'unique(company_id)', 'Configuration already exists for this company!')
    ]

    def onchange_company_id(self, cr, uid, ids, company_id, context=None):
        company = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
        return {'value': {'name': company.name}}

class card(osv.osv):
    """Represents a gift card in the system."""
    _name = "gift.card"
    _rec_name = "number"

    def _last_four_number(self, cr, uid, ids, name, arg, context=None):
        res = {}
        for id in ids:
            number = self.browse(cr, uid, id, context=None).number
            print number
            try:
                res[id] = '**** **** **** ' + number[-4:]
            except:
                res[id] = 'Bad Number'
        return res

    _columns = {
        'number': fields.char('Card Number', size=19),
        'balance': fields.float('Balance'),#, readonly=True),
        'voucher_ids': fields.one2many('account.voucher', 'giftcard_id', 'Vouchers', readonly=True),
        'sale_order_line_id': fields.many2one('sale.order.line', 'Order Line', readonly=True),
        'order_id': fields.many2one('sale.order', 'Sale Order', help="Sale order the gift card was bought with",
                                    readonly=True),
        'email_recipient': fields.char('Recipient Email', size=128),
        'email_date': fields.date('Email After'),
        'email_sent': fields.boolean('Email Sent?', readonly=1),
        'note': fields.text('Certificate Note'),
        'date_purchase': fields.date('Date Purchased', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Purchaser', readonly=True),
        'init_amount': fields.float('Initial Amount', readonly=True),
        'last_four_number': fields.function(_last_four_number, string='Last Four of Card', type='char', store=False)
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

    def get_config(self, cr, uid, context=None):
        # Grab the gift card configuration for this company.
        company_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
        config_pool = self.pool.get('gift.card.config')
        config = config_pool.browse(cr, uid, config_pool.search(cr, uid, [('company_id', '=', company_id)]))

        if not bool(config):
            raise Exception('Could not find a gift card configuration for your company!')

        return config[0]

    def create_liability_move(self, cr, uid, ids, context=None):
        accounts = {}
        config = self.get_config(cr, uid, context=context)
        to_account = config.liability_account_id

        for card in self.browse(cr, uid, ids, context=context):
            from_account_id = card.sale_order_line_id.product_id.property_account_income.id \
                           or card.sale_order_line_id.product_id.categ_id.property_account_income_categ.id
            accounts[from_account_id] = accounts.get(from_account_id, 0) + card.balance

        move_id = self.create_move(cr, uid, config.gift_card_journal_id.id, config.company_id.id, context=context)

        account_pool = self.pool.get('account.account')
        for account_id, amount in accounts.iteritems():
            from_account = account_pool.browse(cr, uid, account_id, context=context)
            currency_id = from_account.currency_id.id
            self.create_move_lines(cr, uid,move_id, name="Gift Card Creation", amount=amount,
                                   to_account=to_account.id, from_account=from_account.id, context=context)

        return move_id

    def create_sale_refund_move(self, cr, uid, ids, context=None):
        accounts = {}
        config = self.get_config(cr, uid, context=context)
        from_account = config.liability_account_id

        for card in self.browse(cr, uid, ids, context=context):
            to_account_id = card.sale_order_line_id.product_id.property_account_income.id \
                           or card.sale_order_line_id.product_id.categ_id.property_account_income_categ.id
            accounts[to_account_id] = accounts.get(to_account_id, 0) + card.balance

        move_id = self.create_move(cr, uid, config.gift_card_journal_id.id, config.company_id.id, context=context)

        account_pool = self.pool.get('account.account')
        for account_id, amount in accounts.iteritems():
            to_account = account_pool.browse(cr, uid, account_id, context=context)
            currency_id = to_account.currency_id.id
            self.create_move_lines(cr, uid,move_id, name="Gift Card Refund", amount=amount,
                                   to_account=to_account.id, from_account=from_account.id, context=context)

        return move_id

    def create_redemption_move(self, cr, uid, amount, context=None):
        config = self.get_config(cr, uid, context=context)
        move_id = self.create_move(cr, uid, config.gift_card_journal_id.id, config.company_id.id, context=context)
        account_pool = self.pool.get('account.account')
        to_account = account_pool.browse(cr, uid, config.redemption_account_id, context=context)
        currency_id = to_account.currency_id.id
        self.create_move_lines(cr, uid, move_id, name='Gift Card Use', amount=amount,
                               to_account=config.redemption_account_id, from_account=config.liability_account_id,
                               context=context)
        return move_id

    def create_refund_move(self, cr, uid, amount, context=None):
        config = self.get_config(cr, uid, context=context)
        move_id = self.create_move(cr, uid, config.gift_card_journal_id.id, config.company_id.id, context=context)
        account_pool = self.pool.get('account.account')
        to_account = account_pool.browse(cr, uid, config.liability_account_id, context=context)
        currency_id = to_account.currency_id.id
        self.create_move_lines(cr, uid, move_id, name='Refund to Gift Card', amount=amount,
                               to_account=config.liability_account_id, from_account=config.redemption_account_id,
                               context=context)
        return move_id

    def create_move(self, cr, uid, journal_id, company_id, context=None):
        # Move the spent balance out of our gift card liabilities.
        move_pool = self.pool.get('account.move')
        move_dict = move_pool.account_move_prepare(
            cr, uid, journal_id=journal_id, company_id=company_id, context=context)
        return move_pool.create(cr, uid, move_dict, context=context)

    def create_move_lines(self, cr, uid, move_id, name='Gift Card', amount=None,
                          to_account=None, from_account=None, context=None):

        account_pool = self.pool.get('account.account')
        to_account_obj = account_pool.browse(cr, uid, to_account, context=context)
        to_currency_id = to_account_obj.currency_id.id
        from_account_obj = account_pool.browse(cr, uid, from_account, context=context)
        from_currency_id = from_account_obj.currency_id.id

        line_pool = self.pool.get('account.move.line')
        line_pool.create(cr, uid, {
            'name': name,
            'quantity': 1,
            'account_id': from_account,
            'move_id': move_id,
            'debit': amount,
            # 'currency_id': from_currency_id,
            # 'amount_currency': amount
        }, context=context)
        line_pool.create(cr, uid, {
            'name': name,
            'quantity': 1,
            'account_id': to_account,
            'move_id': move_id,
            'credit': amount,
            # 'currency_id': to_currency_id,
            # 'amount_currency': amount
        }, context=context)

card()
