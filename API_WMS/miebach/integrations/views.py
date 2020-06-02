# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import datetime
from integrations.netsuite import netsuiteIntegration
# Create your views here.

auth_dict = {
    'NS_ACCOUNT':'4120343_SB1',
    'NS_CONSUMER_KEY':'c1c9d3560fea16bc87e9a7f1428064346be5f1f28fb33945c096deb1353c64ea',
    'NS_CONSUMER_SECRET':'a28d1fc077c8e9f0f27c74c0720c7519c84a433f1f8c93bfbbfa8fea1f0b4f35',
    'NS_TOKEN_KEY':'e18e37a825e966c6e7e39b604058ce0d31d6903bfda3012f092ef845f64a1b7f',
    'NS_TOKEN_SECRET':'7e4d43cd21d35667105e7ea885221170d871f5ace95733701226a4d5fbdf999c'
}

class Integrations():
    """docstring for Integrations"""
    def __init__(self, intType='netsuiteIntegration', authenticationDict={}):
        self.integration_type = intType
        self.authenticationDict = auth_dict

    def initiateAuthentication(self):
        class_to_initialize = self.integration_type
        self.connectionObject = eval(class_to_initialize)(self.authenticationDict)


    def removeUnnecessaryData(self, skuDict):
        result = {}
        for key, value in skuDict.iteritems():
            if isinstance(value, (basestring, str, int, float, datetime.datetime)):
                result[key] = value
            else:
                continue

        return result

    def gatherSkuData(self, skuObject):
        skuDict = skuObject.__dict__
        skuDict = self.removeUnnecessaryData(skuDict)
        skuAttributesList = list(skuObject.skuattributes_set.values('attribute_name', 'attribute_value'))
        skuAttributes = {}
        for row in skuAttributesList:
            skuAttributes[row.get('attribute_name')] = row.get('attribute_value')
        skuDict.update(skuAttributes)
        return skuDict

    def integrateSkuMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = skuObject #self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'InventoryItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = skuObject #self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'InventoryItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def integrateServiceMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = skuObject#self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = row#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def integrateAssetMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = skuObject#self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = row#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def integrateNonInventoryMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = skuObject#self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = row#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def integrateOtherItemsMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = skuObject#self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = row#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)


    def IntegratePurchaseRequizition(self, prData, is_multiple=False):
        if not is_multiple:
            recordDict = prData #self.gatherSkuData(skuObject)
            record = self.connectionObject.netsuite_create_pr(recordDict)
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in prData:
                recordDict = row
                record = self.connectionObject.netsuite_create_pr(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def IntegratePurchaseOrder(self, poData, is_multiple=False):
        if not is_multiple:
            recordDict = poData #self.gatherSkuData(skuObject)
            record = self.connectionObject.netsuite_create_po(recordDict)
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in poData:
                recordDict = row
                record = self.connectionObject.netsuite_create_po(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)


    def IntegrateRTV(self, rtvData, is_multiple=False):
        if not is_multiple:
            recordDict = rtvData #self.gatherSkuData(skuObject)
            record = self.connectionObject.netsuite_update_create_rtv(recordDict)
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in rtvData:
                recordDict = row
                record = self.connectionObject.netsuite_update_create_rtv(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def IntegrateGRN(self, grnData, is_multiple=False):
        if not is_multiple:
            recordDict = prData #self.gatherSkuData(skuObject)
            record = self.connectionObject.netsuite_create_grn(recordDict)
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in grnData:
                recordDict = row
                record = self.connectionObject.netsuite_create_grn(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)
        
        
        