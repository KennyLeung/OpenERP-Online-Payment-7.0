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
from urllib import quote as quote
from openerp.osv import osv, fields
from openerp.tools.translate import _
import hashlib

import logging
_logger = logging.getLogger(__name__)
# try:
#     from mako.template import Template as MakoTemplate
# except ImportError:
#     _logger.warning("payment_acquirer: mako templates not available, payment acquirer will not work!")


class acquirer(osv.Model):
    _inherit = 'portal.payment.acquirer'
    _columns = {
        'internal_name': fields.char('Internal Name'),
        'form_template': fields.text('Payment form template (HTML)', required=True), 
        'merchant_code': fields.char('Merchant Code'),
        'appid': fields.char('App ID'),
        'key': fields.char('Key'),
        'url_payment': fields.char('Payment Url'),
        'url_return': fields.char('Front Return Url'),
        'url_notify': fields.char('Backend Notify Url'),
        'url_cancel': fields.char('Cancel Payment Url'),
        'sequence': fields.integer('Sequence'),
    }
    _order = 'sequence'


    def render_payment_block(self, cr, uid, object, reference, currency, amount, context=None, **kwargs):
        ''' Before render payment block, do something else, add some parameters to context etc.'''
        acquirer_ids = self.search(cr, uid, [('visible', '=', True)])
        if not acquirer_ids:
            return
        
        context.update({'currency': currency.name or '', 'amount': '%0.2f' % amount})
        html_forms = []
        for this in self.browse(cr, uid, acquirer_ids):
            context.update({'payment_url': this.url_payment or '', 'acquirer_id': '%d' % this.id,})

            # 添加专用参数
            res = self.pool.get(self._name + "." + this.internal_name).get_render_params(cr, uid, this.id, context=context)
            context.update(res)  

            # 生成 token
            v1 = context.get("amount", "")
            v2 = currency.name or ""
            v3 = this.merchant_code or ""
            v4 = this.key or ""
            v5 = context.get("dbname", "")
            v6 = context.get("model", "")
            v7 = context.get("id", "")
            v8 = context.get("acquirer_id", "")
            token_text = v1 + v2 + v3 + v4 + v5 + v6 + v7 + v8
            md = hashlib.md5()
            md.update(token_text)
            token = md.hexdigest().upper()

            # 数据库记录参数
            record = {"dbname": context.get("dbname", ""), "model": context.get("model", ""), 
                "id": context.get("id", ""), "acqid": context.get("acquirer_id", ""), "token": token}

            context.update({"record": str(record).replace(" ","")})

            content = this.render(object, reference, currency, amount, context=context, **kwargs)
            if content:
                html_forms.append(content)
        html_block = '\n'.join(filter(None,html_forms))
        return self._wrap_payment_block(cr, uid, html_block, amount, currency, context=context)  
        
