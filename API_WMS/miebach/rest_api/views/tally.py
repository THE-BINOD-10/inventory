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
from common import *
from miebach_utils import *
from tally.tally.api import *


class TallyAPI:
    def __init__(self, user=''):
        self.user = user
        self.content_type = 'application/json'
        self.tally_dict = {}
        tally_obj = TallyConfiguration.objects.filter(user_id=user)
        if tally_obj:
            self.tally_dict = tally_obj[0].json()
        self.headers = {'ContentType': self.content_type}

    def get_item_master(self, limit=10):
        send_ids = []
        user_id = self.user
        exclude_ids = OrdersAPI.objects.filter(user=user_id, engine_type='Tally', order_type='sku', status__in=[1, 9]). \
            values_list('order_id', flat=True)
        sku_masters = SKUMaster.objects.exclude(id__in=exclude_ids).filter(user=user_id)[:limit]
        tally_company_name = 'Mieone'
        for sku_master in sku_masters:
            data_dict = {}
            data_dict['item_name'] = sku_master.sku_desc
            data_dict['sku_code'] = sku_master.sku_code
            data_dict['description'] = sku_master.sku_desc
            data_dict['unit_name'] = sku_master.measurement_type
            data_dict['stock_group_name'] = ''
            data_dict['stock_category_name'] = sku_master.sku_category

            data_dict['opening_qty'] = 0
            data_dict['opening_rate'] = sku_master.price
            data_dict['opening_amt'] = 0
            data_dict['tally_company_name'] = self.tally_dict.get('company_name', '')
            send_ids.append(sku_master.id)

    def update_masters_data(self, masters, master_type, field_mapping, user_id):
        master_group = MasterGroupMapping.objects.filter(user_id=user_id, master_type=master_type)
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
            credit_period = master.credit_period
            if not credit_period and self.tally_dict.get('credit_perod', 0):
                credit_period = self.tally_dict.get('credit_perod')
            data_dict['default_credit_period'] = credit_period
            data_dict['maintainBillWiseDetails'] = STATUS_DICT[self.tally_dict.get('maintain_bill', 0)]

    def get_supplier_master(self, limit=10):
        user_id = self.user
        supplier_masters = SupplierMaster.objects.filter(user=user_id)[:limit]
        self.update_masters_data(supplier_masters, 'vendor', {'id': 'id', 'type': 'supplier_type'}, user_id)

    def get_customer_master(self, limit=10):
        user_id = self.user
        customer_masters = CustomerMaster.objects.filter(user=user_id)[:limit]
        self.update_masters_data(customer_masters, 'customer', {'id': 'customer_id', 'type': 'customer_type'}, user_id)

    def run_main(self):
        self.get_item_master()
