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

    def complete_transaction(self, records, is_list):
        ns = self.nc.raw_client
        if is_list:
            data_response =  ns.upsertList(records)
        else:
            data_response =  ns.upsert(records)
        print(data_response)

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
            invitem.includeChildren = 'Y'
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
            customFieldList.append(
              ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=1))
            )
            customFieldList.append(
              ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T')
            )
            customFieldList.append(
              ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=ns.ListOrRecordRef(internalId=1)),
            )
            customFieldList.append(
              ns.StringCustomFieldRef(scriptId='custitem_mhl_data_type', value=ns.RecordRef(internalId=1))
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
            rtvitem.tranId = rtv_data["invoice_num"] if rtv_data["invoice_num"] else None
            rtvitem.date = rtv_data["date_of_issue_of_original_invoice"] if rtv_data["date_of_issue_of_original_invoice"] else None
            rtvitem.createdFrom = ns.RecordRef(externalId=rtv_data["po_number"])
            # rtvitem.location = ns.RecordRef(internalId=108)
            custom_field_list=[]
            custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value=rtv_data["debit_note_url"]))
            rtvitem.customFieldList = ns.CustomFieldList(custom_field_list)
            item = []
            for data in rtv_data['item_details']:
                line_item = {
                'item': ns.RecordRef(externalId=data['sku_code']),
                'orderLine': 1,
                'quantity': data['order_qty'],
                'location': ns.RecordRef(internalId=297),
                # 'itemReceive': True
                'description': data['sku_desc']
                }
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
            if(grn_data.get("items",None)):
                for idx, data in enumerate(grn_data['items']):
                    line_item = {
                    'item': ns.RecordRef(externalId=data['sku_code']), 'orderLine': idx+1,
                    'quantity': data['received_quantity'], 'location': ns.RecordRef(internalId=297), 'itemReceive': True}
                    item.append(line_item)
                grnrec.itemList = {'item':item}
                grnrec.tranId = grn_data['grn_number']
                grnrec.tranDate = grn_data["grn_date"]
            grnrec.externalId = grn_data['grn_number']
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create GRN data failed for %s and error was %s' % (str(grn_data['po_number']), str(e)))
        return grnrec


    def netsuite_create_po(self, po_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            purorder = ns.PurchaseOrder()
            purorder.entity = ns.RecordRef(internalId=po_data['reference_id'], type="vendor")
            purorder.tranDate = po_data['po_date']
            if po_data['due_date']:
                purorder.dueDate = po_data['due_date']
            purorder.approvalStatus = ns.RecordRef(internalId=2)
            purorder.externalId = po_data['po_number']
            purorder.tranId = po_data['po_number']
            purorder.memo = po_data['remarks']
            # purorder.purchaseordertype = po_data['order_type']
            if po_data['product_category'] == 'Services':
                product_list_id = 2
            elif po_data['product_category'] == 'Assets':
                product_list_id = 1
            else:
                product_list_id = 3

            # purorder.location = warehouse_id
            purorder.approvalstatus = ns.RecordRef(internalId=2)
            # purorder.subsidiary = '1'
            # purorder.department = po_data['user_id']
            # ns.StringCustomFieldRef(scriptId='custbody_mhl_po_billtoplantid', value=po_data['company_id'])
            purorder.customFieldList =  ns.CustomFieldList([
                ns.StringCustomFieldRef(scriptId='custbody_mhl_po_supplierhubid', value=po_data['supplier_id']),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver1', value=po_data['approval1']),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_po_shiptoaddress', value=po_data['ship_to_address']),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_po_purchaseordertype', value=product_list_id),
                # ns.SelectCustomFieldRef(scriptId='custbody_in_gst_pos', value=ns.ListOrRecordRef(internalId=28))
            ])
            for data in po_data['items']:
                line_item = {'item': ns.RecordRef(externalId=data['sku_code']),
                 'description': data['sku_desc'],
                 'rate': data['unit_price'],
                 'quantity':data['quantity'],
                 'location':ns.RecordRef(internalId=297),
                 'customFieldList': ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custcol_mhl_po_mrp', value=data['mrp']),
                  ns.SelectCustomFieldRef(scriptId='custcol_mhl_pr_external_id', value=ns.ListOrRecordRef(externalId=po_data['full_pr_number']))])
                 }
                item.append(line_item)
            purorder.itemList = {'item':item}

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
            purreq.subsidiary = ns.RecordRef(internalId=16)
            purreq.customFieldList =  ns.CustomFieldList([
                ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_prtype', value=pr_data['product_category']),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver1', value=pr_data['approval1']),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_requestor', value=pr_data['requested_by'])
            ])
            for data in pr_data['items']:
                line_item = {
                    'item': ns.RecordRef(externalId=data['sku_code']),
                    'description': data['sku_desc'],
                    'quantity':data['quantity'],
                    'location':ns.RecordRef(internalId=297)
                }
                item.append(line_item)
            purreq.itemList = { 'purchaseRequisitionItem': item }
            purreq.externalId = pr_data['full_pr_number']
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create PurchaseRequisition data failed and error was %s' % (str(e)))
        return purreq
