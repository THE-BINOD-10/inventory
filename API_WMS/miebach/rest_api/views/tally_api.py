import os
import sys
#sys.path.append('../../tally/tally')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
import django
django.setup()
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import copy
import json
from itertools import chain
from django.db.models import Q, F
from collections import OrderedDict
from django.contrib.auth import authenticate
from django.contrib import auth
from miebach_admin.models import *
from rest_api.views.common import *
from rest_api.views.miebach_utils import *
#from tally.api import *

class TallyAPI:
    def __init__(self, user=''):
        self.user = user
        self.content_type = 'application/json'
        self.tally_dict = {}
        tally_obj = TallyConfiguration.objects.filter(user_id=user)
        if tally_obj:
            self.tally_dict = tally_obj[0].json()
        #self.tally_bridge_api = TallyBridgeApi(dll='/home/headrun/miebach_srikanth/WMS_ANGULAR/tally/tally/DLL/TallyBridgeDll.dll')
        self.headers = { 'ContentType' : self.content_type }

    def get_item_master(self, limit=10):
        send_ids = []
        user_id = self.user
        exclude_ids = OrdersAPI.objects.filter(user=user_id, engine_type='Tally', order_type='sku', status__in=[1,9]).\
                                        values_list('order_id', flat=True)
        sku_masters = SKUMaster.objects.exclude(id__in=exclude_ids).filter(user=user_id)[:limit]
        tally_company_name = 'Mieone'
        data_list = []
        for sku_master in sku_masters:
            data_dict = {}
            data_dict['item_name'] = sku_master.sku_desc
            data_dict['sku_code'] = sku_master.sku_code
            data_dict['description'] = sku_master.sku_desc
            data_dict['unit_name'] = sku_master.measurement_type
            data_dict['stock_group_name'] = self.tally_dict.get('stock_group_name', '')
            data_dict['stock_category_name'] = self.tally_dict.get('stock_category_name', '')

            #data_dict['opening_qty'] = 0 #Present Stock
            data_dict['opening_rate'] = sku_master.price
            data_dict['opening_amt'] = 0 # opening qty * opening rate
            data_dict['tally_company_name'] = self.tally_dict.get('company_name', '')
            #data_dict['post_stock_item'] = ''
            data_list.append(data_dict)
            #self.tally_bridge_api.add_item(**data_dict)
            #send_ids.append(sku_master.id)
        #if send_ids:
        #    OrdersAPI.objects.filter(user=user_id, engine_type='Tally', order_type='sku', order_id__in=send_ids).update(status=9)
        return data_list

    def update_masters_data(self, masters, master_type, field_mapping, user_id):
        master_group = MasterGroupMapping.objects.filter(user_id=user_id, master_type=master_type)
        send_ids =[]
        data_list = []
        for master in masters:
            data_dict = {}
            data_dict['tally_company_name'] = self.tally_dict.get('company_name', '')
            data_dict['ledger_name'] = master.name
            data_dict['ledger_alias'] = getattr(master, field_mapping['id'])
            parent_group_name = ''
            master_type = getattr(master, field_mapping['type'])
            group_obj = master_group.filter(master_value=master_type)
            if group_obj:
                parent_group_name = group_obj[0].parent_group
            data_dict['parentGroupName'] = parent_group_name
            data_dict['ledgerMailingName'] = master.name
            data_dict['address_1'] = master.address
            data_dict['state'] = master.state
            data_dict['pin_code'] = master.pincode
            data_dict['country'] = master.country
            data_dict['telephone_no'] = master.phone_number
            data_dict['email'] = master.email_id
            data_dict['tin_no'] = master.tin_number
            data_dict['cst_no'] = master.cst_number
            data_dict['pan_no'] = master.pan_number
            if master_type == 'customer':
                credit_period = master.credit_period
                if not credit_period and self.tally_dict.get('credit_perod', 0):
                    credit_period = self.tally_dict.get('credit_perod')
                data_dict['default_credit_period'] = credit_period
            data_dict['maintainBillWiseDetails'] = STATUS_DICT[self.tally_dict.get('maintain_bill', 0)]
            data_list.append(data_dict)
            #if master_type == 'vendor':
            #    self.tally_bridge_api.add_vendor(data_dict)
            #else:
            #    self.tally_bridge_api.add_customer(data_dict)
            #send_ids.append(master.id)
        #if send_ids:
        #    OrdersAPI.objects.filter(user=user_id, engine_type='Tally', order_type=master_type, order_id__in=send_ids).update(status=9)
        return data_list

    def get_supplier_master(self, limit=10):
        user_id = self.user
        exclude_ids = OrdersAPI.objects.filter(user=user_id, engine_type='Tally', order_type='vendor', status__in=[1,9]).\
                                            values_list('order_id', flat=True)
        supplier_masters = SupplierMaster.objects.exclude(id__in=exclude_ids).filter(user=user_id)[:limit]
        data_list = self.update_masters_data(supplier_masters, 'vendor', {'id': 'id', 'type': 'supplier_type'}, user_id)
        return data_list

    def get_customer_master(self, limit=10):
        user_id = self.user
        exclude_ids = OrdersAPI.objects.filter(user=user_id, engine_type='Tally', order_type='customer', status__in=[1,9]).\
                                            values_list('order_id', flat=True)
        customer_masters = CustomerMaster.objects.exclude(id__in=exclude_ids).filter(user=user_id)[:limit]
        data_list = self.update_masters_data(customer_masters, 'customer', {'id': 'customer_id', 'type': 'customer_type'}, user_id)
        return data_list

    def get_purchase_invoice(self, limit=10):
        user_id = self.user
        OrdersAPI.objects.filter(user=user_id, engine_type='Tally', )

    def run_main(self):
        self.get_item_master()
        self.get_customer_master()
        self.get_supplier_master()

tally_api_obj = TallyAPI(user=3)
tally_api_obj.run_main()
