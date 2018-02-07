#!/usr/bin/env python
from flask import Flask, request
app = Flask(__name__)
import common_exceptions
import traceback
from tally_wrapper import TallyBridgeApp
bridge = TallyBridgeApp(dll="C:\\Users\\stockone\\TallySetup\\WMS_ANGULAR\\tally\\tally\\DLL\\TallyBridgeDll.dll")
#bridge = TallyBridgeApp(dll="C:\\Users\\stockone\\Desktop\\TallyBridgeDll\\bin\\Release\\TallyBridgeDll.dll")

data = { 'ledger_name': 'samsahd',
'sku_code': 'dcscddsd',
'unit_name': 'inr',
'stock_group_name': 'M1',
'stock_category_name':'da',
'opening_qty':2,
'opening_rate':2,
'opening_amt':1,
'tally_company_name': 'Mieone',
'dll': 'C:\\Users\\stockone\\TallySetup\\WMS_ANGULAR\\tally\\tally\\DLL\\TallyBridgeDll.dll',
'ledger_alias':'sam121',
'parent_group_name':'SW',
'state':'INDIA'}
import json
def parse_request(request):
    return {i: j for i, j in request.form.iteritems()}
@app.route('/AddCustomer/', methods=['POST'])
def add_customer(**kwargs):
    for obj in json.loads(request.form.get('data', [{}])):
        try:
            bridge.customer_and_vendor_master(obj)
        except:
            print traceback.format_exc()
            return traceback.format_exc()

@app.route('/AddVendor/', methods=['POST'])
def add_vendor(**kwargs):
    for obj in json.loads(request.form.get('data', [{}])):
        try:
            print obj
            return bridge.customer_and_vendor_master(obj)
        except:
            return traceback.format_exc()

@app.route('/AddItem/', methods=['POST'])
def add_item(**kwargs):
    for obj in json.loads(request.form.get('data', [{}])):
        try:
            return bridge.item_master(obj)
        except:
            return traceback.format_exc()

@app.route('/AddPurchaseInvoice/', methods=['POST'])
def add_purchase_invoice(**kwargs):
    for obj in json.loads(request.form.get('data', [{}])):
        try:
            return bridge.post_sales_voucher(parse_request(request))
        except:
            return traceback.format_exc()

@app.route('/AddSalesInvoice/', methods=['POST'])
def add_sales_invoice(**kwargs):
    for obj in json.loads(request.form.get('data', [{}])):
        try:
            return bridge.sales_invoice(obj)
        except:
            return traceback.format_exc()

@app.route('/AddPurchaseReturn/', methods=['POST'])
def add_purchase_return(**kwargs):
    for obj in json.loads(request.form.get('data', [{}])):
        try:
            return bridge.purchase_returns(obj)
        except:
            return traceback.format_exc()

@app.route('/AddSalesReturn/', methods=['POST'])
def add_sales_return(**kwargs):
    for obj in json.loads(request.form.get('data', [{}])):
        try:
            return bridge.sales_returns(obj)
        except:
            return traceback.format_exc()


#print add_vendor(**data)
print data
data = bridge.item_master({u'unit_name': u'', u'opening_qty': u'', u'item_name': u'Pollo cotton white T-shirt', u'tally_company_name': u'',
        u'sku_code': u'1', u'opening_amt': 0, u'opening_rate': 0.0, u'stock_group_name': u'', u'stock_category_name': u'',
        'parent_group_name': 'cshdjc', 'ledger_name': 'sandhani', 'state': 'IN', 'ledger_alias': 'asd'})
print(bridge.customer_and_vendor_master(data))


