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
import openerp.addons.payment_base.controllers.main as payment
import hashlib
from openerp.modules.registry import RegistryManager
import openerp
import time
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

class Paypal_Payment(payment.PayReceive):

    @http.httprequest
    def paypal_return(self, req, **kwargs):
        ''' Paypal 交易成功后将调用此函数，只需要简单地告诉用户支付成功即可以。
        return -- html 网页
        '''
        result = ''
        if req.params.get('st', False)=='Completed':
            result = _(u'付款已经收妥，请返回订单页面刷新付款状态。')
        else:
            result = _(u'付款有问题，没有完成支付。')
        return self.process_return(req.params.get('cm', ''), result)

    @http.httprequest
    def paypal_notify(self, req, **kwargs):
        ''' 本函数会被 Paypal 回调多次，Paypal 要求原样返回数据进行校验，
        以确保数据没有被黑客篡改。'''

        result = ""
        res = self.process_notify(req.params.get("custom", False), req.params.get('payment_gross', ''),
            req.params.get('mc_currency',''), req.params.get('receiver_id',''))
        if not res.get("verified",False):
            return result
        
        url = False
        dbname = res["dbname"]
        registry = RegistryManager.get(dbname)
        with registry.cursor() as cr:
            acquirer_pool = registry.get('portal.payment.acquirer')
            acquirer_ids = acquirer_pool.search(cr, openerp.SUPERUSER_ID, [('id','=',int(res['acqid']))])
            acquirer_obj = acquirer_pool.browse(cr, openerp.SUPERUSER_ID, acquirer_ids)[0]
            url = acquirer_obj.url_payment
            merchant_code = acquirer_obj.merchant_code

            paypal_account = registry.get(res['model']).browse(cr, openerp.SUPERUSER_ID, int(res['id'])).company_id.paypal_account

        if not url:
            return result

        # prepares provided data set to inform PayPal we wish to validate the response
        data = req.params
        data["cmd"] = "_notify-validate"
        params = urlencode(data)
     
        # sends the data and request to the PayPal
        req = Request(url, params)
        req.add_header("Content-type", "application/x-www-form-urlencoded")
        # reads the response back from PayPal
        response = urlopen(req)
        status = response.read()

        # If not verified
        if not status == "VERIFIED":
            return result

        # if not the correct receiver email
        if not data["receiver_email"] == paypal_account:
            return result
        
        # if not the correct receiver ID
        if not data["receiver_id"] == merchant_code:
            return result
        
        # if not completed
        if not data["payment_status"] == 'Completed':
            return result
        
        # 数据校验完成，对数据进行归类、分析、保存等进一步处理
        self.process_trans(res, data.get('mc_currency', ''), float(data.get('payment_gross', '')), 
            data.get('txn_id', ''), **kwargs)
        return result

    @http.httprequest
    def paypal_cancel(self, req, **kwargs):
        return "<html><head><body><p>%s</p></body></head></html>" % _(u'付款已取消，您没有支付成功。')

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
