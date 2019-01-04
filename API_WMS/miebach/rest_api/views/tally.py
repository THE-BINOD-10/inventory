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
from dateutil import parser

VOUCHER_NAME_DICT = {'Tax Invoice': 'Sales', '': 'Sales'}

log = init_logger('logs/tally_api.log')

class TallyAPI:
    def __init__(self, user=''):
        self.content_type = 'application/json'
        self.headers = {'ContentType': self.content_type}

    def tally_configuration(self):
        tally_config = TallyConfiguration.objects.filter(user=self.user_id).values('company_name', 'stock_group', 'stock_category', 'maintain_bill', 'automatic_voucher', 'credit_period', 'round_off_ledger')
        tally_config = tally_config[0] if tally_config else {}
        return tally_config

    def round_off_value(self, price):
        diff_round = abs(int(price) - price)
        if diff_round >= 0.01:
            price = int(price) + 1
        return price, diff_round

    def handle_updation_date(self, q_obj):
        updation_date = q_obj['updation_date']
        if not updation_date:
            updation_date = q_obj['creation_date']
        else:
            updation_date = q_obj['updation_date']
        return updation_date

    def get_sales_invoices(self, request):
        log.info('-----------------SALES INVOICE STARTED----------------------')
        """
        bill_of_lading_dt
        other_reference
        terms_of_payment
        bill_of_lading_no
        narration
        carrier_name
        voucher_no
        type_of_dealer
        terms_of_delivery_1
        type_of_voucher
        """
        self.user_id = request.POST.get('user_id', 0)
        self.user = User.objects.get(id=self.user_id)
        log.info('Sales Invoice - user_id : ' + self.user_id)
        self.updation_date = self.get_updation_date(request)
        tally_config = self.tally_configuration()
        seller_summary = SellerOrderSummary.objects.filter(order__user=self.user_id).order_by('updation_date')
        if self.updation_date:
            seller_summary = seller_summary.filter(updation_date__gt=self.updation_date).order_by('updation_date')
        seller_summary = seller_summary[:1000]
        seller_summary = seller_summary.values('id', \
                                               'pick_number', 'seller_order', 'order__order_id', 'picklist', \
                                               'quantity', 'invoice_number', 'creation_date', 'order__sku__sku_code', \
                                               'order__state', 'order__quantity', 'order__invoice_amount', \
                                               'order__order_code', 'order__pin_code', 'order__payment_mode', \
                                               'order__payment_received', 'order__unit_price', 'order__order_type', \
                                               'order__shipment_date', 'order__sku__product_type', 'order__customer_id', \
                                               'order__original_order_id', 'order__sku__sku_desc',
                                               'order__sku__measurement_type',
                                               'updation_date', 'order__customer_name', 'order_id')

        invoices = []
        from decimal import Decimal
        s_obj = {}
        for obj in seller_summary:
            key_value = obj['order__original_order_id']
            s_obj.setdefault(key_value, {})
            customer_info = CustomerMaster.objects.filter(user=self.user_id, customer_id=obj['order__customer_id']) \
                .values('customer_id', 'name', 'address', 'state', 'city', 'state', 'country', \
                        'tin_number', 'cst_number', 'pan_number', 'price_type', 'tax_type')
            customer_info = customer_info[0] if customer_info else {}
            COD = {}
            COD_obj = CustomerOrderSummary.objects.filter(order=obj['order_id'], order__user=self.user_id)
            if COD_obj:
                COD = \
                COD_obj.values('dispatch_through', 'payment_terms', 'tax_type', 'cgst_tax', 'sgst_tax', 'igst_tax',
                               'invoice_type', 'invoice_date')[0]
            s_obj[key_value]['tally_company_name'] = tally_config.get('company_name', '')
            order_no = obj['invoice_number'] if obj['invoice_number'] else obj['order__order_id']
            order_obj = OrderDetail.objects.get(id=obj['order_id'])
            invoice_date = obj['creation_date']
            #if COD['invoice_date']:
            #    invoice_date = obj['invoice_date']
            pick_number = obj['pick_number']
            if int(pick_number) == 1:
                pick_number = ''
            s_obj[key_value]['voucher_foreign_key'] = get_full_invoice_number(self.user, order_no, order_obj, invoice_date=invoice_date, pick_number=pick_number)
            s_obj[key_value]['dt_of_voucher'] = obj['creation_date'].strftime('%d/%m/%Y')
            s_obj[key_value]['voucher_type_name'] = VOUCHER_NAME_DICT.get(COD.get('invoice_type', ''),
                                                                          COD.get('invoice_type', ''))
            s_obj[key_value]['buyer_state'] = obj['order__state']
            if obj['order__original_order_id']:
                s_obj[key_value]['orders'] = [{"order_no": obj['order__original_order_id'],
                                               'order_date': obj['creation_date'].strftime('%d/%m/%Y')}]
            else:
                s_obj[key_value]['orders'] = [
                    {"order_no": "".join([obj['order__order_code'], str(obj['order__order_id'])]),
                     "order_date": obj['creation_date'].strftime('%d/%m/%Y')}]

            item_obj = {}
            item_obj['is_deemeed_positive'] = True
            item_obj['name'] = obj['order__sku__sku_desc']
            item_obj['actual_qty'] = obj['quantity']
            item_obj['billed_qty'] = obj['quantity']
            item_obj['unit'] = obj['order__sku__measurement_type']
            item_obj['rate'] = obj['order__unit_price']
            item_obj['rate_unit'] = item_obj['unit']
            item_obj['amount'] = item_obj['rate'] * item_obj['billed_qty']

            s_obj[key_value].setdefault('items', [])
            s_obj[key_value]['items'].append(item_obj)

            ledger_obj = GroupLedgerMapping.objects.filter(user_id=self.user_id, ledger_type='sales',
                                                           product_group=obj['order__sku__product_type'],
                                                           state=obj['order__state'])
            item_obj['ledger_name'] = ''
            if ledger_obj:
                item_obj['ledger_name'] = ledger_obj[0].ledger_name
            party_ledger_obj = {}
            party_ledger_obj['name'] = customer_info.get('name', '')
            if not party_ledger_obj['name']:
                party_ledger_obj['name'] = obj['order__customer_name']
            party_ledger_obj['is_deemeed_positive'] = True

            cgst_tax = COD.get('cgst_tax', 0)
            sgst_tax = COD.get('sgst_tax', 0)
            igst_tax = COD.get('igst_tax', 0)
            utgst_tax = COD.get('utgst_tax', 0)

            party_ledger_total_tax = cgst_tax + sgst_tax + igst_tax + utgst_tax
            party_amount = 0
            if item_obj['billed_qty'] and item_obj['rate']:
                party_amount = int(item_obj['billed_qty']) * float(item_obj['rate'])
            total_amount = party_amount + ((party_amount / 100) * party_ledger_total_tax)
            party_ledger_obj['amount'] = total_amount
            if 'party_ledger' in s_obj[key_value].keys():
                s_obj[key_value]['party_ledger']['amount'] += s_obj[key_value]['party_ledger'].get('amount', 0)
            else:
                s_obj[key_value]['party_ledger'] = party_ledger_obj
            s_obj[key_value].setdefault('party_ledger_tax', [])
            party_ledger_tax_obj = []
            vat_ledger = []
            if igst_tax:
                vat_ledger = VatLedgerMapping.objects.filter(tax_percentage=igst_tax, tax_type='sales',
                                                             user=self.user_id, ledger_name__icontains='igst')
            if sgst_tax:
                vat_ledger = VatLedgerMapping.objects.exclude(ledger_name__icontains='igst').filter(
                    tax_percentage=sgst_tax, tax_type='sales',
                    user=self.user_id)
                if not vat_ledger:
                    total_tax = cgst_tax + sgst_tax
                    vat_ledger = VatLedgerMapping.objects.filter(tax_percentage=total_tax, tax_type='sales',
                                                                 user=self.user_id)
            for vat_obj in vat_ledger:
                party_ledger_tax_dict = {}
                party_ledger_tax_dict['is_deemeed_positive'] = True
                party_ledger_tax_dict['entry_rate'] = vat_obj.tax_percentage
                party_ledger_tax_dict['amount'] = (party_amount / 100) * vat_obj.tax_percentage
                party_ledger_tax_dict['name'] = vat_obj.ledger_name
                party_ledger_tax_obj.append(party_ledger_tax_dict)

            order_charges_obj = OrderCharges.objects.filter(user=self.user_id, order_id=key_value)
            for amt in order_charges_obj:
                party_ledger_tax_dict = {}
                party_ledger_tax_dict['is_deemeed_positive'] = True
                party_ledger_tax_dict['entry_rate'] = 0
                party_ledger_tax_dict['amount'] = 0
                party_ledger_tax_dict['name'] = amt.charge_name
                party_ledger_obj['amount'] += amt.charge_amount
                s_obj[key_value]['party_ledger'].update(party_ledger_obj)
                party_ledger_tax_dict['amount'] += amt.charge_amount
                party_ledger_tax_obj.append(party_ledger_tax_dict)

            round_amt, diff_round = self.round_off_value(s_obj[key_value]['party_ledger'].get('amount', 0))
            if diff_round:
                party_ledger_tax_dict = {}
                party_ledger_tax_dict['is_deemeed_positive'] = True
                party_ledger_tax_dict['entry_rate'] = diff_round
                party_ledger_tax_dict['amount'] = diff_round
                party_ledger_tax_dict['name'] = tally_config.get('round_off_ledger', '')
                party_ledger_tax_obj.append(party_ledger_tax_dict)
                party_ledger_obj['amount'] = round_amt
                s_obj[key_value]['party_ledger'].update(party_ledger_obj)

            s_obj[key_value]['party_ledger_tax'] = s_obj[key_value]['party_ledger_tax'] + party_ledger_tax_obj
            s_obj[key_value]['voucher_no'] = '' if int(tally_config.get('automatic_voucher', 0)) else s_obj[key_value]['voucher_foreign_key']
            s_obj[key_value]['reference'] = obj['order__order_id']
            s_obj[key_value]['despatch_doc_no'] = obj['order__order_code']
            s_obj[key_value]['despatched_through'] = COD.get('dispatch_through', '')
            s_obj[key_value]['destination'] = customer_info.get('address', '')
            s_obj[key_value]['bill_of_lading_no'] = ''
            s_obj[key_value]['bill_of_lading_dt'] = ''
            s_obj[key_value]['carrier_name'] = ''
            s_obj[key_value]['terms_of_payment'] = COD.get('payment_terms', '')
            s_obj[key_value]['other_reference'] = ''
            s_obj[key_value]['terms_of_delivery_1'] = ''
            s_obj[key_value]['updation_date'] = self.handle_updation_date(obj)

            # added
            s_obj[key_value]['terms_of_delivery_2'] = ''
            s_obj[key_value]['use_separate_buyer_cons_addr'] = ''
            s_obj[key_value]['is_invoice'] = ''
            s_obj[key_value]['is_optional'] = ''
            s_obj[key_value]['type_of_voucher'] = ''

            s_obj[key_value]['buyer_name'] = customer_info.get('name', '')
            s_obj[key_value]['address_line1'] = customer_info.get('address', '')
            s_obj[key_value]['buyer_tin_no'] = customer_info.get('tin_number', '')
            s_obj[key_value]['buyer_cst_no'] = customer_info.get('cst_number', '')
            s_obj[key_value]['type_of_dealer'] = ''
            s_obj[key_value]['narration'] = ''
            s_obj[key_value]['creation_date'] = obj['creation_date']
            del_notes = {}
            del_notes['delivery_note_no'] = ''
            del_notes['delivery_note_Date'] = obj['creation_date'].strftime('%d/%m/%Y')

            s_obj[key_value].setdefault('del_notes', [])
            s_obj[key_value]['del_notes'].append(del_notes)
        log.info('Sales Invoice Count :'+str(len(s_obj.values())))
        log.info('-----------------SALES INVOICE ENDED----------------------')
        return HttpResponse(json.dumps(s_obj.values(), cls=DjangoJSONEncoder))

    def get_item_master(self, request):
        log.info('-----------------ITEM MASTER STARTED----------------------')
        """
        EMPTY FIELDS:
        opening_amt
        is_vat_app

        FIELDS NOT USED IN TALLY:
        opening_amt
        part_no
        stock_category_name
        """
        self.user_id = request.POST.get('user_id', 0)
        log.info('Item Master : user_id :' + self.user_id)
        self.updation_date = self.get_updation_date(request)
        tally_config = self.tally_configuration()
        send_ids = []
        sku_masters = SKUMaster.objects.filter(user=self.user_id).order_by('updation_date')
        if self.updation_date:
            stock_ids = StockDetail.objects.filter(updation_date__gt=self.updation_date, sku__user=self.user_id).\
                                        values_list('sku_id', flat=True)
            sku_masters = sku_masters.filter(Q(updation_date__gt=self.updation_date) |
                                             Q(id__in=stock_ids)).order_by('updation_date').distinct()
        sku_masters = sku_masters.values('id', 'sku_desc', 'price', 'sku_code', 'measurement_type', 'creation_date', 'updation_date')
        sku_masters = sku_masters[:1000]
        data_list = []
        for sku_master in sku_masters:
            data_dict = {}
            data_dict['tally_company_name'] = tally_config.get('company_name', '')
            data_dict['old_item_name'] = sku_master['sku_desc'].strip()
            data_dict['item_name'] = sku_master['sku_desc'].strip()
            data_dict['stock_group_name'] = tally_config.get('stock_group', '')
            data_dict['stock_category_name'] = tally_config.get('stock_category', '')
            data_dict['is_vat_app'] = ''  # if empty default True
            opening_qty = StockDetail.objects.filter(sku__user=self.user_id, sku_id=sku_master['id']).exclude(
                location__zone__zone='DAMAGED_ZONE').aggregate(Sum('quantity'))
            data_dict['opening_qty'] = 0
            if opening_qty['quantity__sum']:
                data_dict['opening_qty'] = opening_qty['quantity__sum']
            data_dict['opening_rate'] = sku_master['price']
            data_dict['opening_amt'] = data_dict['opening_qty'] * data_dict['opening_rate']
            data_dict['partNo'] = 'part_' + data_dict['item_name']
            data_dict['description'] = sku_master['sku_desc']
            data_dict['creation_date'] = sku_master['creation_date']
            data_dict['updation_date'] = self.handle_updation_date(sku_master)
            data_dict['sku_code'] = sku_master['sku_code']
            data_dict['unit_name'] = sku_master['measurement_type'] if sku_master['measurement_type'] else 'nos'
            data_list.append(data_dict)
        log.info('Item Data Count :' + str(len(data_list)))
        log.info('-----------------ITEM MASTER ENDED----------------------')
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def update_masters_data(self, masters, master_type, field_mapping, tally_config):
        """
        Customer Master

        "fax_no": "",
        "service_tax_no": "",
        "contact_person": "",
        "opening_balance": 0,

        Customer Master Not Used
        fax_no
        mobile_no
        cst_no
        service_tax_no
        contact_person

        """
        master_group = MasterGroupMapping.objects.filter(user_id=self.user_id, master_type=master_type)
        send_ids = []
        data_list = []
        for master in masters:
            data_dict = {}
            data_dict['tally_company_name'] = tally_config.get('company_name', '')
            data_dict['old_ledger_name'] = master['name']
            data_dict['ledger_name'] = master['name']
            data_dict['ledger_alias'] = ''
            data_dict['update_opening_balance'] = True
            data_dict['opening_balance'] = 0  # ?int or Float
            parent_group_name = 'Sundry Creditors'
            master_type = master[field_mapping['type']]
            if not master_type:
                master_type = 'Default'
            group_obj = master_group.filter(master_value=master_type)
            if group_obj:
                parent_group_name = group_obj[0].parent_group
            data_dict['ledger_mailing_name'] = master['name']
            data_dict['parent_group_name'] = parent_group_name
            data_dict['address_1'] = master['address']
            data_dict['address_2'] = ''
            data_dict['address_3'] = ''
            # list of states available in Tally
            data_dict['state'] = master['state']
            data_dict['pin_code'] = master['pincode']
            # list of country available in Tally
            data_dict['country'] = master['country']
            data_dict['contact_person'] = ''
            data_dict['telephone_no'] = master['phone_number']
            data_dict['fax_no'] = ''
            data_dict['email'] = master['email_id']
            data_dict['tin_no'] = master['tin_number']
            data_dict['cst_no'] = master['cst_number']
            # 5 Alpha with 4 Num with 1 Alpha
            data_dict['pan_no'] = master['pan_number']
            data_dict['mobile_no'] = ''
            data_dict['service_tax_no'] = ''
            data_dict['creation_date'] = master['creation_date']
            data_dict['updation_date'] = self.handle_updation_date(master)
            if master_type == 'customer':
                credit_period = master.credit_period
                if not credit_period and tally_config.get('credit_perod', 0):
                    credit_period = tally_config.get('credit_perod')
                data_dict['default_credit_period'] = credit_period
            data_dict['maintain_billWise_details'] = STATUS_DICT[tally_config.get('maintain_bill', 0)]
            data_list.append(data_dict)
        return data_list

    def get_updation_date(self, request):
        updation_date = request.POST.get('updation_date', '')
        return updation_date

    def get_supplier_master(self, request):
        # limit = 10
        log.info('-----------------SUPPLIER MASTER STARTED----------------------')
        self.user_id = request.POST.get('user_id', 0)
        log.info('Supplier Master user id : ' + self.user_id)
        self.updation_date = self.get_updation_date(request)
        tally_config = self.tally_configuration()
        supplier_masters = SupplierMaster.objects.filter(user=self.user_id)
        if self.updation_date:
            supplier_masters = supplier_masters.filter(updation_date__gt=self.updation_date)
            supplier_masters = customer_masters.values('name', 'address', 'state', 'pincode', 'country', 'phone_number', 'email_id', 'tin_number', 'cst_number', 'credit_period', 'id', 'supplier_type', 'pan_number', 'creation_date', 'updation_date')
            supplier_masters = supplier_masters[:1000]
        data_list = self.update_masters_data(supplier_masters, \
                                             'vendor', {'id': 'id', 'type': 'supplier_type'}, tally_config)
        log.info('Supplier Data Count :' + str(len(data_list)))
        log.info('-----------------SUPPLIER MASTER ENDS-------------------------')
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def get_customer_master(self, request):
        log.info('-----------------CUSTOMER MASTER STARTED----------------------')
        self.user_id = request.POST.get('user_id', 0)
        log.info('Customer Master user id : ' + self.user_id)
        self.updation_date = self.get_updation_date(request)
        tally_config = self.tally_configuration()
        customer_masters = CustomerMaster.objects.filter(user=self.user_id).order_by('updation_date')
        if self.updation_date:
            customer_masters = customer_masters.filter(updation_date__gt=self.updation_date).order_by('updation_date')
        customer_masters = customer_masters.values('name', 'address', 'state', 'pincode', 'country', 'phone_number', 'email_id', 'tin_number', 'cst_number', 'credit_period', 'customer_id', 'customer_type', 'pan_number', 'creation_date', 'updation_date')
        customer_masters = customer_masters[:1000]
        data_list = self.update_masters_data(customer_masters, \
                                             'customer', {'id': 'customer_id', 'type': 'customer_type'}, tally_config)
        log.info('Customer Data Count :' + str(len(data_list)))
        log.info('-----------------CUSTOMER MASTER ENDS----------------------')
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def get_sales_returns(self, request):
        self.user_id = request.POST.get('user_id', 0)
        self.updation_date = self.get_updation_date(request)
        sales_returns = []
        order_returns = {}
        tally_config = self.tally_configuration()
        order_returns_obj = OrderReturns.objects.filter(order__user=self.user_id)
        if self.updation_date:
            order_returns_obj = order_returns_obj.filter(updation_date__gt=self.updation_date)
        order_returns_obj = order_returns_obj.values('order__customer_name', 'order__state', \
                                                     'seller_order__invoice_no', 'seller_order__creation_date',
                                                     'return_id', 'seller_order__seller__address', \
                                                     'seller_order__seller__tin_number', 'creation_date',
                                                     'order__sku__sku_desc', 'quantity', 'damaged_quantity', \
                                                     'sku__measurement_type', 'order__unit_price', 'order__order_id',
                                                     'order__sku__product_type', 'order__state', \
                                                     'order__customer_id', 'order__user', 'order__address', 'updation_date')
        for obj in order_returns_obj:
            order_returns['tally_company_name'] = tally_config.get('company_name', 'Mieone')
            order_returns['voucher_foreign_key'] = obj['return_id']
            order_returns['dt_of_voucher'] = obj['creation_date'].strftime('%d/%m/%Y')
            order_returns['buyer_name'] = obj['order__customer_name']
            order_returns['buyer_state'] = obj['order__state']
            item_obj = {}
            item_obj['is_deemeed_positive'] = True
            item_obj['name'] = obj['order__sku__sku_desc']
            item_obj['actual_qty'] = obj['quantity'] + obj['damaged_quantity']
            item_obj['billed_qty'] = item_obj['actual_qty']
            item_obj['qty_unit'] = obj['sku__measurement_type']
            item_obj['rate'] = obj['order__unit_price'] if obj['order__unit_price'] else 0
            item_obj['rate_unit'] = item_obj['qty_unit']
            discount = cgst_tax = sgst_tax = igst_tax = utgst_tax = total_ledger_tax = total_amount = item_obj_amount = 0
            item_obj['discount_percentage'] = 0
            if obj['order__order_id']:
                COD = CustomerOrderSummary.objects.filter(order__id=obj['order__order_id'], order__user=self.user_id)
                COD = COD.values('discount', 'cgst_tax', 'sgst_tax', 'igst_tax', 'utgst_tax')
                COD = COD[0] if COD else {}
                discount = COD.get('discount', 0)
                cgst_tax = COD.get('cgst_tax', 0)
                sgst_tax = COD.get('sgst_tax', 0)
                igst_tax = COD.get('igst_tax', 0)
                utgst_tax = COD.get('utgst_tax', 0)
                total_ledger_tax = cgst_tax + sgst_tax + igst_tax + utgst_tax
                total_amount = item_obj['billed_qty'] * item_obj['rate']
                if discount:
                    item_obj['discount_percentage'] = "%.1f" % (float((discount * 100) / (total_amount)))
                    item_obj['discount_percentage'] = float(item_obj['discount_percentage'])
                amount_with_discount = total_amount - discount
                item_obj_amount = amount_with_discount + ((amount_with_discount * total_ledger_tax) / 100)
            item_obj['amount'] = item_obj_amount
            order_returns.setdefault('items', [])
            order_returns['items'].append(item_obj)

            party_ledger_obj = {}
            ledger_obj = GroupLedgerMapping.objects.filter(user_id=self.user_id, ledger_type='sales',
                                                           product_group=obj['order__sku__product_type'],
                                                           state=obj['order__state'])
            party_ledger_obj['name'] = ''
            if ledger_obj:
                party_ledger_obj['name'] = ledger_obj[0].ledger_name
            party_ledger_obj['is_deemed_positive'] = False
            party_ledger_obj['amount'] = item_obj_amount
            order_returns.setdefault('party_ledger', {})
            order_returns['party_ledger'].update(party_ledger_obj)
            party_ledger_tax_obj = {}
            party_ledger_tax_obj['name'] = ''
            party_ledger_obj = VatLedgerMapping.objects.filter(tax_percentage=total_ledger_tax, tax_type='sales',
                                                               user=self.user_id)
            if party_ledger_obj:
                party_ledger_tax_obj['name'] = party_ledger_obj[0].ledger_name
            party_ledger_tax_obj['entry_rate'] = total_ledger_tax
            party_ledger_tax_obj['amount'] = item_obj_amount
            party_ledger_tax_obj['is_deemed_positive'] = False

            order_returns.setdefault('party_ledger_tax', {})
            order_returns['party_ledger_tax'].update(party_ledger_tax_obj)

            order_returns['voucher_no'] = '' if int(tally_config.get('automatic_voucher', 0)) else obj['return_id']
            order_returns['reference'] = obj['seller_order__invoice_no']
            order_returns['reference_date'] = obj['seller_order__creation_date']
            order_returns['voucher_identifier'] = obj['return_id']
            try:
                customer_obj = CustomerMaster.objects.get(customer_id=obj['order__customer_id'], user=user_id)
            except:
                customer_obj = None
                order_returns['buyer_TIN_no'] = ''
                order_returns['buyer_CST_no'] = ''
                order_returns['consignee_name'] = ''
                order_returns['consignee_address'] = ''
                order_returns['consignee_address_1'] = ''
                order_returns['buyer_address_1'] = ''
            if customer_obj:
                order_returns['buyer_TIN_no'] = customer_obj.tin_number
                order_returns['buyer_CST_no'] = customer_obj.cst_number
                order_returns['consignee_name'] = customer_obj.name
                order_returns['consignee_address'] = customer_obj.address
                order_returns['consignee_address_1'] = customer_obj.address
                order_returns['buyer_address_1'] = customer_obj.address
            else:
                order_returns['buyer_TIN_no'] = ''
                order_returns['buyer_CST_no'] = ''
                order_returns['consignee_name'] = obj['order__customer_name']
                order_returns['consignee_address'] = obj['order__address']
                order_returns['consignee_address_1'] = obj['order__address']
                order_returns['buyer_address_1'] = obj['order__address']
            order_returns['type_of_dealer'] = 'Unregistered Dealer'
            order_returns['narration'] = ''
            sales_returns.append(order_returns)
        return HttpResponse(json.dumps(sales_returns, cls=DjangoJSONEncoder))

    def get_voucher(self, order):
        po_number = '%s%s_%s' % (
        order['prefix'], str(order['creation_date']).split(' ')[0].replace('-', ''), order['order_id'])
        return po_number

    def get_purchase_invoice(self, request):
        from django.core.exceptions import ObjectDoesNotExist
        data_list = []
        self.user_id = request.POST.get('user_id', 0)
        self.updation_date = self.get_updation_date(request)
        tally_config = self.tally_configuration()
        purchase_order = PurchaseOrder.objects.filter(open_po__sku__user=self.user_id)
        if self.updation_date:
            purchase_order = purchase_order.filter(updation_date=self.updation_date)
        purchase_order = purchase_order.values('id', \
                                               'order_id', 'open_po', 'received_quantity', 'saved_quantity', \
                                               'po_date', 'ship_to', 'status', 'reason', 'prefix', 'creation_date', \
                                               'updation_date', 'open_po__supplier__name', 'open_po__supplier__state', \
                                               'open_po__sgst_tax', 'open_po__cgst_tax', 'open_po__igst_tax', \
                                               'open_po__utgst_tax', 'open_po__sku__product_type',
                                               'open_po__supplier__state', \
                                               'open_po__supplier__address', 'open_po__supplier__cst_number',
                                               'open_po__supplier__tin_number', \
                                               'open_po__vendor__address', 'open_po__vendor__name',
                                               'open_po__supplier__address', \
                                               'open_po__po_name', 'open_po__sku__sku_desc',
                                               'open_po__measurement_unit', 'open_po__price')[:10]
        invoices = []
        from decimal import Decimal
        purchase_order_obj = {}
        for obj in purchase_order:
            s_obj = {}
            purchase_order_obj.setdefault(obj['order_id'], {})
            purchase_order_obj[obj['order_id']]['tally_company_name'] = tally_config.get('company_name', 'Mieone')
            purchase_order_obj[obj['order_id']]['voucher_foreign_key'] = self.get_voucher(obj)
            purchase_order_obj[obj['order_id']]['dt_of_voucher'] = obj['creation_date'].strftime('%d/%m/%Y')
            purchase_order_obj[obj['order_id']]['supplier_name'] = obj['open_po__supplier__name']
            purchase_order_obj[obj['order_id']]['supplier_state'] = obj['open_po__supplier__state']
            ledger_obj = GroupLedgerMapping.objects.filter(user_id=self.user_id, ledger_type='purchase',
                                                           product_group=obj['open_po__sku__product_type'],
                                                           state=obj['open_po__supplier__state'])
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
            total_amount = party_amount + ((party_amount / 100) * party_ledger_total_tax)
            party_ledger_obj['amount'] = total_amount
            party_ledger_obj['is_deemed_positive'] = False

            purchase_order_obj[obj['order_id']].setdefault('party_ledger', {})
            purchase_order_obj[obj['order_id']]['party_ledger'].update(party_ledger_obj)

            # optional
            purchase_order_obj[obj['order_id']]['voucher_no'] = int(tally_config.get('automatic_voucher', 0))
            purchase_order_obj[obj['order_id']]['reference'] = ''  # Supplier Invoice Number to be sent
            purchase_order_obj[obj['order_id']]['despatch_doc_no'] = ''
            COD = CustomerOrderSummary.objects.filter(order__id=obj['order_id'], order__user=self.user_id).values(
                'dispatch_through', 'payment_terms', 'tax_type')
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

            party_ledger_obj = VatLedgerMapping.objects.filter(tax_percentage=party_ledger_total_tax,
                                                               tax_type='purchase', user=self.user_id)
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

    def get_purchase_returns(self, request):
        self.user_id = request.POST.get('user_id', 0)
        data_dict = {}
        data_list = []
        data_list.append(data_dict)
        return HttpResponse(json.dumps(data_list, cls=DjangoJSONEncoder))

    def run_main(self):
        self.get_item_master()
