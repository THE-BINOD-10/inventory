"""
 Code for Stock Reconciliation
"""
from collections import OrderedDict
from django.core.management import BaseCommand
from django.db.models import Q, FloatField
from django.db.models.functions import Cast, Concat
from django.db.models.fields import DateField, CharField
import os
import logging
import copy
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "miebach.settings")
django.setup()
from itertools import chain
from miebach_admin.models import *
from rest_api.views.common import get_sku_weight
from rest_api.views.miebach_utils import MILKBASKET_USERS
from django.db.models import Count
from datetime import datetime, date, timedelta
extra_data_fields = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'cess_tax': 0, 'value_before_tax': 0,
                     'value_after_tax': 0, 'price_before_tax': 0}

def init_logger(log_file):
    log = logging.getLogger(log_file)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=10485760, backupCount=25)
    formatter = logging.Formatter(
        '%(asctime)s.%(msecs)d: %(filename)s: %(lineno)d: %(funcName)s: %(levelname)s: %(message)s', "%Y%m%dT%H%M%S")
    handler.setFormatter(formatter)
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    return log

log = init_logger('logs/stock_reconciliation_report.log')

class Command(BaseCommand):
    help = "Stock Reconciliation"

    def handle(self, *args, **options):
        self.stdout.write("Started Stock Reconciliation Updating")


        def get_extra_data_info(batch_detail, sku, quantity, tax_type_dict):
            taxes = {'cgst_tax': 0, 'sgst_tax': 0, 'igst_tax': 0, 'cess_tax': 0}
            prices = {}
            transact_id = batch_detail.transact_id
            transact_type = batch_detail.transact_type
            tax = batch_detail.tax_percent
            prices['value_before_tax'] = batch_detail.buy_price * quantity
            prices['price_before_tax_values'] = prices['value_before_tax']
            prices['price_before_tax_qtys'] = quantity
            prices['quantity'] = quantity
            prices['value_after_tax'] = prices['value_before_tax']  + \
                                             ((prices['value_before_tax']/100)*batch_detail.tax_percent)
            if transact_type == 'po_loc':
                po_loc = POLocation.objects.filter(id=transact_id, location__zone__user=user.id)
                if po_loc.exists():
                    open_po = po_loc[0].purchase_order.open_po
                    if open_po:
                        taxes['cgst_tax'] = open_po.cgst_tax
                        taxes['sgst_tax'] = open_po.sgst_tax
                        taxes['igst_tax'] = open_po.igst_tax
                        taxes['cess_tax'] = open_po.cess_tax
            elif transact_type == 'po':
                purchase_order = PurchaseOrder.objects.filter(id=transact_id, open_po__sku__user=user.id)
                if purchase_order.exists():
                    open_po = purchase_order[0].open_po
                    if open_po:
                        taxes['cgst_tax'] = open_po.cgst_tax
                        taxes['sgst_tax'] = open_po.sgst_tax
                        taxes['igst_tax'] = open_po.igst_tax
                        taxes['cess_tax'] = open_po.cess_tax
            else:
                if tax_type_dict.get(sku.id, '') == 'intra_state':
                    taxes['cgst_tax'] = tax / 2
                    taxes['sgst_tax'] = tax / 2
                else:
                    taxes['igst_tax'] = tax
            return prices, taxes


        def sku_stats_group(group_val, group_name, sku_stats_dict, sku_detail, tax, unit_price,
                            field_type, tax_type_dict, discount=0):
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['quantity'] += sku_detail.quantity
            qty_price = (sku_detail.quantity * unit_price) - discount
            amount = qty_price
            tax_rate = 0
            if tax:
                tax_rate = ((amount / 100) * tax)
                amount = amount + tax_rate
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['unit_price_list'].append(amount)
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['amount'] += amount
            extra_data_key = (field_type, 0)
            if sku_detail.stock_detail and sku_detail.stock_detail.batch_detail:
                prices, taxes = get_extra_data_info(sku_detail.stock_detail.batch_detail, sku_detail.sku, sku_detail.quantity,
                                    tax_type_dict)
                extra_data_key = (field_type, sku_detail.stock_detail.batch_detail.tax_percent)
            taxes.update({'value_before_tax': 0, 'value_after_tax': 0, 'price_before_tax_values': [],
                          'price_before_tax_qtys': [], 'quantity': 0, 'field_type': field_type})
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['transact_data'].\
                setdefault(extra_data_key, taxes)
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['transact_data']\
                [extra_data_key]['value_before_tax'] += prices['value_before_tax']
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['transact_data']\
                [extra_data_key]['value_after_tax'] += prices['value_after_tax']
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['transact_data']\
                [extra_data_key]['quantity'] += prices['quantity']
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['transact_data'] \
                [extra_data_key]['price_before_tax_values'].append(prices['price_before_tax_values'])
            sku_stats_dict[sku_detail.sku_id][group_val][group_name]['transact_data'] \
                [extra_data_key]['price_before_tax_qtys'].append(prices['price_before_tax_qtys'])

        def stock_reconciliation_for_po_picklist(user, today, tax_type_dict):
            filterStats = OrderedDict()
            sku_stats_dict = {}
            filterStats['sku__user'] = user.id
            filterStats['creation_date__startswith'] = today.date()
            filterStats['transact_type__in'] = ['PO', 'picklist', 'inventory-upload', 'inventory-adjustment',
                                                'return', 'rtv']
            sku_detail_stats = SKUDetailStats.objects.filter(**filterStats).exclude(stock_detail__isnull=True)
            for sku_detail in sku_detail_stats:
                mrp = 0
                weight = ''
                tax = 0
                unit_price = sku_detail.stock_detail.unit_price
                if sku_detail.stock_detail.batch_detail:
                    batch_obj = sku_detail.stock_detail.batch_detail
                    mrp = batch_obj.mrp
                    weight = batch_obj.weight
                    unit_price = batch_obj.buy_price
                    tax = batch_obj.tax_percent
                order_type = ''
                if sku_detail.transact_type == 'return':
                    order_return = OrderReturns.objects.filter(id=sku_detail.transact_id, order__isnull=False)
                    if order_return.exists():
                        order_return = order_return[0]
                        unit_price = order_return.order.unit_price
                        cod = order_return.order.customerordersummary_set.filter()
                        if cod.exists():
                            cod = cod[0]
                            if cod.cgst_tax:
                                tax += (cod.cgst_tax + cod.sgst_tax)
                            else:
                                tax = cod.igst_tax

                if sku_detail.transact_type == 'picklist':
                    discount = 0
                    picklist_obj = Picklist.objects.filter(id=sku_detail.transact_id)
                    if picklist_obj.exists() and picklist_obj[0].order:
                        picklist_obj = picklist_obj[0]
                        unit_price = picklist_obj.order.unit_price
                        cod = picklist_obj.order.customerordersummary_set.filter()
                        so = picklist_obj.order.sellerorder_set.filter()
                        if so.exists():
                            seller_id = int(so[0].seller.seller_id)
                            if seller_id == 2:
                                order_type = 'customer_sales'
                            elif seller_id == 1 and picklist_obj.order.marketplace == 'STOCK TRANSFER':
                                order_type = 'stock_transfer'
                            else:
                                order_type = 'internal_sales'
                        if cod.exists():
                            cod = cod[0]
                            if cod.cgst_tax:
                                tax += (cod.cgst_tax + cod.sgst_tax)
                            else:
                                tax = cod.igst_tax
                            if order_type == 'internal_sales':
                                discount = cod.discount
                    else:
                        unit_price = 0
                group_val = (sku_detail.sku_id, mrp, weight)
                sku_stats_dict.setdefault(sku_detail.sku_id, {})
                sku_stats_dict[sku_detail.sku_id].setdefault(group_val,
                                          {'PO': {'quantity': 0, 'unit_price_list': [], 'amount': 0,
                                                  'transact_data': {}},
                                           'customer_sales': {'quantity': 0, 'unit_price_list': [], 'amount': 0,
                                                              'transact_data': {}},
                                           'internal_sales': {'quantity': 0, 'unit_price_list': [], 'amount': 0,
                                                              'transact_data': {}},
                                           'stock_transfer': {'quantity': 0, 'unit_price_list': [], 'amount': 0,
                                                              'transact_data': {}},
                                           'inventory-adjustment': {'quantity': 0, 'unit_price_list': [], 'amount': 0,
                                                                    'transact_data': {}},
                                           'rtv': {'quantity': 0, 'unit_price_list': [], 'amount': 0,
                                                   'transact_data': {}},
                                           'return': {'quantity': 0, 'unit_price_list': [], 'amount': 0,
                                                      'transact_data': {}},
                                           })
                if sku_detail.transact_type in ['PO', 'inventory-upload', 'po']:
                    field_type = 'purchase'
                    sku_stats_group(group_val, 'PO', sku_stats_dict, sku_detail, tax, unit_price,
                                    field_type, tax_type_dict)
                elif sku_detail.transact_type == 'inventory-adjustment':
                    field_type = 'adjustment'
                    sku_stats_group(group_val, 'inventory-adjustment', sku_stats_dict, sku_detail, tax,
                                    unit_price, field_type, tax_type_dict)
                elif sku_detail.transact_type == 'rtv':
                    field_type = 'rtv'
                    sku_stats_group(group_val, 'rtv', sku_stats_dict, sku_detail, tax, unit_price,
                                    field_type, tax_type_dict)
                elif sku_detail.transact_type == 'return':
                    field_type = 'returns'
                    sku_stats_group(group_val, 'return', sku_stats_dict, sku_detail, tax, unit_price,
                                    field_type, tax_type_dict)
                elif sku_detail.transact_type == 'picklist' and order_type:
                    field_type = order_type
                    sku_stats_dict[sku_detail.sku_id][group_val][order_type]['quantity'] += sku_detail.quantity
                    # qty_price = (sku_detail.quantity * unit_price) - discount
                    # amount = qty_price
                    # tax_rate = 0
                    # if tax:
                    #     tax_rate = ((amount/100)* tax)
                    #     amount = amount + tax_rate
                    sku_stats_group(group_val, order_type, sku_stats_dict, sku_detail, tax, unit_price,
                                    field_type, tax_type_dict, discount=discount)
                    # sku_stats_dict[sku_detail.sku_id][group_val][order_type]['unit_price_list'].append(amount)
                    # sku_stats_dict[sku_detail.sku_id][group_val][order_type]['amount'] += amount
                    # sku_stats_dict[sku_detail.sku_id][group_val][order_type]['transact_data'].append(extra_data)
            return sku_stats_dict

        def get_sku_stock_total(user, tax_type_dict):
            search_params = {}
            sku_stock_dict = {}
            search_params['sku__user'] = user.id
            search_params['quantity__gt'] = 0
            stock_data = StockDetail.objects.exclude(Q(receipt_number=0) | Q(location__zone__zone__in=['DAMAGED_ZONE', 'QC_ZONE'])).filter(**search_params)
            counter = 1
            for stock in stock_data:
                print counter
                counter += 1
                mrp = 0
                weight = ''
                unit_price = stock.unit_price
                tax = 0
                field_type = 'closing'
                extra_data_key = (field_type, float(0))
                if stock.batch_detail:
                    batch_detail = stock.batch_detail
                    mrp = batch_detail.mrp
                    weight = batch_detail.weight
                    unit_price = batch_detail.buy_price
                    tax = batch_detail.tax_percent
                    prices, taxes = get_extra_data_info(batch_detail, stock.sku, stock.quantity,
                                                     tax_type_dict)
                    extra_data_key = (field_type, batch_detail.tax_percent)
                taxes.update({'value_before_tax': 0, 'value_after_tax': 0, 'price_before_tax_values': [],
                              'price_before_tax_qtys': [], 'quantity': 0, 'field_type': field_type})
                group_val = (stock.sku_id, mrp, weight)
                sku_stock_dict.setdefault(stock.sku_id, {})
                sku_stock_dict[stock.sku_id].setdefault(group_val, {'quantity': 0, 'unit_price_list': [],
                                                                    'amount': 0, 'transact_data': {}})
                sku_stock_dict[stock.sku_id][group_val]['quantity'] += stock.quantity
                qty_price = stock.quantity * unit_price
                amount = qty_price
                if tax:
                    amount = amount + ((amount/100) * tax)
                sku_stock_dict[stock.sku_id][group_val]['unit_price_list'].append(qty_price)
                sku_stock_dict[stock.sku_id][group_val]['amount'] += amount
                sku_stock_dict[stock.sku_id][group_val]['transact_data'].setdefault(extra_data_key, taxes)
                sku_stock_dict[stock.sku_id][group_val]['transact_data'][extra_data_key]['value_before_tax'] += \
                    prices['value_before_tax']
                sku_stock_dict[stock.sku_id][group_val]['transact_data'][extra_data_key]['value_after_tax'] += \
                    prices['value_after_tax']
                sku_stock_dict[stock.sku_id][group_val]['transact_data'][extra_data_key]['quantity'] += \
                    prices['quantity']
                sku_stock_dict[stock.sku_id][group_val]['transact_data'][extra_data_key]['price_before_tax_values'].\
                    append(prices['price_before_tax_values'])
                sku_stock_dict[stock.sku_id][group_val]['transact_data'][extra_data_key]['price_before_tax_qtys'].\
                    append(prices['price_before_tax_qtys'])
            return sku_stock_dict


        def get_opening_stock_dict(user, today, sku_stats_dict, sku_stock_dict):
            opening_stock_dict = {}
            query_opening_stock = {'sku__user': user.id}
            yesterday = (today - timedelta(days=1)).date()
            query_opening_stock['creation_date__startswith'] = yesterday
            stock_rec_objs = StockReconciliation.objects.filter(**query_opening_stock)
            if stock_rec_objs:
                for stock_rec_obj in stock_rec_objs:
                    opening_stock_dict.setdefault(stock_rec_obj.sku_id, {})
                    group_val = (stock_rec_obj.sku_id, stock_rec_obj.mrp, stock_rec_obj.weight)
                    if group_val not in opening_stock_dict:
                        opening_stock_dict[stock_rec_obj.sku_id].setdefault(group_val, {})
                        opening_stock_dict[stock_rec_obj.sku_id][group_val] =  {'quantity': stock_rec_obj.closing_quantity,
                                                          'avg_rate': stock_rec_obj.closing_avg_rate,
                                                          'amount': stock_rec_obj.closing_amount,
                                                                                'transact_data': []}
                        exist_rec_fields = StockReconciliationFields.objects.filter(
                                                stock_reconciliation_id=stock_rec_obj.id, field_type='closing').\
                                                    values('cgst_tax', 'sgst_tax', 'igst_tax', 'cess_tax',
                                                           'value_after_tax', 'value_before_tax', 'price_before_tax',
                                                           'quantity')
                        for exist_rec_field in exist_rec_fields:
                            exist_rec_field1 = copy.deepcopy(exist_rec_field)
                            exist_rec_field1['field_type'] = 'opening'
                            opening_stock_dict[stock_rec_obj.sku_id][group_val]['transact_data'].append(exist_rec_field1)
            else:
                opening_stock_dict = {}
                for sku_id, sku_stocks_data in sku_stock_dict.iteritems():
                    opening_stock_dict.setdefault(sku_id, {})
                    for key, sku_stocks in sku_stocks_data.iteritems():
                        opening_stock_dict[sku_id].setdefault(key, {'quantity': 0, 'avg_rate': 0, 'amount': 0,
                                                                    'qty_price_sum': 0, 'transact_data': []})
                        opening_stock_dict[sku_id][key]['quantity'] = sku_stocks.get('quantity', 0)
                        opening_stock_dict[sku_id][key]['amount'] = sku_stocks.get('amount', 0)
                        stock_unit_price_list = sku_stocks.get('unit_price_list', [])
                        if stock_unit_price_list and sku_stocks.get('quantity', 0):
                            opening_stock_dict[sku_id][key]['avg_rate'] = sum(stock_unit_price_list)/sku_stocks['quantity']
                            opening_stock_dict[sku_id][key]['qty_price_sum'] += sum(stock_unit_price_list)
                            if sku_stocks.get('transact_data', ''):
                                sku_stock_transact_data = sku_stocks.get('transact_data', {}).values()
                                for ind, val in enumerate(sku_stock_transact_data):
                                    sku_stock_transact_data[ind]['field_type'] = 'opening'
                                opening_stock_dict[sku_id][key]['transact_data'] = \
                                    list(chain(opening_stock_dict[sku_id][key]['transact_data'],
                                               sku_stock_transact_data))
                for sku_id, sku_stats in sku_stats_dict.iteritems():
                    opening_stock_dict.setdefault(sku_id, {})
                    for key, sku_stat in sku_stats.iteritems():
                        opening_stock_dict[sku_id].setdefault(key, {'quantity': 0, 'avg_rate': 0, 'amount': 0, 'qty_price_sum': 0})
                        for stat_name, stat_value in sku_stat.iteritems():
                            if stat_name in ['customer_sales', 'internal_sales', 'rtv', 'stock_transfer']:
                                opening_stock_dict[sku_id][key]['quantity'] += stat_value['quantity']
                                opening_stock_dict[sku_id][key]['amount'] += stat_value['amount']
                                stat_unit_price_list = stat_value.get('unit_price_list', [])
                                if stat_unit_price_list and stat_value['quantity']:
                                    opening_stock_dict[sku_id][key]['qty_price_sum'] += sum(stat_unit_price_list)
                            elif stat_name in ['PO', 'return', 'inventory-adjustment']:
                                opening_stock_dict[sku_id][key]['quantity'] -= stat_value['quantity']
                                opening_stock_dict[sku_id][key]['amount'] -= stat_value['amount']
                                stat_unit_price_list = stat_value.get('unit_price_list', [])
                                if stat_unit_price_list and stat_value['quantity']:
                                    opening_stock_dict[sku_id][key]['qty_price_sum'] -= sum(stat_unit_price_list)
                            else:
                                print stat_name
            return opening_stock_dict

        def stock_reconciliation_group(prefix, data_dict, stock_reconciliation_dict):
            stock_reconciliation_dict[key]['%s_quantity' % prefix] = data_dict['quantity']
            avg_rate = 0
            if data_dict['unit_price_list'] and data_dict['quantity']:
                avg_rate = sum(data_dict['unit_price_list']) / data_dict['quantity']
            stock_reconciliation_dict[key][ '%s_avg_rate' % prefix] = avg_rate
            stock_reconciliation_dict[key]['%s_amount' % prefix] = data_dict['amount']
            stock_reconciliation_dict[key]['transact_data'] = \
                list(chain(stock_reconciliation_dict[key]['transact_data'], data_dict['transact_data'].values()))
        users = User.objects.filter(username__in=MILKBASKET_USERS)
        #users = User.objects.filter(username='NOIDA02')
        today = datetime.now()
        print today
        stock_rec_field_objs = []
        stock_rec_obj_ids = []
        for user in users:
            try:
                log.info("Stock Reconciliation Report Creation Started for user %s" % (user.username))
                tax_type_dict = dict(
                    SKUSupplier.objects.filter(supplier__user=user.id, preference=1).\
                                        values_list('sku_id', 'supplier__tax_type'))
                sku_stats_dict = stock_reconciliation_for_po_picklist(user, today, tax_type_dict)
                sku_stock_dict = get_sku_stock_total(user, tax_type_dict)
                opening_stock_dict = get_opening_stock_dict(user, today, sku_stats_dict, sku_stock_dict)
                skus = SKUMaster.objects.filter(user=user.id).only('id', 'sku_code')
                for sku in skus:
                    sku_stats = sku_stats_dict.get(sku.id, {})
                    sku_stocks = sku_stock_dict.get(sku.id, {})
                    sku_openings = opening_stock_dict.get(sku.id, {})
                    stock_reconciliation_dict = {}
                    for key, value in sku_stats.iteritems():
                        sku_id, mrp, weight = key
                        po_details = value['PO']
                        customer_sales_details = value['customer_sales']
                        internal_sales_details = value['internal_sales']
                        stock_transfer_details = value['stock_transfer']
                        adj_details = value['inventory-adjustment']
                        rtv_details = value['rtv']
                        return_details = value['return']
                        stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight,
                                                                   'transact_data': []})
                        if po_details:
                            stock_reconciliation_group('purchase', po_details, stock_reconciliation_dict)
                        if customer_sales_details:
                            stock_reconciliation_group('customer_sales', customer_sales_details, stock_reconciliation_dict)
                        if internal_sales_details:
                            stock_reconciliation_group('internal_sales', internal_sales_details, stock_reconciliation_dict)
                        if stock_transfer_details:
                            stock_reconciliation_group('stock_transfer', stock_transfer_details, stock_reconciliation_dict)
                        if adj_details:
                            stock_reconciliation_group('adjustment', adj_details, stock_reconciliation_dict)
                        if rtv_details:
                            stock_reconciliation_group('rtv', rtv_details, stock_reconciliation_dict)
                        if return_details:
                            stock_reconciliation_group('returns', return_details, stock_reconciliation_dict)
                    for key, value in sku_stocks.iteritems():
                        sku_id, mrp, weight = key
                        stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight,
                                                                   'transact_data': []})
                        stock_reconciliation_dict[key]['closing_quantity'] = value['quantity']
                        avg_rate = 0
                        if value['unit_price_list'] and value['quantity']:
                            avg_rate = sum(value['unit_price_list'])/value['quantity']
                        stock_reconciliation_dict[key]['closing_avg_rate'] = avg_rate
                        stock_reconciliation_dict[key]['closing_amount'] = value['amount']
                        stock_reconciliation_dict[key]['transact_data'] = \
                            list(chain(stock_reconciliation_dict[key]['transact_data'], value['transact_data'].values()))
                    for key, value in sku_openings.iteritems():
                        sku_id, mrp, weight = key
                        stock_reconciliation_dict.setdefault(key, {'sku_id': sku_id, 'mrp': mrp, 'weight': weight,
                                                                   'transact_data': []})
                        stock_reconciliation_dict[key]['opening_quantity'] = value['quantity']
                        if stock_reconciliation_dict[key].get('qty_price_sum', 0):
                            stock_reconciliation_dict[key]['opening_avg_rate'] = value['qty_price_sum']/value['quantity']
                        else:
                            stock_reconciliation_dict[key]['opening_avg_rate'] = value['avg_rate']
                        stock_reconciliation_dict[key]['opening_amount'] = abs(value['amount'])
                        if value.get('transact_data'):
                            for ind, val in enumerate(value.get('transact_data', [])):
                                value['transact_data'][ind]['field_type'] = 'opening'
                            stock_reconciliation_dict[key]['transact_data'] = \
                                list(chain(stock_reconciliation_dict[key]['transact_data'], value['transact_data']))

                    for key, stock_reconciliation_data1 in stock_reconciliation_dict.iteritems():
                        stock_reconciliation_data = copy.deepcopy(stock_reconciliation_data1)
                        stock_rec_fields = []
                        for key, value in stock_reconciliation_data1.iteritems():
                            if 'transact_data' in key:
                                if value:
                                    stock_rec_fields = list(chain(stock_rec_fields, value))
                                del stock_reconciliation_data[key]
                        stock_rec_obj, created = StockReconciliation.objects.update_or_create(sku_id=stock_reconciliation_data['sku_id'],
                                                          mrp=stock_reconciliation_data['mrp'],
                                                          weight=stock_reconciliation_data['weight'],
                                                          creation_date__startswith=today.date(),
                                                                           defaults=stock_reconciliation_data)
                        if not created:
                            stock_rec_obj_ids.append(stock_rec_obj.id)
                        for stock_rec_field in stock_rec_fields:
                            stock_rec_field['stock_reconciliation_id'] = stock_rec_obj.id
                            if 'price_before_tax_values' in stock_rec_field.keys():
                                stock_rec_field['price_before_tax'] = 0
                                if stock_rec_field['price_before_tax_values']:
                                    stock_rec_field['price_before_tax'] = \
                                        sum(stock_rec_field['price_before_tax_values'])/sum(stock_rec_field['price_before_tax_qtys'])
                                del stock_rec_field['price_before_tax_values']
                                del stock_rec_field['price_before_tax_qtys']
                            stock_rec_field_objs.append(StockReconciliationFields(**stock_rec_field))
                    if not stock_reconciliation_dict:
                        weight = get_sku_weight(sku)
                        for key, stock_reconciliation_data1 in stock_reconciliation_dict.iteritems():
                            stock_reconciliation_data = copy.deepcopy(stock_reconciliation_data1)
                            stock_rec_fields = []
                            for key, value in stock_reconciliation_data1.iteritems():
                                if 'transact_data' in key:
                                    if value:
                                        stock_rec_fields = list(chain(stock_rec_fields, value))
                                    del stock_reconciliation_data[key]
                        stock_rec_obj, created = StockReconciliation.objects.update_or_create(sku_id=sku.id,
                                                          mrp=sku.mrp,
                                                          weight=weight,
                                                          creation_date__startswith=today.date(),
                                                                           defaults={})
                        if not created:
                            stock_rec_obj_ids.append(stock_rec_obj.id)
                        for stock_rec_field in stock_rec_fields:
                            stock_rec_field['stock_reconciliation_id'] = stock_rec_obj.id
                            if 'price_before_tax_values' in stock_rec_field.keys():
                                stock_rec_field['price_before_tax'] = \
                                    sum(stock_rec_field['price_before_tax_values'])/sum(stock_rec_field['price_before_tax_qtys'])
                                del stock_rec_field['price_before_tax_values']
                                del stock_rec_field['price_before_tax_qtys']
                            stock_rec_field_objs.append(StockReconciliationFields(**stock_rec_field))
                if stock_rec_field_objs:
                    try:
                        if stock_rec_obj_ids:
                            StockReconciliationFields.objects.filter(stock_reconciliation_id__in=stock_rec_obj_ids).\
                                delete()
                            #StockReconciliationFields.objects.filter(id__in=stock_rec_obj_ids).update(creation_date=today)
                        StockReconciliationFields.objects.bulk_create(stock_rec_field_objs)
                    except Exception as e:
                        import traceback
                        log.debug(traceback.format_exc())
                        log.info('Stock Reconciliation Fields creation failed for user %s' % (str(user.username)))
                log.info("Stock Reconciliation Report Creation Ended for user %s" % (user.username))
            except Exception as e:
                import traceback
                log.debug(traceback.format_exc())
                log.info('Stock Reconciliation report creation failed for user %s' % (str(user.username)))
