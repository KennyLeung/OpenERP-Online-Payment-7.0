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
from openerp.tools.translate import _
import hashlib
import time

class Chinabank_acquirer(osv.Model):
    _name = "portal.payment.acquirer.chinabank"
    _inherit = "portal.payment.acquirer"
    _table = "portal_payment_acquirer"
    _description = "Chinabank Payment"
    _defaults = {
        'name': 'Chinabank',
        'internal_name': 'chinabank',
    }

    def get_render_params(self, cr, uid, id, context=None, **kwargs):
        ''' 获取与本支付方式对应的表单（form）的专用参数。'''
        res = {}
        this = self.browse(cr, uid, id, context=context)

        v_mid = this.merchant_code or ""
        orderno = time.strftime('%Y%m%d' ,time.strptime(context.get('date',''),'%Y-%m-%d')) + \
                '-' + v_mid + '-' + context.get('code','')
        v_amount = context.get('amount', '')
        v_moneytype = context.get('currency', '')
        v_url = this.url_return or ""
        key = this.key or ""

        md5text = v_amount + v_moneytype + orderno + v_mid + v_url + key
        m = hashlib.md5()
        m.update(md5text)
        md5info = m.hexdigest().upper()

        res.update({
            'v_oid': orderno,
            'v_mid': v_mid, 
            'v_url': v_url ,
            'v_md5info': md5info,
            'remark2': '[url:=' + (this.url_notify or '') + ']',
            })
        return res
