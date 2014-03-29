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

class Chinabank_Payment(payment.PayReceive):

    @http.httprequest
    def chinabank_return(self, req, **kwargs):
        ''' Chinabank 交易成功后将调用此函数，只需要简单地告诉用户支付成功即可以。
        return -- html 网页
        '''
        result = ''
        if req.params.get('v_pstatus', '')=='20':
            result = _(u'付款已经收妥，请返回订单页面刷新付款状态。')
        else:
            result = _(u'付款有问题，没有完成支付。')
        return self.process_return(req.params.get('remark1', ''), result)

    @http.httprequest
    def chinabank_notify(self, req, **kwargs):
        ''' 本函数会被 Chinabank 回调多次，先计算返回值的 md5, 再与返回的 md5 进行对比，
        确保数据没有被黑客篡改。'''

        result = "error"
        # 计算 md5 
        try:
            v_oid           = req.params.get('v_oid','')
            v_mid           = v_oid.split('-')[1]
            v_pstatus       = req.params.get('v_pstatus','')
            v_amount        = req.params.get('v_amount','')
            v_moneytype     = req.params.get('v_moneytype','')
            v_idx           = req.params.get('TranSerialNum','')
            v_md5str        = req.params.get('v_md5str','')
            remark1         = req.params.get('remark1','')
            record          = eval(remark1)
            
            dbname          = record["dbname"]
            registry        = RegistryManager.get(dbname)
            with registry.cursor() as cr:
                acquirer_pool   = registry.get('portal.payment.acquirer')
                acquirer_ids    = acquirer_pool.search(cr, openerp.SUPERUSER_ID, [('id','=',int(record['acqid']))])
                acquirer_obj    = acquirer_pool.browse(cr, openerp.SUPERUSER_ID, acquirer_ids)[0]
                key             = acquirer_obj.key or ''
                merchant_code   = acquirer_obj.merchant_code or ''

            if v_mid != merchant_code:
                return result

            md5text = v_oid + v_pstatus + v_amount + v_moneytype + key
            m = hashlib.md5()
            m.update(md5text)
            md5info = m.hexdigest().upper()

            if md5info != v_md5str:
                return result

            res = self.process_notify(remark1, v_amount, v_moneytype, v_mid)

            if not res.get("verified",False):
                return result
            
            # 数据校验完成，对数据进行归类、分析、保存等进一步处理
            if v_pstatus=="20":
                self.process_trans(res, v_moneytype, float(v_amount), v_idx, **kwargs)

            result = 'ok'
        except Exception:
            return result

        return result

    @http.httprequest
    def chinabank_cancel(self, req, **kwargs):
        return "<html><head><body><p>%s</p></body></head></html>" % _(u'付款已取消，您没有支付成功。')

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
