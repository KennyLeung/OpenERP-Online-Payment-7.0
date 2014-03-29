# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2001-2014 Zhuhai sunlight software development co.,ltd. All Rights Reserved.
#    Author: Kenny
#    Website: http://zhsunlight.cn
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import osv, fields
import time

class sale_order(osv.Model):
    _inherit = 'sale.order'

    _columns = {
        'payment_state': fields.selection([('uncertain', 'Uncertain'), ('unpaid', 'Unpaid'),
            ('exception', 'Exception'),('completed', 'Completed')], 'Payment Status', readonly=True,
                help='Payment Status'),
        'acquirer_id': fields.many2one('portal.payment.acquirer','Acquirer', readonly=True),
        'payment_currency': fields.char('Payment Currency', readonly=True),
        'payment_amount': fields.float('Payment Amount', readonly=True),
        'payment_transaction': fields.char('Payment Transaction No.', readonly=True),
        'payment_date': fields.datetime('Payment Date', readonly=True),
        'payment_note': fields.char('Payment Note', readonly=True),
    }

    _defaults = {
        'payment_state': 'unpaid',
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)

        # # 限制只有客户亲自登录才显示支付按钮
        # if not self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.customer:
        #     return result

        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.state not in ('draft', 'cancel') and not this.invoiced and \
                this.payment_state not in ('completed', 'exception'):
                # 增加一些参数到 context
                context.update({'date': this.date_order,
                    'code': this.name, 'model': self._name,
                    'dbname':cr.dbname, 'id': '%d' % this.id})
                result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.name,
                    this.pricelist_id.currency_id, this.amount_total, context=context)
                # result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.name,
                #     this.pricelist_id.currency_id, this.amount_total, context=context)
        return result



class account_invoice(osv.Model):
    _inherit = 'account.invoice'
    _columns = {
        'payment_state': fields.selection([('uncertain', 'Uncertain'), ('unpaid', 'Unpaid'),
            ('exception', 'Exception'),('completed', 'Completed')], 'Payment Status', readonly=True,
                help='Payment Status'),
        'acquirer_id': fields.many2one('portal.payment.acquirer','Acquirer', readonly=True),
        'payment_currency': fields.char('Payment Currency', readonly=True),
        'payment_amount': fields.float('Payment Amount', readonly=True),
        'payment_transaction': fields.char('Payment Transaction No.', readonly=True),
        'payment_date': fields.datetime('Payment Date', readonly=True),
        'payment_note': fields.char('Payment Note', readonly=True),
    }

    _defaults = {
        'payment_state': 'unpaid',
    }

    def _portal_payment_block(self, cr, uid, ids, fieldname, arg, context=None):
        result = dict.fromkeys(ids, False)

        # # 限制只有客户亲自登录才显示支付按钮
        # if not self.pool.get('res.users').browse(cr, uid, uid, context=context).partner_id.customer:
        #     return result

        payment_acquirer = self.pool.get('portal.payment.acquirer')
        for this in self.browse(cr, uid, ids, context=context):
            if this.type == 'out_invoice' and this.state not in ('draft', 'done') and not this.reconciled \
                and this.payment_state not in ('completed', 'exception'):
                # 增加一些参数到 context
                context.update({'date': this.date_invoice,
                    'code': this.number, 'model': self._name,
                    'dbname':cr.dbname, 'id': '%d' % this.id})
                result[this.id] = payment_acquirer.render_payment_block(cr, uid, this, this.number,
                    this.currency_id, this.residual, context=context)
        return result

