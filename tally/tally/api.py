#!/usr/bin/env python

import exceptions
from tally_wrapper import TallyBridgeApp

class TallyBridgeApi(object):

    def __init__(self, **kwargs):
        self.dll_file = kwargs.get('dll')
        if not self.dll_file:
            print 'NOTE: you have to pass only file name not file path.'
            print 'NOTE: file should be kept in WMS_ANGULAR/tally/DLL/<your file>.dll'
            print 'CMD: python TallyBridgeApp.py -d <dll file name>'
            raise exceptions.DllFileNotPresentError
        self.bridge = TallyBridgeApp(dll=self.dll_file)

    def add_customer(self, **kwargs):
        resp = self.bridge.post_ledger(kwargs)
        return resp

    def add_vendor(self, **kwargs):
        resp = self.bridge.post_ledger(kwargs)
        return resp

    def add_item(self, **kwargs):
        resp = self.bridge.post_stock_item(kwargs)
        return resp

    def add_purchase_invoice(self, **kwargs):
        resp = self.bridge.post_sales_voucher(kwargs)

    def add_sales_invoice(self, **kwargs):
        pass

    def add_purchase_return(self, **kwargs):
        pass

    def add_sales_return(self, **kwargs):
        pass



# def Customer( tobj):
#     CustomerUrl = 'http://176.9.181.43:8778/rest_api/get_customer_data'
#     response = urllib2.urlopen(CustomerUrl)
#     xml = response.read()
#     sel = Selector(text=xml)
#     nodes = sel.xpath('//root/item/orders')
#     for node in nodes:
#         tallyCompanyName, ledgerName, updateOpeningBalance, ledgerMailingName, parentGroupName = node.xpath('.//text()').extract()
#         customerledgers = [{
#             'tallyCompanyName': tallyCompanyName,
#             'oldLedgerName': '',
#             'ledgerName': ledgerName,
#             'openingBalance': '',
#             'parentGroupName': parentGroupName,
#             'updateOpeningBalance': updateOpeningBalance ,
#             'ledgerMailingName': ledgerMailingName 
#         }]
#         print customerledgers
#         for ledgers in customerledgers:
#             tobj.PostLedger(**ledgers)
#     response.close() 