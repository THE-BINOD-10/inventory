# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import datetime
from integrations.netsuite import netsuiteIntegration
# Create your views here.

class Integrations():
    """docstring for Integrations"""
    def __init__(self, intType='netsuiteIntegration', authenticationDict={}):
        self.integration_type = intType
        self.authenticationDict = authenticationDict

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
            recordDict = self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def integrateAssetMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def integrateNonInventoryMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)

    def integrateOtherItemsMaster(self, skuObject, is_multiple=False):
        if not is_multiple:
            recordDict = self.gatherSkuData(skuObject)
            record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
            self.connectionObject.complete_transaction(record, is_multiple)
        else:
            records = []
            for row in skuObject:
                recordDict = self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                records.append(record)
            self.connectionObject.complete_transaction(records, is_multiple)




            
        
        
        