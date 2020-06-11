# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
import datetime
from stockone_integrations.netsuite import netsuiteIntegration
from stockone_integrations.models import IntegrationMaster
import json,os  
from miebach_admin.models import Integrations as integmodel
# Create your views here.

auth_dict = {
    'NS_ACCOUNT':'4120343_SB1',
    'NS_CONSUMER_KEY':'c1c9d3560fea16bc87e9a7f1428064346be5f1f28fb33945c096deb1353c64ea',
    'NS_CONSUMER_SECRET':'a28d1fc077c8e9f0f27c74c0720c7519c84a433f1f8c93bfbbfa8fea1f0b4f35',
    'NS_TOKEN_KEY':'e18e37a825e966c6e7e39b604058ce0d31d6903bfda3012f092ef845f64a1b7f',
    'NS_TOKEN_SECRET':'7e4d43cd21d35667105e7ea885221170d871f5ace95733701226a4d5fbdf999c'
}

Batched = True
TEMPFOLDER = '/tmp'

class Integrations():
    """docstring for Integrations"""
    def __init__(self, userObject, intType='netsuiteIntegration', executebatch=False):
        self.integration_type = intType
        self.userObject = userObject
        try:
            self.authenticationDict = self.get_auth_dict(userObject, intType)
            self.executebatch = executebatch
            self.initiateAuthentication()
            self.is_connected = True
        except Exception as e:
            self.is_connected = False


    def get_auth_dict(self, userObject, intType):
        respObj = integmodel.objects.get(user=userObject.id)
        return respObj.__dict__


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


    def storeIntegrationDataForLaterUser(self, dataDict, recordType, unique_variable):
        # currentData = self.getRelatedJson(recordType)
        # currentData.append(dataDict)
        self.writeJsonToFile(recordType, dataDict, unique_variable)

    def integrateSkuMaster(self, skuObject, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'InventoryItem', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'InventoryItem', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = skuObject #self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'InventoryItem')
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in skuObject:
                    recordDict = row #self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'InventoryItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('InventoryItem', row)

    def integrateServiceMaster(self, skuObject, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'ServicePurchaseItem', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'ServicePurchaseItem', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in skuObject:
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('ServicePurchaseItem', row)

    def integrateAssetMaster(self, skuObject, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'NonInventoryPurchaseItem', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'NonInventoryPurchaseItem', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in skuObject:
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('NonInventoryPurchaseItem', row)

    def integrateNonInventoryMaster(self, skuObject, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'NonInventoryPurchaseItem', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'NonInventoryPurchaseItem', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in skuObject:
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('NonInventoryPurchaseItem', row)

    def integrateOtherItemsMaster(self, skuObject, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'NonInventoryPurchaseItem', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'NonInventoryPurchaseItem', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in skuObject:
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('NonInventoryPurchaseItem', row)

    def IntegratePurchaseRequizition(self, prData, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'PurchaseRequizition', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'PurchaseRequizition', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = prData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_pr(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in prData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_pr(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('PurchaseRequizition', row)

    def IntegratePurchaseOrder(self, poData, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'PurchaseOrder', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'PurchaseOrder', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = poData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_po(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in poData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_po(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('PurchaseOrder', row)

    def IntegrateRTV(self, rtvData, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'rtv', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'rtv', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = rtvData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_update_create_rtv(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in rtvData:
                    recordDict = row
                    record = self.connectionObject.netsuite_update_create_rtv(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('rtv', row)

    def IntegrateGRN(self, grnData, unique_variable, is_multiple=False):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(skuObject, 'grn', unique_variable)
            else:
                for dataDict in skuObject:
                    self.storeIntegrationDataForLaterUser(dataDict, 'grn', unique_variable)
        else:
            result = []
            if not is_multiple:
                recordDict = prData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_grn(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple)
            else:
                records = []
                for row in grnData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_grn(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple)
            if len(result):
                for row in result:
                    self.markResults('grn', row)


    def getRelatedJson(self, recordType):
        rows = IntegrationMaster.objects.filter(
            user=self.userObject,
            integration_type=self.integration_type,
            module_type=recordType,
            status=False
        )
        data = []
        try:
            for row in rows:
                data.append(json.loads(row.integration_data))
            return data
        except Exception as e:
            return []

    def writeJsonToFile(self, recordType, data, unique_variable):
        b = IntegrationMaster(
                user=self.userObject,
                integration_type=self.integration_type,
                module_type=recordType,
                integration_data=json.dumps(data),
                stockone_reference=data.get(unique_variable)
            )
        b.save()

    def markResults(self, recordType, data):
        resultArr = IntegrationMaster.objects.filter(
                user=self.userObject,
                integration_type=self.integration_type,
                module_type=recordType,
                stockone_reference=data.externalId
            )
        resultArr.update(
            integration_reference = data.internalId,
            status = True
        )
