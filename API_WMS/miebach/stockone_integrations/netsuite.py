# from django.shortcuts import render
# from django.http import HttpResponse, HttpResponseRedirect
# from django.contrib.auth import authenticate, login
# from django.contrib.auth.models import User
# from django.contrib import auth
# from django.views.decorators.csrf import csrf_exempt
# from miebach_admin.models import *
# from miebach_admin.custom_decorators import login_required
# from collections import OrderedDict
# from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
# from dateutil.relativedelta import relativedelta
# from operator import itemgetter
# from django.db.models import Sum, Count
# from rest_api.views.common import get_local_date, folder_check
# from rest_api.views.integrations import *
import json
import datetime
import os
# from django.db.models import Q, F
# from django.core.serializers.json import DjangoJSONEncoder
from stockone_integrations.utils import init_logger
import reversion
import itertools
from netsuitesdk import NetSuiteConnection
from netsuitesdk.internal.utils import PaginatedSearch


today = datetime.datetime.now().strftime("%Y%m%d")
log = init_logger('logs/netsuite_integrations_' + today + '.log')
log_err = init_logger('logs/netsuite_integration_errors.log')


class netsuiteIntegration(object):
    def __init__(self, auth_dict):
        self.nc = NetSuiteConnection(
          account=auth_dict.get('api_instance', None),
          consumer_key=auth_dict.get('client_id'),
          consumer_secret=auth_dict.get('secret'),
          token_key=auth_dict.get('token_id'),
          token_secret=auth_dict.get('token_secret'))

    def complete_transaction(self, records, is_list, action='upsert'):
        ns = self.nc.raw_client
        if is_list:
            data_response =  ns.upsertList(records, action)
        else:
            data_response =  ns.upsert(records, action)
        return data_response

    def initiate_item(self, data, item_type):
        data_response = {}
        try:
            ns = self.nc.raw_client
            invitem = getattr(ns, item_type)()
            # invitem.taxSchedule = ns.RecordRef(internalId=1)
            invitem.itemId = data.get('sku_code','')
            invitem.externalId = data.get('sku_code')
            invitem.displayName = data.get('sku_desc','')
            invitem.itemType = data.get('sku_type','')
            invitem.vendorName = data.get('sku_brand','')
            invitem.upc = data.get('ean_number','')
            invitem.isinactive = data.get('status','')
            invitem.itemtype = data.get('batch_based','')
            invitem.purchaseunit = data.get('measurement_type','')
            invitem.salesDescription = data.get('sku_desc','')
            if data.get("gl_code",None) and data.get("gl_code","") != "0":
		invitem.assetAccount =  ns.ListOrRecordRef(externalId=data["gl_code"])
            invitem.cogsAccount =  ns.ListOrRecordRef(externalId="40050010")
            invitem.incomeAccount =  ns.ListOrRecordRef(externalId="30001600")
            if data.get('subsidiary', None):
                invitem.subsidiary = ns.ListOrRecordRef(internalId=data["subsidiary"])
            if data.get('department', None):
                invitem.department = ns.RecordRef(internalId=data["department"])
            invitem.includeChildren = 'Y'
            invitem.cost= data.get('cost_price','')
            if data.get('unitypeexid', None):
                invitem.unitsType = ns.RecordRef(externalId=data.get('unitypeexid'))
            if data.get('stock_unit', None) and data.get('unitypeexid', None):
                internId = self.netsuite_get_uom(data['stock_unit'], data['unitypeexid'])
                if internId:
                    invitem.stockUnit = ns.RecordRef(internalId=internId)
            if data.get('sale_unit', None) and data.get('unitypeexid', None):
                internId = self.netsuite_get_uom(data['sale_unit'], data['unitypeexid'])
                if internId:
                    invitem.saleUnit = ns.RecordRef(internalId=internId)
            if data.get('purchase_unit', None) and data.get('unitypeexid', None):
                internId = self.netsuite_get_uom(data['purchase_unit'], data['unitypeexid'])
                if internId:
                    invitem.purchaseUnit = ns.RecordRef(internalId=internId)
                    invitem.stockUnit = ns.RecordRef(internalId=internId)
                    invitem.saleUnit = ns.RecordRef(internalId=internId)
            if data.get('ServicePurchaseItem', None):
                invitem.isFulfillable="T"
            customFieldList = []
            if data.get('No.OfTests', None):
                customFieldList.append(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_nooftest', value=data.get('No.OfTests')))
            if data.get('No. of flex', None):
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_noofflex', value=data.get('No. of flex'))
                )
            if data.get('Conversion Factor', None):
                if(data.get('Conversion Factor')!="['']"):
                    customFieldList.append(
                    ns.StringCustomFieldRef(scriptId='custitem_mhl_item_conversionfactor', value=data.get('Conversion Factor'))
                    )
            if data.get('mrp', None):
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.get('mrp'))
                )
            if data.get('hsn_code', None):
                customFieldList.append(
                  ns.SelectCustomFieldRef(scriptId='custitem_in_hsn_code', value=ns.ListOrRecordRef(internalId= data.get('hsn_code')))
                )
            if data.get("service_start_date",None):
                customFieldList.append(
                 ns.DateCustomFieldRef(scriptId='custitesm_mhl_item_startdate', value=data.get('service_start_date').isoformat())
                )
            if  data.get("plant", None):
                customFieldList.append(ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_plantcode', value=ns.ListOrRecordRef(internalId=data["plant"])))
            item_skucategory=""
            if data.get("product_type", None):
                if data["product_type"] == "SKU":
                    item_skucategory = 1
                if data["product_type"] == "Service":
                    item_skucategory = 2
                if data["product_type"] == "Asset":
                    item_skucategory = 4
                    if data.get('sku_class', None):
                        customFieldList.append(ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=ns.ListOrRecordRef(internalId=data["sku_class"])))
                if data["product_type"]== "OtherItem":
                    item_skucategory = 14
            if data.get('sku_category', None):
                customFieldList.append(
                  ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_servicecategory', value=ns.ListOrRecordRef(internalId=data["sku_category"]))
                )
            if(item_skucategory):
                customFieldList.append(
                  ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=item_skucategory))
                )
            customFieldList.append(ns.SelectCustomFieldRef(scriptId='custitem_in_nature', value=ns.ListOrRecordRef(internalId=1)))
            customFieldList.append(
              ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T')
            )
            customFieldList.append(
              ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=ns.ListOrRecordRef(internalId=1))
            )
            # customFieldList.append(
            #   ns.SelectCustomFieldRef(scriptId='custitem_mhl_data_type', value=ns.ListOrRecordRef(internalId=2))
            # )
            invitem.customFieldList = ns.CustomFieldList(customFieldList)
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Update/Create sku data failed for %s and error was %s' % (str(data.get('sku_code')), str(e)))
        return invitem



    def netsuite_update_create_rtv(self, rtv_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            rtvitem = ns.VendorReturnAuthorization()
            if rtv_data.get("supplier_name", None):
                rtvitem.entity = str(rtv_data["supplier_name"])
            rtvitem.tranId = rtv_data['rtv_number']
            rtvitem.orderStatus = ns.RecordRef(internalId='B')
            # rtvitem.location = ns.RecordRef(internalId=297) #UAT Location Internal id
            #rtvitem.location = ns.RecordRef(internalId=327) # Prod Internal Id
            # rtvitem.tranId = rtv_data["invoice_num"] if rtv_data["invoice_num"] else None
            if rtv_data.get('location', None):
                location =rtv_data["location"]
            else:
                location = 327
            rtvitem.location = ns.RecordRef(internalId=location) # Prod Internal Id
            if rtv_data.get("date_of_issue_of_original_invoice", None):
                rtvitem.date = rtv_data["date_of_issue_of_original_invoice"] if rtv_data["date_of_issue_of_original_invoice"] else None
            if rtv_data.get("po_number", None):
                rtvitem.createdFrom = ns.RecordRef(externalId=rtv_data["po_number"])
            # rtvitem.location = ns.RecordRef(internalId=108)
            custom_field_list=[]
            if rtv_data.get("debit_note_url", None):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value=rtv_data["debit_note_url"]))
                custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_adjustinventory_status', value=ns.ListOrRecordRef(internalId=2)))
            if rtv_data.get('subsidiary', None):
                rtvitem.subsidiary = ns.ListOrRecordRef(internalId=rtv_data["subsidiary"])
            if rtv_data.get('department', None):
                rtvitem.department = ns.RecordRef(internalId=rtv_data["department"])

            rtvitem.customFieldList = ns.CustomFieldList(custom_field_list)
            item = []
            if rtv_data.get("item_details", None):
                for idx, data in enumerate(rtv_data['item_details']):
                    rtv_custom_field_list=[]
                    if(data.get("batch_no",None)):
                        rtv_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_vra_batchnumber', value=data["batch_no"]))
                    if(data.get("mfg_date",None)):
                        rtv_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_grn_mfgdate', value=data["mfg_date"]))
                    if(data.get("exp_date",None)):
                        rtv_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_adjustinvent_expirydate', value=data["exp_date"]))
                    if data.get("return_reason", None):
                        rtv_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_reason', value=data["return_reason"]))
                    line_item = {
                    'item': ns.RecordRef(externalId=data['sku_code']),
                    'orderLine': idx+1,
                    'rate': data['price'],
                    'quantity': data['order_qty'],
                    # 'location': ns.RecordRef(internalId=297),  #UAT Location Internal ID
                    'location': ns.RecordRef(internalId=location),  #Prod Internal ID
                    # 'itemReceive': True
                    'description': data['sku_desc'],
                    "customFieldList": ns.CustomFieldList(rtv_custom_field_list)
                    }
                    if data.get('uom_name', None) and data.get('unitypeexid', None):
                        internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                        if internId:
                            line_item.update({'units': ns.RecordRef(internalId=internId)})
                    item.append(line_item)
            if item:
                rtvitem.itemList = {'item':item}
            rtvitem.externalId = rtv_data['rtv_number']
            if rtv_data.get("total_qty", None):
                rtvitem.quantity = rtv_data["total_qty"]
            if rtv_data.get("total_without_discount", None):
                rtvitem.amount = rtv_data["total_without_discount"]
            if rtv_data.get("return_reason", None):
                rtvitem.memo= rtv_data["return_reason"]
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create RTV data failed for %s and error was %s' % (str(rtv_data["grn_no"].split("/")[0]), str(e)))
        return rtvitem

    def netsuite_create_grn(self, grn_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            grnrec = ns.ItemReceipt()
            if grn_data.get('po_number',None):
                grnrec.createdFrom = ns.RecordRef(externalId=grn_data['po_number'])
            custom_field_list=[]
            # custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=122, internalId=65))
            if(grn_data.get("dc_number",None)):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_vra_challannumber', value=grn_data["dc_number"]))
            if(grn_data.get("invoice_no",None)):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_grn_invoicenumber', value=grn_data["invoice_no"]))
            if(grn_data.get("invoice_value",None)):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_invoice_value', value=grn_data["invoice_value"]))
            if(grn_data.get("invoice_date",None)):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_vb_vendorinvoicedate', value=grn_data["invoice_date"]))
            if(grn_data.get("grn_date",None)):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_grn_veninvoicereceivedate', value=grn_data["grn_date"]))
            if grn_data.get("vendorbill_url",None):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value=grn_data["vendorbill_url"]))
            if(grn_data.get("dc_date",None)):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_vra_challandate', value=grn_data["dc_date"]))
            if(grn_data.get("credit_note_url",None)):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_credit_note', value=grn_data["credit_note_url"]))
            if(grn_data.get("credit_date",None)):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_grn_creditdate', value=grn_data["credit_date"]))
            if(grn_data.get("credit_number",None)):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_grn_creditnotenumber', value=grn_data["credit_number"]))
            if(grn_data.get("credit_note_value",None)):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_credit_note_value', value=grn_data["credit_note_value"]))
            if(grn_data.get("tcs_value",None)):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_tcs_amount_g', value=grn_data["tcs_value"]))
            if(grn_data.get("inv_receipt_date",None)):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_grn_veninvoicereceivedate', value=grn_data["inv_receipt_date"]))
            grnrec.customFieldList =  ns.CustomFieldList(custom_field_list)
            subsidiary=0
            if(grn_data.get("subsidiary",None)):
                subsidiary=grn_data['subsidiary']
                grnrec.subsidiary = ns.ListOrRecordRef(internalId=subsidiary)
            if(grn_data.get("department",None)):
                grnrec.department = ns.RecordRef(internalId=grn_data['department'])
            if(grn_data.get("items",None)):
                for idx, data in enumerate(grn_data['items']):
                    if data["itemReceive"]:
                        grn_custom_field_list=[]
                        if(data.get("batch_no",None)):
                            grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_vra_batchnumber', value=data["batch_no"]))
                        if(data.get("mfg_date",None)):
                            grn_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_grn_mfgdate', value=data["mfg_date"]))
                        if(data.get("exp_date",None)):
                            grn_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_adjustinvent_expirydate', value=data["exp_date"]))
                        if(data.get("mrp",None)):
                            grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_po_mrp', value=data['mrp']))

                        line_item = {
                        'sku_PO_quantity': data['quantity'],
                        'item': ns.RecordRef(externalId=data['sku_code']),
                        # 'quantity': data['received_quantity'],
                        'description': data['sku_desc'],
                        # 'rate': data['unit_price'],
                        # 'location': ns.RecordRef(internalId=297),
                        'itemReceive': data["itemReceive"],
                        #"customFieldList": ns.CustomFieldList(grn_custom_field_list)
                        }
                        if data.get("unit_price", None):
                            if int(subsidiary) == 17:
                                unit_price= data['unit_price']
                            else:
                                cgst_tax, sgst_tax, igst_tax, utgst_tax, cess_tax=[0]*5
                                if data.get('cgst_tax', 0):
                                    cgst_tax= float(data["cgst_tax"])
                                if data.get('sgst_tax', 0):
                                    sgst_tax= float(data["sgst_tax"])
                                if data.get('igst_tax', 0):
                                    igst_tax= float(data["igst_tax"])
                                if data.get('utgst_tax', 0):
                                    utgst_tax= float(data['utgst_tax'])
                                if data.get('cess_tax', 0):
                                    cess_tax = float(data['cess_tax'])
                                unit_price= data['unit_price'] +((data['unit_price'] *(igst_tax+ sgst_tax + cgst_tax+ utgst_tax + cess_tax))/100)
                            line_item.update({'rate': unit_price})
                            grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_unit_price_grn', value= unit_price))
                            grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_unit_price_wo_gst',value=data["unit_price"]))
                        else:
                            line_item.update({'rate': 0})
                            grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_unit_price_grn', value= 0))
                            grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_unit_price_wo_gst',value=0))
                        if data.get("received_quantity", None):
                            line_item.update({'quantity': data["received_quantity"]})
                        if data.get("order_idx", None):
                            line_item.update({'orderLine': data["order_idx"]})
                        if data.get('uom_name', None) and data.get('unitypeexid', None):
                            internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                            if internId:
                                line_item.update({'units': ns.RecordRef(internalId=internId)})
                        if grn_custom_field_list:
                            line_item.update({"customFieldList": ns.CustomFieldList(grn_custom_field_list)})
                        item.append(line_item)
                grnrec.itemList = {'item':item, 'replaceAll': False}
                grnrec.tranId = grn_data['grn_number']
                grnrec.tranDate = grn_data["grn_date"]
                if grn_data.get('remarks',None):
                    grnrec.memo = grn_data['remarks']
            grnrec.externalId = grn_data['grn_number']
        except Exception as e:
            print(e)
            import traceback
            log_err.debug(traceback.format_exc())
            log_err.info('Create GRN data failed for %s and error was %s' % (str(grn_data['po_number']), str(e)))
        return grnrec


    def netsuite_create_po(self, po_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            purorder = ns.PurchaseOrder()
            if(po_data.get('reference_id',None)):
                purorder.entity = ns.RecordRef(internalId=po_data['reference_id'], type="vendor")
                purorder.approvalstatus = ns.RecordRef(internalId=2)
            if(po_data.get('po_date',None)):
                purorder.tranDate = po_data['po_date']
            if(po_data.get('due_date',None)):
            # if po_data['due_date']:
                purorder.dueDate = po_data['due_date']
            purorder.approvalStatus = ns.RecordRef(internalId=2)
            purorder.externalId = po_data['po_number']
            purorder.tranId = po_data['po_number']
            if(po_data.get('remarks',None)):
                purorder.memo = po_data['remarks']
            # purorder.nexus = ns.RecordRef(internalId=1)
            # purorder.subsidiaryTaxRegNum = ns.RecordRef(internalId= "", type="")
            # purorder.taxRegOverride = True
            # purorder.taxDetailsOverride = True
            # purorder.entityTaxRegNum = ns.RecordRef(internalId= 437)

            # purorder.purchaseordertype = po_data['order_type']
            product_list_id=0
            if(po_data.get('product_category',None)):
                if po_data['product_category'] == 'Services':
                    product_list_id = 2
                elif po_data['product_category'] == 'Assets':
                    product_list_id = 1
                elif po_data['product_category'] == 'OtherItems':
                    product_list_id = 4
                else:
                    product_list_id = 3

            # purorder.location = warehouse_id
            # purorder.subsidiary = '1'
            if(po_data.get('subsidiary',None)):
                purorder.subsidiary = ns.ListOrRecordRef(internalId=po_data['subsidiary'])
            if(po_data.get('department',None)):
                purorder.department = ns.RecordRef(internalId=po_data['department'])

            if (po_data.get("payment_code", None)):
                purorder.terms = ns.ListOrRecordRef(internalId=po_data.get("payment_code"))
                # purorder.terms = po_data.get("payment_code")
            if (po_data.get("address_id", None)):
                purorder.billAddressList = ns.ListOrRecordRef(internalId=po_data.get("address_id"))

            if (po_data.get('currency_internal_id', None)):
                purorder.currency = ns.ListOrRecordRef(internalId=po_data.get("currency_internal_id"))

            if (po_data.get('exchangerate', None)):
                purorder.exchangerate = po_data.get('exchangerate')

            po_custom_field_list =  []
            if po_data.get('nexus', None):
                purorder.nexus=ns.ListOrRecordRef(internalId=po_data["nexus"])
                purorder.taxRegOverride = "T"
                # purorder.taxDetailsOverride = True
            #po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_process_grn', value='T'))
            if(po_data.get('supplier_id',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_po_supplierhubid', value=po_data['supplier_id']))
            if(po_data.get('requested_by',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_requestor', value=po_data['requested_by']))
            if(po_data.get('approval1',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver1', value=po_data['approval1']))
            if(po_data.get('ship_to_address',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_po_shiptoaddress', value=po_data['ship_to_address']))
            if(product_list_id):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_po_purchaseordertype', value=product_list_id))
            if po_data.get("place_of_supply",None):
                po_custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_in_gst_pos', value=ns.ListOrRecordRef(internalId=str(po_data['place_of_supply']).lstrip("0"))))
            if(po_data.get('approval2',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver2', value=po_data['approval2']))
            if(po_data.get('approval3',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver3', value=po_data['approval3']))
            if(po_data.get('approval4',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver4', value=po_data['approval4']))
            if(po_data.get('po_url1',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_attachment_1', value=po_data['po_url1']))
            if(po_data.get('po_url2',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_attachment_2', value=po_data['po_url2']))
            if(po_data.get("plant", None)):
                 po_custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_po_billtoplantid', value=ns.ListOrRecordRef(internalId=po_data['plant'])))
                 po_custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=ns.ListOrRecordRef(internalId=po_data['plant'])))
            if (po_data.get("supplier_gstin", None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_stockone_vendor_gstin', value=po_data["supplier_gstin"]))
            purorder.customFieldList = ns.CustomFieldList(po_custom_field_list)
            if(po_data.get("items",None)):
                for data in po_data['items']:
                    item_custom_list=[]
                    if(data.get('mrp',None)):
                        item_custom_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_po_mrp', value=data['mrp']))
                    if(po_data.get('full_pr_number',None)):
                        item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_mhl_pr_external_id', value=ns.ListOrRecordRef(externalId=po_data['full_pr_number'])))
                    cgst_tax, sgst_tax, igst_tax, utgst_tax, cess_tax=[0]*5
                    if data.get('cgst_tax', 0):
                        cgst_tax= float(data["cgst_tax"])
                    if data.get('sgst_tax', 0):
                        sgst_tax= float(data["sgst_tax"])
                    if data.get('igst_tax', 0):
                        igst_tax= float(data["igst_tax"])
                    if data.get('utgst_tax', 0):
                        utgst_tax= float(data['utgst_tax'])
                    if data.get('cess_tax', 0):
                        cess_tax = float(data['cess_tax'])
                    total_tax=igst_tax+ sgst_tax + cgst_tax+ utgst_tax + cess_tax
                    if(data.get('hsn_code',None)):
                        if total_tax and data.get('unit_price',None):
                            temp_hsn =str(data["hsn_code"]).split("_")[-1]
                            if temp_hsn=="KL":
                                item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_in_hsn_code', value=ns.ListOrRecordRef(externalId=data['hsn_code'])))
                            else:
                                item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_in_hsn_code', value=ns.ListOrRecordRef(internalId=data['hsn_code'])))
                            item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_in_nature_of_item', value=ns.ListOrRecordRef(internalId=1)))
                    if (data.get("document_number", None)):
                        item_custom_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_grn_document_number', value=data["document_number"]))
                    line_item = {
                     'item': ns.RecordRef(externalId=data['sku_code']),
                     # 'item': ns.RecordRef(internalId=17346),
                     # 'location':ns.RecordRef(internalId=297),
                    }
                    if(item_custom_list):
                        line_item.update({'customFieldList':  ns.CustomFieldList(item_custom_list)})
                    if(data.get('sku_desc',None)):
                        line_item.update({'description': data['sku_desc']})
                    if(data.get('unit_price',None)):
                        line_item.update({'rate': data['unit_price']})
                    if(data.get('quantity',None)):
                        line_item.update({'quantity':data['quantity']})
                    '''if data.get('uom_name', None) and data.get('unitypeexid', None):
                        internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                        if internId:
                            line_item.update({'units': ns.RecordRef(internalId=internId)})'''
                    item.append(line_item)
                item_list= { 'item': item}
                if po_data.get('replaceAll_1', ''):
                    if po_data['replaceAll'] == 'replaceAll_False':
                        item_list.update({'replaceAll': False})
                    elif po_data['replaceAll'] == 'replaceAll_True':
                        item_list.update({'replaceAll': True})
                purorder.itemList = item_list
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create PurchaseOrder data failed and error was %s' % (str(e)))
        return purorder

    def netsuite_create_pr(self, pr_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            purreq = ns.PurchaseRequisition()
            # purreq.entity = ns.RecordRef(internalId=6)
            # purreq.memo = "Webservice PR"
            # purreq.approvalStatus = ns.RecordRef(internalId=2)
            purreq.tranDate = pr_data['pr_date']
            purreq.tranId = pr_data['full_pr_number']
            purreq.tranDate = pr_data['pr_date']
            # purreq.location= ns.RecordRef(internalId=297)
            # purreq.subsidiary = ns.RecordRef(internalId=1)
            if(pr_data['subsidiary']):
                purreq.subsidiary = ns.ListOrRecordRef(internalId=pr_data['subsidiary'])
            # if(pr_data['department']):
            #     purreq.department = ns.RecordRef(internalId=pr_data['department'])
            custom_list=[
                ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_prtype', value=pr_data['product_category']),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver1', value=pr_data['approval1']),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_requestor', value=pr_data['requested_by'])
            ]
            if(pr_data.get('approval2',None)):
                custom_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver2', value=pr_data['approval2']))
            if(pr_data.get('approval3',None)):
                custom_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver3', value=pr_data['approval3']))
            if(pr_data.get('approval4',None)):
                custom_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver4', value=pr_data['approval4']))
            if(pr_data.get('pr_url1',None)):
                custom_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_attachment_1', value=pr_data['pr_url1']))
            if(pr_data.get('pr_url2',None)):
                custom_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_attachment_2', value=pr_data['pr_url2']))
            if(pr_data.get('plant', None)):
                custom_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=ns.ListOrRecordRef(internalId=pr_data['plant'])))
            if(pr_data['department']):
                custom_list.append(ns.SelectCustomFieldRef(scriptId='cseg_mhl_custseg_de', value=ns.ListOrRecordRef(internalId=pr_data['department'])))
            purreq.customFieldList =  ns.CustomFieldList(custom_list)
            for data in pr_data['items']:
                item_custom_list=[]
                # if(data.get('hsn_code',None)):
                #     item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_in_hsn_code', value=ns.ListOrRecordRef(internalId=data['hsn_code'])))
                #     item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_in_nature_of_item', value=ns.ListOrRecordRef(internalId=1)))
                line_item = {
                    'item':ns.RecordRef(externalId=data['sku_code']),
                    'description': data['sku_desc'],
                    'quantity':data['quantity'],
                    # 'rate': data['price'],
                    'estimatedRate': data['price'],
                    # 'estimatedAmount':
                    # "poVendor": ns.RecordRef(internalId=data['reference_id'], type="vendor"),
                    # "vendorName": data["supplier_name"]
                    # 'location':ns.RecordRef(internalId=297)
                }
                if(item_custom_list):
                    line_item.update({'customFieldList':  ns.CustomFieldList(item_custom_list)})
                '''if data.get('uom_name', None) and data.get('unitypeexid', None):
                    internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                    if internId:
                        line_item.update({'units': ns.RecordRef(internalId=internId)})'''
                item.append(line_item)
            purreq.itemList = { 'purchaseRequisitionItem': item }
            purreq.externalId = pr_data['full_pr_number']
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create PurchaseRequisition data failed and error was %s' % (str(e)))
        return purreq

    def netsuite_create_uom(self, uom_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []

            UnitsType = ns.UnitsType()
            UnitsType.name = uom_data['name']
            for data in uom_data['uom_items']:
                line_item = {
                    'externalId': '%s-%s' % (uom_data['name'], data['unit_name']),
                    'unitName': data['unit_name'],
                    'abbreviation': data['unit_name'],
                    'pluralName': data['unit_name'],
                    'pluralAbbreviation': data['unit_name'],
                    'conversionRate': data['unit_conversion']
                }
                if data.get('is_base', False):
                    line_item.update({'baseUnit': True})
                item.append(line_item)

            UnitsType.uomList = { 'uom': item, 'replaceAll': False}
            UnitsType.externalId = uom_data['name']
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            log.debug(traceback.format_exc())
            log.info('Create PurchaseRequisition data failed and error was %s' % (str(e)))
        return UnitsType

    def netsuite_get_uom(self, uomname, unitypeexid):
        try:
            ns = self.nc.raw_client
            uoms = ns.get('UnitsType', externalId=unitypeexid).uomList.uom
            for row in uoms:
                if row.unitName == uomname:
                    return row.internalId
            return False
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            log.debug(traceback.format_exc())
            log.info('Create PurchaseRequisition data failed and error was %s' % (str(e)))
        return False


    def get_data(self, rec_type, internalId=None, externalId=None):
        try:
            ns = self.nc.raw_client
            if internalId:
                response = ns.get(rec_type, internalId=internalId)
            elif externalId:
                response = ns.get(rec_type, externalId=externalId)
            else:
                return None
            return response
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            log.debug(traceback.format_exc())
            log_err.info('Fetching Data Failed For %s , reason :: %s' % (rec_type, str(e)))

    def netsuite_create_invadj(self, ia_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            ia = ns.InventoryAdjustment()
            ia.tranDate = ia_data['ia_date']
            ia.externalId = ia_data['ia_number']
            ia.tranId = ia_data['ia_number']
            ia.memo = ia_data['remarks']

            # if po_data['product_category'] == 'Services':
            #     product_list_id = 2
            # elif po_data['product_category'] == 'Assets':
            #     product_list_id = 1
            # else:
            #     product_list_id = 3
            ia.adjLocation = ns.RecordRef(internalId=327) # Prod Internal Id
            if ia_data.get('location_id',None):
                ia.adjLocation = ns.RecordRef(internalId=ia_data["location_id"])
            if (ia_data.get('subsidiary',None)):
                ia.subsidiary = ns.ListOrRecordRef(internalId=ia_data['subsidiary'])
            if (ia_data.get('department',None)):
                ia.department = ns.RecordRef(internalId=ia_data['department'])
            ia.account = ns.RecordRef(internalId=1705)
            if (ia_data.get('account',None)):
                ia.account = ns.RecordRef(internalId=ia_data['account'])

            ia_custom_field_list =  [
                ns.SelectCustomFieldRef(scriptId='custbody_mhl_adjustinventory_reason', value=ns.ListOrRecordRef(internalId=1))
            ]

            if ia_data.get("plant", None):
                ia_custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=ns.ListOrRecordRef(internalId=ia_data['plant'])))
            #ia.customFieldList = ns.CustomFieldList(ia_custom_field_list)
            for data in ia_data['items']:
                inv_adj_custom_field_list=[]
                if(data.get("batch_no",None)):
                    ia_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_batch_number', value=data["batch_no"]))
                if(data.get("mfg_date",None)):
                    ia_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_mnf_date_adju', value=data["mfg_date"]))
                if(data.get("exp_date",None)):
                    ia_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_expiry_date', value=data["exp_date"]))
                line_item = {
                 'item': ns.RecordRef(externalId=data['sku_code']),
                 'adjustQtyBy':data['adjust_qty_by'],
                 'location': ns.RecordRef(internalId=327),
                 'unitCost': data['price'],
                 #"customFieldList": ns.CustomFieldList(inv_adj_custom_field_list)
                }
                if ia_data.get('location_id',None):
                    line_item.update({"location":ns.RecordRef(internalId=ia_data["location_id"])})
                if data.get('uom_name', None) and data.get('unitypeexid', None):
                    internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                    if internId:
                        line_item.update({'units': ns.RecordRef(internalId=internId)})
                item.append(line_item)
            ia.customFieldList = ns.CustomFieldList(ia_custom_field_list)
            ia.inventoryList = { 'inventory': item }
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create Inventory Adjustment data failed and error was %s' % (str(e)))
        return ia

    def netsuite_create_invtrf(self, it_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            it = ns.InventoryTransfer()
            it.tranDate = it_data['it_date']
            it.externalId = it_data['it_number']
            #it.tranId = it_data['it_number']
            it.memo = it_data['remarks']

            # if po_data['product_category'] == 'Services':
            #     product_list_id = 2
            # elif po_data['product_category'] == 'Assets':
            #     product_list_id = 1
            # else:
            #     product_list_id = 3

            if (it_data.get('subsidiary',None)):
                it.subsidiary = ns.ListOrRecordRef(internalId=it_data['subsidiary'])
            if (it_data.get('department',None)):
                it.department = ns.RecordRef(internalId=it_data['department'])
            if (it_data.get('account',None)):
                it.account = ns.RecordRef(internalId=it_data['account'])

            it.location = ns.RecordRef(internalId=297)
            it.transferLocation = ns.RecordRef(internalId=269)
            # ia_custom_field_list =  [
            #     ns.StringCustomFieldRef(scriptId='custbody_mhl_adjustinventory_reason', value=ns.ListOrRecordRef(internalId=1))
            # ]
            # ia.customFieldList = ns.CustomFieldList(ia_custom_field_list)
            for data in it_data['items']:
                inv_transfer_custom_field_list=[]
                if(data.get("batchno",None)):
                    inv_transfer_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_vra_batchnumber', value=data["batchno"]))
                if(data.get("mfg_date",None)):
                    inv_transfer_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_grn_mfgdate', value=data["mfg_date"]))
                if(data.get("exp_date",None)):
                    inv_transfer_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_adjustinvent_expirydate', value=data["exp_date"]))
                line_item = {
                 'item': ns.RecordRef(externalId=data['sku_code']),
                 'adjustQtyBy':data['adjust_qty_by'],
                 "customFieldList": ns.CustomFieldList(inv_transfer_custom_field_list)
                }
                if data.get('uom_name', None) and data.get('unitypeexid', None):
                    internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                    if internId:
                        line_item.update({'units': ns.RecordRef(internalId=internId)})
                item.append(line_item)
            it.inventoryList = { 'inventory': item }
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create Inventory Adjustment data failed and error was %s' % (str(e)))
        return it
