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

    def get_sales_invoices(self, request):
        #user_id= request.user.id
        user_id= 15
        tally_config = TallyConfiguration.objects.filter(user=user_id).values('tally_ip', 'tally_ip', 'tally_path',\
                                'company_name', 'stock_group', 'stock_category', 'maintain_bill', 'automatic_voucher')
        tally_config = tally_config[0] if tally_config else {}

        seller_summary = SellerOrderSummary.objects.filter(order__user=user_id).values('id',\
                            'pick_number', 'seller_order', 'order__order_id', 'picklist',\
                            'quantity', 'invoice_number', 'creation_date', 'order__sku__sku_code',\
                            'order__state', 'order__quantity', 'order__invoice_amount',\
                            'order__order_code', 'order__pin_code', 'order__payment_mode',\
                            'order__payment_received', 'order__unit_price', 'order__order_type',\
                            'order__shipment_date', 'order__sku__product_type', 'order__customer_id',\
                            'order__original_order_id', 'order__sku__sku_desc', 'order__sku__measurement_type',\
			    )[:10]
        invoices = []
        from decimal import Decimal
        for obj in seller_summary:
            s_obj = {}
            customer_info = CustomerMaster.objects.filter(user=user_id, customer_id=obj['order__customer_id'])\
                            .values('customer_id', 'name', 'address', 'state', 'city', 'state', 'country',\
                            'tin_number', 'cst_number', 'pan_number', 'price_type', 'tax_type')
            customer_info = customer_info[0] if customer_info else {}

            s_obj['tally_company_name'] = tally_config.get('company_name', '')
            s_obj['voucher_foreign_key'] = obj['invoice_number'] if obj['invoice_number'] else obj['order__order_id']
            s_obj['dt_of_voucher'] = obj['creation_date'].strftime('%d/%m/%Y')
            s_obj['voucher_typeName'] = 'Sales'
            #s_obj['buyer_state']  = customer_info.get('state')
	    s_obj['buyer_state'] = obj['order__state']
            s_obj['orders'] = [obj['order__original_order_id']] if obj['order__original_order_id'] else ["".join([obj['order__order_code'], str(obj['order__order_id'])])]

	    item_obj = {}
	    item_obj['is_deemeed_positive'] = True
	    item_obj['name'] = obj['order__sku__sku_desc']
	    item_obj['actual_qty'] = obj['quantity']
	    item_obj['billed_qty'] = obj['quantity']
	    item_obj['unit'] = obj['order__sku__measurement_type']
	    item_obj['rate'] = obj['order__unit_price']
	    item_obj['rate_unit'] = item_obj['unit']
	    item_obj['amount'] = item_obj['rate'] * item_obj['billed_qty']

	    s_obj.setdefault('items', [])
            s_obj['items'].append(item_obj)

	    ledger_obj = GroupLedgerMapping.objects.filter(user_id = user_id, ledger_type = 'sales', product_group = obj['order__sku__product_type'], state = obj['order__state'])
	    item_obj['ledger_name'] = ''
	    if ledger_obj:
	        item_obj['ledger_name'] = ledger_obj[0].name

	    party_ledger_obj = {}
	    party_ledger_obj['is_deemeed_positive'] = True
	    COD = CustomerOrderSummary.objects.filter(order=obj['order__order_id']).values('dispatch_through', 'payment_terms', 'tax_type')
            COD = COD[0] if COD else {}
	    cgst_tax = COD.get('cgst_tax', 0)
	    sgst_tax = COD.get('sgst_tax', 0)
	    igst_tax = COD.get('igst_tax', 0)
	    utgst_tax = COD.get('utgst_tax', 0)
	    party_ledger_total_tax = cgst_tax + sgst_tax + igst_tax + utgst_tax
	    party_amount = 0
	    if item_obj['billed_qty'] and item_obj['unit']:
                party_amount = int(item_obj['billed_qty']) * int(item_obj['unit'])
	    total_amount = party_amount + ( (party_amount/100) * party_ledger_total_tax )
            party_ledger_obj['amount'] = total_amount

	    party_ledger_tax_obj = {}
	    party_ledger_tax_obj['is_deemeed_positive'] = True
	    party_ledger_tax_obj['entry_rate'] = party_ledger_total_tax
	    party_ledger_tax_obj['amount'] = total_amount
	    vat_ledger = VatLedgerMapping.objects.filter(tax_percentage = party_ledger_total_tax, tax_type = 'sales', user = user_id)
            party_ledger_tax_obj['name'] = ''
            if vat_ledger:
                party_ledger_tax_obj['name'] = vat_ledger[0].ledger_name

	    s_obj.setdefault('party_ledger', {})
	    s_obj['party_ledger'].update(party_ledger_obj)

	    s_obj.setdefault('party_ledger_tax', {})
            s_obj['party_ledger_tax'].update(party_ledger_tax_obj)

            #s_obj['items'] = []
	    #[obj['order__sku__sku_code']]
            #s_obj['party_ledger'] = {'name': i.ledger_name for i in GroupLedgerMapping.objects.filter(user=user_id, product_group=obj['order__sku__product_type'], ledger_type='sales')}

            #Optional things
            #COD = CustomerOrderSummary.objects.filter(order=obj['order__order_id']).values('dispatch_through', 'payment_terms', 'tax_type')
            #COD = COD[0] if COD else {}
            #s_obj['party_ledger_tax'] = COD.get('tax_type', '')
            s_obj['voucher_no'] = '' if int(tally_config.get('automatic_voucher', 0)) else obj['order__order_id']
            s_obj['reference'] = obj['order__order_id']
            s_obj['despatch_doc_no'] = obj['order__order_code']
            s_obj['despatched_through'] = COD.get('dispatch_through', '')
            s_obj['destination'] =  customer_info.get('address', '')
            s_obj['bill_of_lading_no'] = ''
            s_obj['bill_of_lading_dt'] = ''
            s_obj['carrier_name'] = ''
            s_obj['terms_of_payment'] =  COD.get('payment_terms', '')
            s_obj['other_reference'] = ''
            s_obj['terms_of_delivery_1'] = ''
            s_obj['buyer_name'] = customer_info.get('customer_name', '')
            s_obj['address_line1'] = ''
            s_obj['buyer_tin_no'] = customer_info.get('tin_num', '')
            s_obj['buyer_cst_no'] = customer_info.get('cst_num', '')
            s_obj['type_of_dealer'] = ''
            s_obj['narration'] = ''
            s_obj['del_notes'] = ''
            invoices.append(s_obj)
        return HttpResponse(json.dumps(invoices, cls=DjangoJSONEncoder))

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
            data_dict['tally_company_name'] = self.tally_dict.get('company_name', 'Mieone')
            #data_dict['oldItemName'] = ''
            data_dict['item_name'] = sku_master.sku_desc
            data_dict['item_alias'] = ''
            #data_dict['primaryUnitName'] = ''
            data_dict['stock_group_name'] = self.tally_dict.get('stock_group', '')
            data_dict['stock_category_name'] = self.tally_dict.get('stock_category', '')
            #data_dict['isVatAppl'] = ''
            data_dict['opening_qty'] = 0
            data_dict['opening_rate'] = sku_master.price
            data_dict['opening_amt'] = 0
            #data_dict['partNo'] = ''
            #data_dict['description'] = sku_master.sku_desc
            data_dict['sku_code'] = sku_master.sku_code
            data_dict['unit_name'] = sku_master.measurement_type if sku_master.measurement_type else 'nos'
            data_list.append(data_dict)
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def update_masters_data(self, masters, master_type, field_mapping, user_id):
        master_group = MasterGroupMapping.objects.filter(user_id=user_id, master_type=master_type)
        send_ids =[]
        data_list = []
        for master in masters:
            data_dict = {}
            data_dict['tally_company_name'] = self.tally_dict.get('company_name', '')
            data_dict['oldLedgerName'] = ''
            data_dict['ledger_name'] = master.name
            data_dict['ledger_alias'] = getattr(master, field_mapping['id'])
            data_dict['updateOpeningBalance'] = getattr(master, field_mapping['id'])
            data_dict['openingBalance'] = 'Optional'
            parent_group_name = ''
            master_type = getattr(master, field_mapping['type'])
            group_obj = master_group.filter(master_value=master_type)
            if group_obj:
                parent_group_name = group_obj[0].parent_group
            data_dict['ledgerMailingName'] = master.name
            data_dict['parent_group_name'] = parent_group_name
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
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def get_customer_master(self, limit=10):
        limit=10
        user_id = self.user
        customer_masters = CustomerMaster.objects.filter(user=user_id)[:limit]
        data_list = self.update_masters_data(customer_masters,\
            'customer', {'id': 'customer_id', 'type': 'customer_type'}, user_id)
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def get_sales_returns(self, limit=10):
        user_id = self.user
        data_dict = {}
        data_list = []
        data_list.append(data_dict)
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def get_voucher(self, order):
        po_number = '%s%s_%s' % (order['prefix'], str(order['creation_date']).split(' ')[0].replace('-', ''), order['order_id'])
    	return po_number

    def get_purchase_invoice(self, limit=10):
	from django.core.exceptions import ObjectDoesNotExist
        data_list = []
        user_id= 15
        tally_config = TallyConfiguration.objects.filter(user=user_id).values('tally_ip', 'tally_ip', 'tally_path',\
                                'company_name', 'stock_group', 'stock_category', 'maintain_bill', 'automatic_voucher')
        tally_config = tally_config[0] if tally_config else {}
        purchase_order = PurchaseOrder.objects.filter(open_po__sku__user=user_id).values('id',\
                            'order_id', 'open_po', 'received_quantity', 'saved_quantity',\
                            'po_date', 'ship_to', 'status', 'reason', 'prefix', 'creation_date',\
			    'updation_date', 'open_po__supplier__name', 'open_po__supplier__state',\
			    'open_po__sgst_tax', 'open_po__cgst_tax', 'open_po__igst_tax',\
			    'open_po__utgst_tax', 'open_po__sku__product_type', 'open_po__supplier__state',\
			    'open_po__supplier__address', 'open_po__supplier__cst_number', 'open_po__supplier__tin_number',\
			    'open_po__vendor__address', 'open_po__vendor__name', 'open_po__supplier__address',\
			    'open_po__po_name', 'open_po__sku__sku_desc', 'open_po__measurement_unit', 'open_po__price')[:10]
	invoices = []
        from decimal import Decimal
	purchase_order_obj = {}
        for obj in purchase_order:
            s_obj = {}
	    purchase_order_obj.setdefault(obj['order_id'], {})
	    purchase_order_obj[obj['order_id']]['tally_company_name'] = tally_config.get('company_name', '')
            purchase_order_obj[obj['order_id']]['voucher_foreign_key'] = self.get_voucher(obj)
            purchase_order_obj[obj['order_id']]['dt_of_voucher'] = obj['creation_date'].strftime('%d/%m/%Y')
            purchase_order_obj[obj['order_id']]['supplier_name'] = obj['open_po__supplier__name']
	    purchase_order_obj[obj['order_id']]['supplier_state'] = obj['open_po__supplier__state']
	    ledger_obj = GroupLedgerMapping.objects.filter(user_id = user_id, ledger_type = 'purchase', product_group = obj['open_po__sku__product_type'], state = obj['open_po__supplier__state'])
	    item_obj = {}
            item_obj['is_deemeed_positive'] = True
            item_obj['name'] = obj['open_po__sku__sku_desc']
            item_obj['quantity'] = obj['received_quantity']
            item_obj['billed_qty'] = obj['received_quantity']
            item_obj['unit'] = obj['open_po__measurement_unit']
            item_obj['rate'] = obj['open_po__price']
            item_obj['rate_unit'] = obj['open_po__measurement_unit']
	    item_obj['amount'] = 0
	    if obj['received_quantity'] and obj['open_po__measurement_unit']:
	        item_obj['amount'] = int(obj['received_quantity']) * int(obj['open_po__measurement_unit'])
            item_obj['discount_percentage'] = 0
            item_obj['ledger_name'] = ''
	    if ledger_obj:
                party_ledger_obj['name'] = ledger_obj[0].ledger_name
            item_obj['actual_qty'] = obj['received_quantity']
	    purchase_order_obj[obj['order_id']].setdefault('items', [])
	    purchase_order_obj[obj['order_id']]['items'].append(item_obj)

	    party_ledger_obj = {}
            party_ledger_obj['name'] = ''
            if ledger_obj:
                party_ledger_obj['name'] = ledger_obj[0].ledger_name

            sgst_tax = obj['open_po__sgst_tax']
            cgst_tax = obj['open_po__cgst_tax']
            igst_tax = obj['open_po__igst_tax']
            utgst_tax = obj['open_po__utgst_tax']
            party_ledger_total_tax = float(sgst_tax) + float(cgst_tax) + float(igst_tax) + float(utgst_tax)
	    party_amount = 0
	    if obj['received_quantity'] and obj['open_po__measurement_unit']:
            	party_amount = int(obj['received_quantity']) * int(obj['open_po__measurement_unit'])
            total_amount = party_amount + ( (party_amount/100) * party_ledger_total_tax )
            party_ledger_obj['amount'] = total_amount
            party_ledger_obj['is_deemed_positive'] = False

	    purchase_order_obj[obj['order_id']].setdefault('party_ledger', {})
	    purchase_order_obj[obj['order_id']]['party_ledger'].update(party_ledger_obj)

            #optional
            purchase_order_obj[obj['order_id']]['voucher_no'] = int(tally_config.get('automatic_voucher', 0))
            purchase_order_obj[obj['order_id']]['reference'] = '' #Supplier Invoice Number to be sent
	    purchase_order_obj[obj['order_id']]['despatch_doc_no'] = ''
	    COD = CustomerOrderSummary.objects.filter(order__id = obj['order_id']).values('dispatch_through', 'payment_terms', 'tax_type')
            COD = COD[0] if COD else {}
            purchase_order_obj[obj['order_id']]['despatched_through'] = COD.get('dispatch_through', '')
            purchase_order_obj[obj['order_id']]['destination'] = obj['open_po__supplier__address']
            purchase_order_obj[obj['order_id']]['bill_of_lading_no'] = ''
            purchase_order_obj[obj['order_id']]['bill_of_lading_dt'] = ''
            purchase_order_obj[obj['order_id']]['carrier_name'] = ''
            purchase_order_obj[obj['order_id']]['terms_of_payment'] = COD.get('payment_terms', '')
            purchase_order_obj[obj['order_id']]['other_reference'] = ''
            purchase_order_obj[obj['order_id']]['terms_of_delivery_1'] = ''
            purchase_order_obj[obj['order_id']]['buyer_name'] = obj['open_po__vendor__name']
            purchase_order_obj[obj['order_id']]['address_line1'] = obj['open_po__vendor__address']
            purchase_order_obj[obj['order_id']]['buyer_tin_no'] = obj['open_po__supplier__tin_number']
            purchase_order_obj[obj['order_id']]['buyer_cst_no'] = obj['open_po__supplier__cst_number']
            purchase_order_obj[obj['order_id']]['type_of_dealer'] = 'Unregistered Dealer'
	    purchase_order_obj[obj['order_id']]['type_of_voucher'] = 'Purchase'
            purchase_order_obj[obj['order_id']]['narration'] = ''
            purchase_order_obj[obj['order_id']]['del_notes'] = ''

	    party_ledger_obj = VatLedgerMapping.objects.filter(tax_percentage = party_ledger_total_tax, tax_type = 'purchase', user = user_id)
	    party_ledger_tax = {}
	    party_ledger_tax['name'] = ''
	    if party_ledger_obj:
		party_ledger_tax['name'] = party_ledger_obj[0].ledger_name
	    party_ledger_tax['entry_rate'] = party_ledger_total_tax
	    party_ledger_tax['amount'] = total_amount
	    party_ledger_tax['is_deemed_positive'] = False
	    purchase_order_obj[obj['order_id']].setdefault('party_ledger_tax', {})
	    purchase_order_obj[obj['order_id']]['party_ledger_tax'].update(party_ledger_tax)

        return HttpResponse(json.dumps(purchase_order_obj, cls=DjangoJSONEncoder))

    def get_purchase_returns(self, limit=10):
        user_id = self.user
        data_dict = {}
        data_list = []
        data_list.append(data_dict)
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def run_main(self):
        self.get_item_master()
