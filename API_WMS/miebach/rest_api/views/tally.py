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
#from tally.tally.api import *

class TallyAPI:
    def __init__(self, user=''):
        self.user = 1
        self.content_type = 'application/json'
        self.tally_dict = {}
        tally_obj = TallyConfiguration.objects.filter(user_id=self.user)
        if tally_obj:
            self.tally_dict = tally_obj[0].json()
        self.headers = { 'ContentType' : self.content_type }
    
    def get_item_master(self, limit=10):
        user_id = self.user
        limit = 10
        send_ids = []
        exclude_ids = OrdersAPI.objects.filter(user=user_id, engine_type='Tally', order_type='sku',\
            status__in=[1,9]).values_list('order_id', flat=True)
        sku_masters = SKUMaster.objects.exclude(id__in=exclude_ids).filter(user=user_id)[:limit]
        tally_company_name = 'Mieone'
        data_list = []
        for sku_master in sku_masters:
            data_dict = {}
            data_dict['tally_company_name'] = self.tally_dict.get('company_name', '')
            data_dict['oldItemName'] = ''
            data_dict['item_name'] = sku_master.sku_desc
            data_dict['itemAlias'] = ''
            data_dict['primaryUnitName'] = ''
            data_dict['stock_group_name'] = self.tally_dict.get('stock_group', '')
            data_dict['stock_category_name'] = self.tally_dict.get('stock_category', '')
            data_dict['isVatAppl'] = ''
            data_dict['opening_qty'] = ''
            data_dict['opening_rate'] = sku_master.price
            data_dict['opening_amt'] = 0
            data_dict['partNo'] = ''
            data_dict['description'] = sku_master.sku_desc
            data_dict['sku_code'] = sku_master.sku_code
            data_dict['unit_name'] = sku_master.measurement_type
            data_list.append(data_dict)
        return HttpResponse(json.dumps(data_list))

    def update_masters_data(self, masters, master_type, field_mapping, user_id):
        master_group = MasterGroupMapping.objects.filter(user_id=user_id, master_type=master_type)
        send_ids =[]
        data_list = []
        for master in masters:
            data_dict = {}
            data_dict['tallyCompanyName'] = self.tally_dict.get('company_name', '')
            data_dict['oldLedgerName'] = ''
            data_dict['ledgerName'] = master.name
            data_dict['ledgerAlias'] = getattr(master, field_mapping['id'])
            data_dict['updateOpeningBalance'] = getattr(master, field_mapping['id'])
            data_dict['openingBalance'] = 'Optional'
            parent_group_name = ''
            master_type = getattr(master, field_mapping['type'])
            group_obj = master_group.filter(master_value=master_type)
            if group_obj:
                parent_group_name = group_obj[0].parent_group
            data_dict['ledgerMailingName'] = master.name
            data_dict['parentGroupName'] = parent_group_name
            data_dict['address'] = master.address
            data_dict['state'] = master.state
            data_dict['pinCode'] = master.pincode
            data_dict['country'] = master.country
            data_dict['contactPerson'] = ''
            data_dict['telephoneNo'] = master.phone_number
            data_dict['faxNo'] = master.phone_number
            data_dict['email'] = master.email_id
            data_dict['tinNo'] = master.tin_number
            data_dict['cstNo'] = master.cst_number
            data_dict['panNo'] = master.pan_number
            data_dict['serviceTaxNo'] = ''
            if master_type == 'customer':
                credit_period = master.credit_period
                if not credit_period and self.tally_dict.get('credit_perod', 0):
                    credit_period = self.tally_dict.get('credit_perod')
                data_dict['defaultCreditPeriod'] = credit_period
            data_dict['maintainBillWiseDetails'] = STATUS_DICT[self.tally_dict.get('maintain_bill', 0)]
            data_list.append(data_dict)
        return data_list

    def get_supplier_master(self, limit=10):
        limit = 10
        user_id = self.user
        supplier_masters = SupplierMaster.objects.filter(user=user_id)[:limit]
        data_list = self.update_masters_data(supplier_masters,\
            'vendor', {'id': 'id', 'type': 'supplier_type'}, user_id)
        return HttpResponse(json.dumps(data_list))

    def get_customer_master(self, limit=10):
        limit=10
        user_id = self.user
        customer_masters = CustomerMaster.objects.filter(user=user_id)[:limit]
        data_list = self.update_masters_data(customer_masters,\
            'customer', {'id': 'customer_id', 'type': 'customer_type'}, user_id)
        return HttpResponse(json.dumps(data_list))

    def run_main(self):
        self.get_item_master()