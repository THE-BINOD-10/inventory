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
            invitem.vendorname = data.get('sku_brand','')
            invitem.upc = data.get('ean_number','')
            invitem.isinactive = data.get('status','')
            invitem.itemtype = data.get('batch_based','')
            invitem.purchaseunit = data.get('measurement_type','')
            invitem.includeChildren = 'Y'
            # invitem.taxtype = data.product_type
            # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skugroup', value=data.sku_group))
            # invitem.customFieldList =  ns.CustomFieldList(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_shelflife', value=data.shelf_life))
            customFieldList = []
            if data.get('No. of Test', None):
                customFieldList.append(ns.StringCustomFieldRef(scriptId='custitem_mhl_item_nooftest', value=data.get('No. of Test')))
            if data.get('No. of flex', None):  
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_noofflex', value=data.get('No. of flex'))
                )
            if data.get('Conversion Factor', None):  
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_conversionfactor', value=data.get('Conversion Factor'))
                )
            if data.get('sku_class', None):  
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
                  ns.StringCustomFieldRef(scriptId='custitem_in_hsn_code', value=ns.ListOrRecordRef(externalId=data.get('hsn_code')))
                )
            if data.get('sub_category', None):  
                customFieldList.append(
                  ns.StringCustomFieldRef(scriptId='custitem_mhl_item_skusubcategory', value=data.get('sub_category'))
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



    def netsuite_update_create_rtv(rtv_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
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

        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create RTV data failed for %s and error was %s' % (str(rtv_data["grn_no"].split("/")[0]), str(e)))
        return rtvitem

    def netsuite_create_grn(grn_data):
        data_response = {}
        try:
            ns = self.nc.raw_client
            item = []
            grnrec = ns.ItemReceipt()
            grnrec.createdFrom = ns.RecordRef(externalId=grn_data['po_number'])
            # grnrec.tranDate = '2020-05-25T10:47:05+05:30'
            grnrec.tranDate = grn_data["grn_date"]
            grnrec.customFieldList =  ns.CustomFieldList([ns.StringCustomFieldRef(scriptId='custbody_mhl_pr_plantid', value=122, internalId=65)
                                                          # ns.StringCustomFieldRef(scriptId='custbody_mhl_upload_copy_vendorbill', value="api.stockone.in/static/master_docs/GRN_1/3.pdf")
                                                          ])
            for idx, data in enumerate(grn_data['items']):
                line_item = {
                'item': ns.RecordRef(externalId=data['sku_code']), 'orderLine': idx+1,
                'quantity': data['received_quantity'], 'location': ns.RecordRef(internalId=108), 'itemReceive': True}
                item.append(line_item)
            grnrec.itemList = {'item':item}
            grnrec.externalId = grn_data['grn_number']
            grnrec.tranId = grn_data['grn_number']

        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create GRN data failed for %s and error was %s' % (str(grn_data['po_number']), str(e)))
        return grnrec


    def netsuite_create_po(po_data):
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
                ns.SelectCustomFieldRef(scriptId='custbody_in_gst_pos', value=ns.ListOrRecordRef(internalId=28))
            ])
            for data in po_data['items']:
                line_item = {
                    'item': ns.RecordRef(externalId=data['sku_code']), 
                    'description': data['sku_desc'], 
                    'rate': data['unit_price'],
                    'quantity':data['quantity'],
                    'customFieldList': ns.CustomFieldList([
                        ns.StringCustomFieldRef(scriptId='custcol_mhl_po_mrp', value=data['mrp']),
                        ns.StringCustomFieldRef(scriptId='custcol_mhl_pr_external_id', value=po_data['full_pr_number'])
                    ])
                }
                item.append(line_item)
            purorder.itemList = {'item':item}

        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create PurchaseOrder data failed and error was %s' % (str(e)))
        return purorder

    def netsuite_create_pr(pr_data):
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
                    'location':ns.RecordRef(internalId=108)
                }
                item.append(line_item)
            purreq.itemList = { 'purchaseRequisitionItem': item }
            purreq.externalId = pr_data['full_pr_number']
        except Exception as e:
            import traceback
            log.debug(traceback.format_exc())
            log.info('Create PurchaseRequisition data failed and error was %s' % (str(e)))
        return purreq

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
