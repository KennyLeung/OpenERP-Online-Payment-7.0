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
#    License, or (at your option) any later version
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from urllib import urlencode
from urllib2 import urlopen, Request
import openerp.addons.web.http as http
import openerp.addons.web.controllers.main as webmain
import hashlib
from openerp.modules.registry import RegistryManager
import openerp
import time
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

class PayReceive(http.Controller):
    _cp_path = "/online_payment"

    def process_notify(self, data, amount, currency, merchant_code):
        ''' 获取后台传回的交易数据并校验其正确性。
        data:传入的数据，格式-- 数据库;单据标识:ID值
        例如： "{'model': 'sale.order', 'dbname': 'samples', 'token': 'D2F483A70913D042124635C2CCF06144', 'id': '30'}"
        返回：分离后的数据'''

        res = {'verified': False}
        try:
            record = eval(data)
            registry = RegistryManager.get(record.get('dbname', ''))
            with registry.cursor() as cr:
                acquirer_pool = registry.get('portal.payment.acquirer')
                acquirer_ids = acquirer_pool.search(cr, openerp.SUPERUSER_ID, [('id','=',int(record.get('acqid','')))])
                acquirer_obj = acquirer_pool.browse(cr, openerp.SUPERUSER_ID, acquirer_ids)[0]
                key = acquirer_obj.key or ""

                # 生成 token，必须与交易前传递的 token 算法一致
                v1 = '%0.2f' % float(amount)
                v2 = currency
                v3 = merchant_code
                v4 = key
                v5 = record.get("dbname", "")
                v6 = record.get("model", "")
                v7 = record.get("id", "")
                v8 = record.get("acqid", "")
                token_text = v1 + v2 + v3 + v4 + v5 + v6 + v7 + v8
                md = hashlib.md5()
                md.update(token_text)
                token = md.hexdigest().upper()

                if token == record.get('token', ''):
                    res.update({'verified': True})
                    res.update(record)
        except Exception:
            res.update({'verified': False})

        return res


    def process_return(self, data, result):
        ''' 分析处理前台返回的数据，主要是大致分析交易结果，返回原来的单据给用户查看。'''

        try:
            res = eval(data)
            dbname      = res.get("dbname", "")
            obj_name    = res.get("model", "")
            oid         = res.get("id", "")

            registry = RegistryManager.get(dbname)
            with registry.cursor() as cr:
                url = registry.get('ir.config_parameter').get_param(cr, openerp.SUPERUSER_ID, 'web.base.url', 'http://localhost')

            url += '/?db=%s' % dbname + '#id=%s' % oid + '&model=%s' % obj_name
            ret = "<html><head><meta http-equiv='refresh' content='0;URL=%s'></head></html>" % url
            # ret = "<html><head><script>window.location.href='%s';</script></head></html>" % url
        except Exception:
            ret = "<html><head><body><p>%s</p></body></head></html>" % result

        return ret


    def process_trans(self, record, payment_currency, payment_amount, payment_transaction, **kwargs):
        ''' 处理交易数据，分析交易结果，对关键交易数据进行保存。'''

        dbname                  = record.get('dbname', '')
        model_name              = record.get('model', '')
        oid                     = record.get('id', '')
        acquirer_id             = int(record.get('acqid', ''))

        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            trans_pool = registry.get(model_name)
            trans_obj = trans_pool.browse(cr, openerp.SUPERUSER_ID, int(oid))
            if not trans_obj:
                return False

            payment_state = 'uncertain'
            note = ''
            if model_name == 'sale.order':
                if trans_obj.pricelist_id.currency_id.name == payment_currency and payment_amount == trans_obj.amount_total:
                    payment_state = 'completed'

                if trans_obj.pricelist_id.currency_id.name != payment_currency:
                    payment_state = 'exception'
                    note += u'货币与待付单据不一致。'

            if model_name == 'account.invoice':
                if trans_obj.currency_id.name == payment_currency and payment_amount == trans_obj.amount_total:
                    payment_state = 'completed'

                if trans_obj.currency_id.name != payment_currency:
                    payment_state = 'exception'
                    note += u'货币与待付单据不一致。'


            # 以下对 sale.order 和 account.invoice 均适用
            if payment_amount != trans_obj.amount_total:
                payment_state = 'exception'
                note += u'付款金额与待付单据不一致。'

            if trans_obj.payment_transaction and payment_transaction != trans_obj.payment_transaction:
                payment_state = 'exception'
                note += trans_obj.payment_note + u'交易单号与先前不一致，疑似重复付款：' + trans_obj.payment_transaction + ';'

            ord_ids = trans_pool.search(cr, openerp.SUPERUSER_ID, [('payment_transaction','=',payment_transaction)])
            if not (len(ord_ids) == 0 or len(ord_ids) == 1 and ord_ids[0] == trans_obj.id):
                payment_state = 'exception'
                note += u'此交易号先前已经使用，此次付款可疑：' + payment_transaction + ';' 

            trans_obj.write({'payment_state': payment_state, 'acquirer_id': acquirer_id, 
                'payment_currency': payment_currency, 'payment_amount': payment_amount, 
                'payment_transaction': payment_transaction, 'payment_date': time.strftime('%Y-%m-%d %H:%M:%S'), 
                'payment_note': note})

        return True


# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
