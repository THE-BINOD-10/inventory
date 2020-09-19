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
from utils import init_logger
log_err = init_logger('logs/netsuite_integration_View_errors.log')

actual_date=["14-24032-000000043","14-24032-000000045","14-28050-000000016","14-29009-000000073","14-29009-000000074","14-29009-000000075","14-33004-000000261","14-33004-000000262","14-33004-000000263","14-33004-000000264","14-33004-000000265","14-33004-000000266","14-33004-000000267","14-33004-000000268","14-33004-000000269","14-33004-000000270","14-33004-000000271","14-33004-000000272","14-33004-000000273","14-33004-000000274","14-33004-000000275","14-33004-000000276","14-33004-000000277","14-33004-000000278","14-33004-000000279","14-33004-000000280","14-33004-000000281","14-33004-000000282","14-33004-000000283","14-33004-000000284","14-33033-000000007","14-33033-000000008","14-33033-000000009","14-33036-000000014","14-33036-000000015","14-33061-000000015","14-33061-000000016","14-33066-000000010","14-33066-000000011","14-33066-000000012","14-33091-000000014","14-33091-000000015","14-33091-000000016","14-36053-000000015","14-36053-000000016","14-36053-000000017","14-36053-000000018","14-37064-000000010","17-33004-000000001","43-29005-000000113","43-29005-000000114","43-29005-000000115","43-29005-000000116","43-29005-000000117","43-29005-000000118","43-29005-000000119","43-29005-000000120","43-29005-000000121","43-29005-000000122","43-29005-000000123","43-29005-000000124","43-29005-000000125","43-29005-000000126","43-29005-000000127","43-29005-000000128","43-29005-000000129","43-29005-000000130","43-29005-000000131","43-29005-000000132","43-29005-000000133","43-29005-000000134","43-29005-000000135","43-29005-000000136","43-29005-000000137"]

do_not_integrate=["14-10076-000000023","14-10076-000000024","14-10076-000000025","14-10076-000000026","14-10076-000000027","14-19065-000000028","14-19065-000000029","14-24032-000000044","43-27020-000000024"]

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
        # skuAttributesList = list(skuObject.skuattributes_set.values('attribute_name', 'attribute_value'))
        # skuAttributes = {}
        # for row in skuAttributesList:
        #     skuAttributes[row.get('attribute_name')] = row.get('attribute_value')
        # skuDict.update(skuAttributes)
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
                    self.markResults('InventoryItem', row, action)

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
                    self.markResults('ServicePurchaseItem', row, action)

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
                    self.markResults('NonInventoryPurchaseItem', row, action)

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
                    self.markResults('NonInventoryPurchaseItem', row, action)

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
                    self.markResults('NonInventoryPurchaseItem', row, action)

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
                    self.markResults('PurchaseRequizition', row, action)

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
                    self.markResults('PurchaseOrder', row, action)

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
                    self.markResults('rtv', row, action)

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
                    self.markResults('InventoryAdjustment', row, action)

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
                    self.markResults('InventoryTransfer', row, action)


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
                if action  == 'upsert':
                    if grnData.get('items',[]):
                        if int(grnData["grn_date"].split('-')[1])==9:
                            grnData.update({"grn_date": '2020-08-31T19:33:52+05:30'})
                recordDict = grnData #self.gatherSkuData(skuObject)
                record = self.connectionObject.netsuite_create_grn(recordDict)
                if action  == 'upsert':
                    po_initialize= self.connectionObject.complete_transaction([record], True, "initialize")
                    record= self.match_itemlist_data([record], po_initialize, is_multiple)
                result = self.connectionObject.complete_transaction(record, is_multiple, action)
            else:
                records = []
                for row in grnData:
                    if row.get("grn_number",'') in do_not_integrate:
                        continue
                    if action  =='upsert' and row.get("grn_number",'') not in actual_date:
                        if row.get('items',[]):
                            if int(row["grn_date"].split('-')[1])==9:
                                row.update({"grn_date": '2020-08-31T19:33:52+05:30'})
                    recordDict = row
                    record = self.connectionObject.netsuite_create_grn(recordDict)
                    records.append(record)
                if action  =='upsert':
                    po_initialize= self.connectionObject.complete_transaction(records, True, "initialize")
                    records= self.match_itemlist_data(records, po_initialize, is_multiple)
                result = self.connectionObject.complete_transaction(records, is_multiple, action)
            if len(result):
                for row in result:
                    self.markResults('grn', row, action)

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
                    self.markResults('uom', row, action)


    def getData(self, rec_type, internalId=None, externalId=None):
        return self.connectionObject.get_data(rec_type, internalId=internalId, externalId=externalId)


    def getRelatedJson(self, recordType, action='upsert'):
        rows = IntegrationMaster.objects.filter(
            user=self.userObject,
            integration_type=self.integration_type,
            module_type=recordType,
            action_type=action,
            integration_error__in=["null","","-"]
        ).exclude(status=True)
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
            resultArr.update(
                integration_error=data.error_msg,
                status = False
                )
            status = False
        resultArr.update(
            integration_reference = data.internalId,
            status = status
        )

    def match_itemlist_data(self, GRN_data, po_initialize,  is_multiple):
        try:
            final_GRN_data=[]
            for row in GRN_data:
                try:
                    if str(row.createdFrom.externalId) in po_initialize:
                        indx_list=[]
                        total_item_length=0
                        price_mismatch_ckeck=0
                        for line_item in po_initialize[str(row.createdFrom.externalId)]:
                            check_sku_code=False
                            if row.itemList.get("item", None):
                                item_length=len(row.itemList['item'])
                                for indx, grn_line_item in enumerate(row.itemList['item']):
                                    if grn_line_item["item"]["externalId"]== line_item["itemName"] and grn_line_item["itemReceive"]:
                                        if not grn_line_item.get("flag_duplicate",False):
                                        #if float(grn_line_item["quantity"])<=float(line_item["quantityRemaining"]) and float(grn_line_item["rate"])==float(line_item["rate"]):
                                            if float(grn_line_item["quantity"])<=float(line_item["quantityRemaining"]):
                                                grn_line_item.update({'orderLine': line_item['orderLine'], "flag_duplicate":True})
                                                check_sku_code=True
                                                price_mismatch_ckeck+=1
                                                break
                                            else:
                                                print("price or quantity mismatch", "GRN",float(grn_line_item["quantity"]), "Initialigelist", float(line_item["quantityRemaining"]))
                                if not check_sku_code:
                                    row.itemList['item'].append({
                                                                'item': {
                                                                'name': None,
                                                                'internalId': None,
                                                                'externalId': line_item["itemName"],
                                                                'type': None
                                                        },
                                                        'orderLine': line_item['orderLine'],
                                                        'itemReceive': False
                                                })
                    final_GRN_data.append(row)
                except Exception as e:
                    import traceback
                    log_err.debug(traceback.format_exc())
                    log_err.info('po_initialize GRN data failed for %s and error was %s' % (str(row), str(e)))
            return final_GRN_data
        except Exception as e:
            import traceback
            log_err.debug(traceback.format_exc())
            log_err.info('po_initialize GRN data failed for %s and error was %s' % (str(GRN_data), str(e)))
            return GRN_data
