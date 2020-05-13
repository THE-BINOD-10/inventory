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
        external_id = get_incremental(user, 'netsuite_external_id')
        invitem = ns.InventoryItem()
        invitem.taxSchedule = ns.RecordRef(internalId=1)
        invitem.itemId = data.sku_code
        invitem.externalId = external_id
        invitem.displayName = data.sku_desc
        invitem.itemType = data.sku_type
        invitem.vendorname = data.sku_brand
        invitem.upc = data.ean_number
        invitem.isinactive = data.status
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skucategory', value=data.sku_category))
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=data.sku_group))
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=data.sub_category))
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skuclass', value=data.sku_class))
        # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_shelflife', value=data.shelf_life))
        # invitem.purchaseunit = sku_attr_dict['Purchase UOM']
        data_response = ns.upsert(invitem)
        data_response = json.dumps(data_response.__dict__)
        data_response = json.loads(data_response)

    except Exception as e:
        import traceback
        log.debug(traceback.format_exc())
        log.info('Update/Create sku data failed for %s and error was %s' % (str(data.sku_code), str(e)))
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
        failed_status = netsuite_validate_supplier(supplier, user=request.user)
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

def netsuite_validate_supplier(supplier, user=''):
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
            supplier_master = get_or_none(SupplierMaster, {'id': supplier_id, 'user':user.id})
        else:
            error_message = 'supplier id missing'
            update_error_message(failed_status, 5024, error_message, '')

        supplier_dict = {'name': 'suppliername', 'address': 'address', 'phone_number': 'phoneno', 'email_id': 'email',
		                 'tax_type': 'taxtype', 'po_exp_duration': 'poexpiryduration',
		                 'spoc_name': 'spocname', 'spoc_number': 'spocnumber', 'spoc_email_id': 'spocemail',
		                 'lead_time': 'leadtime', 'credit_period': 'creditperiod', 'bank_name': 'bankname', 'ifsc_code': 'ifsccode',
		                 'branch_name': 'branchname', 'account_number': 'accountnumber', 'account_holder_name': 'accountholdername',
		                 'pincode':'pincode','city':'city','state':'state','pan_number':'panno','tin_number':'gstno'
		                }
        number_field = {'credit_period':0, 'lead_time':0, 'account_number':0, 'status':1, 'po_exp_duration':0}
        data_dict = {"id":supplier_id, "user":user.id, 'creation_date':datetime.datetime.now(), 'updation_date':datetime.datetime.now()}
        for key,val in supplier_dict.iteritems():
            value = supplier.get(val, '')
            if key in number_field.keys():
            	value = supplier.get(val, 0)
            if key == 'email_id' and value:
                if validate_supplier_email(value):
                    update_error_message(failed_status, 5024, 'Enter valid Email ID', '')
            data_dict[key] = value
            if supplier_master and value:
                setattr(supplier_master, key, value)
        secondary_email_id = supplier.get('secondaryemailid', '')
        if secondary_email_id:
            secondary_email_id = secondary_email_id.split(',')
            for mail in secondary_email_id:
                if validate_supplier_email(mail):
                    update_error_message(failed_status, 5024, 'Enter valid secondary Email ID', '')
        if not failed_status:
            if supplier_master:
                supplier_master.save()
            else:
                supplier_master = SupplierMaster(**data_dict)
                supplier_master.save()
            if secondary_email_id:
                for mail in secondary_email_id:
                    master_email_map = {}
                    master_email_map['user'] = user
                    master_email_map['master_id'] = supplier_master.id
                    master_email_map['master_type'] = 'supplier'
                    master_email_map['email_id'] = mail
                    master_email_map['creation_date'] = datetime.datetime.now()
                    master_email_map['updation_date'] = datetime.datetime.now()
                    master_email_map = MasterEmailMapping.objects.create(**master_email_map)
        return failed_status.values()

    except:
        traceback.print_exc()
        return failed_status.values()