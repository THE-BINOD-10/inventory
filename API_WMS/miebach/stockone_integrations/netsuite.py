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
            if data.get('purchase_unit', None) and data.get('unitypeexid', None):
                internId = self.netsuite_get_uom(data['purchase_unit'], data['unitypeexid'])
                if internId:
                    invitem.purchaseUnit = ns.RecordRef(internalId=internId)
            if data.get('sale_unit', None) and data.get('unitypeexid', None):
                internId = self.netsuite_get_uom(data['sale_unit'], data['unitypeexid'])
                if internId:
                    invitem.saleUnit = ns.RecordRef(internalId=internId)
            if data.get('ServicePurchaseItem', None):
                invitem.isFulfillable="T"
            # invitem.taxtype = data.product_type
            # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=data.sku_group))
            # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_shelflife', value=data.shelf_life))
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
            if data.get('sku_class', None):
                if("non_inventoryitem" not in data):
                    customFieldList.append(
                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=data.get('sku_class'))
                    )
            if data.get('mrp', None):
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.get('mrp'))
                )
            if data.get('sub_category', None):
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=data.get('sub_category'))
                )
            if data.get('hsn_code', None):
                customFieldList.append(
                  ns.SelectCustomFieldRef(scriptId='custitem_in_hsn_code', value=ns.ListOrRecordRef(externalId=data.get('hsn_code')))
                )
            if data.get('sub_category', None):
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=data.get('sub_category'))
                )
            if("non_inventoryitem" not in data):
                customFieldList.append(
                 ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetgroup', value=data.get('sku_group',''))
                )
            if data.get("service_start_date",None):
                customFieldList.append(
                 ns.DateCustomFieldRef(scriptId='custitesm_mhl_item_startdate', value=data.get('service_start_date').isoformat())
                )
            if  data.get("plant", None):
                customFieldList.append(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_plantcode', value=data["plant"]))
            customFieldList.append(
              ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=1))
            )
            customFieldList.append(
              ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T')
            )
            customFieldList.append(
              ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=ns.ListOrRecordRef(internalId=1))
            )
            customFieldList.append(
              ns.SelectCustomFieldRef(scriptId='custitem_mhl_data_type', value=ns.ListOrRecordRef(internalId=2))
            )
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
            rtvitem.entity = str(rtv_data["supplier_name"])
            rtvitem.tranId = rtv_data['rtv_number']
            rtvitem.orderStatus = ns.RecordRef(internalId='B')
            rtvitem.location = ns.RecordRef(internalId=297)
            # rtvitem.tranId = rtv_data["invoice_num"] if rtv_data["invoice_num"] else None
            rtvitem.date = rtv_data["date_of_issue_of_original_invoice"] if rtv_data["date_of_issue_of_original_invoice"] else None
            rtvitem.createdFrom = ns.RecordRef(externalId=rtv_data["po_number"])
            # rtvitem.location = ns.RecordRef(internalId=108)
            custom_field_list=[]
            custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value=rtv_data["debit_note_url"]))
            custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_adjustinventory_status', value=ns.ListOrRecordRef(internalId=2)))
            if rtv_data.get('subsidiary', None):
                rtvitem.subsidiary = ns.ListOrRecordRef(internalId=rtv_data["subsidiary"])
            if rtv_data.get('department', None):
                rtvitem.department = ns.RecordRef(internalId=rtv_data["department"])

            rtvitem.customFieldList = ns.CustomFieldList(custom_field_list)
            item = []
            for idx, data in enumerate(rtv_data['item_details']):
                rtv_custom_field_list=[]
                if(data.get("batch_no",None)):
                    rtv_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_vra_batchnumber', value=data["batch_no"]))
                if(data.get("mfg_date",None)):
                    rtv_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_grn_mfgdate', value=data["mfg_date"]))
                if(data.get("exp_date",None)):
                    rtv_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_adjustinvent_expirydate', value=data["exp_date"]))
                line_item = {
                'item': ns.RecordRef(externalId=data['sku_code']),
                'orderLine': idx+1,
                'rate': data['price'],
                'quantity': data['order_qty'],
                'location': ns.RecordRef(internalId=297),
                # 'itemReceive': True
                'description': data['sku_desc'],
                "customFieldList": ns.CustomFieldList(rtv_custom_field_list)
                }
                if data.get('uom_name', None) and data.get('unitypeexid', None):
                    internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                    if internId:
                        line_item.update({'units': ns.RecordRef(internalId=internId)})
                item.append(line_item)
            rtvitem.itemList = {'item':item}
            rtvitem.externalId = rtv_data['rtv_number']
            rtvitem.quantity = rtv_data["total_qty"]
            rtvitem.amount = rtv_data["total_without_discount"]
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
            if(grn_data.get("invoice_date",None)):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_vb_vendorinvoicedate', value=grn_data["invoice_date"]))
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
            if(grn_data.get("inv_receipt_date",None)):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_grn_veninvoicereceivedate', value=grn_data["inv_receipt_date"]))
            grnrec.customFieldList =  ns.CustomFieldList(custom_field_list)
            if(grn_data.get("subsidiary",None)):
                grnrec.subsidiary = ns.ListOrRecordRef(internalId=grn_data['subsidiary'])
            if(grn_data.get("department",None)):
                grnrec.department = ns.RecordRef(internalId=grn_data['department'])
            if(grn_data.get("items",None)):
                for idx, data in enumerate(grn_data['items']):
                    grn_custom_field_list=[]
                    if(data.get("batch_no",None)):
                        grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_vra_batchnumber', value=data["batch_no"]))
                    if(data.get("mfg_date",None)):
                        grn_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_grn_mfgdate', value=data["mfg_date"]))
                    if(data.get("exp_date",None)):
                        grn_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_adjustinvent_expirydate', value=data["exp_date"]))
                    if(data.get("mrp",None)):
                        grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_po_mrp', value=data['mrp']))
                    if data.get("unit_price", None):
                        grn_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_unit_price_grn', value=data['unit_price']))
                    line_item = {
                    'item': ns.RecordRef(externalId=data['sku_code']),
                    # 'quantity': data['received_quantity'],
                    'description': data['sku_desc'],
                    # 'rate': data['unit_price'],
                    # 'location': ns.RecordRef(internalId=297),
                    'itemReceive': data["itemReceive"],
                    "customFieldList": ns.CustomFieldList(grn_custom_field_list)
                    }
                    if data.get("unit_price", None):
                        line_item.update({'rate': data["unit_price"]})
                    if data.get("received_quantity", None):
                        line_item.update({'quantity': data["received_quantity"]})
                    if data.get("order_idx", None):
                        line_item.update({'orderLine': data["order_idx"]})
                    if data.get('uom_name', None) and data.get('unitypeexid', None):
                        internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                        if internId:
                            line_item.update({'units': ns.RecordRef(internalId=internId)})
                    item.append(line_item)
                grnrec.itemList = {'item':item, 'replaceAll': False}
                grnrec.tranId = grn_data['grn_number']
                grnrec.tranDate = grn_data["grn_date"]
                if grn_data.get('remarks',None):
                    grnrec.memo = grn_data['remarks']
            grnrec.externalId = grn_data['grn_number']
        except Exception as e:
            import traceback
            log_error.debug(traceback.format_exc())
            log_error.info('Create GRN data failed for %s and error was %s' % (str(grn_data['po_number']), str(e)))
        return grnrec


    def netsuite_create_po(self, po_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            purorder = ns.PurchaseOrder()
            if(po_data.get('reference_id',None)):
                purorder.entity = ns.RecordRef(internalId=po_data['reference_id'], type="vendor")
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
                else:
                    product_list_id = 3

            # purorder.location = warehouse_id
            purorder.approvalstatus = ns.RecordRef(internalId=2)
            # purorder.subsidiary = '1'
            if(po_data.get('subsidiary',None)):
                purorder.subsidiary = ns.ListOrRecordRef(internalId=po_data['subsidiary'])
            if(po_data.get('department',None)):
                purorder.department = ns.RecordRef(internalId=po_data['department'])

            if (po_data.get("payment_code", None)):
                purorder.terms = po_data.get("payment_code")
            if (po_data.get("address_id", None)):
                purorder.billAddress = ns.RecordRef(internalId=po_data.get("address_id"))

            po_custom_field_list =  []
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
            po_custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_in_gst_pos', value=ns.ListOrRecordRef(internalId=27)))

            if(po_data.get('approval2',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver2', value=po_data['approval2']))
            if(po_data.get('approval3',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver3', value=po_data['approval3']))
            if(po_data.get('approval4',None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver4', value=po_data['approval4']))
            # purorder.location= ns.RecordRef(internalId=297)
            if(po_data.get("plant", None)):
                 po_custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_po_billtoplantid', value=ns.ListOrRecordRef(internalId=po_data['plant'])))
                 po_custom_field_list.append(ns.SelectCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=ns.ListOrRecordRef(internalId=po_data['plant'])))
            if (po_data.get("supplier_gstin", None)):
                po_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_in_vendor_gstin', value=po_data["supplier_gstin"]))
            purorder.customFieldList = ns.CustomFieldList(po_custom_field_list)
            for data in po_data['items']:
                item_custom_list=[]
                if(data.get('mrp',None)):
                    item_custom_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_po_mrp', value=data['mrp']))
                if(po_data.get('full_pr_number',None)):
                    item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_mhl_pr_external_id', value=ns.ListOrRecordRef(externalId=po_data['full_pr_number'])))
                if(data.get('hsn_code',None)):
                    item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_in_hsn_code', value=ns.ListOrRecordRef(internalId=data['hsn_code'])))
                    item_custom_list.append(ns.SelectCustomFieldRef(scriptId='custcol_in_nature_of_item', value=ns.ListOrRecordRef(internalId=1)))
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
                if data.get('uom_name', None) and data.get('unitypeexid', None):
                    internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                    if internId:
                        line_item.update({'units': ns.RecordRef(internalId=internId)})
                item.append(line_item)
            purorder.itemList = { 'item': item }
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
                    'rate': data['price'],
                    'estimatedRate': data['price'],
                    # 'estimatedAmount':
                    # "poVendor": ns.RecordRef(internalId=data['reference_id'], type="vendor"),
                    # "vendorName": data["supplier_name"]
                    # 'location':ns.RecordRef(internalId=297)
                }
                if(item_custom_list):
                    line_item.update({'customFieldList':  ns.CustomFieldList(item_custom_list)})
                if data.get('uom_name', None) and data.get('unitypeexid', None):
                    internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                    if internId:
                        line_item.update({'units': ns.RecordRef(internalId=internId)})
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

            if (ia_data.get('subsidiary',None)):
                ia.subsidiary = ns.ListOrRecordRef(internalId=ia_data['subsidiary'])
            if (ia_data.get('department',None)):
                ia.department = ns.RecordRef(internalId=ia_data['department'])
            ia.account = ns.RecordRef(internalId=124)
            if (ia_data.get('account',None)):
                ia.account = ns.RecordRef(internalId=ia_data['account'])

            ia_custom_field_list =  [
                ns.StringCustomFieldRef(scriptId='custbody_mhl_adjustinventory_reason', value=ns.ListOrRecordRef(internalId=1))
            ]
            ia.customFieldList = ns.CustomFieldList(ia_custom_field_list)
            for data in ia_data['items']:
                inv_adj_custom_field_list=[]
                if(data.get("batch_no",None)):
                    inv_adj_custom_field_list.append(ns.StringCustomFieldRef(scriptId='custcol_mhl_vra_batchnumber', value=data["batch_no"]))
                if(data.get("mfg_date",None)):
                    inv_adj_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_grn_mfgdate', value=data["mfg_date"]))
                if(data.get("exp_date",None)):
                    inv_adj_custom_field_list.append(ns.DateCustomFieldRef(scriptId='custcol_mhl_adjustinvent_expirydate', value=data["exp_date"]))
                line_item = {
                 'item': ns.RecordRef(externalId=data['sku_code']),
                 'adjustQtyBy':data['adjust_qty_by'],
                 # 'location':ns.RecordRef(internalId=297),
                 "customFieldList": ns.CustomFieldList(inv_adj_custom_field_list)
                }
                if data.get('uom_name', None) and data.get('unitypeexid', None):
                    internId = self.netsuite_get_uom(data['uom_name'], data['unitypeexid'])
                    if internId:
                        line_item.update({'units': ns.RecordRef(internalId=internId)})
                item.append(line_item)
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
