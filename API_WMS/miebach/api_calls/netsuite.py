from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib import auth
from django.views.decorators.csrf import csrf_exempt
from miebach_admin.models import *
from miebach_admin.custom_decorators import login_required
from collections import OrderedDict
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from django.db.models import Sum, Count
from rest_api.views.common import get_local_date, folder_check
from rest_api.views.integrations import *
import json
import datetime
import os
from django.db.models import Q, F
from django.core.serializers.json import DjangoJSONEncoder
from rest_api.views.utils import *
import reversion
import itertools
from netsuitesdk import NetSuiteConnection
from netsuitesdk.internal.utils import PaginatedSearch

today = datetime.datetime.now().strftime("%Y%m%d")
log = init_logger('logs/netsuite_integrations_' + today + '.log')
log_err = init_logger('logs/netsuite_integration_errors.log')

NS_ACCOUNT='4120343_SB1'
NS_CONSUMER_KEY='c1c9d3560fea16bc87e9a7f1428064346be5f1f28fb33945c096deb1353c64ea'
NS_CONSUMER_SECRET='a28d1fc077c8e9f0f27c74c0720c7519c84a433f1f8c93bfbbfa8fea1f0b4f35'
NS_TOKEN_KEY='e18e37a825e966c6e7e39b604058ce0d31d6903bfda3012f092ef845f64a1b7f'
NS_TOKEN_SECRET='7e4d43cd21d35667105e7ea885221170d871f5ace95733701226a4d5fbdf999c'

def connect_tba():
    nc = NetSuiteConnection(
      account=NS_ACCOUNT,
      consumer_key=NS_CONSUMER_KEY,
      consumer_secret=NS_CONSUMER_SECRET,
      token_key=NS_TOKEN_KEY,
      token_secret=NS_TOKEN_SECRET)
    return nc

def netsuite_update_create_sku(data, sku_attr_dict, user):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        invitem = ns.InventoryItem()
        # invitem.taxSchedule = ns.RecordRef(internalId=1)
        invitem.itemId = data.sku_code
        invitem.externalId = data.sku_code
        invitem.displayName = data.sku_desc
        invitem.itemType = data.sku_type
        invitem.vendorname = data.sku_brand
        invitem.upc = data.ean_number
        invitem.isinactive = data.status
        invitem.itemtype = data.batch_based
        invitem.purchaseunit = data.measurement_type
        invitem.includeChildren = 'Y'
        # invitem.taxtype = data.product_type
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=data.sku_group))
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_shelflife', value=data.shelf_life))
        invitem.purchaseunit = data.measurement_type
        invitem.customFieldList = ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custitem_mhl_item_nooftest', value=sku_attr_dict.get('No. of Test', '')),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_noofflex', value=sku_attr_dict.get('No. of flex', '')),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_conversionfactor', value=sku_attr_dict.get('Conversion Factor', '')),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=data.sku_class),
                                                      ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=1)),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.mrp),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=data.sub_category),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T'),
                                                      ns.SelectCustomFieldRef(scriptId='custitem_in_hsn_code', value=ns.ListOrRecordRef(externalId=data.hsn_code)),
                                                      ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=ns.ListOrRecordRef(internalId=1)),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_data_type', value=ns.RecordRef(internalId=1))])
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_shelflife', value=data.shelf_life)])
        data_response = ns.upsert(invitem)
        data_response = json.dumps(data_response.__dict__)
        data_response = json.loads(data_response)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create sku data failed for %s and error was %s' % (str(data.sku_code), str(e)))
    return data_response

def netsuite_sku_bulk_create(model_obj,  sku_key_map, new_skus):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        list_skuitems=[]
        for sku_code, sku_id in sku_key_map.items():
            sku_master_data=new_skus[sku_code].get('sku_obj', {})
            sku_attr_dict=new_skus[sku_code].get('attr_dict', {})
            skuitem= ns.InventoryItem()
            skuitem.itemId = sku_master_data.sku_code
            skuitem.externalId = sku_master_data.sku_code
            skuitem.displayName = sku_master_data.sku_desc
            skuitem.itemType = sku_master_data.sku_type
            skuitem.includeChildren = 'Y'
            skuitem.vendorname = sku_master_data.sku_brand
            skuitem.upc = sku_master_data.ean_number
            skuitem.isinactive = sku_master_data.status
            skuitem.purchaseunit = sku_master_data.measurement_type
            skuitem.customFieldList = ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custitem_mhl_item_nooftest', value=sku_attr_dict.get('No. of Test', '')),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_noofflex', value=sku_attr_dict.get('No. of flex', '')),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_conversionfactor', value=sku_attr_dict.get('Conversion Factor', '')),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=sku_master_data.sku_class),
                                                      ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=1)),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T'),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=sku_master_data.mrp),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=sku_master_data.sub_category)])
            list_skuitems.append(skuitem)
        data_response =  ns.upsertList(list_skuitems)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create Bulk sku data failed , error was %s' % (str(e)))
    return data_response

def netsuite_service_master_bulk_create(model_obj,  sku_key_map, new_skus):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        list_serviceitems=[]
        for sku_code, sku_id in sku_key_map.items():
            sku_master_data=new_skus[sku_code].get('sku_obj', {})
            sku_attr_dict=new_skus[sku_code].get('attr_dict', {})
            serviceitem = ns.ServicePurchaseItem()
            serviceitem.itemId = sku_master_data.sku_code
            serviceitem.externalId = sku_master_data.sku_code
            serviceitem.displayName = sku_master_data.sku_desc
            serviceitem.itemType = sku_master_data.sku_type
            serviceitem.vendorname = sku_master_data.sku_brand
            serviceitem.upc = sku_master_data.ean_number
            serviceitem.isinactive = sku_master_data.status
            serviceitem.cost = sku_master_data.cost_price
            serviceitem.includeChildren = 'Y'
            serviceitem.customFieldList = ns.CustomFieldList([ ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=sku_master_data.sku_class),
                                                               ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T'),
                                                               ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=2))
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_servicecategory', value=sku_master_data.sku_category),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=sku_master_data.mrp),
                                                      # ns.DateCustomFieldRef(scriptId='custitesm_mhl_item_startdate', value=sku_master_data.service_start_date.isoformat()),
                                                      # ns.DateCustomFieldRef(scriptId='custitem_mhl_item_enddate', value=sku_master_data.service_end_date.isoformat()),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_servicesubcategory', value=sku_master_data.sub_category)
                                                      ])
            list_serviceitems.append(serviceitem)
        data_response =  ns.upsertList(list_serviceitems)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create sku data failed , error was %s' % (str(e)))
    return data_response

def netsuite_asset_master_bulk_create(model_obj,  sku_key_map, new_skus):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        list_assetitems=[]
        for sku_code, sku_id in sku_key_map.items():
            sku_master_data=new_skus[sku_code].get('sku_obj', {})
            sku_attr_dict=new_skus[sku_code].get('attr_dict', {})
            assetitem= ns.NonInventoryPurchaseItem()
            assetitem.itemId = sku_master_data.sku_code
            assetitem.externalId = sku_master_data.sku_code
            assetitem.displayName = sku_master_data.sku_desc
            assetitem.itemType = sku_master_data.sku_type
            assetitem.vendorname = sku_master_data.sku_brand
            assetitem.upc = sku_master_data.ean_number
            assetitem.isinactive = sku_master_data.status
            assetitem.cost = sku_master_data.cost_price
            assetitem.includeChildren = 'Y'
            assetitem.customFieldList = ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=sku_master_data.sku_class),
                                                           ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T'),
                                                           ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=4))
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetcategory', value=sku_master_data.sku_category),
                                                    #   ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.mrp),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetsubcategory', value=sku_master_data.sub_category)
                                                      ])
            list_assetitems.append(assetitem)
        data_response =  ns.upsertList(list_assetitems)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create sku data failed , error was %s' % (str(e)))
    return data_response

def netsuite_otheritem_master_bulk_create(model_obj,  sku_key_map, new_skus):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        list_otheritems=[]
        for sku_code, sku_id in sku_key_map.items():
            sku_master_data=new_skus[sku_code].get('sku_obj', {})
            sku_attr_dict=new_skus[sku_code].get('attr_dict', {})
            otheritem = ns.NonInventoryPurchaseItem()
            otheritem.itemId = sku_master_data.sku_code
            otheritem.externalId = sku_master_data.sku_code
            otheritem.displayName = sku_master_data.sku_desc
            otheritem.itemType = sku_master_data.sku_type
            otheritem.vendorname = sku_master_data.sku_brand
            otheritem.department = sku_master_data.sku_class
            otheritem.isinactive = sku_master_data.status
            otheritem.cost = sku_master_data.cost_price
            otheritem.includeChildren = 'Y'
            otheritem.customFieldList = ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=sku_master_data.sku_class),
                                                            ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T')
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetcategory', value=ns.RecordRef(internalId=2)),
                                                    #   ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.mrp),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetsubcategory', value=ns.RecordRef(internalId=3))
                                                      ])
            list_otheritems.append(otheritem)
        data_response =  ns.upsertList(list_otheritems)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create sku data failed , error was %s' % (str(e)))
    return data_response

def netsuite_update_create_service(data, user):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        serviceitem = ns.ServicePurchaseItem()
        serviceitem.itemId = data.sku_code
        serviceitem.externalId = data.sku_code
        serviceitem.displayName = data.sku_desc
        serviceitem.itemType = data.sku_type
        serviceitem.vendorname = data.sku_brand
        serviceitem.department = data.sku_class
        serviceitem.isinactive = data.status
        serviceitem.cost = data.cost_price
        serviceitem.purchaseunit = data.measurement_type
        serviceitem.includeChildren = 'Y'
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_servicegroup', value=data.sku_group))

        serviceitem.customFieldList = ns.CustomFieldList([ 
                                                    # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=data.sku_class),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_servicecategory', value=data.sku_category),
                                                      ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=ns.ListOrRecordRef(internalId=2)),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.mrp),
                                                      ns.DateCustomFieldRef(scriptId='custitesm_mhl_item_startdate', value=data.service_start_date.isoformat()),
                                                      # ns.DateCustomFieldRef(scriptId='custitem_mhl_item_enddate', value=data.service_end_date.isoformat()),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_servicesubcategory', value=data.sub_category),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T')
                                                      ])
        data_response = ns.upsert(serviceitem)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create service data failed for %s and error was %s' % (str(data.sku_code), str(e)))
    return data_response

def netsuite_update_create_assetmaster(data, user):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        assetitem = ns.NonInventoryPurchaseItem()
        # assetitem.taxSchedule = ns.RecordRef(internalId=1)
        assetitem.itemId = data.sku_code
        assetitem.externalId = data.sku_code
        assetitem.displayName = data.sku_desc
        assetitem.itemType = data.sku_type
        assetitem.vendorName = data.sku_brand
        assetitem.department = data.sku_class
        #assetitem.parent = ns.RecordRef(externalId=data['sku_code'])
        assetitem.isinactive = data.status
        assetitem.includeChildren = 'Y'
        assetitem.cost = data.cost_price
        assetitem.purchaseunit = data.measurement_type
        assetitem.customFieldList = ns.CustomFieldList([
                                                        # ns.SelectCustomFieldRef(scriptId='custitem_mhl_item_assetcategory', value=ns.ListOrRecordRef(internalId=4)),
                                                        ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetgroup', value=data.sku_group),
                                                        ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T'),
                                                        ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=data.sub_category)
                                                        # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.mrp),
                                                      # ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetsubcategory', value=data.sub_category)
                                                      ])
        data_response = ns.upsert(assetitem)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create AssetMaster data failed for %s and error was %s' % (str(data.sku_code), str(e)))
    return data_response

def netsuite_update_create_otheritem_master(data, user):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        otheritem = ns.NonInventoryPurchaseItem()
        # otheritem.taxSchedule = ns.RecordRef(internalId=1)
        otheritem.itemId = data.sku_code
        otheritem.externalId = data.sku_code
        otheritem.displayName = data.sku_desc
        otheritem.itemType = data.sku_type
        otheritem.vendorName = data.sku_brand
        otheritem.department = data.sku_class
        #assetitem.parent = ns.RecordRef(externalId=data['sku_code'])
        otheritem.isinactive = data.status
        otheritem.includeChildren = 'Y'
        otheritem.cost = data.cost_price
        otheritem.purchaseunit = data.measurement_type
        otheritem.customFieldList = ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=data.sku_class),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=data.sku_category),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_for_purchase', value='T'),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_assetgroup', value=data.sku_group),
                                                    #   ns.StringCustomFieldRef(scriptId='custitem_mhl_item_mrpprice', value=data.mrp),
                                                      ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=data.sub_category)
                                                      ])
        data_response = ns.upsert(otheritem)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create OtherItem data failed for %s and error was %s' % (str(data.sku_code), str(e)))
    return data_response

def netsuite_update_create_rtv(rtv_data, user):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        rtvitem = ns.VendorReturnAuthorization()
        rtvitem.entity = str(rtv_data["supplier_name"])
        rtvitem.tranId = rtv_data["invoice_num"] if rtv_data["invoice_num"] else None
        rtvitem.date = rtv_data["date_of_issue_of_original_invoice"] if rtv_data["date_of_issue_of_original_invoice"] else None
        rtvitem.createdFrom = ns.RecordRef(externalId=rtv_data["grn_no"].split("/")[0])
        # rtvitem.location = ns.RecordRef(internalId=108)
        item = []
        for data in rtv_data['item_details']:
            line_item = {
            'item': ns.RecordRef(externalId=data['sku_code']),
            'orderLine': 1,
            'quantity': data['order_qty'],
            'location': ns.RecordRef(internalId=108),
            # 'itemReceive': True
            'description': data['sku_desc']
            }
            item.append(line_item)
        rtvitem.itemList = {'item':item}
        rtvitem.externalId = rtv_data['rtv_number']
        rtvitem.quantity = rtv_data["total_qty"]
        rtvitem.amount = rtv_data["total_without_discount"]
        rtvitem.memo= rtv_data["return_reason"]
        data_response = ns.upsert(rtvitem)
        data_response = json.dumps(data_response.__dict__)
        data_response = json.loads(data_response)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create RTV data failed for %s and error was %s' % (str(rtv_data["grn_no"].split("/")[0]), str(e)))
    return data_response

def netsuite_create_grn(user, grn_data):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        item = []
        if("po_challan" in grn_data):
            list_dc_items=[]
            for t_grn_data in grn_data["dc_data"]:
                grnrec = ns.ItemReceipt()
                grnrec.createdFrom = ns.RecordRef(externalId=t_grn_data['grn_number'].split("/")[0])
                grnrec.customFieldList =  ns.CustomFieldList([
                                                            ns.StringCustomFieldRef(scriptId='custbody_mhl_vra_challannumber', value=grn_data["dc_number"]),
                                                            # ns.DateCustomFieldRef(scriptId='custbody_mhl_vra_challandate', value=grn_data["dc_date"]),
                                                            # ns.StringCustomFieldRef(scriptId='custbody_mhl_grn_veninvoicereceivedate', value=grn_data["grn_date"])
                                                            ])
                grnrec.externalId = t_grn_data['grn_number']
                list_dc_items.append(grnrec)
            data_response =  ns.upsertList(list_dc_items)
        elif("credit_note_approve" in grn_data):
            grnrec = ns.ItemReceipt()
            grnrec.createdFrom = ns.RecordRef(externalId=grn_data['grn_number'].split("/")[0])
            custom_field_list=[
                ns.StringCustomFieldRef(scriptId='custbody_mhl_grn_invoicenumber', value=grn_data["invoice_no"]),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_credit_note', value=grn_data["url"]),
                ns.DateCustomFieldRef(scriptId='custbody_mhl_vb_vendorinvoicedate', value=grn_data["invoice_date"]),
                ns.DateCustomFieldRef(scriptId='custbody_mhl_grn_creditdate', value=grn_data["credit_date"]),
                ns.StringCustomFieldRef(scriptId='custbody_mhl_grn_creditnotenumber', value=grn_data["credit_number"])
            ]
            if(grn_data["vendor_url"]):
                custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value=grn_data["vendor_url"]))
            grnrec.customFieldList =  ns.CustomFieldList(custom_field_list)
            grnrec.externalId = grn_data['grn_number']
            data_response = ns.upsert(grnrec)
            data_response = json.dumps(data_response.__dict__)
            data_response = json.loads(data_response)
        else:
            grnrec = ns.ItemReceipt()
            grnrec.createdFrom = ns.RecordRef(externalId=grn_data['po_number'])
            grnrec.tranDate = grn_data["grn_date"]
            custom_field_list=[ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=122, internalId=65),
                                                        ns.StringCustomFieldRef(scriptId='custbody_mhl_vra_challannumber', value=grn_data["dc_number"]),
                                                        # ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value="api.stockone.in/static/master_docs/GRN_1/3.pdf"),
                                                        # ns.StringCustomFieldRef(scriptId='custbody_mhl_grn_veninvoicereceivedate', value=grn_data["grn_date"])
                                                        ]
            if((grn_data["invoice_quantity"]==grn_data["grn_qty"] and grn_data["invoice_value"]==grn_data["grn_value"]) or (grn_data["invoice_quantity"]==grn_data["grn_qty"] and grn_data["invoice_value"] < grn_data["grn_value"])):
                if(grn_data["invoice_no"]):
                    custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_grn_invoicenumber', value=grn_data["invoice_no"]))
                if(grn_data["invoice_date"]):
                    custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_vb_vendorinvoicedate', value=grn_data["invoice_date"]))
                if grn_data["url"]:
                    custom_field_list.append(ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value=grn_data["url"]))
            if(grn_data["dc_date"]):
                custom_field_list.append(ns.DateCustomFieldRef(scriptId='custbody_mhl_vra_challandate', value=grn_data["dc_date"]))
            grnrec.customFieldList =  ns.CustomFieldList(custom_field_list)
            for idx, data in enumerate(grn_data['items']):
                line_item = {
                'item': ns.RecordRef(externalId=data['sku_code']), 'orderLine': idx+1,
                'quantity': data['received_quantity'], 'location': ns.RecordRef(internalId=108), 'itemReceive': True}
                item.append(line_item)
            grnrec.itemList = {'item':item}
            grnrec.externalId = grn_data['grn_number']
            grnrec.tranId = grn_data['grn_number']
            data_response = ns.upsert(grnrec)
            data_response = json.dumps(data_response.__dict__)
            data_response = json.loads(data_response)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create GRN data failed for %s and error was %s' % (str(grn_data['po_number']), str(e)))
    return data_response


def netsuite_create_po(po_data, user):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
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
        # purorder.subsidiary = ns.RecordRef(internalId=po_data['company_id'])
        # purorder.department = ns.RecordRef(internalId=po_data['department_id'])
        # ns.StringCustomFieldRef(scriptId='custbody_mhl_po_billtoplantid', value=po_data['company_id'])
        purorder.customFieldList =  ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custbody_mhl_po_supplierhubid', value=po_data['supplier_id']),
                                                        ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver1', value=po_data['approval1']),
                                                        ns.StringCustomFieldRef(scriptId='custbody_mhl_po_shiptoaddress', value=po_data['ship_to_address']),
                                                        ns.StringCustomFieldRef(scriptId='custbody_mhl_po_purchaseordertype', value=product_list_id),
                                                        # ns.SelectCustomFieldRef(scriptId='custbody_mhl_po_shiptoplantid', value=ns.ListOrRecordRef(internalId=po_data['store_id'])),
                                                        # ns.SelectCustomFieldRef(scriptId='custbody_mhl_po_billtoplantid', value=ns.ListOrRecordRef(internalId=po_data['company_id'])),
                                                        ns.SelectCustomFieldRef(scriptId='custbody_in_gst_pos', value=ns.ListOrRecordRef(internalId=po_data['place_of_supply']))])
        for data in po_data['items']:
            line_item = {'item': ns.RecordRef(externalId=data['sku_code']), 'description': data['sku_desc'], 'rate': data['unit_price'],
                         'quantity':data['quantity'],'location':ns.RecordRef(internalId=108),
                         'customFieldList': ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custcol_mhl_po_mrp', value=data['mrp']),
                                                                ns.SelectCustomFieldRef(scriptId='custcol_mhl_pr_external_id', value=ns.ListOrRecordRef(externalId=po_data['full_pr_number']))])
                         }
            item.append(line_item)
        purorder.itemList = {'item':item}
        data_response = ns.upsert(purorder)
        data_response = json.dumps(data_response.__dict__)
        data_response = json.loads(data_response)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create PurchaseOrder data failed and error was %s' % (str(e)))
    return data_response
def netsuite_create_pr(pr_datas, user):
    data_response = {}
    try:
        nc = connect_tba()
        ns = nc.raw_client
        list_prs = []
        for pr_data in pr_datas:
            item = []
            purreq = ns.PurchaseRequisition()
            # purreq.entity = ns.RecordRef(internalId=6)
            # purreq.memo = "Webservice PR"
            # purreq.approvalStatus = ns.RecordRef(internalId=2)
            purreq.tranDate = pr_data['pr_date']
            purreq.tranId = pr_data['full_pr_number']
            purreq.tranDate = pr_data['pr_date']
            purreq.subsidiary = ns.RecordRef(internalId=16)
            purreq.customFieldList =  ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_prtype', value=pr_data['product_category']),
                                                         ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_approver1', value=pr_data['approval1']),
                                                         # ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_skutype', value=ns.RecordRef(internalId=1)),
                                                         ns.StringCustomFieldRef(scriptId='custbody_mhl_requestor', value=pr_data['requested_by'])
                                                         ])
            for data in pr_data['items']:
                line_item = {'item': ns.RecordRef(externalId=data['sku_code']), 'description': data['sku_desc'],
                            # 'estimatedRate': data['price'],
                             'quantity':data['quantity'], 'location':ns.RecordRef(internalId=108)}
                item.append(line_item)
            purreq.itemList = {'purchaseRequisitionItem':item}
            purreq.externalId = pr_data['full_pr_number']
            list_prs.append(purreq)
        data_response =  ns.upsertList(list_prs)
        data_response = json.dumps(data_response.__dict__)
        data_response = json.loads(data_response)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Create PurchaseRequisition data failed and error was %s' % (str(e)))
    return data_response

@login_required
@get_admin_user
def netsuite_update_supplier(request, user=''):
    try:
    	supplier = json.loads(request.body)
    except:
        return HttpResponse(json.dumps({'message': 'Please send proper data'}))
    log.info('Request params for ' + request.user.username + ' is ' + str(supplier))
    try:
        failed_status = netsuite_validate_supplier(request,supplier, user=request.user)
        status = {'status': 200, 'message': 'Success'}
        if failed_status:
            status = failed_status[0]
        return HttpResponse(json.dumps(status))
        log.info(status)
    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update supplier data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        status = {'status': 0,'message': 'Internal Server Error'}
    return HttpResponse(json.dumps(message), status=message.get('status', 200))

def netsuite_validate_supplier(request, supplier, user=''):
    from rest_api.views.masters import *
    failed_status = OrderedDict()
    sister_whs1 = list(get_sister_warehouse(user).values_list('user__username', flat=True))
    sister_whs1.append(user.username)
    sister_whs = []
    for sister_wh1 in sister_whs1:
        sister_whs.append(str(sister_wh1).lower())
    try:
        if supplier.has_key('warehouse'):
            warehouse = supplier['warehouse']
            if warehouse.lower() in sister_whs:
                user = User.objects.get(username=warehouse)
            else:
                error_message = 'Invalid Warehouse Name'
                update_error_message(failed_status, 5024, error_message, '')
        if supplier.has_key('supplierid'):
            supplier_id = supplier.get('supplierid')
            # supplier_master = get_or_none(SupplierMaster, {'supplier_id': supplier_id, 'user':user.id})
        else:
            error_message = 'supplier id missing'
            update_error_message(failed_status, 5024, error_message, '', 'supplierid')

        supplier_dict = {'name': 'suppliername', 'address': 'address', 'phone_number': 'phoneno', 'email_id': 'email',
		                 'tax_type': 'taxtype', 'po_exp_duration': 'poexpiryduration','reference_id':'nsinternalid',
		                 'spoc_name': 'spocname', 'spoc_number': 'spocnumber', 'spoc_email_id': 'spocemail',
		                 'lead_time': 'leadtime', 'credit_period': 'creditperiod', 'bank_name': 'bankname', 'ifsc_code': 'ifsccode',
		                 'branch_name': 'branchname', 'account_number': 'accountnumber', 'account_holder_name': 'accountholdername',
		                 'pincode':'pincode','city':'city','state':'state','pan_number':'panno','tin_number':'gstno','status':'status',
                         'payment_terms':'paymentterms', 'subsidiary':'subsidiary', 'place_of_supply':'placeofsupply'
		                }
        number_field = {'credit_period':0, 'lead_time':0, 'account_number':0, 'po_exp_duration':0}
        data_dict = {}
        supplier_count = 0
        gst_check = []
        for address in supplier['addresses']:
            if supplier_count and address['gstno'] not in gst_check:
                supplier_id = supplier_id+'-'+str(supplier_count)
            filter_dict = {'supplier_id': supplier_id }
            for key,val in supplier_dict.iteritems():
                value = supplier.get(val, '')
                if key in number_field.keys():
                    value = supplier.get(val, 0)
                    try:
                        value = float(value)
                    except:
                        error_message = '%s is Number field' % val
                        update_error_message(failed_status, 5024, error_message, supplier_id, 'supplierid')
                if key == 'email_id' and value:
                    if validate_supplier_email(value):
                        update_error_message(failed_status, 5024, 'Enter valid Email ID', supplier_id, 'supplierid')
                if key == 'status':
                    status = supplier.get(val, 'active')
                    value = 1
                    if status.lower() != 'active':
                        value = 0
                if key == 'address':
                    value = address.get('address', '')
                if key == 'state':
                    value = address.get('state', '')
                if key == 'city':
                    value = address.get('city', '')
                if key == 'country':
                    value = address.get('country', '')
                if key == 'tin_number':
                    value = address.get('gstno', '')
                if key == 'place_of_supply':
                    value = address.get('placeofsupply', '')
                gst_check.append(address['gstno'])
                data_dict[key] = value
                # if supplier_master and value:
                #     setattr(supplier_master, key, value)
            secondary_email_id = supplier.get('secondaryemailid', '')
            if secondary_email_id:
                secondary_email_id = secondary_email_id.split(',')
                for mail in secondary_email_id:
                    if validate_supplier_email(mail):
                        update_error_message(failed_status, 5024, 'Enter valid secondary Email ID', supplier_id, 'supplierid')
            if not failed_status:
                master_objs = sync_supplier_master(request, user, data_dict, filter_dict, secondary_email_id=secondary_email_id)
                supplier_count += 1
                log.info("supplier created for %s and supplier_id %s" %(str(user.username), str(supplier_id)))
        return failed_status.values()

    except Exception as e:
        traceback.print_exc()
        log_err.debug(traceback.format_exc())
        log_err.info('Update supplier data failed for %s and params are %s and error statement is %s' % (str(request.user.username), str(request.body), str(e)))
        failed_status = [{'status': 0,'message': 'Internal Server Error'}]
        return failed_status
