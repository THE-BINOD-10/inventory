# -*- coding: utf-8 -*-
# from __future__ import unicode_literals

from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import auth
from django.views.decorators.csrf import csrf_exempt
from itertools import chain

from django.shortcuts import render
import datetime
from stockone_integrations.netsuite import netsuiteIntegration
from stockone_integrations.models import IntegrationMaster
import json,os
from miebach_admin.models import Integrations as integmodel
# Create your views here.

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
        # self.authenticationDict = auth_dict
        self.connectionObject = eval(class_to_initialize)(self.authenticationDict)

    def removeUnnecessaryData(self, skuDict):
        result = {}
        for key, value in skuDict.iteritems():
            if isinstance(value, (basestring, str, int, float)):
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


    def storeIntegrationDataForLaterUser(self, dataDict, recordType, unique_variable, action='upsert'):
        # currentData = self.getRelatedJson(recordType)
        # currentData.append(dataDict)
        self.writeJsonToFile(recordType, dataDict, unique_variable, action)

    def integrateSkuMaster(self, skuObject, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                self.storeIntegrationDataForLaterUser(skuObject, 'InventoryItem', unique_variable, action)
            else:
                for dataDict in skuObject:
                    dataDict = self.removeUnnecessaryData(dataDict)
                    self.storeIntegrationDataForLaterUser(dataDict, 'InventoryItem', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                recordDict = skuObject #self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'InventoryItem')
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in skuObject:
                    row = self.removeUnnecessaryData(row)
                    recordDict = row #self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'InventoryItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('InventoryItem', row)

    def integrateServiceMaster(self, skuObject, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                self.storeIntegrationDataForLaterUser(skuObject, 'ServicePurchaseItem', unique_variable, action)
            else:
                for dataDict in skuObject:
                    dataDict = self.removeUnnecessaryData(dataDict)
                    self.storeIntegrationDataForLaterUser(dataDict, 'ServicePurchaseItem', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in skuObject:
                    row = self.removeUnnecessaryData(row)
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'ServicePurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('ServicePurchaseItem', row)

    def integrateAssetMaster(self, skuObject, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                self.storeIntegrationDataForLaterUser(skuObject, 'NonInventoryPurchaseItem', unique_variable, action)
            else:
                for dataDict in skuObject:
                    dataDict = self.removeUnnecessaryData(dataDict)
                    self.storeIntegrationDataForLaterUser(dataDict, 'NonInventoryPurchaseItem', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in skuObject:
                    row = self.removeUnnecessaryData(row)
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('NonInventoryPurchaseItem', row)

    def integrateNonInventoryMaster(self, skuObject, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                self.storeIntegrationDataForLaterUser(skuObject, 'NonInventoryPurchaseItem', unique_variable, action)
            else:
                for dataDict in skuObject:
                    dataDict = self.removeUnnecessaryData(dataDict)
                    self.storeIntegrationDataForLaterUser(dataDict, 'NonInventoryPurchaseItem', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in skuObject:
                    row = self.removeUnnecessaryData(row)
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('NonInventoryPurchaseItem', row)

    def integrateOtherItemsMaster(self, skuObject, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                self.storeIntegrationDataForLaterUser(skuObject, 'NonInventoryPurchaseItem', unique_variable, action)
            else:
                for dataDict in skuObject:
                    dataDict = self.removeUnnecessaryData(dataDict)
                    self.storeIntegrationDataForLaterUser(dataDict, 'NonInventoryPurchaseItem', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                skuObject = self.removeUnnecessaryData(skuObject)
                recordDict = skuObject#self.gatherSkuData(skuObject)
                record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in skuObject:
                    row = self.removeUnnecessaryData(row)
                    recordDict = row#self.gatherSkuData(skuObject)
                    record = self.connectionObject.initiate_item(recordDict, 'NonInventoryPurchaseItem')
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('NonInventoryPurchaseItem', row)

    def IntegratePurchaseRequizition(self, prData, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(prData, 'PurchaseRequizition', unique_variable, action)
            else:
                for dataDict in prData:
                    self.storeIntegrationDataForLaterUser(dataDict, 'PurchaseRequizition', unique_variable, action)

        else:
            result = []
            if not is_multiple:
                recordDict = prData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_pr(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in prData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_pr(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('PurchaseRequizition', row)

    def IntegratePurchaseOrder(self, poData, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(poData, 'PurchaseOrder', unique_variable, action)
            else:
                for dataDict in poData:
                    self.storeIntegrationDataForLaterUser(dataDict, 'PurchaseOrder', unique_variable, action)

        else:
            result = []
            if not is_multiple:
                recordDict = poData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_po(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in poData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_po(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('PurchaseOrder', row)

    def IntegrateRTV(self, rtvData, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(rtvData, 'rtv', unique_variable, action)
            else:
                for dataDict in rtvData:
                    self.storeIntegrationDataForLaterUser(dataDict, 'rtv', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                recordDict = rtvData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_update_create_rtv(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in rtvData:
                    recordDict = row
                    record = self.connectionObject.netsuite_update_create_rtv(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('rtv', row)

    def IntegrateInventoryAdjustment(self, iaData, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(iaData, 'InventoryAdjustment', unique_variable, action)
            else:
                for dataDict in iaData:
                    self.storeIntegrationDataForLaterUser(dataDict, 'InventoryAdjustment', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                recordDict = iaData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_invadj(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in iaData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_invadj(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('InventoryAdjustment', row)

    def IntegrateInventoryTransfer(self, itData, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(itData, 'InventoryTransfer', unique_variable, action)
            else:
                for dataDict in itData:
                    self.storeIntegrationDataForLaterUser(dataDict, 'InventoryTransfer', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                recordDict = itData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_invtrf(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in itData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_invtrf(recordDict)
                    records.append(record)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('InventoryTransfer', row)


    def IntegrateGRN(self, grnData, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(grnData, 'grn', unique_variable, action)
            else:
                for dataDict in grnData:
                    self.storeIntegrationDataForLaterUser(dataDict, 'grn', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                recordDict = grnData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_grn(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in grnData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_grn(recordDict)
                    records.append(record)

                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('grn', row)

    def IntegrateUOM(self, uomData, unique_variable, is_multiple=False, action='upsert'):
        if not self.executebatch and Batched:
            if not is_multiple:
                self.storeIntegrationDataForLaterUser(uomData, 'uom', unique_variable, action)
            else:
                for dataDict in uomData:
                    self.storeIntegrationDataForLaterUser(dataDict, 'uom', unique_variable, action)
        else:
            result = []
            if not is_multiple:
                recordDict = uomData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_uom(recordDict)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
                return result
            else:
                records = []
                for row in uomData:
                    recordDict = row
                    record = self.connectionObject.netsuite_create_uom(recordDict)
                    records.append(record)

                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('uom', row)


    def getData(self, rec_type, internalId=None, externalId=None):
        return self.connectionObject.get_data(rec_type, internalId=internalId, externalId=externalId)
        

    def getRelatedJson(self, recordType, action='upsert'):
        rows = IntegrationMaster.objects.filter(
            user=self.userObject,
            integration_type=self.integration_type,
            module_type=recordType,
            action_type=action,
            status=False
        )
        data = []
        try:
            for row in rows:
                data.append(json.loads(row.integration_data))
            return data
        except Exception as e:
            return []

    def writeJsonToFile(self, recordType, data, unique_variable, action='upsert'):
        b = IntegrationMaster(
                user=self.userObject,
                integration_type=self.integration_type,
                module_type=recordType,
                action_type=action,
                integration_data=json.dumps(data),
                stockone_reference=data.get(unique_variable)
            )
        b.save()

    def markResults(self, recordType, data, action='upsert'):
        resultArr = IntegrationMaster.objects.filter(
                user=self.userObject,
                integration_type=self.integration_type,
                module_type=recordType,
                action_type=action,
                stockone_reference=data.externalId
            )
        status = True
        if hasattr(data, 'error'):
            status = False
        resultArr.update(
            integration_reference = data.internalId,
            status = status
        )
